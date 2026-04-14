"""Tests for migration 024 — seed initial data (demo tenant + superadmin).

Verifies that upgrade() and downgrade() call op.execute() with expected
SQL and parameters by mocking alembic.op and inspecting the calls.
"""

import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

from pwdlib import PasswordHash

# Migration file starts with a digit — import via importlib
_migration_path = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "024_seed_initial_data.py"
_spec = importlib.util.spec_from_file_location("m024", _migration_path)
m024 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m024)

# Fixed UUIDs from the migration
DEMO_TENANT_ID = m024.DEMO_TENANT_ID
SUPERADMIN_USER_ID = m024.SUPERADMIN_USER_ID


class TestMigration024Constants:
    """Test that migration 024 defines expected constants."""

    def test_revision_identifiers(self):
        assert m024.revision == "024"
        assert m024.down_revision == "023"

    def test_fixed_uuids_are_valid(self):
        import uuid

        uuid.UUID(DEMO_TENANT_ID)
        uuid.UUID(SUPERADMIN_USER_ID)

    def test_uuids_are_distinct(self):
        assert DEMO_TENANT_ID != SUPERADMIN_USER_ID


class TestMigration024Upgrade:
    """Test upgrade logic by calling m024.upgrade() with mocked op.execute."""

    def test_upgrade_calls_op_execute_twice(self):
        """upgrade() must call op.execute exactly twice (tenant + user)."""
        with patch.object(m024, "op") as mock_op:
            m024.upgrade()
            assert mock_op.execute.call_count == 2

    def test_upgrade_inserts_demo_tenant(self):
        """Verify first op.execute call contains tenant INSERT with correct params."""
        with patch.object(m024, "op") as mock_op:
            m024.upgrade()

            first_call = mock_op.execute.call_args_list[0]
            sql_obj = first_call[0][0]
            # The text object's string contains the SQL
            sql_str = str(sql_obj)

            assert "INSERT INTO public.tenants" in sql_str
            assert "ICC Demo s.r.o." in sql_str or ":name" in sql_str
            # Verify bindparams contain expected values
            compiled = sql_obj.compile()
            params = compiled.params
            assert params["id"] == DEMO_TENANT_ID
            assert params["name"] == "ICC Demo s.r.o."
            assert params["ico"] == "12345678"
            assert params["schema_name"] == "tenant_demo"
            assert params["address_street"] == "Testovacia 1"
            assert params["address_city"] == "Bratislava"
            assert params["address_zip"] == "81101"
            assert params["bank_iban"] == "SK0000000000000000000000"

    def test_upgrade_inserts_superadmin_user(self):
        """Verify second op.execute call contains user INSERT with correct params."""
        with patch.object(m024, "op") as mock_op:
            m024.upgrade()

            second_call = mock_op.execute.call_args_list[1]
            sql_obj = second_call[0][0]
            sql_str = str(sql_obj)

            assert "INSERT INTO public.users" in sql_str
            compiled = sql_obj.compile()
            params = compiled.params
            assert params["id"] == SUPERADMIN_USER_ID
            assert params["tenant_id"] == DEMO_TENANT_ID
            assert params["username"] == "superadmin"
            assert params["email"] == "superadmin@isnex.eu"
            # password_hash should be a non-empty string
            assert params["password_hash"]
            assert len(params["password_hash"]) > 10

    def test_upgrade_uses_env_var_password(self):
        """Verify upgrade() hashes password from PAYROLL_ADMIN_PASSWORD env var."""
        test_password = "my_secret_prod_password_42"
        with (
            patch.dict(os.environ, {"PAYROLL_ADMIN_PASSWORD": test_password}),
            patch.object(m024, "op") as mock_op,
        ):
            m024.upgrade()

            second_call = mock_op.execute.call_args_list[1]
            sql_obj = second_call[0][0]
            compiled = sql_obj.compile()
            password_hash = compiled.params["password_hash"]

            # Verify the hash was generated from the env var password
            hasher = PasswordHash.recommended()
            assert hasher.verify(test_password, password_hash)

    def test_upgrade_uses_default_password_when_env_not_set(self):
        """Verify upgrade() falls back to 'changeme' when env var is absent."""
        env = os.environ.copy()
        env.pop("PAYROLL_ADMIN_PASSWORD", None)
        with (
            patch.dict(os.environ, env, clear=True),
            patch.object(m024, "op") as mock_op,
        ):
            m024.upgrade()

            second_call = mock_op.execute.call_args_list[1]
            sql_obj = second_call[0][0]
            compiled = sql_obj.compile()
            password_hash = compiled.params["password_hash"]

            hasher = PasswordHash.recommended()
            assert hasher.verify("changeme", password_hash)

    def test_upgrade_tenant_on_conflict_ico(self):
        """Verify tenant INSERT uses ON CONFLICT (ico) DO NOTHING."""
        with patch.object(m024, "op") as mock_op:
            m024.upgrade()

            first_call = mock_op.execute.call_args_list[0]
            sql_str = str(first_call[0][0])
            assert "ON CONFLICT (ico) DO NOTHING" in sql_str


class TestMigration024Downgrade:
    """Test downgrade logic by calling m024.downgrade() with mocked op.execute."""

    def test_downgrade_calls_op_execute_twice(self):
        """downgrade() must call op.execute exactly twice (user + tenant)."""
        with patch.object(m024, "op") as mock_op:
            m024.downgrade()
            assert mock_op.execute.call_count == 2

    def test_downgrade_deletes_user_then_tenant(self):
        """Verify downgrade deletes user first (FK), then tenant."""
        with patch.object(m024, "op") as mock_op:
            m024.downgrade()

            first_call_sql = str(mock_op.execute.call_args_list[0][0][0])
            second_call_sql = str(mock_op.execute.call_args_list[1][0][0])

            assert "DELETE FROM public.users" in first_call_sql
            assert "DELETE FROM public.tenants" in second_call_sql

    def test_downgrade_uses_correct_ids(self):
        """Verify downgrade deletes by the same fixed UUIDs used in upgrade."""
        with patch.object(m024, "op") as mock_op:
            m024.downgrade()

            # User delete
            user_sql = mock_op.execute.call_args_list[0][0][0]
            user_params = user_sql.compile().params
            assert user_params["id"] == SUPERADMIN_USER_ID

            # Tenant delete
            tenant_sql = mock_op.execute.call_args_list[1][0][0]
            tenant_params = tenant_sql.compile().params
            assert tenant_params["id"] == DEMO_TENANT_ID
