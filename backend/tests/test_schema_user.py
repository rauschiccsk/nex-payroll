"""Tests for User Pydantic schemas."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.user import (
    UserBase,
    UserCreate,
    UserInDB,
    UserPublic,
    UserRead,
    UserUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = uuid4()
_EMPLOYEE_ID = uuid4()

# A password that satisfies complexity: uppercase, lowercase, digit, special, 12+ chars
_VALID_PASSWORD = "StrongPass1!xy"


def _valid_create_kwargs() -> dict:
    """Return a dict with all required fields for UserCreate."""
    return {
        "tenant_id": _TENANT_ID,
        "username": "jnovak",
        "email": "jan.novak@example.com",
        "password": _VALID_PASSWORD,
        "role": "accountant",
    }


# ---------------------------------------------------------------------------
# UserBase
# ---------------------------------------------------------------------------


class TestUserBase:
    """Tests for the UserBase schema."""

    def test_valid(self):
        schema = UserBase(
            username="jnovak",
            email="jan.novak@example.com",
            role="accountant",
        )
        assert schema.username == "jnovak"
        assert schema.email == "jan.novak@example.com"
        assert schema.role == "accountant"
        assert schema.is_active is True

    def test_email_format_validation(self):
        with pytest.raises(ValidationError) as exc_info:
            UserBase(
                username="jnovak",
                email="not-an-email",
                role="accountant",
            )
        assert "email" in str(exc_info.value).lower()

    def test_email_normalized_to_lowercase(self):
        schema = UserBase(
            username="jnovak",
            email="Jan.Novak@Example.COM",
            role="accountant",
        )
        assert schema.email == "jan.novak@example.com"

    def test_username_stripped(self):
        schema = UserBase(
            username="  jnovak  ",
            email="jan.novak@example.com",
            role="accountant",
        )
        assert schema.username == "jnovak"

    def test_blank_username_rejected(self):
        with pytest.raises(ValidationError):
            UserBase(
                username="   ",
                email="jan.novak@example.com",
                role="accountant",
            )

    def test_invalid_role_superadmin(self):
        with pytest.raises(ValidationError):
            UserBase(
                username="admin",
                email="admin@example.com",
                role="superadmin",
            )


# ---------------------------------------------------------------------------
# UserCreate
# ---------------------------------------------------------------------------


class TestUserCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        schema = UserCreate(**_valid_create_kwargs())
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id is None
        assert schema.username == "jnovak"
        assert schema.email == "jan.novak@example.com"
        assert schema.password == _VALID_PASSWORD
        assert schema.role == "accountant"
        assert schema.is_active is True

    def test_valid_full(self):
        schema = UserCreate(
            **_valid_create_kwargs(),
            employee_id=_EMPLOYEE_ID,
            is_active=False,
        )
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.is_active is False

    # -- tenant_id is required --

    def test_tenant_id_required(self):
        kw = _valid_create_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "tenant_id" in str(exc_info.value)

    # -- required field validation --

    def test_missing_required_username(self):
        kw = _valid_create_kwargs()
        del kw["username"]
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "username" in str(exc_info.value)

    def test_missing_required_email(self):
        kw = _valid_create_kwargs()
        del kw["email"]
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "email" in str(exc_info.value)

    def test_missing_required_password(self):
        kw = _valid_create_kwargs()
        del kw["password"]
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "password" in str(exc_info.value)

    def test_missing_required_role(self):
        kw = _valid_create_kwargs()
        del kw["role"]
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "role" in str(exc_info.value)

    # -- max_length validation --

    def test_username_max_length(self):
        kw = _valid_create_kwargs()
        kw["username"] = "x" * 101
        with pytest.raises(ValidationError):
            UserCreate(**kw)

    def test_username_at_max_length(self):
        kw = _valid_create_kwargs()
        kw["username"] = "x" * 100
        schema = UserCreate(**kw)
        assert len(schema.username) == 100

    def test_email_max_length(self):
        kw = _valid_create_kwargs()
        kw["email"] = "x" * 256
        with pytest.raises(ValidationError):
            UserCreate(**kw)

    def test_password_max_length(self):
        kw = _valid_create_kwargs()
        kw["password"] = "x" * 256
        with pytest.raises(ValidationError):
            UserCreate(**kw)

    # -- password complexity validation --

    def test_password_too_short(self):
        kw = _valid_create_kwargs()
        kw["password"] = "Abc1!short"  # < 12 chars
        with pytest.raises(ValidationError):
            UserCreate(**kw)

    def test_password_no_uppercase(self):
        kw = _valid_create_kwargs()
        kw["password"] = "strongpass1!xy"
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "uppercase" in str(exc_info.value)

    def test_password_no_lowercase(self):
        kw = _valid_create_kwargs()
        kw["password"] = "STRONGPASS1!XY"
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "lowercase" in str(exc_info.value)

    def test_password_no_digit(self):
        kw = _valid_create_kwargs()
        kw["password"] = "StrongPass!!xy"
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "digit" in str(exc_info.value)

    def test_password_no_special(self):
        kw = _valid_create_kwargs()
        kw["password"] = "StrongPass1xyz"
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "special" in str(exc_info.value)

    # -- email format validation --

    def test_invalid_email_format(self):
        kw = _valid_create_kwargs()
        kw["email"] = "not-an-email"
        with pytest.raises(ValidationError):
            UserCreate(**kw)

    def test_valid_email_format(self):
        kw = _valid_create_kwargs()
        kw["email"] = "user@domain.co.uk"
        schema = UserCreate(**kw)
        assert schema.email == "user@domain.co.uk"

    # -- role validation --

    def test_invalid_role(self):
        kw = _valid_create_kwargs()
        kw["role"] = "admin"
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "role" in str(exc_info.value)

    def test_invalid_role_superuser(self):
        kw = _valid_create_kwargs()
        kw["role"] = "superuser"
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "role" in str(exc_info.value)

    def test_role_director(self):
        kw = _valid_create_kwargs()
        kw["role"] = "director"
        schema = UserCreate(**kw)
        assert schema.role == "director"

    def test_role_accountant(self):
        kw = _valid_create_kwargs()
        kw["role"] = "accountant"
        schema = UserCreate(**kw)
        assert schema.role == "accountant"

    def test_role_employee(self):
        kw = _valid_create_kwargs()
        kw["role"] = "employee"
        kw["employee_id"] = _EMPLOYEE_ID
        schema = UserCreate(**kw)
        assert schema.role == "employee"
        assert schema.employee_id == _EMPLOYEE_ID

    def test_role_superadmin_rejected(self):
        kw = _valid_create_kwargs()
        kw["role"] = "superadmin"
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "role" in str(exc_info.value)

    # -- business rule: role='employee' requires employee_id --

    def test_employee_role_without_employee_id_raises(self):
        kw = _valid_create_kwargs()
        kw["role"] = "employee"
        # employee_id defaults to None
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "employee_id is required when role is 'employee'" in str(exc_info.value)

    def test_employee_role_with_employee_id_ok(self):
        kw = _valid_create_kwargs()
        kw["role"] = "employee"
        kw["employee_id"] = _EMPLOYEE_ID
        schema = UserCreate(**kw)
        assert schema.role == "employee"
        assert schema.employee_id == _EMPLOYEE_ID

    def test_director_without_employee_id_ok(self):
        kw = _valid_create_kwargs()
        kw["role"] = "director"
        schema = UserCreate(**kw)
        assert schema.role == "director"
        assert schema.employee_id is None

    def test_accountant_without_employee_id_ok(self):
        kw = _valid_create_kwargs()
        kw["role"] = "accountant"
        schema = UserCreate(**kw)
        assert schema.role == "accountant"
        assert schema.employee_id is None

    def test_director_with_employee_id_ok(self):
        kw = _valid_create_kwargs()
        kw["role"] = "director"
        kw["employee_id"] = _EMPLOYEE_ID
        schema = UserCreate(**kw)
        assert schema.role == "director"
        assert schema.employee_id == _EMPLOYEE_ID


# ---------------------------------------------------------------------------
# UserUpdate
# ---------------------------------------------------------------------------


class TestUserUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        schema = UserUpdate()
        assert schema.employee_id is None
        assert schema.username is None
        assert schema.email is None
        assert schema.password is None
        assert schema.role is None
        assert schema.is_active is None

    def test_partial_update(self):
        schema = UserUpdate(
            username="pnovak",
            email="peter.novak@example.com",
            role="director",
        )
        assert schema.username == "pnovak"
        assert schema.email == "peter.novak@example.com"
        assert schema.role == "director"
        assert schema.password is None
        assert schema.is_active is None

    # -- max_length validation in update --

    def test_update_username_max_length(self):
        with pytest.raises(ValidationError):
            UserUpdate(username="x" * 101)

    def test_update_email_max_length(self):
        with pytest.raises(ValidationError):
            UserUpdate(email="x" * 256)

    def test_update_password_max_length(self):
        with pytest.raises(ValidationError):
            UserUpdate(password="x" * 256)

    # -- password complexity in update --

    def test_update_password_complexity(self):
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(password="weakpassword1")
        assert "uppercase" in str(exc_info.value)

    def test_update_valid_password(self):
        schema = UserUpdate(password=_VALID_PASSWORD)
        assert schema.password == _VALID_PASSWORD

    # -- email format in update --

    def test_update_invalid_email(self):
        with pytest.raises(ValidationError):
            UserUpdate(email="not-an-email")

    def test_update_valid_email(self):
        schema = UserUpdate(email="valid@example.com")
        assert schema.email == "valid@example.com"

    # -- role validation in update --

    def test_update_invalid_role(self):
        with pytest.raises(ValidationError):
            UserUpdate(role="admin")

    def test_update_valid_role_director(self):
        schema = UserUpdate(role="director")
        assert schema.role == "director"

    def test_update_valid_role_accountant(self):
        schema = UserUpdate(role="accountant")
        assert schema.role == "accountant"

    def test_update_valid_role_employee(self):
        schema = UserUpdate(role="employee")
        assert schema.role == "employee"

    def test_update_invalid_role_superadmin(self):
        with pytest.raises(ValidationError):
            UserUpdate(role="superadmin")

    # -- readonly datetime fields are NOT in UserUpdate --

    def test_last_login_at_not_in_update(self):
        """last_login_at is system-managed and must not be in UserUpdate fields."""
        assert "last_login_at" not in UserUpdate.model_fields

    def test_password_changed_at_not_in_update(self):
        """password_changed_at is system-managed and must not be in UserUpdate fields."""
        assert "password_changed_at" not in UserUpdate.model_fields


# ---------------------------------------------------------------------------
# UserRead
# ---------------------------------------------------------------------------


class TestUserRead:
    """Tests for the Read schema — from_attributes=True."""

    def _read_kwargs(self) -> dict:
        """Return a complete dict for constructing UserRead."""
        now = datetime(2025, 6, 1, 12, 0, 0)
        return {
            "id": uuid4(),
            "tenant_id": _TENANT_ID,
            "employee_id": _EMPLOYEE_ID,
            "username": "jnovak",
            "email": "jan.novak@example.com",
            "role": "accountant",
            "is_active": True,
            "last_login_at": now,
            "password_changed_at": None,
            "created_at": now,
            "updated_at": now,
        }

    def test_from_dict(self):
        kw = self._read_kwargs()
        schema = UserRead(**kw)
        assert schema.id == kw["id"]
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.username == "jnovak"
        assert schema.email == "jan.novak@example.com"
        assert schema.role == "accountant"
        assert schema.is_active is True
        assert schema.last_login_at == datetime(2025, 6, 1, 12, 0, 0)
        assert schema.password_changed_at is None
        assert schema.created_at == datetime(2025, 6, 1, 12, 0, 0)
        assert schema.updated_at == datetime(2025, 6, 1, 12, 0, 0)

    def test_password_excluded(self):
        """Verify that password is NOT part of UserRead schema."""
        kw = self._read_kwargs()
        schema = UserRead(**kw)
        dumped = schema.model_dump()
        assert "password" not in dumped

        # Also verify that passing password is ignored (extra='ignore' default)
        kw["password"] = _VALID_PASSWORD
        schema2 = UserRead(**kw)
        assert not hasattr(schema2, "password") or "password" not in schema2.model_fields

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.tenant_id = _TENANT_ID
                self.employee_id = _EMPLOYEE_ID
                self.username = "jnovak"
                self.email = "jan.novak@example.com"
                self.role = "accountant"
                self.is_active = True
                self.last_login_at = None
                self.password_changed_at = None
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)
                self.updated_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = UserRead.model_validate(orm_obj)
        assert schema.username == "jnovak"
        assert schema.email == "jan.novak@example.com"
        assert schema.role == "accountant"
        assert schema.is_active is True

    def test_serialisation_roundtrip(self):
        kw = self._read_kwargs()
        schema = UserRead(**kw)
        dumped = schema.model_dump()
        assert dumped["id"] == kw["id"]
        assert dumped["username"] == "jnovak"
        assert dumped["email"] == "jan.novak@example.com"
        assert dumped["role"] == "accountant"
        assert dumped["is_active"] is True
        assert dumped["password_changed_at"] is None

    def test_read_role_validation(self):
        """UserRead should reject invalid role values."""
        kw = self._read_kwargs()
        kw["role"] = "admin"
        with pytest.raises(ValidationError) as exc_info:
            UserRead(**kw)
        assert "role" in str(exc_info.value)

    def test_read_all_valid_roles(self):
        """UserRead should accept all valid role values."""
        for role in ("director", "accountant", "employee"):
            kw = self._read_kwargs()
            kw["role"] = role
            schema = UserRead(**kw)
            assert schema.role == role


# ---------------------------------------------------------------------------
# UserInDB
# ---------------------------------------------------------------------------


class TestUserInDB:
    """Tests for the InDB schema — includes password_hash."""

    def _indb_kwargs(self) -> dict:
        now = datetime(2025, 6, 1, 12, 0, 0)
        return {
            "id": uuid4(),
            "tenant_id": _TENANT_ID,
            "employee_id": _EMPLOYEE_ID,
            "username": "jnovak",
            "email": "jan.novak@example.com",
            "role": "accountant",
            "is_active": True,
            "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fakehash",
            "last_login_at": now,
            "password_changed_at": None,
            "created_at": now,
            "updated_at": now,
        }

    def test_valid(self):
        kw = self._indb_kwargs()
        schema = UserInDB(**kw)
        assert schema.id == kw["id"]
        assert schema.password_hash == "$argon2id$v=19$m=65536,t=3,p=4$fakehash"
        assert schema.tenant_id == _TENANT_ID

    def test_from_attributes(self):
        """UserInDB has from_attributes=True."""
        assert UserInDB.model_config.get("from_attributes") is True

    def test_tenant_id_required(self):
        kw = self._indb_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            UserInDB(**kw)
        assert "tenant_id" in str(exc_info.value)


# ---------------------------------------------------------------------------
# UserPublic
# ---------------------------------------------------------------------------


class TestUserPublic:
    """Tests for the Public schema — safe subset."""

    def test_valid(self):
        schema = UserPublic(
            id=uuid4(),
            username="jnovak",
            email="jan.novak@example.com",
            role="accountant",
            is_active=True,
            tenant_id=_TENANT_ID,
            last_login_at=datetime(2025, 6, 1, 12, 0, 0),
        )
        assert schema.username == "jnovak"
        assert schema.tenant_id == _TENANT_ID

    def test_no_password_hash_field(self):
        """UserPublic must NOT have password_hash."""
        assert "password_hash" not in UserPublic.model_fields

    def test_no_timestamps(self):
        """UserPublic must NOT expose created_at/updated_at."""
        assert "created_at" not in UserPublic.model_fields
        assert "updated_at" not in UserPublic.model_fields

    def test_from_attributes(self):
        """UserPublic has from_attributes=True."""
        assert UserPublic.model_config.get("from_attributes") is True

    def test_tenant_id_required(self):
        with pytest.raises(ValidationError) as exc_info:
            UserPublic(
                id=uuid4(),
                username="admin",
                email="admin@example.com",
                role="director",
                is_active=True,
            )
        assert "tenant_id" in str(exc_info.value)
