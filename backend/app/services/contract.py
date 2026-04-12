"""Service layer for Contract entity.

Provides CRUD operations over the contracts table (tenant-specific schema).
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.payroll import Payroll
from app.schemas.contract import ContractCreate, ContractUpdate


def _apply_filters(stmt, *, tenant_id, employee_id, is_current):
    """Apply common list/count filters to a select statement."""
    if tenant_id is not None:
        stmt = stmt.where(Contract.tenant_id == tenant_id)
    if employee_id is not None:
        stmt = stmt.where(Contract.employee_id == employee_id)
    if is_current is not None:
        stmt = stmt.where(Contract.is_current == is_current)
    return stmt


def count_contracts(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    is_current: bool | None = None,
) -> int:
    """Return total number of contracts, optionally filtered."""
    stmt = select(func.count()).select_from(Contract)
    stmt = _apply_filters(stmt, tenant_id=tenant_id, employee_id=employee_id, is_current=is_current)
    result = db.execute(stmt).scalar_one()
    return int(result)


def list_contracts(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    is_current: bool | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Contract]:
    """Return a paginated list of contracts ordered by start_date descending.

    When *tenant_id* is provided the result is scoped to that tenant.
    When *employee_id* is provided the result is further scoped to that employee.
    When *is_current* is provided only current/non-current contracts are returned.
    """
    stmt = select(Contract).order_by(Contract.start_date.desc())
    stmt = _apply_filters(stmt, tenant_id=tenant_id, employee_id=employee_id, is_current=is_current)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_contract(db: Session, contract_id: UUID) -> Contract | None:
    """Return a single contract by primary key, or ``None``."""
    return db.get(Contract, contract_id)


def create_contract(
    db: Session,
    payload: ContractCreate,
) -> Contract:
    """Insert a new contract and flush (no commit).

    Raises ``ValueError`` if a contract with the same
    ``(tenant_id, contract_number)`` already exists.
    """
    dup_stmt = select(Contract).where(
        Contract.tenant_id == payload.tenant_id,
        Contract.contract_number == payload.contract_number,
    )
    existing = db.execute(dup_stmt).scalar_one_or_none()
    if existing is not None:
        raise ValueError(
            f"Contract with contract_number={payload.contract_number!r} already exists in tenant {payload.tenant_id}"
        )

    contract = Contract(**payload.model_dump())
    db.add(contract)
    db.flush()
    return contract


def update_contract(
    db: Session,
    contract_id: UUID,
    payload: ContractUpdate,
) -> Contract | None:
    """Partially update an existing contract.

    Only fields explicitly set in *payload* are changed.
    Returns the updated instance or ``None`` if not found.
    """
    contract = db.get(Contract, contract_id)
    if contract is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)

    # Validate unique constraint if contract_number is being changed
    if "contract_number" in update_data and update_data["contract_number"] != contract.contract_number:
        dup_stmt = select(Contract).where(
            Contract.tenant_id == contract.tenant_id,
            Contract.contract_number == update_data["contract_number"],
            Contract.id != contract.id,
        )
        existing = db.execute(dup_stmt).scalar_one_or_none()
        if existing is not None:
            raise ValueError(
                f"Contract with contract_number={update_data['contract_number']!r} "
                f"already exists in tenant {contract.tenant_id}"
            )

    for field, value in update_data.items():
        setattr(contract, field, value)

    db.flush()
    return contract


def delete_contract(db: Session, contract_id: UUID) -> bool:
    """Delete a contract by primary key (hard delete).

    Returns ``True`` if the row was deleted, ``False`` if not found.
    Raises ``ValueError`` if the contract has dependent payroll records.
    """
    contract = db.get(Contract, contract_id)
    if contract is None:
        return False

    # Check FK dependencies — payrolls reference this contract
    payroll_count_stmt = (
        select(func.count())
        .select_from(Payroll)
        .where(
            Payroll.contract_id == contract_id,
        )
    )
    payroll_count = db.execute(payroll_count_stmt).scalar_one()
    if payroll_count > 0:
        raise ValueError(f"Cannot delete contract {contract_id}: {payroll_count} payroll record(s) depend on it")

    db.delete(contract)
    db.flush()
    return True
