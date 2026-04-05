"""Tests for Notification model (app.models.notification)."""

import uuid

import pytest
from sqlalchemy import Boolean, String, Text, inspect, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.models.notification import Notification
from app.models.tenant import Tenant
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers — reusable fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant(db_session):
    """Create a Tenant required as FK parent."""
    t = Tenant(
        name="Notification Test Firma s.r.o.",
        ico="77000015",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK0000000000000000000077",
        schema_name="tenant_test_notification",
    )
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture()
def user(db_session, tenant):
    """Create a User required as FK parent for user_id."""
    u = User(
        tenant_id=tenant.id,
        username="notif_user",
        email="notif@test.sk",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="accountant",
    )
    db_session.add(u)
    db_session.flush()
    return u


def _make_notification(tenant, user, **overrides):
    """Return a Notification instance with sensible defaults; overrides win."""
    defaults = {
        "tenant_id": tenant.id,
        "user_id": user.id,
        "type": "deadline",
        "title": "SP deadline approaching",
        "message": "Sociálna poisťovňa deadline is in 3 days.",
    }
    defaults.update(overrides)
    return Notification(**defaults)


# ===================================================================
# Schema / metadata tests (no DB required)
# ===================================================================


class TestNotificationSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert Notification.__tablename__ == "notifications"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(Notification, Base)

    def test_inherits_uuid_mixin(self):
        from app.models.base import UUIDMixin

        assert issubclass(Notification, UUIDMixin)

    def test_inherits_timestamp_mixin(self):
        from app.models.base import TimestampMixin

        assert issubclass(Notification, TimestampMixin)


class TestNotificationColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(Notification)

    def test_id_column(self):
        col = self.mapper.columns["id"]
        assert col.primary_key is True
        assert isinstance(col.type, UUID)
        assert col.server_default is not None

    def test_tenant_id_column(self):
        col = self.mapper.columns["tenant_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_user_id_column(self):
        col = self.mapper.columns["user_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_type_column(self):
        col = self.mapper.columns["type"]
        assert isinstance(col.type, String)
        assert col.type.length == 50
        assert col.nullable is False

    def test_severity_column(self):
        col = self.mapper.columns["severity"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is False
        assert col.server_default is not None

    def test_severity_server_default_info(self):
        col = self.mapper.columns["severity"]
        assert "info" in str(col.server_default.arg)

    def test_title_column(self):
        col = self.mapper.columns["title"]
        assert isinstance(col.type, String)
        assert col.type.length == 200
        assert col.nullable is False

    def test_message_column(self):
        col = self.mapper.columns["message"]
        assert isinstance(col.type, Text)
        assert col.nullable is False

    def test_related_entity_column(self):
        col = self.mapper.columns["related_entity"]
        assert isinstance(col.type, String)
        assert col.type.length == 50
        assert col.nullable is True

    def test_related_entity_id_column(self):
        col = self.mapper.columns["related_entity_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is True

    def test_is_read_column(self):
        col = self.mapper.columns["is_read"]
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert col.server_default is not None

    def test_is_read_server_default_false(self):
        col = self.mapper.columns["is_read"]
        assert "false" in str(col.server_default.arg).lower()

    def test_read_at_column(self):
        col = self.mapper.columns["read_at"]
        assert isinstance(col.type, TIMESTAMP)
        assert col.type.timezone is True
        assert col.nullable is True

    def test_check_constraint_type(self):
        constraints = Notification.__table__.constraints
        ck_names = [c.name for c in constraints if c.name and c.name.startswith("ck_")]
        assert "ck_notifications_type" in ck_names

    def test_check_constraint_severity(self):
        constraints = Notification.__table__.constraints
        ck_names = [c.name for c in constraints if c.name and c.name.startswith("ck_")]
        assert "ck_notifications_severity" in ck_names

    def test_index_tenant_user_is_read(self):
        indexes = Notification.__table__.indexes
        ix_names = [ix.name for ix in indexes]
        assert "ix_notifications_tenant_user_is_read" in ix_names

    def test_index_tenant_created_at(self):
        indexes = Notification.__table__.indexes
        ix_names = [ix.name for ix in indexes]
        assert "ix_notifications_tenant_created_at" in ix_names


# ===================================================================
# Repr
# ===================================================================


class TestNotificationRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        user_id = uuid.uuid4()
        notif = Notification(
            user_id=user_id,
            type="deadline",
            severity="warning",
            title="Test deadline",
            is_read=False,
        )
        result = repr(notif)
        assert "Notification" in result
        assert "deadline" in result
        assert "warning" in result
        assert "Test deadline" in result

    def test_repr_contains_is_read(self):
        notif = Notification(
            user_id=uuid.uuid4(),
            type="anomaly",
            severity="critical",
            title="Payroll anomaly",
            is_read=True,
        )
        result = repr(notif)
        assert "True" in result


# ===================================================================
# Constraint tests (DB required)
# ===================================================================


class TestNotificationConstraints:
    """DB-level constraint enforcement."""

    def test_fk_tenant_nonexistent(self, db_session, user):
        """FK to tenant must exist."""
        notif = Notification(
            tenant_id=uuid.uuid4(),
            user_id=user.id,
            type="deadline",
            title="Test",
            message="Test msg",
        )
        db_session.add(notif)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_user_nonexistent(self, db_session, tenant):
        """FK to user must exist."""
        notif = Notification(
            tenant_id=tenant.id,
            user_id=uuid.uuid4(),
            type="deadline",
            title="Test",
            message="Test msg",
        )
        db_session.add(notif)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_type_invalid(self, db_session, tenant, user):
        """Invalid type must be rejected."""
        notif = _make_notification(tenant, user, type="email")
        db_session.add(notif)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_type_deadline(self, db_session, tenant, user):
        notif = _make_notification(tenant, user, type="deadline")
        db_session.add(notif)
        db_session.flush()
        assert notif.type == "deadline"

    def test_check_type_anomaly(self, db_session, tenant, user):
        notif = _make_notification(tenant, user, type="anomaly")
        db_session.add(notif)
        db_session.flush()
        assert notif.type == "anomaly"

    def test_check_type_system(self, db_session, tenant, user):
        notif = _make_notification(tenant, user, type="system")
        db_session.add(notif)
        db_session.flush()
        assert notif.type == "system"

    def test_check_type_approval(self, db_session, tenant, user):
        notif = _make_notification(tenant, user, type="approval")
        db_session.add(notif)
        db_session.flush()
        assert notif.type == "approval"

    def test_check_severity_invalid(self, db_session, tenant, user):
        """Invalid severity must be rejected."""
        notif = _make_notification(tenant, user, severity="low")
        db_session.add(notif)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_severity_info(self, db_session, tenant, user):
        notif = _make_notification(tenant, user, severity="info")
        db_session.add(notif)
        db_session.flush()
        assert notif.severity == "info"

    def test_check_severity_warning(self, db_session, tenant, user):
        notif = _make_notification(tenant, user, severity="warning")
        db_session.add(notif)
        db_session.flush()
        assert notif.severity == "warning"

    def test_check_severity_critical(self, db_session, tenant, user):
        notif = _make_notification(tenant, user, severity="critical")
        db_session.add(notif)
        db_session.flush()
        assert notif.severity == "critical"

    def test_not_null_type(self, db_session, tenant, user):
        """type cannot be NULL."""
        notif = _make_notification(tenant, user, type=None)
        db_session.add(notif)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_title(self, db_session, tenant, user):
        """title cannot be NULL."""
        notif = _make_notification(tenant, user, title=None)
        db_session.add(notif)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_message(self, db_session, tenant, user):
        """message cannot be NULL."""
        notif = _make_notification(tenant, user, message=None)
        db_session.add(notif)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_tenant_restrict_delete(self, db_session, tenant, user):
        """Deleting a tenant with notifications must be rejected.

        Uses raw SQL per FK RESTRICT Test Pattern — ORM session.delete()
        sets FK to NULL first (NOT NULL failure before FK check).
        """
        notif = _make_notification(tenant, user)
        db_session.add(notif)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM public.tenants WHERE id = :id"),
                {"id": str(tenant.id)},
            )
        db_session.rollback()

    def test_fk_user_restrict_delete(self, db_session, tenant, user):
        """Deleting a user with notifications must be rejected (RESTRICT).

        Uses raw SQL per FK RESTRICT Test Pattern — ORM session.delete()
        sets FK to NULL first (NOT NULL failure before FK check).
        """
        notif = _make_notification(tenant, user)
        db_session.add(notif)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM users WHERE id = :id"),
                {"id": str(user.id)},
            )
        db_session.rollback()


# ===================================================================
# Database integration tests
# ===================================================================


class TestNotificationDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session, tenant, user):
        """Full create with all fields — verify round-trip."""
        related_id = uuid.uuid4()
        notif = _make_notification(
            tenant,
            user,
            type="anomaly",
            severity="critical",
            title="Payroll anomaly detected",
            message="Employee XY wage deviation exceeds 20%.",
            related_entity="payroll",
            related_entity_id=related_id,
        )
        db_session.add(notif)
        db_session.flush()

        assert notif.id is not None
        assert notif.created_at is not None
        assert notif.updated_at is not None
        assert notif.tenant_id == tenant.id
        assert notif.user_id == user.id
        assert notif.type == "anomaly"
        assert notif.severity == "critical"
        assert notif.title == "Payroll anomaly detected"
        assert notif.message == "Employee XY wage deviation exceeds 20%."
        assert notif.related_entity == "payroll"
        assert notif.related_entity_id == related_id
        assert notif.is_read is False
        assert notif.read_at is None

    def test_create_minimal_defaults(self, db_session, tenant, user):
        """Create with only required fields — verify all server_defaults."""
        notif = _make_notification(tenant, user)
        db_session.add(notif)
        db_session.flush()

        # server_defaults
        assert notif.severity == "info"
        assert notif.is_read is False
        # nullable fields
        assert notif.related_entity is None
        assert notif.related_entity_id is None
        assert notif.read_at is None

    def test_mark_as_read(self, db_session, tenant, user):
        """Notification can be marked as read."""
        notif = _make_notification(tenant, user)
        db_session.add(notif)
        db_session.flush()
        assert notif.is_read is False

        notif.is_read = True
        db_session.flush()
        assert notif.is_read is True

    def test_multiple_notifications_same_user(self, db_session, tenant, user):
        """Multiple notifications for the same user are allowed."""
        notif1 = _make_notification(tenant, user, title="First")
        notif2 = _make_notification(tenant, user, title="Second")
        db_session.add_all([notif1, notif2])
        db_session.flush()
        assert notif1.id != notif2.id

    def test_message_text_field(self, db_session, tenant, user):
        """message field accepts long text."""
        long_msg = "A" * 2000
        notif = _make_notification(tenant, user, message=long_msg)
        db_session.add(notif)
        db_session.flush()
        assert notif.message == long_msg

    def test_related_entity_optional(self, db_session, tenant, user):
        """related_entity and related_entity_id can be NULL."""
        notif = _make_notification(
            tenant,
            user,
            related_entity=None,
            related_entity_id=None,
        )
        db_session.add(notif)
        db_session.flush()
        assert notif.related_entity is None
        assert notif.related_entity_id is None

    def test_related_entity_with_value(self, db_session, tenant, user):
        """related_entity and related_entity_id can be set."""
        entity_id = uuid.uuid4()
        notif = _make_notification(
            tenant,
            user,
            related_entity="leave",
            related_entity_id=entity_id,
        )
        db_session.add(notif)
        db_session.flush()
        assert notif.related_entity == "leave"
        assert notif.related_entity_id == entity_id
