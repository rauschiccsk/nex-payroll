"""Tests for TaxBracket service layer."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.tax_bracket import TaxBracket
from app.schemas.tax_bracket import TaxBracketCreate, TaxBracketUpdate
from app.services.tax_bracket import (
    count_tax_brackets,
    create_tax_bracket,
    delete_tax_bracket,
    get_effective_brackets,
    get_tax_bracket,
    list_tax_brackets,
    update_tax_bracket,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_payload(**overrides) -> TaxBracketCreate:
    """Build a valid TaxBracketCreate with sensible defaults."""
    defaults = {
        "bracket_order": 1,
        "min_amount": Decimal("0.00"),
        "max_amount": Decimal("41445.46"),
        "rate_percent": Decimal("19.00"),
        "nczd_annual": Decimal("5646.48"),
        "nczd_monthly": Decimal("470.54"),
        "nczd_reduction_threshold": Decimal("24952.06"),
        "nczd_reduction_formula": "44.2 * ZM - ZD",
        "valid_from": date(2025, 1, 1),
        "valid_to": None,
    }
    defaults.update(overrides)
    return TaxBracketCreate(**defaults)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateTaxBracket:
    """Tests for create_tax_bracket."""

    def test_create_returns_model_instance(self, db_session):
        payload = _make_payload()
        result = create_tax_bracket(db_session, payload)

        assert isinstance(result, TaxBracket)
        assert result.id is not None
        assert result.bracket_order == 1
        assert result.min_amount == Decimal("0.00")
        assert result.max_amount == Decimal("41445.46")
        assert result.rate_percent == Decimal("19.00")
        assert result.nczd_annual == Decimal("5646.48")
        assert result.nczd_monthly == Decimal("470.54")
        assert result.nczd_reduction_threshold == Decimal("24952.06")
        assert result.nczd_reduction_formula == "44.2 * ZM - ZD"
        assert result.valid_from == date(2025, 1, 1)
        assert result.valid_to is None

    def test_create_with_valid_to(self, db_session):
        payload = _make_payload(valid_to=date(2025, 12, 31))
        result = create_tax_bracket(db_session, payload)

        assert result.valid_to == date(2025, 12, 31)

    def test_create_unlimited_bracket(self, db_session):
        payload = _make_payload(bracket_order=2, max_amount=None, rate_percent=Decimal("25.00"))
        result = create_tax_bracket(db_session, payload)

        assert result.max_amount is None
        assert result.rate_percent == Decimal("25.00")

    def test_create_second_bracket(self, db_session):
        payload = _make_payload(
            bracket_order=2,
            min_amount=Decimal("41445.47"),
            max_amount=None,
            rate_percent=Decimal("25.00"),
        )
        result = create_tax_bracket(db_session, payload)

        assert result.bracket_order == 2
        assert result.min_amount == Decimal("41445.47")

    def test_create_duplicate_raises_value_error(self, db_session):
        """Creating a bracket with the same (valid_from, bracket_order) raises ValueError."""
        create_tax_bracket(db_session, _make_payload())

        with pytest.raises(ValueError, match="already exists"):
            create_tax_bracket(db_session, _make_payload())

    def test_create_same_order_different_valid_from_ok(self, db_session):
        """Same bracket_order but different valid_from should succeed."""
        create_tax_bracket(db_session, _make_payload(valid_from=date(2025, 1, 1)))
        result = create_tax_bracket(db_session, _make_payload(valid_from=date(2024, 1, 1)))

        assert result.valid_from == date(2024, 1, 1)


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetTaxBracket:
    """Tests for get_tax_bracket."""

    def test_get_existing(self, db_session):
        created = create_tax_bracket(db_session, _make_payload())

        fetched = get_tax_bracket(db_session, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.bracket_order == created.bracket_order

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_tax_bracket(db_session, uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestCountTaxBrackets:
    """Tests for count_tax_brackets."""

    def test_count_empty(self, db_session):
        assert count_tax_brackets(db_session) == 0

    def test_count_after_inserts(self, db_session):
        create_tax_bracket(db_session, _make_payload(bracket_order=1))
        create_tax_bracket(
            db_session,
            _make_payload(bracket_order=2, min_amount=Decimal("41445.47"), max_amount=None),
        )

        assert count_tax_brackets(db_session) == 2

    def test_count_unaffected_by_pagination(self, db_session):
        """count_tax_brackets returns total regardless of list pagination."""
        for i in range(1, 6):
            create_tax_bracket(
                db_session,
                _make_payload(bracket_order=i, min_amount=Decimal(str(i * 1000))),
            )

        # list returns only 2, but count returns all 5
        items = list_tax_brackets(db_session, limit=2)
        assert len(items) == 2
        assert count_tax_brackets(db_session) == 5


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListTaxBrackets:
    """Tests for list_tax_brackets."""

    def test_list_empty(self, db_session):
        result = list_tax_brackets(db_session)

        assert result == []

    def test_list_returns_all(self, db_session):
        create_tax_bracket(db_session, _make_payload(bracket_order=1))
        create_tax_bracket(
            db_session,
            _make_payload(bracket_order=2, min_amount=Decimal("41445.47"), max_amount=None),
        )

        result = list_tax_brackets(db_session)

        assert len(result) == 2

    def test_list_ordering(self, db_session):
        """Brackets are ordered by valid_from DESC then bracket_order ASC."""
        create_tax_bracket(
            db_session,
            _make_payload(bracket_order=1, valid_from=date(2024, 1, 1)),
        )
        create_tax_bracket(
            db_session,
            _make_payload(bracket_order=2, valid_from=date(2025, 1, 1)),
        )
        create_tax_bracket(
            db_session,
            _make_payload(bracket_order=1, valid_from=date(2025, 1, 1)),
        )

        result = list_tax_brackets(db_session)

        # 2025 brackets first (newest), ordered by bracket_order
        assert result[0].valid_from == date(2025, 1, 1)
        assert result[0].bracket_order == 1
        assert result[1].valid_from == date(2025, 1, 1)
        assert result[1].bracket_order == 2
        # 2024 bracket last
        assert result[2].valid_from == date(2024, 1, 1)

    def test_list_pagination_skip(self, db_session):
        for i in range(1, 4):
            create_tax_bracket(
                db_session,
                _make_payload(bracket_order=i, min_amount=Decimal(str(i * 1000))),
            )

        result = list_tax_brackets(db_session, skip=1)

        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        for i in range(1, 4):
            create_tax_bracket(
                db_session,
                _make_payload(bracket_order=i, min_amount=Decimal(str(i * 1000))),
            )

        result = list_tax_brackets(db_session, limit=2)

        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        for i in range(1, 6):
            create_tax_bracket(
                db_session,
                _make_payload(bracket_order=i, min_amount=Decimal(str(i * 1000))),
            )

        result = list_tax_brackets(db_session, skip=1, limit=2)

        assert len(result) == 2


# ---------------------------------------------------------------------------
# get_effective_brackets
# ---------------------------------------------------------------------------


class TestGetEffectiveBrackets:
    """Tests for get_effective_brackets."""

    def test_effective_returns_matching_brackets(self, db_session):
        """Brackets valid on the given date are returned."""
        create_tax_bracket(
            db_session,
            _make_payload(bracket_order=1, valid_from=date(2025, 1, 1)),
        )
        create_tax_bracket(
            db_session,
            _make_payload(
                bracket_order=2,
                min_amount=Decimal("41445.47"),
                max_amount=None,
                rate_percent=Decimal("25.00"),
                valid_from=date(2025, 1, 1),
            ),
        )

        result = get_effective_brackets(db_session, date(2025, 6, 15))

        assert len(result) == 2
        assert result[0].bracket_order == 1
        assert result[1].bracket_order == 2

    def test_effective_excludes_future_brackets(self, db_session):
        """Brackets with valid_from in the future are excluded."""
        create_tax_bracket(
            db_session,
            _make_payload(bracket_order=1, valid_from=date(2026, 1, 1)),
        )

        result = get_effective_brackets(db_session, date(2025, 6, 15))

        assert result == []

    def test_effective_excludes_expired_brackets(self, db_session):
        """Brackets with valid_to before the date are excluded."""
        create_tax_bracket(
            db_session,
            _make_payload(
                bracket_order=1,
                valid_from=date(2024, 1, 1),
                valid_to=date(2024, 12, 31),
            ),
        )

        result = get_effective_brackets(db_session, date(2025, 6, 15))

        assert result == []

    def test_effective_includes_boundary_dates(self, db_session):
        """Brackets on exact valid_from and valid_to boundaries are included."""
        create_tax_bracket(
            db_session,
            _make_payload(
                bracket_order=1,
                valid_from=date(2025, 1, 1),
                valid_to=date(2025, 12, 31),
            ),
        )

        # Exact start
        assert len(get_effective_brackets(db_session, date(2025, 1, 1))) == 1
        # Exact end
        assert len(get_effective_brackets(db_session, date(2025, 12, 31))) == 1
        # Day before start
        assert len(get_effective_brackets(db_session, date(2024, 12, 31))) == 0
        # Day after end
        assert len(get_effective_brackets(db_session, date(2026, 1, 1))) == 0

    def test_effective_empty_when_no_brackets(self, db_session):
        result = get_effective_brackets(db_session, date(2025, 1, 1))

        assert result == []

    def test_effective_ordered_by_bracket_order(self, db_session):
        """Results are sorted by bracket_order ascending."""
        # Insert in reverse order
        create_tax_bracket(
            db_session,
            _make_payload(
                bracket_order=3,
                min_amount=Decimal("80000.00"),
                max_amount=None,
                valid_from=date(2025, 1, 1),
            ),
        )
        create_tax_bracket(
            db_session,
            _make_payload(bracket_order=1, valid_from=date(2025, 1, 1)),
        )
        create_tax_bracket(
            db_session,
            _make_payload(
                bracket_order=2,
                min_amount=Decimal("41445.47"),
                max_amount=Decimal("79999.99"),
                valid_from=date(2025, 1, 1),
            ),
        )

        result = get_effective_brackets(db_session, date(2025, 6, 15))

        assert [b.bracket_order for b in result] == [1, 2, 3]


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateTaxBracket:
    """Tests for update_tax_bracket."""

    def test_update_single_field(self, db_session):
        created = create_tax_bracket(db_session, _make_payload())

        updated = update_tax_bracket(
            db_session,
            created.id,
            TaxBracketUpdate(rate_percent=Decimal("20.00")),
        )

        assert updated is not None
        assert updated.rate_percent == Decimal("20.00")
        # unchanged fields stay the same
        assert updated.bracket_order == 1

    def test_update_multiple_fields(self, db_session):
        created = create_tax_bracket(db_session, _make_payload())

        updated = update_tax_bracket(
            db_session,
            created.id,
            TaxBracketUpdate(
                nczd_annual=Decimal("6000.00"),
                nczd_monthly=Decimal("500.00"),
                valid_to=date(2025, 12, 31),
            ),
        )

        assert updated is not None
        assert updated.nczd_annual == Decimal("6000.00")
        assert updated.nczd_monthly == Decimal("500.00")
        assert updated.valid_to == date(2025, 12, 31)

    def test_update_nonexistent_returns_none(self, db_session):
        result = update_tax_bracket(
            db_session,
            uuid4(),
            TaxBracketUpdate(rate_percent=Decimal("25.00")),
        )

        assert result is None

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        created = create_tax_bracket(db_session, _make_payload())

        updated = update_tax_bracket(
            db_session,
            created.id,
            TaxBracketUpdate(),
        )

        assert updated is not None
        assert updated.rate_percent == created.rate_percent

    def test_update_duplicate_raises_value_error(self, db_session):
        """Updating bracket_order to conflict with another bracket raises ValueError."""
        create_tax_bracket(db_session, _make_payload(bracket_order=1))
        second = create_tax_bracket(
            db_session,
            _make_payload(bracket_order=2, min_amount=Decimal("41445.47"), max_amount=None),
        )

        with pytest.raises(ValueError, match="already exists"):
            update_tax_bracket(
                db_session,
                second.id,
                TaxBracketUpdate(bracket_order=1),
            )

    def test_update_same_values_no_error(self, db_session):
        """Updating a bracket without changing bracket_order/valid_from should not raise."""
        created = create_tax_bracket(db_session, _make_payload(bracket_order=1))

        updated = update_tax_bracket(
            db_session,
            created.id,
            TaxBracketUpdate(bracket_order=1),
        )

        assert updated is not None
        assert updated.bracket_order == 1


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteTaxBracket:
    """Tests for delete_tax_bracket."""

    def test_delete_existing(self, db_session):
        created = create_tax_bracket(db_session, _make_payload())

        deleted = delete_tax_bracket(db_session, created.id)

        assert deleted is True
        assert get_tax_bracket(db_session, created.id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        result = delete_tax_bracket(db_session, uuid4())

        assert result is False
