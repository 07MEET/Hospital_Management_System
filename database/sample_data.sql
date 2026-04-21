-- Insert roles
INSERT INTO roles(role_name, description) VALUES
('Admin',         'Full system access'),
('Doctor',        'Clinical access only'),
('Receptionist',  'Patient and appointment management'),
('Lab_Tech',      'Lab orders and results'),
('Pharmacist',    'Prescriptions and medicine stock'),
('Billing_Staff', 'Bills and payments');

-- Insert users (all passwords = "Pass@1234")
INSERT INTO users(username, password_hash, role_id) VALUES
('admin',      crypt('Pass@1234', gen_salt('bf',12)), 1),
('dr_sharma',  crypt('Pass@1234', gen_salt('bf',12)), 2),
('dr_mehta',   crypt('Pass@1234', gen_salt('bf',12)), 2),
('reception1', crypt('Pass@1234', gen_salt('bf',12)), 3),
('labtech1',   crypt('Pass@1234', gen_salt('bf',12)), 4),
('pharma1',    crypt('Pass@1234', gen_salt('bf',12)), 5),
('billing1',   crypt('Pass@1234', gen_salt('bf',12)), 6);

-- Insert departments
INSERT INTO departments(dept_name, location, phone_ext) VALUES
('Cardiology',   'Floor 2 Wing A', '201'),
('Neurology',    'Floor 3 Wing B', '301'),
('Orthopedics',  'Floor 1 Wing C', '101'),
('General OPD',  'Ground Floor',   '001');

-- Insert doctors
INSERT INTO doctors(full_name, dept_id, specialization, qualification, phone, opd_fee) VALUES
('Dr. Rahul Sharma',  1, 'Cardiologist',    'MBBS, MD Cardiology',  '9876543210', 800),
('Dr. Priya Mehta',   2, 'Neurologist',     'MBBS, DM Neurology',   '9876543211', 1000),
('Dr. Amit Verma',    3, 'Orthopedician',   'MBBS, MS Ortho',       '9876543212', 700),
('Dr. Sunita Rao',    4, 'General Physician','MBBS, MD General',    '9876543213', 500);

-- Insert lab tests
INSERT INTO lab_tests(test_name, category, normal_range, unit, price, turnaround_hours) VALUES
('Complete Blood Count',  'Blood',     '4.5-11 x10^9/L', 'x10^9/L', 350,  4),
('Lipid Profile',         'Blood',     '<200 mg/dL',     'mg/dL',   600,  6),
('Blood Glucose Fasting', 'Blood',     '70-100 mg/dL',   'mg/dL',   150,  2),
('Urine Routine',         'Urine',     'Normal',         'NA',       100,  2),
('Chest X-Ray',           'Radiology', 'Normal',         'NA',       500, 24),
('ECG',                   'Cardiology','Normal Sinus Rhythm', 'NA', 300,  1);

-- Insert medicines
INSERT INTO medicines(brand_name, generic_name, category, stock_quantity, reorder_level, unit_price, expiry_date) VALUES
('Crocin',      'Paracetamol',   'Painkiller',    500, 100, 2.50,  '2026-12-31'),
('Augmentin',   'Amoxicillin',   'Antibiotic',    300,  50, 15.00, '2026-06-30'),
('Pantop',      'Pantoprazole',  'Antacid',       400,  80, 8.00,  '2026-09-30'),
('Metformin',   'Metformin',     'Antidiabetic',  250,  50, 5.00,  '2026-12-31'),
('Atorvastatin','Atorvastatin',  'Cholesterol',   200,  40, 12.00, '2026-08-31');

-- Insert insurance
INSERT INTO insurance(provider_name, policy_number, coverage_amount, expiry_date) VALUES
('Star Health',   'STAR-001', 200000, '2025-12-31'),
('HDFC ERGO',     'HDFC-002', 300000, '2025-10-31'),
('Bajaj Allianz', 'BAJA-003', 150000, '2026-03-31');

-- Insert sample patients
INSERT INTO patients(full_name, date_of_birth, gender, blood_group, phone, email, address, insurance_id) VALUES
('Raj Patel',      '1985-03-15', 'Male',   'B+', '9000000001', 'raj@email.com',   'Mumbai',  1),
('Priya Singh',    '1990-07-22', 'Female', 'A+', '9000000002', 'priya@email.com', 'Pune',    2),
('Amit Kumar',     '1978-11-08', 'Male',   'O+', '9000000003', 'amit@email.com',  'Nashik',  3),
('Sunita Sharma',  '1995-01-30', 'Female', 'AB+','9000000004', 'sunita@email.com','Mumbai',  1),
('Rahul Desai',    '1982-06-14', 'Male',   'B-', '9000000005', 'rahul@email.com', 'Thane',   2);