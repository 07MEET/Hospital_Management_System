-- ROLES
CREATE TABLE roles (
  role_id   SERIAL PRIMARY KEY,
  role_name VARCHAR(50) UNIQUE NOT NULL,
  description TEXT
);

-- USERS
CREATE TABLE users (
  user_id        SERIAL PRIMARY KEY,
  username       VARCHAR(50) UNIQUE NOT NULL,
  password_hash  TEXT NOT NULL,
  role_id        INTEGER REFERENCES roles(role_id),
  staff_ref_id   INTEGER,
  last_login     TIMESTAMP,
  is_active      BOOLEAN DEFAULT TRUE,
  failed_attempts INTEGER DEFAULT 0,
  locked_until   TIMESTAMP,
  created_at     TIMESTAMP DEFAULT NOW()
);

-- USER SESSIONS
CREATE TABLE user_sessions (
  session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    INTEGER REFERENCES users(user_id),
  role_id    INTEGER REFERENCES roles(role_id),
  ip_address INET,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '30 minutes',
  is_active  BOOLEAN DEFAULT TRUE
);

-- INSURANCE
CREATE TABLE insurance (
  insurance_id   SERIAL PRIMARY KEY,
  provider_name  VARCHAR(100),
  policy_number  VARCHAR(50) UNIQUE,
  coverage_amount DECIMAL(12,2),
  expiry_date    DATE,
  plan_type      VARCHAR(50)
);

-- PATIENTS
CREATE TABLE patients (
  patient_id         SERIAL PRIMARY KEY,
  full_name          VARCHAR(100) NOT NULL,
  date_of_birth      DATE NOT NULL,
  gender             VARCHAR(10) CHECK (gender IN ('Male','Female','Other')),
  blood_group        VARCHAR(5)  CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
  phone              VARCHAR(15) UNIQUE NOT NULL,
  email              VARCHAR(100),
  address            TEXT,
  emergency_contact  VARCHAR(100),
  insurance_id       INTEGER REFERENCES insurance(insurance_id),
  registration_date  TIMESTAMP DEFAULT NOW(),
  status             VARCHAR(20) DEFAULT 'Active' CHECK (status IN ('Active','Discharged'))
);

-- DEPARTMENTS
CREATE TABLE departments (
  dept_id        SERIAL PRIMARY KEY,
  dept_name      VARCHAR(100) NOT NULL,
  location       VARCHAR(100),
  phone_ext      VARCHAR(10),
  head_doctor_id INTEGER
);

-- DOCTORS
CREATE TABLE doctors (
  doctor_id      SERIAL PRIMARY KEY,
  full_name      VARCHAR(100) NOT NULL,
  dept_id        INTEGER REFERENCES departments(dept_id),
  specialization VARCHAR(100),
  qualification  VARCHAR(100),
  phone          VARCHAR(15),
  email          VARCHAR(100),
  joining_date   DATE,
  opd_fee        DECIMAL(10,2) DEFAULT 500,
  status         VARCHAR(20) DEFAULT 'Active'
);

