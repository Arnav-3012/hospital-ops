"""
seed.py — Seed hospital_db with realistic Indian hospital data.
Run from project root: python database/seed.py
"""

import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from faker import Faker

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("ERROR: DATABASE_URL not found in backend/.env")

fake = Faker("en_IN")
random.seed(42)
Faker.seed(42)

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
DEPARTMENTS = [
    ("Cardiology",       "Dr. Ramesh Sharma",    4),
    ("Neurology",        "Dr. Priya Nair",        3),
    ("Orthopedics",      "Dr. Vikram Patel",      2),
    ("Pediatrics",       "Dr. Sunita Desai",      1),
    ("Oncology",         "Dr. Anjali Mehta",      5),
    ("Emergency",        "Dr. Suresh Kumar",      0),
    ("Radiology",        "Dr. Kavita Joshi",      2),
    ("Pathology",        "Dr. Mohan Rao",         1),
    ("Dermatology",      "Dr. Neha Gupta",        3),
    ("General Medicine", "Dr. Arun Verma",        1),
]

DEPT_SPECIALIZATIONS = {
    "Cardiology":       ["Interventional Cardiology", "Electrophysiology", "Heart Failure"],
    "Neurology":        ["Stroke Medicine", "Epilepsy", "Movement Disorders"],
    "Orthopedics":      ["Joint Replacement", "Spine Surgery", "Sports Medicine"],
    "Pediatrics":       ["Neonatology", "Pediatric Cardiology", "Child Neurology"],
    "Oncology":         ["Medical Oncology", "Surgical Oncology", "Radiation Oncology"],
    "Emergency":        ["Emergency Medicine", "Trauma Surgery", "Critical Care"],
    "Radiology":        ["Interventional Radiology", "Neuroradiology", "Musculoskeletal Radiology"],
    "Pathology":        ["Clinical Pathology", "Histopathology", "Microbiology"],
    "Dermatology":      ["Cosmetic Dermatology", "Pediatric Dermatology", "Dermatopathology"],
    "General Medicine": ["Internal Medicine", "Diabetology", "Geriatrics"],
}

DIAGNOSES = [
    "Acute Myocardial Infarction", "Hypertensive Crisis", "Type 2 Diabetes Mellitus",
    "Community-acquired Pneumonia", "Acute Appendicitis", "Femur Fracture",
    "Ischemic Stroke", "Dengue Fever", "Typhoid Fever", "Urinary Tract Infection",
    "Chronic Kidney Disease", "Liver Cirrhosis", "Bronchial Asthma", "COPD Exacerbation",
    "Septicemia", "Epileptic Seizure", "Migraine", "Deep Vein Thrombosis",
    "Acute Gastroenteritis", "Cellulitis",
]

MEDICATIONS = [
    "Paracetamol", "Amoxicillin", "Metformin", "Atorvastatin", "Amlodipine",
    "Pantoprazole", "Azithromycin", "Cefixime", "Ondansetron", "Ranitidine",
    "Aspirin", "Clopidogrel", "Enalapril", "Losartan", "Furosemide",
    "Insulin Glargine", "Dexamethasone", "Methylprednisolone", "Tramadol",
    "Diclofenac", "Ciprofloxacin", "Metronidazole", "Fluconazole", "Acyclovir",
]

DOSAGE_TEMPLATES = [
    "500mg twice daily", "250mg three times daily", "1g once daily",
    "100mg twice daily", "40mg once daily", "20mg twice daily",
    "10 units subcutaneous once daily", "0.5mg once daily", "5mg once daily",
    "200mg three times daily",
]

INVENTORY_CATEGORIES = {
    "Medicines":         ["Paracetamol Tablets", "IV Fluids NS 500ml", "Glucose 5% 500ml",
                          "Amoxicillin Capsules", "Metformin Tablets"],
    "Surgical Supplies": ["Surgical Gloves (pair)", "Gauze Bandage Roll", "Suture Kit",
                          "Scalpel Blades", "Sterile Drapes"],
    "Equipment":         ["Syringe 5ml", "Syringe 10ml", "IV Cannula 20G",
                          "Oxygen Mask", "Nebulizer Mask"],
    "Diagnostics":       ["Blood Collection Tubes", "Urine Dipsticks", "Glucose Test Strips",
                          "Pregnancy Test Kits", "Rapid Malaria Kits"],
}

