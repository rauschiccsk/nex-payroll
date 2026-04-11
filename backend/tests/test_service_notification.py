"""Tests for Notification service layer."""

import inspect
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.notification import Notification
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationUpdate
from app.services.notification import (
    count_notifications,
    create_notification,
    delete_notification,
    get_notification,
    list_notifications,
    update_notification,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tenant(db_session, **overrides) -> Tenant:
    """Insert a minimal Tenant and flush; return the instance."""
    defaults = {
        "name": "Test s.r.o.",
        "ico": "12345678",
        "address_street": "Hlavna 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "schema_name": "tenant_test_12345678",
    }
    defaults.update(overrides)
    tenant = Tenant(**defaults)
    db_session.add(tenant)
    db_session.flush()
    return tenant


def _make_user(db_session, tenant_id, **overrides) -> User:
    """Insert a minimal User and flush; return the instance."""
    defaults = {
        "tenant_id": tenant_id,
        "username": "testuser",
        "email": "testuser@test.sk",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        "role": "director",
    }
    defaults.update(overrides)
    user = User(**defaults)
    db_session.add(user)
    db_session.flush()
    return user


def _make_notification_payload(tenant_id, user_id, **overrides) -> NotificationCreate:
    """Build a valid NotificationCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "type": "deadline",
        "severity": "info",
        "title": "Blizi sa termin pre vykaz SP",
        "message": "Termin pre mesacny vykaz SP je o 3 dni.",
        "related_entity": None,
        "related_entity_id": None,
    }
    defaults.update(overrides)
    return NotificationCreate(**defaults)


def _setup_prerequisites(db_session):
    """Create tenant and user; return (tenant, user)."""
    tenant = _make_tenant(db_session)
    user = _make_user(db_session, tenant.id)
    return tenant, user


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateNotification:
    """Tests for create_notification."""

    def test_create_returns_model_instance(self, db_session):
        tenant, user = _setup_prerequisites(db_session)
        payload = _make_notification_payload(tenant.id, user.id)

        result = create_notification(db_session, payload)

        assert isinstance(result, Notification)
        assert result.id is not None
        assert result.tenant_id == tenant.id
        assert result.user_id == user.id
        assert result.type == "deadline"
        assert result.severity == "info"
        assert result.title == "Blizi sa termin pre vykaz SP"
        assert result.message == "Termin pre mesacny vykaz SP je o 3 dni."
        assert result.related_entity is None
        assert result.related_entity_id is None
        assert result.is_read is False

    def test_create_with_related_entity(self, db_session):
        tenant, user = _setup_prerequisites(db_session)
        entity_id = uuid4()
        payload = _make_notification_payload(
            tenant.id,
            user.id,
            related_entity="payroll",
            related_entity_id=entity_id,
        )

        result = create_notification(db_session, payload)

        assert result.related_entity == "payroll"
        assert result.related_entity_id == entity_id

    def test_create_anomaly_type(self, db_session):
        tenant, user = _setup_prerequisites(db_session)
        payload = _make_notification_payload(
            tenant.id,
            user.id,
            type="anomaly",
            severity="warning",
            title="Odchylka v mzde",
            message="AI detegovalo neobvyklu odchylku v mzde zamestnanca.",
        )

        result = create_notification(db_session, payload)

        assert result.type == "anomaly"
        assert result.severity == "warning"

    def test_create_system_type_critical(self, db_session):
        tenant, user = _setup_prerequisites(db_session)
        payload = _make_notification_payload(
            tenant.id,
            user.id,
            type="system",
            severity="critical",
            title="Chyba synchronizacie",
            message="Synchronizacia s uctovnym systemom zlyhala.",
        )

        result = create_notification(db_session, payload)

        assert result.type == "system"
        assert result.severity == "critical"

    def test_create_approval_type(self, db_session):
        tenant, user = _setup_prerequisites(db_session)
        leave_id = uuid4()
        payload = _make_notification_payload(
            tenant.id,
            user.id,
            type="approval",
            title="Ziadost o dovolenku",
            message="Jan Novak ziada o schvalenie dovolenky.",
            related_entity="leave",
            related_entity_id=leave_id,
        )

        result = create_notification(db_session, payload)

        assert result.type == "approval"
        assert result.related_entity == "leave"
        assert result.related_entity_id == leave_id

    def test_create_multiple_for_same_user(self, db_session):
        """A user can have multiple notifications."""
        tenant, user = _setup_prerequisites(db_session)

        notif_a = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, title="First"),
        )
        notif_b = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, title="Second"),
        )

        assert notif_a.id != notif_b.id
        assert notif_a.user_id == notif_b.user_id


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetNotification:
    """Tests for get_notification."""

    def test_get_existing(self, db_session):
        tenant, user = _setup_prerequisites(db_session)
        created = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id),
        )

        fetched = get_notification(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.type == created.type
        assert fetched.title == created.title

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_notification(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListNotifications:
    """Tests for list_notifications."""

    def test_list_empty(self, db_session):
        result = list_notifications(db_session)
        assert result == []

    def test_list_returns_all(self, db_session):
        tenant, user = _setup_prerequisites(db_session)

        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, title="First"),
        )
        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, title="Second"),
        )

        result = list_notifications(db_session)
        assert len(result) == 2

    def test_list_ordering_newest_first(self, db_session):
        """Notifications are ordered by created_at descending (newest first)."""
        tenant, user = _setup_prerequisites(db_session)

        first = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, title="Older"),
        )
        second = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, title="Newer"),
        )

        result = list_notifications(db_session)
        assert len(result) == 2
        result_ids = [r.id for r in result]
        assert first.id in result_ids
        assert second.id in result_ids

    def test_list_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(
            db_session,
            ico="11111111",
            schema_name="tenant_a_11111111",
        )
        tenant_b = _make_tenant(
            db_session,
            ico="22222222",
            schema_name="tenant_b_22222222",
        )
        user_a = _make_user(
            db_session,
            tenant_a.id,
            username="user_a",
            email="a@test.sk",
        )
        user_b = _make_user(
            db_session,
            tenant_b.id,
            username="user_b",
            email="b@test.sk",
        )

        create_notification(
            db_session,
            _make_notification_payload(tenant_a.id, user_a.id),
        )
        create_notification(
            db_session,
            _make_notification_payload(tenant_b.id, user_b.id),
        )

        result = list_notifications(db_session, tenant_id=tenant_a.id)
        assert len(result) == 1
        assert result[0].tenant_id == tenant_a.id

    def test_list_scoped_by_user(self, db_session):
        tenant = _make_tenant(db_session)
        user_a = _make_user(
            db_session,
            tenant.id,
            username="user_a",
            email="a@test.sk",
        )
        user_b = _make_user(
            db_session,
            tenant.id,
            username="user_b",
            email="b@test.sk",
        )

        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user_a.id),
        )
        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user_b.id),
        )

        result = list_notifications(db_session, user_id=user_a.id)
        assert len(result) == 1
        assert result[0].user_id == user_a.id

    def test_list_filtered_by_is_read(self, db_session):
        tenant, user = _setup_prerequisites(db_session)

        notif_unread = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, title="Unread"),
        )
        notif_read = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, title="Read"),
        )
        # Mark one as read via update
        update_notification(
            db_session,
            notif_read.id,
            NotificationUpdate(is_read=True),
        )

        result_unread = list_notifications(db_session, is_read=False)
        result_read = list_notifications(db_session, is_read=True)

        assert len(result_unread) == 1
        assert result_unread[0].id == notif_unread.id
        assert len(result_read) == 1
        assert result_read[0].id == notif_read.id

    def test_list_filtered_by_type(self, db_session):
        tenant, user = _setup_prerequisites(db_session)

        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, type="deadline"),
        )
        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, type="anomaly"),
        )

        result = list_notifications(db_session, type="deadline")
        assert len(result) == 1
        assert result[0].type == "deadline"

    def test_list_filtered_by_severity(self, db_session):
        tenant, user = _setup_prerequisites(db_session)

        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, severity="info"),
        )
        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, severity="critical"),
        )

        result = list_notifications(db_session, severity="critical")
        assert len(result) == 1
        assert result[0].severity == "critical"

    def test_list_filter_combination_tenant_is_read_type(self, db_session):
        """Test combining multiple filters: tenant_id + is_read + type."""
        tenant_a = _make_tenant(
            db_session,
            ico="11111111",
            schema_name="tenant_a_11111111",
        )
        tenant_b = _make_tenant(
            db_session,
            ico="22222222",
            schema_name="tenant_b_22222222",
        )
        user_a = _make_user(
            db_session,
            tenant_a.id,
            username="user_a",
            email="a@test.sk",
        )
        user_b = _make_user(
            db_session,
            tenant_b.id,
            username="user_b",
            email="b@test.sk",
        )

        # tenant_a: unread deadline
        create_notification(
            db_session,
            _make_notification_payload(tenant_a.id, user_a.id, type="deadline"),
        )
        # tenant_a: read anomaly
        notif_read = create_notification(
            db_session,
            _make_notification_payload(tenant_a.id, user_a.id, type="anomaly"),
        )
        update_notification(
            db_session,
            notif_read.id,
            NotificationUpdate(is_read=True),
        )
        # tenant_b: unread deadline
        create_notification(
            db_session,
            _make_notification_payload(tenant_b.id, user_b.id, type="deadline"),
        )

        # Filter: tenant_a + unread + deadline => 1 result
        result = list_notifications(
            db_session,
            tenant_id=tenant_a.id,
            is_read=False,
            type="deadline",
        )
        assert len(result) == 1
        assert result[0].tenant_id == tenant_a.id
        assert result[0].type == "deadline"
        assert result[0].is_read is False

    def test_list_pagination_skip(self, db_session):
        tenant, user = _setup_prerequisites(db_session)

        for i in range(3):
            create_notification(
                db_session,
                _make_notification_payload(tenant.id, user.id, title=f"N{i}"),
            )

        result = list_notifications(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        tenant, user = _setup_prerequisites(db_session)

        for i in range(3):
            create_notification(
                db_session,
                _make_notification_payload(tenant.id, user.id, title=f"N{i}"),
            )

        result = list_notifications(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        tenant, user = _setup_prerequisites(db_session)

        for i in range(5):
            create_notification(
                db_session,
                _make_notification_payload(tenant.id, user.id, title=f"N{i}"),
            )

        result = list_notifications(db_session, skip=1, limit=2)
        assert len(result) == 2

    def test_list_default_limit_is_50(self, db_session):
        """Default limit should be 50 per project convention."""
        sig = inspect.signature(list_notifications)
        assert sig.parameters["limit"].default == 50


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCountNotifications:
    """Tests for count_notifications."""

    def test_count_empty(self, db_session):
        result = count_notifications(db_session)
        assert result == 0

    def test_count_all(self, db_session):
        tenant, user = _setup_prerequisites(db_session)
        for i in range(3):
            create_notification(
                db_session,
                _make_notification_payload(tenant.id, user.id, title=f"N{i}"),
            )

        result = count_notifications(db_session)
        assert result == 3

    def test_count_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(
            db_session,
            ico="11111111",
            schema_name="tenant_a_11111111",
        )
        tenant_b = _make_tenant(
            db_session,
            ico="22222222",
            schema_name="tenant_b_22222222",
        )
        user_a = _make_user(
            db_session,
            tenant_a.id,
            username="user_a",
            email="a@test.sk",
        )
        user_b = _make_user(
            db_session,
            tenant_b.id,
            username="user_b",
            email="b@test.sk",
        )

        create_notification(
            db_session,
            _make_notification_payload(tenant_a.id, user_a.id),
        )
        create_notification(
            db_session,
            _make_notification_payload(tenant_b.id, user_b.id),
        )

        assert count_notifications(db_session, tenant_id=tenant_a.id) == 1
        assert count_notifications(db_session, tenant_id=tenant_b.id) == 1

    def test_count_scoped_by_user(self, db_session):
        tenant = _make_tenant(db_session)
        user_a = _make_user(
            db_session,
            tenant.id,
            username="user_a",
            email="a@test.sk",
        )
        user_b = _make_user(
            db_session,
            tenant.id,
            username="user_b",
            email="b@test.sk",
        )

        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user_a.id, title="A1"),
        )
        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user_a.id, title="A2"),
        )
        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user_b.id, title="B1"),
        )

        assert count_notifications(db_session, user_id=user_a.id) == 2
        assert count_notifications(db_session, user_id=user_b.id) == 1

    def test_count_filtered_by_is_read(self, db_session):
        tenant, user = _setup_prerequisites(db_session)

        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, title="Unread"),
        )
        notif_read = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, title="Read"),
        )
        update_notification(
            db_session,
            notif_read.id,
            NotificationUpdate(is_read=True),
        )

        assert count_notifications(db_session, is_read=False) == 1
        assert count_notifications(db_session, is_read=True) == 1

    def test_count_filtered_by_type(self, db_session):
        tenant, user = _setup_prerequisites(db_session)

        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, type="deadline"),
        )
        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, type="system"),
        )
        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, type="system"),
        )

        assert count_notifications(db_session, type="deadline") == 1
        assert count_notifications(db_session, type="system") == 2

    def test_count_filtered_by_severity(self, db_session):
        tenant, user = _setup_prerequisites(db_session)

        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, severity="info"),
        )
        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id, severity="critical"),
        )

        assert count_notifications(db_session, severity="info") == 1
        assert count_notifications(db_session, severity="critical") == 1

    def test_count_with_combined_filters(self, db_session):
        """Test count with multiple filters combined."""
        tenant, user = _setup_prerequisites(db_session)

        create_notification(
            db_session,
            _make_notification_payload(
                tenant.id,
                user.id,
                type="deadline",
                severity="info",
            ),
        )
        create_notification(
            db_session,
            _make_notification_payload(
                tenant.id,
                user.id,
                type="deadline",
                severity="warning",
            ),
        )
        create_notification(
            db_session,
            _make_notification_payload(
                tenant.id,
                user.id,
                type="anomaly",
                severity="info",
            ),
        )

        assert (
            count_notifications(
                db_session,
                tenant_id=tenant.id,
                type="deadline",
                severity="info",
            )
            == 1
        )
        assert (
            count_notifications(
                db_session,
                tenant_id=tenant.id,
                type="deadline",
            )
            == 2
        )


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateNotification:
    """Tests for update_notification."""

    def test_update_single_field(self, db_session):
        tenant, user = _setup_prerequisites(db_session)
        created = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id),
        )

        updated = update_notification(
            db_session,
            created.id,
            NotificationUpdate(is_read=True),
        )

        assert updated is not None
        assert updated.is_read is True
        # unchanged fields stay the same
        assert updated.type == "deadline"
        assert updated.title == created.title

    def test_update_multiple_fields(self, db_session):
        tenant, user = _setup_prerequisites(db_session)
        created = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id),
        )

        updated = update_notification(
            db_session,
            created.id,
            NotificationUpdate(
                title="Aktualizovany titul",
                severity="warning",
            ),
        )

        assert updated is not None
        assert updated.title == "Aktualizovany titul"
        assert updated.severity == "warning"

    def test_update_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            update_notification(
                db_session,
                uuid4(),
                NotificationUpdate(is_read=True),
            )

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        tenant, user = _setup_prerequisites(db_session)
        created = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id),
        )

        updated = update_notification(
            db_session,
            created.id,
            NotificationUpdate(),
        )

        assert updated is not None
        assert updated.type == created.type
        assert updated.title == created.title

    def test_update_message(self, db_session):
        tenant, user = _setup_prerequisites(db_session)
        created = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id),
        )

        updated = update_notification(
            db_session,
            created.id,
            NotificationUpdate(message="Upravena sprava"),
        )

        assert updated is not None
        assert updated.message == "Upravena sprava"

    def test_update_is_read_sets_read_at_automatically(self, db_session):
        """Setting is_read=True must auto-set read_at server-side."""
        tenant, user = _setup_prerequisites(db_session)
        created = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id),
        )
        assert created.read_at is None

        updated = update_notification(
            db_session,
            created.id,
            NotificationUpdate(is_read=True),
        )

        assert updated.is_read is True
        assert updated.read_at is not None

    def test_update_is_read_false_clears_read_at(self, db_session):
        """Setting is_read=False must clear read_at."""
        tenant, user = _setup_prerequisites(db_session)
        created = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id),
        )
        # First mark as read
        update_notification(
            db_session,
            created.id,
            NotificationUpdate(is_read=True),
        )
        assert created.read_at is not None

        # Then mark as unread
        updated = update_notification(
            db_session,
            created.id,
            NotificationUpdate(is_read=False),
        )

        assert updated.is_read is False
        assert updated.read_at is None

    def test_update_client_supplied_read_at_is_ignored(self, db_session):
        """Client-supplied read_at must be stripped — server controls it."""
        tenant, user = _setup_prerequisites(db_session)
        created = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id),
        )

        from datetime import UTC, datetime

        fake_time = datetime(2020, 1, 1, tzinfo=UTC)
        updated = update_notification(
            db_session,
            created.id,
            NotificationUpdate(read_at=fake_time),
        )

        # read_at must remain None since is_read was never set to True
        assert updated.read_at is None
        assert updated.is_read is False

    def test_update_already_read_does_not_change_read_at(self, db_session):
        """Sending is_read=True on an already-read notification keeps original read_at."""
        tenant, user = _setup_prerequisites(db_session)
        created = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id),
        )
        # First mark as read
        first_update = update_notification(
            db_session,
            created.id,
            NotificationUpdate(is_read=True),
        )
        original_read_at = first_update.read_at

        # Mark as read again — should not change read_at
        second_update = update_notification(
            db_session,
            created.id,
            NotificationUpdate(is_read=True),
        )

        assert second_update.read_at == original_read_at


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteNotification:
    """Tests for delete_notification."""

    def test_delete_existing(self, db_session):
        tenant, user = _setup_prerequisites(db_session)
        created = create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id),
        )

        deleted = delete_notification(db_session, created.id)

        assert deleted is True
        assert get_notification(db_session, created.id) is None

    def test_delete_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            delete_notification(db_session, uuid4())


# ---------------------------------------------------------------------------
# FK RESTRICT delete tests
# ---------------------------------------------------------------------------


class TestFKRestrictNotification:
    """FK RESTRICT enforcement: raw SQL DELETE on parent must fail when child exists."""

    def test_delete_tenant_blocked_by_notification(self, db_session):
        """Deleting a tenant that has notifications must raise due to RESTRICT FK."""
        tenant, user = _setup_prerequisites(db_session)
        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id),
        )
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM public.tenants WHERE id = :id"),
                {"id": str(tenant.id)},
            )
            db_session.flush()

    def test_delete_user_blocked_by_notification(self, db_session):
        """Deleting a user that has notifications must raise due to RESTRICT FK."""
        tenant, user = _setup_prerequisites(db_session)
        create_notification(
            db_session,
            _make_notification_payload(tenant.id, user.id),
        )
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM users WHERE id = :id"),
                {"id": str(user.id)},
            )
            db_session.flush()
