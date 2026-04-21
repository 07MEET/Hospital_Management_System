# 🏥 MediCare HMS — Hospital Management System

A **production-grade, multi-role hospital management system** built on PostgreSQL and Python (Streamlit). All critical business logic — scheduling, billing, fraud detection, and auditing — lives at the database layer via PL/pgSQL stored procedures, triggers, and functions, making the system robust regardless of which client connects.

---

## 🚀 Live Features

| Role | Capabilities |
|------|-------------|
| **Admin** | Full dashboard, patient/doctor management, fraud alerts, audit log, settings |
| **Doctor** | Appointments, diagnose & prescribe, lab orders |
| **Receptionist** | Register patients, book appointments, today's queue |
| **Lab Technician** | View pending orders, enter results |
| **Pharmacist** | Dispense medicines, inventory management, low-stock alerts |
| **Billing Staff** | Generate bills, record payments, fraud dashboard |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Python · Streamlit · Plotly |
| **Backend Logic** | PL/pgSQL · Stored Procedures · Trigger Functions |
| **Database** | PostgreSQL 15+ |
| **Security** | RBAC (6 roles) · Row-Level Security · Append-only Audit Log |
| **ORM / Connector** | psycopg2 · psycopg2-pool |

---

## 🗄️ Database Architecture

- **16 core tables** across Identity, Clinical, Pharmacy, Lab, Billing, and Audit domains
- **5 triggers** — appointment conflict prevention, low-stock alerts, lab result auto-flagging, real-time fraud detection, comprehensive audit logging
- **4 stored procedures** — `register_patient()`, `book_appointment()`, `generate_bill()`, `record_payment()`
- **4 user-defined functions** — age calculation, slot availability check, payment deduction, patient status
- **5 views** — OPD queue, patient history, billing summary, fraud dashboard, low-stock monitor
- **7 fraud detection functions** + master scan procedure
- **RBAC** (6 PostgreSQL roles) + **Row-Level Security** on 4 tables
- **JSONB audit trail** capturing full before/after row snapshots on every data change
- **8 B-Tree indexes** for high-frequency query optimization

---

## 📁 Project Structure

```
Hospital-Management-System/
├── app/
│   ├── main.py              # App entry point, routing, session management
│   ├── auth.py              # Login, session, timeout handling
│   ├── db.py                # Connection pool, query utilities
│   ├── validators.py        # Input validation
│   ├── styles.py            # Custom CSS
│   ├── components.py        # Shared UI components
│   └── pageviews/
│       ├── admin.py         # Admin dashboard
│       ├── doctor.py        # Doctor dashboard
│       ├── receptionist.py  # Receptionist dashboard
│       ├── billing.py       # Billing dashboard
│       ├── lab_tech.py      # Lab technician dashboard
│       ├── pharmacist.py    # Pharmacist dashboard
│       └── components/      # Shared page components (charts, patient card, sidebar)
├── database/
│   ├── tables.sql           # Schema — 16 tables with constraints
│   ├── triggers.sql         # 5 PL/pgSQL trigger functions
│   ├── procedures.sql       # 4 stored procedures
│   ├── functions.sql        # 4 user-defined functions
│   ├── views.sql            # 5 analytical views
│   ├── rbac.sql             # RBAC roles, grants, Row-Level Security policies
│   ├── fraud.sql            # 7 fraud detection functions + master scan
│   └── sample_data.sql      # Seed data for testing
├── assets/
│   └── logo.svg
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- PostgreSQL 15+

### 1. Clone the repository
```bash
git clone https://github.com/07MEET/Hospital-Management-System.git
cd Hospital-Management-System
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up the database
```bash
# Create the database
psql -U postgres -c "CREATE DATABASE HMS;"

# Run SQL files in order
psql -U postgres -d HMS -f database/tables.sql
psql -U postgres -d HMS -f database/functions.sql
psql -U postgres -d HMS -f database/views.sql
psql -U postgres -d HMS -f database/triggers.sql
psql -U postgres -d HMS -f database/procedures.sql
psql -U postgres -d HMS -f database/rbac.sql
psql -U postgres -d HMS -f database/fraud.sql
psql -U postgres -d HMS -f database/sample_data.sql
```

### 4. Configure the database connection
Edit `app/db.py` and update with your PostgreSQL credentials:
```python
DB_CONFIG = {
    "host":     "localhost",
    "database": "HMS",
    "user":     "postgres",
    "password": "your_password",   # ← update this
    "port":     5432
}
```

### 5. Run the application
```bash
cd app
streamlit run main.py
```

Visit `http://localhost:8501` in your browser.

### Demo Credentials
| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `Pass@1234` |
| Doctor | `kartik` | `Pass@1234` |
| Receptionist | `reception1` | `Pass@1234` |
| Lab Tech | `labtech1` | `Pass@1234` |
| Pharmacist | `pharma1` | `Pass@1234` |
| Billing | `billing1` | `Pass@1234` |

---

## 🔐 Security Highlights

- **Role-Based Access Control (RBAC)** — 6 PostgreSQL roles with fine-grained table-level GRANT/REVOKE
- **Row-Level Security (RLS)** — Doctors are filtered at the DB layer to see only their own patients
- **Append-only Audit Log** — A PostgreSQL RULE makes `audit_log` physically immutable; even admins cannot delete records
- **Session Management** — UUID session keys with 30-minute TTL and failed-attempt lockout
- **Real-time Fraud Detection** — 4 rules checked on every bill finalization (duplicate billing, charge spikes, insurance overcharge, after-hours billing)

---

## 🧠 Advanced Database Concepts Demonstrated

| Concept | Implementation |
|---------|---------------|
| BEFORE / AFTER Triggers | Slot conflict prevention, low-stock alerts, audit logging |
| Trigger WHEN clause | Lab result auto-flagging fires only on NULL → non-NULL transition |
| Stored Procedures | Atomic multi-step workflows with full validation chains |
| Window Functions | `AVG / ROW_NUMBER / RANK / COUNT OVER (PARTITION BY ...)` for fraud analytics |
| Recursive CTEs | Drug interaction checker using `CROSS JOIN` on patient prescriptions |
| RBAC + RLS | Two-layer security — table-level permissions + row-level filtering |
| JSONB Storage | Full row snapshots (`row_to_json()::JSONB`) in audit trail |
| Indexing Strategy | 8 B-Tree indexes on high-frequency filter columns |
| Transaction Safety | All procedures are atomic — RAISE EXCEPTION rolls back on failure |
| UUID Primary Keys | `gen_random_uuid()` for tamper-resistant session management |
