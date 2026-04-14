"""Tests for Tenant model (app.models.tenant)."""

import pytest
from sqlalchemy import TIMESTAMP, Boolean, String, inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.tenant import Tenant


class TestTenantSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert Tenant.__tablename__ == "tenants"

    def test_schema_is_public(self):
        assert Tenant.__table__.schema == "public"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(Tenant, Base)

    def test_inherits_uuid_mixin(self):
        from app.models.base import UUIDMixin

        assert issubclass(Tenant, UUIDMixin)

    def test_inherits_timestamp_mixin(self):
        from app.models.base import TimestampMixin

        assert issubclass(Tenant, TimestampMixin)

    def test_table_args_dict(self):
        """Table args must include schema='public' dict."""
        table_opts = Tenant.__table_args__[-1]
        assert table_opts.get("schema") == "public"
        assert table_opts.get("extend_existing") is True


class TestTenantColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(Tenant)

    def test_id_column(self):
        col = self.mapper.columns["id"]
        assert col.primary_key is True
        assert isinstance(col.type, UUID)
        assert col.server_default is not None

    def test_name_column(self):
        col = self.mapper.columns["name"]
        assert isinstance(col.type, String)
        assert col.type.length == 200
        assert col.nullable is False

    def test_ico_column(self):
        col = self.mapper.columns["ico"]
        assert isinstance(col.type, String)
        assert col.type.length == 8
        assert col.nullable is False

    def test_ico_unique_constraint(self):
        constraints = Tenant.__table__.constraints
        uq_names = [c.name for c in constraints if hasattr(c, "columns") and "ico" in c.columns]
        assert "uq_tenants_ico" in uq_names

    def test_dic_column(self):
        col = self.mapper.columns["dic"]
        assert isinstance(col.type, String)
        assert col.type.length == 12
        assert col.nullable is True

    def test_ic_dph_column(self):
        col = self.mapper.columns["ic_dph"]
        assert isinstance(col.type, String)
        assert col.type.length == 14
        assert col.nullable is True

    def test_address_street_column(self):
        col = self.mapper.columns["address_street"]
        assert isinstance(col.type, String)
        assert col.type.length == 200
        assert col.nullable is False

    def test_address_city_column(self):
        col = self.mapper.columns["address_city"]
        assert isinstance(col.type, String)
        assert col.type.length == 100
        assert col.nullable is False

    def test_address_zip_column(self):
        col = self.mapper.columns["address_zip"]
        assert isinstance(col.type, String)
        assert col.type.length == 10
        assert col.nullable is False

    def test_address_country_column(self):
        col = self.mapper.columns["address_country"]
        assert isinstance(col.type, String)
        assert col.type.length == 2
        assert col.nullable is False
        assert col.server_default is not None

    def test_bank_iban_column(self):
        col = self.mapper.columns["bank_iban"]
        assert isinstance(col.type, String)
        assert col.type.length == 34
        assert col.nullable is False

    def test_bank_bic_column(self):
        col = self.mapper.columns["bank_bic"]
        assert isinstance(col.type, String)
        assert col.type.length == 11
        assert col.nullable is True

    def test_schema_name_column(self):
        col = self.mapper.columns["schema_name"]
        assert isinstance(col.type, String)
        assert col.type.length == 63
        assert col.nullable is False

    def test_schema_name_unique_constraint(self):
        constraints = Tenant.__table__.constraints
        uq_names = [c.name for c in constraints if hasattr(c, "columns") and "schema_name" in c.columns]
        assert "uq_tenants_schema_name" in uq_names

    def test_default_role_column(self):
        col = self.mapper.columns["default_role"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is False
        assert col.server_default is not None

    def test_is_active_column(self):
        col = self.mapper.columns["is_active"]
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert col.server_default is not None

    def test_created_at_column(self):
        col = self.mapper.columns["created_at"]
        assert isinstance(col.type, TIMESTAMP)
        assert col.type.timezone is True
        assert col.nullable is False
        assert col.server_default is not None

    def test_updated_at_column(self):
        col = self.mapper.columns["updated_at"]
        assert isinstance(col.type, TIMESTAMP)
        assert col.type.timezone is True
        assert col.nullable is False
        assert col.server_default is not None


class TestTenantConstraints:
    """Verify UNIQUE constraints on ico and schema_name."""

    def test_ico_unique_constraint(self, db_session):
        """DB must reject duplicate IČO values."""
        tenant1 = Tenant(
            name="Firma A s.r.o.",
            ico="12345678",
            address_street="Hlavná 1",
            address_city="Bratislava",
            address_zip="81101",
            bank_iban="SK0000000000000000000001",
            schema_name="tenant_firma_a",
        )
        db_session.add(tenant1)
        db_session.flush()

        tenant2 = Tenant(
            name="Firma B s.r.o.",
            ico="12345678",
            address_street="Štúrova 2",
            address_city="Košice",
            address_zip="04001",
            bank_iban="SK0000000000000000000002",
            schema_name="tenant_firma_b",
        )
        db_session.add(tenant2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_schema_name_unique_constraint(self, db_session):
        """DB must reject duplicate schema names."""
        tenant1 = Tenant(
            name="Firma C s.r.o.",
            ico="11111111",
            address_street="Hlavná 1",
            address_city="Bratislava",
            address_zip="81101",
            bank_iban="SK0000000000000000000001",
            schema_name="tenant_firma_c",
        )
        db_session.add(tenant1)
        db_session.flush()

        tenant2 = Tenant(
            name="Firma D s.r.o.",
            ico="22222222",
            address_street="Štúrova 2",
            address_city="Košice",
            address_zip="04001",
            bank_iban="SK0000000000000000000002",
            schema_name="tenant_firma_c",
        )
        db_session.add(tenant2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()


class TestTenantRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        tenant = Tenant(
            name="Test Company s.r.o.",
            ico="99999999",
            address_street="Testová 1",
            address_city="Bratislava",
            address_zip="81101",
            bank_iban="SK0000000000000000000001",
            schema_name="tenant_test",
            is_active=True,
        )

        result = repr(tenant)
        assert "Test Company s.r.o." in result
        assert "99999999" in result
        assert "tenant_test" in result
        assert "is_active=True" in result


class TestTenantDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session):
        tenant = Tenant(
            name="NEX Test s.r.o.",
            ico="87654321",
            dic="2087654321",
            ic_dph="SK2087654321",
            address_street="Priemyselná 10",
            address_city="Bratislava",
            address_zip="81101",
            bank_iban="SK3100000000000000000099",
            bank_bic="KOMBSKBA",
            schema_name="tenant_nex_test",
            default_role="accountant",
        )
        db_session.add(tenant)
        db_session.flush()

        assert tenant.id is not None
        assert tenant.created_at is not None
        assert tenant.updated_at is not None
        assert tenant.name == "NEX Test s.r.o."
        assert tenant.ico == "87654321"
        assert tenant.dic == "2087654321"
        assert tenant.ic_dph == "SK2087654321"
        assert tenant.address_street == "Priemyselná 10"
        assert tenant.address_city == "Bratislava"
        assert tenant.address_zip == "81101"
        assert tenant.address_country == "SK"
        assert tenant.bank_iban == "SK3100000000000000000099"
        assert tenant.bank_bic == "KOMBSKBA"
        assert tenant.schema_name == "tenant_nex_test"
        assert tenant.default_role == "accountant"
        assert tenant.is_active is True

    def test_create_minimal(self, db_session):
        """Create tenant with only required fields — verify defaults."""
        tenant = Tenant(
            name="Minimal s.r.o.",
            ico="55555555",
            address_street="Krátka 1",
            address_city="Žilina",
            address_zip="01001",
            bank_iban="SK0000000000000000000055",
            schema_name="tenant_minimal",
        )
        db_session.add(tenant)
        db_session.flush()

        assert tenant.id is not None
        assert tenant.dic is None
        assert tenant.ic_dph is None
        assert tenant.bank_bic is None
        assert tenant.address_country == "SK"
        assert tenant.default_role == "accountant"
        assert tenant.is_active is True

    def test_deactivate_tenant(self, db_session):
        tenant = Tenant(
            name="Inactive s.r.o.",
            ico="33333333",
            address_street="Dlhá 5",
            address_city="Nitra",
            address_zip="94901",
            bank_iban="SK0000000000000000000033",
            schema_name="tenant_inactive",
            is_active=False,
        )
        db_session.add(tenant)
        db_session.flush()

        assert tenant.is_active is False
