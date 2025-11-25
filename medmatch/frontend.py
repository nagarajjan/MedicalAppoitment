import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="MedMatch Pro", layout="wide", page_icon="🩺")

# --- CSS ---
st.markdown("""
<style>
    .slot-card { padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 0.85em; }
    .status-open { background-color: white; border: 2px solid #28a745; color: #28a745; }
    .status-pending { background-color: #fff3cd; border: 2px solid #ffc107; color: #856404; }
    .status-confirmed { background-color: #f8d7da; border: 2px solid #dc3545; color: #721c24; }
    .status-completed { background-color: #d1ecf1; border: 2px solid #17a2b8; color: #0c5460; }
    .status-blocked { background-color: #e2e3e5; border: 2px solid #6c757d; color: #383d41; }
    div.stButton > button { width: 100%; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

if 'user' not in st.session_state: st.session_state.user = None
def logout(): st.session_state.user = None; st.rerun()

def get_time_slots():
    slots = []
    start = datetime.strptime("09:00", "%H:%M")
    end = datetime.strptime("17:00", "%H:%M")
    while start < end:
        slots.append(start.strftime("%H:%M"))
        start += timedelta(minutes=30)
    return slots

# ==========================================
# 🔐 AUTH
# ==========================================
if not st.session_state.user:
    st.title("🏥 MedMatch Pro")
    t1, t2 = st.tabs(["Login", "Register"])
    
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            role = st.selectbox("Role", ["Patient", "Doctor", "Admin"])
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.button("Login"):
                try:
                    res = requests.post(f"{API_URL}/auth/login", json={"role": role, "email": email, "password": pw})
                    if res.status_code == 200: 
                        st.session_state.user = res.json()
                        st.rerun()
                    else: st.error("Invalid")
                except: st.error("Server Error")

    with t2:
        c1, c2 = st.columns(2)
        with c1:
            r_role = st.selectbox("Register as", ["Patient", "Doctor", "Admin"])
            r_name = st.text_input("Name")
            r_email = st.text_input("Email (User)")
            r_pw = st.text_input("Password (8-10 chars, @#$%&*)", type="password")
            r_phone = st.text_input("Phone Number")
            
            extra, fee, dob = "", 0.0, ""
            if r_role == "Patient": 
                dob = str(st.date_input("Date of Birth", min_value=datetime(1900,1,1)))
                extra = str(st.number_input("Age", 18))
            elif r_role == "Doctor":
                try:
                    specs = requests.get(f"{API_URL}/specialties/all").json()
                    if specs:
                        spec_map = {s['name']: s['id'] for s in specs}
                        s_name = st.selectbox("Specialty", list(spec_map.keys()))
                        extra = str(spec_map[s_name])
                    else: st.warning("No Specialties available")
                    fee = st.number_input("Consulting Fee ($)", value=100.0)
                except: st.warning("DB Error")

            if st.button("Create Account"):
                try:
                    pl = {"role": r_role, "name": r_name, "email": r_email, "password": r_pw, "phone": r_phone, "extra_field": extra, "dob": dob, "fee": fee}
                    res = requests.post(f"{API_URL}/auth/register", json=pl)
                    if res.status_code == 200: st.success("Success! Login now."); 
                    else: st.error(res.text)
                except: st.error("Error")

# ==========================================
# 🚀 MAIN APP
# ==========================================
else:
    user = st.session_state.user
    with st.sidebar:
        st.header(f"{user['role']}")
        st.info(user['name'])
        if st.button("Logout"): logout()

    tabs = st.tabs(["🏠 Dashboard", "👤 My Profile"])
    
    # --- PROFILE TAB ---
    with tabs[1]:
        st.subheader("Update My Record")
        with st.form("profile_upd"):
            c1, c2 = st.columns(2)
            u_name = c1.text_input("Name", value=user['name'])
            u_email = c2.text_input("Email", value=user['email'])
            
            u_phone, u_dob, u_fee, u_qual = "", "", 0.0, ""
            if user['role'] == "Patient":
                u_phone = c1.text_input("Phone", value=user.get('phone', ''))
                u_dob = c2.text_input("DOB", value=user.get('dob', ''))
            elif user['role'] == "Doctor":
                u_phone = c1.text_input("Phone", value=user.get('phone', ''))
                u_fee = c2.number_input("Consulting Fee", value=float(user.get('fee', 100.0)))
                u_qual = st.text_input("Qualification", value=user.get('qual', 'MD'))
            
            st.markdown("---")
            u_pass = st.text_input("New Password (Leave blank to keep current)", type="password")
            
            if st.form_submit_button("Update Profile"):
                pl = {
                    "role": user['role'], "user_id": user['id'], 
                    "name": u_name, "email": u_email, "password": u_pass,
                    "phone": u_phone, "dob": u_dob, "fee": u_fee, "qualification": u_qual
                }
                res = requests.put(f"{API_URL}/auth/update_profile", json=pl)
                if res.status_code == 200: st.success("Updated! Please re-login."); logout()
                else: st.error("Update failed")

    # --- DASHBOARD TAB ---
    with tabs[0]:
        
        # PATIENT
        if user['role'] == "Patient":
            st.subheader("📅 Find & Book")
            pt1, pt2 = st.tabs(["🔍 AI Match", "📂 Browse Directory"])
            
            with pt1:
                symptoms = st.text_area("Describe Symptoms")
                if st.button("Find Doctor"):
                    res = requests.post(f"{API_URL}/analyze/doctors", json={"description": symptoms}).json()
                    st.session_state['search'] = res; st.session_state['sym'] = symptoms
                
                if 'search' in st.session_state:
                    res = st.session_state['search']
                    st.success(f"Recommended: {res['specialty']}")
                    doc_map = {d['name']: d['id'] for d in res['doctors']}
                    sel_doc = st.selectbox("Select Doctor", list(doc_map.keys()), key="aid")
                    
                    if sel_doc:
                        doc_id = doc_map[sel_doc]
                        d_str = st.date_input("Date", min_value=datetime.today(), key="aidt").strftime("%Y-%m-%d")
                        slots = requests.get(f"{API_URL}/calendar/slots", params={"doctor_id": doc_id, "date": d_str}).json()
                        
                        cols = st.columns(4)
                        for i, time in enumerate(get_time_slots()):
                            info = slots.get(time)
                            with cols[i%4]:
                                if info is None:
                                    st.markdown(f'<div class="slot-card status-open">{time}<br>Open</div>', unsafe_allow_html=True)
                                    if st.button("Book", key=f"ai_{time}"):
                                        requests.post(f"{API_URL}/calendar/book", json={"patient_id": user['id'], "doctor_id": doc_id, "date": d_str, "time": time, "symptoms": st.session_state['sym']})
                                        st.rerun()
                                elif info['status'] == "PENDING":
                                    msg = "My Req" if info['patient_id'] == user['id'] else "Pending"
                                    st.markdown(f'<div class="slot-card status-pending">{time}<br>{msg}</div>', unsafe_allow_html=True)
                                else:
                                    st.markdown(f'<div class="slot-card status-confirmed">{time}<br>Busy</div>', unsafe_allow_html=True)

            with pt2:
                specs = requests.get(f"{API_URL}/specialties/all").json()
                docs = requests.get(f"{API_URL}/doctors/all").json()
                s_sel = st.selectbox("Filter by Specialty", ["All"] + [s['name'] for s in specs])
                
                filtered = docs
                if s_sel != "All":
                    sid = next((s['id'] for s in specs if s['name'] == s_sel), None)
                    if sid:
                        filtered = [d for d in docs if d['specialty_id'] == sid]
                
                if filtered:
                    d_map = {f"{d['name']} ({d['qualification']})": d['id'] for d in filtered}
                    t_doc = st.selectbox("Choose Doctor", list(d_map.keys()))
                    if t_doc:
                        tid = d_map[t_doc]
                        t_date = st.date_input("Date", min_value=datetime.today(), key="mdt").strftime("%Y-%m-%d")
                        t_slots = requests.get(f"{API_URL}/calendar/slots", params={"doctor_id": tid, "date": t_date}).json()
                        
                        cols = st.columns(4)
                        for i, time in enumerate(get_time_slots()):
                            info = t_slots.get(time)
                            with cols[i%4]:
                                if info is None:
                                    st.markdown(f'<div class="slot-card status-open">{time}<br>Open</div>', unsafe_allow_html=True)
                                    with st.popover(f"Book {time}"):
                                        sym = st.text_input("Sym", key=f"ms_{time}")
                                        if st.button("Confirm", key=f"mb_{time}"):
                                            requests.post(f"{API_URL}/calendar/book", json={"patient_id": user['id'], "doctor_id": tid, "date": t_date, "time": time, "symptoms": sym}); st.rerun()
                                else:
                                    st.markdown(f'<div class="slot-card status-confirmed">{time}<br>Busy</div>', unsafe_allow_html=True)

        # DOCTOR
        elif user['role'] == "Doctor":
            dt1, dt2 = st.tabs(["📅 Schedule", "🧠 AI Assistant"])
            with dt1:
                d_str = st.date_input("Date", min_value=datetime.today()).strftime("%Y-%m-%d")
                slots = requests.get(f"{API_URL}/calendar/slots", params={"doctor_id": user['id'], "date": d_str}).json()
                cols = st.columns(4)
                for i, time in enumerate(get_time_slots()):
                    info = slots.get(time)
                    with cols[i%4]:
                        if info is None:
                            st.markdown(f'<div class="slot-card status-open">{time}<br>Open</div>', unsafe_allow_html=True)
                            if st.button("Block", key=f"blk_{time}"):
                                requests.post(f"{API_URL}/calendar/block", params={"doc_id": user['id'], "date": d_str, "time": time}); st.rerun()
                        elif info['status'] == "PENDING":
                            st.markdown(f'<div class="slot-card status-pending">{time}<br>REQ</div>', unsafe_allow_html=True)
                            with st.popover("Action"):
                                st.write(f"Sym: {info['symptom']}")
                                if st.button("✅", key=f"a_{time}"): requests.post(f"{API_URL}/calendar/action", params={"appt_id": info['id'], "action": "approve"}); st.rerun()
                                if st.button("❌", key=f"d_{time}"): requests.post(f"{API_URL}/calendar/action", params={"appt_id": info['id'], "action": "cancel"}); st.rerun()
                        elif info['status'] == "CONFIRMED":
                            st.markdown(f'<div class="slot-card status-confirmed">{time}<br>{info["patient_name"]}</div>', unsafe_allow_html=True)
                            with st.popover("Manage"):
                                c_a, c_b = st.tabs(["Consult", "Cancel"])
                                with c_a:
                                    with st.form(f"c_{time}"):
                                        diag = st.text_input("Diagnosis")
                                        note = st.text_area("Notes")
                                        fee = st.number_input("Fee", value=user.get('fee', 100.0))
                                        if st.form_submit_button("Finish"):
                                            requests.post(f"{API_URL}/doctor/consult", json={"appt_id": info['id'], "diagnosis": diag, "notes": note, "charges": fee}); st.rerun()
                                with c_b:
                                    st.warning("Cancel appointment?")
                                    if st.button("Cancel Appt", key=f"can_{time}"):
                                        requests.post(f"{API_URL}/calendar/action", params={"appt_id": info['id'], "action": "cancel"}); st.rerun()
                        elif info['status'] == "COMPLETED":
                            st.markdown(f'<div class="slot-card status-completed">{time}<br>Done</div>', unsafe_allow_html=True)
                        elif info['status'] == "BLOCKED":
                            st.markdown(f'<div class="slot-card status-blocked">{time}<br>Blocked</div>', unsafe_allow_html=True)
                            if st.button("Unblock", key=f"ub_{time}"):
                                requests.post(f"{API_URL}/calendar/action", params={"appt_id": info['id'], "action": "cancel"}); st.rerun()

            with dt2:
                q = st.text_input("Query Similar Cases")
                if st.button("Search"):
                    res = requests.post(f"{API_URL}/knowledge/query", json={"description": q}).json()
                    st.write(res)

        # ADMIN
        elif user['role'] == "Admin":
            at1, at2, at3 = st.tabs(["📊 Reports", "👥 Manage Users", "⚙️ Master Data"])
            
            with at1:
                st.subheader("Advanced Reporting")
                with st.sidebar:
                    st.write("### Filter Report")
                    d1 = st.date_input("Start Date", value=None)
                    d2 = st.date_input("End Date", value=None)
                    
                    try:
                        docs = requests.get(f"{API_URL}/doctors/all").json()
                        doc_sel = st.selectbox("Doctor", ["All"] + [d['name'] for d in docs])
                        doc_id = next((d['id'] for d in docs if d['name'] == doc_sel), None) if doc_sel != "All" else None
                        
                        specs = requests.get(f"{API_URL}/specialties/all").json()
                        spec_sel = st.selectbox("Specialty", ["All"] + [s['name'] for s in specs])
                        spec_id = next((s['id'] for s in specs if s['name'] == spec_sel), None) if spec_sel != "All" else None
                    except:
                        st.warning("Could not load filters")
                        doc_id, spec_id = None, None

                if st.button("Generate Report"):
                    pl = {"start_date": d1.strftime("%Y-%m-%d") if d1 else None, "end_date": d2.strftime("%Y-%m-%d") if d2 else None, "doctor_id": doc_id, "specialty_id": spec_id}
                    try:
                        resp = requests.post(f"{API_URL}/reports/advanced", json=pl)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data:
                                df = pd.DataFrame(data)
                                st.dataframe(df)
                                st.metric("Total Revenue", f"${df['Fee'].sum():,.2f}")
                                st.download_button("Download CSV", df.to_csv().encode('utf-8'), "report.csv", "text/csv")
                            else: st.info("No records match filters.")
                        else:
                            st.error(f"Report Error: {resp.text}")
                    except Exception as e:
                        st.error(f"Failed to fetch report: {e}")

            with at2:
                st.subheader("User Management")
                m_role = st.radio("Select Role", ["Patient", "Doctor", "Admin"], horizontal=True)
                users = requests.get(f"{API_URL}/users/all", params={"role": m_role}).json()
                if users:
                    udf = pd.DataFrame(users)
                    st.dataframe(udf)
                    
                    c_del, c_upd = st.tabs(["Delete User", "Update User"])
                    with c_del:
                        d_id = st.number_input("Enter ID to Delete", min_value=1, key="del_id")
                        if st.button("Delete User"):
                            r = requests.delete(f"{API_URL}/admin/delete_user", params={"role": m_role, "id": d_id})
                            if r.status_code == 200: st.success("Deleted"); st.rerun()
                            else: st.error("Failed")
                    with c_upd:
                        u_id = st.number_input("Enter ID to Update", min_value=1, key="upd_id")
                        with st.form("adm_upd_form"):
                            un = st.text_input("New Name")
                            ue = st.text_input("New Email")
                            up = st.text_input("New Phone")
                            upw = st.text_input("New Password (Optional)")
                            if st.form_submit_button("Update User"):
                                pl = {"target_role": m_role, "target_id": u_id, "name": un, "email": ue, "phone": up, "password": upw}
                                requests.put(f"{API_URL}/admin/update_user", json=pl)
                                st.success("Updated"); st.rerun()

            with at3:
                st.subheader("Specialties & Symptoms")
                c_m1, c_m2 = st.columns(2)
                
                with c_m1:
                    st.write("#### Specialties")
                    sp = requests.get(f"{API_URL}/specialties/all").json()
                    st.dataframe(sp)
                    
                    with st.expander("Add Specialty"):
                        ns = st.text_input("Name")
                        if st.button("Add Spec"):
                            requests.post(f"{API_URL}/master/specialty", params={"action": "add", "name": ns})
                            st.rerun()
                    
                    with st.expander("Update/Delete Specialty"):
                        if sp:
                            target_sp = st.selectbox("Select Specialty", [s['name'] for s in sp], key="dsp")
                            sp_id = next(s['id'] for s in sp if s['name'] == target_sp)
                            if st.button("Delete Selected Spec"):
                                r = requests.post(f"{API_URL}/master/specialty", params={"action": "delete", "name": "", "id": sp_id})
                                if r.status_code != 200: st.error(r.json()['detail'])
                                else: st.rerun()
                            
                            new_sp_name = st.text_input("New Name", key="nsp_ren")
                            if st.button("Rename"):
                                requests.post(f"{API_URL}/master/specialty", params={"action": "update", "name": new_sp_name, "id": sp_id})
                                st.rerun()

                with c_m2:
                    st.write("#### Symptoms")
                    sy = requests.get(f"{API_URL}/symptoms/all").json()
                    st.dataframe(sy)
                    
                    with st.expander("Add Symptom"):
                        if sp:
                            tgt_spec = st.selectbox("Link to Specialty", [s['name'] for s in sp])
                            n_kw = st.text_input("Keyword")
                            if st.button("Add Symp"):
                                sid = next(s['id'] for s in sp if s['name'] == tgt_spec)
                                requests.post(f"{API_URL}/master/symptom", params={"action": "add", "keyword": n_kw, "spec_id": sid})
                                st.rerun()
                    
                    with st.expander("Delete Symptom"):
                        if sy:
                            del_sym = st.selectbox("Select Symptom", [s['keyword'] for s in sy])
                            if st.button("Delete Symp"):
                                sy_id = next(s['id'] for s in sy if s['keyword'] == del_sym)
                                requests.post(f"{API_URL}/master/symptom", params={"action": "delete", "keyword": "", "id": sy_id})
                                st.rerun()