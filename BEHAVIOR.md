# BEHAVIOR.md — NEX Payroll

**Verzia**: v0.1  
**Dátum**: 2026-04-05  
**Stav**: Draft  
**Komplementárny k**: DESIGN.md v0.2  
**Legal framework**: Zákon č. 311/2001 Z.z. (Zákonník práce), Zákon č. 461/2003 Z.z. (Sociálne poistenie), Zákon č. 580/2004 Z.z. (Zdravotné poistenie), Zákon č. 595/2003 Z.z. (Daň z príjmov)

**Legenda markerov**:
- `[TO VERIFY]` — hodnota alebo tvrdenie vyžaduje overenie proti reálnym dátam 2025
- `[PLACEHOLDER]` — sekcia má byť rozpracovaná v nasledujúcich verziách
- `[STATUTORY]` — hodnota definovaná zákonom, musí byť pravidelne aktualizovaná

---

## 0. Executive Summary

NEX Payroll je **AI-native mzdový systém** pre **malé a stredné firmy na Slovensku** (1-100 zamestnancov), ktorý umožňuje **kompletné spracovanie miezd, odvodov, daní a statutory hlásení bez externej mzdovej účtovníčky**.

Kľúčové prípady použitia:
- Mesačná mzdová uzávierka s výpočtom hrubej mzdy, odvodov a dane
- Generovanie výplatných pások a platobných príkazov do banky
- Mesačné hlásenia Sociálnej poisťovni, zdravotným poisťovniam a daňovému úradu
- Evidencia dovoleniek, PN, OČR, materských a rodičovských dovoleniek
- Ročné zúčtovanie dane pre zamestnancov

**Cieľová skupina**: ICC s.r.o. ako prvý zákazník (12 zamestnancov), neskôr ďalší slovenskí zamestnávatelia.

---

## 1. Actors & Roles

### 1.1 {{actor: payroll_administrator}}

**Popis**: Mzdová účtovníčka alebo osoba zodpovedná za spracovanie miezd. V malej firme typicky majiteľ, konateľ alebo interný účtovník.  
**Autorita**: Plný prístup k všetkým mzdovým funkciám — vytváranie zamestnancov, spracovanie miezd, generovanie hlásení, schvaľovanie výplat.  
**Typické činnosti**:
- Každodenné: evidencia PN, dovoleniek, zmien údajov zamestnancov
- Mesačne: mzdová uzávierka, generovanie výplatných pások, odoslanie hlásení
- Ročne: ročné zúčtovanie dane, výkaz DÚ

**Počet v systéme**: 1-2 na tenant  
**Mapovanie na DB**: [[entity:User]] s role=`payroll_admin`

**Príklad**:
> Mária Kováčová, 15 rokov skúseností ako mzdová účtovníčka, spracováva mzdy pre ICC s.r.o. Každý mesiac 25. robí uzávierku za predchádzajúci mesiac, generuje výplatné pásky a odosiela hlásenia. Používa NEX Payroll denne.

### 1.2 {{actor: company_director}}

**Popis**: Štatutár firmy (konateľ, riaditeľ). Schvaľuje výplaty pred odoslaním do banky a má prístup k súhrnným reportom.  
**Autorita**: Read-only na mzdové dáta, schvaľovanie platobných príkazov, prístup k súhrnným reportom pre firmu.  
**Typické činnosti**: Mesačné schválenie mzdovej uzávierky, review nákladov na mzdy  
**Mapovanie na DB**: [[entity:User]] s role=`director`

### 1.3 {{actor: employee}}

**Popis**: Zamestnanec firmy, subjekt mzdového spracovania.  
**Autorita**: Read-only na vlastné mzdové údaje, download vlastných výplatných pások, change password.  
**Typické činnosti**: Zobrazenie výplatnej pásky, sťahnutie potvrdenia o príjme  
**Mapovanie na DB**: [[entity:Employee]] + [[entity:User]] s role=`employee`  
**Poznámka**: Self-service portál je deferred (W-03) — v Phase 1-6 implementácie len admin prístup k employee dátam.

### 1.4 {{actor: social_insurance_agency}}

**Popis**: Sociálna poisťovňa (SP) — externá autorita  
**Rozhranie**: XML export, manuálny upload cez eSlužby SP portál (automatizácia cez API v budúcnosti)  
**Frekvencia**: Mesačne do 20. dňa nasledujúceho mesiaca (mesačný výkaz preddavkov), registrácia/odregistrácia do 8 dní

### 1.5 {{actor: health_insurer}}

**Popis**: Zdravotná poisťovňa (Dôvera, VšZP, Union) — 3 aktívne poisťovne na Slovensku  
**Rozhranie**: XML export per poisťovňa, manuálny upload cez ePobočku  
**Frekvencia**: Mesačne do 20. dňa nasledujúceho mesiaca  
**Poznámka**: Každý zamestnanec môže byť v inej poisťovni, systém musí spravovať paralelné výkazy.

### 1.6 {{actor: tax_office}}

**Popis**: Daňový úrad Slovenskej republiky (Finančná správa SR)  
**Rozhranie**: eDane XML, portál Finančnej správy  
**Frekvencia**: Mesačne (preddavky na daň do 5. dňa nasl. mesiaca), ročne (výkaz za celý rok do 31.3. ďalšieho roka)

### 1.7 {{actor: bank}}

**Popis**: Banka firmy (Tatra banka, Slovenská sporiteľňa, VÚB, atď.)  
**Rozhranie**: SEPA XML (ISO 20022 pain.001) platobné príkazy  
**Frekvencia**: Mesačne (mzdy), ad-hoc (preddavky, odvody)

---

## 2. Entry Points

### 2.1 {{entry: web_login}}

**URL**: `https://payroll.isnex.eu/login`  
**Actor**: [[actor:payroll_administrator]], [[actor:company_director]], [[actor:employee]]  
**Autentifikácia**: email + heslo, JWT token  
**Session**: 8 hodín (mzdová účtovníčka typicky pracuje v rámci pracovného dňa)  
**Pri zlyhaní**: chybová hláška, max 5 pokusov za 15 minút, potom account lock  
**Dvojfaktorová autentifikácia**: Voliteľná pre admin roles `[PLACEHOLDER]`

### 2.2 {{entry: scheduled_reminders}}

