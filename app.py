
import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv
import base64
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
import fitz  # PyMuPDF
import io
from PIL import Image

load_dotenv()

client = OpenAI()

def pdf_to_images(pdf_file):
    """Convert PDF pages to images"""
    images = []
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    
    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        # Convert page to image with high DPI for better quality
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
        img_data = pix.tobytes("png")
        images.append({
            'data': img_data,
            'type': 'png',
            'name': f"{pdf_file.name}_page_{page_num + 1}"
        })
    
    pdf_document.close()
    return images

def process_uploaded_files(uploaded_files):
    """Process uploaded files (images or PDFs) and return list of images"""
    all_images = []
    
    for uploaded_file in uploaded_files:
        if uploaded_file.type == "application/pdf":
            # Convert PDF to images
            pdf_images = pdf_to_images(uploaded_file)
            all_images.extend(pdf_images)
        else:
            # Handle regular image files
            image_data = uploaded_file.getvalue()
            image_type = uploaded_file.type.split("/")[1]
            all_images.append({
                'data': image_data,
                'type': image_type,
                'name': uploaded_file.name
            })
    
    return all_images

class AircraftInfo(BaseModel):
    make_model: str
    registration_number: str
    serial_number: str
    hobbs_time: float
    tach_time: float
    ttaf: float
    engine_TSMOH: Optional[str] = None
    propeller_TSPOH: Optional[str] = None
    date_of_audit: Optional[str] = None
    auditor_name: str

class LogbookCondition(BaseModel):
    all_original_logs_present: bool
    chronologically_organized: bool
    legible_handwriting: bool
    gaps_in_entries: bool
    scanned_digital_copies_exist: bool

class InspectionEntry(BaseModel):
    inspection_type: str
    last_completed: Optional[str] = None
    next_due: Optional[str] = None
    completed: bool
    notes: str

class RequiredInspections(BaseModel):
    inspections: List[InspectionEntry]

class ADEntry(BaseModel):
    ad_number: str
    description: str
    complied_date: Optional[str] = None
    method_of_compliance: Optional[str] = None
    recurring: bool
    next_due: Optional[str] = None
    notes: str

class AirworthinessDirectives(BaseModel):
    ads: List[ADEntry]

class ComponentEntry(BaseModel):
    component: str
    time_since_overhaul: str
    next_due: str
    notes: str

class TimeAndComponents(BaseModel):
    components: List[ComponentEntry]

class RepairsAndMods(BaseModel):
    STCs_logged: bool
    form_337s: bool
    field_approvals: bool
    updated_weight_balance: bool
    avionics_upgrades: str

class RegulatoryDocs(BaseModel):
    airworthiness_certificate: bool
    registration_certificate: bool
    current_POH_AFM: bool
    MEL_applicable: bool
    maintenance_tracking_reports: bool

class Summary(BaseModel):
    missing_items: str
    outstanding_maintenance_or_ADs: str
    logbook_gaps: str
    general_observations: str
    recommendations: str

class AviationLogbookAudit(BaseModel):
    aircraft_info: AircraftInfo
    logbook_condition: LogbookCondition
    required_inspections: RequiredInspections
    airworthiness_directives: AirworthinessDirectives
    time_and_components: TimeAndComponents
    repairs_and_mods: RepairsAndMods
    regulatory_docs: RegulatoryDocs
    summary: Summary

st.title("Aviation Logbook Audit")

# Initialize session state for storing audit results
if 'audit_results' not in st.session_state:
    st.session_state.audit_results = None
if 'processed_images' not in st.session_state:
    st.session_state.processed_images = 0

uploaded_files = st.file_uploader("Choose logbook files (images or PDFs)...", type=["jpg", "png", "jpeg", "pdf"], accept_multiple_files=True)

