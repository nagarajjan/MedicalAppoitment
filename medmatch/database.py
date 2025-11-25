from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from passlib.context import CryptContext 

DATABASE_URL = "sqlite:///./medmatch.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- ENTITIES ---
class Specialty(Base):
    __tablename__ = "specialties"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    doctors = relationship("Doctor", back_populates="specialty_rel")
    symptoms = relationship("Symptom", back_populates="specialty_rel")

class Symptom(Base):
    __tablename__ = "symptoms"
    id = Column(Integer, primary_key=True)
    keyword = Column(String)
    specialty_id = Column(Integer, ForeignKey("specialties.id"))
    specialty_rel = relationship("Specialty", back_populates="symptoms")

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    qualification = Column(String)
    phone_number = Column(String)
    specialty_id = Column(Integer, ForeignKey("specialties.id"))
    default_fee = Column(Float, default=100.0)
    
    specialty_rel = relationship("Specialty", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    age = Column(Integer)
    dob = Column(String) # YYYY-MM-DD
    phone = Column(String)
    appointments = relationship("Appointment", back_populates="patient")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    
    appt_date = Column(String) 
    appt_time = Column(String) 
    symptoms = Column(String, nullable=True)
    status = Column(String, default="PENDING") 
    
    # Consultation Fields
    diagnosis = Column(String, nullable=True)
    doctor_comments = Column(Text, nullable=True)
    charges = Column(Float, nullable=True)
    
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")

class KnowledgeEntry(Base):
    __tablename__ = "knowledge_base"
    id = Column(Integer, primary_key=True)
    symptom_text = Column(Text)
    diagnosis = Column(String)
    treatment_plan = Column(Text)
    doctor_name = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    if not db.query(Specialty).first():
        # Seed Specialties
        specs = {
            "Cardiology": ["chest", "heart", "breath", "angina"],
            "Dermatology": ["skin", "rash", "acne", "mole"],
            "Podiatry": ["foot", "heel", "toe", "ankle"],
            "Gastroenterology": ["stomach", "gut", "acid", "bloating"]
        }
        for name, keywords in specs.items():
            spec = Specialty(name=name)
            db.add(spec)
            db.commit(); db.refresh(spec)
            for k in keywords: db.add(Symptom(keyword=k, specialty_id=spec.id))
        
        # Seed Admin & Doctor using local hasher to avoid circular imports
        pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
        
        db.add(Admin(name="System Admin", email="admin@med.com", password_hash=pwd_ctx.hash("Admin123@")))
        db.add(Doctor(name="Dr. House", email="house@med.com", password_hash=pwd_ctx.hash("Doc1234@"), qualification="MD", specialty_id=1, default_fee=150.0, phone_number="555-0101"))
        db.add(Patient(name="John Doe", email="john@test.com", password_hash=pwd_ctx.hash("Pass123@"), age=30, dob="1995-01-01", phone="555-0202"))
        
        db.commit()
    db.close()