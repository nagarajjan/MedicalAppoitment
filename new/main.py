from fastapi import FastAPI, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import database
from database import Doctor, Patient, Appointment, Admin, SessionLocal, Specialty, Symptom, KnowledgeEntry, AdhocReceipt
from security_utils import get_password_hash, verify_password, validate_password_complexity
from logic_engine import SymptomRouter
from knowledge_engine import MedicalKnowledgeSystem
from pdf_generator import generate_medical_report, generate_adhoc_receipt
from datetime import datetime, timedelta
import json

app = FastAPI()
database.init_db()
router = SymptomRouter()
knowledge_sys = MedicalKnowledgeSystem()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- DTOs ---
class RegisterModel(BaseModel):
    role: str; name: str; email: EmailStr; password: str; extra_field: str = ""; fee: float = 0.0; phone: str = ""; dob: str = ""
class LoginModel(BaseModel):
    role: str; email: str; password: str
class UpdateProfileModel(BaseModel):
    role: str; user_id: int; name: str; email: str; phone: str; password: str = ""; dob: str = ""; fee: float = 0.0; qualification: str = ""
class AdminUpdateUserModel(BaseModel):
    target_role: str; target_id: int; name: str; email: str; phone: str; password: str = ""
class ReportFilter(BaseModel):
    start_date: Optional[str] = None; end_date: Optional[str] = None; doctor_id: Optional[int] = None; specialty_id: Optional[int] = None; patient_name: Optional[str] = None
class SymptomInput(BaseModel): description: str
class BookSlotModel(BaseModel): patient_id: int; doctor_id: int; date: str; time: str; symptoms: str
class ConsultModel(BaseModel): appt_id: int; diagnosis: str; notes: str; medications: str; charges: float
class ActionModel(BaseModel): appt_id: int; action: str; reason: str = ""
class AdhocModel(BaseModel): recipient: str; description: str; amount: float
class EditBookingModel(BaseModel): appt_id: int; new_symptoms: str

# --- AUTH ---
@app.post("/auth/register")
def register(reg: RegisterModel, db: Session = Depends(get_db)):
    if not validate_password_complexity(reg.password): raise HTTPException(400, "Password weak")
    hashed = get_password_hash(reg.password)
    
    if reg.role == "Patient":
        if db.query(Patient).filter(Patient.email==reg.email).first(): raise HTTPException(400, "Email used")
        db.add(Patient(name=reg.name, email=reg.email, password_hash=hashed, age=int(reg.extra_field) if reg.extra_field.isdigit() else 0, phone=reg.phone, dob=reg.dob))
    elif reg.role == "Doctor":
        if db.query(Doctor).filter(Doctor.email==reg.email).first(): raise HTTPException(400, "Email used")
        sid = int(reg.extra_field) if reg.extra_field.isdigit() else 1
        db.add(Doctor(name=reg.name, email=reg.email, password_hash=hashed, specialty_id=sid, default_fee=reg.fee, phone_number=reg.phone, qualification="MD"))
    elif reg.role == "Admin":
        if db.query(Admin).filter(Admin.email==reg.email).first(): raise HTTPException(400, "Email used")
        db.add(Admin(name=reg.name, email=reg.email, password_hash=hashed))
    db.commit(); return {"msg": "OK"}

@app.post("/auth/login")
def login(creds: LoginModel, db: Session = Depends(get_db)):
    user = None
    if creds.role=="Patient": user=db.query(Patient).filter(Patient.email==creds.email).first()
    elif creds.role=="Doctor": user=db.query(Doctor).filter(Doctor.email==creds.email).first()
    elif creds.role=="Admin": user=db.query(Admin).filter(Admin.email==creds.email).first()
    
    if not user or not verify_password(creds.password, user.password_hash): raise HTTPException(401, "Invalid Credentials")
    
    res={"id":user.id, "name":user.name, "role":creds.role, "email":user.email}
    if creds.role=="Patient": res.update({"phone":user.phone, "dob":user.dob})
    if creds.role=="Doctor": res.update({"phone":user.phone_number, "fee":user.default_fee, "qual":user.qualification})
    return res

