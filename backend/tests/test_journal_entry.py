"""Tests for NEX Ledger integration — journal entry model, service, and router.

Covers:
  - JournalEntry model CRUD and constraints
  - Journal entry generation from payroll data
  - Integration sync and status endpoints
  - Double-entry balancing validation
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.journal_entry import JournalEntry
from app.models.payroll import Payroll
from app.models.tenant import Tenant
from app.services.journal_entry import (
    ACCOUNT_331_EMPLOYEES,
    ACCOUNT_336_SP,
    ACCOUNT_336_ZP,
    ACCOUNT_342_TAX,
    ACCOUNT_521_WAGES,
    ACCOUNT_524_SP,
    ACCOUNT_524_ZP,
    generate_entries_for_payroll,
    get_entries_for_period,
    get_period_status,
    sync_period,
)

# ---------------------------------------------------------------------------
# Auto-increment counter for unique test data
# ---------------------------------------------------------------------------
_counter = 0


def _next() -> int:
    global _counter  # noqa: PLW0603
    _counter += 1
    return _counter


# ---------------------------------------------------------------------------
# Helpers — create full entity chain
# ---------------------------------------------------------------------------


def _create_health_insurer(db: Session) -> HealthInsurer:
    n = _next()
    hi = HealthInsurer(
        code=f"{60 + n:02d}"[:4],
        name=f"Test ZP {n}",
        iban=f"SK00000000000000060{n:05d}",
    )
    db.add(hi)
    db.flush()
    return hi


def _create_tenant(db: Session) -> Tenant:
    n = _next()
    tenant = Tenant(
        name=f"Test Corp {n}",
        ico=f"9900{n:04d}",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban=f"SK00000000000000009{n:05d}",
        schema_name=f"tenant_test_journal_{n}",
    )
    db.add(tenant)
    db.flush()
    return tenant


def _create_employee(db: Session, tenant: Tenant, hi: HealthInsurer) -> Employee:
    n = _next()
    emp = Employee(
        tenant_id=tenant.id,
        employee_number=f"EMP-JE-{n:03d}",
        first_name="Ján",
        last_name="Novák",
        birth_date=date(1990, 5, 15),
        birth_number=f"900515{n:04d}",
        gender="M",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban=f"SK31000000000000000{n:05d}",
        health_insurer_id=hi.id,
        tax_declaration_type="standard",
        nczd_applied=True,
        pillar2_saver=False,
        is_disabled=False,
        status="active",
        hire_date=date(2023, 1, 1),
    )
    db.add(emp)
    db.flush()
    return emp


def _create_contract(db: Session, tenant: Tenant, emp: Employee) -> Contract:
    n = _next()
    contract = Contract(
        tenant_id=tenant.id,
        employee_id=emp.id,
        contract_number=f"CTR-JE-{n:03d}",
        contract_type="permanent",
        job_title="Účtovník",
        start_date=date(2026, 1, 1),
        base_wage=Decimal("2500.00"),
        wage_type="monthly",
        is_current=True,
    )
    db.add(contract)
    db.flush()
    return contract


def _create_full_chain(
    db: Session,
) -> tuple[Tenant, Employee, Contract]:
    """Create tenant + health insurer + employee + contract."""
    hi = _create_health_insurer(db)
    tenant = _create_tenant(db)
    emp = _create_employee(db, tenant, hi)
    contract = _create_contract(db, tenant, emp)
    return tenant, emp, contract


def _create_approved_payroll(
    db: Session,
    tenant: Tenant,
    emp: Employee,
    contract: Contract,
    *,
    period_year: int = 2026,
    period_month: int = 3,
    gross_wage: Decimal = Decimal("2500.00"),
    net_wage: Decimal = Decimal("1845.42"),
) -> Payroll:
    """Create an approved payroll with realistic Slovak payroll data."""
    payroll = Payroll(
        tenant_id=tenant.id,
        employee_id=emp.id,
        contract_id=contract.id,
        period_year=period_year,
        period_month=period_month,
        status="approved",
        base_wage=gross_wage,
        overtime_hours=Decimal("0"),
        overtime_amount=Decimal("0"),
        bonus_amount=Decimal("0"),
        supplement_amount=Decimal("0"),
        gross_wage=gross_wage,
        sp_assessment_base=gross_wage,
        sp_nemocenske=Decimal("35.00"),
        sp_starobne=Decimal("100.00"),
        sp_invalidne=Decimal("75.00"),
        sp_nezamestnanost=Decimal("25.00"),
        sp_employee_total=Decimal("235.00"),
        zp_assessment_base=gross_wage,
        zp_employee=Decimal("100.00"),
        partial_tax_base=Decimal("2165.00"),
        nczd_applied=Decimal("477.73"),
        tax_base=Decimal("1687.27"),
        tax_advance=Decimal("319.58"),
        child_bonus=Decimal("0"),
        tax_after_bonus=Decimal("319.58"),
        net_wage=net_wage,
        sp_employer_nemocenske=Decimal("35.00"),
        sp_employer_starobne=Decimal("350.00"),
        sp_employer_invalidne=Decimal("75.00"),
        sp_employer_nezamestnanost=Decimal("25.00"),
        sp_employer_garancne=Decimal("6.25"),
        sp_employer_rezervny=Decimal("119.38"),
        sp_employer_kurzarbeit=Decimal("12.50"),
        sp_employer_urazove=Decimal("20.00"),
        sp_employer_total=Decimal("643.13"),
        zp_employer=Decimal("250.00"),
        total_employer_cost=Decimal("3393.13"),
        pillar2_amount=Decimal("0"),
    )
    db.add(payroll)
    db.flush()
    return payroll


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestJournalEntryModel:
    """Test JournalEntry SQLAlchemy model."""

    def test_create_journal_entry(self, db_session: Session):
        """JournalEntry can be created with all required fields."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entry = JournalEntry(
            tenant_id=tenant.id,
            payroll_id=payroll.id,
            period_year=2026,
            period_month=3,
            entry_date=date(2026, 3, 31),
            account_code="521",
            account_name="Mzdové náklady",
            entry_type="debit",
            amount=Decimal("2500.00"),
            description="Hrubá mzda za 2026/03",
        )
        db_session.add(entry)
        db_session.commit()

        assert entry.id is not None
        assert entry.tenant_id == tenant.id
        assert entry.account_code == "521"
        assert entry.entry_type == "debit"
        assert entry.amount == Decimal("2500.00")
        assert entry.synced_at is None
        assert entry.sync_batch_id is None

    def test_entry_type_constraint(self, db_session: Session):
        """entry_type must be 'debit' or 'credit'."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entry = JournalEntry(
            tenant_id=tenant.id,
            payroll_id=payroll.id,
            period_year=2026,
            period_month=3,
            entry_date=date(2026, 3, 31),
            account_code="521",
            account_name="Test",
            entry_type="invalid",
            amount=Decimal("100.00"),
            description="Bad entry type",
        )
        db_session.add(entry)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.commit()

    def test_amount_positive_constraint(self, db_session: Session):
        """amount must be >= 0."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entry = JournalEntry(
            tenant_id=tenant.id,
            payroll_id=payroll.id,
            period_year=2026,
            period_month=3,
            entry_date=date(2026, 3, 31),
            account_code="521",
            account_name="Test",
            entry_type="debit",
            amount=Decimal("-10.00"),
            description="Negative amount",
        )
        db_session.add(entry)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.commit()

    def test_payroll_fk_restrict(self, db_session: Session):
        """FK to payroll prevents deletion of referenced payroll."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entry = JournalEntry(
            tenant_id=tenant.id,
            payroll_id=payroll.id,
            period_year=2026,
            period_month=3,
            entry_date=date(2026, 3, 31),
            account_code="521",
            account_name="Test",
            entry_type="debit",
            amount=Decimal("100.00"),
            description="Test entry",
        )
        db_session.add(entry)
        db_session.commit()

        # Use raw SQL per FK RESTRICT test pattern (pg8000 quirk)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM payrolls WHERE id = :id"),
                {"id": payroll.id},
            )
            db_session.commit()

    def test_repr(self, db_session: Session):
        """__repr__ includes key fields."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entry = JournalEntry(
            tenant_id=tenant.id,
            payroll_id=payroll.id,
            period_year=2026,
            period_month=3,
            entry_date=date(2026, 3, 31),
            account_code="521",
            account_name="Test",
            entry_type="debit",
            amount=Decimal("100.00"),
            description="Test",
        )
        r = repr(entry)
        assert "521" in r
        assert "debit" in r


