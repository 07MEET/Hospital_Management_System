
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

CREATE OR REPLACE PROCEDURE run_full_fraud_scan()
LANGUAGE plpgsql
AS $$
BEGIN

    -- Clear previous alerts so scan is always fresh
    DELETE FROM fraud_alerts;

    ----------------------------------------------------------
    -- FRAUD 1 : BILL GENERATED FOR CANCELLED APPOINTMENT
    ----------------------------------------------------------

    INSERT INTO fraud_alerts (
        bill_id,
        patient_id,
        rule_triggered,
        severity,
        details
    )
    SELECT
        b.bill_id,
        b.patient_id,
        'Billing for Cancelled Appointment',
        'High',
        'Appointment #' || b.appt_id ||
        ' is cancelled but Bill #' || b.bill_id ||
        ' exists.'
    FROM bills b
    JOIN appointments a
        ON b.appt_id = a.appt_id
    WHERE a.status = 'Cancelled';

    ----------------------------------------------------------
    -- FRAUD 2 : DUPLICATE BILL FOR SAME APPOINTMENT
    ----------------------------------------------------------

    INSERT INTO fraud_alerts (
        bill_id,
        patient_id,
        rule_triggered,
        severity,
        details
    )
    SELECT
        b.bill_id,
        b.patient_id,
        'Duplicate Bill for Appointment',
        'High',
        'Multiple bills exist for Appointment #' || b.appt_id
    FROM bills b
    WHERE b.appt_id IN (
        SELECT appt_id
        FROM bills
        WHERE appt_id IS NOT NULL
        GROUP BY appt_id
        HAVING COUNT(*) > 1
    );

END;
$$;