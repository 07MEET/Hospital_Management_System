-- ============================================================
-- 08_fraud.sql — FIXED VERSION
-- Fix: "window functions are not allowed in window definitions"
-- Solution: Use subqueries instead of nested window functions
-- ============================================================

-- ── Rule 1: Duplicate Billing ─────────────────────────────────
CREATE OR REPLACE FUNCTION detect_duplicate_billing()
RETURNS TABLE (
  bill_id_a    INTEGER,
  bill_id_b    INTEGER,
  patient_id   INTEGER,
  patient_name TEXT,
  bill_date    DATE,
  total_amount DECIMAL
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    b1.bill_id,
    b2.bill_id,
    b1.patient_id,
    p.full_name,
    DATE(b1.bill_date),
    b1.total_amount
  FROM bills b1
  JOIN bills b2 ON (
    b1.patient_id = b2.patient_id
    AND DATE(b1.bill_date) = DATE(b2.bill_date)
    AND b1.bill_id < b2.bill_id
  )
  JOIN patients p ON b1.patient_id = p.patient_id
  WHERE b1.bill_id NOT IN (
    SELECT COALESCE(bill_id, 0) FROM fraud_alerts
    WHERE rule_triggered = 'Duplicate Billing'
  );
END;
$$ LANGUAGE plpgsql;

-- ── Rule 2: Abnormal Charge Spike ────────────────────────────
CREATE OR REPLACE FUNCTION detect_charge_spikes()
RETURNS TABLE (
  bill_id      INTEGER,
  patient_name TEXT,
  bill_amount  DECIMAL,
  avg_amount   DECIMAL,
  spike_ratio  NUMERIC
) AS $$
DECLARE
  v_avg DECIMAL;
BEGIN
  SELECT AVG(total_amount) INTO v_avg FROM bills;
  IF v_avg IS NULL OR v_avg = 0 THEN RETURN; END IF;

  RETURN QUERY
  SELECT
    b.bill_id,
    p.full_name,
    b.total_amount,
    v_avg,
    ROUND((b.total_amount / v_avg)::NUMERIC, 2)
  FROM bills b
  JOIN patients p ON b.patient_id = p.patient_id
  WHERE b.total_amount > (v_avg * 3)
  AND b.bill_id NOT IN (
    SELECT COALESCE(bill_id, 0) FROM fraud_alerts
    WHERE rule_triggered = 'Abnormal Charge Spike'
  );
END;
$$ LANGUAGE plpgsql;

-- ── Rule 3: Ghost Patient Billing ────────────────────────────
CREATE OR REPLACE FUNCTION detect_ghost_patient_billing()
RETURNS TABLE (
  bill_id      INTEGER,
  patient_name TEXT,
  bill_amount  DECIMAL,
  bill_date    TIMESTAMP
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    b.bill_id,
    p.full_name,
    b.total_amount,
    b.bill_date
  FROM bills b
  JOIN patients p ON b.patient_id = p.patient_id
  WHERE (b.appt_id IS NULL
    OR b.appt_id NOT IN (SELECT appt_id FROM appointments))
  AND b.bill_id NOT IN (
    SELECT COALESCE(bill_id, 0) FROM fraud_alerts
    WHERE rule_triggered = 'Ghost Patient Billing'
  );
END;
$$ LANGUAGE plpgsql;

-- ── Rule 4: Prescription Overload ────────────────────────────
CREATE OR REPLACE FUNCTION detect_prescription_overload()
RETURNS TABLE (
  appt_id      INTEGER,
  patient_name TEXT,
  doctor_name  TEXT,
  rx_count     BIGINT,
  appt_date    DATE
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    a.appt_id,
    p.full_name,
    d.full_name,
    COUNT(pr.rx_id),
    a.appt_date
  FROM appointments a
  JOIN patients p   ON a.patient_id = p.patient_id
  JOIN doctors d    ON a.doctor_id  = d.doctor_id
  JOIN diagnoses di ON a.appt_id   = di.appt_id
  JOIN prescriptions pr ON di.diag_id = pr.diag_id
  GROUP BY a.appt_id, p.full_name, d.full_name, a.appt_date
  HAVING COUNT(pr.rx_id) > 5;
END;
$$ LANGUAGE plpgsql;

-- ── Rule 5: Insurance Overcharge ─────────────────────────────
CREATE OR REPLACE FUNCTION detect_insurance_overcharge()
RETURNS TABLE (
  bill_id           INTEGER,
  patient_name      TEXT,
  total_amount      DECIMAL,
  insurance_claimed DECIMAL,
  overcharge_by     DECIMAL
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    b.bill_id,
    p.full_name,
    b.total_amount,
    b.insurance_covered,
    (b.insurance_covered - b.total_amount)
  FROM bills b
  JOIN patients p ON b.patient_id = p.patient_id
  WHERE b.insurance_covered > b.total_amount
  AND b.bill_id NOT IN (
    SELECT COALESCE(bill_id, 0) FROM fraud_alerts
    WHERE rule_triggered = 'Insurance Overcharge'
  );
END;
$$ LANGUAGE plpgsql;

-- ── Rule 6: Rapid Re-admission ───────────────────────────────
CREATE OR REPLACE FUNCTION detect_rapid_readmission()
RETURNS TABLE (
  patient_name  TEXT,
  appt_1_id     INTEGER,
  appt_2_id     INTEGER,
  first_visit   TIMESTAMP,
  readmit_visit TIMESTAMP,
  hours_gap     NUMERIC
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    p.full_name,
    a1.appt_id,
    a2.appt_id,
    a1.created_at,
    a2.created_at,
    ROUND(EXTRACT(EPOCH FROM (a2.created_at - a1.created_at)) / 3600, 1)
  FROM appointments a1
  JOIN appointments a2 ON (
    a1.patient_id = a2.patient_id
    AND a2.appt_id > a1.appt_id
    AND a2.created_at - a1.created_at < INTERVAL '24 hours'
    AND a2.created_at > a1.created_at
  )
  JOIN patients p ON a1.patient_id = p.patient_id;
END;
$$ LANGUAGE plpgsql;

-- ── Rule 7: After-Hours Billing ──────────────────────────────
CREATE OR REPLACE FUNCTION detect_after_hours_billing()
RETURNS TABLE (
  bill_id      INTEGER,
  patient_name TEXT,
  bill_amount  DECIMAL,
  bill_time    TIMESTAMP,
  hour_of_day  DOUBLE PRECISION
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    b.bill_id,
    p.full_name,
    b.total_amount,
    b.bill_date,
    EXTRACT(HOUR FROM b.bill_date)
  FROM bills b
  JOIN patients p ON b.patient_id = p.patient_id
  WHERE (EXTRACT(HOUR FROM b.bill_date) < 8
     OR  EXTRACT(HOUR FROM b.bill_date) >= 20)
  AND b.bill_id NOT IN (
    SELECT COALESCE(bill_id, 0) FROM fraud_alerts
    WHERE rule_triggered = 'After-Hours Billing'
  );
END;
$$ LANGUAGE plpgsql;

-- ── FIXED: Billing anomaly view using subquery not nested window ──
-- The original had window functions inside window definitions — illegal in PostgreSQL
-- Fix: compute window values in a CTE first, then reference them
CREATE OR REPLACE VIEW vw_billing_anomaly_ranked AS
WITH base AS (
  SELECT
    b.bill_id,
    b.patient_id,
    b.total_amount,
    b.bill_date,
    AVG(b.total_amount) OVER ()                                              AS overall_avg,
    AVG(b.total_amount) OVER (PARTITION BY DATE_TRUNC('month', b.bill_date)) AS monthly_avg,
    ROW_NUMBER() OVER (PARTITION BY b.patient_id ORDER BY b.bill_date)       AS visit_number,
    COUNT(b.bill_id)    OVER (PARTITION BY b.patient_id, DATE(b.bill_date))  AS bills_same_day,
    RANK()              OVER (ORDER BY b.total_amount DESC)                   AS amount_rank
  FROM bills b
)
SELECT
  base.bill_id,
  p.full_name                                                AS patient,
  base.total_amount,
  base.bill_date,
  base.overall_avg,
  base.monthly_avg,
  -- spike_ratio computed here, NOT inside another window function
  ROUND((base.total_amount / NULLIF(base.overall_avg, 0))::NUMERIC, 2) AS spike_ratio,
  base.visit_number,
  base.bills_same_day,
  base.amount_rank
FROM base
JOIN patients p ON base.patient_id = p.patient_id;

-- ── FIXED: Prescription analysis — no nested window functions ──
CREATE OR REPLACE VIEW vw_prescription_analysis AS
WITH rx_counts AS (
  SELECT
    a.appt_id,
    a.doctor_id,
    a.appt_date,
    a.patient_id,
    COUNT(pr.rx_id) AS rx_per_visit
  FROM appointments a
  LEFT JOIN diagnoses di    ON a.appt_id  = di.appt_id
  LEFT JOIN prescriptions pr ON di.diag_id = pr.diag_id
  GROUP BY a.appt_id, a.doctor_id, a.appt_date, a.patient_id
)
SELECT
  rc.appt_id,
  p.full_name                                               AS patient,
  d.full_name                                               AS doctor,
  rc.appt_date,
  rc.rx_per_visit,
  SUM(rc.rx_per_visit) OVER (
    PARTITION BY rc.doctor_id, DATE_TRUNC('month', rc.appt_date)
  )                                                         AS rx_this_month,
  RANK() OVER (ORDER BY rc.rx_per_visit DESC)               AS rx_rank,
  CASE
    WHEN rc.rx_per_visit > 5 THEN 'OVERLOAD'
    WHEN rc.rx_per_visit > 3 THEN 'HIGH'
    ELSE 'NORMAL'
  END                                                       AS rx_flag
FROM rx_counts rc
JOIN patients p ON rc.patient_id = p.patient_id
JOIN doctors  d ON rc.doctor_id  = d.doctor_id;

-- ── Master Fraud Scanner ──────────────────────────────────────
CREATE OR REPLACE PROCEDURE run_full_fraud_scan()
LANGUAGE plpgsql AS $$
DECLARE v_count INTEGER := 0;
BEGIN
  -- Rule 1: Duplicate Billing
  INSERT INTO fraud_alerts(bill_id, patient_id, rule_triggered, severity, details)
  SELECT bill_id_a, patient_id, 'Duplicate Billing', 'High',
    FORMAT('Patient "%s" billed twice on %s', patient_name, bill_date)
  FROM detect_duplicate_billing();
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Rule 1 Duplicate Billing: % alerts', v_count;

  -- Rule 2: Charge Spike
  INSERT INTO fraud_alerts(bill_id, patient_id, rule_triggered, severity, details)
  SELECT cs.bill_id, b.patient_id, 'Abnormal Charge Spike', 'High',
    FORMAT('Bill ₹%s is %sx above average ₹%s for "%s"',
           cs.bill_amount, cs.spike_ratio, ROUND(cs.avg_amount,2), cs.patient_name)
  FROM detect_charge_spikes() cs JOIN bills b ON cs.bill_id = b.bill_id;
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Rule 2 Charge Spike: % alerts', v_count;

  -- Rule 3: Ghost Patient
  INSERT INTO fraud_alerts(bill_id, patient_id, rule_triggered, severity, details)
  SELECT gp.bill_id, b.patient_id, 'Ghost Patient Billing', 'High',
    FORMAT('Bill #%s for "%s" has no appointment', gp.bill_id, gp.patient_name)
  FROM detect_ghost_patient_billing() gp JOIN bills b ON gp.bill_id = b.bill_id;
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Rule 3 Ghost Patient: % alerts', v_count;

  -- Rule 5: Insurance Overcharge
  INSERT INTO fraud_alerts(bill_id, patient_id, rule_triggered, severity, details)
  SELECT io.bill_id, b.patient_id, 'Insurance Overcharge', 'High',
    FORMAT('Insurance ₹%s exceeds bill ₹%s for "%s"',
           io.insurance_claimed, io.total_amount, io.patient_name)
  FROM detect_insurance_overcharge() io JOIN bills b ON io.bill_id = b.bill_id;
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Rule 5 Insurance Overcharge: % alerts', v_count;

  -- Rule 7: After-Hours
  INSERT INTO fraud_alerts(bill_id, patient_id, rule_triggered, severity, details)
  SELECT ah.bill_id, b.patient_id, 'After-Hours Billing', 'Medium',
    FORMAT('Bill #%s generated at hour %s outside working hours', ah.bill_id, ah.hour_of_day)
  FROM detect_after_hours_billing() ah JOIN bills b ON ah.bill_id = b.bill_id;
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Rule 7 After-Hours: % alerts', v_count;

  RAISE NOTICE 'Fraud scan complete.';
END;
$$;

-- Drug interaction check via Recursive CTE
CREATE OR REPLACE FUNCTION check_drug_interactions(p_patient_id INTEGER)
RETURNS TABLE (medicine_a_name TEXT, medicine_b_name TEXT, interaction_note TEXT) AS $$
BEGIN
  RETURN QUERY
  WITH patient_medicines AS (
    SELECT DISTINCT m.medicine_id, m.brand_name, m.category
    FROM prescriptions pr
    JOIN diagnoses d    ON pr.diag_id   = d.diag_id
    JOIN appointments a ON d.appt_id    = a.appt_id
    JOIN medicines m    ON pr.medicine_id = m.medicine_id
    WHERE a.patient_id = p_patient_id
    AND   a.appt_date >= CURRENT_DATE - INTERVAL '30 days'
  )
  SELECT
    m1.brand_name,
    m2.brand_name,
    FORMAT('Both are %s — potential interaction', m1.category)
  FROM patient_medicines m1
  CROSS JOIN patient_medicines m2
  WHERE m1.medicine_id < m2.medicine_id
  AND   m1.category = m2.category
  AND   m1.category IN ('Antibiotic','Anticoagulant','NSAID','Antidepressant');
END;
$$ LANGUAGE plpgsql;

-- Fraud summary view
CREATE OR REPLACE VIEW vw_fraud_summary AS
SELECT
  rule_triggered,
  severity,
  COUNT(*)                                    AS total_alerts,
  COUNT(*) FILTER (WHERE status='Open')       AS open_alerts,
  COUNT(*) FILTER (WHERE status='Reviewed')   AS reviewed_alerts,
  COUNT(*) FILTER (WHERE status='Closed')     AS closed_alerts,
  MAX(detected_at)                            AS latest_detection
FROM fraud_alerts
GROUP BY rule_triggered, severity
ORDER BY CASE severity WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END;