# ---------------------------------------------------------------------------
# Service tests — entry generation
# ---------------------------------------------------------------------------


class TestGenerateEntries:
    """Test journal entry generation from payroll."""

    def test_generates_seven_entry_lines(self, db_session: Session):
        """A standard payroll generates 7 journal entry lines."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entries = generate_entries_for_payroll(payroll, sync_batch_id="test123")
        assert len(entries) == 7

    def test_debit_entries(self, db_session: Session):
        """Debit entries cover gross wage, SP employer, ZP employer."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entries = generate_entries_for_payroll(payroll, sync_batch_id="test123")
        debits = [e for e in entries if e["entry_type"] == "debit"]

        assert len(debits) == 3
        codes = {e["account_code"] for e in debits}
        assert ACCOUNT_521_WAGES[0] in codes
        assert ACCOUNT_524_SP[0] in codes
        assert ACCOUNT_524_ZP[0] in codes

    def test_credit_entries(self, db_session: Session):
        """Credit entries cover net wage, SP total, ZP total, tax."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entries = generate_entries_for_payroll(payroll, sync_batch_id="test123")
        credits = [e for e in entries if e["entry_type"] == "credit"]

        assert len(credits) == 4
        codes = {e["account_code"] for e in credits}
        assert ACCOUNT_331_EMPLOYEES[0] in codes
        assert ACCOUNT_336_SP[0] in codes
        assert ACCOUNT_336_ZP[0] in codes
        assert ACCOUNT_342_TAX[0] in codes

    def test_double_entry_balanced(self, db_session: Session):
        """Total debits must equal total credits (double-entry invariant)."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entries = generate_entries_for_payroll(payroll, sync_batch_id="test123")

        total_debit = sum(e["amount"] for e in entries if e["entry_type"] == "debit")
        total_credit = sum(e["amount"] for e in entries if e["entry_type"] == "credit")

        assert total_debit == total_credit, f"Debits ({total_debit}) != Credits ({total_credit})"

    def test_entry_date_is_last_day_of_month(self, db_session: Session):
        """Entry date is the last day of the payroll period month."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(
            db_session,
            tenant,
            emp,
            contract,
            period_year=2026,
            period_month=2,
        )

        entries = generate_entries_for_payroll(payroll, sync_batch_id="test123")

        for entry in entries:
            assert entry["entry_date"] == date(2026, 2, 28)

    def test_sync_batch_id_propagated(self, db_session: Session):
        """All entries share the same sync_batch_id."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entries = generate_entries_for_payroll(payroll, sync_batch_id="batch-abc")

        for entry in entries:
            assert entry["sync_batch_id"] == "batch-abc"

    def test_gross_wage_debit_amount(self, db_session: Session):
        """521 debit equals gross_wage."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(
            db_session,
            tenant,
            emp,
            contract,
            gross_wage=Decimal("3000.00"),
        )

        entries = generate_entries_for_payroll(payroll, sync_batch_id="test")
        wage_debit = next(e for e in entries if e["account_code"] == "521")
        assert wage_debit["amount"] == Decimal("3000.00")

    def test_net_wage_credit_amount(self, db_session: Session):
        """331 credit equals net_wage."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(
            db_session,
            tenant,
            emp,
            contract,
            net_wage=Decimal("1900.00"),
        )

        entries = generate_entries_for_payroll(payroll, sync_batch_id="test")
        net_credit = next(e for e in entries if e["account_code"] == "331")
        assert net_credit["amount"] == Decimal("1900.00")

    def test_sp_liability_combines_employee_and_employer(self, db_session: Session):
        """336.1 credit = SP employee + SP employer total."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entries = generate_entries_for_payroll(payroll, sync_batch_id="test")
        sp_credit = next(e for e in entries if e["account_code"] == "336.1")
        expected = payroll.sp_employee_total + payroll.sp_employer_total
        assert sp_credit["amount"] == expected

    def test_zp_liability_combines_employee_and_employer(self, db_session: Session):
        """336.2 credit = ZP employee + ZP employer."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entries = generate_entries_for_payroll(payroll, sync_batch_id="test")
        zp_credit = next(e for e in entries if e["account_code"] == "336.2")
        expected = payroll.zp_employee + payroll.zp_employer
        assert zp_credit["amount"] == expected