**Spúštač**: cron, denne 08:00  
**Účel**: Pripomienky na blížiace sa statutory deadliny  
**Príklady**:
- "Do 5 dní (20. apríla) je potrebné odoslať mesačný výkaz SP za marec"
- "Zamestnankyňa Jana Horváthová má dnes posledný deň materskej dovolenky — overte návrat do práce"
- "Minimálna mzda 2026 vstúpila do platnosti 1.1. — overte všetky kontrakty"

### 2.3 {{entry: scheduled_payroll_close_assist}}

**Spúštač**: cron, 25. deň mesiaca, 06:00  
**Účel**: AI agent pripraví návrh mzdovej uzávierky a upozorní administrátora  
**Správanie**: Agent načíta všetky zmeny za mesiac, detekuje anomálie, pripraví draft payroll, pošle notifikáciu.  
**Poznámka**: AI-native feature, reflektuje NEX Automat filozofiu (AI monitoruje a proaktívne koná).

---

## 3. Core Workflows (Happy Paths)

---

### 3.1 {{workflow: employee_onboarding}}

**Cieľ**: Zaevidovať nového zamestnanca do systému pri nástupe do pracovného pomeru  
**Actor**: [[actor:payroll_administrator]]  
**Frekvencia**: Ad-hoc, typicky 1-5x mesačne  
**Priorita**: Kritická

**Precondition**:
- Actor je prihlásený s role `payroll_admin`
- Zamestnanec má platný občiansky preukaz (rodné číslo, meno, adresa)
- Zamestnanec má zvolenú zdravotnú poisťovňu (Dôvera / VšZP / Union)
- Je podpísaná pracovná zmluva alebo dohoda (DoVP, DoBPŠ, DoPČ)

**Steps**:

| # | Actor action | System response |
|---|--------------|-----------------|
| 1 | Actor klikne "Zamestnanci" → "Pridať nového" | System zobrazí formulár "Nový zamestnanec" so sekciami: Osobné údaje, Kontakt, Pracovný pomer, Mzda, Daňový bonus, Bankové údaje |
| 2 | Actor vyplní: meno, priezvisko, rodné číslo, adresa, kontakt | System real-time validuje rodné číslo (checksum + vek >= 15 rokov) |
| 3 | Actor vyberie zdravotnú poisťovňu zo zoznamu [[entity:HealthInsurer]] | System zobrazí kód poisťovne (25, 27, 24) |
| 4 | Actor nastaví typ pracovného pomeru: TPP (trvalý), Skrátený úväzok, DoVP, DoBPŠ, DoPČ | System zobrazí príslušné povinné polia podľa typu (napr. hodinová sadzba pre dohody) |
| 5 | Actor zadá: dátum nástupu, hrubú mzdu (EUR/mesiac), úväzok (1.0 = plný) | System validuje že hrubá mzda >= minimálna mzda prispôsobená úväzku (rule 6.1) |
| 6 | Actor pridá vyživované deti (ak existujú) — meno, rodné číslo, typ: dieťa do 6 / do 18 / študent do 25 | System pre každé dieťa validuje rodné číslo a umožní daňový bonus |
| 7 | Actor zadá IBAN zamestnanca pre výplatu mzdy | System validuje IBAN checksum a formát |
| 8 | Actor klikne "Vytvoriť zamestnanca" | System uloží záznam, vygeneruje zamestnanecké číslo, odošle registráciu do SP/ZP queue, presmeruje na detail zamestnanca |

**Postcondition**:
- Nový záznam [[entity:Employee]] s statusom `active`
- Nový záznam [[entity:Contract]] s dátumom začiatku a statusom `active`
- Záznamy [[entity:EmployeeChild]] pre každé dieťa (ak relevantné)
- Registrácia do SP v queue (odoslanie do 8 dní je legal requirement)
- Audit log záznam o vytvorení
- Notifikácia directorovi (informačná)

**Data touched**: [[entity:Employee]], [[entity:Contract]], [[entity:EmployeeChild]], [[entity:HealthInsurer]], [[entity:AuditLog]], [[entity:Notification]]

**Test scenario**: `tests/e2e/test_employee_onboarding.py::test_happy_path`

**Konkrétny príklad**:
> Mária (mzdová účtovníčka) dňa 28.4.2026 zaeviduje nového zamestnanca **Ján Novák** (rodné číslo 950315/1234, narodený 15.3.1995). Nastúpil 1.5.2026 na TPP s mzdou 1500€/mesiac, plný úväzok. Má 1 dieťa (Emma Nováková, 2 roky). Zdravotná poisťovňa: Dôvera. IBAN: SK89 1100 0000 0012 3456 7890.  
> System vytvorí Employee ID=42, Contract ID=156, EmployeeChild ID=78. Odošle registráciu do SP (deadline 8.5.2026). Audit log zaznamená vytvorenie.

**Validation test target**: Tento workflow musí produkovať identické ID-ka a výstupy ako reálna evidencia ICC z roku 2025.

---

### 3.2 {{workflow: monthly_payroll_closure}}

**Cieľ**: Vykonať kompletnú mzdovú uzávierku za daný mesiac pre všetkých aktívnych zamestnancov  
**Actor**: [[actor:payroll_administrator]]  
**Frekvencia**: Mesačne, typicky 25.-28. deň predchádzajúceho mesiaca  
**Priorita**: Kritická (core business process)

**Precondition**:
- Aktuálny mesiac je `closed=false` v [[entity:Payroll]]
- Všetky predchádzajúce mesiace sú `closed=true`
- Všetky PN, dovolenky, OČR za tento mesiac sú zaevidované
- Všetky odmeny, prémie, zrážky sú zaevidované
- Contribution rates ([[entity:ContributionRate]]) pre daný mesiac sú v systéme
- Tax brackets ([[entity:TaxBracket]]) pre daný rok sú v systéme
- Minimálna mzda ([[entity:StatutoryDeadline]] alebo config) je aktuálna

**Steps**:

| # | Actor action | System response |
|---|--------------|-----------------|
| 1 | Actor navigates na "Mzdy" → vyberie mesiac (napr. Marec 2026) | System zobrazí stav mesiaca: `draft` / `calculated` / `approved` / `closed` |
| 2 | Actor klikne "Spustiť uzávierku" | System spustí AI agenta (NEX Automat pattern) ktorý: načíta všetkých aktívnych zamestnancov pre daný mesiac, načíta všetky evidované zmeny (PN, dovolenky, odmeny), validuje kompletnosť dát |
| 3 | System zobrazí "Pre-uzávierka checklist" s výsledkami validácie | Actor vidí napr. "12 zamestnancov pripravených", "2 varovania: chýba evidencia dovolenky pri 2 zamestnancoch" |
| 4 | Actor rieši varovania (vráti sa na krok evidencie alebo akceptuje ich) | System zapíše akceptované varovania do audit log |
| 5 | Actor klikne "Vypočítať mzdy" | System pre každého zamestnanca vypočíta: hrubú mzdu, odpracované dni, dovolenkový priemer, odvody (zamestnanec + zamestnávateľ), daň, čistú mzdu. Výsledky ukladá do [[entity:Payroll]] s statusom `calculated` |
| 6 | System zobrazí súhrnnú tabuľku: meno zamestnanca, hrubá mzda, odvody, daň, čistá mzda, k výplate | Actor review jednotlivé riadky |
| 7 | Actor klikne na konkrétneho zamestnanca pre detail | System zobrazí výpočet krok po kroku: hrubá mzda → zrážky dovolenkového priemeru → odvody ZP 4% / SP 9.4% → zdaniteľná mzda → odpočítateľná položka → daň 19% → daňový bonus na deti → čistá mzda |
| 8 | Actor klikne "Odoslať na schválenie" | System zmení status payroll na `pending_approval`, pošle notifikáciu directorovi |
| 9 | Director (iná session) schváli | Status → `approved` |
| 10 | Actor klikne "Generovať výplatné pásky" | System pre každého zamestnanca vygeneruje [[entity:PaySlip]] (PDF) |
| 11 | Actor klikne "Generovať platobný príkaz do banky" | System vytvorí [[entity:PaymentOrder]] SEPA XML so všetkými výplatami |
| 12 | Actor stiahne SEPA XML a nahrá do internet bankingu | Extern proces |
| 13 | Actor klikne "Generovať mesačné výkazy" | System pre každú SP/ZP kombináciu vygeneruje XML výkazy ([[entity:MonthlyReport]]) |
| 14 | Actor stiahne výkazy a nahrá na portály SP / zdravotných poisťovní / DÚ | Extern proces |
| 15 | Actor klikne "Uzavrieť mesiac" | System zmení status na `closed`, zamkne všetky súvisiace záznamy pred úpravami. Vytvorí notifikáciu všetkým zamestnancom "Výplatná páska za marec je pripravená" |

**Postcondition**:
- [[entity:Payroll]] pre daný mesiac status `closed`
- 12x [[entity:PaySlip]] PDF vygenerované
- 1x [[entity:PaymentOrder]] SEPA XML
- 3x [[entity:MonthlyReport]] XML (SP, ZP, DÚ — per poisťovňa)
- Audit log záznamy o každom kroku
- Notifikácie všetkým zamestnancom
- Nasledujúci mesiac automaticky v stave `draft`, pripravený na evidenciu

**Data touched**: [[entity:Employee]], [[entity:Contract]], [[entity:Payroll]], [[entity:PaySlip]], [[entity:PaymentOrder]], [[entity:MonthlyReport]], [[entity:ContributionRate]], [[entity:TaxBracket]], [[entity:Leave]], [[entity:AuditLog]], [[entity:Notification]]

**Test scenario**: `tests/e2e/test_monthly_payroll_closure.py::test_happy_path_12_employees`

**Konkrétny príklad**:
> Mária dňa 28.4.2026 spúšťa uzávierku za marec 2026. Pre ICC s.r.o. (12 aktívnych zamestnancov). Všetci mali plný mesiac bez PN/dovolenky okrem Jána Nováka, ktorý mal 3 dni dovolenky (15.-17.3). System vypočíta hrubé mzdy, aplikuje dovolenkový priemer pre Jána, vypočíta odvody (13.4% zamestnanec, 35.2% zamestnávateľ). Celkový mesačný náklad na mzdy: ~18,000€ hrubého + 6,336€ odvody zamestnávateľa = 24,336€. Čisté výplaty spolu: ~13,200€. Generuje 12 výplatných pások, 1 SEPA XML platobný príkaz, 3 výkazy (SP, Dôvera, VšZP — podľa poisťovní zamestnancov). `[TO VERIFY]`

**Validation test target**: Tento workflow na reálnych dátach ICC z roku 2025 musí produkovať identické hrubé/čisté mzdy, odvody a daň ako mzdová účtovníčka. Tolerancia: 0 centov.

---

### 3.3 {{workflow: sick_leave_crossing_month_boundary}}

**Cieľ**: Správne spracovať pracovnú neschopnosť (PN) zamestnanca ktorá prechádza cez prelom mesiaca  
**Actor**: [[actor:payroll_administrator]]  
**Frekvencia**: Občasne (5-10 PN za rok v 12-zamestnaneckej firme)  
**Priorita**: Vysoká — chybný výpočet spôsobí incident s SP a finančné straty

**Precondition**:
- Zamestnanec má platný pracovný pomer (status [[entity:Contract]] = `active`)
- Zamestnanec doručil papierové Potvrdenie o dočasnej pracovnej neschopnosti (PN)
- Dátum začiatku PN je v minulosti alebo aktuálny deň
- PN trvá cez prelom mesiaca (napr. 28.3.2026 — 5.4.2026)

**Steps**:

| # | Actor action | System response |
|---|--------------|-----------------|
| 1 | Actor otvorí detail zamestnanca (napr. Ján Novák) | System zobrazí sekciu "Absencie" |
| 2 | Actor klikne "Pridať PN" | System zobrazí formulár: dátum od, dátum do (predpoklad), dôvod, číslo PN od lekára |
| 3 | Actor zadá: dátum od=28.3.2026, dátum do=5.4.2026, číslo PN=XY123456 | System validuje: dátum do >= dátum od, zamestnanec v danom období aktívny |
| 4 | System **detekuje prechod cez prelom mesiaca** a zobrazí upozornenie: "PN prechádza cez 2 mesiace (marec-apríl). PN bude automaticky rozdelená pre správne spracovanie v oboch mesačných uzávierkach." | Informácia pre actora |
| 5 | Actor potvrdí uloženie | System vytvorí DVA záznamy [[entity:Leave]]: (a) PN marec 28.-31.3. (4 dni), (b) PN apríl 1.-5.4. (5 dní) — oba prepojené cez `parent_leave_id` |
| 6 | System automaticky aplikuje pravidlo: **prvé 3 dni PN platí zamestnávateľ (55% denného priemeru)**, 4.-10. deň zamestnávateľ (55%), od 11. dňa Sociálna poisťovňa (55%) | Výpočet per deň, zohľadní continuity cez mesiac |
| 7 | Actor vidí prehľad: "28.3. (1. deň PN, 55% zamestnávateľ), 29.3. (2. deň), 30.3. (3. deň), 31.3. (4. deň), 1.4. (5. deň), 2.4. (6. deň), 3.4. (7. deň), 4.4. (8. deň), 5.4. (9. deň)" | Všetky v úhrade zamestnávateľa (prvých 10 dní) |
| 8 | Actor klikne "Uložiť" | System zaeviduje, aktualizuje zamestnancovu dostupnosť, odošle notifikáciu directorovi |

