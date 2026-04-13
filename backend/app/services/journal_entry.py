"""Service layer for journal entry generation and NEX Ledger integration.

Generates double-entry accounting journal entries from approved payrolls.
Uses the Slovak chart of accounts (Účtová osnova) for payroll accounting:

  521 - Mzdové náklady (Wage costs)                         DEBIT
  524 - Zákonné sociálne poistenie (Statutory social ins.)   DEBIT
  524 - Zákonné zdravotné poistenie (Statutory health ins.)  DEBIT
  331 - Zamestnanci (Employees — net wage liability)         CREDIT
  336 - Zúčtovanie s orgánmi SP (Social ins. liability)      CREDIT
  336 - Zúčtovanie s orgánmi ZP (Health ins. liability)      CREDIT
  342 - Ostatné priame dane (Income tax liability)           CREDIT

All functions are synchronous (def, not async def) per DESIGN.md.
They flush but never commit — the caller owns the transaction.
"""

import calendar
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.journal_entry import JournalEntry
from app.models.payroll import Payroll

# ---------------------------------------------------------------------------
# Account code constants — Slovak chart of accounts
# ---------------------------------------------------------------------------

ACCOUNT_521_WAGES = ("521", "Mzdové náklady")
ACCOUNT_524_SP = ("524.1", "Zákonné sociálne poistenie")
ACCOUNT_524_ZP = ("524.2", "Zákonné zdravotné poistenie")
ACCOUNT_331_EMPLOYEES = ("331", "Zamestnanci")
ACCOUNT_336_SP = ("336.1", "Zúčtovanie s orgánmi sociálneho poistenia")
ACCOUNT_336_ZP = ("336.2", "Zúčtovanie s orgánmi zdravotného poistenia")
ACCOUNT_342_TAX = ("342", "Ostatné priame dane")


def _last_day_of_month(year: int, month: int) -> date:
    """Return the last day of given year/month."""
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, last_day)


# ---------------------------------------------------------------------------
# generate_entries_for_payroll — create journal lines for one payroll
# ---------------------------------------------------------------------------


def generate_entries_for_payroll(
    payroll: Payroll,
    *,
    sync_batch_id: str,
) -> list[dict]:
    """Generate journal entry dicts for a single payroll record.

    Returns a list of dicts suitable for constructing JournalEntry models.
    Each payroll generates 7 entry lines (assuming non-zero amounts):
      - DEBIT  521   gross_wage
      - DEBIT  524.1 sp_employer_total
      - DEBIT  524.2 zp_employer
      - CREDIT 331   net_wage
      - CREDIT 336.1 sp_employee_total + sp_employer_total
      - CREDIT 336.2 zp_employee + zp_employer
      - CREDIT 342   tax_after_bonus
    """
    entry_date = _last_day_of_month(payroll.period_year, payroll.period_month)
    period_desc = f"{payroll.period_year}/{payroll.period_month:02d}"

    entries = []

    def _add(account_code: str, account_name: str, entry_type: str, amount: Decimal, desc: str):
        if amount and amount > 0:
            entries.append(
                {
                    "tenant_id": payroll.tenant_id,
                    "payroll_id": payroll.id,
                    "period_year": payroll.period_year,
                    "period_month": payroll.period_month,
                    "entry_date": entry_date,
                    "account_code": account_code,
                    "account_name": account_name,
                    "entry_type": entry_type,
                    "amount": amount,
                    "description": desc,
                    "sync_batch_id": sync_batch_id,
                }
            )

    # DEBIT entries
    _add(
        *ACCOUNT_521_WAGES,
        "debit",
        payroll.gross_wage,
        f"Hrubá mzda za {period_desc}",
    )
    _add(
        *ACCOUNT_524_SP,
        "debit",
        payroll.sp_employer_total,
        f"Sociálne poistenie zamestnávateľ za {period_desc}",
    )
    _add(
        *ACCOUNT_524_ZP,
        "debit",
        payroll.zp_employer,
        f"Zdravotné poistenie zamestnávateľ za {period_desc}",
    )

    # CREDIT entries
    _add(
        *ACCOUNT_331_EMPLOYEES,
        "credit",
        payroll.net_wage,
        f"Čistá mzda zamestnanec za {period_desc}",
    )
    sp_total_liability = payroll.sp_employee_total + payroll.sp_employer_total
    _add(
        *ACCOUNT_336_SP,
        "credit",
        sp_total_liability,
        f"Sociálne poistenie spolu za {period_desc}",
    )
    zp_total_liability = payroll.zp_employee + payroll.zp_employer
    _add(
        *ACCOUNT_336_ZP,
        "credit",
        zp_total_liability,
        f"Zdravotné poistenie spolu za {period_desc}",
    )
    _add(
        *ACCOUNT_342_TAX,
        "credit",
        payroll.tax_after_bonus,
        f"Preddavok na daň za {period_desc}",
    )

    return entries


# ---------------------------------------------------------------------------
# sync_period — generate & persist journal entries for a period
# ---------------------------------------------------------------------------


