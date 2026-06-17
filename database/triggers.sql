-- 1. SLOT CONFLICT TRIGGER
CREATE OR REPLACE FUNCTION check_slot_conflict()
RETURNS TRIGGER AS $$
DECLARE v_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO v_count FROM appointments
  WHERE doctor_id = NEW.doctor_id
  AND appt_date = NEW.appt_date
  AND appt_time = NEW.appt_time
  AND status != 'Cancelled'
  AND appt_id != COALESCE(NEW.appt_id, 0);

  IF v_count > 0 THEN
    RAISE EXCEPTION 'Slot conflict: Doctor already booked at this time';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_slot_conflict
BEFORE INSERT OR UPDATE ON appointments
FOR EACH ROW EXECUTE FUNCTION check_slot_conflict();

-- 2. LOW STOCK ALERT TRIGGER
CREATE OR REPLACE FUNCTION check_low_stock()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.stock_quantity < NEW.reorder_level THEN
    RAISE NOTICE 'LOW STOCK ALERT: % has only % units left',
      NEW.brand_name, NEW.stock_quantity;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_low_stock
AFTER UPDATE ON medicines
FOR EACH ROW EXECUTE FUNCTION check_low_stock();

-- 3. ABNORMAL LAB RESULT TRIGGER
CREATE OR REPLACE FUNCTION flag_abnormal()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.result_value IS NOT NULL THEN
    NEW.is_abnormal := TRUE;
    NEW.result_date := NOW();
    NEW.status := 'Done';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_abnormal_result
BEFORE UPDATE ON lab_orders
FOR EACH ROW
WHEN (NEW.result_value IS NOT NULL AND OLD.result_value IS NULL)
EXECUTE FUNCTION flag_abnormal();



-- 5. AUDIT LOG TRIGGER
CREATE OR REPLACE FUNCTION log_audit()
RETURNS TRIGGER AS $$
DECLARE
  v_record_id INTEGER;
BEGIN
  -- Dynamically get the PK value based on table
  IF TG_TABLE_NAME = 'patients' THEN
    v_record_id := COALESCE(NEW.patient_id, OLD.patient_id);
  ELSIF TG_TABLE_NAME = 'bills' THEN
    v_record_id := COALESCE(NEW.bill_id, OLD.bill_id);
  ELSIF TG_TABLE_NAME = 'appointments' THEN
    v_record_id := COALESCE(NEW.appt_id, OLD.appt_id);
  ELSE
    v_record_id := NULL;
  END IF;

  IF TG_OP = 'DELETE' THEN
    INSERT INTO audit_log(table_name, operation, record_id, old_values)
    VALUES (TG_TABLE_NAME, 'DELETE', v_record_id, row_to_json(OLD)::JSONB);
  ELSIF TG_OP = 'UPDATE' THEN
    INSERT INTO audit_log(table_name, operation, record_id, old_values, new_values)
    VALUES (TG_TABLE_NAME, 'UPDATE', v_record_id, row_to_json(OLD)::JSONB, row_to_json(NEW)::JSONB);
  ELSIF TG_OP = 'INSERT' THEN
    INSERT INTO audit_log(table_name, operation, record_id, new_values)
    VALUES (TG_TABLE_NAME, 'INSERT', v_record_id, row_to_json(NEW)::JSONB);
  END IF;

  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Apply audit to key tables
CREATE TRIGGER trg_audit_patients
AFTER INSERT OR UPDATE OR DELETE ON patients
FOR EACH ROW EXECUTE FUNCTION log_audit();

CREATE TRIGGER trg_audit_bills
AFTER INSERT OR UPDATE OR DELETE ON bills
FOR EACH ROW EXECUTE FUNCTION log_audit();

CREATE TRIGGER trg_audit_appointments
AFTER INSERT OR UPDATE OR DELETE ON appointments
FOR EACH ROW EXECUTE FUNCTION log_audit();