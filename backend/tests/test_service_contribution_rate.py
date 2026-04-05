"""Tests for ContributionRate service layer."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.models.contribution_rate import ContributionRate
from app.schemas.contribution_rate import ContributionRateCreate, ContributionRateUpdate
from app.services.contribution_rate import (
    create_contribution_rate,
    delete_contribution_rate,
    get_contribution_rate,
    list_contribution_rates,
    update_contribution_rate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_payload(**overrides) -> ContributionRateCreate:
    """Build a valid ContributionRateCreate with sensible defaults."""
    defaults = {
        "rate_type": "sp_employee_nemocenske",
        "rate_percent": Decimal("1.4000"),
        "max_assessment_base": None,
        "payer": "employee",
        "fund": "nemocenske",
        "valid_from": date(2025, 1, 1),
        "valid_to": None,
    }
    defaults.update(overrides)
    return ContributionRateCreate(**defaults)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateContributionRate:
    """Tests for create_contribution_rate."""

    def test_create_returns_model_instance(self, db_session):
        payload = _make_payload()
        result = create_contribution_rate(db_session, payload)

        assert isinstance(result, ContributionRate)
        assert result.id is not None
        assert result.rate_type == "sp_employee_nemocenske"
        assert result.rate_percent == Decimal("1.4000")
        assert result.payer == "employee"
        assert result.fund == "nemocenske"
        assert result.valid_from == date(2025, 1, 1)
        assert result.valid_to is None

    def test_create_with_max_assessment_base(self, db_session):
        payload = _make_payload(max_assessment_base=Decimal("9128.00"))
        result = create_contribution_rate(db_session, payload)

        assert result.max_assessment_base == Decimal("9128.00")

    def test_create_with_valid_to(self, db_session):
        payload = _make_payload(valid_to=date(2025, 12, 31))
        result = create_contribution_rate(db_session, payload)

        assert result.valid_to == date(2025, 12, 31)

    def test_create_employer_payer(self, db_session):
        payload = _make_payload(payer="employer")
        result = create_contribution_rate(db_session, payload)

        assert result.payer == "employer"


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetContributionRate:
    """Tests for get_contribution_rate."""

    def test_get_existing(self, db_session):
        created = create_contribution_rate(db_session, _make_payload())

        fetched = get_contribution_rate(db_session, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.rate_type == created.rate_type

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_contribution_rate(db_session, uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListContributionRates:
    """Tests for list_contribution_rates."""

    def test_list_empty(self, db_session):
        result = list_contribution_rates(db_session)

        assert result == []

    def test_list_returns_all(self, db_session):
        create_contribution_rate(db_session, _make_payload(rate_type="rate_a"))
        create_contribution_rate(db_session, _make_payload(rate_type="rate_b"))

        result = list_contribution_rates(db_session)

        assert len(result) == 2

    def test_list_ordering(self, db_session):
        """Rates with the same type are ordered by valid_from DESC."""
        create_contribution_rate(
            db_session,
            _make_payload(rate_type="sp_x", valid_from=date(2024, 1, 1)),
        )
        create_contribution_rate(
            db_session,
            _make_payload(rate_type="sp_x", valid_from=date(2025, 1, 1)),
        )

        result = list_contribution_rates(db_session)

        assert result[0].valid_from == date(2025, 1, 1)
        assert result[1].valid_from == date(2024, 1, 1)

    def test_list_pagination_skip(self, db_session):
        for i in range(3):
            create_contribution_rate(
                db_session,
                _make_payload(rate_type=f"rate_{i:02d}"),
            )

        result = list_contribution_rates(db_session, skip=1)

        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        for i in range(3):
            create_contribution_rate(
                db_session,
                _make_payload(rate_type=f"rate_{i:02d}"),
            )

        result = list_contribution_rates(db_session, limit=2)

        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        for i in range(5):
            create_contribution_rate(
                db_session,
                _make_payload(rate_type=f"rate_{i:02d}"),
            )

        result = list_contribution_rates(db_session, skip=1, limit=2)

        assert len(result) == 2


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateContributionRate:
    """Tests for update_contribution_rate."""

    def test_update_single_field(self, db_session):
        created = create_contribution_rate(db_session, _make_payload())

        updated = update_contribution_rate(
            db_session,
            created.id,
            ContributionRateUpdate(rate_percent=Decimal("2.0000")),
        )

        assert updated is not None
        assert updated.rate_percent == Decimal("2.0000")
        # unchanged fields stay the same
        assert updated.rate_type == "sp_employee_nemocenske"

    def test_update_multiple_fields(self, db_session):
        created = create_contribution_rate(db_session, _make_payload())

        updated = update_contribution_rate(
            db_session,
            created.id,
            ContributionRateUpdate(
                fund="starobne",
                valid_to=date(2025, 12, 31),
            ),
        )

        assert updated is not None
        assert updated.fund == "starobne"
        assert updated.valid_to == date(2025, 12, 31)

    def test_update_nonexistent_returns_none(self, db_session):
        result = update_contribution_rate(
            db_session,
            uuid4(),
            ContributionRateUpdate(rate_percent=Decimal("5.0000")),
        )

        assert result is None

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        created = create_contribution_rate(db_session, _make_payload())

        updated = update_contribution_rate(
            db_session,
            created.id,
            ContributionRateUpdate(),
        )

        assert updated is not None
        assert updated.rate_percent == created.rate_percent


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteContributionRate:
    """Tests for delete_contribution_rate."""

    def test_delete_existing(self, db_session):
        created = create_contribution_rate(db_session, _make_payload())

        deleted = delete_contribution_rate(db_session, created.id)

        assert deleted is True
        assert get_contribution_rate(db_session, created.id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        result = delete_contribution_rate(db_session, uuid4())

        assert result is False
