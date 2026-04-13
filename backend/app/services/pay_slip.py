"""Service layer for PaySlip entity.

Provides CRUD operations over the pay_slips table (tenant-specific schema)
plus PDF generation for approved payrolls.
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.pay_slip import PaySlip
from app.models.payroll import Payroll
from app.models.tenant import Tenant
from app.schemas.pay_slip import PaySlipCreate, PaySlipUpdate
from app.services.pdf_generator import (
    build_pay_slip_data_from_models,
    build_pay_slip_pdf,
    get_pdf_path,
    write_pdf_to_disk,
)

logger = logging.getLogger(__name__)


def count_pay_slips(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    payroll_id: UUID | None = None,
    period_year: int | None = None,
    period_month: int | None = None,
) -> int:
    """Return the total number of pay slips matching the given filters.

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    stmt = select(func.count()).select_from(PaySlip)

    if tenant_id is not None:
        stmt = stmt.where(PaySlip.tenant_id == tenant_id)

    if employee_id is not None:
        stmt = stmt.where(PaySlip.employee_id == employee_id)

    if payroll_id is not None:
        stmt = stmt.where(PaySlip.payroll_id == payroll_id)

    if period_year is not None:
        stmt = stmt.where(PaySlip.period_year == period_year)

    if period_month is not None:
        stmt = stmt.where(PaySlip.period_month == period_month)

    return db.execute(stmt).scalar_one()


def list_pay_slips(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    payroll_id: UUID | None = None,
    period_year: int | None = None,
    period_month: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[PaySlip]:
    """Return a paginated list of pay slips ordered by period (desc).

    When *tenant_id* is provided the result is scoped to that tenant.
    When *employee_id* is provided the result is filtered to that employee.
    When *payroll_id* is provided the result is filtered to that payroll.
    When *period_year* / *period_month* are provided the result is filtered
    to the given period.
    """
    stmt = select(PaySlip).order_by(
        PaySlip.period_year.desc(),
        PaySlip.period_month.desc(),
    )

    if tenant_id is not None:
        stmt = stmt.where(PaySlip.tenant_id == tenant_id)

    if employee_id is not None:
        stmt = stmt.where(PaySlip.employee_id == employee_id)

    if payroll_id is not None:
        stmt = stmt.where(PaySlip.payroll_id == payroll_id)

    if period_year is not None:
        stmt = stmt.where(PaySlip.period_year == period_year)

    if period_month is not None:
        stmt = stmt.where(PaySlip.period_month == period_month)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_pay_slip(db: Session, pay_slip_id: UUID) -> PaySlip | None:
    """Return a single pay slip by primary key, or ``None``."""
    return db.get(PaySlip, pay_slip_id)


def create_pay_slip(
    db: Session,
    payload: PaySlipCreate,
) -> PaySlip:
    """Insert a new pay slip record and flush (no commit).

    Raises ``ValueError`` if a pay slip with the same
    ``(tenant_id, payroll_id)`` already exists.
    """
    dup_stmt = select(PaySlip).where(
        PaySlip.tenant_id == payload.tenant_id,
        PaySlip.payroll_id == payload.payroll_id,
    )
    existing = db.execute(dup_stmt).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"PaySlip for payroll_id={payload.payroll_id} already exists in tenant {payload.tenant_id}")

    pay_slip = PaySlip(**payload.model_dump())
    db.add(pay_slip)
    db.flush()
    return pay_slip


