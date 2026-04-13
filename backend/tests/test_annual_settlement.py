"""Tests for annual tax settlement — R-09 implementation.

Tests cover:
1. AnnualSettlement model CRUD
2. Annual NČZD recalculation logic
3. Annual settlement calculation service
4. Income certificate PDF generation
5. Annual tax report summary
6. API endpoints
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.annual_settlement import AnnualSettlement
from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.payroll import Payroll
from app.models.tenant import Tenant
from app.services.annual_settlement import (
    _calculate_annual_nczd,
    _round,
    approve_settlement,
    calculate_annual_settlement,
    generate_annual_tax_report_summary,
    generate_income_certificate_pdf,
    get_settlements_for_year,
)
from app.services.calculation_engine import (
    NCZD_ANNUAL,
    NCZD_ELIMINATION_THRESHOLD,
    NCZD_REDUCTION_CONSTANT,
    NCZD_REDUCTION_THRESHOLD,
)

# Counter for unique values across tests
_counter = 0


def _next_counter() -> int:
    global _counter  # noqa: PLW0603
    _counter += 1
    return _counter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_health_insurer(db: Session) -> HealthInsurer:
    """Create a test health insurer."""
    n = _next_counter()
    hi = HealthInsurer(
        code=f"{25 + n:02d}"[:4],
        name=f"Test ZP {n}",
        iban=f"SK00000000000000000{n:05d}",
    )
    db.add(hi)
    db.flush()
    return hi


def _create_tenant(db: Session) -> Tenant:
    """Create a test tenant."""
    n = _next_counter()
    tenant = Tenant(
        name=f"Test Corp {n}",
        ico=f"9900{n:04d}",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban=f"SK00000000000000009{n:05d}",
        schema_name=f"tenant_test_annual_{n}",
    )
    db.add(tenant)
    db.flush()
    return tenant


def _create_employee(
    db: Session,
    tenant: Tenant,
    *,
    nczd_applied: bool = True,
    first_name: str = "Ján",
    last_name: str = "Novák",
    _health_insurer: HealthInsurer | None = None,
) -> Employee:
    """Create a test employee."""
    if _health_insurer is None:
        _health_insurer = _create_health_insurer(db)
    n = _next_counter()
    employee = Employee(
        tenant_id=tenant.id,
        employee_number=f"EMP-AN-{n:03d}",
        first_name=first_name,
        last_name=last_name,
        birth_date=date(1990, 5, 15),
        birth_number=f"900515{n:04d}",
        gender="M",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban=f"SK31000000000000000{n:05d}",
        health_insurer_id=_health_insurer.id,
        tax_declaration_type="standard",
        nczd_applied=nczd_applied,
        pillar2_saver=False,
        is_disabled=False,
        status="active",
        hire_date=date(2023, 1, 1),
    )
    db.add(employee)
    db.flush()
    return employee


def _create_contract(db: Session, employee: Employee, tenant: Tenant) -> Contract:
    """Create a test contract."""
    n = _next_counter()
    contract = Contract(
        tenant_id=tenant.id,
        employee_id=employee.id,
        contract_number=f"CTR-AN-{n:03d}",
        contract_type="permanent",
        job_title="Účtovník",
        start_date=date(2026, 1, 1),
        base_wage=Decimal("2000.00"),
        wage_type="monthly",
        is_current=True,
    )
    db.add(contract)
    db.flush()
    return contract


def _create_monthly_payroll(
    db: Session,
    tenant: Tenant,
    employee: Employee,
    contract: Contract,
    month: int,
    *,
    gross_wage: Decimal = Decimal("2000.00"),
    sp_employee_total: Decimal = Decimal("188.00"),
    zp_employee: Decimal = Decimal("100.00"),
    nczd_applied: Decimal = Decimal("497.23"),
    tax_after_bonus: Decimal = Decimal("230.71"),
    child_bonus: Decimal = Decimal("0.00"),
) -> Payroll:
    """Create a test monthly payroll record."""
    partial_tax_base = _round(gross_wage - sp_employee_total - zp_employee)
    tax_base = max(Decimal("0"), _round(partial_tax_base - nczd_applied))
    tax_advance = _round(tax_base * Decimal("0.19"))
    net_wage = _round(gross_wage - sp_employee_total - zp_employee - tax_after_bonus)

    payroll = Payroll(
        tenant_id=tenant.id,
        employee_id=employee.id,
        contract_id=contract.id,
        period_year=2026,
        period_month=month,
        status="approved",
        base_wage=gross_wage,
        gross_wage=gross_wage,
        sp_assessment_base=gross_wage,
        sp_nemocenske=Decimal("28.00"),
        sp_starobne=Decimal("80.00"),
        sp_invalidne=Decimal("60.00"),
        sp_nezamestnanost=Decimal("20.00"),
        sp_employee_total=sp_employee_total,
        zp_assessment_base=gross_wage,
        zp_employee=zp_employee,
        partial_tax_base=partial_tax_base,
        nczd_applied=nczd_applied,
        tax_base=tax_base,
        tax_advance=tax_advance,
        child_bonus=child_bonus,
        tax_after_bonus=tax_after_bonus,
        net_wage=net_wage,
        sp_employer_nemocenske=Decimal("28.00"),
        sp_employer_starobne=Decimal("280.00"),
        sp_employer_invalidne=Decimal("60.00"),
        sp_employer_nezamestnanost=Decimal("20.00"),
        sp_employer_garancne=Decimal("5.00"),
        sp_employer_rezervny=Decimal("95.00"),
        sp_employer_kurzarbeit=Decimal("6.00"),
        sp_employer_urazove=Decimal("16.00"),
        sp_employer_total=Decimal("510.00"),
        zp_employer=Decimal("220.00"),
        total_employer_cost=Decimal("2730.00"),
        calculated_at=datetime.now(UTC),
    )
    db.add(payroll)
    db.flush()
    return payroll


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


class TestAnnualSettlementModel:
    """Test AnnualSettlement model creation and constraints."""

    def test_create_settlement(self, db_session: Session):
        """Test creating a basic annual settlement record."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)

        settlement = AnnualSettlement(
            tenant_id=tenant.id,
            employee_id=employee.id,
            year=2026,
            total_gross_wage=Decimal("24000.00"),
            total_sp_employee=Decimal("2256.00"),
            total_zp_employee=Decimal("1200.00"),
            annual_partial_tax_base=Decimal("20544.00"),
            nczd_monthly_total=Decimal("5966.76"),
            nczd_annual_recalculated=Decimal("5966.73"),
            annual_tax_base=Decimal("14577.27"),
            annual_tax_19=Decimal("2769.68"),
            annual_tax_25=Decimal("0.00"),
            annual_tax_total=Decimal("2769.68"),
            annual_child_bonus=Decimal("0.00"),
            annual_tax_after_bonus=Decimal("2769.68"),
            total_monthly_advances=Decimal("2768.52"),
            settlement_amount=Decimal("-1.16"),
            months_count=12,
            status="calculated",
        )
        db_session.add(settlement)
        db_session.flush()

        assert settlement.id is not None
        assert settlement.year == 2026
        assert settlement.settlement_amount == Decimal("-1.16")
        assert settlement.status == "calculated"

    def test_unique_constraint(self, db_session: Session):
        """Test unique constraint on (tenant_id, employee_id, year)."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)

        base_data = {
            "tenant_id": tenant.id,
            "employee_id": employee.id,
            "year": 2026,
            "total_gross_wage": Decimal("24000.00"),
            "total_sp_employee": Decimal("2256.00"),
            "total_zp_employee": Decimal("1200.00"),
            "annual_partial_tax_base": Decimal("20544.00"),
            "nczd_monthly_total": Decimal("5966.76"),
            "nczd_annual_recalculated": Decimal("5966.73"),
            "annual_tax_base": Decimal("14577.27"),
            "annual_tax_19": Decimal("2769.68"),
            "annual_tax_25": Decimal("0.00"),
            "annual_tax_total": Decimal("2769.68"),
            "annual_child_bonus": Decimal("0.00"),
            "annual_tax_after_bonus": Decimal("2769.68"),
            "total_monthly_advances": Decimal("2768.52"),
            "settlement_amount": Decimal("-1.16"),
            "months_count": 12,
        }

        s1 = AnnualSettlement(**base_data)
        db_session.add(s1)
        db_session.flush()

        s2 = AnnualSettlement(**base_data)
        db_session.add(s2)

        from sqlalchemy.exc import IntegrityError, ProgrammingError

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()

    def test_repr(self, db_session: Session):
        """Test string representation."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)

        settlement = AnnualSettlement(
            tenant_id=tenant.id,
            employee_id=employee.id,
            year=2026,
            total_gross_wage=Decimal("24000.00"),
            total_sp_employee=Decimal("2256.00"),
            total_zp_employee=Decimal("1200.00"),
            annual_partial_tax_base=Decimal("20544.00"),
            nczd_monthly_total=Decimal("5966.76"),
            nczd_annual_recalculated=Decimal("5966.73"),
            annual_tax_base=Decimal("14577.27"),
            annual_tax_19=Decimal("2769.68"),
            annual_tax_25=Decimal("0.00"),
            annual_tax_total=Decimal("2769.68"),
            annual_child_bonus=Decimal("0.00"),
            annual_tax_after_bonus=Decimal("2769.68"),
            total_monthly_advances=Decimal("2768.52"),
            settlement_amount=Decimal("-1.16"),
            months_count=12,
        )
        db_session.add(settlement)
        db_session.flush()

        repr_str = repr(settlement)
        assert "AnnualSettlement" in repr_str
        assert "2026" in repr_str


