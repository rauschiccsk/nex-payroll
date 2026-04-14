"""Seed initial data — demo tenant and superadmin user.

Inserts a demo tenant (ICC Demo s.r.o.) into public.tenants and a
superadmin user (director role) into users, linked to the demo tenant.
The superadmin password is read from PAYROLL_ADMIN_PASSWORD env var
at migration time (default: 'changeme').

Revision ID: 024
Revises: 023
Create Date: 2026-04-14 00:00:00.000000

"""

import logging
import os
from collections.abc import Sequence

from pwdlib import PasswordHash
from sqlalchemy import text

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "024"
down_revision: str | Sequence[str] | None = "023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Fixed UUIDs for deterministic seed data (allows reliable downgrade)
DEMO_TENANT_ID = "00000000-0000-4000-8000-000000000001"
SUPERADMIN_USER_ID = "00000000-0000-4000-8000-000000000002"


def upgrade() -> None:
    """Insert demo tenant and superadmin user."""
    password = os.getenv("PAYROLL_ADMIN_PASSWORD")
    if not password:
        logger.warning(
            "PAYROLL_ADMIN_PASSWORD env var not set — using insecure default password. "
            "Set PAYROLL_ADMIN_PASSWORD before running this migration in production."
        )
        password = "changeme"
    password_hash = PasswordHash.recommended().hash(password)

    # Insert demo tenant
    op.execute(
        text(
            """
            INSERT INTO public.tenants (
                id, name, ico, schema_name,
                address_street, address_city, address_zip, address_country,
                bank_iban, is_active
            ) VALUES (
                CAST(:id AS uuid), :name, :ico, :schema_name,
                :address_street, :address_city, :address_zip, 'SK',
                :bank_iban, true
            )
            ON CONFLICT (ico) DO NOTHING
            """
        ).bindparams(
            id=DEMO_TENANT_ID,
            name="ICC Demo s.r.o.",
            ico="12345678",
            schema_name="tenant_demo",
            address_street="Testovacia 1",
            address_city="Bratislava",
            address_zip="81101",
            bank_iban="SK0000000000000000000000",
        )
    )

    # Insert superadmin user
    op.execute(
        text(
            """
            INSERT INTO public.users (
                id, tenant_id, username, email,
                password_hash, role, is_active
            ) VALUES (
                CAST(:id AS uuid), CAST(:tenant_id AS uuid), :username, :email,
                :password_hash, 'director', true
            )
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(
            id=SUPERADMIN_USER_ID,
            tenant_id=DEMO_TENANT_ID,
            username="superadmin",
            email="superadmin@isnex.eu",
            password_hash=password_hash,
        )
    )


def downgrade() -> None:
    """Remove seeded superadmin user and demo tenant."""
    op.execute(
        text("DELETE FROM public.users WHERE id = CAST(:id AS uuid)").bindparams(
            id=SUPERADMIN_USER_ID,
        )
    )
    op.execute(
        text("DELETE FROM public.tenants WHERE id = CAST(:id AS uuid)").bindparams(
            id=DEMO_TENANT_ID,
        )
    )
