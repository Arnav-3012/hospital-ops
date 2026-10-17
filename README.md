# 🏥 Hospital Operations Intelligence System

A hospital back-office platform: a PostgreSQL database, a FastAPI service on top of it, a Streamlit dashboard, and an **AI layer that turns plain English into SQL** ("which department has the most occupied beds?").

> BTech Data Science · Semester IV · NMIMS MPSTME, Mumbai

This README does two jobs: it tells you **how to run** the project, and it explains **how it works and why** it was built this way, so you can read the code, defend the design in a viva, or extend it.

---

## Contents
1. [Big picture](#1-big-picture)
2. [Quick start](#2-quick-start)
3. [The database](#3-the-database)
4. [Authentication and roles](#4-authentication-and-roles)
5. [Admissions: why a transaction matters](#5-admissions-why-a-transaction-matters)
6. [Natural language to SQL](#6-natural-language-to-sql)
7. [Analytics endpoints](#7-analytics-endpoints)
8. [Audit log and undo](#8-audit-log-and-undo)
9. [The Streamlit frontend](#9-the-streamlit-frontend)
10. [API reference](#10-api-reference)
11. [Known limitations](#11-known-limitations)
12. [Viva questions](#12-viva-questions)

---

## 1. Big picture

```
 Streamlit (8501) ──HTTP + JWT──▶ FastAPI (8000) ──SQLAlchemy──▶ PostgreSQL
   dashboard.py                    app/main.py                    hospital_db
   pages/*.py                      app/routers/*                       ▲
                                        │                              │
                                        └─ /query/natural ─▶ Groq LLM ─┘
                                           (SQL generated, then run as the
                                            read-only DB user)
```

Think of it as a hospital front desk with three layers:

- **Database** is the filing room. It stores the truth and refuses bad data (foreign keys, CHECK constraints).
- **FastAPI** is the clerk. Nobody touches the files directly. Every request is checked (who are you? are you allowed? is the data valid?) before the clerk opens a drawer.
- **Streamlit** is the counter staff see. It only talks to the clerk over HTTP, never to the database.

```
hospital-ops/
├── backend/
│   ├── .env.example            # template for secrets (real .env is git-ignored)
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # app creation, CORS, router wiring, OpenAPI bearer auth
│       ├── db/database.py      # engine + session factory + get_db dependency
│       ├── models/models.py    # SQLAlchemy ORM classes (tables as Python objects)
│       ├── schemas/schemas.py  # Pydantic: validates request / shapes response
│       └── routers/            # one file per resource, plus auth, analytics, audit, nl_query
├── database/
│   ├── schema.sql              # CREATE TABLE + indexes
│   └── seed.py                 # Faker (en_IN) data, FK-ordered
└── frontend/
    ├── dashboard.py            # login / register / home
    └── pages/                  # 1_Overview, 2_Doctors, 3_NL_Query, 4_Admin_DB, 5_Database_Info
```

### Anatomy of one request
Take `GET /patients/?limit=10`:

1. **Router** matches the path.
2. **`Depends(get_current_user)`** decodes the JWT. A bad token gives 401.
3. **`Depends(get_db)`** opens a database session and closes it afterwards, even if there's an error.
4. **SQLAlchemy** runs the query. **Pydantic** (`response_model`) converts rows to JSON.

Every endpoint follows this pattern. Dependency injection (`Depends`) is what keeps routers short.

---

## 2. Quick start

**Prerequisites:** Python 3.10+, PostgreSQL 16, a free [Groq API key](https://console.groq.com).

### Database
```bash
createdb hospital_db
psql -d hospital_db -f database/schema.sql
```
Create two users. The second one matters for security (see [section 6](#6-natural-language-to-sql)):
```sql
CREATE USER hospital_user     WITH PASSWORD 'CHANGE_ME';
CREATE USER hospital_readonly WITH PASSWORD 'CHANGE_ME';
GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA public TO hospital_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hospital_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO hospital_readonly;
```
Run these `GRANT`s after `schema.sql` so they cover the tables.

### Backend
```bash
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env       # fill in real values
python database/seed.py                    # 5000+ realistic rows
venv/bin/uvicorn backend.app.main:app --reload --port 8000
```
Open http://localhost:8000/docs for interactive Swagger docs. Click **Authorize** and paste a JWT.

### Frontend
```bash
streamlit run frontend/dashboard.py        # run from the project root
```
Open http://localhost:8501.

### Environment variables (`backend/.env`)
| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Full-access connection used by the CRUD API |
| `READONLY_DATABASE_URL` | SELECT-only connection used for AI-generated queries |
| `GROQ_API_KEY` | LLM access for NL-to-SQL |
| `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT signing and lifetime |
| `SETUP_KEY` | Secret needed to register an *admin* account |

### Default logins
Auto-created on first backend start (when `backend/users.json` doesn't exist):

| User | Password | Role |
|---|---|---|
| admin | admin123 | admin |
| demo | demo123 | user |

⚠️ Demo credentials. Change them, and use a strong `SECRET_KEY` and `SETUP_KEY`, before any real use.

---

## 3. The database

Nine tables with `admissions` as the hub:

```
departments ──< doctors ──< appointments >── patients
     │             │                            │
     ├──< beds     ├──< admissions >────────────┤
     │                    │  ▲ (bed_id)         │
     └──< inventory       ├──< prescriptions    │
                          └──< billing >────────┘
```

| Table | Holds |
|---|---|
| `patients` | demographics: name, dob, gender, blood type, contact |
| `doctors` | staff, with specialization and experience; belongs to a department |
| `departments` | wards such as Cardiology; has a floor and a head doctor |
| `appointments` | scheduled visits (patient + doctor + time + status) |
| `admissions` | inpatient stays (patient + doctor + **bed**, admitted/discharged times) |
| `beds` | physical beds with a `status` (e.g. available, occupied) |
| `prescriptions` | medication given during an admission |
| `billing` | amounts billed and paid for an admission |
| `inventory` | stock per department with a `reorder_level` |
| `audit_log` | change history written by the API (not one of the 9 core tables) |

**Why this shape?**
- **3NF.** A department's name lives in exactly one row. Doctors and beds point to it by ID, so renaming a department is a one-row update.
- **Admissions as the hub.** Prescriptions and bills only make sense during a stay, so they hang off `admission_id`. The database itself enforces that rule.
- **Beds are a separate table.** A bed outlives any single admission, so "is this bed free?" is a property of the bed, not of a stay.
- **Indexes on every FK column.** JOINs such as patients → admissions → prescriptions use index lookups, not full scans.
- **OLTP, not a warehouse.** The design suits many small reads and writes. Heavy aggregations run as SQL on top (see [section 7](#7-analytics-endpoints)).

`seed.py` inserts in dependency order (departments → doctors → patients → beds → …). A child row can't be inserted before the parent it references, or the FK would reject it.

---

## 4. Authentication and roles

Code: [auth.py](backend/app/routers/auth.py)

**Analogy:** a JWT is a wristband at a festival. You show your ID once (login) and get a signed wristband. After that, staff just check that the band is genuine, without calling the ticket office each time.

Flow:
1. `POST /auth/login` checks the username and bcrypt password hash, then returns a JWT containing `{"sub": username, "role": role}`, signed with `SECRET_KEY`.
2. The frontend sends `Authorization: Bearer <token>` on every call.
3. Two reusable guards:
   - `get_current_user`: any valid token.
   - `get_admin_user`: valid token **and** `role == "admin"`, otherwise 403.

| Role | Can do |
|---|---|
| `user` | read everything, run NL queries, view analytics |
| `admin` | all of the above, plus create/update/delete, NL-modify, audit log |

Registering an `admin` account requires the `X-Setup-Key` header to equal `SETUP_KEY`, so strangers can't self-promote.

Passwords are **bcrypt-hashed** (never stored in plain text). Accounts are kept in `backend/users.json`, which is fine for a demo; a production system would use a `users` table.

---

## 5. Admissions: why a transaction matters

Code: [admissions.py](backend/app/routers/admissions.py)

**The problem.** Admitting a patient is really *two* writes: insert an `admissions` row, and set `beds.status = 'occupied'`. If the server crashed between them you'd have either an admission with a "free" bed (double-booking) or an "occupied" bed with nobody in it.

**The fix.** Do both in one **transaction**. They both happen or neither does (the *A* in ACID).

```python
admission = Admission(**payload.model_dump())
db.add(admission)
db.flush()                  # sends the INSERT, but nothing is permanent yet
bed.status = "occupied"     # second write, same transaction
db.commit()                 # both become permanent together
# on any exception: db.rollback() undoes both
```

Before the transaction starts, `POST /admissions/` runs five checks, each returning a clear error:

1. Bed exists → else 404
2. Bed is `available` → else 400
3. Patient exists → else 404
4. Doctor exists → else 404
5. Patient isn't already admitted (no row with `discharged_at IS NULL`) → else 400

`DELETE /admissions/{id}` does the reverse: it frees the bed and deletes the admission in one commit.

---

## 6. Natural language to SQL

Code: [nl_query.py](backend/app/routers/nl_query.py) · UI: [3_NL_Query.py](frontend/pages/3_NL_Query.py)

**Analogy:** you hire a fast, eager translator who knows SQL but has never seen your database. You hand them a cheat-sheet of your tables (the *system prompt*), and they translate each question. Because they're fast but sometimes wrong, you never let them near the filing room with a pen. They get read-only access.

### The pipeline (`POST /query/natural`)
```
question ─▶ [1 LLM] ─▶ [2 clean] ─▶ [3 validate] ─▶ [4 run as read-only user] ─▶ rows
```
1. **Generate.** Groq's `llama-3.1-8b-instant` gets `SCHEMA_CONTEXT` (all 9 tables with exact column names, join rules, table aliases, three worked examples) plus the question. `temperature=0.1` keeps output near-deterministic. Hard-coding the schema and examples is what stops the model inventing columns like `p.doctor_id`.
2. **Clean.** Strip any markdown fences or a stray leading `sql`.
3. **Validate.** The statement must start with `SELECT`. It's rejected if it contains `DROP, DELETE, UPDATE, INSERT, TRUNCATE, ALTER, CREATE`.
4. **Execute** through a *separate* SQLAlchemy engine built from `READONLY_DATABASE_URL`, fetching at most 100 rows.

Response: `{question, sql, columns, rows, row_count}`. The UI shows the generated SQL next to the results so a human can sanity-check what the AI did.

### Defence in depth
| Layer | Stops |
|---|---|
| Prompt rules ("SELECT only", "LIMIT 100") | most bad output (not trusted on its own) |
| Keyword validation | obvious destructive SQL |
| **Read-only DB user** | everything else: even if the filter is bypassed, Postgres itself refuses writes |

The third layer is the real guarantee. String filters can be fooled; database permissions can't.

### Admin-only extensions
- `POST /query/preview` generates SQL for an instruction *without running it*, tagging it `SELECT/INSERT/UPDATE/DELETE`.
- `POST /query/modify` runs INSERT/UPDATE/DELETE via the full-access user. It blocks `DROP/TRUNCATE/ALTER/CREATE/CASCADE/GRANT/REVOKE`, **requires a `WHERE`** on UPDATE/DELETE, and writes an audit entry. The UI preview step exists so an admin reads the SQL before it runs.

---

## 7. Analytics endpoints

Code: [analytics.py](backend/app/routers/analytics.py). All are read-only SQL aggregations behind JWT auth.

| Endpoint | SQL idea | Powers |
|---|---|---|
| `/analytics/bed-occupancy` | `GROUP BY department, status` and `COUNT(*)` | occupancy chart |
| `/analytics/revenue-trend` | `GROUP BY TO_CHAR(billed_at,'YYYY-MM')`; `SUM` of billed, paid, and billed − paid | monthly revenue and outstanding |
| `/analytics/doctor-load` | `LEFT JOIN` appointments and admissions; `COUNT(DISTINCT …)` | workload ranking |
| `/analytics/inventory-alerts` | `WHERE quantity < reorder_level`, ordered by shortage | restock list |

Two details worth knowing:
- **`LEFT JOIN`** keeps doctors with zero appointments in the result. An inner join would silently hide them.
- **`COUNT(DISTINCT …)`** is required in `doctor-load` because joining two one-to-many tables multiplies rows (a doctor with 5 appointments and 3 admissions yields 15 rows). Without `DISTINCT` the counts would be wrong.

---

## 8. Audit log and undo

There are two separate mechanisms:

**Audit log (server side, database).** After a create/update/delete, routers call `write_audit_log(...)`, which inserts a row into `audit_log`: table, operation, record ID, **old values**, **new values** (as JSON), who did it, when, which endpoint. Admins read it via `GET /audit-log/` (filterable) and `/audit-log/summary` (counts per table and operation). If logging itself fails, the error is printed and the main operation still succeeds.

**Undo log (client side, file).** The Admin page records the previous state of edited/deleted records in `backend/undo_log.json`. The *Undo Log* tab can restore them. Created records can't be undone this way; use Delete instead.

---

## 9. The Streamlit frontend

Login lives in `dashboard.py`; the token, username and role are kept in `st.session_state`. Every page checks for the token first and stops if you're not logged in.

| Page | What it does |
|---|---|
| **Home** (`dashboard.py`) | login/register, headline counts |
| **1 Overview** | bed occupancy, revenue trend, inventory alerts (Plotly) |
| **2 Doctors** | doctor workload from `/analytics/doctor-load` |
| **3 NL Query** | example questions, free-text input, generated SQL, results, history |
| **4 Admin DB** | admin console in 10 tabs: Overview, Resources, Discharge, Browse, Add, Edit, Delete, NL Modify, Undo Log, Audit Log |
| **5 Database Info** | schema, relationships, design decisions, live stats (a built-in viva cheat-sheet) |

---

## 10. API reference

| Group | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| CRUD (9 resources) | `/patients`, `/doctors`, `/departments`, `/appointments`, `/admissions`, `/beds`, `/prescriptions`, `/billing`, `/inventory`: list, `/count`, `/{id}`, `POST`, `PUT /{id}`, `DELETE /{id}`; `/search` on most |
| Analytics | `GET /analytics/bed-occupancy · revenue-trend · doctor-load · inventory-alerts` |
| NL | `POST /query/natural`; admin: `POST /query/preview`, `POST /query/modify` |
| Audit (admin) | `GET /audit-log/`, `GET /audit-log/summary` |

Reads need any valid login; writes need `admin`. Full interactive docs are at `/docs`.

---

## 11. Known limitations

Being honest about these is a strength in a viva.

- **No query timeout yet.** `/query/natural` limits results to 100 rows but does not enforce a statement timeout. A slow AI-generated query could run long. Fix: `SET statement_timeout = '5s'` on the read-only connection.
- **Keyword filter is crude.** It does substring matching, so a harmless column such as `updated_at` or `created_at` would be falsely rejected. Safety does not depend on it (the read-only user does), but it can cause false alarms.
- **Audit write is a second commit.** The audit row is written *after* the main commit, so a crash between them could lose the log entry. A stricter design writes both in one transaction or uses a DB trigger.
- **`/query/modify` uses AI-generated writes** on the full-access user. The `WHERE` rule and preview step reduce risk but don't eliminate it; it's admin-only for that reason.
- **Users live in a JSON file** and the undo log in another; use database tables for multi-user deployments.
- **CORS is `*`** and `SETUP_KEY` has a hard-coded fallback in `auth.py`. Set a real value in `.env` and tighten CORS before deploying.
- **Small models make mistakes.** `llama-3.1-8b-instant` can write wrong SQL on complex questions. That's why the SQL is shown to the user.

---



## Tech stack
PostgreSQL 16 · FastAPI · SQLAlchemy 2 · Pydantic 2 · python-jose · passlib/bcrypt · Groq (`llama-3.1-8b-instant`) · Streamlit · Plotly · Faker

## Authors
Arnav Chaturvedi and Rushil: NMIMS MPSTME, Mumbai.
