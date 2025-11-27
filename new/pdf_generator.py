from fpdf import FPDF
import json
import os

CONFIG_FILE = "clinic_config.json"

def get_config():
    try:
        with open(CONFIG_FILE, "r") as f: return json.load(f)
    except:
        return {"platform_title": "MEDMATCH HEALTH", "address": "Clinic Address", "phone": "000"}

class BasePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.conf = get_config()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_fill_color(245, 245, 245)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 18)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, self.conf.get('platform_title').upper(), 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.set_text_color(100, 100, 100)
        contact = f"{self.conf.get('address')} | Tel: {self.conf.get('phone')}"
        self.cell(0, 5, contact, 0, 1, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_medical_report(rec_num, d_name, d_qual, p_name, p_age, date, diag, treat, meds, fee):
    pdf = BasePDF()
    pdf.add_page()
    
    # --- RECEIPT HEADER ---
    pdf.set_draw_color(200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(0)
    pdf.cell(95, 8, f"PATIENT: {p_name} (Age: {p_age})", 0, 0)
    # FIX: Ensure Receipt Number is visible
    r_no = rec_num if rec_num else "PENDING"
    pdf.set_text_color(150, 0, 0)
    pdf.cell(95, 8, f"RECEIPT #: {r_no}", 0, 1, 'R')
    
    pdf.set_text_color(0)
    pdf.cell(95, 8, f"DOCTOR: {d_name} ({d_qual})", 0, 0)
    pdf.cell(95, 8, f"DATE: {date}", 0, 1, 'R')
    
    pdf.ln(5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)
    
    # --- CLINICAL DATA ---
    sections = [("DIAGNOSIS", diag), ("TREATMENT PLAN", treat), ("MEDICATIONS", meds)]
    
    for title, content in sections:
        pdf.set_fill_color(240, 248, 255)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 7, f"  {title}", 0, 1, 'L', 1)
        pdf.set_font('Arial', '', 10)
        # FIX: Handle NoneType
        val = str(content) if content else "N/A"
        pdf.multi_cell(0, 6, f"  {val}")
        pdf.ln(3)

    # --- FINANCIALS ---
    pdf.ln(10)
    pdf.set_fill_color(250)
    pdf.rect(10, pdf.get_y(), 190, 20, 'F')
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(140, 10, "   Professional Services Fee", 0, 0)
    pdf.cell(50, 10, f"${fee:,.2f}", 0, 1, 'R')
    
    pdf.ln(15)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(140, 10, "   TOTAL PAID", 0, 0)
    pdf.cell(50, 10, f"${fee:,.2f}", 0, 1, 'R')

    return bytes(pdf.output())

def generate_adhoc_receipt(num, date, rec, desc, amt):
    pdf = BasePDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "PAYMENT RECEIPT", 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font('Arial', '', 11)
    pdf.cell(100, 8, f"Receipt #: {num}", 0, 0); pdf.cell(90, 8, f"Date: {date}", 0, 1, 'R')
    pdf.ln(5)
    pdf.cell(0, 8, f"Received From: {rec}", 0, 1); pdf.ln(10)
    
    pdf.set_fill_color(230)
    pdf.cell(140, 10, "Description", 1, 0, 'C', 1)
    pdf.cell(50, 10, "Amount", 1, 1, 'C', 1)
    pdf.ln()
    pdf.cell(140, 10, desc, 1)
    pdf.cell(50, 10, f"${amt:.2f}", 1, 1, 'R')
    return bytes(pdf.output())