-- ============================================================
-- 06_rbac.sql — Role-Based Access Control for HMS
-- Run this AFTER 01_tables.sql and 07_sample_data.sql
-- ============================================================

-- ── Step 1: Create PostgreSQL DB-level roles ──────────────────
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hms_admin')        THEN CREATE ROLE hms_admin        NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hms_doctor')       THEN CREATE ROLE hms_doctor       NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hms_receptionist') THEN CREATE ROLE hms_receptionist NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hms_lab_tech')     THEN CREATE ROLE hms_lab_tech     NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hms_pharmacist')   THEN CREATE ROLE hms_pharmacist   NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hms_billing')      THEN CREATE ROLE hms_billing      NOLOGIN; END IF;
END
$$;

-- ── Step 2: RECEPTIONIST permissions ─────────────────────────
-- Can register patients, book appointments, view doctors/depts
GRANT SELECT, INSERT, UPDATE ON patients     TO hms_receptionist;
GRANT SELECT, INSERT, UPDATE ON appointments TO hms_receptionist;
GRANT SELECT, INSERT         ON insurance    TO hms_receptionist;
GRANT SELECT                 ON doctors      TO hms_receptionist;
GRANT SELECT                 ON departments  TO hms_receptionist;
GRANT SELECT                 ON roles        TO hms_receptionist;
GRANT USAGE, SELECT ON SEQUENCE patients_patient_id_seq     TO hms_receptionist;
GRANT USAGE, SELECT ON SEQUENCE appointments_appt_id_seq    TO hms_receptionist;
GRANT USAGE, SELECT ON SEQUENCE insurance_insurance_id_seq  TO hms_receptionist;
GRANT INSERT                 ON audit_log                    TO hms_receptionist;
GRANT USAGE, SELECT ON SEQUENCE audit_log_log_id_seq         TO hms_receptionist;

-- ── Step 3: DOCTOR permissions ───────────────────────────────
-- Can see own appointments (enforced via RLS), diagnose, prescribe, order labs
GRANT SELECT, UPDATE         ON appointments  TO hms_doctor;
GRANT SELECT                 ON patients      TO hms_doctor;
GRANT SELECT, INSERT         ON diagnoses     TO hms_doctor;
GRANT SELECT, INSERT         ON prescriptions TO hms_doctor;
GRANT SELECT, INSERT         ON lab_orders    TO hms_doctor;
GRANT SELECT                 ON lab_tests     TO hms_doctor;
GRANT SELECT                 ON medicines     TO hms_doctor;
GRANT SELECT                 ON doctors       TO hms_doctor;
GRANT SELECT                 ON departments   TO hms_doctor;
GRANT USAGE, SELECT ON SEQUENCE diagnoses_diag_id_seq         TO hms_doctor;
GRANT USAGE, SELECT ON SEQUENCE prescriptions_rx_id_seq       TO hms_doctor;
GRANT USAGE, SELECT ON SEQUENCE lab_orders_order_id_seq       TO hms_doctor;

-- ── Step 4: LAB TECHNICIAN permissions ───────────────────────
-- Can view and update lab orders only
GRANT SELECT, UPDATE         ON lab_orders  TO hms_lab_tech;
GRANT SELECT                 ON lab_tests   TO hms_lab_tech;
GRANT SELECT                 ON appointments TO hms_lab_tech;
GRANT SELECT                 ON patients    TO hms_lab_tech;

-- ── Step 5: PHARMACIST permissions ───────────────────────────
-- Can view prescriptions and manage medicine stock
GRANT SELECT                 ON prescriptions TO hms_pharmacist;
GRANT SELECT                 ON diagnoses     TO hms_pharmacist;
GRANT SELECT                 ON appointments  TO hms_pharmacist;
GRANT SELECT                 ON patients      TO hms_pharmacist;
GRANT SELECT, UPDATE         ON medicines     TO hms_pharmacist;

-- ── Step 6: BILLING STAFF permissions ────────────────────────
GRANT SELECT, INSERT, UPDATE ON bills        TO hms_billing;
GRANT SELECT, INSERT         ON bill_items   TO hms_billing;
GRANT SELECT, INSERT         ON payments     TO hms_billing;
GRANT SELECT                 ON patients     TO hms_billing;
GRANT SELECT                 ON appointments TO hms_billing;
GRANT SELECT                 ON doctors      TO hms_billing;
GRANT SELECT                 ON lab_orders   TO hms_billing;
GRANT SELECT                 ON lab_tests    TO hms_billing;
GRANT SELECT                 ON prescriptions TO hms_billing;
GRANT SELECT                 ON medicines    TO hms_billing;
GRANT SELECT                 ON diagnoses    TO hms_billing;
GRANT USAGE, SELECT ON SEQUENCE bills_bill_id_seq        TO hms_billing;
GRANT USAGE, SELECT ON SEQUENCE bill_items_item_id_seq   TO hms_billing;
GRANT USAGE, SELECT ON SEQUENCE payments_payment_id_seq  TO hms_billing;

-- ── Step 7: ADMIN — full access ──────────────────────────────
GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA public TO hms_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hms_admin;

-- ── Step 8: PROTECT sensitive tables from all non-admin roles ─

