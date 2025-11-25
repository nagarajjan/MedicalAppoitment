from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import database
from database import Doctor, Patient, Appointment, Admin, SessionLocal, Specialty, Symptom, KnowledgeEntry
from security_utils import get_password_hash, verify_password, validate_password_complexity
from logic_engine import SymptomRouter
from knowledge_engine import MedicalKnowledgeSystem

app = FastAPI()
database.init_db()
router = SymptomRouter()
knowledge_sys = MedicalKnowledgeSystem()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- MODELS ---
class RegisterModel(BaseModel):
    role: str; name: str; email: EmailStr; password: str; extra_field: str = ""; fee: float = 0.0; phone: str = ""; dob: str = ""
class LoginModel(BaseModel):
    role: str; email: str; password: str
class UpdateProfileModel(BaseModel):
    role: str; user_id: int; name: str; email: str; phone: str; password: str = ""; dob: str = ""; fee: float = 0.0; qualification: str = ""
class AdminUpdateUserModel(BaseModel):
    target_role: str; target_id: int; name: str; email: str; phone: str; password: str = ""
class ReportFilter(BaseModel):
    start_date: Optional[str] = None; end_date: Optional[str] = None; doctor_id: Optional[int] = None; specialty_id: Optional[int] = None
class SymptomInput(BaseModel): description: str
class BookSlotModel(BaseModel): patient_id: int; doctor_id: int; date: str; time: str; symptoms: str
class ConsultModel(BaseModel): appt_id: int; diagnosis: str; notes: str; charges: float

# --- AUTH ---
@app.post("/auth/register")
def register(reg: RegisterModel, db: Session = Depends(get_db)):
    if not validate_password_complexity(reg.password): raise HTTPException(400, "Password weak (8-10 chars, special)")
    hashed = get_password_hash(reg.password)
    
    if reg.role == "Patient":
        if db.query(Patient).filter(Patient.email==reg.email).first(): raise HTTPException(400, "Email exists")
        age_val = int(reg.extra_field) if reg.extra_field.isdigit() else 0
        db.add(Patient(name=reg.name, email=reg.email, password_hash=hashed, age=age_val, phone=reg.phone, dob=reg.dob))
    elif reg.role == "Doctor":
        if db.query(Doctor).filter(Doctor.email==reg.email).first(): raise HTTPException(400, "Email exists")
        spec_id = int(reg.extra_field) if reg.extra_field.isdigit() else 1
        db.add(Doctor(name=reg.name, email=reg.email, password_hash=hashed, specialty_id=spec_id, default_fee=reg.fee, phone_number=reg.phone, qualification="MD"))
    elif reg.role == "Admin":
        if db.query(Admin).filter(Admin.email==reg.email).first(): raise HTTPException(400, "Email exists")
        db.add(Admin(name=reg.name, email=reg.email, password_hash=hashed))
    db.commit(); return {"msg": "Registered"}

@app.post("/auth/login")
def login(creds: LoginModel, db: Session = Depends(get_db)):
    user = None
    if creds.role == "Patient": user = db.query(Patient).filter(Patient.email==creds.email).first()
    elif creds.role == "Doctor": user = db.query(Doctor).filter(Doctor.email==creds.email).first()
    elif creds.role == "Admin": user = db.query(Admin).filter(Admin.email==creds.email).first()
    
    if not user or not verify_password(creds.password, user.password_hash): raise HTTPException(401, "Invalid")
    res = {"id": user.id, "name": user.name, "role": creds.role, "email": user.email}
    if creds.role == "Patient": res.update({"phone": user.phone, "dob": user.dob})
    if creds.role == "Doctor": res.update({"phone": user.phone_number, "fee": user.default_fee, "qual": user.qualification})
    return res

@app.put("/auth/update_profile")
def update_profile(data: UpdateProfileModel, db: Session = Depends(get_db)):
    user = None
    if data.role == "Patient": user = db.query(Patient).get(data.user_id)
    elif data.role == "Doctor": user = db.query(Doctor).get(data.user_id)
    elif data.role == "Admin": user = db.query(Admin).get(data.user_id)
    if not user: raise HTTPException(404, "Not found")
    
    user.name = data.name; user.email = data.email
    if data.password:
        if not validate_password_complexity(data.password): raise HTTPException(400, "Password weak")
        user.password_hash = get_password_hash(data.password)
    
    if data.role == "Patient": user.phone = data.phone; user.dob = data.dob
    elif data.role == "Doctor": user.phone_number = data.phone; user.default_fee = data.fee; user.qualification = data.qualification
    db.commit(); return {"msg": "Updated"}

