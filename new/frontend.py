import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="MedMatch Pro", layout="wide", page_icon="🩺")

# --- STATE INIT ---
for k in ['user', 'admin_report_data', 'edit_u', 'pat_search', 'doc_ai_res']:
    if k not in st.session_state: st.session_state[k] = None

def logout():
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

def get_sess():
    s=requests.Session(); r=Retry(total=3, backoff_factor=0.2, status_forcelist=[500]); s.mount('http://', HTTPAdapter(max_retries=r)); return s
http=get_sess()

def get_slots(dt_str):
    s=[]; t=datetime.strptime("09:00","%H:%M"); e=datetime.strptime("17:00","%H:%M")
    sel_dt = datetime.strptime(dt_str, "%Y-%m-%d").date()
    now = datetime.now()
    while t<e:
        tm_str = t.strftime("%H:%M")
        is_past = False
        # Calculate if past
        slot_dt = datetime.combine(sel_dt, t.time())
        if slot_dt < now: is_past = True
        
        s.append({"time": tm_str, "is_past": is_past})
        t+=timedelta(minutes=30)
    return s

# CSS
st.markdown("""<style>
    .slot-card { padding:10px;border-radius:8px;text-align:center;margin:4px;font-weight:bold;font-size:0.8em;box-shadow:0 2px 4px #0002;color:#333;}
    .status-open { background:white; border:2px solid #28a745; color:#28a745!important; cursor:pointer; }
    .status-pending { background:#fff3cd; border:2px solid #ffc107; color:#d35400!important; }
    .status-confirmed { background:#f8d7da; border:2px solid #dc3545; color:#c0392b!important; }
    .status-completed { background:#e3f2fd; border:2px solid #2196f3; color:#0277bd!important; }
    .status-blocked { background:#cfd8dc; border:2px solid #78909c; color:#555!important; cursor:not-allowed; }
    .status-past { background:#f0f0f0; border:1px solid #ddd; color:#aaa!important; cursor:not-allowed; }
    .stButton>button{width:100%; border-radius:5px;}
</style>""", unsafe_allow_html=True)

try: C=http.get(f"{API_URL}/config/read").json(); st.markdown(f"<h2 style='text-align:center;color:#003366'>{C.get('platform_title')}</h2>", unsafe_allow_html=True)
except: pass

# LOGIN
if not st.session_state.user:
    t1, t2 = st.tabs(["Login", "Register"])
    with t1:
        c1,c2=st.columns(2)
        with c1:
            r=st.selectbox("Role",["Patient","Doctor","Admin"]); e=st.text_input("Email"); p=st.text_input("Password",type="password")
            if st.button("Login"):
                try:
                    rs=http.post(f"{API_URL}/auth/login", json={"role":r,"email":e,"password":p})
                    if rs.status_code==200: st.session_state.user=rs.json(); st.rerun()
                    else: st.error("Invalid")
                except: st.error("Connection Failed")
    with t2:
        c1,c2=st.columns(2)
        with c1:
            rr=st.selectbox("Register As",["Patient","Doctor","Admin"]); rn=st.text_input("Name"); re=st.text_input("UsrEmail"); rp=st.text_input("Pass (4+)",type="password"); ph=st.text_input("Ph")
            ex,fe,db="",0.0,""
            if rr=="Patient": db=str(st.date_input("DOB",datetime(1990,1,1))); ex=str(st.number_input("Age",18))
            elif rr=="Doctor":
                sl=http.get(f"{API_URL}/specialties/all").json()
                if sl: m={s['name']:s['id'] for s in sl}; k=st.selectbox("Spc",list(m.keys())); ex=str(m[k])
                fe=st.number_input("Fee",100.0)
            if st.button("Register"):
                http.post(f"{API_URL}/auth/register", json={"role":rr,"name":rn,"email":re,"password":rp,"phone":ph,"extra_field":ex,"dob":db,"fee":fe}); st.success("OK Login")

