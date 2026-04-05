"""Tests for HealthInsurer service layer."""

from uuid import uuid4

from app.models.health_insurer import HealthInsurer
from app.schemas.health_insurer import HealthInsurerCreate, HealthInsurerUpdate
from app.services.health_insurer import (
    create_health_insurer,
    delete_health_insurer,
    get_health_insurer,
    list_health_insurers,
    update_health_insurer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_payload(**overrides) -> HealthInsurerCreate:
    """Build a valid HealthInsurerCreate with sensible defaults."""
    defaults = {
        "code": "25",
        "name": "Všeobecná zdravotná poisťovňa, a.s.",
        "iban": "SK8975000000000012345678",
        "bic": None,
        "is_active": True,
    }
    defaults.update(overrides)
    return HealthInsurerCreate(**defaults)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateHealthInsurer:
    """Tests for create_health_insurer."""

    def test_create_returns_model_instance(self, db_session):
        payload = _make_payload()
        result = create_health_insurer(db_session, payload)

        assert isinstance(result, HealthInsurer)
        assert result.id is not None
        assert result.code == "25"
        assert result.name == "Všeobecná zdravotná poisťovňa, a.s."
        assert result.iban == "SK8975000000000012345678"
        assert result.bic is None
        assert result.is_active is True

    def test_create_with_bic(self, db_session):
        payload = _make_payload(bic="SUBASKBX")
        result = create_health_insurer(db_session, payload)

        assert result.bic == "SUBASKBX"

    def test_create_inactive(self, db_session):
        payload = _make_payload(code="99", is_active=False)
        result = create_health_insurer(db_session, payload)

        assert result.is_active is False


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetHealthInsurer:
    """Tests for get_health_insurer."""

    def test_get_existing(self, db_session):
        created = create_health_insurer(db_session, _make_payload())

        fetched = get_health_insurer(db_session, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.code == created.code

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_health_insurer(db_session, uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListHealthInsurers:
    """Tests for list_health_insurers."""

    def test_list_empty(self, db_session):
        result = list_health_insurers(db_session)

        assert result == []

    def test_list_returns_all(self, db_session):
        create_health_insurer(db_session, _make_payload(code="24"))
        create_health_insurer(db_session, _make_payload(code="25"))

        result = list_health_insurers(db_session)

        assert len(result) == 2

    def test_list_ordering_by_code(self, db_session):
        """Insurers are ordered by code ascending."""
        create_health_insurer(db_session, _make_payload(code="27"))
        create_health_insurer(db_session, _make_payload(code="24"))
        create_health_insurer(db_session, _make_payload(code="25"))

        result = list_health_insurers(db_session)

        assert [r.code for r in result] == ["24", "25", "27"]

    def test_list_pagination_skip(self, db_session):
        for code in ("24", "25", "27"):
            create_health_insurer(db_session, _make_payload(code=code))

        result = list_health_insurers(db_session, skip=1)

        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        for code in ("24", "25", "27"):
            create_health_insurer(db_session, _make_payload(code=code))

        result = list_health_insurers(db_session, limit=2)

        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        for code in ("24", "25", "27"):
            create_health_insurer(db_session, _make_payload(code=code))

        result = list_health_insurers(db_session, skip=1, limit=1)

        assert len(result) == 1


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateHealthInsurer:
    """Tests for update_health_insurer."""

    def test_update_single_field(self, db_session):
        created = create_health_insurer(db_session, _make_payload())

        updated = update_health_insurer(
            db_session,
            created.id,
            HealthInsurerUpdate(name="VšZP (nový názov)"),
        )

        assert updated is not None
        assert updated.name == "VšZP (nový názov)"
        # unchanged fields stay the same
        assert updated.code == "25"

    def test_update_multiple_fields(self, db_session):
        created = create_health_insurer(db_session, _make_payload())

        updated = update_health_insurer(
            db_session,
            created.id,
            HealthInsurerUpdate(
                iban="SK1234567890123456789012",
                bic="TATRSKBX",
            ),
        )

        assert updated is not None
        assert updated.iban == "SK1234567890123456789012"
        assert updated.bic == "TATRSKBX"

    def test_update_is_active(self, db_session):
        created = create_health_insurer(db_session, _make_payload())

        updated = update_health_insurer(
            db_session,
            created.id,
            HealthInsurerUpdate(is_active=False),
        )

        assert updated is not None
        assert updated.is_active is False

    def test_update_nonexistent_returns_none(self, db_session):
        result = update_health_insurer(
            db_session,
            uuid4(),
            HealthInsurerUpdate(name="Neexistujúca"),
        )

        assert result is None

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        created = create_health_insurer(db_session, _make_payload())

        updated = update_health_insurer(
            db_session,
            created.id,
            HealthInsurerUpdate(),
        )

        assert updated is not None
        assert updated.name == created.name


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteHealthInsurer:
    """Tests for delete_health_insurer."""

    def test_delete_existing(self, db_session):
        created = create_health_insurer(db_session, _make_payload())

        deleted = delete_health_insurer(db_session, created.id)

        assert deleted is True
        assert get_health_insurer(db_session, created.id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        result = delete_health_insurer(db_session, uuid4())

        assert result is False
