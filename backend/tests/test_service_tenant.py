"""Tests for Tenant service layer."""

from uuid import uuid4

import pytest

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.services.tenant_service import (
    _generate_schema_name,
    count_tenants,
    create_tenant,
    delete_tenant,
    get_tenant,
    list_tenants,
    update_tenant,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_payload(**overrides) -> TenantCreate:
    """Build a valid TenantCreate with sensible defaults."""
    defaults = {
        "name": "Firma s.r.o.",
        "ico": "12345678",
        "dic": "2012345678",
        "ic_dph": "SK2012345678",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "bank_bic": "CEKOSKBX",
        "default_role": "accountant",
        "is_active": True,
    }
    defaults.update(overrides)
    return TenantCreate(**defaults)


# ---------------------------------------------------------------------------
# _generate_schema_name
# ---------------------------------------------------------------------------


class TestGenerateSchemaName:
    """Tests for the schema name generation helper."""

    def test_basic_name(self):
        result = _generate_schema_name("Firma", "12345678")
        assert result == "tenant_firma_12345678"

    def test_strips_diacritics(self):
        result = _generate_schema_name("Účtovníctvo s.r.o.", "11111111")
        assert result == "tenant_uctovnictvo_s_r_o_11111111"

    def test_replaces_special_chars(self):
        result = _generate_schema_name("Test & Company, Ltd.", "22222222")
        assert result == "tenant_test_company_ltd_22222222"

    def test_max_length(self):
        long_name = "A" * 100
        result = _generate_schema_name(long_name, "12345678")
        assert len(result) <= 63

    def test_empty_name(self):
        result = _generate_schema_name("", "12345678")
        assert result == "tenant__12345678"


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCountTenants:
    """Tests for count_tenants."""

    def test_count_empty(self, db_session):
        assert count_tenants(db_session) == 0

    def test_count_after_inserts(self, db_session):
        create_tenant(db_session, _make_payload(ico="11111111", name="Alpha"))
        create_tenant(db_session, _make_payload(ico="22222222", name="Beta"))
        assert count_tenants(db_session) == 2

    def test_count_after_delete(self, db_session):
        t = create_tenant(db_session, _make_payload())
        assert count_tenants(db_session) == 1
        delete_tenant(db_session, t.id)
        assert count_tenants(db_session) == 0


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateTenant:
    """Tests for create_tenant."""

    def test_create_returns_model_instance(self, db_session):
        payload = _make_payload()
        result = create_tenant(db_session, payload)

        assert isinstance(result, Tenant)
        assert result.id is not None
        assert result.name == "Firma s.r.o."
        assert result.ico == "12345678"
        assert result.dic == "2012345678"
        assert result.ic_dph == "SK2012345678"
        assert result.address_street == "Hlavná 1"
        assert result.address_city == "Bratislava"
        assert result.address_zip == "81101"
        assert result.address_country == "SK"
        assert result.bank_iban == "SK8975000000000012345678"
        assert result.bank_bic == "CEKOSKBX"
        assert result.default_role == "accountant"
        assert result.is_active is True

    def test_create_generates_schema_name(self, db_session):
        payload = _make_payload()
        result = create_tenant(db_session, payload)

        assert result.schema_name == "tenant_firma_s_r_o_12345678"

    def test_create_with_optional_fields_null(self, db_session):
        payload = _make_payload(dic=None, ic_dph=None, bank_bic=None)
        result = create_tenant(db_session, payload)

        assert result.dic is None
        assert result.ic_dph is None
        assert result.bank_bic is None

    def test_create_duplicate_ico_raises(self, db_session):
        create_tenant(db_session, _make_payload(ico="99999999"))

        with pytest.raises(ValueError, match="ico='99999999' already exists"):
            create_tenant(
                db_session,
                _make_payload(ico="99999999", name="Different Name"),
            )


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetTenant:
    """Tests for get_tenant."""

    def test_get_existing(self, db_session):
        created = create_tenant(db_session, _make_payload())

        fetched = get_tenant(db_session, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == created.name

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_tenant(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListTenants:
    """Tests for list_tenants."""

    def test_list_empty(self, db_session):
        result = list_tenants(db_session)
        assert result == []

    def test_list_returns_all(self, db_session):
        create_tenant(db_session, _make_payload(ico="11111111", name="Alpha"))
        create_tenant(db_session, _make_payload(ico="22222222", name="Beta"))

        result = list_tenants(db_session)
        assert len(result) == 2

    def test_list_ordering_by_name(self, db_session):
        """Tenants are ordered by name ascending."""
        create_tenant(db_session, _make_payload(ico="22222222", name="Zeta"))
        create_tenant(db_session, _make_payload(ico="11111111", name="Alpha"))

        result = list_tenants(db_session)
        assert result[0].name == "Alpha"
        assert result[1].name == "Zeta"

    def test_list_pagination_skip(self, db_session):
        for i in range(3):
            create_tenant(
                db_session,
                _make_payload(ico=f"0000000{i}", name=f"Tenant {i:02d}"),
            )

        result = list_tenants(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        for i in range(3):
            create_tenant(
                db_session,
                _make_payload(ico=f"0000000{i}", name=f"Tenant {i:02d}"),
            )

        result = list_tenants(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        for i in range(5):
            create_tenant(
                db_session,
                _make_payload(ico=f"0000000{i}", name=f"Tenant {i:02d}"),
            )

        result = list_tenants(db_session, skip=1, limit=2)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateTenant:
    """Tests for update_tenant."""

    def test_update_single_field(self, db_session):
        created = create_tenant(db_session, _make_payload())

        updated = update_tenant(
            db_session,
            created.id,
            TenantUpdate(name="New Name s.r.o."),
        )

        assert updated is not None
        assert updated.name == "New Name s.r.o."
        # unchanged fields stay the same
        assert updated.ico == "12345678"

    def test_update_multiple_fields(self, db_session):
        created = create_tenant(db_session, _make_payload())

        updated = update_tenant(
            db_session,
            created.id,
            TenantUpdate(
                address_city="Košice",
                address_zip="04001",
            ),
        )

        assert updated is not None
        assert updated.address_city == "Košice"
        assert updated.address_zip == "04001"

    def test_update_nonexistent_returns_none(self, db_session):
        result = update_tenant(
            db_session,
            uuid4(),
            TenantUpdate(name="No Such Tenant"),
        )
        assert result is None

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        created = create_tenant(db_session, _make_payload())

        updated = update_tenant(
            db_session,
            created.id,
            TenantUpdate(),
        )

        assert updated is not None
        assert updated.name == created.name

    def test_update_ico_duplicate_raises(self, db_session):
        create_tenant(db_session, _make_payload(ico="11111111", name="First"))
        second = create_tenant(db_session, _make_payload(ico="22222222", name="Second"))

        with pytest.raises(ValueError, match="ico='11111111' already exists"):
            update_tenant(
                db_session,
                second.id,
                TenantUpdate(ico="11111111"),
            )

    def test_update_ico_same_value_no_error(self, db_session):
        """Updating ico to the same value should NOT raise."""
        created = create_tenant(db_session, _make_payload(ico="33333333"))

        updated = update_tenant(
            db_session,
            created.id,
            TenantUpdate(ico="33333333"),
        )

        assert updated is not None
        assert updated.ico == "33333333"

    def test_update_is_active_soft_delete(self, db_session):
        created = create_tenant(db_session, _make_payload())

        updated = update_tenant(
            db_session,
            created.id,
            TenantUpdate(is_active=False),
        )

        assert updated is not None
        assert updated.is_active is False


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteTenant:
    """Tests for delete_tenant."""

    def test_delete_existing(self, db_session):
        created = create_tenant(db_session, _make_payload())

        deleted = delete_tenant(db_session, created.id)

        assert deleted is True
        assert get_tenant(db_session, created.id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        result = delete_tenant(db_session, uuid4())
        assert result is False
