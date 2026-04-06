"""Tests for PaySlip API router.

Covers all CRUD endpoints:
  GET    /api/v1/pay-slips         (list, paginated)
  GET    /api/v1/pay-slips/{id}    (detail)
  POST   /api/v1/pay-slips         (create)
  PUT    /api/v1/pay-slips/{id}    (update)
  DELETE /api/v1/pay-slips/{id}    (delete)
"""

import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.payroll import Payroll
from app.models.tenant import Tenant

BASE_URL = "/api/v1/pay-slips"

# Minimal payroll amounts for creating a valid payroll record
_PAYROLL_AMOUNTS = {
    "base_wage": Decimal("2500.00"),
    "overtime_hours": Decimal("0"),
    "overtime_amount": Decimal("0"),
    "bonus_amount": Decimal("0"),
    "supplement_amount": Decimal("0"),
    "gross_wage": Decimal("2500.00"),
    "sp_assessment_base": Decimal("2500.00"),
    "sp_nemocenske": Decimal("35.00"),
    "sp_starobne": Decimal("100.00"),
    "sp_invalidne": Decimal("75.00"),
    "sp_nezamestnanost": Decimal("25.00"),
    "sp_employee_total": Decimal("235.00"),
    "zp_assessment_base": Decimal("2500.00"),
    "zp_employee": Decimal("100.00"),
    "partial_tax_base": Decimal("2165.00"),
    "nczd_applied": Decimal("457.89"),
    "tax_base": Decimal("1707.11"),
    "tax_advance": Decimal("323.35"),
    "child_bonus": Decimal("0"),
    "tax_after_bonus": Decimal("323.35"),
    "net_wage": Decimal("1841.65"),
    "sp_employer_nemocenske": Decimal("35.00"),
    "sp_employer_starobne": Decimal("350.00"),
    "sp_employer_invalidne": Decimal("75.00"),
    "sp_employer_nezamestnanost": Decimal("25.00"),
    "sp_employer_garancne": Decimal("6.25"),
    "sp_employer_rezervny": Decimal("119.25"),
    "sp_employer_kurzarbeit": Decimal("15.00"),
    "sp_employer_urazove": Decimal("20.00"),
    "sp_employer_total": Decimal("645.50"),
    "zp_employer": Decimal("250.00"),
    "total_employer_cost": Decimal("3395.50"),
    "pillar2_amount": Decimal("0"),
}


def _setup_payroll(db_session: Session) -> tuple[str, str, str]:
    """Create tenant + insurer + employee + contract + payroll, return (tenant_id, employee_id, payroll_id)."""
    tenant = Tenant(
        name="Test s.r.o.",
        ico="12345678",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        address_country="SK",
        bank_iban="SK8975000000000012345678",
        schema_name="tenant_test_ps",
    )
    db_session.add(tenant)
    db_session.flush()

    insurer = HealthInsurer(code="25", name="VšZP", iban="SK0000000000000000000025")
    db_session.add(insurer)
    db_session.flush()

    employee = Employee(
        tenant_id=tenant.id,
        employee_number="EMP001",
        first_name="Ján",
        last_name="Novák",
        birth_date=date(1990, 5, 15),
        birth_number="9005150001",
        gender="M",
        nationality="SK",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        address_country="SK",
        bank_iban="SK8975000000000012345678",
        health_insurer_id=insurer.id,
        tax_declaration_type="standard",
        nczd_applied=True,
        pillar2_saver=False,
        is_disabled=False,
        status="active",
        hire_date=date(2024, 1, 15),
    )
    db_session.add(employee)
    db_session.flush()

    contract = Contract(
        tenant_id=tenant.id,
        employee_id=employee.id,
        contract_number="PZ-2024-001",
        contract_type="permanent",
        job_title="Softvérový inžinier",
        wage_type="monthly",
        base_wage=Decimal("2500.00"),
        hours_per_week=Decimal("40.0"),
        start_date=date(2024, 1, 15),
    )
    db_session.add(contract)
    db_session.flush()

    payroll = Payroll(
        tenant_id=tenant.id,
        employee_id=employee.id,
        contract_id=contract.id,
        period_year=2025,
        period_month=1,
        status="draft",
        **_PAYROLL_AMOUNTS,
    )
    db_session.add(payroll)
    db_session.flush()

    return str(tenant.id), str(employee.id), str(payroll.id)


def _pay_slip_payload(tenant_id: str, employee_id: str, payroll_id: str, **overrides) -> dict:
    defaults = {
        "tenant_id": tenant_id,
        "payroll_id": payroll_id,
        "employee_id": employee_id,
        "period_year": 2025,
        "period_month": 1,
        "pdf_path": "/data/payslips/2025/01/EMP001.pdf",
        "file_size_bytes": 52480,
    }
    defaults.update(overrides)
    return defaults


