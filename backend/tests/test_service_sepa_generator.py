"""Tests for SEPA XML generator service (pain.001.001.03)."""

from datetime import date
from decimal import Decimal
from uuid import uuid4
from xml.etree import ElementTree

import pytest

from app.models.payment_order import PaymentOrder
from app.models.tenant import Tenant
from app.services.sepa_generator import (
    _amount_to_cents,
    _build_description,
    _build_end_to_end_id,
    generate_sepa_xml,
    generate_sepa_xml_preview,
)

# SEPA XML namespace
NS = {"sepa": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tenant(db_session, **overrides) -> Tenant:
    defaults = {
        "name": "Test s.r.o.",
        "ico": "12345678",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "bank_bic": "CEKOSKBX",
        "schema_name": "tenant_sepa_12345678",
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
        "period_month": 1,
        "payment_type": "sp",
        "recipient_name": "Sociálna poisťovňa",
        "recipient_iban": "SK3112000000198742637541",
        "recipient_bic": "TATRSKBX",
        "amount": Decimal("1850.00"),
        "variable_symbol": "1234567890",
        "specific_symbol": None,
        "constant_symbol": "0558",
        "reference": "PAYROLL-2025-01-SP",
        "status": "pending",
        "employee_id": None,
        "health_insurer_id": None,
    }
    defaults.update(overrides)
    order = PaymentOrder(**defaults)
    db_session.add(order)
    db_session.flush()
    return order


# ---------------------------------------------------------------------------
# Unit tests — helper functions
# ---------------------------------------------------------------------------


class TestAmountToCents:
    """Tests for _amount_to_cents conversion."""

    def test_whole_euros(self):
        assert _amount_to_cents(Decimal("100.00")) == 10000

    def test_with_cents(self):
        assert _amount_to_cents(Decimal("1850.50")) == 185050

    def test_zero(self):
        assert _amount_to_cents(Decimal("0.00")) == 0

    def test_small_amount(self):
        assert _amount_to_cents(Decimal("0.01")) == 1

    def test_large_amount(self):
        assert _amount_to_cents(Decimal("999999999.99")) == 99999999999


class TestBuildDescription:
    """Tests for _build_description."""

    def test_with_all_symbols(self):
        order = PaymentOrder(
            payment_type="sp",
            period_year=2025,
            period_month=1,
            variable_symbol="1234567890",
            specific_symbol="0012345678",
            constant_symbol="0558",
        )
        desc = _build_description(order)
        assert "/VS1234567890" in desc
        assert "/SS0012345678" in desc
        assert "/KS0558" in desc

    def test_with_only_variable_symbol(self):
        order = PaymentOrder(
            payment_type="sp",
            period_year=2025,
            period_month=1,
            variable_symbol="1234567890",
        )
        desc = _build_description(order)
        assert desc == "/VS1234567890"

    def test_without_symbols_fallback(self):
        order = PaymentOrder(
            payment_type="tax",
            period_year=2025,
            period_month=3,
        )
        desc = _build_description(order)
        assert "tax" in desc
        assert "2025/03" in desc


class TestBuildEndToEndId:
    """Tests for _build_end_to_end_id."""

    def test_with_reference(self):
        order = PaymentOrder(reference="PAYROLL-2025-01-SP")
        assert _build_end_to_end_id(order) == "PAYROLL-2025-01-SP"

    def test_long_reference_truncated(self):
        order = PaymentOrder(reference="A" * 50)
        result = _build_end_to_end_id(order)
        assert len(result) <= 35

    def test_without_reference(self):
        order = PaymentOrder(reference=None)
        order.id = uuid4()
        result = _build_end_to_end_id(order)
        assert result.startswith("PO-")


# ---------------------------------------------------------------------------
# Integration tests — generate_sepa_xml
# ---------------------------------------------------------------------------


class TestGenerateSepaXml:
    """Tests for generate_sepa_xml (marks orders as exported)."""

    def test_generates_valid_xml(self, db_session):
        tenant = _make_tenant(db_session)
        _make_order(db_session, tenant.id)

        xml_bytes = generate_sepa_xml(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 1, 15),
        )

        assert xml_bytes is not None
        assert len(xml_bytes) > 0
        # Parse as valid XML
        root = ElementTree.fromstring(xml_bytes)
        assert root.tag == "{urn:iso:std:iso:20022:tech:xsd:pain.001.001.03}Document"

    def test_xml_contains_debtor_info(self, db_session):
        tenant = _make_tenant(db_session, name="ACME s.r.o.")
        _make_order(db_session, tenant.id)

        xml_bytes = generate_sepa_xml(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 1, 15),
        )

        root = ElementTree.fromstring(xml_bytes)
        # Check debtor name
        dbtr_nm = root.find(".//sepa:Dbtr/sepa:Nm", NS)
        assert dbtr_nm is not None
        assert dbtr_nm.text == "ACME s.r.o."

        # Check debtor IBAN
        dbtr_iban = root.find(".//sepa:DbtrAcct/sepa:Id/sepa:IBAN", NS)
        assert dbtr_iban is not None
        assert dbtr_iban.text == "SK8975000000000012345678"

    def test_xml_contains_creditor_info(self, db_session):
        tenant = _make_tenant(db_session)
        _make_order(
            db_session,
            tenant.id,
            recipient_name="Sociálna poisťovňa",
            recipient_iban="SK3112000000198742637541",
        )

        xml_bytes = generate_sepa_xml(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 1, 15),
        )

        root = ElementTree.fromstring(xml_bytes)
        cdtr_nm = root.find(".//sepa:Cdtr/sepa:Nm", NS)
        assert cdtr_nm is not None
        # sepaxml strips diacritical marks from names
        assert "poistovn" in cdtr_nm.text.lower()

        cdtr_iban = root.find(".//sepa:CdtrAcct/sepa:Id/sepa:IBAN", NS)
        assert cdtr_iban is not None
        assert cdtr_iban.text == "SK3112000000198742637541"

    def test_xml_contains_correct_amount(self, db_session):
        tenant = _make_tenant(db_session)
        _make_order(db_session, tenant.id, amount=Decimal("1850.00"))

        xml_bytes = generate_sepa_xml(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 1, 15),
        )

        root = ElementTree.fromstring(xml_bytes)
        amt = root.find(".//sepa:InstdAmt", NS)
        assert amt is not None
        assert amt.text == "1850.00"
        assert amt.attrib.get("Ccy") == "EUR"

    def test_xml_contains_end_to_end_id(self, db_session):
        tenant = _make_tenant(db_session)
        _make_order(db_session, tenant.id, reference="PAYROLL-2025-01-SP")

        xml_bytes = generate_sepa_xml(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 1, 15),
        )

        root = ElementTree.fromstring(xml_bytes)
        e2e = root.find(".//sepa:EndToEndId", NS)
        assert e2e is not None
        assert e2e.text == "PAYROLL-2025-01-SP"

    def test_xml_contains_remittance_info(self, db_session):
        tenant = _make_tenant(db_session)
        _make_order(
            db_session,
            tenant.id,
            variable_symbol="1234567890",
            constant_symbol="0558",
        )

        xml_bytes = generate_sepa_xml(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 1, 15),
        )

        root = ElementTree.fromstring(xml_bytes)
        ustrd = root.find(".//sepa:Ustrd", NS)
        assert ustrd is not None
        assert "/VS1234567890" in ustrd.text
        assert "/KS0558" in ustrd.text

    def test_marks_orders_as_exported(self, db_session):
        tenant = _make_tenant(db_session)
        order = _make_order(db_session, tenant.id)
        assert order.status == "pending"

        generate_sepa_xml(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 1, 15),
        )

        assert order.status == "exported"

    def test_multiple_orders_in_single_xml(self, db_session):
        tenant = _make_tenant(db_session)
        _make_order(
            db_session,
            tenant.id,
            payment_type="sp",
            recipient_name="Sociálna poisťovňa",
            amount=Decimal("1000.00"),
            reference="SP-2025-01",
        )
        _make_order(
            db_session,
            tenant.id,
            payment_type="tax",
            recipient_name="Daňový úrad",
            recipient_iban="SK6807200002891987426353",
            amount=Decimal("500.00"),
            reference="TAX-2025-01",
        )

        xml_bytes = generate_sepa_xml(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 1, 15),
        )

        root = ElementTree.fromstring(xml_bytes)
        # Group header should show 2 transactions
        nb_txs = root.find(".//sepa:GrpHdr/sepa:NbOfTxs", NS)
        assert nb_txs is not None
        assert nb_txs.text == "2"

        # Control sum should be 1500.00
        ctrl_sum = root.find(".//sepa:GrpHdr/sepa:CtrlSum", NS)
        assert ctrl_sum is not None
        assert ctrl_sum.text == "1500.00"

    def test_no_pending_orders_raises_value_error(self, db_session):
        tenant = _make_tenant(db_session)
        # Create an exported order — should not be picked up
        _make_order(db_session, tenant.id, status="exported")

        with pytest.raises(ValueError, match="No pending payment orders"):
            generate_sepa_xml(
                db_session,
                tenant_id=tenant.id,
                period_year=2025,
                period_month=1,
            )

    def test_tenant_not_found_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            generate_sepa_xml(
                db_session,
                tenant_id=uuid4(),
                period_year=2025,
                period_month=1,
            )

    def test_tenant_without_iban_raises_value_error(self, db_session):
        tenant = _make_tenant(
            db_session,
            bank_iban="",
            ico="99999999",
            schema_name="tenant_no_iban_99999999",
        )
        _make_order(db_session, tenant.id)

        with pytest.raises(ValueError, match="bank_iban"):
            generate_sepa_xml(
                db_session,
                tenant_id=tenant.id,
                period_year=2025,
                period_month=1,
            )

    def test_execution_date_in_xml(self, db_session):
        tenant = _make_tenant(db_session)
        _make_order(db_session, tenant.id)

        xml_bytes = generate_sepa_xml(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 2, 28),
        )

        root = ElementTree.fromstring(xml_bytes)
        exec_dt = root.find(".//sepa:ReqdExctnDt", NS)
        assert exec_dt is not None
        assert exec_dt.text == "2025-02-28"

    def test_schema_is_pain_001_001_03(self, db_session):
        tenant = _make_tenant(db_session)
        _make_order(db_session, tenant.id)

        xml_bytes = generate_sepa_xml(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 1, 15),
        )

        root = ElementTree.fromstring(xml_bytes)
        # Namespace must be pain.001.001.03
        assert "pain.001.001.03" in root.tag

    def test_only_pending_orders_included(self, db_session):
        tenant = _make_tenant(db_session)
        _make_order(
            db_session,
            tenant.id,
            status="pending",
            recipient_name="Pending One",
            amount=Decimal("100.00"),
            reference="PENDING",
        )
        _make_order(
            db_session,
            tenant.id,
            status="exported",
            recipient_name="Already Exported",
            amount=Decimal("200.00"),
            reference="EXPORTED",
        )
        _make_order(
            db_session,
            tenant.id,
            status="paid",
            recipient_name="Already Paid",
            amount=Decimal("300.00"),
            reference="PAID",
        )

        xml_bytes = generate_sepa_xml(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 1, 15),
        )

        root = ElementTree.fromstring(xml_bytes)
        nb_txs = root.find(".//sepa:GrpHdr/sepa:NbOfTxs", NS)
        assert nb_txs.text == "1"
        ctrl_sum = root.find(".//sepa:GrpHdr/sepa:CtrlSum", NS)
        assert ctrl_sum.text == "100.00"


