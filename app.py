import streamlit as st
from faker import Faker
from fpdf import FPDF
import random

# Page configuration
st.set_page_config(
    page_title="Credential Generator",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

fake = Faker()

# -----------------------------
# Random value pools
# -----------------------------
DEGREES = ["MD", "DO", "PhD", "MBBS", "DMD", "DDS", "MSN", "BSN", "MPH", "MBA (Healthcare)", "MHA"]
EDU_TYPES = ["Medical School", "Residency", "Fellowship", "Nursing School", "Graduate Program", "Continuing Med Ed", "Board Certification Program"]
POSITIONS = ["Physician", "Surgeon", "Nurse", "Anesthesiologist", "Therapist", "Radiology Tech", "PA", "NP", "Medical Director"]
RELATIONSHIPS = ["Colleague", "Supervisor", "Mentor", "Program Director", "Residency Director", "Advisor", "Department Chair"]
COVERAGE_TYPES = ["Malpractice", "General Liability", "Workers Comp", "Cyber Liability", "Auto (Commercial)", "Premises Liability"]
LIABILITY_TYPES = ["Claims-made", "Occurrence", "Tail Coverage", "Consent to Settle", "Shared Aggregate"]
POLICY_LIMITS_POOL = [
    "$1M / $3M", "$2M / $4M", "$500k / $1M", "$5M Aggregate", "$1M Occurrence"
]

# -----------------------------
# Section / field schemas
# -----------------------------
SECTIONS = {
    "education": [
        ("edu_type", "Education and Training Type"),
        ("degree", "Degree"),
        ("institution_name", "Institution Name"),
        ("start_year", "Start Year"),
        ("end_year", "End Year"),
    ],
    "work": [
        ("position", "Position"),
        ("practice_name", "Practice Name"),
        ("practice_address", "Practice Address"),
        ("start_date", "Start Date"),
        ("end_date", "End Date"),
    ],
    "reference": [
        ("name", "Name"),
        ("position", "Position"),
        ("ref_practice_name", "Practice Name"),
        ("email", "Email"),
        ("relationship", "Relationship"),
        ("phone", "Phone"),
    ],
    "insurance": [
        ("issued_by", "Issued By"),
        ("coverage_type", "Coverage Type"),
        ("effective_date", "Effective Date"),
        ("policy_number", "Policy Number"),
        ("policy_limits", "Policy Limits"),
        ("expiration_date", "Expiration Date"),
    ],
    "liability": [
        ("liab_issued_by", "Issued By"),
        ("liab_policy_number", "Policy Number"),
        ("liab_coverage_type", "Coverage Type"),
        ("liab_policy_limits", "Policy Limits"),
        ("liab_effective_date", "Effective Date"),
        ("liab_expiration_date", "Expiration Date"),
    ],
}


# -----------------------------
# Randomizers per field
# -----------------------------
def rand_edu_type(): return random.choice(EDU_TYPES)
def rand_degree(): return random.choice(DEGREES)
def rand_institution(): return fake.company()
def rand_year_start(): return str(random.randint(1990, 2018))
def rand_year_end(): return str(random.randint(2019, 2025))

def rand_position(): return random.choice(POSITIONS)
def rand_practice(): return fake.company()
def rand_address(): return fake.address().replace("\n", ", ")
def rand_start_date(): return str(fake.date_between("-10y", "-3y"))
def rand_end_date(): return str(fake.date_between("-2y", "today"))

def rand_name(): return fake.name()
def rand_job(): return fake.job()
def rand_ref_practice(): return fake.company()
def rand_email(): return fake.email()
def rand_relationship(): return random.choice(RELATIONSHIPS)
def rand_phone(): return fake.phone_number()

def rand_ins_issued(): return fake.company()
def rand_ins_coverage(): return random.choice(COVERAGE_TYPES)
def rand_ins_effective(): return str(fake.date_between("-3y", "today"))
def rand_policy_number(): return fake.bothify("???-#######")
def rand_limits(): return random.choice(POLICY_LIMITS_POOL)
def rand_expiration(): return str(fake.date_between("today", "+1y"))

def rand_liab_issued(): return fake.company()
def rand_liab_policy_number(): return fake.bothify("???-#######")
def rand_liab_coverage(): return random.choice(LIABILITY_TYPES)
def rand_liab_limits(): return random.choice(POLICY_LIMITS_POOL)
def rand_liab_effective(): return str(fake.date_between("-3y", "today"))
def rand_liab_expiration(): return str(fake.date_between("today", "+1y"))

FIELD_RANDOMIZERS = {
    "edu_type": rand_edu_type,
    "degree": rand_degree,
    "institution_name": rand_institution,
    "start_year": rand_year_start,
    "end_year": rand_year_end,

    "position": rand_position,
    "practice_name": rand_practice,
    "practice_address": rand_address,
    "start_date": rand_start_date,
    "end_date": rand_end_date,

    "name": rand_name,
    "ref_practice_name": rand_ref_practice,
    "email": rand_email,
    "relationship": rand_relationship,
    "phone": rand_phone,
    # re-using rand_job for reference "Position"
    "position_reference": rand_job,

    "issued_by": rand_ins_issued,
    "coverage_type": rand_ins_coverage,
    "effective_date": rand_ins_effective,
    "policy_number": rand_policy_number,
    "policy_limits": rand_limits,
    "expiration_date": rand_expiration,

    "liab_issued_by": rand_liab_issued,
    "liab_policy_number": rand_liab_policy_number,
    "liab_coverage_type": rand_liab_coverage,
    "liab_policy_limits": rand_liab_limits,
    "liab_effective_date": rand_liab_effective,
    "liab_expiration_date": rand_liab_expiration,
}


# -----------------------------
# Init session state values (blank)
# -----------------------------
def ensure_session_defaults():
    for section_key, fields in SECTIONS.items():
        for field_key, _label in fields:
            state_key = f"{section_key}__{field_key}"
            if state_key not in st.session_state:
                st.session_state[state_key] = ""


# -----------------------------
# Master randomize all
# -----------------------------
def randomize_all():
    for section_key, fields in SECTIONS.items():
        for field_key, _label in fields:
            state_key = f"{section_key}__{field_key}"
            # Some shared field keys (like "position") appear in multiple sections;
            # differentiate with section prefix, so map to correct randomizer:
            rand_key = field_key
            if section_key == "reference" and field_key == "position":
                rand_key = "position_reference"
            if section_key == "liability" and field_key.startswith("liab_"):
                rand_key = field_key  # already prefixed
            if section_key == "insurance" and field_key in FIELD_RANDOMIZERS:
                rand_key = field_key
            # fallback
            rand_func = FIELD_RANDOMIZERS.get(rand_key, lambda: fake.word())
            st.session_state[state_key] = rand_func()


# -----------------------------
# Render a field row
# -----------------------------
def render_field(section_key: str, field_key: str, label: str):
    state_key = f"{section_key}__{field_key}"
    col1, col2 = st.columns([5, 1])

    with col1:
        st.session_state[state_key] = st.text_input(
            label,
            value=st.session_state.get(state_key, ""),
            key=f"input_{state_key}",
        )

    with col2:
        if st.button("🎲", key=f"dice_{state_key}"):
            # choose correct randomizer mapping
            rand_key = field_key
            if section_key == "reference" and field_key == "position":
                rand_key = "position_reference"
            rand_func = FIELD_RANDOMIZERS.get(rand_key, lambda: fake.word())
            st.session_state[state_key] = rand_func()
            # Force immediate UI update by rerunning
            st.rerun()


# -----------------------------
# Render a section
# -----------------------------
def render_section(section_key: str, title: str):
    st.subheader(title)
    for field_key, label in SECTIONS[section_key]:
        render_field(section_key, field_key, label)
    
    # Add individual PDF download button for this section
    section_data = {}
    for field_key, label in SECTIONS[section_key]:
        state_key = f"{section_key}__{field_key}"
        section_data[label] = st.session_state.get(state_key, "")
    
    pdf_path = build_single_category_pdf(section_key, section_data)
    with open(pdf_path, "rb") as f:
        st.download_button(
            f"📄 Download {title} PDF", 
            f, 
            file_name=f"{section_key}_document.pdf",
            key=f"download_{section_key}"
        )
    st.markdown("---")


# -----------------------------
# Gather data for PDF
# -----------------------------
def collect_data_for_pdf():
    data = {}
    for section_key, fields in SECTIONS.items():
        section_data = {}
        for field_key, label in fields:
            state_key = f"{section_key}__{field_key}"
            section_data[label] = st.session_state.get(state_key, "")
        data[section_key] = section_data
    return data


# -----------------------------
# PDF creation
# -----------------------------
def build_pdf(data: dict, out_path: str = "generated_form.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    for section_key, section_data in data.items():
        title = section_key.replace("_", " ").title()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, txt=title, ln=True)
        pdf.set_font("Arial", "", 12)
        for label, value in section_data.items():
            pdf.multi_cell(0, 8, txt=f"{label}: {value}")
        pdf.ln(4)

    pdf.output(out_path)
    return out_path

def build_single_category_pdf(section_key: str, section_data: dict, out_path: str = None):
    if out_path is None:
        out_path = f"{section_key}_document.pdf"
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title
    title = section_key.replace("_", " ").title()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 15, txt=f"{title} Document", ln=True, align='C')
    pdf.ln(5)
    
    # Content
    pdf.set_font("Arial", "", 12)
    for label, value in section_data.items():
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, txt=f"{label}:", ln=True)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 6, txt=str(value))
        pdf.ln(2)
    
    pdf.output(out_path)
    return out_path


# -----------------------------
# MAIN APP
# -----------------------------
st.title("📄 Credential Generator")

ensure_session_defaults()

# Master randomize button
if st.button("🎲 Generate All Random"):
    randomize_all()
    st.rerun()

# Sections
render_section("education", "Education and Training")
render_section("work", "Work History")
render_section("reference", "Professional Reference")
render_section("insurance", "Insurance")
render_section("liability", "Professional Liability")

