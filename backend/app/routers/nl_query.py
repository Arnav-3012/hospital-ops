"""
nl_query.py — Natural language to SQL endpoint (powered by Groq).

POST /query/natural
  Accepts a plain-English question, calls Groq (llama-3.1-8b-instant) to
  generate SQL, validates SELECT-only, executes against the read-only DB
  user, and returns the results.
"""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from groq import Groq
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_db
from app.routers.auth import get_admin_user, get_current_user

# ---------------------------------------------------------------------------
# Environment + Groq client
# ---------------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Module-level read-only engine — created once, reused across requests
_readonly_engine = create_engine(
    os.getenv("READONLY_DATABASE_URL"),
    pool_pre_ping=True,
)
_ReadOnlySession = sessionmaker(bind=_readonly_engine)

# Module-level full-access engine — used by /modify endpoint
_full_engine = create_engine(
    os.getenv("DATABASE_URL"),
    pool_pre_ping=True,
)
_FullSession = sessionmaker(bind=_full_engine)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter()

# ---------------------------------------------------------------------------
# Schema context injected as system prompt
# ---------------------------------------------------------------------------
SCHEMA_CONTEXT = """You are a PostgreSQL expert.
Convert the user question to a SQL SELECT query.
Return ONLY the raw SQL query. No explanation, no markdown, no backticks, no comments.

Database schema with exact column names:

patients: patient_id(PK), name, dob, gender, blood_type, contact, address

doctors: doctor_id(PK), name, department_id(FK→departments),
         specialization, contact, years_experience

departments: department_id(PK), name, head_doctor, floor_number

appointments: appointment_id(PK), patient_id(FK→patients),
              doctor_id(FK→doctors), scheduled_at, status, notes

admissions: admission_id(PK), patient_id(FK→patients),
            doctor_id(FK→doctors), bed_id(FK→beds),
            admitted_at, discharged_at, diagnosis

beds: bed_id(PK), department_id(FK→departments), ward_type, status

prescriptions: prescription_id(PK), admission_id(FK→admissions),
               doctor_id(FK→doctors), medication, dosage,
               duration_days, prescribed_at

billing: bill_id(PK), patient_id(FK→patients),
         admission_id(FK→admissions), total_amount,
         paid_amount, payment_status, billed_at

inventory: item_id(PK), department_id(FK→departments),
           item_name, category, quantity, reorder_level, unit_cost

Critical rules:
- doctor_id is in: doctors, appointments, admissions, prescriptions
- patient_id is in: patients, appointments, admissions, billing
- department_id is in: departments, doctors, beds, inventory
- admission_id is in: admissions, prescriptions, billing
- Always use clear table aliases that match the table name
- Use apt alias: doctors=d, patients=p, appointments=a,
  admissions=adm, beds=b, departments=dept,
  prescriptions=rx, billing=bill, inventory=inv
- Never use p.doctor_id — doctors table uses d.doctor_id
- Never use a.patient_id with alias a for appointments
  and also p for patients in same query without being explicit
- Always LIMIT to 100 rows unless user asks for specific count
- Use PostgreSQL syntax only
- For counting doctors with appointments use:
  SELECT COUNT(DISTINCT d.doctor_id) FROM doctors d
  JOIN appointments a ON d.doctor_id = a.doctor_id
- For HAVING clauses always GROUP BY first

Examples of correct queries:
Q: how many doctors have more than 100 appointments?
A: SELECT d.name, COUNT(a.appointment_id) as total
   FROM doctors d
   JOIN appointments a ON d.doctor_id = a.doctor_id
   GROUP BY d.doctor_id, d.name
   HAVING COUNT(a.appointment_id) > 100
   ORDER BY total DESC;

Q: show patients with unpaid bills
A: SELECT p.name, b.total_amount, b.payment_status
   FROM patients p
   JOIN billing b ON p.patient_id = b.patient_id
   WHERE b.payment_status = 'pending'
   LIMIT 100;

Q: which department has most occupied beds
A: SELECT dept.name, COUNT(beds.bed_id) as occupied_count
   FROM departments dept
   JOIN beds ON dept.department_id = beds.department_id
   WHERE beds.status = 'occupied'
   GROUP BY dept.department_id, dept.name
   ORDER BY occupied_count DESC
   LIMIT 1;
"""

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class NLQueryRequest(BaseModel):
    question: str


class NLQueryResponse(BaseModel):
    question:  str
    sql:       str
    columns:   list[str]
    rows:      list[list[Any]]
    row_count: int


# ---------------------------------------------------------------------------
# NL Modify models
# ---------------------------------------------------------------------------
class NLModifyRequest(BaseModel):
    question: str


class NLModifyResponse(BaseModel):
    question:      str
    sql:           str
    rows_affected: int
    message:       str