# ---------------------------------------------------------------------------
# Integration tests — generate_sepa_xml_preview
# ---------------------------------------------------------------------------


class TestGenerateSepaXmlPreview:
    """Tests for generate_sepa_xml_preview (does NOT mark orders)."""

    def test_preview_does_not_change_status(self, db_session):
        tenant = _make_tenant(db_session)
        order = _make_order(db_session, tenant.id)
        assert order.status == "pending"

        xml_bytes = generate_sepa_xml_preview(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 1, 15),
        )

        assert xml_bytes is not None
        assert order.status == "pending"  # NOT changed

    def test_preview_includes_pending_and_exported(self, db_session):
        tenant = _make_tenant(db_session)
        _make_order(
            db_session,
            tenant.id,
            status="pending",
            amount=Decimal("100.00"),
            reference="P1",
        )
        _make_order(
            db_session,
            tenant.id,
            status="exported",
            amount=Decimal("200.00"),
            recipient_name="Exported",
            reference="E1",
        )
        _make_order(
            db_session,
            tenant.id,
            status="paid",
            amount=Decimal("300.00"),
            recipient_name="Paid",
            reference="PAID1",
        )

        xml_bytes = generate_sepa_xml_preview(
            db_session,
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            execution_date=date(2025, 1, 15),
        )

        root = ElementTree.fromstring(xml_bytes)
        nb_txs = root.find(".//sepa:GrpHdr/sepa:NbOfTxs", NS)
        # pending + exported = 2 (paid excluded)
        assert nb_txs.text == "2"

    def test_preview_no_orders_raises_value_error(self, db_session):
        tenant = _make_tenant(db_session)

        with pytest.raises(ValueError, match="No payment orders"):
            generate_sepa_xml_preview(
                db_session,
                tenant_id=tenant.id,
                period_year=2025,
                period_month=1,
            )

    def test_preview_tenant_not_found_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            generate_sepa_xml_preview(
                db_session,
                tenant_id=uuid4(),
                period_year=2025,
                period_month=1,
            )