# ---------------------------------------------------------------------------
# NČZD Recalculation Tests
# ---------------------------------------------------------------------------


class TestAnnualNczdRecalculation:
    """Test annual NČZD recalculation logic."""

    def test_full_nczd_low_income(self):
        """Income below reduction threshold gets full annual NČZD."""
        result = _calculate_annual_nczd(Decimal("20000.00"), True)
        assert result == NCZD_ANNUAL  # 5,966.73

    def test_full_nczd_at_threshold(self):
        """Income exactly at reduction threshold gets full NČZD."""
        result = _calculate_annual_nczd(NCZD_REDUCTION_THRESHOLD, True)
        assert result == NCZD_ANNUAL

    def test_reduced_nczd_above_threshold(self):
        """Income above threshold but below elimination gets reduced NČZD."""
        income = Decimal("30000.00")
        expected = _round(NCZD_REDUCTION_CONSTANT - income / 4)
        result = _calculate_annual_nczd(income, True)
        assert result == expected
        assert result > Decimal("0")
        assert result < NCZD_ANNUAL

    def test_nczd_zero_high_income(self):
        """Income above elimination threshold gets zero NČZD."""
        result = _calculate_annual_nczd(Decimal("55000.00"), True)
        assert result == Decimal("0")

    def test_nczd_zero_at_elimination(self):
        """Income exactly at elimination threshold."""
        # At exactly 50,234.20, NČZD formula: 12558.55 - 50234.20/4 = 12558.55 - 12558.55 = 0
        result = _calculate_annual_nczd(NCZD_ELIMINATION_THRESHOLD, True)
        assert result == Decimal("0")

    def test_nczd_not_eligible(self):
        """Employee without tax declaration gets zero NČZD."""
        result = _calculate_annual_nczd(Decimal("20000.00"), False)
        assert result == Decimal("0")

    def test_nczd_custom_rates(self):
        """NČZD calculation with custom rate parameters."""
        result = _calculate_annual_nczd(
            Decimal("15000.00"),
            True,
            nczd_annual=Decimal("6000.00"),
            nczd_reduction_threshold=Decimal("20000.00"),
        )
        assert result == Decimal("6000.00")


