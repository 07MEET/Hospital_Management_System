"""
validators.py — FIXED VERSION
Fix: register_patient was always failing validation
Root cause: validate_dob min_value check was too strict,
            email was required but should be optional
Fix 2: validate_appointment_time now accepts date param
       to enforce 2-hour minimum buffer for today's appointments
"""
import re
from datetime import date, datetime, timedelta


def validate_email(email: str) -> tuple:
    """Email is optional. Only validate format if provided."""
    if not email or not email.strip():
        return True, ""  # Optional field — pass if empty
    email = email.strip().lower()
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format. Example: name@example.com"
    if len(email) > 254:
        return False, "Email is too long (max 254 characters)."
    if '..' in email:
        return False, "Email cannot contain consecutive dots."
    return True, ""


def validate_phone(phone: str) -> tuple:
    if not phone or not phone.strip():
        return False, "Phone number is required."
    clean = re.sub(r'[\s\-\+\(\)]', '', phone.strip())
    if clean.startswith('91') and len(clean) == 12:
        clean = clean[2:]
    if not clean.isdigit():
        return False, "Phone number must contain digits only."
    if len(clean) != 10:
        return False, f"Phone must be exactly 10 digits. You entered {len(clean)} digit(s)."
    if clean[0] not in '6789':
        return False, "Indian mobile numbers must start with 6, 7, 8, or 9."
    return True, ""


def validate_name(name: str, field: str = "Name") -> tuple:
    if not name or not name.strip():
        return False, f"{field} is required."
    name = name.strip()
    if len(name) < 2:
        return False, f"{field} must be at least 2 characters."
    if len(name) > 100:
        return False, f"{field} must be under 100 characters."
    if not re.match(r"^[A-Za-z\s\.\-']+$", name):
        return False, f"{field} can only contain letters, spaces, dots and hyphens."
    return True, ""


def validate_dob(dob) -> tuple:
    if dob is None:
        return False, "Date of birth is required."
    today = date.today()
    if hasattr(dob, 'date'):
        dob = dob.date()
    if dob >= today:
        return False, "Date of birth must be in the past."
    age = (today - dob).days // 365
    if age > 120:
        return False, "Age cannot exceed 120 years."
    return True, ""


def validate_appointment_date(appt_date) -> tuple:
    if appt_date is None:
        return False, "Appointment date is required."
    today = date.today()
    if hasattr(appt_date, 'date'):
        appt_date = appt_date.date()
    if appt_date < today:
        return False, "Appointment date cannot be in the past."
    if (appt_date - today).days > 365:
        return False, "Cannot schedule more than 1 year in advance."
    return True, ""


def validate_appointment_time(appt_time, appt_date=None) -> tuple:
    """
    Validates appointment time.
    - Must be between 8:00 AM and 8:00 PM
    - If appointment is today, must be at least 2 hours from now
    """
    if appt_time is None:
        return False, "Appointment time is required."

    hour = appt_time.hour if hasattr(appt_time, 'hour') else int(str(appt_time).split(':')[0])

    if hour < 8:
        return False, "Appointments cannot be before 8:00 AM."
    if hour >= 20:
        return False, "Appointments cannot be after 8:00 PM."

    # 2-hour buffer check — only when booking for today
    if appt_date is not None:
        # Normalise appt_date to a date object
        if hasattr(appt_date, 'date'):
            appt_date = appt_date.date()
        if appt_date == date.today():
            min_allowed = (datetime.now() + timedelta(hours=2)).time().replace(second=0, microsecond=0)
            if appt_time < min_allowed:
                return False, (
                    f"For today's appointments, time must be at least 2 hours from now "
                    f"(earliest allowed: {min_allowed.strftime('%I:%M %p')})."
                )

    return True, ""


def validate_password(password: str) -> tuple:
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-\[\]]', password):
        return False, "Password must contain at least one special character (!@#$%)."
    return True, ""


def validate_username(username: str) -> tuple:
    if not username or not username.strip():
        return False, "Username is required."
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(username) > 50:
        return False, "Username must be under 50 characters."
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers and underscores."
    if username[0].isdigit():
        return False, "Username cannot start with a number."
    return True, ""


def validate_amount(amount, field="Amount", min_val=0.01, max_val=10000000) -> tuple:
    if amount is None:
        return False, f"{field} is required."
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return False, f"{field} must be a valid number."
    if amount < min_val:
        return False, f"{field} must be at least ₹{min_val:.2f}."
    if amount > max_val:
        return False, f"{field} cannot exceed ₹{max_val:,.2f}."
    return True, ""


def validate_icd_code(code: str) -> tuple:
    if not code or not code.strip():
        return False, "ICD code is required."
    code = code.strip().upper()
    if not re.match(r'^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$', code):
        return False, "Invalid ICD-10 format. Use e.g. J18.9 or A00"
    return True, ""


def validate_text(text: str, field="Field", required=True, max_len=1000) -> tuple:
    if required and (not text or not text.strip()):
        return False, f"{field} is required."
    if text and len(text) > max_len:
        return False, f"{field} cannot exceed {max_len} characters."
    return True, ""


def validate_dosage(dosage: str) -> tuple:
    if not dosage or not dosage.strip():
        return False, "Dosage is required (e.g. 500mg, 10ml, 1 tablet)."
    if len(dosage.strip()) > 50:
        return False, "Dosage too long (max 50 characters)."
    return True, ""


def validate_duration_days(days) -> tuple:
    try:
        days = int(days)
    except (TypeError, ValueError):
        return False, "Duration must be a whole number."
    if days < 1:
        return False, "Duration must be at least 1 day."
    if days > 365:
        return False, "Duration cannot exceed 365 days."
    return True, ""


def validate_transaction_ref(ref: str, mode: str) -> tuple:
    if mode in ['Card', 'UPI'] and (not ref or not ref.strip()):
        return False, f"Transaction reference is required for {mode} payments."
    return True, ""


def validate_medicine_name(name: str) -> tuple:
    if not name or not name.strip():
        return False, "Medicine name is required."
    if len(name.strip()) < 2:
        return False, "Medicine name must be at least 2 characters."
    if len(name.strip()) > 100:
        return False, "Medicine name too long."
    return True, ""


def validate_stock_quantity(qty) -> tuple:
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        return False, "Stock quantity must be a whole number."
    if qty < 0:
        return False, "Stock quantity cannot be negative."
    if qty > 1000000:
        return False, "Stock quantity seems too high."
    return True, ""


def sanitize_string(s: str) -> str:
    if not s:
        return ""
    return ' '.join(s.strip().split())


def sanitize_phone(phone: str) -> str:
    clean = re.sub(r'[^\d]', '', phone or "")
    if len(clean) == 12 and clean.startswith('91'):
        clean = clean[2:]
    return clean[-10:] if len(clean) >= 10 else clean


def sanitize_email(email: str) -> str:
    return (email or "").strip().lower()