**Postcondition**:
- 2x [[entity:Leave]] záznamy s `type=sick_leave`, prepojené cez parent_leave_id
- Obidva záznamy status `approved`
- Denné sumy náhrady mzdy vypočítané korektne per deň
- Pri marcovej mzdovej uzávierke: PN 28.-31.3. sa zaráta do marcovej mzdy (4 dni náhrady mzdy)
- Pri aprílovej mzdovej uzávierke: PN 1.-5.4. sa zaráta do aprílovej mzdy (5 dní náhrady mzdy, pokračovanie z marca)
- V oboch mesiacoch sa správne vypočíta denný priemer **z predchádzajúceho štvrťroka** (dovolenkový priemer) `[TO VERIFY — či nie je iný výpočet pre PN]`

**Data touched**: [[entity:Leave]], [[entity:Employee]], [[entity:Contract]], [[entity:AuditLog]]

**Test scenario**: `tests/e2e/test_sick_leave.py::test_crossing_month_boundary`

**Konkrétny príklad**:
> Ján Novák ochorie 28.3.2026 (sobota) s chrípkou. Lekár mu vystaví PN do 5.4.2026 (nedeľa). Mária 30.3.2026 (pondelok) eviduje PN v systéme: od=28.3., do=5.4. System detekuje prechod mesiaca, vytvorí 2 záznamy. Pri marcovej uzávierke (28.4.): Ján má odpracovaných 19 dní + 4 dni PN. Hrubá mzda za marec: (19/23 * 1500€) + (4 * denný priemer * 0.55). Pri aprílovej uzávierke (28.5.): Ján má 17 odpracovaných dní + 5 dní PN (pokračovanie). Oba mesiace vypočítajú náhradu mzdy, oba v úhrade zamestnávateľa (prvých 10 dní). `[TO VERIFY]`

**Edge cases spojené s týmto workflow**:
- [[edge:sick_leave_longer_than_10_days]] — od 11. dňa platí SP, nie zamestnávateľ
- [[edge:sick_leave_during_vacation]] — dovolenka sa ruší, PN nahradí
- [[edge:sick_leave_during_employment_termination]] — ochranná doba, zamestnanec nemôže byť prepustený počas PN

**Validation test target**: Presná suma náhrady mzdy per deň musí zodpovedať výpočtu mzdovej účtovníčky na centy. Kľúčové kontrolné body: správny denný priemer, správne rozhranie 10. dňa medzi zamestnávateľom a SP.

---

### 3.4–3.15 Ďalšie Core Workflows `[PLACEHOLDER]`

Nasledujúce workflows sú identifikované ako kritické pre NEX Payroll. Budú dopracované počas Phase 4-6 implementácie a validation testov s dátami 2025.

| # | Anchor | Stručný popis | Priorita |
|---|--------|---------------|----------|
| 3.4 | `{{workflow: vacation_request_approval}}` | Evidencia dovolenky zamestnanca, schvaľovanie, výpočet dovolenkového priemeru | Vysoká |
| 3.5 | `{{workflow: maternity_leave_start}}` | Nástup zamestnankyne na materskú dovolenku, prechod z mzdy na SP dávky | Vysoká |
| 3.6 | `{{workflow: parental_leave_transition}}` | Prechod z materskej na rodičovskú dovolenku (28 týždňov / 34 / 37) | Vysoká |
| 3.7 | `{{workflow: employee_termination}}` | Ukončenie pracovného pomeru — výpočet záverečnej mzdy, odstupné, odhlásenie z SP/ZP | Kritická |
| 3.8 | `{{workflow: annual_tax_reconciliation}}` | Ročné zúčtovanie dane pre zamestnancov (do 31.3. nasl. roka) | Vysoká |
| 3.9 | `{{workflow: wage_change_mid_period}}` | Zmena mzdy počas mesiaca (napr. zvýšenie od 15.) | Stredná |
| 3.10 | `{{workflow: bonus_payment}}` | Jednorazová odmena, prémia, 13. plat — zdanenie, odvody | Stredná |
| 3.11 | `{{workflow: wage_garnishment}}` | Exekúcia na mzdu — výpočet zrážky, výplata oprávnenému | Stredná |
| 3.12 | `{{workflow: dohoda_processing}}` | Spracovanie dohôd mimo pracovného pomeru (DoVP, DoBPŠ, DoPČ) — iné sadzby odvodov | Vysoká |
| 3.13 | `{{workflow: health_insurer_change}}` | Zmena zdravotnej poisťovne zamestnanca (raz ročne, do 30.9.) | Nízka |
| 3.14 | `{{workflow: statutory_deadline_monitoring}}` | AI monitoring nadchádzajúcich statutory deadlinov a automatické pripomienky | Vysoká |
| 3.15 | `{{workflow: monthly_report_generation}}` | Generovanie mesačných výkazov pre SP, ZP, DÚ (XML export) | Vysoká |

Každý z týchto workflows bude mať rovnakú štruktúru ako 3.1-3.3: precondition, steps, postcondition, data touched, konkrétny príklad, validation target.

---

## 4. Edge Cases & Exceptions

### 4.1 {{edge: salary_below_minimum_wage}}

**Parent workflow**: [[workflow:employee_onboarding]], [[workflow:wage_change_mid_period]]  
**Scenario**: Actor sa pokúša nastaviť hrubú mzdu nižšiu ako minimálna mzda prispôsobená úväzku  
**Trigger**: Mzda 600€ pri plnom úväzku v 2026 (minimálna mzda 2026 = `[TO VERIFY, STATUTORY]` ~816€)  
**Expected behavior**:
- System NEULOŽÍ záznam
- Chybová hláška: "Mzda 600€ je pod minimálnou mzdou 816€ pre plný úväzok"
- Focus zostane na poli "hrubá mzda"
- Actor dostane možnosť opraviť alebo zrušiť