# ---------------------------------------------------------------------------
# Service Tests
# ---------------------------------------------------------------------------


class TestAnnualSettlementService:
    """Test annual settlement calculation service."""

    def test_calculate_settlement_single_employee(self, db_session: Session):
        """Test settlement calculation for one employee with 12 months."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        # Create 12 monthly payrolls
        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        settlements = calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)

        assert len(settlements) == 1
        s = settlements[0]
        assert s.employee_id == employee.id
        assert s.year == 2026
        assert s.months_count == 12
        assert s.total_gross_wage == Decimal("24000.00")
        assert s.status == "calculated"
        assert s.calculated_at is not None

    def test_settlement_nczd_recalculation(self, db_session: Session):
        """Test that annual NČZD is recalculated differently from monthly sum."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant, nczd_applied=True)
        contract = _create_contract(db_session, employee, tenant)

        # Create 12 monthly payrolls with standard NČZD
        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        settlements = calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)

        s = settlements[0]
        # Monthly NČZD total = 497.23 * 12 = 5966.76
        assert s.nczd_monthly_total == Decimal("5966.76")
        # Annual NČZD recalculated (should be 5966.73 for low income)
        assert s.nczd_annual_recalculated == NCZD_ANNUAL

    def test_settlement_no_nczd(self, db_session: Session):
        """Test settlement for employee without NČZD eligibility."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant, nczd_applied=False)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(
                db_session,
                tenant,
                employee,
                contract,
                month,
                nczd_applied=Decimal("0"),
            )

        settlements = calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)

        s = settlements[0]
        assert s.nczd_annual_recalculated == Decimal("0")

    def test_settlement_partial_year(self, db_session: Session):
        """Test settlement for employee with only 6 months of payroll."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        # Only 6 months
        for month in range(1, 7):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        settlements = calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)

        assert len(settlements) == 1
        assert settlements[0].months_count == 6
        assert settlements[0].total_gross_wage == Decimal("12000.00")

    def test_settlement_multiple_employees(self, db_session: Session):
        """Test settlement for multiple employees in same tenant."""
        tenant = _create_tenant(db_session)
        emp1 = _create_employee(db_session, tenant, first_name="Ján")
        emp2 = _create_employee(db_session, tenant, first_name="Peter")
        contract1 = _create_contract(db_session, emp1, tenant)
        contract2 = _create_contract(db_session, emp2, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, emp1, contract1, month)
            _create_monthly_payroll(
                db_session,
                tenant,
                emp2,
                contract2,
                month,
                gross_wage=Decimal("3000.00"),
                sp_employee_total=Decimal("282.00"),
                zp_employee=Decimal("150.00"),
                tax_after_bonus=Decimal("393.45"),
            )

        settlements = calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)

        assert len(settlements) == 2

    def test_settlement_recalculation_updates_existing(self, db_session: Session):
        """Test that re-running settlement updates existing records."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        # First calculation
        settlements1 = calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)
        settlement_id = settlements1[0].id
        db_session.flush()

        # Second calculation — should update, not create new
        settlements2 = calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)

        assert len(settlements2) == 1
        assert settlements2[0].id == settlement_id

    def test_settlement_no_payrolls(self, db_session: Session):
        """Test settlement with no payrolls returns empty list."""
        tenant = _create_tenant(db_session)

        settlements = calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)

        assert settlements == []

    def test_settlement_only_draft_payrolls_excluded(self, db_session: Session):
        """Test that draft payrolls are excluded from settlement."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        payroll = Payroll(
            tenant_id=tenant.id,
            employee_id=employee.id,
            contract_id=contract.id,
            period_year=2026,
            period_month=1,
            status="draft",
            base_wage=Decimal("2000.00"),
            gross_wage=Decimal("2000.00"),
            sp_assessment_base=Decimal("2000.00"),
            sp_nemocenske=Decimal("28.00"),
            sp_starobne=Decimal("80.00"),
            sp_invalidne=Decimal("60.00"),
            sp_nezamestnanost=Decimal("20.00"),
            sp_employee_total=Decimal("188.00"),
            zp_assessment_base=Decimal("2000.00"),
            zp_employee=Decimal("100.00"),
            partial_tax_base=Decimal("1712.00"),
            nczd_applied=Decimal("497.23"),
            tax_base=Decimal("1214.77"),
            tax_advance=Decimal("230.81"),
            tax_after_bonus=Decimal("230.81"),
            net_wage=Decimal("1481.19"),
            sp_employer_nemocenske=Decimal("28.00"),
            sp_employer_starobne=Decimal("280.00"),
            sp_employer_invalidne=Decimal("60.00"),
            sp_employer_nezamestnanost=Decimal("20.00"),
            sp_employer_garancne=Decimal("5.00"),
            sp_employer_rezervny=Decimal("95.00"),
            sp_employer_kurzarbeit=Decimal("6.00"),
            sp_employer_urazove=Decimal("16.00"),
            sp_employer_total=Decimal("510.00"),
            zp_employer=Decimal("220.00"),
            total_employer_cost=Decimal("2730.00"),
        )
        db_session.add(payroll)
        db_session.flush()

        settlements = calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)
        assert settlements == []

    def test_settlement_positive_overpayment(self, db_session: Session):
        """Test settlement where monthly advances exceed annual tax (refund)."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant, nczd_applied=True)
        contract = _create_contract(db_session, employee, tenant)

        # Create payrolls where monthly NČZD was lower than annual recalculation
        # would yield, so advances are higher than actual annual tax
        for month in range(1, 13):
            _create_monthly_payroll(
                db_session,
                tenant,
                employee,
                contract,
                month,
                gross_wage=Decimal("2000.00"),
                sp_employee_total=Decimal("188.00"),
                zp_employee=Decimal("100.00"),
                nczd_applied=Decimal("400.00"),  # less than full monthly NČZD
                tax_after_bonus=Decimal("249.76"),  # higher advances
            )

        settlements = calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)

        s = settlements[0]
        # Monthly advances were higher because less NČZD was applied monthly
        # Annual recalc with full NČZD → lower tax → positive settlement
        assert s.settlement_amount > Decimal("0")


# ---------------------------------------------------------------------------
# Get Settlements Tests
# ---------------------------------------------------------------------------


class TestGetSettlements:
    """Test retrieving annual settlements."""

    def test_get_settlements_for_year(self, db_session: Session):
        """Test retrieving settlements for a specific year."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)

        results = get_settlements_for_year(db_session, tenant_id=tenant.id, year=2026)
        assert len(results) == 1

    def test_get_settlements_empty(self, db_session: Session):
        """Test retrieving settlements when none exist."""
        tenant = _create_tenant(db_session)

        results = get_settlements_for_year(db_session, tenant_id=tenant.id, year=2026)
        assert results == []


