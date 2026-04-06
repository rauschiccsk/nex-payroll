"""Tests for User Pydantic schemas."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.user import (
    UserCreate,
    UserRead,
    UserUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = uuid4()
_EMPLOYEE_ID = uuid4()


def _valid_create_kwargs() -> dict:
    """Return a dict with all required fields for UserCreate."""
    return {
        "tenant_id": _TENANT_ID,
        "username": "jnovak",
        "email": "jan.novak@example.com",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fakehashfortest",
        "role": "accountant",
    }


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
        assert schema.password_hash == "$argon2id$v=19$m=65536,t=3,p=4$fakehashfortest"
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

    # -- required field validation --

    def test_missing_required_tenant_id(self):
        kw = _valid_create_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "tenant_id" in str(exc_info.value)

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

    def test_missing_required_password_hash(self):
        kw = _valid_create_kwargs()
        del kw["password_hash"]
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**kw)
        assert "password_hash" in str(exc_info.value)

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

    def test_email_at_max_length(self):
        kw = _valid_create_kwargs()
        kw["email"] = "x" * 255
        schema = UserCreate(**kw)
        assert len(schema.email) == 255

    def test_password_hash_max_length(self):
        kw = _valid_create_kwargs()
        kw["password_hash"] = "x" * 256
        with pytest.raises(ValidationError):
            UserCreate(**kw)

    def test_password_hash_at_max_length(self):
        kw = _valid_create_kwargs()
        kw["password_hash"] = "x" * 255
        schema = UserCreate(**kw)
        assert len(schema.password_hash) == 255

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
        assert schema.password_hash is None
        assert schema.role is None
        assert schema.is_active is None
        assert schema.last_login_at is None
        assert schema.password_changed_at is None

    def test_partial_update(self):
        schema = UserUpdate(
            username="pnovak",
            email="peter.novak@example.com",
            role="director",
        )
        assert schema.username == "pnovak"
        assert schema.email == "peter.novak@example.com"
        assert schema.role == "director"
        assert schema.password_hash is None
        assert schema.is_active is None

    # -- max_length validation in update --

    def test_update_username_max_length(self):
        with pytest.raises(ValidationError):
            UserUpdate(username="x" * 101)

    def test_update_email_max_length(self):
        with pytest.raises(ValidationError):
            UserUpdate(email="x" * 256)

    def test_update_password_hash_max_length(self):
        with pytest.raises(ValidationError):
            UserUpdate(password_hash="x" * 256)

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

    # -- datetime fields --

    def test_update_last_login_at(self):
        now = datetime(2025, 6, 1, 12, 0, 0)
        schema = UserUpdate(last_login_at=now)
        assert schema.last_login_at == now

    def test_update_password_changed_at(self):
        now = datetime(2025, 6, 1, 12, 0, 0)
        schema = UserUpdate(password_changed_at=now)
        assert schema.password_changed_at == now


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

    def test_password_hash_excluded(self):
        """Verify that password_hash is NOT part of UserRead schema."""
        kw = self._read_kwargs()
        schema = UserRead(**kw)
        dumped = schema.model_dump()
        assert "password_hash" not in dumped

        # Also verify that passing password_hash is ignored (extra='ignore' default)
        kw["password_hash"] = "$argon2id$v=19$m=65536,t=3,p=4$fakehash"
        schema2 = UserRead(**kw)
        assert not hasattr(schema2, "password_hash") or "password_hash" not in schema2.model_fields

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
