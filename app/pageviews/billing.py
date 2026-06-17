"""
pages/billing.py — Fixed
Fix: HTML metric cards rendering as raw text
"""
import streamlit as st
import pandas as pd
from db import run_query, run_query_one, call_procedure
from validators import validate_amount, validate_transaction_ref
from auth import require_role
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
import tempfile
import os

def show_dashboard(user):
    require_role(["Billing_Staff", "Admin"])

    st.markdown(
        '<p class="page-title">💰 Billing Dashboard</p>',
        unsafe_allow_html=True
    )

    # ----------------------------
    # Dashboard Metrics
    # ----------------------------
    today_rev = run_query_one("""
        SELECT COALESCE(SUM(amount_paid), 0) AS revenue
        FROM payments
        WHERE DATE(payment_date) = CURRENT_DATE
    """)

    outstanding = run_query_one("""
        SELECT COALESCE(
            SUM(
                b.net_payable -
                COALESCE(p.paid, 0)
            ),
            0
        ) AS outstanding
        FROM bills b
        LEFT JOIN (
            SELECT
                bill_id,
                SUM(amount_paid) AS paid
            FROM payments
            GROUP BY bill_id
        ) p
        ON b.bill_id = p.bill_id
        WHERE b.status != 'Paid'
    """)

    unpaid = run_query_one("""
        SELECT COUNT(*) AS c
        FROM bills
        WHERE status != 'Paid'
    """)

    fraud = run_query_one("""
        SELECT COUNT(*) AS c
        FROM fraud_alerts
        WHERE status = 'Open'
    """)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "💰 Today's Revenue",
        f"₹{float(today_rev['revenue'] or 0):,.2f}"
    )

    c2.metric(
        "💳 Outstanding",
        f"₹{float(outstanding['outstanding'] or 0):,.2f}"
    )

    c3.metric(
        "🧾 Pending Bills",
        unpaid["c"]
    )

    c4.metric(
        "🚨 Fraud Alerts",
        fraud["c"]
    )

    st.markdown("---")

    # ----------------------------
    # Recent Bills
    # ----------------------------
    left, right = st.columns(2)

    with left:
        st.subheader("📜 Recent Bills")

        recent_bills = run_query("""
            SELECT
                b.bill_id,
                p.full_name AS patient,
                b.net_payable,
                b.status,
                b.bill_date
            FROM bills b
            JOIN patients p
              ON b.patient_id = p.patient_id
            ORDER BY b.bill_date DESC
            LIMIT 5
        """)

        if recent_bills:
            import pandas as pd
            st.dataframe(
                pd.DataFrame(recent_bills),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No bills generated yet.")

    # ----------------------------
    # Recent Payments
    # ----------------------------
    with right:
        st.subheader("💳 Recent Payments")

        recent_payments = run_query("""
            SELECT
                pay.payment_id,
                p.full_name AS patient,
                pay.amount_paid,
                pay.payment_mode,
                pay.payment_date
            FROM payments pay
            JOIN bills b
              ON pay.bill_id = b.bill_id
            JOIN patients p
              ON b.patient_id = p.patient_id
            ORDER BY pay.payment_date DESC
            LIMIT 5
        """)

        if recent_payments:
            import pandas as pd
            st.dataframe(
                pd.DataFrame(recent_payments),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No payments recorded yet.")

def show_generate(user):
    require_role(["Billing_Staff", "Admin"])
    st.markdown('<p class="page-title">🧾 Generate Bill</p>', unsafe_allow_html=True)

    completed = run_query("""
        SELECT a.appt_id, p.full_name, p.phone, a.appt_date,
               d.full_name AS doctor, d.opd_fee
        FROM appointments a
        JOIN patients p ON a.patient_id=p.patient_id
        JOIN doctors d  ON a.doctor_id=d.doctor_id
        WHERE a.status='Completed'
        AND a.appt_id NOT IN (SELECT appt_id FROM bills WHERE appt_id IS NOT NULL)
        ORDER BY a.appt_date DESC
    """)

    if not completed:
        st.info("No completed appointments pending billing.")
        return

    appt_sel = st.selectbox("Select Appointment",
        [""]+[f"{a['appt_id']} — {a['full_name']} ({a['phone']}) — {a['appt_date']} — Dr.{a['doctor']}" for a in completed])

    if appt_sel:
        appt_id = int(appt_sel.split("—")[0].strip())
        appt    = next((a for a in completed if a['appt_id']==appt_id), None)
        if appt:
            lab_r  = run_query_one("SELECT COALESCE(SUM(lt.price),0) AS t FROM lab_orders lo JOIN lab_tests lt ON lo.test_id=lt.test_id WHERE lo.appt_id=%s", [appt_id])
            pha_r  = run_query_one("SELECT COALESCE(SUM(m.unit_price*pr.duration_days),0) AS t FROM diagnoses d JOIN prescriptions pr ON d.diag_id=pr.diag_id JOIN medicines m ON pr.medicine_id=m.medicine_id WHERE d.appt_id=%s", [appt_id])
            consult  = float(appt['opd_fee'] or 0)
            lab      = float(lab_r['t'] if lab_r else 0)
            pharmacy = float(pha_r['t'] if pha_r else 0)
            total    = consult + lab + pharmacy

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Consultation", f"₹{consult:,.2f}")
            col2.metric("Lab Tests",    f"₹{lab:,.2f}")
            col3.metric("Pharmacy",     f"₹{pharmacy:,.2f}")
            col4.metric("Total",        f"₹{total:,.2f}")

    if st.button("🧾 Generate Bill", type="primary",
                 use_container_width=True, disabled=not appt_sel):
        try:
            call_procedure("generate_bill", [appt_id, user["user_id"]])
            st.success("✅ Bill generated! Fraud scan completed automatically.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ {e}")


def show_payment(user):
    require_role(["Billing_Staff", "Admin"])
    st.markdown('<p class="page-title">💳 Record Payment</p>', unsafe_allow_html=True)

    bills = run_query("""
        SELECT b.bill_id, p.full_name AS patient, p.phone,
               b.total_amount, b.insurance_covered, b.net_payable,
               b.status, b.due_date,
               COALESCE(SUM(pay.amount_paid),0) AS paid_so_far,
               b.net_payable - COALESCE(SUM(pay.amount_paid),0) AS outstanding
        FROM bills b
        JOIN patients p ON b.patient_id=p.patient_id
        LEFT JOIN payments pay ON b.bill_id=pay.bill_id
        WHERE b.status!='Paid'
        GROUP BY b.bill_id, p.full_name, p.phone, b.total_amount,
                 b.insurance_covered, b.net_payable, b.status, b.due_date
        ORDER BY b.due_date ASC
    """)

    if not bills:
        st.info("No outstanding bills.")
        return

    col1, col2 = st.columns([3, 2])
    with col1:
        st.dataframe(pd.DataFrame(bills), use_container_width=True)
        bill_sel = st.selectbox("Select Bill",
            [""]+[f"{b['bill_id']} — {b['patient']} — ₹{b['outstanding']:,.2f} outstanding" for b in bills])

        if bill_sel:
            b_id  = int(bill_sel.split("—")[0].strip())
            b_inf = next((b for b in bills if b['bill_id']==b_id), None)
            if b_inf:
                outstanding = float(b_inf['outstanding'])
                st.info(f"Total: ₹{b_inf['total_amount']:,.2f} | Insurance: ₹{b_inf['insurance_covered']:,.2f} | Net: ₹{b_inf['net_payable']:,.2f} | Outstanding: ₹{outstanding:,.2f}")

                amount = st.number_input("Amount (₹) *", min_value=1.0, max_value=outstanding, value=outstanding, step=100.0)
                mode   = st.selectbox("Payment Mode *", ["Cash","Card","UPI","Insurance"])
                ref    = st.text_input("Transaction Reference", placeholder="Required for Card/UPI")

                if st.button("💳 Record Payment", type="primary"):
                    errors = []
                    ok, msg = validate_amount(amount, "Payment Amount", min_val=1, max_val=outstanding)
                    if not ok: errors.append(msg)
                    ok, msg = validate_transaction_ref(ref, mode)
                    if not ok: errors.append(msg)
                    if errors:
                        for e in errors: st.error(f"❌ {e}")
                    else:
                        try:
                            call_procedure("record_payment", [b_id, amount, mode, ref.strip() or None, user["user_id"]])
                            st.success(f"✅ Payment of ₹{amount:,.2f} recorded!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {e}")

    with col2:
        st.markdown("**Recent Payments**")
        recent = run_query("""
            SELECT p.full_name AS patient, pay.amount_paid, pay.payment_mode, pay.payment_date
            FROM payments pay JOIN bills b ON pay.bill_id=b.bill_id JOIN patients p ON b.patient_id=p.patient_id
            ORDER BY pay.payment_date DESC LIMIT 8
        """)
        if recent:
            for r in recent:
                st.markdown(f'<div style="background:#f0fdf4;border-radius:8px;padding:0.5rem 0.75rem;margin-bottom:0.4rem;font-size:0.85rem;">💳 <b>₹{r["amount_paid"]:,.2f}</b> — {r["patient"]}<br>{r["payment_mode"]} | {str(r["payment_date"])[:16]}</div>', unsafe_allow_html=True)
        else:
            st.info("No payment history yet.")


def show_fraud(user):
    require_role(["Billing_Staff", "Admin"])

    st.markdown(
        '<p class="page-title">🚨 Billing Fraud & Integrity Monitor</p>',
        unsafe_allow_html=True
    )

    # --------------------------------------------------
    # Run Fraud Scan
    # --------------------------------------------------
    col1, col2 = st.columns([1, 5])

    with col1:
        if st.button("🔍 Run Fraud Scan", use_container_width=True):
            try:
                run_query(
                    "CALL run_full_fraud_scan();",
                    fetch=False
                )
                st.success("✅ Fraud scan completed successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ {e}")

    st.markdown("---")

    # --------------------------------------------------
    # Load Alerts
    # --------------------------------------------------
    alerts = run_query("""
        SELECT *
        FROM vw_fraud_dashboard
        ORDER BY detected_at DESC
    """)

    if not alerts:
        st.success("✅ No fraud alerts detected.")
        return

    # --------------------------------------------------
    # Metrics
    # --------------------------------------------------
    high = sum(1 for a in alerts if a["severity"] == "High")
    open_alerts = sum(1 for a in alerts if a["status"] == "Open")
    reviewed = sum(1 for a in alerts if a["status"] == "Reviewed")

    c1, c2, c3 = st.columns(3)

    c1.metric("🔴 High Alerts", high)
    c2.metric("📂 Open", open_alerts)
    c3.metric("✅ Reviewed", reviewed)

    st.markdown("---")

    # --------------------------------------------------
    # Fraud Table
    # --------------------------------------------------
    import pandas as pd

    df = pd.DataFrame(alerts)

    df = df.rename(columns={
        "alert_id": "Alert ID",
        "patient": "Patient",
        "rule_triggered": "Fraud Rule",
        "severity": "Severity",
        "status": "Status",
        "detected_at": "Detected At",
        "details": "Details",
        "total_amount": "Bill Amount"
    })

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------
    # Admin Actions
    # --------------------------------------------------
    if user["role"] == "Admin":

        st.markdown("---")
        st.subheader("🛠️ Update Alert Status")

        open_ids = [
            str(a["alert_id"])
            for a in alerts
            if a["status"] == "Open"
        ]

        if not open_ids:
            st.info("No open alerts.")
            return

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            selected = st.selectbox(
                "Alert ID",
                open_ids
            )

        with col2:
            new_status = st.selectbox(
                "New Status",
                ["Reviewed", "Closed"]
            )

        with col3:
            st.write("")
            st.write("")

            if st.button(
                "Update",
                use_container_width=True
            ):
                try:
                    run_query(
                        """
                        UPDATE fraud_alerts
                        SET status=%s,
                            reviewed_by=%s
                        WHERE alert_id=%s
                        """,
                        [
                            new_status,
                            user["user_id"],
                            int(selected)
                        ],
                        fetch=False
                    )

                    st.success(
                        f"Alert #{selected} updated to '{new_status}'."
                    )
                    st.rerun()

                except Exception as e:
                    st.error(str(e))

def generate_invoice_pdf(bill_id):
    """
    Drop-in replacement.
    Expects run_query() and run_query_one() to exist in your project.
    """
    styles = getSampleStyleSheet()

    bill = run_query_one("""
        SELECT
            b.bill_id,
            b.bill_date,
            b.total_amount,
            b.insurance_covered,
            b.net_payable,
            b.status,
            b.appt_id,
            p.full_name AS patient,
            d.full_name AS doctor,
            a.appt_date,
            a.appt_time
        FROM bills b
        JOIN patients p
          ON b.patient_id = p.patient_id
        LEFT JOIN appointments a
          ON b.appt_id = a.appt_id
        LEFT JOIN doctors d
          ON a.doctor_id = d.doctor_id
        WHERE b.bill_id = %s
    """, [bill_id])

    items = run_query("""
        SELECT service_type,
               description,
               quantity,
               unit_price,
               total
        FROM bill_items
        WHERE bill_id=%s
        ORDER BY item_id
    """, [bill_id])

    payments = run_query("""
        SELECT amount_paid,
               payment_mode,
               payment_date
        FROM payments
        WHERE bill_id=%s
        ORDER BY payment_date
    """, [bill_id])

    total_amount = float(bill["total_amount"] or 0)
    insurance = float(bill["insurance_covered"] or 0)
    net_payable = float(bill["net_payable"] or 0)
    total_paid = sum(float(p["amount_paid"] or 0) for p in payments)
    outstanding = max(0.0, net_payable - total_paid)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name)
    story = []

    story.append(Paragraph("MediCare Hospital", styles["Title"]))
    story.append(Paragraph("Hospital Management System", styles["Heading2"]))
    story.append(Paragraph("Computer Generated Invoice", styles["Italic"]))
    story.append(Spacer(1, 12))

    def fmt_dt(v):
        try:
            return v.strftime("%d-%b-%Y %H:%M")
        except Exception:
            return str(v)

    story.append(Paragraph(f"<b>Invoice No:</b> {bill['bill_id']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Patient:</b> {bill['patient']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Doctor:</b> {bill.get('doctor') or 'N/A'}", styles["Normal"]))
    story.append(Paragraph(f"<b>Appointment ID:</b> {bill.get('appt_id')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Appointment:</b> {fmt_dt(bill.get('appt_date'))} {bill.get('appt_time')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Bill Date:</b> {fmt_dt(bill['bill_date'])}", styles["Normal"]))
    story.append(Spacer(1, 12))

    data = [["Service", "Description", "Qty", "Unit Price", "Total"]]
    for it in items:
        data.append([
            str(it["service_type"]),
            str(it["description"]),
            str(it["quantity"]),
            f"Rs. {float(it['unit_price']):,.2f}",
            f"Rs. {float(it['total']):,.2f}",
        ])

    tbl = Table(data)
    tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0,0), (-1,0), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 12))

    summary = [
        f"<b>Total Amount:</b> Rs. {total_amount:,.2f}",
        f"<b>Insurance Covered:</b> Rs. {insurance:,.2f}",
        f"<b>Net Payable:</b> Rs. {net_payable:,.2f}",
        f"<b>Total Paid:</b> Rs. {total_paid:,.2f}",
        f"<b>Outstanding:</b> Rs. {outstanding:,.2f}",
        f"<b>Status:</b> {bill['status']}",
    ]
    for s in summary:
        story.append(Paragraph(s, styles["Normal"]))

    if payments:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Payments</b>", styles["Heading2"]))
        pdata = [["Mode", "Amount", "Date"]]
        for p in payments:
            pdata.append([
                str(p["payment_mode"]),
                f"Rs. {float(p['amount_paid']):,.2f}",
                fmt_dt(p["payment_date"])
            ])
        pt = Table(pdata)
        pt.setStyle(TableStyle([
            ("GRID",(0,0),(-1,-1),0.5,colors.grey),
            ("BACKGROUND",(0,0),(-1,0),colors.beige),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ]))
        story.append(pt)

    story.append(Spacer(1, 18))
    story.append(Paragraph("Thank you for choosing MediCare.", styles["Italic"]))
    story.append(Paragraph("This is a computer-generated invoice and does not require a signature.", styles["Italic"]))

    doc.build(story)
    return tmp.name

