# CLAUDE.md — Hospital Operations Intelligence System

## Project Overview
MBATech Data Science project, Semester IV, NMIMS MPSTME Mumbai.
A Hospital Operations Intelligence System with an NL-to-SQL AI layer.

## Tech Stack
- Database: PostgreSQL 16 (hospital_db)
- Backend: FastAPI + SQLAlchemy + Pydantic + JWT auth
- AI Layer: Google Gemini API (gemini-1.5-flash) for NL-to-SQL — free tier
- Frontend: Streamlit dashboard (Python)
- Frontend libs: streamlit==1.35.0, plotly==5.22.0, requests==2.31.0
- Seeding: Python Faker (locale en_IN)

## Database
- Host: localhost:5432
- Database: hospital_db
- Main user: hospital_user (full access)
- Readonly user: hospital_readonly (SELECT only — used by NL-to-SQL)
- Schema file: database/schema.sql
- Seed file: database/seed.py

## Schema — 9 Tables (canonical reference)
patients(patient_id PK, name, dob, gender, blood_type, contact, address)
doctors(doctor_id PK, name, department_id FK, specialization, contact, years_experience)
departments(department_id PK, name, head_doctor, floor_number)
appointments(appointment_id PK, patient_id FK, doctor_id FK, scheduled_at, status, notes)
admissions(admission_id PK, patient_id FK, doctor_id FK, bed_id FK, admitted_at, discharged_at, diagnosis)
beds(bed_id PK, department_id FK, ward_type, status)
prescriptions(prescription_id PK, admission_id FK, doctor_id FK, medication, dosage, duration_days, prescribed_at)
billing(bill_id PK, patient_id FK, admission_id FK, total_amount, paid_amount, payment_status, billed_at)
inventory(item_id PK, department_id FK, item_name, category, quantity, reorder_level, unit_cost)

## Project Structure
hospital-ops/
├── CLAUDE.md
├── README.md
├── backend/
│   ├── .env
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── __init__.py
│       ├── db/
│       │   └── __init__.py
│       ├── models/
│       │   └── __init__.py
│       ├── routers/
│       │   └── __init__.py
│       └── schemas/
│           └── __init__.py
├── database/
│   ├── schema.sql
│   └── seed.py
└── frontend/
    └── dashboard.py

## API Endpoints
### Auth
- POST /auth/register
- POST /auth/login

### CRUD (all 9 resources)
- GET/POST /patients
- GET/POST /doctors
- GET/POST /departments
- GET/POST /appointments
- GET/POST /admissions  ← atomic transaction: also updates beds.status
- GET/POST /beds
- GET/POST /prescriptions
- GET/POST /billing
- GET/POST /inventory

### Analytics (4 endpoints)
- GET /analytics/bed-occupancy
- GET /analytics/revenue-trend
- GET /analytics/doctor-load
- GET /analytics/inventory-alerts

### NL-to-SQL
- POST /query/natural  ← centrepiece demo feature
  Uses: google-generativeai==0.7.2

## NL-to-SQL Rules
- Accepts: {"question": "..."}
- Injects full schema into Claude system prompt
- Validates: must start with SELECT, blocks DROP/DELETE/UPDATE/INSERT/TRUNCATE/ALTER
- Executes against hospital_readonly user with 5s timeout
- Returns: {question, sql, columns, rows, row_count}

## Key Design Decisions (for report/viva)
1. PostgreSQL chosen for ACID guarantees — hospital ops are transactional
2. Admissions endpoint is atomic — admit patient + update bed status in one transaction
3. Read-only DB user for NL-to-SQL — security layer against destructive queries
4. 3NF normalisation — no redundant data, all FKs enforced
5. OLTP design — optimised for row-level transactions not aggregations
6. Indexes on all FK columns — JOIN performance on 5000+ row tables

## Workflow Rules for Claude Code
- Always verify file exists before editing
- Never hardcode credentials — always read from .env
- Always use canonical column names from schema above
- For any SQL, use PostgreSQL syntax
- After writing any Python file, check imports are complete
- Seed script must respect FK insertion order

### Workflow Orchestration

**1. Plan Mode Default**
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately
- Use plan mode for verification steps, not just building
- Write detailed specs upfront before writing any code — reduce ambiguity first

**2. Subagent Strategy**
- Keep main context window clean and focused
- Offload research, exploration, and parallel analysis when needed
- For complex problems, throw more thinking at it before coding
- One task at a time — focused execution only

**3. Self-Improvement Loop**
- After ANY correction from me, update your understanding of the pattern
- Write mental rules for yourself that prevent the same mistake again
- Ruthlessly iterate until mistake rate drops
- Review lessons at the start of each session for relevant context

**4. Verification Before Done**
- NEVER mark a task complete without proving it works
- Diff behavior between expected and actual output when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run through logic, check outputs, demonstrate correctness before presenting

**5. Demand Elegance (Balanced)**
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: implement the elegant solution instead
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it to me

**6. Autonomous Bug Fixing**
- When given a bug or error: just fix it, don't ask for hand-holding
- Point at logs, errors, and failing outputs — then resolve them
- Zero context switching required from me
- Go fix the problem without being told exactly how

### Task Management — Every Session

1. **Plan First:** Write plan with checkable items before starting
2. **Verify Plan:** Check in before starting implementation
3. **Track Progress:** Mark items complete as you go
4. **Explain Changes:** Give high-level summary at each step
5. **Document Results:** Add review notes after each milestone
6. **Capture Lessons:** Update understanding after any corrections

### Core Principles

- **Simplicity First:** Make every change as simple as possible. Impact minimal code.
- **No Laziness:** Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact:** Only touch what's necessary. No side effects, no new bugs.

---


