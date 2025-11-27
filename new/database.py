from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from passlib.context import CryptContext 

DATABASE_URL = "sqlite:///./medmatch.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    dob = Column(String)
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
    cancellation_reason = Column(String, nullable=True)
    diagnosis = Column(String, nullable=True)
    doctor_comments = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    charges = Column(Float, nullable=True)
    receipt_number = Column(String, nullable=True)
    
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")

class KnowledgeEntry(Base):
    __tablename__ = "knowledge_base"
    id = Column(Integer, primary_key=True)
    symptom_text = Column(Text)
    diagnosis = Column(String)
    treatment_plan = Column(Text)
    medication_plan = Column(Text, nullable=True)
    doctor_name = Column(String)

class AdhocReceipt(Base):
    __tablename__ = "adhoc_receipts"
    id = Column(Integer, primary_key=True)
    receipt_number = Column(String, unique=True, index=True)
    recipient_name = Column(String)
    description = Column(String)
    amount = Column(Float)
    created_at = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(Specialty).first():
        s1 = Specialty(name="Cardiology"); db.add(s1); db.commit(); db.refresh(s1)
        db.add(Symptom(keyword="chest", specialty_id=s1.id))
        pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
        db.add(Admin(name="System Admin", email="admin@med.com", password_hash=pwd_ctx.hash("12345")))
        db.add(Doctor(name="Dr. House", email="house@med.com", password_hash=pwd_ctx.hash("12345"), qualification="MD", specialty_id=1, default_fee=150.0, phone_number="555-0101"))
        db.add(Patient(name="John Doe", email="john@test.com", password_hash=pwd_ctx.hash("12345"), age=30, dob="1995-01-01", phone="555-0202"))
        db.commit()
    db.close()