def show(user, tab="dashboard"):
    require_role(["Billing_Staff", "Admin"])
    if tab=="fraud":    show_fraud(user)
    elif tab=="generate": show_generate(user)
    elif tab=="payment":  show_payment(user)
    else:               show_dashboard(user)
    
def show_bill_history(user):
    require_role(["Billing_Staff", "Admin"])

    st.markdown(
        '<p class="page-title">📜 Bill History</p>',
        unsafe_allow_html=True
    )

    search = st.text_input(
        "Search Patient",
        placeholder="Enter patient name"
    )

    status = st.selectbox(
        "Status",
        ["All", "Unpaid", "Partial", "Paid"]
    )

    query = """
        SELECT
            b.bill_id,
            p.full_name,
            b.bill_date,
            b.total_amount,
            b.insurance_covered,
            b.net_payable,
            b.status
        FROM bills b
        JOIN patients p
            ON b.patient_id = p.patient_id
        WHERE 1=1
    """

    params = []

    if search.strip():
        query += " AND LOWER(p.full_name) LIKE LOWER(%s)"
        params.append(f"%{search.strip()}%")

    if status != "All":
        query += " AND b.status=%s"
        params.append(status)

    query += " ORDER BY b.bill_date DESC"

    bills = run_query(query, params if params else None)

    if not bills:
        st.info("No bills found.")
        return

    import pandas as pd

    st.dataframe(
        pd.DataFrame(bills),
        use_container_width=True
    )

    selected = st.selectbox(
        "Select Bill",
        [""] + [
            f"{b['bill_id']} — {b['full_name']}"
            for b in bills
        ]
    )

    if not selected:
        return

    bill_id = int(selected.split("—")[0].strip())

    st.markdown("---")
    st.subheader("Bill Details")

    items = run_query("""
        SELECT
            service_type,
            description,
            quantity,
            unit_price,
            total
        FROM bill_items
        WHERE bill_id=%s
    """, [bill_id])

    if items:
        st.table(pd.DataFrame(items))

    payments = run_query("""
        SELECT
            amount_paid,
            payment_mode,
            payment_date
        FROM payments
        WHERE bill_id=%s
        ORDER BY payment_date
    """, [bill_id])

    st.subheader("Payment History")

    if payments:
        st.table(pd.DataFrame(payments))
    else:
        st.info("No payments recorded yet.")

    summary = run_query_one("""
        SELECT
            net_payable,
            COALESCE(
                (
                    SELECT SUM(amount_paid)
                    FROM payments
                    WHERE bill_id=%s
                ),
                0
            ) AS paid
        FROM bills
        WHERE bill_id=%s
    """, [bill_id, bill_id])

    outstanding = (
        float(summary["net_payable"])
        - float(summary["paid"])
    )

    st.success(
        f"""
Net Payable: ₹{summary['net_payable']:,.2f}

Paid: ₹{summary['paid']:,.2f}

Outstanding: ₹{outstanding:,.2f}
"""
    )
    
    # -----------------------------
    # Download Invoice PDF
    # -----------------------------
    pdf_path = generate_invoice_pdf(bill_id)

    with open(pdf_path, "rb") as f:
        st.download_button(
            label="📄 Download Invoice",
            data=f.read(),
            file_name=f"Invoice_{bill_id}.pdf",
            mime="application/pdf",
            use_container_width=True
        )