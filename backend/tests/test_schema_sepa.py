"""Tests for SEPA-related Pydantic schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.payment_order import PaymentOrderStatusUpdate, SepaXmlRequest


class TestPaymentOrderStatusUpdate:
    """Tests for PaymentOrderStatusUpdate schema."""

    def test_valid_status_pending(self):
        schema = PaymentOrderStatusUpdate(status="pending")
        assert schema.status == "pending"

    def test_valid_status_exported(self):
        schema = PaymentOrderStatusUpdate(status="exported")
        assert schema.status == "exported"

    def test_valid_status_paid(self):
        schema = PaymentOrderStatusUpdate(status="paid")
        assert schema.status == "paid"

    def test_invalid_status_rejects(self):
        with pytest.raises(ValidationError):
            PaymentOrderStatusUpdate(status="invalid")

    def test_status_required(self):
        with pytest.raises(ValidationError):
            PaymentOrderStatusUpdate()


class TestSepaXmlRequest:
    """Tests for SepaXmlRequest schema."""

    def test_valid_request(self):
        tid = uuid4()
        schema = SepaXmlRequest(tenant_id=tid)
        assert schema.tenant_id == tid
        assert schema.execution_date is None

    def test_tenant_id_required(self):
        with pytest.raises(ValidationError):
            SepaXmlRequest()