# ── LIST ───────────────────────────────────────────────────────────────


class TestListPaySlips:
    def test_empty_list(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient, db_session: Session):
        tid, eid, pid = _setup_payroll(db_session)
        client.post(BASE_URL, json=_pay_slip_payload(tid, eid, pid))
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_pagination(self, client: TestClient, db_session: Session):
        tid, eid, pid = _setup_payroll(db_session)
        # create_pay_slip checks (tenant_id, payroll_id) uniqueness,
        # so we need separate payroll records for each pay slip
        tenant = db_session.get(Tenant, uuid.UUID(tid))
        employee = db_session.get(Employee, uuid.UUID(eid))
        contract_id = db_session.execute(select(Contract.id).where(Contract.employee_id == employee.id)).scalar_one()
        payroll_ids = [pid]
        for m in (2, 3):
            p = Payroll(
                tenant_id=tenant.id,
                employee_id=employee.id,
                contract_id=contract_id,
                period_year=2025,
                period_month=m,
                status="draft",
                **_PAYROLL_AMOUNTS,
            )
            db_session.add(p)
            db_session.flush()
            payroll_ids.append(str(p.id))

        for i, pr_id in enumerate(payroll_ids):
            client.post(
                BASE_URL,
                json=_pay_slip_payload(tid, eid, pr_id, period_month=i + 1, pdf_path=f"/data/{i}.pdf"),
            )
        resp = client.get(BASE_URL, params={"skip": 0, "limit": 2})
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    def test_filter_by_tenant(self, client: TestClient, db_session: Session):
        tid, eid, pid = _setup_payroll(db_session)
        client.post(BASE_URL, json=_pay_slip_payload(tid, eid, pid))

        resp = client.get(BASE_URL, params={"tenant_id": tid})
        assert resp.json()["total"] == 1

        resp = client.get(BASE_URL, params={"tenant_id": str(uuid.uuid4())})
        assert resp.json()["total"] == 0


# ── GET DETAIL ─────────────────────────────────────────────────────────


class TestGetPaySlip:
    def test_get_existing(self, client: TestClient, db_session: Session):
        tid, eid, pid = _setup_payroll(db_session)
        created = client.post(BASE_URL, json=_pay_slip_payload(tid, eid, pid)).json()
        resp = client.get(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["period_year"] == 2025

    def test_get_not_found(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/{uuid.uuid4()}")
        assert resp.status_code == 404


# ── CREATE ─────────────────────────────────────────────────────────────


class TestCreatePaySlip:
    def test_create_success(self, client: TestClient, db_session: Session):
        tid, eid, pid = _setup_payroll(db_session)
        resp = client.post(BASE_URL, json=_pay_slip_payload(tid, eid, pid))
        assert resp.status_code == 201
        data = resp.json()
        assert data["period_year"] == 2025
        assert data["period_month"] == 1
        assert data["pdf_path"] == "/data/payslips/2025/01/EMP001.pdf"
        assert data["file_size_bytes"] == 52480
        assert "id" in data
        assert "created_at" in data

    def test_create_missing_required(self, client: TestClient):
        resp = client.post(BASE_URL, json={"period_year": 2025})
        assert resp.status_code == 422


# ── UPDATE ─────────────────────────────────────────────────────────────


class TestUpdatePaySlip:
    def test_update_success(self, client: TestClient, db_session: Session):
        tid, eid, pid = _setup_payroll(db_session)
        created = client.post(BASE_URL, json=_pay_slip_payload(tid, eid, pid)).json()
        resp = client.put(
            f"{BASE_URL}/{created['id']}",
            json={"pdf_path": "/data/updated.pdf", "file_size_bytes": 99999},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pdf_path"] == "/data/updated.pdf"
        assert data["file_size_bytes"] == 99999

    def test_update_not_found(self, client: TestClient):
        resp = client.put(f"{BASE_URL}/{uuid.uuid4()}", json={"pdf_path": "/x.pdf"})
        assert resp.status_code == 404


# ── DELETE ─────────────────────────────────────────────────────────────


class TestDeletePaySlip:
    def test_delete_success(self, client: TestClient, db_session: Session):
        tid, eid, pid = _setup_payroll(db_session)
        created = client.post(BASE_URL, json=_pay_slip_payload(tid, eid, pid)).json()
        resp = client.delete(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 204
        assert client.get(f"{BASE_URL}/{created['id']}").status_code == 404

    def test_delete_not_found(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/{uuid.uuid4()}")
        assert resp.status_code == 404