def sync_period(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    period_year: int,
    period_month: int,
) -> dict:
    """Generate journal entries for all approved payrolls in a period.

    Steps:
      1. Find approved payrolls (status='approved' or 'paid') without journal entries
         or with status='pending' for re-sync.
      2. Delete any existing journal entries for payrolls being re-synced.
      3. Generate new journal entry lines.
      4. Mark payrolls as pending → synced.
      5. Return summary.

    Returns dict with sync results.
    Raises ``ValueError`` if no payrolls found.
    """
    sync_batch_id = str(uuid.uuid4())[:8]

    # Find approved/paid payrolls for this period
    payrolls = list(
        db.execute(
            select(Payroll).where(
                Payroll.tenant_id == tenant_id,
                Payroll.period_year == period_year,
                Payroll.period_month == period_month,
                Payroll.status.in_(["approved", "paid"]),
            )
        )
        .scalars()
        .all()
    )

    if not payrolls:
        raise ValueError(f"No approved/paid payrolls found for {period_year}/{period_month:02d}")

    # Delete existing journal entries for these payrolls (allows re-sync)
    payroll_ids = [p.id for p in payrolls]
    db.execute(
        delete(JournalEntry).where(
            JournalEntry.payroll_id.in_(payroll_ids),
        )
    )

    # Generate entries for each payroll
    all_entries = []
    for payroll in payrolls:
        entries = generate_entries_for_payroll(payroll, sync_batch_id=sync_batch_id)
        all_entries.extend(entries)

    # Persist journal entries
    journal_objects = []
    for entry_data in all_entries:
        journal_objects.append(JournalEntry(**entry_data))
    db.add_all(journal_objects)

    # Update payroll sync status to 'synced'
    for payroll in payrolls:
        payroll.ledger_sync_status = "synced"

    db.flush()

    # Calculate totals
    total_debit = sum(e["amount"] for e in all_entries if e["entry_type"] == "debit")
    total_credit = sum(e["amount"] for e in all_entries if e["entry_type"] == "credit")

    return {
        "period_year": period_year,
        "period_month": period_month,
        "tenant_id": str(tenant_id),
        "sync_batch_id": sync_batch_id,
        "entries_created": len(all_entries),
        "total_debit": total_debit,
        "total_credit": total_credit,
        "payrolls_synced": len(payrolls),
        "entries": [
            {
                "account_code": e["account_code"],
                "account_name": e["account_name"],
                "entry_type": e["entry_type"],
                "amount": e["amount"],
                "description": e["description"],
            }
            for e in all_entries
        ],
    }


# ---------------------------------------------------------------------------
# get_period_status — integration status for a period
# ---------------------------------------------------------------------------


def get_period_status(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    period_year: int,
    period_month: int,
) -> dict:
    """Return integration status for a period.

    Includes payroll sync counts and journal entry totals.
    """
    # Payroll counts
    payrolls = list(
        db.execute(
            select(Payroll).where(
                Payroll.tenant_id == tenant_id,
                Payroll.period_year == period_year,
                Payroll.period_month == period_month,
            )
        )
        .scalars()
        .all()
    )

    total = len(payrolls)
    synced = sum(1 for p in payrolls if p.ledger_sync_status == "synced")
    pending = sum(1 for p in payrolls if p.ledger_sync_status == "pending")
    error = sum(1 for p in payrolls if p.ledger_sync_status == "error")
    not_synced = sum(1 for p in payrolls if p.ledger_sync_status is None)

    # Journal entry totals
    debit_total = db.execute(
        select(func.coalesce(func.sum(JournalEntry.amount), 0)).where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.period_year == period_year,
            JournalEntry.period_month == period_month,
            JournalEntry.entry_type == "debit",
        )
    ).scalar_one()

    credit_total = db.execute(
        select(func.coalesce(func.sum(JournalEntry.amount), 0)).where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.period_year == period_year,
            JournalEntry.period_month == period_month,
            JournalEntry.entry_type == "credit",
        )
    ).scalar_one()

    entry_count = db.execute(
        select(func.count())
        .select_from(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.period_year == period_year,
            JournalEntry.period_month == period_month,
        )
    ).scalar_one()

    # Last sync timestamp
    last_sync = db.execute(
        select(func.max(JournalEntry.created_at)).where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.period_year == period_year,
            JournalEntry.period_month == period_month,
        )
    ).scalar_one()

    return {
        "period_year": period_year,
        "period_month": period_month,
        "tenant_id": str(tenant_id),
        "total_payrolls": total,
        "synced_payrolls": synced,
        "pending_payrolls": pending,
        "error_payrolls": error,
        "not_synced_payrolls": not_synced,
        "total_journal_entries": entry_count,
        "total_debit": Decimal(str(debit_total)),
        "total_credit": Decimal(str(credit_total)),
        "last_sync_at": last_sync,
        "is_balanced": Decimal(str(debit_total)) == Decimal(str(credit_total)),
    }


# ---------------------------------------------------------------------------
# get_entries_for_period — list journal entries
# ---------------------------------------------------------------------------


def get_entries_for_period(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    period_year: int,
    period_month: int,
) -> list[JournalEntry]:
    """Return all journal entries for a period."""
    return list(
        db.execute(
            select(JournalEntry)
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.period_year == period_year,
                JournalEntry.period_month == period_month,
            )
            .order_by(JournalEntry.account_code, JournalEntry.entry_type)
        )
        .scalars()
        .all()
    )