@app.put("/admin/update_user")
def admin_update_user(data: AdminUpdateUserModel, db: Session = Depends(get_db)):
    user = None
    if data.target_role == "Patient": user = db.query(Patient).get(data.target_id)
    elif data.target_role == "Doctor": user = db.query(Doctor).get(data.target_id)
    elif data.target_role == "Admin": user = db.query(Admin).get(data.target_id)
    
    if not user: raise HTTPException(404, "Not found")
    user.name = data.name; user.email = data.email
    if data.target_role != "Admin":
        if data.target_role == "Patient": user.phone = data.phone
        elif data.target_role == "Doctor": user.phone_number = data.phone
    if data.password: user.password_hash = get_password_hash(data.password)
    db.commit(); return {"msg": "Updated"}

@app.delete("/admin/delete_user")
def delete_user(role: str, id: int, db: Session = Depends(get_db)):
    record = None
    if role == "Patient": record = db.query(Patient).get(id)
    elif role == "Doctor": record = db.query(Doctor).get(id)
    elif role == "Admin": record = db.query(Admin).get(id)
    if not record: raise HTTPException(404, "Not found")
    try: db.delete(record); db.commit()
    except: raise HTTPException(400, "History exists")
    return {"msg": "Deleted"}

@app.post("/master/specialty")
def manage_specialty(action: str, name: str, id: int = 0, db: Session = Depends(get_db)):
    if action == "add": db.add(Specialty(name=name))
    elif action == "update": 
        s = db.query(Specialty).get(id); 
        if s: s.name = name
    elif action == "delete": 
        s = db.query(Specialty).get(id); 
        if s: db.delete(s)
    db.commit(); return {"msg": "OK"}

@app.post("/master/symptom")
def manage_symptom(action: str, keyword: str, id: int = 0, spec_id: int = 0, db: Session = Depends(get_db)):
    if action == "add": db.add(Symptom(keyword=keyword, specialty_id=spec_id))
    elif action == "update":
        s = db.query(Symptom).get(id); 
        if s: s.keyword = keyword
    elif action == "delete":
        s = db.query(Symptom).get(id); 
        if s: db.delete(s)
    db.commit(); return {"msg": "OK"}

# --- REPORTING (FIXED) ---
@app.post("/reports/advanced")
def get_advanced_reports(f: ReportFilter, db: Session = Depends(get_db)):
    # FIXED QUERY: Explicit joins to resolve ambiguity
    query = db.query(Appointment, Doctor, Patient, Specialty)\
        .select_from(Appointment)\
        .join(Doctor, Appointment.doctor_id == Doctor.id)\
        .outerjoin(Patient, Appointment.patient_id == Patient.id)\
        .outerjoin(Specialty, Doctor.specialty_id == Specialty.id)
        
    if f.doctor_id: query = query.filter(Appointment.doctor_id == f.doctor_id)
    if f.specialty_id: query = query.filter(Doctor.specialty_id == f.specialty_id)
    if f.start_date: query = query.filter(Appointment.appt_date >= f.start_date)
    if f.end_date: query = query.filter(Appointment.appt_date <= f.end_date)
    
    try:
        res = query.all()
        data = []
        for a, d, p, s in res:
            pname = p.name if p else "N/A (Blocked)"
            sname = s.name if s else "Unknown"
            data.append({
                "Date": a.appt_date, "Time": a.appt_time, 
                "Doctor": d.name, "Specialty": sname, 
                "Patient": pname, "Status": a.status, "Fee": a.charges or 0.0
            })
        return data
    except Exception as e:
        print(f"Report Error: {e}")
        raise HTTPException(500, f"Database Query Failed: {str(e)}")

# --- APP LOGIC ---
@app.post("/analyze/doctors")
def find_doctors(input: SymptomInput, db: Session = Depends(get_db)):
    spec_id = router.predict_specialty(input.description, db)
    if spec_id:
        s = db.query(Specialty).get(spec_id)
        docs = db.query(Doctor).filter(Doctor.specialty_id == spec_id).all()
        return {"specialty": s.name, "doctors": [{"id": d.id, "name": d.name, "specialty_id": d.specialty_id, "qualification": d.qualification} for d in docs]}
    return {"specialty": "General", "doctors": []}