class NLPreviewResponse(BaseModel):
    question:       str
    sql:            str
    is_modification: bool
    operation_type: str


# ---------------------------------------------------------------------------
# Schema context for modify endpoint
# ---------------------------------------------------------------------------
MODIFY_SCHEMA_CONTEXT = """You are a PostgreSQL expert. Convert the user instruction to a SQL query.
Return ONLY the raw SQL query. No explanation, no markdown, no backticks, no comments.

Database schema with exact column names:

patients: patient_id(PK), name, dob, gender, blood_type, contact, address

doctors: doctor_id(PK), name, department_id(FK→departments),
         specialization, contact, years_experience

departments: department_id(PK), name, head_doctor, floor_number

appointments: appointment_id(PK), patient_id(FK→patients),
              doctor_id(FK→doctors), scheduled_at, status, notes

admissions: admission_id(PK), patient_id(FK→patients),
            doctor_id(FK→doctors), bed_id(FK→beds),
            admitted_at, discharged_at, diagnosis

beds: bed_id(PK), department_id(FK→departments), ward_type, status

prescriptions: prescription_id(PK), admission_id(FK→admissions),
               doctor_id(FK→doctors), medication, dosage,
               duration_days, prescribed_at

billing: bill_id(PK), patient_id(FK→patients),
         admission_id(FK→admissions), total_amount,
         paid_amount, payment_status, billed_at

inventory: item_id(PK), department_id(FK→departments),
           item_name, category, quantity, reorder_level, unit_cost

Critical rules:
- doctor_id is in: doctors, appointments, admissions, prescriptions
- patient_id is in: patients, appointments, admissions, billing
- department_id is in: departments, doctors, beds, inventory
- admission_id is in: admissions, prescriptions, billing
- Always use clear table aliases that match the table name
- Use apt alias: doctors=d, patients=p, appointments=a,
  admissions=adm, beds=b, departments=dept,
  prescriptions=rx, billing=bill, inventory=inv
- Never use p.doctor_id — doctors table uses d.doctor_id
- Generate INSERT, UPDATE, DELETE or SELECT statements
- Use correct PostgreSQL syntax
- For INSERT always specify column names explicitly
- Never use DROP, TRUNCATE, ALTER, CREATE, CASCADE
- For UPDATE and DELETE always include a WHERE clause
- Never update or delete without a specific WHERE condition

PostgreSQL UPDATE syntax rules:
- CORRECT: UPDATE table_name SET col = val WHERE condition
- WRONG: UPDATE alias SET col = val FROM table alias WHERE condition
- Never use table aliases in UPDATE statements
- Never use FROM clause in UPDATE
- Examples:
  UPDATE beds SET status = 'available' WHERE bed_id = 5
  UPDATE patients SET contact = '9999' WHERE patient_id = 1
  UPDATE billing SET payment_status = 'paid' WHERE bill_id = 3

PostgreSQL DELETE syntax rules:
- CORRECT: DELETE FROM table_name WHERE condition
- WRONG: DELETE FROM table alias WHERE alias.col = val
- Never use table aliases in DELETE statements
- Examples:
  DELETE FROM appointments WHERE appointment_id = 1
  DELETE FROM patients WHERE patient_id = 5
"""


# ---------------------------------------------------------------------------
# Forbidden DML/DDL keywords
# ---------------------------------------------------------------------------
_FORBIDDEN = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE"]


# ---------------------------------------------------------------------------
# POST /query/natural
# ---------------------------------------------------------------------------
@router.post("/natural", response_model=NLQueryResponse)
async def natural_language_query(
    request:      NLQueryRequest,
    db:           Session = Depends(get_db),
    current_user: str     = Depends(get_current_user),
):
    # Step 1: Groq → SQL
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SCHEMA_CONTEXT},
                {"role": "user",   "content": request.question},
            ],
            model="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=1024,
        )
        sql = chat_completion.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API error: {str(e)}")

    # Step 2: Strip markdown fences or leading "sql" word
    sql = sql.replace("```sql", "").replace("```", "").strip()
    if sql.lower().startswith("sql"):
        sql = sql[3:].strip()

    # Step 3: Validate — SELECT only, no destructive keywords
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith("SELECT"):
        raise HTTPException(
            status_code=400,
            detail=f"Only SELECT queries allowed. Got: {sql[:100]}",
        )
    for word in _FORBIDDEN:
        if word in sql_upper:
            raise HTTPException(
                status_code=400,
                detail=f"Forbidden keyword: {word}",
            )

    # Step 4: Execute against read-only user
    try:
        readonly_db = _ReadOnlySession()
        try:
            result  = readonly_db.execute(text(sql))
            columns = list(result.keys())
            rows    = [list(row) for row in result.fetchmany(100)]
        finally:
            readonly_db.close()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL execution error: {str(e)}")

    return NLQueryResponse(
        question=request.question,
        sql=sql,
        columns=columns,
        rows=rows,
        row_count=len(rows),
    )


