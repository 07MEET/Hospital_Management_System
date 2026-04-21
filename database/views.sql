-- Patient history view
CREATE VIEW vw_patient_history AS
SELECT p.patient_id, p.full_name, a.appt_date, a.appt_type,
       d.full_name AS doctor, di.description AS diagnosis,
       di.severity, a.status
FROM patients p
JOIN appointments a ON p.patient_id = a.patient_id
JOIN doctors d ON a.doctor_id = d.doctor_id
LEFT JOIN diagnoses di ON a.appt_id = di.appt_id;

-- OPD Queue view
CREATE VIEW vw_opd_queue AS
SELECT a.appt_id, p.full_name AS patient, d.full_name AS doctor,
       dept.dept_name, a.appt_time, a.appt_type, a.status
FROM appointments a
JOIN patients p ON a.patient_id = p.patient_id
JOIN doctors d ON a.doctor_id = d.doctor_id
JOIN departments dept ON d.dept_id = dept.dept_id
WHERE a.appt_date = CURRENT_DATE
ORDER BY a.appt_time;

-- Billing summary view
CREATE VIEW vw_billing_summary AS
SELECT b.bill_id, p.full_name AS patient,
       b.total_amount, b.insurance_covered,
       b.net_payable, b.status, b.bill_date,
       COALESCE(SUM(pay.amount_paid),0) AS amount_received,
       b.net_payable - COALESCE(SUM(pay.amount_paid),0) AS outstanding
FROM bills b
JOIN patients p ON b.patient_id = p.patient_id
LEFT JOIN payments pay ON b.bill_id = pay.bill_id
GROUP BY b.bill_id, p.full_name, b.total_amount,
         b.insurance_covered, b.net_payable, b.status, b.bill_date;

-- Fraud dashboard view
CREATE VIEW vw_fraud_dashboard AS
SELECT fa.alert_id, fa.rule_triggered, fa.severity,
       fa.detected_at, fa.status, fa.details,
       p.full_name AS patient, b.total_amount
FROM fraud_alerts fa
JOIN bills b ON fa.bill_id = b.bill_id
JOIN patients p ON fa.patient_id = p.patient_id
ORDER BY
  CASE fa.severity WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
  fa.detected_at DESC;

-- Low stock view
CREATE VIEW vw_low_stock AS
SELECT medicine_id, brand_name, category,
       stock_quantity, reorder_level,
       (reorder_level - stock_quantity) AS shortage
FROM medicines
WHERE stock_quantity <= reorder_level
ORDER BY shortage DESC;