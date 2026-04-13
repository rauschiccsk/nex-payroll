"""Tests for SEPA XML router endpoints."""

from decimal import Decimal
from xml.etree import ElementTree

from app.models.payment_order import PaymentOrder
from app.models.tenant import Tenant

NS = {"sepa": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tenant(db_session, **overrides) -> Tenant:
    defaults = {
        "name": "Router Test s.r.o.",
        "ico": "87654321",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "bank_bic": "CEKOSKBX",
        "schema_name": "tenant_router_sepa",
    }
    defaults.update(overrides)
    tenant = Tenant(**defaults)
    db_session.add(tenant)
    db_session.flush()
    return tenant


def _make_order(db_session, tenant_id, **overrides) -> PaymentOrder:
    defaults = {
        "tenant_id": tenant_id,
        "period_year": 2025,
        "period_month": 3,
        "payment_type": "sp",
        "recipient_name": "Sociálna poisťovňa",
        "recipient_iban": "SK3112000000198742637541",
        "recipient_bic": "TATRSKBX",
        "amount": Decimal("1000.00"),
        "variable_symbol": "1234567890",
        "constant_symbol": "0558",
        "reference": "SP-2025-03",
        "status": "pending",
    }
    defaults.update(overrides)
    order = PaymentOrder(**defaults)
    db_session.add(order)
    db_session.flush()
    return order


# ---------------------------------------------------------------------------
# PUT /payments/{id}/status
# ---------------------------------------------------------------------------


class TestUpdatePaymentOrderStatus:
    """Tests for PUT /api/v1/payments/{id}/status."""

    def test_update_status_success(self, client, db_session):
        tenant = _make_tenant(db_session)
        order = _make_order(db_session, tenant.id)

        resp = client.put(
            f"/api/v1/payments/{order.id}/status",
            json={"status": "exported"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "exported"
        assert data["id"] == str(order.id)

    def test_update_status_to_paid(self, client, db_session):
        tenant = _make_tenant(db_session)
        order = _make_order(db_session, tenant.id, status="exported")

        resp = client.put(
            f"/api/v1/payments/{order.id}/status",
            json={"status": "paid"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"

    def test_update_status_invalid(self, client, db_session):
        tenant = _make_tenant(db_session)
        order = _make_order(db_session, tenant.id)

        resp = client.put(
            f"/api/v1/payments/{order.id}/status",
            json={"status": "invalid_status"},
        )

        assert resp.status_code == 422

    def test_update_status_not_found(self, client, db_session):
        resp = client.put(
            "/api/v1/payments/00000000-0000-0000-0000-000000000001/status",
            json={"status": "exported"},
        )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /payments/{year}/{month}
# ---------------------------------------------------------------------------


class TestListPaymentOrdersByPeriod:
    """Tests for GET /api/v1/payments/{year}/{month}."""

    def test_list_by_period(self, client, db_session):
        tenant = _make_tenant(db_session)
        _make_order(db_session, tenant.id, period_year=2025, period_month=3)
        _make_order(
            db_session,
            tenant.id,
            period_year=2025,
            period_month=4,
            reference="OTHER",
        )

        resp = client.get(
            f"/api/v1/payments/2025/3?tenant_id={tenant.id}",
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["period_month"] == 3

    def test_list_by_period_invalid_month(self, client, db_session):
        tenant = _make_tenant(db_session)

        resp = client.get(
            f"/api/v1/payments/2025/13?tenant_id={tenant.id}",
        )

        assert resp.status_code == 422

    def test_list_by_period_empty(self, client, db_session):
        tenant = _make_tenant(db_session)

        resp = client.get(
            f"/api/v1/payments/2025/6?tenant_id={tenant.id}",
        )

        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /payments/{year}/{month}/sepa-xml (preview)
# ---------------------------------------------------------------------------


class TestDownloadSepaXml:
    """Tests for GET /api/v1/payments/{year}/{month}/sepa-xml."""

    def test_download_preview_xml(self, client, db_session):
        tenant = _make_tenant(db_session)
        order = _make_order(db_session, tenant.id, period_year=2025, period_month=3)

        resp = client.get(
            f"/api/v1/payments/2025/3/sepa-xml?tenant_id={tenant.id}",
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/xml"
        assert "SEPA-2025-03.xml" in resp.headers.get("content-disposition", "")

        # Verify XML content
        root = ElementTree.fromstring(resp.content)
        assert "pain.001.001.03" in root.tag

        # Order should remain pending (preview mode)
        db_session.refresh(order)
        assert order.status == "pending"

    def test_download_no_orders_returns_error(self, client, db_session):
        tenant = _make_tenant(db_session)

        resp = client.get(
            f"/api/v1/payments/2025/3/sepa-xml?tenant_id={tenant.id}",
        )

        # No orders → ValueError → mapped to 409 (business-rule)
        assert resp.status_code == 409

    def test_download_invalid_month(self, client, db_session):
        tenant = _make_tenant(db_session)

        resp = client.get(
            f"/api/v1/payments/2025/0/sepa-xml?tenant_id={tenant.id}",
        )

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /payments/{year}/{month}/sepa-xml (export)
# ---------------------------------------------------------------------------


class TestGenerateSepaXml:
    """Tests for POST /api/v1/payments/{year}/{month}/sepa-xml."""

    def test_export_generates_xml_and_marks_exported(self, client, db_session):
        tenant = _make_tenant(db_session)
        order = _make_order(db_session, tenant.id, period_year=2025, period_month=3)
        assert order.status == "pending"

        resp = client.post(
            f"/api/v1/payments/2025/3/sepa-xml?tenant_id={tenant.id}",
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/xml"
        assert "SEPA-2025-03.xml" in resp.headers.get("content-disposition", "")

        # Verify valid XML
        root = ElementTree.fromstring(resp.content)
        assert "pain.001.001.03" in root.tag

        # Order status should now be exported
        db_session.expire_all()
        db_session.refresh(order)
        assert order.status == "exported"

    def test_export_no_pending_orders(self, client, db_session):
        tenant = _make_tenant(db_session)
        # Only exported orders — POST should fail
        _make_order(
            db_session,
            tenant.id,
            period_year=2025,
            period_month=3,
            status="exported",
        )

        resp = client.post(
            f"/api/v1/payments/2025/3/sepa-xml?tenant_id={tenant.id}",
        )

        assert resp.status_code == 409

    def test_export_invalid_month(self, client, db_session):
        tenant = _make_tenant(db_session)

        resp = client.post(
            f"/api/v1/payments/2025/13/sepa-xml?tenant_id={tenant.id}",
        )

        assert resp.status_code == 422

    def test_export_multiple_orders(self, client, db_session):
        tenant = _make_tenant(db_session)
        o1 = _make_order(
            db_session,
            tenant.id,
            period_year=2025,
            period_month=3,
            amount=Decimal("1000.00"),
            reference="R1",
        )
        o2 = _make_order(
            db_session,
            tenant.id,
            period_year=2025,
            period_month=3,
            payment_type="tax",
            recipient_name="Daňový úrad",
            recipient_iban="SK6807200002891987426353",
            amount=Decimal("500.00"),
            reference="R2",
        )

        resp = client.post(
            f"/api/v1/payments/2025/3/sepa-xml?tenant_id={tenant.id}",
        )

        assert resp.status_code == 200

        root = ElementTree.fromstring(resp.content)
        nb_txs = root.find(".//sepa:GrpHdr/sepa:NbOfTxs", NS)
        assert nb_txs.text == "2"
        ctrl_sum = root.find(".//sepa:GrpHdr/sepa:CtrlSum", NS)
        assert ctrl_sum.text == "1500.00"

        # Both orders marked as exported
        db_session.expire_all()
        db_session.refresh(o1)
        db_session.refresh(o2)
        assert o1.status == "exported"
        assert o2.status == "exported"
