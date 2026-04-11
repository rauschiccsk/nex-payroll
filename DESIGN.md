# NEX Payroll — DESIGN.md v0.2

## 1. Project Overview

### 1.1 Identification

| Parameter | Value |
|-----------|-------|
| Project | NEX Payroll |
| Slug | nex-payroll |
| Type | software |
| GitHub | rauschiccsk/nex-payroll |
| Backend Port | 9172 |
| Frontend Port | 9173 |
| Database Port | 9174 |
| Domain | payroll.isnex.eu |
| Source Path | /opt/nex-payroll-src/ |

### 1.2 Customers

| Customer | Company | IČO | Schema |
|----------|---------|------|--------|
| ANDROS | ANDROS s.r.o. | (to be filled) | tenant_andros |
| ICC | ICC s.r.o. | (to be filled) | tenant_icc |

### 1.3 Phases

| Phase | Scope | Description |
|-------|-------|-------------|
| I | Infrastructure & Entities | Repository, Docker, DB, models, CRUD APIs, frontend scaffold, CI/CD |
| II | Payroll Engine | Calculation engine, pay slips, AI validation, payroll UI |
| III | Payments & Reports | SEPA XML, SP/ZP/DÚ reports, payment management |
| IV | Annual & Integration | Annual tax settlement, NEX Ledger sync, notifications, deadline monitoring |

### 1.4 Requirements Traceability

#### Functional Requirements

| ID | Requirement | Phase |
|----|-------------|-------|
| R-01 | Employee master data management with encrypted PII | I |
| R-02 | Contract lifecycle management (create, modify, terminate) | I |
| R-03 | Monthly payroll calculation (gross → net) with Slovak 2026 rates | II |
| R-04 | Pay slip PDF generation (ReportLab) | II |
| R-05 | SEPA XML payment orders (pain.001.001.03) | III |
| R-06 | SP monthly report (XML, fund breakdown) | III |
| R-07 | ZP monthly report per health insurer (XML) | III |
| R-08 | Tax monthly prehľad (XML) | III |
| R-09 | Annual tax settlement with NČZD recalculation | IV |
| R-10 | NEX Ledger integration (journal entry sync) | IV |

#### Non-Functional Requirements

| ID | Requirement | Phase |
|----|-------------|-------|
| NR-01 | AES-256 encryption for PII (birth_number, bank_iban) | I |
| NR-02 | RBAC with 3 roles: director, accountant, employee | I |
| NR-03 | Multi-tenant with schema-per-tenant isolation | I |
| NR-04 | AI-native: anomaly detection, calculation validation, deadline monitoring | II, IV |
| NR-05 | Audit log for all data modifications | I |

---

## 2. Architecture

### 2.1 Multi-Tenant Architecture

- **Strategy:** Schema-per-tenant (PostgreSQL schemas)
- **Public schema:** tenants table, audit_log
- **Shared schema:** health_insurers, contribution_rates, tax_brackets, statutory_deadlines (reference data shared across tenants)
- **Tenant schemas:** tenant_andros, tenant_icc — contain all tenant-specific data (employees, contracts, payrolls, etc.)
- **Tenant resolution:** X-Tenant HTTP header → lookup tenant → set search_path to tenant schema
- **Data isolation:** Complete — tenant A cannot access tenant B data

### 2.2 Security

- **PII Encryption:** AES-256 Fernet encryption for birth_number, bank_iban (at-rest encryption via SQLAlchemy TypeDecorator)
- **Key management:** PAYROLL_ENCRYPTION_KEY environment variable
- **Audit trail:** All CRUD operations logged to public.audit_log with user_id, action, entity, old/new values

### 2.3 Authentication & Authorization

#### 2.3.1 Authentication

- **Method:** JWT (JSON Web Tokens) via OAuth2 Password flow
- **Libraries:** python-jose[cryptography] for JWT, pwdlib with Argon2 for password hashing
- **Access token:** 30 minutes expiry, HS256 signing
- **Secret key:** PAYROLL_JWT_SECRET environment variable (openssl rand -hex 32)
- **Token transport:** Authorization: Bearer header
- **Token storage (frontend):** In-memory (Zustand state), NOT localStorage/sessionStorage
- **Refresh tokens:** Deferred (W-06) — not critical for internal ERP with 2-3 users

#### 2.3.2 RBAC (Role-Based Access Control)

| Role | Scope | Permissions |
|------|-------|-------------|
| director | Full access | All operations, user management, tenant settings, approve payroll, annual processing, integrations |
| accountant | Operational | Employee CRUD, payroll calculation, reports, payments, leaves management |
| employee | Self-service | View own payslips, request leaves, view own data only |

**Implementation:**
- `get_current_user` dependency — extracts and validates JWT
- `require_role(role)` dependency — checks role hierarchy: director > accountant > employee
- Tenant isolation: user always scoped to their tenant_id
- Employee self-service: employee role filtered to own employee_id

#### 2.3.3 Initial User Seeding

- Migration creates default admin user (role=director) per tenant
- Password set via PAYROLL_ADMIN_PASSWORD environment variable

### 2.4 AI-Native Architecture

NEX Payroll is AI-native — the local LLM (Ollama) is a core component, not an add-on.

| AI Function | Description | Phase |
|-------------|-------------|-------|
| Anomaly Detection | Compare payroll with previous 3 months, flag deviations >20% | II |
| Calculation Validation | Verify gross = net + sp + zp + tax identity | II |
| Deadline Monitoring | Risk assessment for approaching deadlines | IV |
| Data Quality | Flag missing/inconsistent employee data | IV |