**Error code**: E601 (Business rule violation)  
**Recovery**: Actor opraví mzdu na platnú hodnotu

### 4.2 {{edge: health_insurer_not_found}}

**Scenario**: Zamestnanec udá poisťovňu ktorá nie je v systéme (napr. zaniknutá poisťovňa)  
**Trigger**: Search "Apollo" v zozname poisťovní  
**Expected behavior**:
- System zobrazí "Poisťovňa nenájdená"
- Ponúkne 3 aktívne SK poisťovne (Dôvera, VšZP, Union)
- Actor musí vybrať jednu z aktívnych

**Error code**: E100 (Validation error)  
**Recovery**: Actor si overí so zamestnancom a vyberie správnu poisťovňu

### 4.3 {{edge: rodne_cislo_checksum_fail}}

**Scenario**: Rodné číslo neprejde checksum validáciou  
**Trigger**: Actor zadá napr. `950315/9999` (nesprávne modulo 11)  
**Expected behavior**:
- Okamžitá frontend validácia (pred uložením)
- Chybová hláška: "Rodné číslo nie je platné (checksum)"
- System neumožní pokračovať kým actor neopraví

**Error code**: E101 (Invalid identifier)  
**Recovery**: Actor overí rodné číslo na občianskom preukaze

### 4.4 {{edge: payroll_recalculation_after_close}}

**Scenario**: Zamestnanec dodatočne doručí PN papier po uzávierke mesiaca  
**Trigger**: Marec je `closed`, ale 10.4. príde PN papier za 25.-27.3.  
**Expected behavior**:
- System neumožní zmenu v closed mesiaci priamym editom
- Actor musí použiť **"Oprava mzdy"** workflow (separate audit trail)
- Vytvorí sa korekčný záznam v apríli s referencoou na marec
- Generuje sa dodatok k mesačnému výkazu SP
- Audit log detailne zaznamenáva zmenu

**Error code**: E602 (Attempt to modify closed period)  
**Recovery**: Cez korekčný workflow, nie priamy edit

### 4.5 {{edge: missing_contribution_rates_for_year}}

**Scenario**: Začiatok nového roka, legal sadzby neboli aktualizované  
**Trigger**: 1.1.2027, spustenie uzávierky za december 2026 (OK) alebo január 2027 (fail)  
**Expected behavior**:
- Pri pokus o uzávierku január 2027 bez contribution rates: blokujúca chyba
- Hláška: "Contribution rates pre rok 2027 nie sú nakonfigurované. Kontaktujte administrátora."
- AI agent (scheduled job) detekuje missing rates pre nadchádzajúci rok už v decembri a upozorní

**Error code**: E501 (Missing reference data)  
**Recovery**: Administrator aktualizuje [[entity:ContributionRate]] a [[entity:TaxBracket]] pre nový rok

### 4.6 {{edge: bank_account_iban_invalid}}

**Scenario**: Zamestnanec udá IBAN ktorý neprejde checksum  
**Trigger**: IBAN s preklepom  
**Expected behavior**:
- Real-time validácia IBAN checksum (mod-97 algoritmus)
- Chybová hláška: "IBAN nie je platný"
- Actor musí opraviť pred uložením

**Error code**: E102  
**Recovery**: Verifikácia s bankovým výpisom zamestnanca

### 4.7–4.20 Ďalšie edge cases `[PLACEHOLDER]`

| # | Anchor | Parent workflow | Stručný popis |
|---|--------|-----------------|---------------|
| 4.7 | `{{edge: sick_leave_longer_than_10_days}}` | 3.3 | Prechod z employer-paid na SP-paid (od 11. dňa) |
| 4.8 | `{{edge: sick_leave_during_vacation}}` | 3.3, 3.4 | PN počas dovolenky — dovolenka sa ruší |
| 4.9 | `{{edge: maternity_leave_ending_mid_month}}` | 3.5 | Zamestnankyňa sa vráti z MD uprostred mesiaca |
| 4.10 | `{{edge: employee_multiple_contracts}}` | viaceré | Jeden človek má paralelne TPP + DoVP u toho istého zamestnávateľa |
| 4.11 | `{{edge: tax_bonus_child_turns_18}}` | 3.2 | Dieťa má 18. narodeniny v danom mesiaci — bonus sa mení |
| 4.12 | `{{edge: tax_bonus_child_turns_25_student}}` | 3.2 | Dieťa (študent) má 25. narodeniny — bonus končí |
| 4.13 | `{{edge: wage_exceeds_assessment_base_max}}` | 3.2 | Mzda prevyšuje maximálny vymeriavací základ — strop odvodov SP |
| 4.14 | `{{edge: non_monetary_benefit}}` | 3.2 | Nepeňažné plnenie (stravné lístky, auto na súkr. účely) — dopad na zdanenie |
| 4.15 | `{{edge: wage_garnishment_multiple}}` | 3.11 | Zamestnanec má viacero exekúcií — poradie uspokojenia |
| 4.16 | `{{edge: retroactive_wage_change}}` | 3.9 | Zmena mzdy so spätnou platnosťou od predchádzajúceho mesiaca |
| 4.17 | `{{edge: employee_on_unpaid_leave}}` | viaceré | Neplatené voľno — odvody len zdravotné |
| 4.18 | `{{edge: sepa_export_bank_rejection}}` | 3.2 | Banka odmietla SEPA XML pre invalid IBAN jedného zamestnanca |
| 4.19 | `{{edge: sp_monthly_report_rejected}}` | 3.15 | SP portál odmietne mesačný výkaz — missing fields |
| 4.20 | `{{edge: concurrent_payroll_closure}}` | 3.2 | Dvaja admin userі sa pokúšajú spustiť uzávierku súčasne |

---

## 5. State Transitions

### 5.1 {{state_machine: employee}}

**Entity**: [[entity:Employee]]  
**Stavy**: `active`, `on_leave`, `terminated`

**Stavový diagram**:

```
    ┌─────────────────────────────┐
    │                             ↓
 [active] ←──(návrat)── [on_leave]
    │
    │(ukončenie PP)
    ↓
 [terminated] (final)
```

**Tranzície**:

