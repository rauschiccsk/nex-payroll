"""Service layer for deadline monitoring.

Checks statutory deadlines against the current date and generates
notifications for approaching deadlines.  Per DESIGN.md §5.13:
  - Deadline notifications generated at 7, 3, and 1 day(s) before
  - Auto-cleanup of notifications older than 90 days

All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.statutory_deadline import StatutoryDeadline
from app.models.user import User
from app.schemas.notification import NotificationCreate
from app.services.notification import create_notification

# Days before deadline to generate notifications
REMINDER_DAYS = (7, 3, 1)

# Notifications older than this are cleaned up
CLEANUP_AGE_DAYS = 90


# ---------------------------------------------------------------------------
# check_upcoming_deadlines — core monitoring function
# ---------------------------------------------------------------------------


def check_upcoming_deadlines(
    db: Session,
    *,
    tenant_id: UUID,
    reference_date: date | None = None,
) -> list[Notification]:
    """Check statutory deadlines and create notifications for upcoming ones.

    For each active statutory deadline, checks if the next occurrence
    falls within the reminder windows (7, 3, 1 days).  Creates
    notifications for all users in the tenant with role 'director'
    or 'accountant'.

    Returns a list of newly created Notification objects.
    """
    if reference_date is None:
        reference_date = date.today()

    # Get active statutory deadlines
    stmt = select(StatutoryDeadline).where(
        StatutoryDeadline.valid_from <= reference_date,
    )
    deadlines = list(db.execute(stmt).scalars().all())

    # Filter out expired deadlines
    active_deadlines = [d for d in deadlines if d.valid_to is None or d.valid_to >= reference_date]

    # Get director and accountant users for this tenant
    user_stmt = select(User).where(
        User.tenant_id == tenant_id,
        User.is_active.is_(True),
        User.role.in_(["director", "accountant"]),
    )
    users = list(db.execute(user_stmt).scalars().all())

    if not users:
        return []

    created_notifications: list[Notification] = []

    for deadline in active_deadlines:
        next_date = _compute_next_deadline_date(deadline, reference_date)
        if next_date is None:
            continue

        days_until = (next_date - reference_date).days

        if days_until not in REMINDER_DAYS:
            continue

        severity = _severity_for_days(days_until)

        for user in users:
            # Check if notification already exists for this deadline/user/date
            existing = db.execute(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.tenant_id == tenant_id,
                    Notification.user_id == user.id,
                    Notification.type == "deadline",
                    Notification.related_entity == "statutory_deadline",
                    Notification.related_entity_id == deadline.id,
                    Notification.title.contains(str(next_date)),
                )
            ).scalar_one()

            if existing > 0:
                continue

            payload = NotificationCreate(
                tenant_id=tenant_id,
                user_id=user.id,
                type="deadline",
                severity=severity,
                title=f"Blíži sa termín: {deadline.name} ({next_date})",
                message=(
                    f"Termín pre {deadline.name} ({deadline.institution}) "
                    f"je o {days_until} {'deň' if days_until == 1 else 'dni'}. "
                    f"Dátum: {next_date}."
                ),
                related_entity="statutory_deadline",
                related_entity_id=deadline.id,
            )
            notification = create_notification(db, payload)
            created_notifications.append(notification)

    return created_notifications


# ---------------------------------------------------------------------------
# cleanup_old_notifications — remove stale notifications
# ---------------------------------------------------------------------------


def cleanup_old_notifications(
    db: Session,
    *,
    tenant_id: UUID,
    max_age_days: int = CLEANUP_AGE_DAYS,
) -> int:
    """Delete notifications older than *max_age_days* for a tenant.

    Per DESIGN.md §5.13: auto-cleanup notifications older than 90 days.
    Returns the number of deleted records.
    """
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)

    stmt = delete(Notification).where(
        Notification.tenant_id == tenant_id,
        Notification.created_at < cutoff,
    )
    result = db.execute(stmt)
    db.flush()
    return result.rowcount


# ---------------------------------------------------------------------------
# get_upcoming_deadlines — list upcoming deadlines without creating notifs
# ---------------------------------------------------------------------------


def get_upcoming_deadlines(
    db: Session,
    *,
    days_ahead: int = 30,
    reference_date: date | None = None,
) -> list[dict]:
    """Return a list of upcoming statutory deadlines within *days_ahead* days.

    Does NOT create notifications — useful for dashboard display.
    Each item includes deadline info and computed next date.
    """
    if reference_date is None:
        reference_date = date.today()

    stmt = select(StatutoryDeadline).where(
        StatutoryDeadline.valid_from <= reference_date,
    )
    deadlines = list(db.execute(stmt).scalars().all())

    results = []
    for deadline in deadlines:
        if deadline.valid_to is not None and deadline.valid_to < reference_date:
            continue

        next_date = _compute_next_deadline_date(deadline, reference_date)
        if next_date is None:
            continue

        days_until = (next_date - reference_date).days
        if 0 <= days_until <= days_ahead:
            results.append(
                {
                    "deadline_id": str(deadline.id),
                    "code": deadline.code,
                    "name": deadline.name,
                    "institution": deadline.institution,
                    "deadline_type": deadline.deadline_type,
                    "next_date": next_date.isoformat(),
                    "days_until": days_until,
                    "severity": _severity_for_days(days_until),
                }
            )

    results.sort(key=lambda x: x["days_until"])
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_next_deadline_date(
    deadline: StatutoryDeadline,
    reference_date: date,
) -> date | None:
    """Compute the next occurrence of a deadline relative to *reference_date*.

    Returns ``None`` if the deadline type doesn't have a computable next date.
    """
    if deadline.day_of_month is None:
        return None

    if deadline.deadline_type == "monthly":
        # Try current month first, then next month
        try:
            candidate = reference_date.replace(day=deadline.day_of_month)
        except ValueError:
            # Day doesn't exist in this month (e.g. Feb 31)
            # Move to next month
            if reference_date.month == 12:
                candidate = date(reference_date.year + 1, 1, deadline.day_of_month)
            else:
                try:
                    candidate = date(
                        reference_date.year,
                        reference_date.month + 1,
                        deadline.day_of_month,
                    )
                except ValueError:
                    return None

        if candidate < reference_date:
            # Already passed this month, use next month
            if reference_date.month == 12:
                try:
                    candidate = date(reference_date.year + 1, 1, deadline.day_of_month)
                except ValueError:
                    return None
            else:
                try:
                    candidate = date(
                        reference_date.year,
                        reference_date.month + 1,
                        deadline.day_of_month,
                    )
                except ValueError:
                    return None

        return candidate

    if deadline.deadline_type == "annual":
        if deadline.month_of_year is None:
            return None
        try:
            candidate = date(
                reference_date.year,
                deadline.month_of_year,
                deadline.day_of_month,
            )
        except ValueError:
            return None

        if candidate < reference_date:
            try:
                candidate = date(
                    reference_date.year + 1,
                    deadline.month_of_year,
                    deadline.day_of_month,
                )
            except ValueError:
                return None

        return candidate

    # one_time deadlines — fixed date, only if in the future
    if deadline.deadline_type == "one_time":
        if deadline.month_of_year is None:
            return None
        try:
            candidate = date(
                reference_date.year,
                deadline.month_of_year,
                deadline.day_of_month,
            )
        except ValueError:
            return None
        return candidate if candidate >= reference_date else None

    return None


def _severity_for_days(days_until: int) -> str:
    """Map days until deadline to notification severity."""
    if days_until <= 1:
        return "critical"
    if days_until <= 3:
        return "warning"
    return "info"
