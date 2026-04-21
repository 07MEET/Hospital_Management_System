"""
components/patient_card.py — Patient display and search UI components
"""
import streamlit as st
from db import run_query


def patient_card(patient: dict, show_actions: bool = False, compact: bool = False):
    """
    Render a styled patient information card.

    Args:
        patient:      dict with patient fields
        show_actions: show action buttons (View, Edit)
        compact:      render a smaller version
    """
    p = patient

    # Age from DOB
    age_str = ""
    if p.get("date_of_birth"):
        from datetime import date
        try:
            dob = p["date_of_birth"]
            if hasattr(dob, "year"):
                age = (date.today() - dob).days // 365
                age_str = f"{age} yrs"
        except Exception:
            pass

    status_color = {
        "Active":    "#10b981",
        "Discharged":"#64748b",
    }.get(str(p.get("status", "")), "#64748b")

    if compact:
        st.markdown(f"""
        <div class="patient-card" style="padding:0.75rem 1rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div class="patient-name" style="font-size:0.95rem;">
                        👤 {p.get('full_name', 'N/A')}
                    </div>
                    <div class="patient-meta">
                        📞 {p.get('phone','—')} &nbsp;|&nbsp;
                        🩸 {p.get('blood_group','—')} &nbsp;|&nbsp;
                        {age_str}
                    </div>
                </div>
                <div>
                    <span style="background:#e0fdf4;color:{status_color};
                                 padding:3px 10px;border-radius:20px;
                                 font-size:0.72rem;font-weight:600;">
                        {p.get('status','—')}
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Full card
    ins = p.get("insurance_id") or p.get("provider_name")
    ins_html = f"🛡️ {p.get('provider_name', 'Insured')}" if ins else "🔓 No Insurance"

    st.markdown(f"""
    <div class="patient-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;
                    margin-bottom:0.75rem;">
            <div>
                <div class="patient-name">👤 {p.get('full_name','N/A')}</div>
                <div class="patient-meta" style="margin-top:4px;">
                    ID #{p.get('patient_id','—')} &nbsp;|&nbsp;
                    Registered: {str(p.get('registration_date','—'))[:10]}
                </div>
            </div>
            <span style="background:#e0fdf4;color:{status_color};
                         padding:4px 12px;border-radius:20px;
                         font-size:0.78rem;font-weight:700;">
                {p.get('status','—')}
            </span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.4rem;
                    font-size:0.85rem;color:#475569;">
            <div>📞 {p.get('phone','—')}</div>
            <div>📧 {p.get('email','—') or '—'}</div>
            <div>🩸 {p.get('blood_group','—')}</div>
            <div>🎂 {str(p.get('date_of_birth','—'))[:10]} {('(' + age_str + ')') if age_str else ''}</div>
            <div>⚧ {p.get('gender','—')}</div>
            <div>{ins_html}</div>
            <div style="grid-column:1/-1;">📍 {p.get('address','—') or '—'}</div>
            <div style="grid-column:1/-1;">🆘 {p.get('emergency_contact','—') or '—'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if show_actions:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 View History", key=f"view_{p.get('patient_id')}"):
                st.session_state["view_patient_id"] = p["patient_id"]
        with col2:
            if st.button("✏️ Edit Details", key=f"edit_{p.get('patient_id')}"):
                st.session_state["edit_patient_id"] = p["patient_id"]


def patient_search_box(
    key:          str   = "patient_search",
    label:        str   = "Search Patient",
    placeholder:  str   = "Name, phone, or patient ID",
    min_chars:    int   = 2,
    show_card:    bool  = True,
) -> dict | None:
    """
    A reusable patient search input with auto-results.

    Returns the selected patient dict or None.
    """
    search = st.text_input(
        label,
        placeholder=placeholder,
        key=key,
        help=f"Type at least {min_chars} characters to search"
    )

    if not search or len(search.strip()) < min_chars:
        return None

    # Search by name, phone, or ID
    query = """
        SELECT p.patient_id, p.full_name, p.phone, p.date_of_birth,
               p.blood_group, p.gender, p.status, p.email, p.address,
               p.emergency_contact, p.registration_date,
               i.provider_name
        FROM patients p
        LEFT JOIN insurance i ON p.insurance_id = i.insurance_id
        WHERE LOWER(p.full_name) LIKE LOWER(%s)
           OR p.phone LIKE %s
           OR CAST(p.patient_id AS TEXT) = %s
        ORDER BY p.full_name
        LIMIT 10
    """
    results = run_query(query, [f"%{search}%", f"%{search}%", search.strip()])

    if not results:
        st.info("ℹ️ No patients found. Try a different search term.")
        return None

    options = {
        f"#{p['patient_id']} — {p['full_name']} ({p['phone']})": p
        for p in results
    }

    if len(options) == 1:
        selected = list(options.values())[0]
    else:
        choice = st.selectbox(
            f"Found {len(options)} patient(s) — select one:",
            [""] + list(options.keys()),
            key=f"{key}_select"
        )
        selected = options.get(choice)

    if selected and show_card:
        patient_card(selected, compact=True)

    return selected


def patient_history_card(patient_id: int):
    """Show full visit history for a patient."""
    history = run_query("""
        SELECT a.appt_date, a.appt_type, d.full_name AS doctor,
               dept.dept_name AS department,
               di.icd_code, di.description AS diagnosis,
               di.severity, a.status
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        JOIN departments dept ON d.dept_id = dept.dept_id
        LEFT JOIN diagnoses di ON a.appt_id = di.appt_id
        WHERE a.patient_id = %s
        ORDER BY a.appt_date DESC
        LIMIT 20
    """, [patient_id])

    if not history:
        st.info("No visit history found for this patient.")
        return

    for h in history:
        severity_color = {
            "Mild":     "#d1fae5",
            "Moderate": "#fef3c7",
            "Severe":   "#fee2e2",
        }.get(h.get("severity", ""), "#f8fafc")

        st.markdown(f"""
        <div style="background:{severity_color};border-radius:10px;
                    padding:0.85rem 1rem;margin-bottom:0.5rem;
                    border:1px solid #e2e8f0;">
            <div style="display:flex;justify-content:space-between;">
                <span style="font-weight:600;color:#1a3c64;">
                    📅 {str(h['appt_date'])[:10]} — {h['appt_type']}
                </span>
                <span style="font-size:0.8rem;color:#64748b;">
                    {h['status']}
                </span>
            </div>
            <div style="font-size:0.85rem;color:#475569;margin-top:4px;">
                👨‍⚕️ Dr. {h['doctor']} ({h['department']})
            </div>
            {"<div style='font-size:0.85rem;color:#374151;margin-top:4px;'>" +
             "🩺 " + str(h.get('icd_code','')) + " — " + str(h.get('diagnosis','No diagnosis recorded')) +
             ("  |  Severity: <b>" + h['severity'] + "</b>" if h.get('severity') else "") +
             "</div>"
             if h.get('diagnosis') else ""}
        </div>
        """, unsafe_allow_html=True)