| Z | Do | Trigger | Guard | Actor | Efekt |
|---|-----|---------|-------|-------|-------|
| `active` | `on_leave` | Evidencia MD/RD/PN dlhšie ako 30 dní | Platný dokument (rodný list dieťaťa, PN potvrdenie) | [[actor:payroll_administrator]] | Pozastavenie štandardnej mzdy, notifikácia SP |
| `on_leave` | `active` | Návrat do práce | Dátum návratu dosiahnutý alebo manuálny override | [[actor:payroll_administrator]] | Obnovenie mzdy, recalculation |
| `active` | `terminated` | Ukončenie pracovného pomeru | Dátum ukončenia zadaný, záverečná mzda vypočítaná | [[actor:payroll_administrator]] | Odhlásenie z SP/ZP, final payslip |
| `on_leave` | `terminated` | Ukončenie počas MD/RD (zriedkavé) | Legal check — ochranná doba | [[actor:payroll_administrator]] | Viac validačné kroky |

**Invariants**:
- Z `terminated` nie je návrat (finálny stav). Pre znovu-zamestnanie sa vytvorí nový [[entity:Contract]].
- `active` Employee musí mať aspoň jeden `active` [[entity:Contract]]
- Počas `on_leave` sa mzda nepočíta, ale zamestnanec zostáva v evidencii SP/ZP

### 5.2 {{state_machine: payroll}}

**Entity**: [[entity:Payroll]] (mesačná mzda)  
**Stavy**: `draft` → `calculated` → `pending_approval` → `approved` → `closed`

**Stavový diagram**:

```
 [draft] ─(calc)→ [calculated] ─(submit)→ [pending_approval] ─(approve)→ [approved] ─(close)→ [closed]
                                                    │
                                                    ↓ (reject)
                                              [calculated]
```

**Tranzície**:

| Z | Do | Trigger | Guard | Actor |
|---|-----|---------|-------|-------|
| `draft` | `calculated` | "Vypočítať mzdy" button | Všetky preconditions z 3.2 met | [[actor:payroll_administrator]] |
| `calculated` | `pending_approval` | "Odoslať na schválenie" | Žiadne validation errors | [[actor:payroll_administrator]] |
| `pending_approval` | `approved` | "Schváliť" | Director role | [[actor:company_director]] |
| `pending_approval` | `calculated` | "Zamietnuť s komentárom" | Komentár nie je prázdny | [[actor:company_director]] |
| `approved` | `closed` | "Uzavrieť mesiac" po generovaní pások + výkazov | PaySlips + PaymentOrder + MonthlyReports vygenerované | [[actor:payroll_administrator]] |

**Invariants**:
- Len jeden `active` Payroll per (tenant, month)
- `closed` je finálny — zmeny len cez korekčný workflow
- Payroll nemôže byť `approved` bez 100% calculated employee records

### 5.3 {{state_machine: leave}}

**Entity**: [[entity:Leave]] (dovolenka, PN, OČR, MD, RD)  
**Stavy**: `requested`, `approved`, `active`, `completed`, `rejected`, `cancelled`

`[PLACEHOLDER — plný state diagram v v0.2]`

---

## 6. Business Rules (Invariants)

### 6.1 {{rule: minimum_wage_enforcement}}

**Constraint**: Hrubá mzda zamestnanca na plný úväzok nesmie byť nižšia ako zákonná minimálna mzda platná v danom období.  
**Formula**: `hruba_mzda >= minimalna_mzda_aktualna * uvazok_ratio`  
**Example**: Minimálna mzda 2026 = `[STATUTORY, TO VERIFY]` 816€/mesiac. Pri úväzku 0.5 minimum = 408€.  
**Enforced at**:
- Frontend validation (pri vytváraní/úprave Employee)
- Backend validation (API layer)
- DB constraint CHECK (`hourly_rate * expected_hours >= minimum_wage`)
- Annual audit scan (pri zmene minimálnej mzdy — detekcia kontraktov pod novou minimálkou)

**Porušenie**: Error E601  
**Legal reference**: Zákon č. 663/2007 Z.z. o minimálnej mzde

### 6.2 {{rule: maximum_assessment_base_sp}}

**Constraint**: Pre odvody do Sociálnej poisťovne je zákonom stanovený **maximálny vymeriavací základ** = 7-násobok priemernej mzdy. Odvody sa počítajú len do tejto hranice.  
**Value 2026**: `[STATUTORY, TO VERIFY]` ~10,500€/mesiac  
**Enforced at**: Výpočtový engine v [[workflow:monthly_payroll_closure]]  
**Porušenie**: Silent cap (nie error) — mzda nad strop sa nezarátava do vymeriavacieho základu  
**Legal reference**: Zákon č. 461/2003 Z.z. § 138

### 6.3 {{rule: tax_deductible_item_conditions}}

**Constraint**: Odpočítateľná položka na daňovníka (~479€/mesiac v 2025 `[TO VERIFY]`) platí len ak mesačný základ dane neprevyšuje stanovený limit. Nad limit sa postupne znižuje.  
**Enforced at**: Výpočtový engine — funkcia `calculate_tax_deductible_item(month, annual_income)`  
**Porušenie**: Chybný výpočet dane, risk reklamácie zo strany zamestnanca  
**Legal reference**: Zákon č. 595/2003 Z.z. § 11

### 6.4 {{rule: child_tax_bonus_age_limits}}

**Constraint**: Daňový bonus na dieťa platí do dosiahnutia:
- 6 rokov — vyšší bonus
- 18 rokov (nezaopatrené dieťa) alebo
- 25 rokov (študent denného štúdia)

**Enforced at**: Výpočtový engine, denná re-evaluácia pri cron job  
**Porušenie**: Neoprávnené uplatnenie bonusu → daňový nedoplatok

### 6.5 {{rule: contract_overlap_prevention}}

**Constraint**: Zamestnanec nemôže mať dva `active` kontrakty typu TPP u toho istého zamestnávateľa s prekrývajúcim sa obdobím.  
**Výnimka**: DoVP/DoBPŠ/DoPČ môžu existovať paralelne s TPP (iný typ pomeru).  
**Enforced at**: Backend validation pri vytváraní Contract, DB constraint

### 6.6–6.15 Ďalšie business rules `[PLACEHOLDER]`