# ---------------------------------------------------------------------------
# Service tests — sync_period
# ---------------------------------------------------------------------------


class TestSyncPeriod:
    """Test period sync service."""

    def test_sync_creates_journal_entries(self, db_session: Session):
        """sync_period creates journal entries in DB."""
        tenant, emp, contract = _create_full_chain(db_session)
        _create_approved_payroll(db_session, tenant, emp, contract)

        result = sync_period(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )

        assert result["entries_created"] == 7
        assert result["payrolls_synced"] == 1
        assert result["period_year"] == 2026
        assert result["period_month"] == 3

    def test_sync_marks_payrolls_as_synced(self, db_session: Session):
        """After sync, payrolls have ledger_sync_status='synced'."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        sync_period(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )

        db_session.refresh(payroll)
        assert payroll.ledger_sync_status == "synced"

    def test_sync_balanced(self, db_session: Session):
        """Sync result has balanced debit/credit totals."""
        tenant, emp, contract = _create_full_chain(db_session)
        _create_approved_payroll(db_session, tenant, emp, contract)

        result = sync_period(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )

        assert result["total_debit"] == result["total_credit"]

    def test_sync_no_payrolls_raises(self, db_session: Session):
        """sync_period raises ValueError when no payrolls exist."""
        tenant, _, _ = _create_full_chain(db_session)

        with pytest.raises(ValueError, match="No approved/paid payrolls"):
            sync_period(
                db_session,
                tenant_id=tenant.id,
                period_year=2026,
                period_month=3,
            )

    def test_resync_replaces_entries(self, db_session: Session):
        """Re-syncing a period replaces existing journal entries."""
        tenant, emp, contract = _create_full_chain(db_session)
        _create_approved_payroll(db_session, tenant, emp, contract)

        # First sync
        result1 = sync_period(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )
        batch1 = result1["sync_batch_id"]

        # Second sync (re-sync)
        result2 = sync_period(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )
        batch2 = result2["sync_batch_id"]

        assert batch1 != batch2
        # Should still be 7 entries, not 14
        entries = get_entries_for_period(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )
        assert len(entries) == 7

    def test_sync_ignores_draft_payrolls(self, db_session: Session):
        """Draft payrolls are not included in sync."""
        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)
        payroll.status = "draft"
        db_session.flush()

        with pytest.raises(ValueError, match="No approved/paid payrolls"):
            sync_period(
                db_session,
                tenant_id=tenant.id,
                period_year=2026,
                period_month=3,
            )


# ---------------------------------------------------------------------------
# Service tests — get_period_status
# ---------------------------------------------------------------------------


class TestGetPeriodStatus:
    """Test period status service."""

    def test_status_before_sync(self, db_session: Session):
        """Status shows not_synced payrolls before sync."""
        tenant, emp, contract = _create_full_chain(db_session)
        _create_approved_payroll(db_session, tenant, emp, contract)

        status = get_period_status(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )

        assert status["total_payrolls"] == 1
        assert status["not_synced_payrolls"] == 1
        assert status["synced_payrolls"] == 0
        assert status["total_journal_entries"] == 0

    def test_status_after_sync(self, db_session: Session):
        """Status shows synced payrolls and journal entries after sync."""
        tenant, emp, contract = _create_full_chain(db_session)
        _create_approved_payroll(db_session, tenant, emp, contract)

        sync_period(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )

        status = get_period_status(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )

        assert status["total_payrolls"] == 1
        assert status["synced_payrolls"] == 1
        assert status["total_journal_entries"] == 7
        assert status["is_balanced"] is True
        assert status["last_sync_at"] is not None

    def test_status_empty_period(self, db_session: Session):
        """Status for empty period returns zeros."""
        tenant, _, _ = _create_full_chain(db_session)

        status = get_period_status(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=1,
        )

        assert status["total_payrolls"] == 0
        assert status["total_journal_entries"] == 0
        assert status["is_balanced"] is True


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------


class TestIntegrationRouter:
    """Test NEX Ledger integration API endpoints."""

    def test_sync_endpoint(self, client, db_session: Session):
        """POST /integration/ledger/{year}/{month}/sync creates entries."""
        tenant, emp, contract = _create_full_chain(db_session)
        _create_approved_payroll(db_session, tenant, emp, contract)
        db_session.commit()

        response = client.post(
            "/api/v1/integration/ledger/2026/3/sync",
            json={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entries_created"] == 7
        assert data["payrolls_synced"] == 1
        assert data["period_year"] == 2026
        assert data["period_month"] == 3
        assert len(data["entries"]) == 7

    def test_sync_endpoint_no_payrolls(self, client, db_session: Session):
        """POST sync returns 404 when no payrolls exist."""
        tenant, _, _ = _create_full_chain(db_session)
        db_session.commit()

        response = client.post(
            "/api/v1/integration/ledger/2026/3/sync",
            json={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 404

    def test_sync_endpoint_invalid_month(self, client, db_session: Session):
        """POST sync returns 422 for invalid month."""
        tenant, _, _ = _create_full_chain(db_session)
        db_session.commit()

        response = client.post(
            "/api/v1/integration/ledger/2026/13/sync",
            json={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 422

    def test_status_endpoint(self, client, db_session: Session):
        """GET /integration/ledger/{year}/{month}/status returns summary."""
        tenant, emp, contract = _create_full_chain(db_session)
        _create_approved_payroll(db_session, tenant, emp, contract)
        db_session.commit()

        response = client.get(
            "/api/v1/integration/ledger/2026/3/status",
            params={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_payrolls"] == 1
        assert data["not_synced_payrolls"] == 1

    def test_status_after_sync(self, client, db_session: Session):
        """Status endpoint reflects synced state after sync."""
        tenant, emp, contract = _create_full_chain(db_session)
        _create_approved_payroll(db_session, tenant, emp, contract)
        db_session.commit()

        # Sync first
        client.post(
            "/api/v1/integration/ledger/2026/3/sync",
            json={"tenant_id": str(tenant.id)},
        )

        # Check status
        response = client.get(
            "/api/v1/integration/ledger/2026/3/status",
            params={"tenant_id": str(tenant.id)},
        )

        data = response.json()
        assert data["synced_payrolls"] == 1
        assert data["total_journal_entries"] == 7
        assert data["is_balanced"] is True

    def test_entries_endpoint(self, client, db_session: Session):
        """GET /integration/ledger/{year}/{month}/entries lists entries."""
        tenant, emp, contract = _create_full_chain(db_session)
        _create_approved_payroll(db_session, tenant, emp, contract)
        db_session.commit()

        # Sync first
        client.post(
            "/api/v1/integration/ledger/2026/3/sync",
            json={"tenant_id": str(tenant.id)},
        )

        # List entries
        response = client.get(
            "/api/v1/integration/ledger/2026/3/entries",
            params={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 7
        entry = data[0]
        assert "account_code" in entry
        assert "account_name" in entry
        assert "entry_type" in entry
        assert "amount" in entry

    def test_entries_empty_period(self, client, db_session: Session):
        """Entries endpoint returns empty list for unsynced period."""
        tenant, _, _ = _create_full_chain(db_session)
        db_session.commit()

        response = client.get(
            "/api/v1/integration/ledger/2026/1/entries",
            params={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestJournalEntrySchemas:
    """Test journal entry Pydantic schemas."""

    def test_journal_entry_read_from_model(self, db_session: Session):
        """JournalEntryRead can be created from ORM model."""
        from app.schemas.journal_entry import JournalEntryRead

        tenant, emp, contract = _create_full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        entry = JournalEntry(
            tenant_id=tenant.id,
            payroll_id=payroll.id,
            period_year=2026,
            period_month=3,
            entry_date=date(2026, 3, 31),
            account_code="521",
            account_name="Mzdové náklady",
            entry_type="debit",
            amount=Decimal("2500.00"),
            description="Test",
        )
        db_session.add(entry)
        db_session.commit()

        schema = JournalEntryRead.model_validate(entry)
        assert schema.account_code == "521"
        assert schema.entry_type == "debit"
        assert schema.amount == Decimal("2500.00")

    def test_ledger_sync_response_schema(self):
        """LedgerSyncResponse validates correctly."""
        from app.schemas.journal_entry import LedgerSyncResponse

        data = LedgerSyncResponse(
            period_year=2026,
            period_month=3,
            tenant_id=str(uuid.uuid4()),
            sync_batch_id="abc123",
            entries_created=7,
            total_debit=Decimal("3393.13"),
            total_credit=Decimal("3393.13"),
            payrolls_synced=1,
            entries=[],
        )
        assert data.entries_created == 7
        assert data.total_debit == data.total_credit

    def test_ledger_sync_status_response_schema(self):
        """LedgerSyncStatusResponse validates correctly."""
        from app.schemas.journal_entry import LedgerSyncStatusResponse

        data = LedgerSyncStatusResponse(
            period_year=2026,
            period_month=3,
            tenant_id=str(uuid.uuid4()),
            total_payrolls=5,
            synced_payrolls=3,
            pending_payrolls=1,
            error_payrolls=0,
            not_synced_payrolls=1,
            total_journal_entries=21,
            total_debit=Decimal("10000.00"),
            total_credit=Decimal("10000.00"),
            last_sync_at=None,
            is_balanced=True,
        )
        assert data.is_balanced is True