-- Nobody except admin can DELETE or UPDATE audit_log
REVOKE DELETE, UPDATE, TRUNCATE ON audit_log FROM PUBLIC;
GRANT SELECT ON audit_log TO hms_admin;

-- Make audit_log physically append-only
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_rules
    WHERE tablename='audit_log' AND rulename='no_delete_audit_log'
  ) THEN
    EXECUTE 'CREATE RULE no_delete_audit_log AS ON DELETE TO audit_log DO INSTEAD NOTHING';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_rules
    WHERE tablename='audit_log' AND rulename='no_update_audit_log'
  ) THEN
    EXECUTE 'CREATE RULE no_update_audit_log AS ON UPDATE TO audit_log DO INSTEAD NOTHING';
  END IF;
END
$$;


-- ── Step 9: ROW LEVEL SECURITY ────────────────────────────────

-- Enable RLS on sensitive tables
ALTER TABLE appointments  ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagnoses     ENABLE ROW LEVEL SECURITY;
ALTER TABLE prescriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE lab_orders    ENABLE ROW LEVEL SECURITY;

-- APPOINTMENTS: Doctor sees only their own
DROP POLICY IF EXISTS doctor_own_appointments ON appointments;
CREATE POLICY doctor_own_appointments
  ON appointments FOR ALL TO hms_doctor
  USING (
    doctor_id = (
      SELECT staff_ref_id FROM users
      WHERE user_id = NULLIF(current_setting('app.user_id', TRUE), '')::INTEGER
    )
  );

-- APPOINTMENTS: Others see all (receptionist, billing, admin)
DROP POLICY IF EXISTS staff_all_appointments ON appointments;
CREATE POLICY staff_all_appointments
  ON appointments FOR ALL
  TO hms_receptionist, hms_billing, hms_admin, hms_lab_tech, hms_pharmacist
  USING (TRUE);

-- DIAGNOSES: Doctor sees only their own patients' diagnoses
DROP POLICY IF EXISTS doctor_own_diagnoses ON diagnoses;
CREATE POLICY doctor_own_diagnoses
  ON diagnoses FOR ALL TO hms_doctor
  USING (
    appt_id IN (
      SELECT appt_id FROM appointments
      WHERE doctor_id = (
        SELECT staff_ref_id FROM users
        WHERE user_id = NULLIF(current_setting('app.user_id', TRUE), '')::INTEGER
      )
    )
  );

DROP POLICY IF EXISTS staff_all_diagnoses ON diagnoses;
CREATE POLICY staff_all_diagnoses
  ON diagnoses FOR ALL
  TO hms_admin, hms_billing, hms_pharmacist
  USING (TRUE);

-- PRESCRIPTIONS: Doctor sees only their own
DROP POLICY IF EXISTS doctor_own_prescriptions ON prescriptions;
CREATE POLICY doctor_own_prescriptions
  ON prescriptions FOR ALL TO hms_doctor
  USING (
    diag_id IN (
      SELECT d.diag_id FROM diagnoses d
      JOIN appointments a ON d.appt_id = a.appt_id
      WHERE a.doctor_id = (
        SELECT staff_ref_id FROM users
        WHERE user_id = NULLIF(current_setting('app.user_id', TRUE), '')::INTEGER
      )
    )
  );

DROP POLICY IF EXISTS staff_all_prescriptions ON prescriptions;
CREATE POLICY staff_all_prescriptions
  ON prescriptions FOR ALL
  TO hms_admin, hms_billing, hms_pharmacist
  USING (TRUE);

-- LAB ORDERS: Lab tech sees all; Doctor sees own
DROP POLICY IF EXISTS lab_tech_all_orders ON lab_orders;
CREATE POLICY lab_tech_all_orders
  ON lab_orders FOR ALL TO hms_lab_tech
  USING (TRUE);

DROP POLICY IF EXISTS doctor_own_lab_orders ON lab_orders;
CREATE POLICY doctor_own_lab_orders
  ON lab_orders FOR ALL TO hms_doctor
  USING (
    appt_id IN (
      SELECT appt_id FROM appointments
      WHERE doctor_id = (
        SELECT staff_ref_id FROM users
        WHERE user_id = NULLIF(current_setting('app.user_id', TRUE), '')::INTEGER
      )
    )
  );

DROP POLICY IF EXISTS staff_all_lab_orders ON lab_orders;
CREATE POLICY staff_all_lab_orders
  ON lab_orders FOR ALL
  TO hms_admin, hms_billing
  USING (TRUE);

-- ── Step 10: GRANT VIEW access ────────────────────────────────
GRANT SELECT ON vw_patient_history  TO hms_doctor, hms_admin, hms_receptionist;
GRANT SELECT ON vw_opd_queue        TO hms_receptionist, hms_admin, hms_doctor;
GRANT SELECT ON vw_billing_summary  TO hms_billing, hms_admin;
GRANT SELECT ON vw_low_stock        TO hms_pharmacist, hms_admin;

-- ── Verification query ────────────────────────────────────────
SELECT
  grantee,
  table_name,
  string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges
FROM information_schema.role_table_grants
WHERE grantee LIKE 'hms_%'
GROUP BY grantee, table_name
ORDER BY grantee, table_name;