# ---------------------------------------------------------------------------
# POST /query/preview  — admin-only: generate SQL without executing
# ---------------------------------------------------------------------------
@router.post("/preview", response_model=NLPreviewResponse)
async def nl_preview(
    request:      NLModifyRequest,
    current_user: dict = Depends(get_admin_user),
):
    # Step 1 — Generate SQL via Groq
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": MODIFY_SCHEMA_CONTEXT},
                {"role": "user",   "content": request.question},
            ],
            model="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=1024,
        )
        sql = chat_completion.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API error: {str(e)}")

    # Step 2 — Clean SQL
    sql = sql.replace("```sql", "").replace("```", "").strip()
    if sql.lower().startswith("sql"):
        sql = sql[3:].strip()

    # Step 3 — Block dangerous operations
    sql_upper = sql.upper().strip()
    _BLOCKED = ["DROP", "TRUNCATE", "ALTER", "CREATE", "CASCADE", "GRANT", "REVOKE"]
    for word in _BLOCKED:
        if word in sql_upper:
            raise HTTPException(
                status_code=400,
                detail=f"Operation '{word}' is blocked",
            )

    # Step 4 — Detect operation type
    if sql_upper.startswith("SELECT"):
        op_type = "SELECT"
        is_mod  = False
    elif sql_upper.startswith("INSERT"):
        op_type = "INSERT"
        is_mod  = True
    elif sql_upper.startswith("UPDATE"):
        op_type = "UPDATE"
        is_mod  = True
    elif sql_upper.startswith("DELETE"):
        op_type = "DELETE"
        is_mod  = True
    else:
        op_type = "UNKNOWN"
        is_mod  = True

    return NLPreviewResponse(
        question=request.question,
        sql=sql,
        is_modification=is_mod,
        operation_type=op_type,
    )


# ---------------------------------------------------------------------------
# POST /query/modify  — admin-only NL → INSERT/UPDATE/DELETE
# ---------------------------------------------------------------------------
@router.post("/modify", response_model=NLModifyResponse)
async def nl_modify(
    request:      NLModifyRequest,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    # Step 1 — Generate SQL via Groq
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": MODIFY_SCHEMA_CONTEXT},
                {"role": "user",   "content": request.question},
            ],
            model="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=1024,
        )
        sql = chat_completion.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API error: {str(e)}")

    # Step 2 — Clean SQL
    sql = sql.replace("```sql", "").replace("```", "").strip()
    if sql.lower().startswith("sql"):
        sql = sql[3:].strip()

    # Step 3 — Block dangerous operations
    sql_upper = sql.upper().strip()
    _BLOCKED = ["DROP", "TRUNCATE", "ALTER", "CREATE", "CASCADE", "GRANT", "REVOKE"]
    for word in _BLOCKED:
        if word in sql_upper:
            raise HTTPException(
                status_code=400,
                detail=f"Operation '{word}' is not allowed for safety.",
            )

    # Step 4 — Require WHERE for UPDATE and DELETE
    if sql_upper.startswith("UPDATE") or sql_upper.startswith("DELETE"):
        if "WHERE" not in sql_upper:
            raise HTTPException(
                status_code=400,
                detail="UPDATE and DELETE must include a WHERE clause. Please be more specific.",
            )

    # Step 5 — Execute against full-access DB user
    try:
        full_db = _FullSession()
        try:
            result       = full_db.execute(text(sql))
            full_db.commit()
            rows_affected = result.rowcount if result.rowcount >= 0 else 0
        finally:
            full_db.close()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL execution error: {str(e)}")

    # Step 6 — Write to audit log (silently skip if audit router absent)
    try:
        from app.routers.audit import write_audit_log
        write_audit_log(
            db=db,
            table_name="nl_modify",
            operation="NL_MODIFY",
            record_id=None,
            old_values=None,
            new_values={"sql": sql, "question": request.question},
            changed_by=current_user["username"],
            endpoint="/query/modify",
        )
    except Exception:
        pass

    # Step 7 — Build message
    if sql_upper.startswith("INSERT"):
        msg = "Record inserted successfully"
    elif sql_upper.startswith("UPDATE"):
        msg = f"{rows_affected} record(s) updated successfully"
    elif sql_upper.startswith("DELETE"):
        msg = f"{rows_affected} record(s) deleted successfully"
    else:
        msg = "Query executed successfully"

    return NLModifyResponse(
        question=request.question,
        sql=sql,
        rows_affected=rows_affected,
        message=msg,
    )