@app.put("/auth/update_profile")
def update_profile(d: UpdateProfileModel, db: Session = Depends(get_db)):
    u = None
    if d.role == "Patient": u = db.query(Patient).get(d.user_id)
    elif d.role == "Doctor": u = db.query(Doctor).get(d.user_id)
    elif d.role == "Admin": u = db.query(Admin).get(d.user_id)
    if not u: raise HTTPException(404)
    u.name = d.name; u.email = d.email
    if d.password: u.password_hash = get_password_hash(d.password)
    if d.role == "Patient": u.phone=d.phone; u.dob=d.dob
    elif d.role == "Doctor": u.phone_number=d.phone; u.default_fee=d.fee; u.qualification=d.qualification
    db.commit(); return {"msg": "Updated"}

# --- ADMIN ---
@app.get("/users/get_one")
def get_one(role: str, id: int, db: Session = Depends(get_db)):
    u = None
    if role=="Patient": u=db.query(Patient).get(id)
    elif role=="Doctor": u=db.query(Doctor).get(id)
    elif role=="Admin": u=db.query(Admin).get(id)
    if not u: raise HTTPException(404, "User Not Found")
    res = {"id":u.id, "name":u.name, "email":u.email}
    if role!="Admin": res['phone'] = u.phone if role=="Patient" else u.phone_number
    return res

@app.put("/admin/update_user")
def admin_upd(d: AdminUpdateUserModel, db: Session = Depends(get_db)):
    u=None
    if d.target_role=="Patient": u=db.query(Patient).get(d.target_id)
    elif d.target_role=="Doctor": u=db.query(Doctor).get(d.target_id)
    elif d.target_role=="Admin": u=db.query(Admin).get(d.target_id)
    if not u: raise HTTPException(404)
    u.name=d.name; u.email=d.email
    if d.password: u.password_hash=get_password_hash(d.password)
    if d.target_role=="Patient": u.phone=d.phone
    elif d.target_role=="Doctor": u.phone_number=d.phone
    db.commit(); return {"msg":"OK"}

@app.delete("/admin/delete_user")
def adm_del(role: str, id: int, db: Session = Depends(get_db)):
    r=None
    if role=="Patient": r=db.query(Patient).get(id)
    elif role=="Doctor": r=db.query(Doctor).get(id)
    elif role=="Admin": r=db.query(Admin).get(id)
    if not r: raise HTTPException(404)
    try: db.delete(r); db.commit()
    except: raise HTTPException(400, "Linked Data Conflict")
    return {"msg":"Deleted"}

# --- MASTER DATA ---
@app.post("/master/specialty")
def m_sp(action: str, name: str, id: int=0, db: Session=Depends(get_db)):
    if action=="add": db.add(Specialty(name=name))
    elif action=="update": s=db.query(Specialty).get(id); s.name=name if s else None
    elif action=="delete": s=db.query(Specialty).get(id); db.delete(s) if s else None
    db.commit(); return {"msg":"OK"}

@app.post("/master/symptom")
def m_sy(action: str, keyword: str, id: int=0, spec_id: int=0, db: Session=Depends(get_db)):
    if action=="add": db.add(Symptom(keyword=keyword, specialty_id=spec_id))
    elif action=="update": s=db.query(Symptom).get(id); s.keyword=keyword if s else None
    elif action=="delete": s=db.query(Symptom).get(id); db.delete(s) if s else None
    db.commit(); return {"msg":"OK"}

# --- CALENDAR & BOOKING ---
@app.post("/analyze/doctors")
def find(i: SymptomInput, db: Session=Depends(get_db)):
    sid = router.predict_specialty(i.description, db)
    if sid:
        s = db.query(Specialty).get(sid)
        docs = db.query(Doctor).filter(Doctor.specialty_id==sid).all()
        return {"specialty": s.name, "doctors": [{"id": d.id, "name": d.name} for d in docs]}
    return {"specialty":"General", "doctors":[]}