if uploaded_files:
    # Process all uploaded files (convert PDFs to images)
    all_images = process_uploaded_files(uploaded_files)
    
    st.write(f"📁 Uploaded {len(uploaded_files)} files → {len(all_images)} images to analyze")
    
    # Display processed images in a grid
    cols = st.columns(min(len(all_images), 4))
    for i, image_info in enumerate(all_images):
        with cols[i % 4]:
            # Display image from bytes
            st.image(image_info['data'], caption=image_info['name'], use_container_width=True)
    
    # Generate Report Button
    if st.button("🔍 Generate Logbook Audit Report", type="primary"):
        batch_size = 5
        total_batches = (len(all_images) + batch_size - 1) // batch_size
        
        # Create progress bar
        progress_bar = st.progress(0, f"Starting analysis...")
        status_text = st.empty()
        
        # Reset session state for new analysis
        st.session_state.audit_results = None
        st.session_state.processed_images = 0
        
        # Process all batches automatically
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(all_images))
            batch_images = all_images[start_idx:end_idx]
            
            # Update progress
            progress = (batch_num + 1) / total_batches
            status_text.text(f"Processing batch {batch_num + 1} of {total_batches} ({len(batch_images)} images)...")
            
            # Prepare messages with batch images
            if st.session_state.audit_results is None:
                # First batch - no previous context
                system_message = "You are an expert aviation logbook auditor. Analyze the provided logbook images and extract information to fill out the aviation logbook audit template. DO NOT make up information - if you cannot find specific information in the images, leave those fields blank or use appropriate null values. It's perfectly acceptable to leave fields empty until the information is found in the images."
                user_message = "Please analyze these aviation logbook images and extract all available information to complete the logbook audit. Only include information that you can clearly see in the images. If information is not visible or unclear, leave those fields blank. Focus on accuracy over completeness."
            else:
                # Subsequent batches - include previous results as context
                system_message = "You are an expert aviation logbook auditor. You have already analyzed some logbook images and created a partial audit report. Now analyze these additional images and UPDATE the existing audit report with any new information found. DO NOT make up information - only add information you can clearly see in the new images. Keep existing information unless you find conflicting data that is more accurate."
                user_message = f"Here is the current audit report from previous images: {st.session_state.audit_results.model_dump_json()}. Now analyze these additional logbook images and update the audit report with any new information you can clearly see. Merge the information intelligently - add new inspections, components, ADs, etc. to the existing lists, and update fields that were previously empty if you now have the information."
            
            messages = [
                {"role": "system", "content": system_message},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": user_message}
                    ]
                }
            ]
            
            # Add batch images to the message
            for image_info in batch_images:
                base64_image = base64.b64encode(image_info['data']).decode("utf-8")
                
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{image_info['type']};base64,{base64_image}"
                    }
                })

            # Process the batch
            response = client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=messages,
                max_tokens=4000,
                response_format=AviationLogbookAudit,
            )
            
            # Update session state with new results
            st.session_state.audit_results = response.choices[0].message.parsed
            st.session_state.processed_images = end_idx
            
            # Update progress bar
            progress_bar.progress(progress, f"Completed batch {batch_num + 1} of {total_batches}")
        
        # Final completion
        progress_bar.progress(1.0, f"✅ Analysis complete! Processed {len(all_images)} images.")
        status_text.text("🎉 All batches processed successfully!")
        
        # Now show the final results
        st.rerun()
    
    # Display results if we have any (only after all processing is complete)
    elif st.session_state.audit_results:
        audit = st.session_state.audit_results
        
        # Add a reset button
        if st.button("🔄 Reset and Start Over", type="secondary"):
            st.session_state.audit_results = None
            st.session_state.processed_images = 0
            st.rerun()
        
        # Create tabs for different sections
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "🛩️ Aircraft Info", 
            "📋 Logbook Condition", 
            "🔍 Inspections", 
            "⚠️ Airworthiness Directives", 
            "⏱️ Time & Components", 
            "🔧 Repairs & Mods", 
            "📄 Regulatory Docs", 
            "📝 Summary"
        ])
        
        with tab1:
            st.header("Aircraft Information")
            aircraft_data = {
                "Field": ["Make/Model", "Registration", "Serial Number", "Hobbs Time", "Tach Time", "TTAF", "Engine TSMOH", "Propeller TSPOH", "Date of Audit", "Auditor"],
                "Value": [
                    str(audit.aircraft_info.make_model),
                    str(audit.aircraft_info.registration_number),
                    str(audit.aircraft_info.serial_number),
                    str(audit.aircraft_info.hobbs_time),
                    str(audit.aircraft_info.tach_time),
                    str(audit.aircraft_info.ttaf),
                    str(audit.aircraft_info.engine_TSMOH or "Not specified"),
                    str(audit.aircraft_info.propeller_TSPOH or "Not specified"),
                    str(audit.aircraft_info.date_of_audit or "Not specified"),
                    str(audit.aircraft_info.auditor_name)
                ]
            }
            st.table(aircraft_data)
        
        with tab2:
            st.header("Logbook Condition")
            condition_data = {
                "Condition": ["All Original Logs Present", "Chronologically Organized", "Legible Handwriting", "Gaps in Entries", "Digital Copies Exist"],
                "Status": [
                    "✅ Yes" if audit.logbook_condition.all_original_logs_present else "❌ No",
                    "✅ Yes" if audit.logbook_condition.chronologically_organized else "❌ No",
                    "✅ Yes" if audit.logbook_condition.legible_handwriting else "❌ No",
                    "⚠️ Yes" if audit.logbook_condition.gaps_in_entries else "✅ No",
                    "✅ Yes" if audit.logbook_condition.scanned_digital_copies_exist else "❌ No"
                ]
            }
            st.table(condition_data)
        
        with tab3:
            st.header("Required Inspections")
            if audit.required_inspections.inspections:
                inspection_data = {
                    "Inspection Type": [str(i.inspection_type) for i in audit.required_inspections.inspections],
                    "Last Completed": [str(i.last_completed or "Not specified") for i in audit.required_inspections.inspections],
                    "Next Due": [str(i.next_due or "Not specified") for i in audit.required_inspections.inspections],
                    "Completed": ["✅ Yes" if i.completed else "❌ No" for i in audit.required_inspections.inspections],
                    "Notes": [str(i.notes) for i in audit.required_inspections.inspections]
                }
                st.table(inspection_data)
            else:
                st.info("No inspection information found in the images.")
        
        with tab4:
            st.header("Airworthiness Directives")
            if audit.airworthiness_directives.ads:
                ad_data = {
                    "AD Number": [str(ad.ad_number) for ad in audit.airworthiness_directives.ads],
                    "Description": [str(ad.description) for ad in audit.airworthiness_directives.ads],
                    "Complied Date": [str(ad.complied_date or "Not specified") for ad in audit.airworthiness_directives.ads],
                    "Method": [str(ad.method_of_compliance or "Not specified") for ad in audit.airworthiness_directives.ads],
                    "Recurring": ["✅ Yes" if ad.recurring else "❌ No" for ad in audit.airworthiness_directives.ads],
                    "Next Due": [str(ad.next_due or "Not specified") for ad in audit.airworthiness_directives.ads],
                    "Notes": [str(ad.notes) for ad in audit.airworthiness_directives.ads]
                }
                st.table(ad_data)
            else:
                st.info("No airworthiness directive information found in the images.")
        
        with tab5:
            st.header("Time and Components")
            if audit.time_and_components.components:
                component_data = {
                    "Component": [str(c.component) for c in audit.time_and_components.components],
                    "Time Since Overhaul": [str(c.time_since_overhaul) for c in audit.time_and_components.components],
                    "Next Due": [str(c.next_due) for c in audit.time_and_components.components],
                    "Notes": [str(c.notes) for c in audit.time_and_components.components]
                }
                st.table(component_data)
            else:
                st.info("No component time information found in the images.")
        
        with tab6:
            st.header("Repairs and Modifications")
            repairs_data = {
                "Item": ["STCs Logged", "Form 337s", "Field Approvals", "Updated Weight & Balance", "Avionics Upgrades"],
                "Status/Details": [
                    "✅ Yes" if audit.repairs_and_mods.STCs_logged else "❌ No",
                    "✅ Yes" if audit.repairs_and_mods.form_337s else "❌ No",
                    "✅ Yes" if audit.repairs_and_mods.field_approvals else "❌ No",
                    "✅ Yes" if audit.repairs_and_mods.updated_weight_balance else "❌ No",
                    str(audit.repairs_and_mods.avionics_upgrades or "None specified")
                ]
            }
            st.table(repairs_data)
        
        with tab7:
            st.header("Regulatory Documents")
            docs_data = {
                "Document": ["Airworthiness Certificate", "Registration Certificate", "Current POH/AFM", "MEL Applicable", "Maintenance Tracking Reports"],
                "Status": [
                    "✅ Present" if audit.regulatory_docs.airworthiness_certificate else "❌ Missing",
                    "✅ Present" if audit.regulatory_docs.registration_certificate else "❌ Missing",
                    "✅ Present" if audit.regulatory_docs.current_POH_AFM else "❌ Missing",
                    "✅ Yes" if audit.regulatory_docs.MEL_applicable else "❌ No",
                    "✅ Present" if audit.regulatory_docs.maintenance_tracking_reports else "❌ Missing"
                ]
            }
            st.table(docs_data)
        
        with tab8:
            st.header("Audit Summary")
            st.subheader("Missing Items")
            st.write(audit.summary.missing_items or "None identified")
            
            st.subheader("Outstanding Maintenance or ADs")
            st.write(audit.summary.outstanding_maintenance_or_ADs or "None identified")
            
            st.subheader("Logbook Gaps")
            st.write(audit.summary.logbook_gaps or "None identified")
            
            st.subheader("General Observations")
            st.write(audit.summary.general_observations or "No additional observations")
            
            st.subheader("Recommendations")
            st.write(audit.summary.recommendations or "No specific recommendations")

else:
    st.info("👆 Please upload one or more logbook images to begin the audit process.")