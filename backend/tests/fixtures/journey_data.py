"""
Reusable test data constants for journey/integration tests.

All dates are ISO strings (YYYY-MM-DD).
IBANs pass mod-97 checksum validation.
Birth numbers follow valid Slovak YYMMDD/XXXX format.
"""

# ---------------------------------------------------------------------------
# Health Insurers (seed data matching shared.health_insurers)
# ---------------------------------------------------------------------------

HEALTH_INSURERS: list[dict] = [
    {
        "code": "24",
        "name": "Dôvera zdravotná poisťovňa, a.s.",
        "iban": "SK401100000000002624001",
        "bic": "TATRSKBX",
        "is_active": True,
    },
    {
        "code": "25",
        "name": "Všeobecná zdravotná poisťovňa, a.s.",
        "iban": "SK488180000000007000251",
        "bic": "SABORSKX",
        "is_active": True,
    },
    {
        "code": "27",
        "name": "Union zdravotná poisťovňa, a.s.",
        "iban": "SK351100000000002627001",
        "bic": "TATRSKBX",
        "is_active": True,
    },
]

# ---------------------------------------------------------------------------
# Employee base data
# ---------------------------------------------------------------------------

EMPLOYEE_BASE: dict = {
    "employee_number": "EMP001",
    "first_name": "Ján",
    "last_name": "Testovací",
    "birth_date": "1990-05-15",
    "birth_number": "9005155678",
    "gender": "M",
    "nationality": "SK",
    "address_street": "Hlavná 123",
    "address_city": "Bratislava",
    "address_zip": "81101",
    "address_country": "SK",
    "bank_iban": "SK2709000000001234567890",
    "tax_declaration_type": "standard",
    "nczd_applied": True,
    "pillar2_saver": False,
    "is_disabled": False,
    "status": "active",
    "hire_date": "2024-01-01",
}

# ---------------------------------------------------------------------------
# Contract base data
# ---------------------------------------------------------------------------

CONTRACT_BASE: dict = {
    "contract_number": "CONTR001",
    "contract_type": "permanent",
    "job_title": "Software Developer",
    "wage_type": "monthly",
    "base_wage": 2000.00,
    "hours_per_week": 40.0,
    "start_date": "2024-01-01",
}

# ---------------------------------------------------------------------------
# Employee child base data
# ---------------------------------------------------------------------------

CHILD_BASE: dict = {
    "first_name": "Matej",
    "last_name": "Testovací",
    "birth_date": "2015-03-20",
    "is_tax_bonus_eligible": True,
}
