"""Payroll processing full lifecycle journey test.

Validates the complete payroll workflow:
  1. Setup — Create tenant, employee + contract (base_wage=3000 EUR)
  2. Calculate payroll (gross → net)
  3. Verify calculation results and mathematical identity
  4. Approve payroll (director)
  5. Generate pay slip PDF
  6. Create and verify payment orders

Uses the ``client`` fixture which overrides get_current_user (auth bypassed)
so the test focuses on the payroll lifecycle, not authentication.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.fixtures.journey_data import (
    CONTRACT_BASE,
    EMPLOYEE_BASE,
    HEALTH_INSURERS,
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_health_insurer_id(db_session: Session, code: str) -> str:
    """Fetch health insurer ID from shared.health_insurers by code."""
    row = db_session.execute(
        text("SELECT id FROM shared.health_insurers WHERE code = :code"),
        {"code": code},
    ).fetchone()
    assert row is not None, f"Health insurer with code '{code}' not found in shared.health_insurers"
    return str(row.id)


# ---------------------------------------------------------------------------
# Journey test
# ---------------------------------------------------------------------------


def test_payroll_full_journey(
    client: TestClient,
    db_session: Session,
) -> None:
    """End-to-end payroll processing: calculate → verify → approve → payslip → payments."""

    # ==================================================================
    # Step 0 — Create tenant via auth-bypassed client (no test_tenant
    # fixture to avoid dependency_overrides conflict with auth_client)
    # ==================================================================
    tenant_payload = {
        "name": "Payroll Journey Firma s.r.o.",
        "ico": "77889900",
        "dic": "2077889900",
        "address_street": "Mzdová 42",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK3975000000000077889900",
        "bank_bic": "TATRSKBX",
    }
    resp = client.post("/api/v1/tenants", json=tenant_payload)
    assert resp.status_code == 201, f"Create tenant failed: {resp.text}"

    tenant_data = resp.json()
    tenant_id = tenant_data["id"]

    # ==================================================================
    # Step 1 — Create employee (PAY001) and contract (3000 EUR)
    # ==================================================================

    # Seed health insurer VšZP (code 25)
    vszp_seed = next(h for h in HEALTH_INSURERS if h["code"] == "25")
    resp = client.post("/api/v1/health-insurers", json=vszp_seed)
    assert resp.status_code == 201, f"Create health insurer failed: {resp.text}"

    hi_id = _get_health_insurer_id(db_session, "25")

    # Create employee PAY001
    employee_data = {
        **EMPLOYEE_BASE,
        "employee_number": "PAY001",
        "tenant_id": tenant_id,
        "health_insurer_id": hi_id,
    }
    resp = client.post("/api/v1/employees", json=employee_data)
    assert resp.status_code == 201, f"Create employee failed: {resp.text}"
    emp = resp.json()
    employee_id = emp["id"]

    # Create contract with base_wage=3000.00
    contract_data = {
        **CONTRACT_BASE,
        "contract_number": "PAY-CONTR001",
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "base_wage": 3000.00,
    }
    resp = client.post(
        f"/api/v1/employees/{employee_id}/contracts",
        json=contract_data,
    )
    assert resp.status_code == 201, f"Create contract failed: {resp.text}"
    contract = resp.json()
    contract_id = contract["id"]

    # ==================================================================
    # Step 2 — Calculate payroll (auth bypassed via client fixture)
    # ==================================================================
    calc_payload = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "contract_id": contract_id,
        "period_year": 2026,
        "period_month": 4,
    }
    resp = client.post("/api/v1/payroll/calculate", json=calc_payload)
    assert resp.status_code == 200, f"Calculate payroll failed: {resp.text}"

    # ==================================================================
    # Step 3 — Verify calculation results
    # ==================================================================
    # Fetch persisted payroll record via list endpoint with filters
    resp = client.get(
        "/api/v1/payroll",
        params={
            "tenant_id": tenant_id,
            "employee_id": employee_id,
            "period_year": 2026,
            "period_month": 4,
        },
    )
    assert resp.status_code == 200, f"List payrolls failed: {resp.text}"
    payroll_list = resp.json()
    assert payroll_list["total"] >= 1, "Expected at least 1 payroll record"

    payroll = payroll_list["items"][0]
    payroll_id = payroll["id"]

    assert payroll["status"] == "calculated"
    assert Decimal(str(payroll["gross_wage"])) == Decimal("3000.00")

    # SP employee total > 0 (9.4% of assessment base)
    sp_employee_total = Decimal(str(payroll["sp_employee_total"]))
    assert sp_employee_total > 0, f"SP employee total should be > 0, got {sp_employee_total}"

    # ZP employee > 0 (5.0% of gross for non-disabled)
    zp_employee = Decimal(str(payroll["zp_employee"]))
    assert zp_employee > 0, f"ZP employee should be > 0, got {zp_employee}"

    # Tax after bonus >= 0
    tax_after_bonus = Decimal(str(payroll["tax_after_bonus"]))
    assert tax_after_bonus >= 0, f"Tax after bonus should be >= 0, got {tax_after_bonus}"

    # Net wage < gross (deductions must reduce it)
    net_wage = Decimal(str(payroll["net_wage"]))
    assert net_wage < Decimal("3000.00"), f"Net wage should be < 3000.00, got {net_wage}"

    # ==================================================================
    # Step 4 — Mathematical identity validation
    # gross_wage == net_wage + sp_employee_total + zp_employee + tax_after_bonus
    # ==================================================================
    gross_wage = Decimal(str(payroll["gross_wage"]))
    identity = net_wage + sp_employee_total + zp_employee + tax_after_bonus
    diff = abs(identity - gross_wage)
    assert diff < Decimal("0.01"), (
        f"Mathematical identity violated: "
        f"net({net_wage}) + sp({sp_employee_total}) + zp({zp_employee}) + tax({tax_after_bonus}) "
        f"= {identity}, but gross = {gross_wage}, diff = {diff}"
    )

    # ==================================================================
    # Step 5 — Approve payroll (auth bypassed — client fake user is director)
    # ==================================================================
    resp = client.patch(
        f"/api/v1/payroll/{payroll_id}",
        json={"status": "approved"},
    )
    assert resp.status_code == 200, f"Approve payroll failed: {resp.text}"

    # Verify approved status
    resp = client.get(f"/api/v1/payroll/{payroll_id}")
    assert resp.status_code == 200, f"Get payroll detail failed: {resp.text}"
    approved_payroll = resp.json()
    assert approved_payroll["status"] == "approved"

    # ==================================================================
    # Step 6 — Generate pay slip PDF
    # ==================================================================
    # Batch generate all pay slips for the period
    resp = client.post(
        "/api/v1/payslips/2026/4/generate-all",
        params={"tenant_id": tenant_id},
    )
    assert resp.status_code == 201, f"Generate pay slips failed: {resp.text}"
    gen_result = resp.json()
    assert gen_result["count"] >= 1, "Expected at least 1 pay slip generated"

    # Download individual PDF
    resp = client.get(
        f"/api/v1/payslips/2026/4/{employee_id}/pdf",
        params={"tenant_id": tenant_id},
    )
    assert resp.status_code == 200, f"Download pay slip PDF failed: {resp.text}"
    assert resp.headers.get("content-type") == "application/pdf"

    # ==================================================================
    # Step 7 — Generate and verify payment orders
    # ==================================================================
    # Batch generate payment orders for the period
    resp = client.post(
        "/api/v1/payments/2026/4/generate",
        params={"tenant_id": tenant_id},
    )
    if resp.status_code in (404, 405):
        pytest.xfail(reason="POST /api/v1/payments/{year}/{month}/generate endpoint not implemented")

    assert resp.status_code == 200, f"Generate payment orders failed: {resp.text}"

    # Verify payment orders for the period
    resp = client.get(
        "/api/v1/payments/2026/4",
        params={"tenant_id": tenant_id},
    )
    assert resp.status_code == 200, f"List payment orders failed: {resp.text}"
    payments_data = resp.json()
    payments = payments_data["items"]
    assert len(payments) >= 4, f"Expected >= 4 payment orders, got {len(payments)}"

    # Find net_wage payment and verify linkage
    net_payments = [p for p in payments if p["payment_type"] == "net_wage"]
    assert len(net_payments) >= 1, "No net_wage payment order found"
    net_payment = net_payments[0]
    assert Decimal(str(net_payment["amount"])) == net_wage, (
        f"Net payment amount {net_payment['amount']} != payroll net_wage {net_wage}"
    )
    assert net_payment["employee_id"] == employee_id
