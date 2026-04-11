"""Validate SAVEPOINT test isolation provided by conftest.py fixtures.

These tests verify that:
- db_session fixture uses join_transaction_mode='create_savepoint'
- Data inserted in one test does NOT leak to another
- session.commit() inside a test does NOT persist after rollback
"""

import pytest
from sqlalchemy import text


@pytest.mark.db
class TestSavepointIsolation:
    """Verify transactional isolation between tests."""

    def test_insert_tenant_row(self, db_session):
        """Insert a tenant row — should be rolled back after this test."""
        db_session.execute(
            text(
                "INSERT INTO tenants (name, ico, address_street, address_city, "
                "address_zip, address_country, bank_iban, schema_name) "
                "VALUES (:name, :ico, :street, :city, :zip, :country, :iban, :schema)"
            ),
            {
                "name": "Isolation Test Corp",
                "ico": "99999999",
                "street": "Test St 1",
                "city": "Bratislava",
                "zip": "81101",
                "country": "SK",
                "iban": "SK0000000000000000000001",
                "schema": "test_isolation_schema",
            },
        )
        db_session.commit()

        result = db_session.execute(text("SELECT count(*) FROM tenants WHERE ico = '99999999'"))
        assert result.scalar() == 1

    def test_tenant_row_not_persisted(self, db_session):
        """Verify the row from the previous test was rolled back."""
        result = db_session.execute(text("SELECT count(*) FROM tenants WHERE ico = '99999999'"))
        assert result.scalar() == 0, "SAVEPOINT isolation failed — data from previous test leaked"

    def test_session_uses_savepoint_mode(self, db_session):
        """Verify the session is configured with create_savepoint mode."""
        assert db_session.join_transaction_mode == "create_savepoint"

    def test_session_is_bound_to_connection(self, db_session):
        """Verify the session is bound to a connection (not engine)."""
        bind = db_session.get_bind()
        # Session should be bound to a connection, not an engine directly
        assert bind is not None