@app.get("/calendar/slots")
def slots(doctor_id: int, date: str, db: Session=Depends(get_db)):
    appts = db.query(Appointment).filter(Appointment.doctor_id==doctor_id, Appointment.appt_date==date).all()
    res = {}
    for a in appts:
        pname = a.patient.name if a.patient else "Blocked"
        res[a.appt_time] = {
            "status": a.status, "id": a.id, "patient_id": a.patient_id, 
            "patient_name": pname, "symptom": a.symptoms, "cancellation_reason": a.cancellation_reason
        }
    return res

@app.post("/calendar/book")
def book(d: BookSlotModel, db: Session=Depends(get_db)):
    # 1. Check Doc Availability
    if db.query(Appointment).filter(Appointment.doctor_id==d.doctor_id, Appointment.appt_date==d.date, Appointment.appt_time==d.time).first(): 
        raise HTTPException(400, "Doctor Busy")
    # 2. Check Patient Availability (No double booking)
    if db.query(Appointment).filter(Appointment.patient_id==d.patient_id, Appointment.appt_date==d.date, Appointment.appt_time==d.time).first():
        raise HTTPException(400, "You have another appointment")
        
    db.add(Appointment(patient_id=d.patient_id, doctor_id=d.doctor_id, appt_date=d.date, appt_time=d.time, symptoms=d.symptoms, status="PENDING"))
    db.commit(); return {"msg":"OK"}

@app.post("/calendar/edit_symptom")
def edit_sym(d: EditBookingModel, db: Session=Depends(get_db)):
    a=db.query(Appointment).get(d.appt_id)
    if a and a.status in ["PENDING", "CONFIRMED"]:
        a.symptoms = d.new_symptoms
        db.commit()
    return {"msg":"Updated"}

@app.post("/calendar/patient_cancel")
def pat_cancel(d: ActionModel, db: Session=Depends(get_db)):
    a=db.query(Appointment).get(d.appt_id)
    if not a: raise HTTPException(404)
    try:
        # 12 Hour check
        dt = datetime.strptime(f"{a.appt_date} {a.appt_time}", "%Y-%m-%d %H:%M")
        if datetime.now() > (dt - timedelta(hours=12)):
             raise HTTPException(400, "Cancellation allowed up to 12h before")
    except: pass
    db.delete(a); db.commit(); return {"msg":"OK"}

@app.post("/calendar/action")
def action(d: ActionModel, db: Session=Depends(get_db)):
    a=db.query(Appointment).get(d.appt_id)
    if not a: raise HTTPException(404)
    if d.action=="approve": a.status="CONFIRMED"
    elif d.action=="cancel": db.delete(a)
    db.commit(); return {"msg":"OK"}

@app.post("/calendar/block")
def block(doc_id: int, date: str, time: str, db: Session=Depends(get_db)):
    db.add(Appointment(patient_id=None, doctor_id=doc_id, appt_date=date, appt_time=time, status="BLOCKED", symptoms="Blocked"))
    db.commit(); return {"msg":"OK"}

@app.post("/doctor/consult")
def consult(d: ConsultModel, db: Session=Depends(get_db)):
    a=db.query(Appointment).get(d.appt_id)
    # Generate Receipt Logic
    dt = datetime.now().strftime("%Y%m%d"); n = f"RCP-{dt}-{a.id:04d}"
    
    a.status="COMPLETED"; a.diagnosis=d.diagnosis; a.doctor_comments=d.notes; 
    a.medications=d.medications; a.charges=d.charges; a.receipt_number=n
    
    doc = db.query(Doctor).get(a.doctor_id)
    db.add(KnowledgeEntry(symptom_text=a.symptoms, diagnosis=d.diagnosis, treatment_plan=d.notes, medication_plan=d.medications, doctor_name=doc.name))
    db.commit(); return {"msg":"Saved"}