| # | Anchor | Popis |
|---|--------|-------|
| 6.6 | `{{rule: rd_vs_md_continuity}}` | Rodičovská dovolenka musí nadväzovať na materskú, bez medzery |
| 6.7 | `{{rule: sick_leave_first_10_days_employer}}` | Prvých 10 dní PN platí zamestnávateľ |
| 6.8 | `{{rule: annual_vacation_minimum}}` | Minimálna ročná dovolenka 4 týždne (5 pre 33+ rokov) |
| 6.9 | `{{rule: termination_notice_period}}` | Výpovedná doba min. 1 mesiac, závisí od trvania PP |
| 6.10 | `{{rule: severance_pay_calculation}}` | Odstupné podľa trvania PP (1x, 2x, 3x priemerná mzda) |
| 6.11 | `{{rule: health_insurance_mandatory}}` | Každý zamestnanec musí mať priradenú ZP |
| 6.12 | `{{rule: dohoda_hour_limits}}` | DoBPŠ max 20 h/týždeň, DoVP max 350 h/rok |
| 6.13 | `{{rule: wage_garnishment_minimum_remaining}}` | Pri exekúcii zamestnancovi musí ostať životné minimum |
| 6.14 | `{{rule: payslip_retention_10_years}}` | Mzdové dokumenty uchovávať 10 rokov |
| 6.15 | `{{rule: social_insurance_registration_8_days}}` | Prihlásenie do SP do 8 dní od nástupu |

---

## 7. Error Taxonomy

| Code | Category | User message (SK) | Developer context | Recovery path |
|------|----------|-------------------|---------------------|---------------|
| E001 | System | "Systémová chyba, skúste znovu neskôr" | Unhandled exception | Retry; escalate |
| E100 | Validation | "Pole '{field}' obsahuje neplatnú hodnotu" | Field-level | User opraví |
| E101 | Validation | "Rodné číslo nie je platné (checksum)" | RC mod-11 fail | Overiť OP |
| E102 | Validation | "IBAN nie je platný (checksum)" | IBAN mod-97 fail | Overiť výpis |
| E200 | Permission | "Nemáte oprávnenie na túto operáciu" | Role check failed | Contact admin |
| E300 | Concurrency | "Záznam bol zmenený iným používateľom" | Optimistic lock | Reload + re-apply |
| E400 | External | "Banka nepotvrdila platobný príkaz" | SEPA XML rejected | Manuálny upload |
| E401 | External | "Sociálna poisťovňa odmietla výkaz" | Missing fields / XML schema | Oprava + resubmit |
| E402 | External | "Zdravotná poisťovňa odmietla výkaz" | Poisťovňa-specific reason | Oprava + resubmit |
| E500 | Data | "Dáta sú v neočakávanom stave" | Consistency check failed | Admin intervention |
| E501 | Data | "Chýbajúce referenčné dáta ({type}) pre rok {year}" | Missing ContributionRate / TaxBracket | Administrator update |
| E601 | Business | "Mzda {amount} je pod minimálnou mzdou {minimum} pre úväzok {ratio}" | Rule 6.1 violated | User opraví mzdu |
| E602 | Business | "Nie je možné upraviť uzatvorený mesiac. Použite korekčný workflow." | Closed period modification attempt | Use correction workflow |
| E603 | Business | "Zamestnanec má prekrývajúce sa pracovné pomery" | Rule 6.5 violated | Ukončiť starý kontrakt najprv |
| E604 | Business | "Daňový bonus nie je možný — dieťa prekročilo vekovú hranicu" | Rule 6.4 violated | Automatic cleanup |
| E901 | Unknown | "Neočakávaná chyba, kontaktujte podporu" | Not in taxonomy | Add to taxonomy |

`[PLACEHOLDER: E7xx sekcia pre reporting errors, E8xx pre archív/audit errors]`

---

## 8. Notifications & Communications

| Trigger | Recipient | Kanál | Content template | Timing |
|---------|-----------|-------|------------------|--------|
| [[workflow:employee_onboarding]] dokončený | [[actor:company_director]] | Email | "Nový zamestnanec {name} bol zaevidovaný, nástup {date}" | Okamžite |
| [[workflow:monthly_payroll_closure]] vypočítaný, čaká na schválenie | [[actor:company_director]] | Email + in-app | "Mzdová uzávierka za {month} je pripravená na schválenie. Celkové náklady: {amount}€" | Okamžite |
| Mzdová uzávierka schválená, payslips vygenerované | Všetci zamestnanci | Email | "Vaša výplatná páska za {month} je pripravená na stiahnutie" | Po `closed` |
| 5 dní pred SP/ZP/DÚ deadline | [[actor:payroll_administrator]] | Email + in-app | "Do {days} dní je potrebné odoslať {report_type} za {month}" | Scheduled daily |
| Minimálna mzda zmenená (nový rok) | [[actor:payroll_administrator]] | In-app banner | "Minimálna mzda 2026 = {amount}€. Overte všetky kontrakty." | 1.1. of new year |
| Contribution rates chýbajú pre nový rok | [[actor:payroll_administrator]] | Email | "Contribution rates pre {year} nie sú nakonfigurované" | 15.12. previous year |
| PN dlhšia ako 10 dní (prechod na SP) | [[actor:payroll_administrator]] | In-app | "PN zamestnanca {name} prekročila 10 dní, od 11. dňa platí SP" | Automatic daily check |
| Dieťa zamestnanca má 18/25 narodeniny | [[actor:payroll_administrator]] | In-app | "Dieťa {child_name} zamestnanca {employee_name} prekročilo vekovú hranicu pre daňový bonus" | Mesačne pred uzávierkou |

---

## 9. Reporting & Audit

### 9.1 {{report: monthly_sp_report}}

**Účel**: Mesačný výkaz preddavkov na poistné do Sociálnej poisťovne  
**Format**: XML podľa SP schema  
**Generuje sa**: Automaticky pri [[workflow:monthly_payroll_closure]] krok 13  
**Submission deadline**: 20. deň nasledujúceho mesiaca  
**Uchovanie**: 10 rokov  
**Legal reference**: Zákon č. 461/2003 Z.z.

### 9.2 {{report: monthly_zp_report}}

**Účel**: Mesačný výkaz preddavkov na zdravotné poistenie  
**Format**: XML per poisťovňa (Dôvera, VšZP, Union — každá má vlastnú schému)  
**Generuje sa**: Automaticky pri uzávierke  
**Submission deadline**: 20. deň nasledujúceho mesiaca

### 9.3 {{report: monthly_du_prehlad}}

**Účel**: Mesačný prehľad o zrazených a odvedených preddavkoch na daň z príjmov  
**Format**: eDane XML (W-02 deferred, zatiaľ manuálny)  
**Submission deadline**: 5. deň druhého mesiaca po výplatnom mesiaci  
**Legal reference**: Zákon č. 595/2003 Z.z.