def update_pay_slip(
    db: Session,
    pay_slip_id: UUID,
    payload: PaySlipUpdate,
) -> PaySlip:
    """Partially update an existing pay slip record.

    Only fields explicitly set in *payload* are changed.
    Raises ``ValueError`` if the pay slip is not found or if the update
    would create a duplicate ``(tenant_id, payroll_id)``.
    """
    pay_slip = db.get(PaySlip, pay_slip_id)
    if pay_slip is None:
        raise ValueError(f"PaySlip with id={pay_slip_id} not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Check for duplicate (tenant_id, payroll_id) if payroll_id is being changed
    new_payroll_id = update_data.get("payroll_id")
    if new_payroll_id is not None and new_payroll_id != pay_slip.payroll_id:
        dup_stmt = select(PaySlip).where(
            PaySlip.tenant_id == pay_slip.tenant_id,
            PaySlip.payroll_id == new_payroll_id,
            PaySlip.id != pay_slip_id,
        )
        if db.execute(dup_stmt).scalar_one_or_none() is not None:
            raise ValueError(f"PaySlip for payroll_id={new_payroll_id} already exists in tenant {pay_slip.tenant_id}")

    for field, value in update_data.items():
        setattr(pay_slip, field, value)

    db.flush()
    return pay_slip


def delete_pay_slip(db: Session, pay_slip_id: UUID) -> bool:
    """Delete a pay slip by primary key (hard delete).

    Returns ``True`` if the row was deleted.
    Raises ``ValueError`` if the pay slip is not found.
    """
    pay_slip = db.get(PaySlip, pay_slip_id)
    if pay_slip is None:
        raise ValueError(f"PaySlip with id={pay_slip_id} not found")

    db.delete(pay_slip)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------


def generate_pay_slip_pdf(
    db: Session,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    period_year: int,
    period_month: int,
) -> PaySlip:
    """Generate a pay slip PDF for a single employee/period.

    Requires an approved payroll for the given employee/period.
    Creates or updates the PaySlip record with file path and size.

    Raises ``ValueError`` if tenant, employee, or approved payroll not found.
    Returns the PaySlip ORM instance (flushed, not committed).
    """
    # Resolve tenant
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError(f"Tenant with id={tenant_id} not found")

    # Resolve employee
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise ValueError(f"Employee with id={employee_id} not found")
    if employee.tenant_id != tenant_id:
        raise ValueError(f"Employee {employee_id} does not belong to tenant {tenant_id}")

    # Find approved payroll for the period
    stmt = select(Payroll).where(
        Payroll.tenant_id == tenant_id,
        Payroll.employee_id == employee_id,
        Payroll.period_year == period_year,
        Payroll.period_month == period_month,
        Payroll.status.in_(["approved", "paid"]),
    )
    payroll = db.execute(stmt).scalar_one_or_none()
    if payroll is None:
        msg = f"Approved payroll not found for employee {employee_id} in {period_year}/{period_month}"
        raise ValueError(msg)

    # Build PDF data and generate bytes
    slip_data = build_pay_slip_data_from_models(
        tenant=tenant,
        employee=employee,
        payroll=payroll,
    )
    pdf_bytes = build_pay_slip_pdf(slip_data)

    # Compute canonical path and write to disk
    pdf_path = get_pdf_path(
        tenant_schema=tenant.schema_name,
        period_year=period_year,
        period_month=period_month,
        employee_number=employee.employee_number,
    )
    file_size = write_pdf_to_disk(pdf_bytes, pdf_path)

    # Create or update PaySlip record
    existing_stmt = select(PaySlip).where(
        PaySlip.tenant_id == tenant_id,
        PaySlip.payroll_id == payroll.id,
    )
    pay_slip = db.execute(existing_stmt).scalar_one_or_none()

    if pay_slip is not None:
        # Update existing record (re-generation)
        pay_slip.pdf_path = pdf_path
        pay_slip.file_size_bytes = file_size
    else:
        pay_slip = PaySlip(
            tenant_id=tenant_id,
            payroll_id=payroll.id,
            employee_id=employee_id,
            period_year=period_year,
            period_month=period_month,
            pdf_path=pdf_path,
            file_size_bytes=file_size,
        )
        db.add(pay_slip)

    db.flush()

    logger.info(
        "Generated pay slip PDF: %s (%d bytes)",
        pdf_path,
        file_size,
    )
    return pay_slip


def generate_all_pay_slips(
    db: Session,
    *,
    tenant_id: UUID,
    period_year: int,
    period_month: int,
) -> list[PaySlip]:
    """Batch-generate pay slip PDFs for all approved payrolls in a period.

    Finds all approved/paid payrolls for the given tenant and period,
    then generates a PDF for each.

    Returns list of created/updated PaySlip records (flushed, not committed).
    Raises ``ValueError`` if tenant not found or no approved payrolls exist.
    """
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError(f"Tenant with id={tenant_id} not found")

    # Find all approved payrolls for the period
    stmt = select(Payroll).where(
        Payroll.tenant_id == tenant_id,
        Payroll.period_year == period_year,
        Payroll.period_month == period_month,
        Payroll.status.in_(["approved", "paid"]),
    )
    payrolls = list(db.execute(stmt).scalars().all())

    if not payrolls:
        raise ValueError(f"Approved payrolls not found for tenant {tenant_id} in period {period_year}/{period_month}")

    results: list[PaySlip] = []
    for payroll in payrolls:
        employee = db.get(Employee, payroll.employee_id)
        if employee is None:
            logger.warning(
                "Skipping payroll %s — employee %s not found",
                payroll.id,
                payroll.employee_id,
            )
            continue

        slip_data = build_pay_slip_data_from_models(
            tenant=tenant,
            employee=employee,
            payroll=payroll,
        )
        pdf_bytes = build_pay_slip_pdf(slip_data)

        pdf_path = get_pdf_path(
            tenant_schema=tenant.schema_name,
            period_year=period_year,
            period_month=period_month,
            employee_number=employee.employee_number,
        )
        file_size = write_pdf_to_disk(pdf_bytes, pdf_path)

        # Create or update PaySlip record
        existing_stmt = select(PaySlip).where(
            PaySlip.tenant_id == tenant_id,
            PaySlip.payroll_id == payroll.id,
        )
        pay_slip = db.execute(existing_stmt).scalar_one_or_none()

        if pay_slip is not None:
            pay_slip.pdf_path = pdf_path
            pay_slip.file_size_bytes = file_size
        else:
            pay_slip = PaySlip(
                tenant_id=tenant_id,
                payroll_id=payroll.id,
                employee_id=payroll.employee_id,
                period_year=period_year,
                period_month=period_month,
                pdf_path=pdf_path,
                file_size_bytes=file_size,
            )
            db.add(pay_slip)

        db.flush()
        results.append(pay_slip)

        logger.info(
            "Generated pay slip PDF: %s (%d bytes)",
            pdf_path,
            file_size,
        )

    return results


def get_pay_slip_pdf_bytes(
    db: Session,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    period_year: int,
    period_month: int,
) -> tuple[bytes, str]:
    """Generate a pay slip PDF in memory (for streaming download).

    Returns (pdf_bytes, filename).
    Raises ``ValueError`` if data not found.
    """
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError(f"Tenant with id={tenant_id} not found")

    employee = db.get(Employee, employee_id)
    if employee is None:
        raise ValueError(f"Employee with id={employee_id} not found")
    if employee.tenant_id != tenant_id:
        raise ValueError(f"Employee {employee_id} does not belong to tenant {tenant_id}")

    stmt = select(Payroll).where(
        Payroll.tenant_id == tenant_id,
        Payroll.employee_id == employee_id,
        Payroll.period_year == period_year,
        Payroll.period_month == period_month,
        Payroll.status.in_(["approved", "paid"]),
    )
    payroll = db.execute(stmt).scalar_one_or_none()
    if payroll is None:
        msg = f"Approved payroll not found for employee {employee_id} in {period_year}/{period_month}"
        raise ValueError(msg)

    slip_data = build_pay_slip_data_from_models(
        tenant=tenant,
        employee=employee,
        payroll=payroll,
    )
    pdf_bytes = build_pay_slip_pdf(slip_data)
    filename = f"payslip_{employee.employee_number}_{period_year}_{period_month:02d}.pdf"

    return pdf_bytes, filename


def mark_downloaded(
    db: Session,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    period_year: int,
    period_month: int,
) -> None:
    """Mark a pay slip as downloaded (set ``downloaded_at`` if not yet set).

    Looks up the PaySlip record by tenant/employee/period and sets
    ``downloaded_at`` to the current UTC timestamp if it was previously NULL.
    No-op if the record doesn't exist or was already marked.
    Flushes but does not commit.
    """
    stmt = select(PaySlip).where(
        PaySlip.tenant_id == tenant_id,
        PaySlip.employee_id == employee_id,
        PaySlip.period_year == period_year,
        PaySlip.period_month == period_month,
    )
    pay_slip = db.execute(stmt).scalar_one_or_none()
    if pay_slip is not None and pay_slip.downloaded_at is None:
        pay_slip.downloaded_at = func.now()
        db.flush()
