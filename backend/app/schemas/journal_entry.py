"""Pydantic v2 schemas for JournalEntry entity.

Used for API response serialisation and integration request validation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# JournalEntryRead — single entry line
# ---------------------------------------------------------------------------


class JournalEntryRead(BaseModel):
    """Schema for returning a journal entry in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    payroll_id: UUID
    period_year: int
    period_month: int
    entry_date: date
    account_code: str
    account_name: str
    entry_type: Literal["debit", "credit"]
    amount: Decimal
    description: str
    sync_batch_id: str | None
    synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Ledger sync request/response
# ---------------------------------------------------------------------------


class LedgerSyncRequest(BaseModel):
    """Request to sync payroll journal entries to NEX Ledger."""

    tenant_id: UUID = Field(..., description="Tenant ID")


class JournalEntrySummary(BaseModel):
    """Summary of a single journal entry for sync response."""

    account_code: str
    account_name: str
    entry_type: Literal["debit", "credit"]
    amount: Decimal
    description: str


class LedgerSyncResponse(BaseModel):
    """Response after syncing journal entries to NEX Ledger."""

    period_year: int
    period_month: int
    tenant_id: str
    sync_batch_id: str
    entries_created: int
    total_debit: Decimal
    total_credit: Decimal
    payrolls_synced: int
    entries: list[JournalEntrySummary]


class LedgerSyncStatusResponse(BaseModel):
    """Status of ledger sync for a period."""

    period_year: int
    period_month: int
    tenant_id: str
    total_payrolls: int
    synced_payrolls: int
    pending_payrolls: int
    error_payrolls: int
    not_synced_payrolls: int
    total_journal_entries: int
    total_debit: Decimal
    total_credit: Decimal
    last_sync_at: datetime | None
    is_balanced: bool