-- APPOINTMENTS
CREATE TABLE appointments (
  appt_id    SERIAL PRIMARY KEY,
  patient_id INTEGER REFERENCES patients(patient_id),
  doctor_id  INTEGER REFERENCES doctors(doctor_id),
  appt_date  DATE NOT NULL,
  appt_time  TIME NOT NULL CHECK (appt_time BETWEEN '08:00' AND '20:00'),
  appt_type  VARCHAR(20) CHECK (appt_type IN ('OPD','IPD','Emergency')),
  status     VARCHAR(20) DEFAULT 'Pending' CHECK (status IN ('Pending','Confirmed','Completed','Cancelled')),
  notes      TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- DIAGNOSES
CREATE TABLE diagnoses (
  diag_id       SERIAL PRIMARY KEY,
  appt_id       INTEGER REFERENCES appointments(appt_id),
  icd_code      VARCHAR(20),
  description   TEXT,
  severity      VARCHAR(20) CHECK (severity IN ('Mild','Moderate','Severe')),
  diagnosed_at  TIMESTAMP DEFAULT NOW()
);

-- MEDICINES
CREATE TABLE medicines (
  medicine_id    SERIAL PRIMARY KEY,
  brand_name     VARCHAR(100) NOT NULL,
  generic_name   VARCHAR(100),
  category       VARCHAR(50),
  stock_quantity INTEGER DEFAULT 0 CHECK (stock_quantity >= 0),
  reorder_level  INTEGER DEFAULT 50,
  unit_price     DECIMAL(10,2) CHECK (unit_price > 0),
  expiry_date    DATE,
  manufacturer   VARCHAR(100)
);

-- PRESCRIPTIONS
CREATE TABLE prescriptions (
  rx_id          SERIAL PRIMARY KEY,
  diag_id        INTEGER REFERENCES diagnoses(diag_id),
  medicine_id    INTEGER REFERENCES medicines(medicine_id),
  dosage         VARCHAR(50),
  frequency      VARCHAR(50),
  duration_days  INTEGER,
  instructions   TEXT,
  prescribed_at  TIMESTAMP DEFAULT NOW()
);

-- LAB TESTS MASTER
CREATE TABLE lab_tests (
  test_id           SERIAL PRIMARY KEY,
  test_name         VARCHAR(100) NOT NULL,
  category          VARCHAR(50),
  normal_range      VARCHAR(100),
  unit              VARCHAR(20),
  price             DECIMAL(10,2),
  turnaround_hours  INTEGER
);

-- LAB ORDERS
CREATE TABLE lab_orders (
  order_id      SERIAL PRIMARY KEY,
  appt_id       INTEGER REFERENCES appointments(appt_id),
  test_id       INTEGER REFERENCES lab_tests(test_id),
  ordered_at    TIMESTAMP DEFAULT NOW(),
  result_value  VARCHAR(100),
  is_abnormal   BOOLEAN DEFAULT FALSE,
  status        VARCHAR(20) DEFAULT 'Pending' CHECK (status IN ('Pending','Collected','Done')),
  result_date   TIMESTAMP
);

-- BILLS
CREATE TABLE bills (
  bill_id            SERIAL PRIMARY KEY,
  patient_id         INTEGER REFERENCES patients(patient_id),
  appt_id            INTEGER REFERENCES appointments(appt_id),
  total_amount       DECIMAL(12,2),
  insurance_covered  DECIMAL(12,2) DEFAULT 0,
  net_payable        DECIMAL(12,2),
  bill_date          TIMESTAMP DEFAULT NOW(),
  due_date           DATE,
  status             VARCHAR(20) DEFAULT 'Unpaid' CHECK (status IN ('Unpaid','Partial','Paid')),
  generated_by       INTEGER REFERENCES users(user_id),
  CONSTRAINT chk_insurance CHECK (insurance_covered <= total_amount),
  CONSTRAINT chk_net       CHECK (net_payable >= 0)
);

-- BILL ITEMS
CREATE TABLE bill_items (
  item_id       SERIAL PRIMARY KEY,
  bill_id       INTEGER REFERENCES bills(bill_id) ON DELETE CASCADE,
  service_type  VARCHAR(30) CHECK (service_type IN ('Consultation','Lab','Pharmacy')),
  description   VARCHAR(200),
  quantity      INTEGER DEFAULT 1,
  unit_price    DECIMAL(10,2),
  total         DECIMAL(10,2)
);

-- PAYMENTS
CREATE TABLE payments (
  payment_id       SERIAL PRIMARY KEY,
  bill_id          INTEGER REFERENCES bills(bill_id),
  amount_paid      DECIMAL(12,2) CHECK (amount_paid > 0),
  payment_mode     VARCHAR(20) CHECK (payment_mode IN ('Cash','Card','UPI','Insurance')),
  payment_date     TIMESTAMP DEFAULT NOW(),
  transaction_ref  VARCHAR(100),
  received_by      INTEGER REFERENCES users(user_id)
);

-- AUDIT LOG
CREATE TABLE audit_log (
  log_id      BIGSERIAL PRIMARY KEY,
  table_name  VARCHAR(50),
  operation   VARCHAR(10) CHECK (operation IN ('INSERT','UPDATE','DELETE')),
  record_id   INTEGER,
  old_values  JSONB,
  new_values  JSONB,
  changed_by  INTEGER REFERENCES users(user_id),
  changed_at  TIMESTAMP DEFAULT NOW(),
  ip_address  INET
);

-- INDEXES
CREATE INDEX idx_patient_phone   ON patients(phone);
CREATE INDEX idx_patient_name    ON patients(full_name);
CREATE INDEX idx_appt_date       ON appointments(appt_date);
CREATE INDEX idx_appt_doctor     ON appointments(doctor_id);
CREATE INDEX idx_bill_patient    ON bills(patient_id);
CREATE INDEX idx_bill_status     ON bills(status);
CREATE INDEX idx_medicine_stock  ON medicines(stock_quantity);