# --- AI KNOWLEDGE (UPDATED TO RETURN CONTEXT) ---
@app.post("/knowledge/query")
def k_query(input: SymptomInput, db: Session = Depends(get_db)):
    m = knowledge_sys.search_similar_cases(input.description, db)
    return [{
        "diagnosis": x['data'].diagnosis, 
        "treatment": x['data'].treatment_plan, 
        "medication": x['data'].medication_plan or "None",
        "symptom": x['data'].symptom_text, # Added context
        "doc": x['data'].doctor_name, 
        "score": x['score']
    } for x in m]

# --- REPORTS & PDF ---
@app.post("/reports/advanced")
def get_reports(f: ReportFilter, db: Session=Depends(get_db)):
    q=db.query(Appointment, Doctor, Patient, Specialty).select_from(Appointment).join(Doctor).outerjoin(Patient).outerjoin(Specialty, Doctor.specialty_id==Specialty.id)
    if f.doctor_id: q=q.filter(Appointment.doctor_id==f.doctor_id)
    if f.specialty_id: q=q.filter(Doctor.specialty_id==f.specialty_id)
    if f.start_date: q=q.filter(Appointment.appt_date>=f.start_date)
    if f.patient_name: q=q.filter(Patient.name==f.patient_name)
    try:
        res=q.all(); data=[]
        for a, d, p, s in res:
            pn=p.name if p else "Blocked"; sn=s.name if s else "General"
            data.append({"ID":a.id,"Date":a.appt_date,"Time":a.appt_time,"Doctor":d.name,"Specialty":sn,"Patient":pn,"Status":a.status,"Fee":a.charges or 0.0, "Diagnosis":a.diagnosis or "", "Receipt":a.receipt_number or ""})
        return data
    except: return []

@app.get("/appointment/{aid}/pdf")
def mpdf(aid: int, db: Session=Depends(get_db)):
    a=db.query(Appointment).get(aid)
    rn = a.receipt_number if a.receipt_number else "PENDING"
    pn=a.patient.name if a.patient else "Walk-In"; pa=a.patient.age if a.patient else 0
    b=generate_medical_report(rn, a.doctor.name, a.doctor.qualification, pn, pa, a.appt_date, a.diagnosis, a.doctor_comments, a.medications, a.charges)
    return Response(content=b, media_type="application/pdf")

@app.get("/config/read")
def cr(): 
    try: return json.load(open("clinic_config.json"))
    except: return {}
@app.get("/doctors/all")
def ld(db:Session=Depends(get_db)): return [{"id":d.id,"name":d.name,"specialty_id":d.specialty_id} for d in db.query(Doctor).all()]
@app.get("/specialties/all")
def ls(db:Session=Depends(get_db)): return [{"id":s.id,"name":s.name} for s in db.query(Specialty).all()]
@app.get("/symptoms/all")
def lsy(db:Session=Depends(get_db)): return [{"id":s.id,"keyword":s.keyword} for s in db.query(Symptom).all()]
@app.get("/users/all")
def lu(role: str, db:Session=Depends(get_db)):
    if role=="Patient": return [{"id":x.id, "name":x.name} for x in db.query(Patient).all()]
    elif role=="Doctor": return [{"id":x.id, "name":x.name} for x in db.query(Doctor).all()]
    return [{"id":x.id, "name":x.name} for x in db.query(Admin).all()]
@app.post("/financial/adhoc")
def adhoc(d: AdhocModel, db: Session=Depends(get_db)):
    n = f"RCP-{datetime.now().strftime('%Y%m%d')}-{db.query(AdhocReceipt).count()+1:03d}"
    rec=AdhocReceipt(receipt_number=n, recipient_name=d.recipient, description=d.description, amount=d.amount, created_at=datetime.now().isoformat())
    db.add(rec); db.commit(); return {"id":rec.id}
@app.get("/financial/adhoc/{rid}/pdf")
def apdf(rid: int, db: Session=Depends(get_db)):
    r=db.query(AdhocReceipt).get(rid)
    return Response(content=generate_adhoc_receipt(r.receipt_number, r.created_at[:10], r.recipient_name, r.description, r.amount), media_type="application/pdf")