- **Ollama URL:** OLLAMA_URL environment variable (default: http://localhost:9132)
- **Model:** llama3.1:8b (via NEX Brain infrastructure)
- **Autonomy:** AI monitors and alerts, human approves actions

---

## 3. Technology Stack

### 3.1 Backend

| Component | Technology | Notes |
|-----------|-----------|-------|
| Framework | FastAPI | def endpoints (NEVER async def) |
| ORM | SQLAlchemy 2.0 | Synchronous only, DeclarativeBase |
| DB Driver | pg8000 | NEVER asyncpg |
| Migrations | Alembic | render_as_batch=True |
| Settings | pydantic-settings | BaseSettings with .env |
| Encryption | cryptography (Fernet) | AES-256 for PII |
| PDF | ReportLab | Pay slips, certificates |
| XML | lxml | SP/ZP/DÚ reports |
| SEPA | sepaxml | pain.001.001.03 |
| Auth | python-jose, pwdlib | JWT + Argon2 |
| Testing | pytest | Coverage minimum 90% |
| Linting | ruff | Standard config |
| Server | Gunicorn + Uvicorn workers | Production deployment |

**ICC Code Standards:**
- `server_default` for all timestamps (NEVER Python-side default)
- `def` endpoints (NEVER `async def`)
- pg8000 driver (NEVER asyncpg)
- Synchronous SQLAlchemy (NEVER async session)
- English identifiers in source code (Slovak only in UI labels)

### 3.2 Frontend

| Component | Technology |
|-----------|-----------|
| Framework | React 18 + TypeScript 5 |
| Build | Vite 5 |
| Styling | TailwindCSS + shadcn/ui |
| HTTP | Axios |
| State | Zustand |
| Tables | TanStack Table |
| Forms | React Hook Form + Zod |
| Charts | Recharts |
| PDF | react-pdf |
| Router | React Router |

### 3.3 Infrastructure

| Component | Technology | Port |
|-----------|-----------|------|
| Backend | FastAPI (Docker) | 9172 |
| Frontend | Nginx (Docker) | 9173 |
| Database | PostgreSQL 16 Alpine (Docker) | 9174 |
| AI | Ollama (shared, NEX Brain) | 9132 |

---

## 4. Data Model

### 4.1 SP Sadzby (Sociálne Poistenie) — 2026

#### Zamestnanec (9.4%)

| Fond | Sadzba |
|------|--------|
| Nemocenské poistenie | 1.4% |
| Starobné dôchodkové poistenie | 4.0% |
| Invalidné dôchodkové poistenie | 3.0% |
| Poistenie v nezamestnanosti | 1.0% |
| **Spolu zamestnanec** | **9.4%** |

#### Zamestnávateľ (24.7% + 0.8%)

| Fond | Sadzba | Strop |
|------|--------|-------|
| Nemocenské poistenie | 1.4% | max VZ |
| Starobné dôchodkové poistenie | 14.0% | max VZ |
| Invalidné dôchodkové poistenie | 3.0% | max VZ |
| Poistenie v nezamestnanosti | 1.0% | max VZ |
| Garančné poistenie | 0.25% | max VZ |
| Rezervný fond solidarity | 4.75% | max VZ |
| Poistenie pre prípad kurzarbeit | 0.3% | max VZ |
| **Spolu zamestnávateľ (stropované)** | **24.7%** | **max VZ** |
| Úrazové poistenie | 0.8% | bez stropu |

#### Maximálny vymeriavací základ SP

- **Mesačný:** 9,128 × 1.8367 = **16,764 €/mesiac** (7× priemerná mzda)
- **Ročný:** 16,764 × 12 = **201,168 €/rok**

### 4.2 ZP Sadzby (Zdravotné Poistenie) — 2026

| Platiteľ | Štandardná | Zdravotne postihnutý |
|----------|-----------|---------------------|
| Zamestnanec | 5.0% | 2.5% |
| Zamestnávateľ | 11.0% | 5.5% |

- **Maximálny VZ ZP:** Bez stropu (od 2017)
- **Minimálny VZ ZP:** 816.00 €/mesiac (minimálna mzda 2026)

### 4.3 Celkové zaťaženie

| | Zamestnanec | Zamestnávateľ |
|--|-------------|---------------|
| SP | 9.4% | 24.7% (+0.8% úrazové) |
| ZP | 5.0% | 11.0% |
| **Spolu** | **14.4%** | **35.7%** (+0.8%) |

### 4.4 Daň z Príjmov — 2026

| Parameter | Hodnota |
|-----------|---------|
| Sadzba 19% | Do 50,234.18 €/rok (4,186.18 €/mesiac) |
| Sadzba 25% | Nad 50,234.18 €/rok |
| NČZD (mesačná) | 497.23 € |
| NČZD (ročná) | 5,966.73 € |
| NČZD krátenie | Ak ročný ZD > 26,367.26 € → NČZD = 12,558.55 − ZD/4 |
| NČZD = 0 | Ak ročný ZD > 50,234.20 € |
| Daňový bonus do 15 rokov | 100 €/mesiac |
| Daňový bonus 15-18 rokov | 50 €/mesiac |
| DB percentuálny limit (1 dieťa) | 29% čiastkového ZD |
| DB percentuálny limit (2 deti) | 36% čiastkového ZD |
| DB percentuálny limit (3 deti) | 43% čiastkového ZD |
| DB percentuálny limit (4 deti) | 50% čiastkového ZD |
| DB percentuálny limit (5 detí) | 57% čiastkového ZD |
| DB percentuálny limit (6+ detí) | 64% čiastkového ZD |

### 4.5 Ďalšie Parametre

| Parameter | Hodnota |
|-----------|---------|
| Minimálna mzda 2026 | 816 €/mesiac |
| Dovolenka (do 33 rokov) | 20 dní |
| Dovolenka (od 33 rokov) | 25 dní |
| PN 1.-3. deň (zamestnávateľ) | 25% DVZ |
| PN 4.-10. deň (zamestnávateľ) | 55% DVZ |
| PN od 11. dňa (SP) | 55% DVZ |
| II. pilier (sporiteľ) | 4% zo starobného VZ |

### 4.6 Výpočtový Algoritmus (gross → net)

```
1. HRUBÁ MZDA (gross_wage)
   = base_wage + overtime + bonuses + supplements

2. VYMERIAVACÍ ZÁKLAD SP (sp_assessment_base)
   = MIN(gross_wage, 16764)

3. SP ZAMESTNANEC (sp_employee_total = 9.4%)
   = sp_assessment_base × 0.094
   Rozpis: nemocenské(1.4%) + starobné(4.0%) + invalidné(3.0%) + nezamestnanosť(1.0%)

4. ZP ZAMESTNANEC (zp_employee = 5.0% alebo 2.5%)
   = gross_wage × 0.05  (bez stropu)

5. ČIASTKOVÝ ZÁKLAD DANE (partial_tax_base)
   = gross_wage - sp_employee_total - zp_employee

6. NČZD (nczd_monthly)
   = 497.23 € (ak má podpísané vyhlásenie)
   = 0 € (ak nemá vyhlásenie)
   Ročné krátenie: ak ZD > 26,367.26 → NČZD = 12,558.55 - ZD/4

7. ZÁKLAD DANE (tax_base)
   = MAX(0, partial_tax_base - nczd_monthly)

8. DAŇ (tax_advance)
   = tax_base × 0.19 (ak ročný ZD ≤ 50,234.18)
   = tax_base × 0.25 (ak ročný ZD > 50,234.18, progresívne)

9. DAŇOVÝ BONUS (child_bonus)
   = SUM(per child: 100€ ak <15r, 50€ ak 15-18r)
   Limit: MAX(DB) = percentuálny limit × čiastkový ZD

10. DAŇ PO BONUSE (tax_after_bonus)
    = MAX(0, tax_advance - child_bonus)

11. ČISTÁ MZDA (net_wage)
    = gross_wage - sp_employee_total - zp_employee - tax_after_bonus

12. SP ZAMESTNÁVATEĽ (sp_employer_total = 24.7% + 0.8%)
    = sp_assessment_base × 0.247 + gross_wage × 0.008 (úrazové bez stropu)

13. ZP ZAMESTNÁVATEĽ (zp_employer = 11.0% alebo 5.5%)
    = gross_wage × 0.11

14. II. PILIER (pillar2)
    = sp_assessment_base × 0.04 (ak je sporiteľ, z fondu starobného)

15. VALIDÁCIA
    gross_wage = net_wage + sp_employee_total + zp_employee + tax_after_bonus
```

### 4.7 Zákonné Termíny

| Termín | Lehota | Inštitúcia |
|--------|--------|------------|
| ZP mesačný prehľad | Do 3 pracovných dní po výplate | Zdravotná poisťovňa |
| SP mesačný výkaz | Do 20. dňa nasledujúceho mesiaca | Sociálna poisťovňa |
| Preddavok dane | Do konca nasledujúceho mesiaca | Daňový úrad |
| Potvrdenie o príjmoch | Do 10. marca | Zamestnávateľ → zamestnanec |
| Ročné hlásenie o dani | Do 30. apríla | Daňový úrad |
| ELDP | Do 30. apríla | Sociálna poisťovňa |

---

## 5. Domain Models

**Total entities: 18**

### 5.1 Entity Overview

| # | Entity | Schema | Description |
|---|--------|--------|-------------|
| 1 | Tenant | public | Spoločnosť/firma |
| 2 | User | tenant | Používateľ systému (auth + RBAC) |
| 3 | Employee | tenant | Zamestnanec |
| 4 | EmployeeChild | tenant | Dieťa zamestnanca (daňový bonus) |
| 5 | Contract | tenant | Pracovná zmluva |
| 6 | Payroll | tenant | Mesačná mzda (výpočet) |
| 7 | PaySlip | tenant | Výplatná páska (PDF) |
| 8 | Leave | tenant | Dovolenka / PN / OČR |
| 9 | LeaveEntitlement | tenant | Nárok na dovolenku (ročný) |
| 10 | PaymentOrder | tenant | Platobný príkaz |
| 11 | MonthlyReport | tenant | Mesačný výkaz (SP/ZP/DÚ) |
| 12 | Notification | tenant | Upozornenie pre používateľa |
| 13 | AuditLog | public | Audit záznam |
| 14 | HealthInsurer | shared | Zdravotná poisťovňa |
| 15 | ContributionRate | shared | Sadzby odvodov (verzované) |
| 16 | TaxBracket | shared | Daňové pásma (verzované) |
| 17 | StatutoryDeadline | shared | Zákonné termíny |

### 5.2 Tenant

**Schema:** public

```
Table: tenants
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
name                String(200)       NOT NULL
ico                 String(8)         NOT NULL, UNIQUE
dic                 String(12)        NULLABLE
ic_dph              String(14)        NULLABLE
address_street      String(200)       NOT NULL
address_city        String(100)       NOT NULL
address_zip         String(10)        NOT NULL
address_country     String(2)         NOT NULL, DEFAULT 'SK'
bank_iban           String(34)        NOT NULL
bank_bic            String(11)        NULLABLE
schema_name         String(63)        NOT NULL, UNIQUE
default_role        String(20)        NOT NULL, DEFAULT 'accountant'
is_active           Boolean           NOT NULL, server_default='true'
created_at          DateTime          NOT NULL, server_default=now()
updated_at          DateTime          NOT NULL, server_default=now(), onupdate=now()
──────────────────────────────────────────────────────────────
```

### 5.3 User

**Schema:** tenant-specific

```
Table: users
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
tenant_id           UUID              FK(public.tenants.id), NOT NULL
employee_id         UUID              FK(employees.id), NULLABLE, UNIQUE
username            String(100)       NOT NULL
email               String(255)       NOT NULL
password_hash       String(255)       NOT NULL
role                String(20)        NOT NULL, CHECK IN ('director','accountant','employee')
is_active           Boolean           NOT NULL, server_default='true'
last_login_at       DateTime          NULLABLE
password_changed_at DateTime          NULLABLE
created_at          DateTime          NOT NULL, server_default=now()
updated_at          DateTime          NOT NULL, server_default=now(), onupdate=now()
──────────────────────────────────────────────────────────────

Indexes:
  UNIQUE(tenant_id, username)
  UNIQUE(tenant_id, email)
  INDEX(tenant_id, role)
  UNIQUE(employee_id) WHERE employee_id IS NOT NULL

Business Rules:
  role='employee' MUST have employee_id set
  role='director'|'accountant' MAY have employee_id
  Soft delete via is_active=False
  password_hash uses Argon2 via pwdlib
```

### 5.4 Employee

**Schema:** tenant-specific

```
Table: employees
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
tenant_id           UUID              FK(public.tenants.id), NOT NULL
employee_number     String(20)        NOT NULL
first_name          String(100)       NOT NULL
last_name           String(100)       NOT NULL
title_before        String(50)        NULLABLE
title_after         String(50)        NULLABLE
birth_date          Date              NOT NULL
birth_number        EncryptedString   NOT NULL (rodné číslo)
gender              String(1)         NOT NULL, CHECK IN ('M','F')
nationality         String(2)         NOT NULL, DEFAULT 'SK'
address_street      String(200)       NOT NULL
address_city        String(100)       NOT NULL
address_zip         String(10)        NOT NULL
address_country     String(2)         NOT NULL, DEFAULT 'SK'
bank_iban           EncryptedString   NOT NULL
bank_bic            String(11)        NULLABLE
health_insurer_id   UUID              FK(shared.health_insurers.id), NOT NULL
tax_declaration_type String(20)       NOT NULL, CHECK IN ('standard','secondary','none')
nczd_applied        Boolean           NOT NULL, DEFAULT True
pillar2_saver       Boolean           NOT NULL, DEFAULT False
is_disabled         Boolean           NOT NULL, DEFAULT False
status              String(20)        NOT NULL, DEFAULT 'active', CHECK IN ('active','inactive','terminated')
hire_date           Date              NOT NULL
termination_date    Date              NULLABLE
is_deleted          Boolean           NOT NULL, server_default='false'
created_at          DateTime          NOT NULL, server_default=now()
updated_at          DateTime          NOT NULL, server_default=now(), onupdate=now()
──────────────────────────────────────────────────────────────

Indexes:
  UNIQUE(tenant_id, employee_number)
  INDEX(tenant_id, status)
  INDEX(tenant_id, last_name)
```

### 5.5 EmployeeChild

**Schema:** tenant-specific

```
Table: employee_children
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
tenant_id           UUID              FK(public.tenants.id), NOT NULL
employee_id         UUID              FK(employees.id), NOT NULL
first_name          String(100)       NOT NULL
last_name           String(100)       NOT NULL
birth_date          Date              NOT NULL
birth_number        EncryptedString   NULLABLE
is_tax_bonus_eligible Boolean         NOT NULL, DEFAULT True
custody_from        Date              NULLABLE
custody_to          Date              NULLABLE
created_at          DateTime          NOT NULL, server_default=now()
updated_at          DateTime          NOT NULL, server_default=now(), onupdate=now()
──────────────────────────────────────────────────────────────

Indexes:
  INDEX(tenant_id, employee_id)
```

### 5.6 Contract

**Schema:** tenant-specific

```
Table: contracts
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
tenant_id           UUID              FK(public.tenants.id), NOT NULL
employee_id         UUID              FK(employees.id), NOT NULL
contract_number     String(50)        NOT NULL
contract_type       String(30)        NOT NULL, CHECK IN ('permanent','fixed_term','agreement_work','agreement_activity')
job_title           String(200)       NOT NULL
wage_type           String(20)        NOT NULL, CHECK IN ('monthly','hourly')
base_wage           Numeric(10,2)     NOT NULL
hours_per_week      Numeric(4,1)      NOT NULL, DEFAULT 40.0
start_date          Date              NOT NULL
end_date            Date              NULLABLE
probation_end_date  Date              NULLABLE
termination_date    Date              NULLABLE
termination_reason  String(200)       NULLABLE
is_current          Boolean           NOT NULL, server_default='true'
created_at          DateTime          NOT NULL, server_default=now()
updated_at          DateTime          NOT NULL, server_default=now(), onupdate=now()
──────────────────────────────────────────────────────────────

Indexes:
  INDEX(tenant_id, employee_id, is_current)
  UNIQUE(tenant_id, contract_number)
```

### 5.7 Payroll

**Schema:** tenant-specific

```
Table: payrolls
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
tenant_id           UUID              FK(public.tenants.id), NOT NULL
employee_id         UUID              FK(employees.id), NOT NULL
contract_id         UUID              FK(contracts.id), NOT NULL
period_year         Integer           NOT NULL
period_month        Integer           NOT NULL
status              String(20)        NOT NULL, DEFAULT 'draft', CHECK IN ('draft','calculated','approved','paid')
-- Gross components
base_wage           Numeric(10,2)     NOT NULL
overtime_hours      Numeric(6,2)      NOT NULL, DEFAULT 0
overtime_amount     Numeric(10,2)     NOT NULL, DEFAULT 0
bonus_amount        Numeric(10,2)     NOT NULL, DEFAULT 0
supplement_amount   Numeric(10,2)     NOT NULL, DEFAULT 0
gross_wage          Numeric(10,2)     NOT NULL
-- SP employee
sp_assessment_base  Numeric(10,2)     NOT NULL
sp_nemocenske       Numeric(10,2)     NOT NULL
sp_starobne         Numeric(10,2)     NOT NULL
sp_invalidne        Numeric(10,2)     NOT NULL
sp_nezamestnanost   Numeric(10,2)     NOT NULL
sp_employee_total   Numeric(10,2)     NOT NULL
-- ZP employee
zp_assessment_base  Numeric(10,2)     NOT NULL
zp_employee         Numeric(10,2)     NOT NULL
-- Tax
partial_tax_base    Numeric(10,2)     NOT NULL
nczd_applied        Numeric(10,2)     NOT NULL
tax_base            Numeric(10,2)     NOT NULL
tax_advance         Numeric(10,2)     NOT NULL
child_bonus         Numeric(10,2)     NOT NULL, DEFAULT 0
tax_after_bonus     Numeric(10,2)     NOT NULL
-- Net
net_wage            Numeric(10,2)     NOT NULL
-- Employer costs
sp_employer_nemocenske    Numeric(10,2) NOT NULL
sp_employer_starobne      Numeric(10,2) NOT NULL
sp_employer_invalidne     Numeric(10,2) NOT NULL
sp_employer_nezamestnanost Numeric(10,2) NOT NULL
sp_employer_garancne      Numeric(10,2) NOT NULL
sp_employer_rezervny      Numeric(10,2) NOT NULL
sp_employer_kurzarbeit    Numeric(10,2) NOT NULL
sp_employer_urazove       Numeric(10,2) NOT NULL
sp_employer_total         Numeric(10,2) NOT NULL
zp_employer               Numeric(10,2) NOT NULL
total_employer_cost       Numeric(10,2) NOT NULL
-- Pillar 2
pillar2_amount      Numeric(10,2)     NOT NULL, DEFAULT 0
-- AI
ai_validation_result JSON             NULLABLE
-- Ledger
ledger_sync_status  String(20)        NULLABLE, CHECK IN ('pending','synced','error')
-- Metadata
calculated_at       DateTime          NULLABLE
approved_at         DateTime          NULLABLE
approved_by         UUID              NULLABLE, FK(users.id)
created_at          DateTime          NOT NULL, server_default=now()
updated_at          DateTime          NOT NULL, server_default=now(), onupdate=now()
──────────────────────────────────────────────────────────────

Indexes:
  UNIQUE(tenant_id, employee_id, period_year, period_month)
  INDEX(tenant_id, period_year, period_month, status)
```

### 5.8 PaySlip

**Schema:** tenant-specific

```
Table: pay_slips
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
tenant_id           UUID              FK(public.tenants.id), NOT NULL
payroll_id          UUID              FK(payrolls.id), NOT NULL
employee_id         UUID              FK(employees.id), NOT NULL
period_year         Integer           NOT NULL
period_month        Integer           NOT NULL
pdf_path            String(500)       NOT NULL
file_size_bytes     Integer           NULLABLE
generated_at        DateTime          NOT NULL, server_default=now()
downloaded_at       DateTime          NULLABLE
──────────────────────────────────────────────────────────────

Indexes:
  UNIQUE(tenant_id, payroll_id)
  INDEX(tenant_id, employee_id, period_year, period_month)

Business Rules:
  PDF path: /opt/nex-payroll-src/data/payslips/{tenant}/{year}/{month}/{employee_number}.pdf
  Generated after payroll approval (status='approved')
  downloaded_at tracks employee access (audit)
```

### 5.9 Leave

**Schema:** tenant-specific

```
Table: leaves
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
tenant_id           UUID              FK(public.tenants.id), NOT NULL
employee_id         UUID              FK(employees.id), NOT NULL
leave_type          String(30)        NOT NULL, CHECK IN ('annual','sick_employer','sick_sp','ocr','maternity','parental','unpaid','obstacle')
start_date          Date              NOT NULL
end_date            Date              NOT NULL
business_days       Integer           NOT NULL
status              String(20)        NOT NULL, DEFAULT 'pending', CHECK IN ('pending','approved','rejected','cancelled')
note                Text              NULLABLE
approved_by         UUID              NULLABLE, FK(users.id)
approved_at         DateTime          NULLABLE
created_at          DateTime          NOT NULL, server_default=now()
updated_at          DateTime          NOT NULL, server_default=now(), onupdate=now()
──────────────────────────────────────────────────────────────

Indexes:
  INDEX(tenant_id, employee_id, start_date)
  INDEX(tenant_id, status)
```

### 5.10 LeaveEntitlement

**Schema:** tenant-specific

```
Table: leave_entitlements
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
tenant_id           UUID              FK(public.tenants.id), NOT NULL
employee_id         UUID              FK(employees.id), NOT NULL
year                Integer           NOT NULL
total_days          Integer           NOT NULL
used_days           Integer           NOT NULL, DEFAULT 0
remaining_days      Integer           NOT NULL (computed: total - used)
carryover_days      Integer           NOT NULL, DEFAULT 0
created_at          DateTime          NOT NULL, server_default=now()
updated_at          DateTime          NOT NULL, server_default=now(), onupdate=now()
──────────────────────────────────────────────────────────────

Indexes:
  UNIQUE(tenant_id, employee_id, year)
```

### 5.11 PaymentOrder

**Schema:** tenant-specific

```
Table: payment_orders
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
tenant_id           UUID              FK(public.tenants.id), NOT NULL
period_year         Integer           NOT NULL
period_month        Integer           NOT NULL
payment_type        String(30)        NOT NULL, CHECK IN ('net_wage','sp','zp_vszp','zp_dovera','zp_union','tax','pillar2')
recipient_name      String(200)       NOT NULL
recipient_iban      String(34)        NOT NULL
recipient_bic       String(11)        NULLABLE
amount              Numeric(12,2)     NOT NULL
variable_symbol     String(10)        NULLABLE
specific_symbol     String(10)        NULLABLE
constant_symbol     String(4)         NULLABLE
reference           String(140)       NULLABLE
status              String(20)        NOT NULL, DEFAULT 'pending', CHECK IN ('pending','exported','paid')
employee_id         UUID              NULLABLE, FK(employees.id) (for net_wage type)
health_insurer_id   UUID              NULLABLE, FK(shared.health_insurers.id) (for zp types)
created_at          DateTime          NOT NULL, server_default=now()
updated_at          DateTime          NOT NULL, server_default=now(), onupdate=now()
──────────────────────────────────────────────────────────────

Indexes:
  INDEX(tenant_id, period_year, period_month, payment_type)
```

### 5.12 MonthlyReport

**Schema:** tenant-specific

```
Table: monthly_reports
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
tenant_id           UUID              FK(public.tenants.id), NOT NULL
period_year         Integer           NOT NULL
period_month        Integer           NOT NULL
report_type         String(30)        NOT NULL, CHECK IN ('sp_monthly','zp_vszp','zp_dovera','zp_union','tax_prehled')
file_path           String(500)       NOT NULL
file_format         String(10)        NOT NULL, DEFAULT 'xml'
status              String(20)        NOT NULL, DEFAULT 'generated', CHECK IN ('generated','submitted','accepted','rejected')
deadline_date       Date              NOT NULL
submitted_at        DateTime          NULLABLE
institution         String(100)       NOT NULL
health_insurer_id   UUID              NULLABLE, FK(shared.health_insurers.id)
created_at          DateTime          NOT NULL, server_default=now()
updated_at          DateTime          NOT NULL, server_default=now(), onupdate=now()
──────────────────────────────────────────────────────────────

Indexes:
  UNIQUE(tenant_id, period_year, period_month, report_type)
```

### 5.13 Notification

**Schema:** tenant-specific

```
Table: notifications
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
tenant_id           UUID              FK(public.tenants.id), NOT NULL
user_id             UUID              FK(users.id), NOT NULL
type                String(50)        NOT NULL, CHECK IN ('deadline','anomaly','system','approval')
severity            String(20)        NOT NULL, DEFAULT 'info', CHECK IN ('info','warning','critical')
title               String(200)       NOT NULL
message             Text              NOT NULL
related_entity      String(50)        NULLABLE
related_entity_id   UUID              NULLABLE
is_read             Boolean           NOT NULL, server_default='false'
read_at             DateTime          NULLABLE
created_at          DateTime          NOT NULL, server_default=now()
──────────────────────────────────────────────────────────────

Indexes:
  INDEX(tenant_id, user_id, is_read)
  INDEX(tenant_id, created_at DESC)

Business Rules:
  Deadline: generated by DeadlineMonitor (7, 3, 1 day before)
  Anomaly: generated by AIValidator on payroll deviation
  Approval: generated when leave request needs approval
  System: errors, sync failures
  Auto-cleanup: notifications older than 90 days
```

### 5.14 AuditLog

**Schema:** public

```
Table: audit_log
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
tenant_id           UUID              FK(tenants.id), NOT NULL
user_id             UUID              NULLABLE
action              String(20)        NOT NULL, CHECK IN ('CREATE','UPDATE','DELETE')
entity_type         String(100)       NOT NULL
entity_id           UUID              NOT NULL
old_values          JSON              NULLABLE
new_values          JSON              NULLABLE
ip_address          String(45)        NULLABLE
created_at          DateTime          NOT NULL, server_default=now()
──────────────────────────────────────────────────────────────

Indexes:
  INDEX(tenant_id, entity_type, entity_id)
  INDEX(tenant_id, created_at DESC)
```

### 5.15 HealthInsurer

**Schema:** shared

```
Table: health_insurers
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
code                String(4)         NOT NULL, UNIQUE
name                String(200)       NOT NULL
iban                String(34)        NOT NULL
bic                 String(11)        NULLABLE
is_active           Boolean           NOT NULL, server_default='true'
created_at          DateTime          NOT NULL, server_default=now()
──────────────────────────────────────────────────────────────

Seed Data:
  24 — Dôvera zdravotná poisťovňa, a.s.
  25 — Všeobecná zdravotná poisťovňa, a.s. (VšZP)
  27 — Union zdravotná poisťovňa, a.s.
```

### 5.16 ContributionRate

**Schema:** shared

```
Table: contribution_rates
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
rate_type           String(50)        NOT NULL (e.g. 'sp_employee_nemocenske')
rate_percent        Numeric(6,4)      NOT NULL
max_assessment_base Numeric(12,2)     NULLABLE
payer               String(20)        NOT NULL, CHECK IN ('employee','employer')
fund                String(50)        NOT NULL
valid_from          Date              NOT NULL
valid_to            Date              NULLABLE
created_at          DateTime          NOT NULL, server_default=now()
──────────────────────────────────────────────────────────────

Indexes:
  INDEX(rate_type, valid_from)
```

### 5.17 TaxBracket

**Schema:** shared

```
Table: tax_brackets
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
bracket_order       Integer           NOT NULL
min_amount          Numeric(12,2)     NOT NULL
max_amount          Numeric(12,2)     NULLABLE
rate_percent        Numeric(5,2)      NOT NULL
nczd_annual         Numeric(10,2)     NOT NULL
nczd_monthly        Numeric(10,2)     NOT NULL
nczd_reduction_threshold Numeric(12,2) NOT NULL
nczd_reduction_formula   String(100)  NOT NULL
valid_from          Date              NOT NULL
valid_to            Date              NULLABLE
created_at          DateTime          NOT NULL, server_default=now()
──────────────────────────────────────────────────────────────

Indexes:
  INDEX(valid_from, bracket_order)
```

### 5.18 StatutoryDeadline

**Schema:** shared

```
Table: statutory_deadlines
──────────────────────────────────────────────────────────────
Column              Type              Constraints
──────────────────────────────────────────────────────────────
id                  UUID              PK, server_default=gen_random_uuid()
code                String(50)        NOT NULL, UNIQUE
name                String(200)       NOT NULL
description         Text              NULLABLE
deadline_type       String(20)        NOT NULL, CHECK IN ('monthly','annual','one_time')
day_of_month        Integer           NULLABLE
month_of_year       Integer           NULLABLE
business_days_rule  Boolean           NOT NULL, server_default='false'
institution         String(100)       NOT NULL
valid_from          Date              NOT NULL
valid_to            Date              NULLABLE
created_at          DateTime          NOT NULL, server_default=now()
──────────────────────────────────────────────────────────────

Seed Data:
  SP_MONTHLY  — Mesačný výkaz SP, day=20, Sociálna poisťovňa
  ZP_MONTHLY  — Mesačný prehľad ZP, day=3, business_days_rule=true, ZP
  TAX_MONTHLY — Preddavok dane, day=last_day, Daňový úrad
  TAX_ANNUAL  — Hlásenie o dani (ročné), month=4 day=30, Daňový úrad
  CERT_ANNUAL — Potvrdenie o príjmoch, month=3 day=10, Zamestnávateľ
  ELDP_ANNUAL — ELDP, month=4 day=30, Sociálna poisťovňa
```

---

## 6. REST API

### 6.1 Auth

```
POST   /api/v1/auth/login            Public. OAuth2 password flow → JWT
POST   /api/v1/auth/logout           Authenticated. Client-side token discard
GET    /api/v1/auth/me               Authenticated. Current user info + role
PUT    /api/v1/auth/change-password   Authenticated. Change own password
```

### 6.2 Users

```
GET    /api/v1/users                 Director. List tenant users
POST   /api/v1/users                 Director. Create user
GET    /api/v1/users/{id}            Director. Get user
PUT    /api/v1/users/{id}            Director. Update user
DELETE /api/v1/users/{id}            Director. Deactivate (soft delete)
```

### 6.3 Health

```
GET    /health                        Public. Service health check
```

### 6.4 Tenants

```
GET    /api/v1/tenants               Director. List tenants
POST   /api/v1/tenants               Director. Create tenant
GET    /api/v1/tenants/{id}          Director. Get tenant
PUT    /api/v1/tenants/{id}          Director. Update tenant
```

### 6.5 Employees

```
GET    /api/v1/employees             Director, Accountant. List (pagination, filters)
POST   /api/v1/employees             Director, Accountant. Create
GET    /api/v1/employees/{id}        All roles (employee: own only). Get detail
PUT    /api/v1/employees/{id}        Director, Accountant. Update
DELETE /api/v1/employees/{id}        Director, Accountant. Soft delete

GET    /api/v1/employees/{id}/children      Director, Accountant. List children
POST   /api/v1/employees/{id}/children      Director, Accountant. Add child
PUT    /api/v1/employees/{id}/children/{cid} Director, Accountant. Update child
DELETE /api/v1/employees/{id}/children/{cid} Director, Accountant. Remove child
```

### 6.6 Contracts

```
GET    /api/v1/employees/{id}/contracts              Director, Accountant. List
POST   /api/v1/employees/{id}/contracts              Director, Accountant. Create
PUT    /api/v1/employees/{id}/contracts/{cid}         Director, Accountant. Update
POST   /api/v1/employees/{id}/contracts/{cid}/terminate Director, Accountant. Terminate
```

### 6.7 Payroll

```
POST   /api/v1/payroll/calculate                     Director, Accountant. Calculate monthly
GET    /api/v1/payroll/{year}/{month}                Director, Accountant. List period
GET    /api/v1/payroll/{year}/{month}/{employee_id}  All roles (employee: own). Get detail
POST   /api/v1/payroll/{year}/{month}/approve        Director. Approve period
POST   /api/v1/payroll/{year}/{month}/recalculate    Director, Accountant. Recalculate (draft only)
```

### 6.8 Pay Slips

```
GET    /api/v1/payslips/{year}/{month}/{employee_id}/pdf   All roles (employee: own). Download PDF
POST   /api/v1/payslips/{year}/{month}/generate-all        Director, Accountant. Batch generate
```

### 6.9 Payments

```
POST   /api/v1/payments/{year}/{month}/generate     Director, Accountant. Generate orders
GET    /api/v1/payments/{year}/{month}               Director, Accountant. List orders
GET    /api/v1/payments/{year}/{month}/sepa-xml      Director, Accountant. Download SEPA
PUT    /api/v1/payments/{id}/status                  Director, Accountant. Update status
```

### 6.10 Reports

```
POST   /api/v1/reports/{year}/{month}/generate       Director, Accountant. Generate all
GET    /api/v1/reports/{year}/{month}                 Director, Accountant. List reports
GET    /api/v1/reports/{id}/download                  Director, Accountant. Download file
PUT    /api/v1/reports/{id}/submit                    Director, Accountant. Mark submitted
```

### 6.11 Leaves

```
GET    /api/v1/leaves                                All roles (employee: own). List (filters)
POST   /api/v1/leaves                                All roles. Create request
PUT    /api/v1/leaves/{id}                           Director, Accountant. Update
POST   /api/v1/leaves/{id}/approve                   Director, Accountant. Approve
POST   /api/v1/leaves/{id}/reject                    Director, Accountant. Reject
GET    /api/v1/leaves/entitlements/{year}            All roles (employee: own). Get entitlements
```

### 6.12 Dashboard

```
GET    /api/v1/dashboard/deadlines                   All roles. Upcoming deadlines
GET    /api/v1/dashboard/summary/{year}/{month}      Director, Accountant. Payroll summary
GET    /api/v1/dashboard/reports-status/{year}/{month} Director, Accountant. Report statuses
GET    /api/v1/dashboard/notifications               All roles. Own notifications
```

### 6.13 Reference Data

```
GET    /api/v1/reference/health-insurers             All roles. List insurers
GET    /api/v1/reference/contribution-rates           All roles. Current rates
GET    /api/v1/reference/tax-brackets                 All roles. Current brackets
GET    /api/v1/reference/deadlines                    All roles. Statutory deadlines
```

### 6.14 Annual Processing

```
POST   /api/v1/annual/{year}/tax-settlement                      Director. Calculate settlement
GET    /api/v1/annual/{year}/income-certificate/{employee_id}/pdf Director, Accountant. Download cert
POST   /api/v1/annual/{year}/tax-report                          Director. Generate annual report
```

### 6.15 NEX Ledger Integration

```
POST   /api/v1/integration/ledger/{year}/{month}/sync   Director. Sync to ledger
GET    /api/v1/integration/ledger/{year}/{month}/status  Director. Sync status
```

### 6.16 Notifications

```
GET    /api/v1/notifications                 All roles. List own notifications
PUT    /api/v1/notifications/{id}/read       All roles. Mark as read
DELETE /api/v1/notifications/{id}            All roles. Delete own notification
```

---

## 7. Frontend

### 7.1 Pages (17)

| Page | Route | Role | Description |
|------|-------|------|-------------|
| LoginPage | /login | Public | Username + password, JWT |
| DashboardPage | / | All | Deadlines, summary, AI alerts |
| EmployeeListPage | /employees | Dir, Acc | Employee list, search, filters |
| EmployeeDetailPage | /employees/:id | All (own) | Tabs: Info, Contracts, Children, Leaves, History |
| EmployeeFormPage | /employees/new | Dir, Acc | Multi-step: Personal → Contract → Tax → Children |
| PayrollListPage | /payroll | Dir, Acc | Payroll periods |
| MonthlyPayrollPage | /payroll/:year/:month | Dir, Acc | All employees for period |
| PayrollDetailPage | /payroll/:year/:month/:id | All (own) | Full breakdown |
| PaymentListPage | /payments | Dir, Acc | Payment periods |
| MonthlyPaymentsPage | /payments/:year/:month | Dir, Acc | Payment orders, SEPA |
| ReportListPage | /reports | Dir, Acc | Report periods |
| MonthlyReportsPage | /reports/:year/:month | Dir, Acc | SP/ZP/DÚ reports |
| LeaveListPage | /leaves | All | Leave requests, approval |
| LeaveCalendarPage | /leaves/calendar | Dir, Acc | Team calendar |
| AnnualPage | /annual/:year | Director | Tax settlement, certificates |
| LedgerIntegrationPage | /integration/ledger | Director | Sync status |
| SettingsPage | /settings | Director | Tenant settings, rates |
| UserManagementPage | /settings/users | Director | User CRUD, roles |

### 7.2 Layout Components

```
AppShell.tsx          Main layout + auth guard (redirect to /login)
Sidebar.tsx           Navigation filtered by role
Header.tsx            TenantSelector, user display (name+role), NotificationBell, logout
TenantSelector.tsx    Tenant switching dropdown
NotificationBell.tsx  Badge with unread count, dropdown
```

### 7.3 Shared Components

```
DataTable.tsx         Reusable TanStack Table
Pagination.tsx        Pagination controls
FormField.tsx         Reusable form field with validation
```

### 7.4 Zustand Stores (6)

```
authStore.ts          token, currentUser, login(), logout(), isAuthenticated (memory, NOT localStorage)
tenantStore.ts        currentTenant, setTenant
employeeStore.ts      selectedEmployee
referenceStore.ts     healthInsurers, rates, brackets (cached)
payrollStore.ts       currentPeriod, filters
notificationStore.ts  unreadCount, notifications
```

---

## 8. Deferred Items

| Code | Description | Reason |
|------|-------------|--------|
| W-01 | Exekúcie a zrážky | Phase V (complex legislation) |
| W-02 | eDane XML export | Waiting for FS API specification |
| W-03 | Self-service portál (employee frontend) | Phase V |
| W-04 | NEX Ledger ImportService status state machine | NEX Ledger scope |
| W-05 | NEX Ledger AccountService normal_balance awareness | NEX Ledger scope |
| W-06 | JWT refresh tokens | Low priority for internal ERP |
| W-07 | Force password change on first login | UX improvement |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v0.1 | 2.4.2026 | Initial version, 7 sections, 14 entities |
| v0.2 | 2.4.2026 | +User, +StatutoryDeadline, +PaySlip, +Notification (18 entities). +Auth/RBAC (Section 2.3). +Auth/Users API. +LoginPage, +UserManagementPage. +W-06, W-07 deferred items. |