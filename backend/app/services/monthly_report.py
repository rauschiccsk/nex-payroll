"""Service layer for MonthlyReport entity.

Provides CRUD operations over the monthly_reports table (tenant-specific schema).
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.monthly_report import MonthlyReport
from app.schemas.monthly_report import MonthlyReportCreate, MonthlyReportUpdate

ALLOWED_REPORT_TYPES = frozenset({"sp_monthly", "zp_vszp", "zp_dovera", "zp_union", "tax_prehled"})
ALLOWED_STATUSES = frozenset({"generated", "submitted", "accepted", "rejected"})


def _validate_report_type(value: str | None) -> None:
    """Raise ``ValueError`` if *value* is not a recognised report_type."""
    if value is not None and value not in ALLOWED_REPORT_TYPES:
        raise ValueError(f"Invalid report_type={value!r}. Allowed values: {sorted(ALLOWED_REPORT_TYPES)}")


def _validate_status(value: str | None) -> None:
    """Raise ``ValueError`` if *value* is not a recognised status."""
    if value is not None and value not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid status={value!r}. Allowed values: {sorted(ALLOWED_STATUSES)}")


def count_monthly_reports(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    report_type: str | None = None,
    status: str | None = None,
    period_year: int | None = None,
    period_month: int | None = None,
) -> int:
    """Return the total number of monthly reports matching the given filters.

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    _validate_report_type(report_type)
    _validate_status(status)

    stmt = select(func.count()).select_from(MonthlyReport)

    if tenant_id is not None:
        stmt = stmt.where(MonthlyReport.tenant_id == tenant_id)

    if report_type is not None:
        stmt = stmt.where(MonthlyReport.report_type == report_type)

    if status is not None:
        stmt = stmt.where(MonthlyReport.status == status)

    if period_year is not None:
        stmt = stmt.where(MonthlyReport.period_year == period_year)

    if period_month is not None:
        stmt = stmt.where(MonthlyReport.period_month == period_month)

    return db.execute(stmt).scalar_one()


def list_monthly_reports(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    report_type: str | None = None,
    status: str | None = None,
    period_year: int | None = None,
    period_month: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[MonthlyReport]:
    """Return a paginated list of monthly reports ordered by period (desc).

    When *tenant_id* is provided the result is scoped to that tenant.
    When *report_type* is provided the result is filtered by report type.
    When *status* is provided the result is filtered by status.
    When *period_year* / *period_month* are provided the result is filtered
    to the given period.
    """
    _validate_report_type(report_type)
    _validate_status(status)

    stmt = select(MonthlyReport).order_by(
        MonthlyReport.period_year.desc(),
        MonthlyReport.period_month.desc(),
    )

    if tenant_id is not None:
        stmt = stmt.where(MonthlyReport.tenant_id == tenant_id)

    if report_type is not None:
        stmt = stmt.where(MonthlyReport.report_type == report_type)

    if status is not None:
        stmt = stmt.where(MonthlyReport.status == status)

    if period_year is not None:
        stmt = stmt.where(MonthlyReport.period_year == period_year)

    if period_month is not None:
        stmt = stmt.where(MonthlyReport.period_month == period_month)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_monthly_report(db: Session, report_id: UUID) -> MonthlyReport | None:
    """Return a single monthly report by primary key, or ``None``."""
    return db.get(MonthlyReport, report_id)


def create_monthly_report(
    db: Session,
    payload: MonthlyReportCreate,
) -> MonthlyReport:
    """Insert a new monthly report record and flush (no commit).

    Raises ``ValueError`` if a report with the same
    ``(tenant_id, period_year, period_month, report_type)`` already exists.
    """
    _validate_report_type(payload.report_type)
    _validate_status(payload.status)

    dup_stmt = select(MonthlyReport).where(
        MonthlyReport.tenant_id == payload.tenant_id,
        MonthlyReport.period_year == payload.period_year,
        MonthlyReport.period_month == payload.period_month,
        MonthlyReport.report_type == payload.report_type,
    )
    existing = db.execute(dup_stmt).scalar_one_or_none()
    if existing is not None:
        raise ValueError(
            f"MonthlyReport for report_type={payload.report_type!r} "
            f"period={payload.period_year}/{payload.period_month} "
            f"already exists in tenant {payload.tenant_id}"
        )

    report = MonthlyReport(**payload.model_dump())
    db.add(report)
    db.flush()
    return report


def update_monthly_report(
    db: Session,
    report_id: UUID,
    payload: MonthlyReportUpdate,
) -> MonthlyReport:
    """Partially update an existing monthly report record.

    Only fields explicitly set in *payload* are changed.
    Raises ``ValueError`` if the report is not found.
    """
    update_data = payload.model_dump(exclude_unset=True)

    if "report_type" in update_data:
        _validate_report_type(update_data["report_type"])
    if "status" in update_data:
        _validate_status(update_data["status"])

    report = db.get(MonthlyReport, report_id)
    if report is None:
        raise ValueError(f"MonthlyReport with id={report_id} not found")

    for field, value in update_data.items():
        setattr(report, field, value)

    db.flush()
    return report


def delete_monthly_report(db: Session, report_id: UUID) -> None:
    """Delete a monthly report by primary key (hard delete).

    Raises ``ValueError`` if the report is not found.
    """
    report = db.get(MonthlyReport, report_id)
    if report is None:
        raise ValueError(f"MonthlyReport with id={report_id} not found")

    db.delete(report)
    db.flush()