WARD_TYPES = ["General", "ICU", "Private", "Semi-Private"]

BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

START_DATE = datetime(2023, 1, 1)
END_DATE   = datetime(2024, 12, 31)


def rand_dt(start: datetime = START_DATE, end: datetime = END_DATE) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def seed_departments(cur) -> list[int]:
    print("  Seeding departments...")
    ids = []
    for name, head, floor in DEPARTMENTS:
        cur.execute(
            "INSERT INTO departments (name, head_doctor, floor_number) VALUES (%s, %s, %s) RETURNING department_id",
            (name, head, floor),
        )
        ids.append(cur.fetchone()[0])
    return ids


def seed_doctors(cur, dept_ids: list[int], dept_names: list[str]) -> list[int]:
    print("  Seeding doctors (50)...")
    ids = []
    for _ in range(50):
        idx = random.randrange(len(dept_ids))
        dept_id   = dept_ids[idx]
        dept_name = dept_names[idx]
        spec = random.choice(DEPT_SPECIALIZATIONS[dept_name])
        cur.execute(
            """INSERT INTO doctors (name, department_id, specialization, contact, years_experience)
               VALUES (%s, %s, %s, %s, %s) RETURNING doctor_id""",
            (
                fake.name(),
                dept_id,
                spec,
                fake.phone_number()[:20],
                random.randint(1, 35),
            ),
        )
        ids.append(cur.fetchone()[0])
    return ids


def seed_patients(cur) -> list[int]:
    print("  Seeding patients (5000)...")
    ids = []
    for _ in range(5000):
        dob = fake.date_of_birth(minimum_age=18, maximum_age=84)
        cur.execute(
            """INSERT INTO patients (name, dob, gender, blood_type, contact, address)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING patient_id""",
            (
                fake.name(),
                dob,
                random.choice(["Male", "Female", "Other"]),
                random.choice(BLOOD_TYPES),
                fake.phone_number()[:20],
                fake.address(),
            ),
        )
        ids.append(cur.fetchone()[0])
    return ids


def seed_beds(cur, dept_ids: list[int]) -> tuple[list[int], list[int]]:
    """Returns (all_bed_ids, occupied_bed_ids)."""
    print("  Seeding beds (200)...")
    all_ids: list[int] = []
    occupied_ids: list[int] = []
    for _ in range(200):
        status = "occupied" if random.random() < 0.30 else "available"
        cur.execute(
            """INSERT INTO beds (department_id, ward_type, status)
               VALUES (%s, %s, %s) RETURNING bed_id""",
            (random.choice(dept_ids), random.choice(WARD_TYPES), status),
        )
        bid = cur.fetchone()[0]
        all_ids.append(bid)
        if status == "occupied":
            occupied_ids.append(bid)
    return all_ids, occupied_ids


def seed_appointments(cur, patient_ids: list[int], doctor_ids: list[int]) -> list[int]:
    print("  Seeding appointments (8000)...")
    statuses = (["scheduled"] * 3) + (["completed"] * 5) + (["cancelled"] * 2)
    ids = []
    for _ in range(8000):
        cur.execute(
            """INSERT INTO appointments (patient_id, doctor_id, scheduled_at, status, notes)
               VALUES (%s, %s, %s, %s, %s) RETURNING appointment_id""",
            (
                random.choice(patient_ids),
                random.choice(doctor_ids),
                rand_dt(),
                random.choice(statuses),
                fake.sentence(nb_words=8) if random.random() < 0.5 else None,
            ),
        )
        ids.append(cur.fetchone()[0])
    return ids


def seed_admissions(
    cur,
    patient_ids: list[int],
    doctor_ids: list[int],
    occupied_bed_ids: list[int],
) -> list[int]:
    print("  Seeding admissions (3000)...")
    # If fewer occupied beds than admissions, reuse them (multiple stays over time is valid)
    ids = []
    for _ in range(3000):
        admitted_at   = rand_dt()
        discharged_at = None
        if random.random() < 0.40:
            discharged_at = admitted_at + timedelta(days=random.randint(1, 30))

        bed_id = random.choice(occupied_bed_ids) if occupied_bed_ids else random.randint(1, 200)

        cur.execute(
            """INSERT INTO admissions (patient_id, doctor_id, bed_id, admitted_at, discharged_at, diagnosis)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING admission_id""",
            (
                random.choice(patient_ids),
                random.choice(doctor_ids),
                bed_id,
                admitted_at,
                discharged_at,
                random.choice(DIAGNOSES),
            ),
        )
        ids.append(cur.fetchone()[0])
    return ids


