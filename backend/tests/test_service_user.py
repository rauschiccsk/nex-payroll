"""Tests for User service layer."""

from uuid import uuid4

import pytest

from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.user import (
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tenant(db_session, **overrides) -> Tenant:
    """Insert a minimal Tenant and flush; return the instance."""
    defaults = {
        "name": "Test s.r.o.",
        "ico": "12345678",
        "address_street": "Hlavná 1",
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


def _make_payload(tenant_id, **overrides) -> UserCreate:
    """Build a valid UserCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "username": "jnovak",
        "email": "jan.novak@example.com",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fakehashvalue",
        "role": "accountant",
        "is_active": True,
    }
    defaults.update(overrides)
    return UserCreate(**defaults)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateUser:
    """Tests for create_user."""

    def test_create_returns_model_instance(self, db_session):
        tenant = _make_tenant(db_session)
        payload = _make_payload(tenant.id)

        result = create_user(db_session, payload)

        assert isinstance(result, User)
        assert result.id is not None
        assert result.tenant_id == tenant.id
        assert result.username == "jnovak"
        assert result.email == "jan.novak@example.com"
        assert result.role == "accountant"
        assert result.is_active is True
        assert result.employee_id is None

    def test_create_with_employee_role_and_id(self, db_session):
        """role='employee' with employee_id should succeed."""
        from datetime import date

        from app.models.employee import Employee
        from app.models.health_insurer import HealthInsurer

        tenant = _make_tenant(db_session)

        insurer = HealthInsurer(code="25", name="VšZP", iban="SK0000000000000000000025")
        db_session.add(insurer)
        db_session.flush()

        employee = Employee(
            tenant_id=tenant.id,
            employee_number="EMP001",
            first_name="Ján",
            last_name="Novák",
            birth_date=date(1990, 5, 15),
            birth_number="9005150001",
            gender="M",
            nationality="SK",
            address_street="Hlavná 1",
            address_city="Bratislava",
            address_zip="81101",
            address_country="SK",
            bank_iban="SK8975000000000012345678",
            health_insurer_id=insurer.id,
            tax_declaration_type="standard",
            hire_date=date(2024, 1, 15),
        )
        db_session.add(employee)
        db_session.flush()

        payload = _make_payload(
            tenant.id,
            username="emp_user",
            email="emp@example.com",
            role="employee",
            employee_id=employee.id,
        )

        result = create_user(db_session, payload)

        assert result.role == "employee"
        assert result.employee_id == employee.id

    def test_create_director_without_employee_id(self, db_session):
        """role='director' without employee_id should succeed."""
        tenant = _make_tenant(db_session)
        payload = _make_payload(
            tenant.id,
            username="director1",
            email="director@example.com",
            role="director",
        )

        result = create_user(db_session, payload)

        assert result.role == "director"
        assert result.employee_id is None

    def test_create_duplicate_username_raises(self, db_session):
        tenant = _make_tenant(db_session)

        create_user(db_session, _make_payload(tenant.id, username="dup_user"))

        with pytest.raises(ValueError, match="username='dup_user' already exists"):
            create_user(
                db_session,
                _make_payload(
                    tenant.id,
                    username="dup_user",
                    email="other@example.com",
                ),
            )

    def test_create_duplicate_email_raises(self, db_session):
        tenant = _make_tenant(db_session)

        create_user(db_session, _make_payload(tenant.id, email="dup@example.com"))

        with pytest.raises(ValueError, match="email='dup@example.com' already exists"):
            create_user(
                db_session,
                _make_payload(
                    tenant.id,
                    username="other_user",
                    email="dup@example.com",
                ),
            )

    def test_create_same_username_different_tenant_ok(self, db_session):
        """Same username in different tenants is allowed."""
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")

        user_a = create_user(db_session, _make_payload(tenant_a.id, username="jnovak"))
        user_b = create_user(
            db_session,
            _make_payload(tenant_b.id, username="jnovak", email="jnovak2@example.com"),
        )

        assert user_a.id != user_b.id
        assert user_a.username == user_b.username

    def test_create_same_email_different_tenant_ok(self, db_session):
        """Same email in different tenants is allowed."""
        tenant_a = _make_tenant(db_session, ico="33333333", schema_name="tenant_c_33333333")
        tenant_b = _make_tenant(db_session, ico="44444444", schema_name="tenant_d_44444444")

        user_a = create_user(
            db_session,
            _make_payload(tenant_a.id, email="shared@example.com"),
        )
        user_b = create_user(
            db_session,
            _make_payload(
                tenant_b.id,
                username="other_user",
                email="shared@example.com",
            ),
        )

        assert user_a.id != user_b.id
        assert user_a.email == user_b.email


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetUser:
    """Tests for get_user."""

    def test_get_existing(self, db_session):
        tenant = _make_tenant(db_session)
        created = create_user(db_session, _make_payload(tenant.id))

        fetched = get_user(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.username == created.username

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_user(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListUsers:
    """Tests for list_users."""

    def test_list_empty(self, db_session):
        result = list_users(db_session)
        assert result == []

    def test_list_returns_all_active(self, db_session):
        tenant = _make_tenant(db_session)

        create_user(
            db_session,
            _make_payload(tenant.id, username="user1", email="u1@example.com"),
        )
        create_user(
            db_session,
            _make_payload(tenant.id, username="user2", email="u2@example.com"),
        )

        result = list_users(db_session)
        assert len(result) == 2

    def test_list_ordering_by_username(self, db_session):
        """Users are ordered by username ascending."""
        tenant = _make_tenant(db_session)

        create_user(
            db_session,
            _make_payload(tenant.id, username="zorro", email="z@example.com"),
        )
        create_user(
            db_session,
            _make_payload(tenant.id, username="adam", email="a@example.com"),
        )

        result = list_users(db_session)
        assert result[0].username == "adam"
        assert result[1].username == "zorro"

    def test_list_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")

        create_user(
            db_session,
            _make_payload(tenant_a.id, username="user_a", email="a@example.com"),
        )
        create_user(
            db_session,
            _make_payload(tenant_b.id, username="user_b", email="b@example.com"),
        )

        result = list_users(db_session, tenant_id=tenant_a.id)
        assert len(result) == 1
        assert result[0].tenant_id == tenant_a.id

    def test_list_filtered_by_role(self, db_session):
        tenant = _make_tenant(db_session)

        create_user(
            db_session,
            _make_payload(
                tenant.id,
                username="acc1",
                email="acc@example.com",
                role="accountant",
            ),
        )
        create_user(
            db_session,
            _make_payload(
                tenant.id,
                username="dir1",
                email="dir@example.com",
                role="director",
            ),
        )

        result = list_users(db_session, role="accountant")
        assert len(result) == 1
        assert result[0].role == "accountant"

    def test_list_excludes_inactive_by_default(self, db_session):
        tenant = _make_tenant(db_session)

        create_user(
            db_session,
            _make_payload(
                tenant.id,
                username="active_user",
                email="active@example.com",
                is_active=True,
            ),
        )
        create_user(
            db_session,
            _make_payload(
                tenant.id,
                username="inactive_user",
                email="inactive@example.com",
                is_active=False,
            ),
        )

        result = list_users(db_session)
        assert len(result) == 1
        assert result[0].username == "active_user"

    def test_list_include_inactive(self, db_session):
        tenant = _make_tenant(db_session)

        create_user(
            db_session,
            _make_payload(
                tenant.id,
                username="active_user",
                email="active@example.com",
                is_active=True,
            ),
        )
        create_user(
            db_session,
            _make_payload(
                tenant.id,
                username="inactive_user",
                email="inactive@example.com",
                is_active=False,
            ),
        )

        result = list_users(db_session, include_inactive=True)
        assert len(result) == 2

    def test_list_pagination_skip(self, db_session):
        tenant = _make_tenant(db_session)

        for i in range(3):
            create_user(
                db_session,
                _make_payload(
                    tenant.id,
                    username=f"user{i:03d}",
                    email=f"u{i}@example.com",
                ),
            )

        result = list_users(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        tenant = _make_tenant(db_session)

        for i in range(3):
            create_user(
                db_session,
                _make_payload(
                    tenant.id,
                    username=f"user{i:03d}",
                    email=f"u{i}@example.com",
                ),
            )

        result = list_users(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        tenant = _make_tenant(db_session)

        for i in range(5):
            create_user(
                db_session,
                _make_payload(
                    tenant.id,
                    username=f"user{i:03d}",
                    email=f"u{i}@example.com",
                ),
            )

        result = list_users(db_session, skip=1, limit=2)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateUser:
    """Tests for update_user."""

    def test_update_single_field(self, db_session):
        tenant = _make_tenant(db_session)
        created = create_user(db_session, _make_payload(tenant.id))

        updated = update_user(
            db_session,
            created.id,
            UserUpdate(username="peter_novak"),
        )

        assert updated is not None
        assert updated.username == "peter_novak"
        # unchanged fields stay the same
        assert updated.email == "jan.novak@example.com"

    def test_update_multiple_fields(self, db_session):
        tenant = _make_tenant(db_session)
        created = create_user(db_session, _make_payload(tenant.id))

        updated = update_user(
            db_session,
            created.id,
            UserUpdate(
                email="new@example.com",
                role="director",
            ),
        )

        assert updated is not None
        assert updated.email == "new@example.com"
        assert updated.role == "director"

    def test_update_nonexistent_returns_none(self, db_session):
        result = update_user(
            db_session,
            uuid4(),
            UserUpdate(username="ghost"),
        )
        assert result is None

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        tenant = _make_tenant(db_session)
        created = create_user(db_session, _make_payload(tenant.id))

        updated = update_user(
            db_session,
            created.id,
            UserUpdate(),
        )

        assert updated is not None
        assert updated.username == created.username

    def test_update_username_duplicate_raises(self, db_session):
        tenant = _make_tenant(db_session)

        create_user(
            db_session,
            _make_payload(tenant.id, username="user1", email="u1@example.com"),
        )
        second = create_user(
            db_session,
            _make_payload(tenant.id, username="user2", email="u2@example.com"),
        )

        with pytest.raises(ValueError, match="username='user1' already exists"):
            update_user(
                db_session,
                second.id,
                UserUpdate(username="user1"),
            )

    def test_update_email_duplicate_raises(self, db_session):
        tenant = _make_tenant(db_session)

        create_user(
            db_session,
            _make_payload(tenant.id, username="user1", email="u1@example.com"),
        )
        second = create_user(
            db_session,
            _make_payload(tenant.id, username="user2", email="u2@example.com"),
        )

        with pytest.raises(ValueError, match="email='u1@example.com' already exists"):
            update_user(
                db_session,
                second.id,
                UserUpdate(email="u1@example.com"),
            )

    def test_update_username_same_value_no_error(self, db_session):
        """Updating username to the same value should NOT raise."""
        tenant = _make_tenant(db_session)
        created = create_user(
            db_session,
            _make_payload(tenant.id, username="keeper"),
        )

        updated = update_user(
            db_session,
            created.id,
            UserUpdate(username="keeper"),
        )

        assert updated is not None
        assert updated.username == "keeper"

    def test_update_email_same_value_no_error(self, db_session):
        """Updating email to the same value should NOT raise."""
        tenant = _make_tenant(db_session)
        created = create_user(
            db_session,
            _make_payload(tenant.id, email="same@example.com"),
        )

        updated = update_user(
            db_session,
            created.id,
            UserUpdate(email="same@example.com"),
        )

        assert updated is not None
        assert updated.email == "same@example.com"

    def test_update_is_active_flag(self, db_session):
        """Soft-deactivate a user via update."""
        tenant = _make_tenant(db_session)
        created = create_user(db_session, _make_payload(tenant.id))

        updated = update_user(
            db_session,
            created.id,
            UserUpdate(is_active=False),
        )

        assert updated is not None
        assert updated.is_active is False


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteUser:
    """Tests for delete_user."""

    def test_delete_existing(self, db_session):
        """Soft-delete sets is_active=False; user still retrievable by ID."""
        tenant = _make_tenant(db_session)
        created = create_user(db_session, _make_payload(tenant.id))

        deleted = delete_user(db_session, created.id)

        assert deleted is True
        # Soft-delete: user still exists but is_active=False
        user = get_user(db_session, created.id)
        assert user is not None
        assert user.is_active is False

    def test_delete_nonexistent_returns_false(self, db_session):
        result = delete_user(db_session, uuid4())
        assert result is False
