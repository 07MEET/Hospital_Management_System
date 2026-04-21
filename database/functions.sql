-- 1. GET PATIENT AGE
CREATE OR REPLACE FUNCTION get_patient_age(p_patient_id INTEGER)
RETURNS INTEGER AS $$
  SELECT DATE_PART('year', AGE(date_of_birth))::INTEGER
  FROM patients WHERE patient_id = p_patient_id;
$$ LANGUAGE sql;

-- 2. CHECK SLOT AVAILABLE
CREATE OR REPLACE FUNCTION is_slot_available(
  p_doctor_id INTEGER, p_date DATE, p_time TIME
)
RETURNS BOOLEAN AS $$
  SELECT COUNT(*) = 0
  FROM appointments
  WHERE doctor_id = p_doctor_id
  AND appt_date = p_date
  AND appt_time = p_time
  AND status != 'Cancelled';
$$ LANGUAGE sql;

-- 3. CALCULATE INSURANCE DEDUCTION
CREATE OR REPLACE FUNCTION calculate_deduction(p_bill_id INTEGER)
RETURNS DECIMAL AS $$
  SELECT net_payable FROM bills WHERE bill_id = p_bill_id;
$$ LANGUAGE sql;

-- 4. CHECK MEAL ELIGIBILITY (here: check patient is active)
CREATE OR REPLACE FUNCTION is_patient_active(p_patient_id INTEGER)
RETURNS BOOLEAN AS $$
  SELECT status = 'Active' FROM patients WHERE patient_id = p_patient_id;
$$ LANGUAGE sql;