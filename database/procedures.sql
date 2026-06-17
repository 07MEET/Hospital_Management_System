-- Updated register_patient procedure (add to 02_procedures.sql)
CREATE OR REPLACE PROCEDURE register_patient(
  p_name        TEXT,
  p_dob         DATE,
  p_gender      TEXT,
  p_blood       TEXT,
  p_phone       TEXT,
  p_email       TEXT,
  p_address     TEXT,
  p_emergency   TEXT,
  p_insurance_id INTEGER DEFAULT NULL
)
LANGUAGE plpgsql AS $$
BEGIN
  -- Phone uniqueness check with friendly message
  IF EXISTS (SELECT 1 FROM patients WHERE phone = p_phone) THEN
    RAISE EXCEPTION 'A patient with phone number % already exists.', p_phone;
  END IF;

  -- Email uniqueness check (if provided)
  IF p_email IS NOT NULL AND p_email != '' THEN
    IF EXISTS (SELECT 1 FROM patients WHERE email = LOWER(p_email)) THEN
      RAISE EXCEPTION 'A patient with email % is already registered.', p_email;
    END IF;
  END IF;

  INSERT INTO patients(
    full_name, date_of_birth, gender, blood_group,
    phone, email, address, emergency_contact, insurance_id
  ) VALUES (
    p_name, p_dob, p_gender, p_blood,
    p_phone,
    CASE WHEN p_email = '' THEN NULL ELSE LOWER(p_email) END,
    p_address, p_emergency, p_insurance_id
  );
END;
$$;

-- Updated book_appointment procedure
CREATE OR REPLACE PROCEDURE book_appointment(
  p_patient_id INTEGER,
  p_doctor_id  INTEGER,
  p_date       DATE,
  p_time       TIME,
  p_type       TEXT,
  p_notes      TEXT DEFAULT NULL
)
LANGUAGE plpgsql AS $$
DECLARE
  v_count        INTEGER;
  v_pat_status   TEXT;
BEGIN
  -- Check patient is active
  SELECT status INTO v_pat_status FROM patients WHERE patient_id = p_patient_id;
  IF v_pat_status IS NULL THEN
    RAISE EXCEPTION 'Patient not found.';
  END IF;

  -- Check doctor is active
  IF NOT EXISTS (SELECT 1 FROM doctors WHERE doctor_id = p_doctor_id AND status = 'Active') THEN
    RAISE EXCEPTION 'Selected doctor is not currently available.';
  END IF;

  -- Check working hours
  IF EXTRACT(HOUR FROM p_time) < 8 OR EXTRACT(HOUR FROM p_time) >= 20 THEN
    RAISE EXCEPTION 'Appointment time must be between 8:00 AM and 8:00 PM.';
  END IF;

  -- Check slot conflict
  SELECT COUNT(*) INTO v_count
  FROM appointments
  WHERE doctor_id = p_doctor_id
  AND   appt_date = p_date
  AND   appt_time = p_time
  AND   status NOT IN ('Cancelled');

  IF v_count > 0 THEN
    RAISE EXCEPTION 'slot conflict: This time slot is already booked for the selected doctor.';
  END IF;

  INSERT INTO appointments(patient_id, doctor_id, appt_date, appt_time, appt_type, status, notes)
  VALUES (p_patient_id, p_doctor_id, p_date, p_time, p_type, 'Confirmed', p_notes);
END;
$$;
-- 3. GENERATE BILL
CREATE OR REPLACE PROCEDURE generate_bill(
  p_appt_id INTEGER,
  p_generated_by INTEGER
)
LANGUAGE plpgsql AS $$
DECLARE
  v_patient_id     INTEGER;
  v_bill_id        INTEGER;
  v_total          DECIMAL(12,2) := 0;
  v_consult_fee    DECIMAL(10,2);
  v_ins_covered    DECIMAL(12,2) := 0;
  v_net            DECIMAL(12,2);
BEGIN

  IF EXISTS (
        SELECT 1
        FROM bills
        WHERE appt_id = p_appt_id
    ) THEN
        RAISE EXCEPTION 'A bill has already been generated for this appointment.';
    END IF;
    
  -- Get patient
  SELECT patient_id INTO v_patient_id
  FROM appointments WHERE appt_id = p_appt_id;

  -- Get consultation fee
  SELECT d.opd_fee INTO v_consult_fee
  FROM appointments a JOIN doctors d ON a.doctor_id = d.doctor_id
  WHERE a.appt_id = p_appt_id;

  v_total := v_consult_fee;

  -- Create bill
  INSERT INTO bills(patient_id, appt_id, total_amount, insurance_covered,
                  net_payable, due_date, generated_by)