# ---------------------------------------------------------------------------
# PDF Generation Tests
# ---------------------------------------------------------------------------


class TestIncomeCertificatePdf:
    """Test income certificate PDF generation."""

    def test_generate_pdf(self, db_session: Session):
        """Test successful PDF generation."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)

        pdf_bytes = generate_income_certificate_pdf(
            db_session,
            tenant_id=tenant.id,
            employee_id=employee.id,
            year=2026,
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF magic bytes
        assert pdf_bytes[:4] == b"%PDF"

    def test_generate_pdf_no_settlement(self, db_session: Session):
        """Test PDF generation fails when no settlement exists."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)

        with pytest.raises(ValueError, match="not found"):
            generate_income_certificate_pdf(
                db_session,
                tenant_id=tenant.id,
                employee_id=employee.id,
                year=2026,
            )

    def test_generate_pdf_employee_not_found(self, db_session: Session):
        """Test PDF generation fails for non-existent employee."""
        tenant = _create_tenant(db_session)
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError):
            generate_income_certificate_pdf(
                db_session,
                tenant_id=tenant.id,
                employee_id=fake_id,
                year=2026,
            )


# ---------------------------------------------------------------------------
# Annual Tax Report Tests
# ---------------------------------------------------------------------------


class TestAnnualTaxReport:
    """Test annual tax report summary generation."""

    def test_generate_report_summary(self, db_session: Session):
        """Test generating annual tax report summary."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)

        report = generate_annual_tax_report_summary(db_session, tenant_id=tenant.id, year=2026)

        assert report["year"] == 2026
        assert report["total_employees"] == 1
        assert report["total_gross_wages"] == Decimal("24000.00")
        assert report["report_generated"] is True

    def test_generate_report_no_settlements(self, db_session: Session):
        """Test report fails when no settlements exist."""
        tenant = _create_tenant(db_session)

        with pytest.raises(ValueError, match="No annual settlements found"):
            generate_annual_tax_report_summary(db_session, tenant_id=tenant.id, year=2026)


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------


class TestAnnualEndpoints:
    """Test annual processing API endpoints."""

    def test_calculate_settlement_endpoint(self, client, db_session: Session):
        """Test POST /api/v1/annual/{year}/tax-settlement."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        response = client.post(
            "/api/v1/annual/2026/tax-settlement",
            json={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2026
        assert data["total_employees"] == 1
        assert len(data["settlements"]) == 1

    def test_calculate_settlement_invalid_year(self, client, db_session: Session):
        """Test settlement endpoint rejects invalid year."""
        tenant = _create_tenant(db_session)

        response = client.post(
            "/api/v1/annual/1999/tax-settlement",
            json={"tenant_id": str(tenant.id)},
        )
        assert response.status_code == 422

    def test_income_certificate_endpoint(self, client, db_session: Session):
        """Test GET /api/v1/annual/{year}/income-certificate/{employee_id}/pdf."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        # First calculate settlement
        client.post(
            "/api/v1/annual/2026/tax-settlement",
            json={"tenant_id": str(tenant.id)},
        )

        # Then download certificate
        response = client.get(
            f"/api/v1/annual/2026/income-certificate/{employee.id}/pdf",
            params={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert b"%PDF" in response.content

    def test_income_certificate_not_found(self, client, db_session: Session):
        """Test certificate endpoint returns 404 when no settlement."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)

        response = client.get(
            f"/api/v1/annual/2026/income-certificate/{employee.id}/pdf",
            params={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 404

    def test_tax_report_endpoint(self, client, db_session: Session):
        """Test POST /api/v1/annual/{year}/tax-report."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        # Calculate settlement first
        client.post(
            "/api/v1/annual/2026/tax-settlement",
            json={"tenant_id": str(tenant.id)},
        )

        # Generate report
        response = client.post(
            "/api/v1/annual/2026/tax-report",
            json={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2026
        assert data["total_employees"] == 1
        assert data["report_generated"] is True

    def test_tax_report_no_settlements(self, client, db_session: Session):
        """Test report endpoint returns 400 when no settlements."""
        tenant = _create_tenant(db_session)

        response = client.post(
            "/api/v1/annual/2026/tax-report",
            json={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 400

    def test_list_settlements_endpoint(self, client, db_session: Session):
        """Test GET /api/v1/annual/{year}/settlements."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        # Calculate settlement
        client.post(
            "/api/v1/annual/2026/tax-settlement",
            json={"tenant_id": str(tenant.id)},
        )

        # List settlements
        response = client.get(
            "/api/v1/annual/2026/settlements",
            params={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2026
        assert data["total_employees"] == 1
        assert len(data["settlements"]) == 1

    def test_list_settlements_empty(self, client, db_session: Session):
        """Test list settlements when none exist."""
        tenant = _create_tenant(db_session)

        response = client.get(
            "/api/v1/annual/2026/settlements",
            params={"tenant_id": str(tenant.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_employees"] == 0
        assert data["settlements"] == []

    def test_approve_settlement_endpoint(self, client, db_session: Session):
        """Test POST /api/v1/annual/{year}/settlements/{id}/approve."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        # Calculate settlement
        calc_resp = client.post(
            "/api/v1/annual/2026/tax-settlement",
            json={"tenant_id": str(tenant.id)},
        )
        settlement_id = calc_resp.json()["settlements"][0]["id"]
        approver_id = str(uuid.uuid4())

        # Approve
        response = client.post(
            f"/api/v1/annual/2026/settlements/{settlement_id}/approve",
            json={
                "tenant_id": str(tenant.id),
                "approved_by": approver_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approved_by"] == approver_id

    def test_approve_settlement_not_found(self, client, db_session: Session):
        """Test approve returns 404 for non-existent settlement."""
        tenant = _create_tenant(db_session)
        fake_id = str(uuid.uuid4())

        response = client.post(
            f"/api/v1/annual/2026/settlements/{fake_id}/approve",
            json={
                "tenant_id": str(tenant.id),
                "approved_by": str(uuid.uuid4()),
            },
        )

        assert response.status_code == 404

    def test_approve_settlement_already_approved(self, client, db_session: Session):
        """Test approve returns 409 when settlement already approved."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        # Calculate settlement
        calc_resp = client.post(
            "/api/v1/annual/2026/tax-settlement",
            json={"tenant_id": str(tenant.id)},
        )
        settlement_id = calc_resp.json()["settlements"][0]["id"]

        # First approval — should succeed
        client.post(
            f"/api/v1/annual/2026/settlements/{settlement_id}/approve",
            json={
                "tenant_id": str(tenant.id),
                "approved_by": str(uuid.uuid4()),
            },
        )

        # Second approval — should fail (invalid state transition → 409)
        response = client.post(
            f"/api/v1/annual/2026/settlements/{settlement_id}/approve",
            json={
                "tenant_id": str(tenant.id),
                "approved_by": str(uuid.uuid4()),
            },
        )

        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Approve Service Tests
# ---------------------------------------------------------------------------


class TestApproveSettlement:
    """Test annual settlement approval service."""

    def test_approve_calculated_settlement(self, db_session: Session):
        """Test approving a settlement in 'calculated' status."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        settlements = calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)
        settlement = settlements[0]
        approver_id = uuid.uuid4()

        result = approve_settlement(
            db_session,
            settlement_id=settlement.id,
            tenant_id=tenant.id,
            approved_by=approver_id,
        )

        assert result.status == "approved"
        assert result.approved_by == approver_id
        assert result.approved_at is not None

    def test_approve_nonexistent_settlement(self, db_session: Session):
        """Test approving a non-existent settlement raises ValueError."""
        tenant = _create_tenant(db_session)

        with pytest.raises(ValueError, match="not found"):
            approve_settlement(
                db_session,
                settlement_id=uuid.uuid4(),
                tenant_id=tenant.id,
                approved_by=uuid.uuid4(),
            )

    def test_approve_already_approved(self, db_session: Session):
        """Test re-approving raises ValueError."""
        tenant = _create_tenant(db_session)
        employee = _create_employee(db_session, tenant)
        contract = _create_contract(db_session, employee, tenant)

        for month in range(1, 13):
            _create_monthly_payroll(db_session, tenant, employee, contract, month)

        settlements = calculate_annual_settlement(db_session, tenant_id=tenant.id, year=2026)
        settlement = settlements[0]

        # First approval
        approve_settlement(
            db_session,
            settlement_id=settlement.id,
            tenant_id=tenant.id,
            approved_by=uuid.uuid4(),
        )

        # Second approval should fail
        with pytest.raises(ValueError, match="cannot be approved"):
            approve_settlement(
                db_session,
                settlement_id=settlement.id,
                tenant_id=tenant.id,
                approved_by=uuid.uuid4(),
            )
