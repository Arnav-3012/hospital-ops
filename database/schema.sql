-- 1. departments
CREATE TABLE departments (
    department_id SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    head_doctor   VARCHAR(100),
    floor_number  INT
);

CREATE INDEX idx_departments_name ON departments(name);

-- 2. doctors
CREATE TABLE doctors (
    doctor_id        SERIAL PRIMARY KEY,
    name             VARCHAR(100) NOT NULL,
    department_id    INT REFERENCES departments(department_id),
    specialization   VARCHAR(100),
    contact          VARCHAR(20),
    years_experience INT
);

CREATE INDEX idx_doctors_department_id ON doctors(department_id);

-- 3. patients
CREATE TABLE patients (
    patient_id SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    dob        DATE,
    gender     VARCHAR(10),
    blood_type VARCHAR(5),
    contact    VARCHAR(20),
    address    TEXT
);

-- 4. beds
CREATE TABLE beds (
    bed_id        SERIAL PRIMARY KEY,
    department_id INT REFERENCES departments(department_id),
    ward_type     VARCHAR(50),
    status        VARCHAR(20) DEFAULT 'available'
                  CHECK (status IN ('available', 'occupied', 'maintenance'))
);

CREATE INDEX idx_beds_department_id ON beds(department_id);

-- 5. appointments
CREATE TABLE appointments (
    appointment_id SERIAL PRIMARY KEY,
    patient_id     INT REFERENCES patients(patient_id),
    doctor_id      INT REFERENCES doctors(doctor_id),
    scheduled_at   TIMESTAMP NOT NULL,
    status         VARCHAR(20) DEFAULT 'scheduled'
                   CHECK (status IN ('scheduled', 'completed', 'cancelled')),
    notes          TEXT
);

CREATE INDEX idx_appointments_patient_id ON appointments(patient_id);
CREATE INDEX idx_appointments_doctor_id  ON appointments(doctor_id);

-- 6. admissions
CREATE TABLE admissions (
    admission_id  SERIAL PRIMARY KEY,
    patient_id    INT REFERENCES patients(patient_id),
    doctor_id     INT REFERENCES doctors(doctor_id),
    bed_id        INT REFERENCES beds(bed_id),
    admitted_at   TIMESTAMP DEFAULT NOW(),
    discharged_at TIMESTAMP,
    diagnosis     TEXT
);

CREATE INDEX idx_admissions_patient_id ON admissions(patient_id);
CREATE INDEX idx_admissions_doctor_id  ON admissions(doctor_id);
CREATE INDEX idx_admissions_bed_id     ON admissions(bed_id);

-- 7. prescriptions
CREATE TABLE prescriptions (
    prescription_id SERIAL PRIMARY KEY,
    admission_id    INT REFERENCES admissions(admission_id),
    doctor_id       INT REFERENCES doctors(doctor_id),
    medication      VARCHAR(200) NOT NULL,
    dosage          VARCHAR(100),
    duration_days   INT,
    prescribed_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_prescriptions_admission_id ON prescriptions(admission_id);
CREATE INDEX idx_prescriptions_doctor_id    ON prescriptions(doctor_id);

-- 8. billing
CREATE TABLE billing (
    bill_id        SERIAL PRIMARY KEY,
    patient_id     INT REFERENCES patients(patient_id),
    admission_id   INT REFERENCES admissions(admission_id),
    total_amount   NUMERIC(10, 2),
    paid_amount    NUMERIC(10, 2) DEFAULT 0,
    payment_status VARCHAR(20) DEFAULT 'pending'
                   CHECK (payment_status IN ('pending', 'partial', 'paid')),
    billed_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_billing_patient_id   ON billing(patient_id);
CREATE INDEX idx_billing_admission_id ON billing(admission_id);

-- 9. inventory
CREATE TABLE inventory (
    item_id       SERIAL PRIMARY KEY,
    department_id INT REFERENCES departments(department_id),
    item_name     VARCHAR(200) NOT NULL,
    category      VARCHAR(100),
    quantity      INT DEFAULT 0,
    reorder_level INT DEFAULT 10,
    unit_cost     NUMERIC(10, 2)
);

CREATE INDEX idx_inventory_department_id ON inventory(department_id);

-- 10. audit_log (used by the API's write_audit_log helper; not one of the 9 core tables)
CREATE TABLE audit_log (
    log_id     SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    operation  VARCHAR(20)  NOT NULL,
    record_id  INT,
    old_values JSON,
    new_values JSON,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT NOW(),
    endpoint   VARCHAR(200),
    ip_address VARCHAR(50)
);

CREATE INDEX idx_audit_log_table_name ON audit_log(table_name);

-- Schema complete: 9 core tables + audit_log, Hospital Operations Intelligence System