VALUES (v_patient_id, p_appt_id, 0, 0, 0,
        CURRENT_DATE + INTERVAL '7 days', p_generated_by)
RETURNING bill_id INTO v_bill_id;

  -- Add consultation item
  INSERT INTO bill_items(bill_id, service_type, description, quantity, unit_price, total)
  VALUES (v_bill_id, 'Consultation', 'Doctor Consultation Fee', 1, v_consult_fee, v_consult_fee);

  -- Add lab charges
  INSERT INTO bill_items(bill_id, service_type, description, quantity, unit_price, total)
  SELECT v_bill_id, 'Lab', lt.test_name, 1, lt.price, lt.price
  FROM lab_orders lo JOIN lab_tests lt ON lo.test_id = lt.test_id
  WHERE lo.appt_id = p_appt_id;

  v_total := v_total + COALESCE((
    SELECT SUM(lt.price) FROM lab_orders lo
    JOIN lab_tests lt ON lo.test_id = lt.test_id
    WHERE lo.appt_id = p_appt_id), 0);

  -- Add pharmacy charges
  INSERT INTO bill_items(bill_id, service_type, description, quantity, unit_price, total)
  SELECT v_bill_id, 'Pharmacy', m.brand_name,
         p.duration_days, m.unit_price, (m.unit_price * p.duration_days)
  FROM diagnoses d
  JOIN prescriptions p ON d.diag_id = p.diag_id
  JOIN medicines m ON p.medicine_id = m.medicine_id
  WHERE d.appt_id = p_appt_id;

  v_total := v_total + COALESCE((
    SELECT SUM(m.unit_price * p.duration_days)
    FROM diagnoses d
    JOIN prescriptions p ON d.diag_id = p.diag_id
    JOIN medicines m ON p.medicine_id = m.medicine_id
    WHERE d.appt_id = p_appt_id), 0);

  -- Get insurance coverage
  SELECT LEAST(i.coverage_amount, v_total) INTO v_ins_covered
  FROM patients pt JOIN insurance i ON pt.insurance_id = i.insurance_id
  WHERE pt.patient_id = v_patient_id;

  v_ins_covered := COALESCE(v_ins_covered, 0);
  v_net := v_total - v_ins_covered;

  -- Update bill totals
  UPDATE bills
  SET total_amount = v_total,
      insurance_covered = v_ins_covered,
      net_payable = v_net
  WHERE bill_id = v_bill_id;

  -- Mark appointment complete
  UPDATE appointments SET status = 'Completed' WHERE appt_id = p_appt_id;
END;
$$;

-- Updated record_payment procedure
CREATE OR REPLACE PROCEDURE record_payment(
  p_bill_id   INTEGER,
  p_amount    DECIMAL,
  p_mode      TEXT,
  p_ref       TEXT,
  p_user_id   INTEGER
)
LANGUAGE plpgsql AS $$
DECLARE
  v_net_payable DECIMAL(12,2);
  v_total_paid  DECIMAL(12,2);
  v_bill_status TEXT;
BEGIN
  -- Validate bill exists and is not already paid
  SELECT net_payable, status INTO v_net_payable, v_bill_status
  FROM bills WHERE bill_id = p_bill_id;

  IF v_net_payable IS NULL THEN
    RAISE EXCEPTION 'Bill not found.';
  END IF;

  IF v_bill_status = 'Paid' THEN
    RAISE EXCEPTION 'This bill has already been fully paid.';
  END IF;

  -- Validate amount
  IF p_amount <= 0 THEN
    RAISE EXCEPTION 'Payment amount must be greater than 0.';
  END IF;

  -- Check for overpayment
  SELECT COALESCE(SUM(amount_paid), 0) INTO v_total_paid
  FROM payments WHERE bill_id = p_bill_id;

  IF v_total_paid + p_amount > v_net_payable + 0.01 THEN
    RAISE EXCEPTION 'Payment of ₹% would exceed outstanding amount of ₹%.',
      p_amount, (v_net_payable - v_total_paid);
  END IF;

  -- Record payment (wrapped in savepoint for safety)
  INSERT INTO payments(bill_id, amount_paid, payment_mode, transaction_ref, received_by)
  VALUES (p_bill_id, p_amount, p_mode, p_ref, p_user_id);

  -- Recalculate total paid
  SELECT COALESCE(SUM(amount_paid), 0) INTO v_total_paid
  FROM payments WHERE bill_id = p_bill_id;

  -- Update bill status
  UPDATE bills
  SET status = CASE
    WHEN v_total_paid >= v_net_payable THEN 'Paid'
    ELSE 'Partial'
  END
  WHERE bill_id = p_bill_id;
END;
$$;