### 9.4 {{report: annual_hlasenie_du}}

**Účel**: Ročné hlásenie o vyúčtovaní dane a úhrne príjmov (do 31.3. nasl. roka)  
**Format**: eDane XML  
`[PLACEHOLDER]`

### 9.5 {{report: audit_log_export}}

**Účel**: Export audit trailu pre compliance  
**Format**: CSV / JSON  
**Prístup**: [[actor:payroll_administrator]], [[actor:company_director]]  
**Uchovanie**: 10 rokov (legal pre mzdové doklady)

---

## 10. Glossary

| Pojem (SK) | English | Definícia |
|------------|---------|-----------|
| Hrubá mzda | Gross salary | Mzda pred odpočítaním odvodov a dane, zmluvne dohodnutá suma |
| Čistá mzda | Net salary | Suma ktorú zamestnanec skutočne dostane na účet po všetkých zrážkach |
| Superhrubá mzda | Total employer cost / super-gross | Hrubá mzda + odvody zamestnávateľa (35.2%) — celkový náklad pre firmu |
| Odvody | Contributions | Povinné platby do SP (sociálne) a ZP (zdravotné) |
| Vymeriavací základ | Assessment base | Suma z ktorej sa počítajú odvody (väčšinou = hrubá mzda, s hornými a dolnými limitmi) |
| PN | Sick leave / temporary work disability | Pracovná neschopnosť — zamestnanec nemôže pracovať zo zdravotných dôvodov |
| OČR | Care for family member | Ošetrovanie člena rodiny — nárok na dávku, maximum 14 dní/rok |
| Materská dovolenka (MD) | Maternity leave | 34 týždňov pre prvé dieťa, 37 týždňov pre viacpočetný pôrod |
| Rodičovská dovolenka (RD) | Parental leave | Po materskej, do 3 rokov veku dieťaťa, rodičovský príspevok z SP |
| Ročné zúčtovanie dane | Annual tax reconciliation | Vyúčtovanie dane z príjmov za celý rok, do 31.3. nasledujúceho roka |
| Exekúcia na mzdu | Wage garnishment | Súdne nariadená zrážka zo mzdy v prospech veriteľa |
| Výplatná páska | Payslip | Doklad o mzde pre zamestnanca, detailný rozpis hrubej → čistej mzdy |
| Mesačný výkaz | Monthly report | Hlásenie pre SP/ZP/DÚ o odvedených preddavkoch |
| Nepeňažné plnenie | Non-cash benefit | Benefit v naturáliách (stravné lístky, auto, telefón) — podlieha zdaneniu |
| Dohoda (DoVP, DoBPŠ, DoPČ) | Work agreement outside employment relationship | Alternative to employment contract — Dohoda o vykonaní práce (DoVP), Dohoda o brigádnickej práci študentov (DoBPŠ), Dohoda o pracovnej činnosti (DoPČ) |
| Odpočítateľná položka | Tax deductible item | Suma znižujúca základ dane (na daňovníka ~479€/mesiac `[TO VERIFY]`) |
| Daňový bonus | Child tax bonus | Zníženie dane za vyživované deti |
| TPP | Permanent employment contract | Trvalý pracovný pomer |
| Zamestnávateľ | Employer | Firma / fyzická osoba ktorá zamestnáva |
| Zamestnanec | Employee | Osoba v pracovnom pomere |
| SP | Sociálna poisťovňa / Social Insurance Agency | Štátna inštitúcia spravujúca sociálne poistenie |
| ZP | Zdravotná poisťovňa / Health insurer | Súkromná / verejná poisťovňa (Dôvera, VšZP, Union) |
| DÚ | Daňový úrad / Tax office | Finančná správa SR |

---

## 11. Changelog

- **v0.1** (2026-04-05): Initial draft. 3 complete workflows (3.1 onboarding, 3.2 monthly closure, 3.3 sick leave crossing month). 12 workflow placeholders. 6 complete edge cases, 14 placeholders. State machines for Employee + Payroll (skeleton for Leave). 5 complete business rules, 10 placeholders. Error taxonomy E001-E604 + E901. Glossary 25 pojmov. All `[TO VERIFY]` markers flagged for validation test against 2025 real ICC data.

---

## 12. Cross-Reference Index

**Actors**: `actor:payroll_administrator`, `actor:company_director`, `actor:employee`, `actor:social_insurance_agency`, `actor:health_insurer`, `actor:tax_office`, `actor:bank`  

**Workflows complete**: `workflow:employee_onboarding`, `workflow:monthly_payroll_closure`, `workflow:sick_leave_crossing_month_boundary`  

**Workflows placeholder** (v0.2+): `workflow:vacation_request_approval`, `workflow:maternity_leave_start`, `workflow:parental_leave_transition`, `workflow:employee_termination`, `workflow:annual_tax_reconciliation`, `workflow:wage_change_mid_period`, `workflow:bonus_payment`, `workflow:wage_garnishment`, `workflow:dohoda_processing`, `workflow:health_insurer_change`, `workflow:statutory_deadline_monitoring`, `workflow:monthly_report_generation`  

**Edge cases complete**: `edge:salary_below_minimum_wage`, `edge:health_insurer_not_found`, `edge:rodne_cislo_checksum_fail`, `edge:payroll_recalculation_after_close`, `edge:missing_contribution_rates_for_year`, `edge:bank_account_iban_invalid`  

**State machines**: `state_machine:employee`, `state_machine:payroll` (`state_machine:leave` placeholder)  

**Rules complete**: `rule:minimum_wage_enforcement`, `rule:maximum_assessment_base_sp`, `rule:tax_deductible_item_conditions`, `rule:child_tax_bonus_age_limits`, `rule:contract_overlap_prevention`  

**DESIGN.md entity cross-references**: [[entity:Employee]], [[entity:Contract]], [[entity:EmployeeChild]], [[entity:Leave]], [[entity:LeaveEntitlement]], [[entity:Payroll]], [[entity:PaySlip]], [[entity:PaymentOrder]], [[entity:MonthlyReport]], [[entity:ContributionRate]], [[entity:HealthInsurer]], [[entity:StatutoryDeadline]], [[entity:TaxBracket]], [[entity:User]], [[entity:Tenant]], [[entity:Notification]], [[entity:AuditLog]]