@app.get("/calendar/slots")
def get_slots(doctor_id: int, date: str, db: Session = Depends(get_db)):
    appts = db.query(Appointment).filter(Appointment.doctor_id==doctor_id, Appointment.appt_date==date).all()
    res = {}
    for a in appts:
        pname = a.patient.name if a.patient else "Blocked"
        res[a.appt_time] = {"status": a.status, "id": a.id, "patient_id": a.patient_id, "patient_name": pname, "symptom": a.symptoms}
    return res

@app.post("/calendar/book")
def book_slot(data: BookSlotModel, db: Session = Depends(get_db)):
    if db.query(Appointment).filter(Appointment.doctor_id==data.doctor_id, Appointment.appt_date==data.date, Appointment.appt_time==data.time).first(): raise HTTPException(400, "Taken")
    db.add(Appointment(patient_id=data.patient_id, doctor_id=data.doctor_id, appt_date=data.date, appt_time=data.time, symptoms=data.symptoms))
    db.commit(); return {"msg": "Booked"}

@app.post("/calendar/action")
def slot_action(appt_id: int, action: str, db: Session = Depends(get_db)):
    a = db.query(Appointment).get(appt_id)
    if not a: raise HTTPException(404, "Not found")
    if action == "approve": a.status = "CONFIRMED"
    elif action == "cancel": db.delete(a)
    db.commit(); return {"msg": "Done"}

@app.post("/calendar/block")
def block_slot(doc_id: int, date: str, time: str, db: Session = Depends(get_db)):
    db.add(Appointment(patient_id=None, doctor_id=doc_id, appt_date=date, appt_time=time, status="BLOCKED", symptoms="Doctor Blocked"))
    db.commit()
    return {"msg": "Blocked"}

@app.post("/doctor/consult")
def consult(data: ConsultModel, db: Session = Depends(get_db)):
    a = db.query(Appointment).get(data.appt_id)
    a.status="COMPLETED"; a.diagnosis=data.diagnosis; a.doctor_comments=data.notes; a.charges=data.charges
    d = db.query(Doctor).get(a.doctor_id)
    db.add(KnowledgeEntry(symptom_text=a.symptoms, diagnosis=data.diagnosis, treatment_plan=data.notes, doctor_name=d.name))
    db.commit(); return {"msg": "Saved"}

@app.post("/knowledge/query")
def query_kb(input: SymptomInput, db: Session = Depends(get_db)):
    matches = knowledge_sys.search_similar_cases(input.description, db)
    return [{"diagnosis": m['data'].diagnosis, "treatment": m['data'].treatment_plan, "doc": m['data'].doctor_name, "score": m['score']} for m in matches]

@app.get("/doctors/all")
def get_all_docs(db: Session = Depends(get_db)): 
    return [{"id": d.id, "name": d.name, "specialty_id": d.specialty_id, "qualification": d.qualification} for d in db.query(Doctor).all()]

@app.get("/specialties/all")
def get_specs(db: Session = Depends(get_db)): return [{"id": s.id, "name": s.name} for s in db.query(Specialty).all()]
@app.get("/symptoms/all")
def get_symps(db: Session = Depends(get_db)): return [{"id": s.id, "keyword": s.keyword, "spec_id": s.specialty_id} for s in db.query(Symptom).all()]
@app.get("/users/all")
def get_users(role: str, db: Session = Depends(get_db)):
    if role == "Patient": return db.query(Patient).all()
    if role == "Doctor": return db.query(Doctor).all()
    if role == "Admin": return db.query(Admin).all()
    return []
@app.get("/reports/all")
def get_reports(db: Session = Depends(get_db)):
    res = db.query(Appointment, Doctor.name.label("d"), Patient.name.label("p")).join(Doctor).outerjoin(Patient).all()
    data = []
    for a, d, p in res:
        pname = p.name if p else "Blocked"
        data.append({"Date": a.appt_date, "Time": a.appt_time, "Doctor": d, "Patient": pname, "Status": a.status, "Diagnosis": a.diagnosis or "", "Charges": a.charges or 0.0})
    return data