# APP
else:
    st_autorefresh(interval=5000)
    user=st.session_state.user
    with st.sidebar:
        st.header(user['role']); st.info(user['name'])
        if st.button("Logout"): logout()

    if user['role']=="Patient":
        t1,t2,t3=st.tabs(["Book","My Bookings","Profile"])
        with t1:
             p1,p2=st.tabs(["AI","Browse"])
             with p1:
                 sy=st.text_area("Symp")
                 if st.button("Find"): st.session_state.pat_search=http.post(f"{API_URL}/analyze/doctors",json={"description":sy}).json(); st.session_state['sy']=sy
                 if st.session_state.pat_search:
                     r=st.session_state.pat_search; st.success(r['specialty']); dm={d['name']:d['id'] for d in r['doctors']}; sd=st.selectbox("Doc", list(dm.keys()))
                     if sd:
                         did=dm[sd]; dt=st.date_input("Dt",datetime.today()).strftime("%Y-%m-%d"); sl=http.get(f"{API_URL}/calendar/slots",params={"doctor_id":did,"date":dt}).json(); c=st.columns(4)
                         for i, ob in enumerate(get_slots(dt)):
                             t=ob['time']; inf=sl.get(t)
                             with c[i%4]:
                                 if ob['is_past']: st.markdown(f"<div class='slot-card status-past'>{t}<br>Past</div>",unsafe_allow_html=True)
                                 elif not inf:
                                     st.markdown(f"<div class='slot-card status-open'>{t}<br>Open</div>",unsafe_allow_html=True)
                                     if st.button("Bk",key=f"b{t}"): http.post(f"{API_URL}/calendar/book",json={"patient_id":user['id'],"doctor_id":did,"date":dt,"time":t,"symptoms":st.session_state['sy']}); st.rerun()
                                 else: 
                                     lbl="My Req" if inf.get('patient_id')==user['id'] and inf['status']=='PENDING' else "Busy"
                                     clr="status-pending" if lbl=="My Req" else "status-blocked"
                                     st.markdown(f"<div class='slot-card {clr}'>{lbl}</div>",unsafe_allow_html=True)
        
        with t2:
             # Get all my history
             try:
                 rp=http.post(f"{API_URL}/reports/advanced",json={"start_date":"2020-01-01","patient_name":user['name']}).json()
                 act=[x for x in rp if x['Status'] in ['PENDING','CONFIRMED']]; hst=[x for x in rp if x['Status']=='COMPLETED']
                 
                 st.write("##### Active")
                 if act:
                     for a in act:
                         with st.expander(f"{a['Date']} @ {a['Time']} (Dr. {a['Doctor']})"):
                             ns=st.text_input("Edit Symp", key=f"s{a['ID']}"); 
                             if st.button("Save", key=f"sv{a['ID']}"): http.post(f"{API_URL}/calendar/edit_symptom",json={"appt_id":a['ID'],"new_symptoms":ns}); st.rerun()
                             
                             rs=st.text_input("Cancel Rsn", key=f"r{a['ID']}")
                             if st.button("❌ Cancel", key=f"c{a['ID']}"):
                                 res=http.post(f"{API_URL}/calendar/action", json={"appt_id":a['ID'],"action":"cancel","reason":rs})
                                 if res.status_code==200: st.success("Cancelled"); st.rerun()
                                 else: st.error(res.json()['detail'])
                 else: st.caption("No active bookings.")

                 st.write("##### History")
                 if hst:
                     df=pd.DataFrame(hst); st.dataframe(df[['Date','Doctor','Fee','Diagnosis']], use_container_width=True)
                     for idx,r in df.iterrows():
                         if st.button(f"🧾 Receipt {r['Date']}",key=f"pd{idx}"):
                             b=http.get(f"{API_URL}/appointment/{r['ID']}/pdf").content; st.download_button("Save PDF",b,f"R.pdf","application/pdf")
             except:pass
        
        with t3:
            with st.form("p"):
                n=st.text_input("Nm",user['name']); w=st.text_input("PW",type="password")
                if st.form_submit_button("Upd"): http.put(f"{API_URL}/auth/update_profile",json={"role":"Patient","user_id":user['id'],"name":n,"email":user['email'],"password":w}); logout()

    elif user['role']=="Doctor":
        t1,t2,t3=st.tabs(["Calendar","AI Search","Profile"])
        with t3:
            with st.form("dp"):
                n=st.text_input("Nm",user['name']); f=st.number_input("Fee",float(user.get('fee',100))); w=st.text_input("PW",type="password")
                if st.form_submit_button("Upd"): http.put(f"{API_URL}/auth/update_profile",json={"role":"Doctor","user_id":user['id'],"name":n,"email":user['email'],"fee":f,"password":w}); logout()
        with t1:
            dt=st.date_input("Date",datetime.today()).strftime("%Y-%m-%d"); sl=http.get(f"{API_URL}/calendar/slots",params={"doctor_id":user['id'],"date":dt}).json(); c=st.columns(4)
            for i,ob in enumerate(get_slots(dt)):
                t=ob['time']; inf=sl.get(t)
                with c[i%4]:
                    if ob['is_past']: st.markdown(f"<div class='slot-card status-blocked'>{t}<br>Past</div>",unsafe_allow_html=True)
                    elif not inf:
                        st.markdown(f"<div class='slot-card status-open'>{t}</div>",unsafe_allow_html=True)
                        if st.button("Block",key=t): http.post(f"{API_URL}/calendar/block",params={"doc_id":user['id'],"date":dt,"time":t}); st.rerun()
                    elif inf['status']=='PENDING':
                        st.markdown(f"<div class='slot-card status-pending'>{t}<br>Req</div>",unsafe_allow_html=True)
                        with st.popover("Act"):
                            st.write(inf['symptom']); rs=st.text_input("Reason", key=f"dr{t}")
                            if st.button("Accept",key=f"y{t}"): http.post(f"{API_URL}/calendar/action",json={"appt_id":inf['id'],"action":"approve"}); st.rerun()
                            if st.button("Reject",key=f"n{t}"): http.post(f"{API_URL}/calendar/action",json={"appt_id":inf['id'],"action":"cancel","reason":rs}); st.rerun()
                    elif inf['status']=='CONFIRMED':
                        st.markdown(f"<div class='slot-card status-confirmed'>{t}<br>Pat</div>",unsafe_allow_html=True)
                        with st.popover("Consult"):
                            with st.form(f"f{t}"):
                                d=st.text_input("Diag"); n=st.text_area("Notes"); m=st.text_area("Rx Meds"); f=st.number_input("Fee",value=user.get('fee',100.0))
                                if st.form_submit_button("Finish"): http.post(f"{API_URL}/doctor/consult",json={"appt_id":inf['id'],"diagnosis":d,"notes":n,"medications":m,"charges":f}); st.rerun()
                            cr=st.text_input("Cxl Rsn",key=f"xr{t}")
                            if st.button("Cancel Appt",key=f"xc{t}"): http.post(f"{API_URL}/calendar/action",json={"appt_id":inf['id'],"action":"cancel","reason":cr}); st.rerun()
                    elif inf['status']=='COMPLETED':
                        st.markdown(f"<div class='slot-card status-completed'>{t}<br>Done</div>",unsafe_allow_html=True)
                        if st.button("📄",key=f"dp{t}"): 
                             b=http.get(f"{API_URL}/appointment/{inf['id']}/pdf").content; st.download_button("PDF",b,f"R{t}.pdf")
                    elif inf['status']=='BLOCKED':
                        st.markdown(f"<div class='slot-card status-blocked'>{t}<br>Blk</div>",unsafe_allow_html=True)
                        if st.button("Unblk",key=f"u{t}"): http.post(f"{API_URL}/calendar/action",json={"appt_id":inf['id'],"action":"cancel"}); st.rerun()

        with t2:
             q=st.text_input("Query History"); 
             if st.button("Search"): st.session_state.doc_ai_res=http.post(f"{API_URL}/knowledge/query",json={"description":q}).json()
             if st.button("Clr"): st.session_state.doc_ai_res=None; st.rerun()
             if st.session_state.doc_ai_res:
                 for x in st.session_state.doc_ai_res: st.info(f"{x['diagnosis']} | Rx: {x['medication']}")

    elif user['role']=="Admin":
        a1,a2,a3,a4=st.tabs(["Report","User","Mast","Prof"])
        with a1:
             c1,c2,c3,c4=st.columns(4); d1=c1.date_input("S",None); d2=c2.date_input("E",None)
             alld=http.get(f"{API_URL}/doctors/all").json(); alls=http.get(f"{API_URL}/specialties/all").json()
             sd=c3.selectbox("Dr",["All"]+[x['name'] for x in alld]); ss=c4.selectbox("Sp",["All"]+[x['name'] for x in alls])
             did=next((x['id'] for x in alld if x['name']==sd),None) if sd!="All" else None
             sid=next((x['id'] for x in alls if x['name']==ss),None) if ss!="All" else None
             if st.button("Gen"):
                 st.session_state.admin_report_data = http.post(f"{API_URL}/reports/advanced",json={"start_date":str(d1) if d1 else None,"end_date":str(d2) if d2 else None,"doctor_id":did,"specialty_id":sid}).json()
             if st.session_state.admin_report_data:
                 df=pd.DataFrame(st.session_state.admin_report_data); st.dataframe(df, use_container_width=True); st.download_button("CSV",df.to_csv().encode(),"r.csv")
        with a2:
             rl=st.radio("Role",["Patient","Doctor","Admin"],horizontal=True)
             us=http.get(f"{API_URL}/users/all",params={"role":rl}).json()
             if us: 
                 st.dataframe(pd.DataFrame(us))
                 n_l=[f"{u['name']} (ID:{u['id']})" for u in us]
                 sel=st.selectbox("User",n_l)
                 if sel:
                     uid=int(sel.split("ID:")[1].replace(")",""))
                     c_a,c_b=st.columns(2)
                     if c_a.button("Load"): st.session_state.edit_u=http.get(f"{API_URL}/users/get_one",params={"role":rl,"id":uid}).json()
                     if c_b.button("Delete"): http.delete(f"{API_URL}/admin/delete_user",params={"role":rl,"id":uid}); st.success("Del"); st.rerun()
                     if st.session_state.edit_u:
                         u=st.session_state.edit_u
                         with st.form("eu"):
                             n=st.text_input("N",u['name']); e=st.text_input("E",u['email']); p=st.text_input("P",u.get('phone','')); w=st.text_input("Set PW",type="password")
                             if st.form_submit_button("Save"): http.put(f"{API_URL}/admin/update_user",json={"target_role":rl,"target_id":uid,"name":n,"email":e,"phone":p,"password":w}); st.success("OK"); st.rerun()
                 
                 with st.expander("Add User"):
                      ar=st.selectbox("Role",["Patient","Doctor","Admin"]); an=st.text_input("Nm"); ae=st.text_input("Em"); aph=st.text_input("Ph"); apw=st.text_input("Pw")
                      aex=""; afe=0.0
                      if ar=="Doctor": afe=st.number_input("F",100.0); sp=http.get(f"{API_URL}/specialties/all").json(); mp={x['name']:x['id'] for x in sp}; k=st.selectbox("S",list(mp.keys())); aex=str(mp[k])
                      if st.button("Add"): http.post(f"{API_URL}/auth/register",json={"role":ar,"name":an,"email":ae,"password":ap,"phone":aph,"extra_field":aex,"fee":afe}); st.rerun()

        with a3:
            c1,c2=st.columns(2)
            sp=http.get(f"{API_URL}/specialties/all").json()
            with c1:
                st.write("Specs"); st.dataframe(sp)
                n=st.text_input("New Sp"); 
                if st.button("Add S"): http.post(f"{API_URL}/master/specialty",params={"action":"add","name":n}); st.rerun()
                tg=st.selectbox("Del S",[x['name'] for x in sp] if sp else []); 
                if st.button("Del S"): 
                    i=next(x['id'] for x in sp if x['name']==tg); r=http.post(f"{API_URL}/master/specialty",params={"action":"delete","name":"","id":i}); 
                    if r.status_code!=200: st.error("Linked"); 
                    else: st.rerun()
            with c2:
                sy=http.get(f"{API_URL}/symptoms/all").json(); st.write("Symptoms"); st.dataframe(sy)
                l=st.selectbox("Link",[x['name'] for x in sp] if sp else []); kw=st.text_input("Kw")
                if st.button("Add Sy"):
                    i=next(x['id'] for x in sp if x['name']==l); http.post(f"{API_URL}/master/symptom",params={"action":"add","keyword":kw,"spec_id":i}); st.rerun()
                ds=st.selectbox("Del Sy",[x['keyword'] for x in sy] if sy else [])
                if st.button("Del Sy"):
                    j=next(x['id'] for x in sy if x['keyword']==ds); http.post(f"{API_URL}/master/symptom",params={"action":"delete","keyword":"","id":j}); st.rerun()
        
        with a4:
            with st.form("ap"):
                 n=st.text_input("N",user['name']); e=st.text_input("E",user['email']); w=st.text_input("Pw",type="password")
                 if st.form_submit_button("Up"): http.put(f"{API_URL}/auth/update_profile",json={"role":"Admin","user_id":user['id'],"name":n,"email":e,"password":w}); logout()