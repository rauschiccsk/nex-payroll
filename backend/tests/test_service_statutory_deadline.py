"""Tests for StatutoryDeadline service layer."""

from datetime import date
from uuid import uuid4

from app.models.statutory_deadline import StatutoryDeadline
from app.schemas.statutory_deadline import StatutoryDeadlineCreate, StatutoryDeadlineUpdate
from app.services.statutory_deadline import (
    count_statutory_deadlines,
    create_statutory_deadline,
    delete_statutory_deadline,
    get_statutory_deadline,
    list_statutory_deadlines,
    update_statutory_deadline,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = 0


def _make_payload(**overrides) -> StatutoryDeadlineCreate:
    """Build a valid StatutoryDeadlineCreate with sensible defaults."""
    global _counter  # noqa: PLW0603
    _counter += 1
    defaults = {
        "code": f"SP_MONTHLY_{_counter}",
        "name": "Mesačný výkaz SP",
        "deadline_type": "monthly",
        "institution": "Sociálna poisťovňa",
        "day_of_month": 20,
        "description": "Mesačný výkaz poistného a príspevkov",
        "valid_from": date(2025, 1, 1),
        "valid_to": None,
    }
    defaults.update(overrides)
    return StatutoryDeadlineCreate(**defaults)


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCountStatutoryDeadlines:
    """Tests for count_statutory_deadlines."""

    def test_count_empty(self, db_session):
        assert count_statutory_deadlines(db_session) == 0

    def test_count_after_inserts(self, db_session):
        create_statutory_deadline(db_session, _make_payload())
        create_statutory_deadline(db_session, _make_payload())
        create_statutory_deadline(db_session, _make_payload())

        assert count_statutory_deadlines(db_session) == 3


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateStatutoryDeadline:
    """Tests for create_statutory_deadline."""

    def test_create_returns_model_instance(self, db_session):
        payload = _make_payload()
        result = create_statutory_deadline(db_session, payload)

        assert isinstance(result, StatutoryDeadline)
        assert result.id is not None
        assert result.deadline_type == "monthly"
        assert result.institution == "Sociálna poisťovňa"
        assert result.day_of_month == 20
        assert result.description == "Mesačný výkaz poistného a príspevkov"
        assert result.valid_from == date(2025, 1, 1)
        assert result.valid_to is None

    def test_create_with_valid_to(self, db_session):
        payload = _make_payload(valid_to=date(2025, 12, 31))
        result = create_statutory_deadline(db_session, payload)

        assert result.valid_to == date(2025, 12, 31)

    def test_create_with_business_days_rule(self, db_session):
        payload = _make_payload(business_days_rule=True)
        result = create_statutory_deadline(db_session, payload)

        assert result.business_days_rule is True

    def test_create_annual_type(self, db_session):
        payload = _make_payload(
            deadline_type="annual",
            institution="Daňový úrad",
            day_of_month=30,
            month_of_year=4,
            description="Ročné hlásenie o dani",
        )
        result = create_statutory_deadline(db_session, payload)

        assert result.deadline_type == "annual"
        assert result.institution == "Daňový úrad"
        assert result.day_of_month == 30
        assert result.month_of_year == 4


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetStatutoryDeadline:
    """Tests for get_statutory_deadline."""

    def test_get_existing(self, db_session):
        created = create_statutory_deadline(db_session, _make_payload())

        fetched = get_statutory_deadline(db_session, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.deadline_type == created.deadline_type

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_statutory_deadline(db_session, uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListStatutoryDeadlines:
    """Tests for list_statutory_deadlines."""

    def test_list_empty(self, db_session):
        result = list_statutory_deadlines(db_session)

        assert result == []

    def test_list_returns_all(self, db_session):
        create_statutory_deadline(db_session, _make_payload(deadline_type="monthly"))
        create_statutory_deadline(db_session, _make_payload(deadline_type="annual"))

        result = list_statutory_deadlines(db_session)

        assert len(result) == 2

    def test_list_ordering(self, db_session):
        """Deadlines with the same type are ordered by valid_from DESC."""
        create_statutory_deadline(
            db_session,
            _make_payload(deadline_type="monthly", valid_from=date(2024, 1, 1)),
        )
        create_statutory_deadline(
            db_session,
            _make_payload(deadline_type="monthly", valid_from=date(2025, 1, 1)),
        )

        result = list_statutory_deadlines(db_session)

        assert result[0].valid_from == date(2025, 1, 1)
        assert result[1].valid_from == date(2024, 1, 1)

    def test_list_pagination_skip(self, db_session):
        for i in range(3):
            create_statutory_deadline(
                db_session,
                _make_payload(
                    deadline_type="annual" if i == 0 else "monthly",
                    valid_from=date(2025, i + 1, 1),
                ),
            )

        result = list_statutory_deadlines(db_session, skip=1)

        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        for i in range(3):
            create_statutory_deadline(
                db_session,
                _make_payload(
                    deadline_type="annual" if i == 0 else "monthly",
                    valid_from=date(2025, i + 1, 1),
                ),
            )

        result = list_statutory_deadlines(db_session, limit=2)

        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        for i in range(5):
            create_statutory_deadline(
                db_session,
                _make_payload(
                    deadline_type="monthly",
                    valid_from=date(2020 + i, 1, 1),
                ),
            )

        result = list_statutory_deadlines(db_session, skip=1, limit=2)

        assert len(result) == 2


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateStatutoryDeadline:
    """Tests for update_statutory_deadline."""

    def test_update_single_field(self, db_session):
        created = create_statutory_deadline(db_session, _make_payload())

        updated = update_statutory_deadline(
            db_session,
            created.id,
            StatutoryDeadlineUpdate(day_of_month=25),
        )

        assert updated is not None
        assert updated.day_of_month == 25
        # unchanged fields stay the same
        assert updated.deadline_type == "monthly"

    def test_update_multiple_fields(self, db_session):
        created = create_statutory_deadline(db_session, _make_payload())

        updated = update_statutory_deadline(
            db_session,
            created.id,
            StatutoryDeadlineUpdate(
                institution="VšZP",
                valid_to=date(2025, 12, 31),
            ),
        )

        assert updated is not None
        assert updated.institution == "VšZP"
        assert updated.valid_to == date(2025, 12, 31)

    def test_update_nonexistent_returns_none(self, db_session):
        result = update_statutory_deadline(
            db_session,
            uuid4(),
            StatutoryDeadlineUpdate(day_of_month=15),
        )

        assert result is None

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        created = create_statutory_deadline(db_session, _make_payload())

        updated = update_statutory_deadline(
            db_session,
            created.id,
            StatutoryDeadlineUpdate(),
        )

        assert updated is not None
        assert updated.day_of_month == created.day_of_month

    def test_update_business_days_rule(self, db_session):
        created = create_statutory_deadline(db_session, _make_payload())

        updated = update_statutory_deadline(
            db_session,
            created.id,
            StatutoryDeadlineUpdate(business_days_rule=True),
        )

        assert updated is not None
        assert updated.business_days_rule is True


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteStatutoryDeadline:
    """Tests for delete_statutory_deadline."""

    def test_delete_existing(self, db_session):
        created = create_statutory_deadline(db_session, _make_payload())

        deleted = delete_statutory_deadline(db_session, created.id)

        assert deleted is True
        assert get_statutory_deadline(db_session, created.id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        result = delete_statutory_deadline(db_session, uuid4())

        assert result is False