def seed_prescriptions(cur, admission_ids: list[int], doctor_ids: list[int]) -> list[int]:
    print("  Seeding prescriptions (6000)...")
    ids = []
    for _ in range(6000):
        cur.execute(
            """INSERT INTO prescriptions (admission_id, doctor_id, medication, dosage, duration_days, prescribed_at)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING prescription_id""",
            (
                random.choice(admission_ids),
                random.choice(doctor_ids),
                random.choice(MEDICATIONS),
                random.choice(DOSAGE_TEMPLATES),
                random.randint(3, 30),
                rand_dt(),
            ),
        )
        ids.append(cur.fetchone()[0])
    return ids


def seed_billing(cur, patient_ids: list[int], admission_ids: list[int]) -> list[int]:
    print("  Seeding billing (3000)...")
    # 50% paid, 30% partial, 20% pending
    status_pool = (["paid"] * 5) + (["partial"] * 3) + (["pending"] * 2)
    ids = []
    for adm_id in random.sample(admission_ids, min(3000, len(admission_ids))):
        total   = round(random.uniform(5000, 500000), 2)
        status  = random.choice(status_pool)
        if status == "paid":
            paid = total
        elif status == "partial":
            paid = round(random.uniform(0.1 * total, 0.9 * total), 2)
        else:
            paid = 0.00

        cur.execute(
            """INSERT INTO billing (patient_id, admission_id, total_amount, paid_amount, payment_status, billed_at)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING bill_id""",
            (
                random.choice(patient_ids),
                adm_id,
                total,
                paid,
                status,
                rand_dt(),
            ),
        )
        ids.append(cur.fetchone()[0])
    return ids


def seed_inventory(cur, dept_ids: list[int]) -> list[int]:
    print("  Seeding inventory (150)...")
    ids = []
    categories = list(INVENTORY_CATEGORIES.keys())
    count = 0
    while count < 150:
        cat      = random.choice(categories)
        item     = random.choice(INVENTORY_CATEGORIES[cat])
        qty      = random.randint(0, 500)
        reorder  = random.choice([10, 20, 25, 50])
        # ~20% of items intentionally below reorder level for alert testing
        if random.random() < 0.20:
            qty = random.randint(0, reorder - 1)
        cur.execute(
            """INSERT INTO inventory (department_id, item_name, category, quantity, reorder_level, unit_cost)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING item_id""",
            (
                random.choice(dept_ids),
                item,
                cat,
                qty,
                reorder,
                round(random.uniform(5, 5000), 2),
            ),
        )
        ids.append(cur.fetchone()[0])
        count += 1
    return ids


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    try:
        # 1. departments
        dept_ids = seed_departments(cur)
        conn.commit()
        dept_names = [d[0] for d in DEPARTMENTS]

        # 2. doctors
        doctor_ids = seed_doctors(cur, dept_ids, dept_names)
        conn.commit()

        # 3. patients
        patient_ids = seed_patients(cur)
        conn.commit()

        # 4. beds
        _, occupied_bed_ids = seed_beds(cur, dept_ids)
        conn.commit()

        # 5. appointments
        seed_appointments(cur, patient_ids, doctor_ids)
        conn.commit()

        # 6. admissions
        admission_ids = seed_admissions(cur, patient_ids, doctor_ids, occupied_bed_ids)
        conn.commit()

        # 7. prescriptions
        seed_prescriptions(cur, admission_ids, doctor_ids)
        conn.commit()

        # 8. billing
        seed_billing(cur, patient_ids, admission_ids)
        conn.commit()

        # 9. inventory
        seed_inventory(cur, dept_ids)
        conn.commit()

        # Summary
        print("\nSeeding complete.")
        for table in ["departments", "doctors", "patients", "beds", "appointments",
                      "admissions", "prescriptions", "billing", "inventory"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  {table:<20} {count:>6} rows")

    except Exception as exc:
        conn.rollback()
        print(f"\nERROR — rolled back transaction: {exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
