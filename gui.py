import streamlit as st
import json
import openai
import pandas as pd
import urllib.parse
import gspread
import yaml
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from config import OPENAI_API_KEY
from fpdf import FPDF
import base64
import re

openai.api_key = st.secrets["OPENAI_API_KEY"]

with open('./config/options.json', 'r') as file:
    opties = json.load(file)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
gclient = gspread.authorize(credentials)
subsheet = gclient.open_by_url("https://docs.google.com/spreadsheets/d/1rVeFabNieHsKQS7zLZgpwisdiAUaOZX4uQ7BsuTKTHY")
worksheet = subsheet.sheet1

st.title("Market Report Generator")

product_choice = st.selectbox("Product", opties["producten"])

if "segments" not in st.session_state:
    st.session_state.segments = []

st.markdown("### Market Segments")
with st.form("segment_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        variety = st.selectbox("Variety/Color", opties["product_specificatie"])
    with col2:
        origin = st.selectbox("Origin", opties["landen_en_continenten"])
    with col3:
        note = st.text_area("Market Note")

    col4, col5 = st.columns(2)
    with col4:
        lowest_price = st.number_input("Lowest Price (€)", min_value=0.0, step=0.1)
    with col5:
        highest_price = st.number_input("Highest Price (€)", min_value=0.0, step=0.1)

    col6, col7 = st.columns(2)
    with col6:
        market_quality = st.selectbox("Market Quality", ["Good", "Medium", "Poor"])
    with col7:
        current_demand = st.selectbox("Current Demand", ["High", "Medium", "Low"])

    col8, col9 = st.columns(2)
    with col8:
        demand_next = st.selectbox("Demand Next Week", ["↑", "→", "↓"])
    with col9:
        arrivals_next = st.selectbox("Arrivals Next Week", ["↑", "→", "↓"])

    submitted = st.form_submit_button("Add Segment")
    if submitted and variety and origin:
        st.session_state.segments.append({
            "variety": variety,
            "origin": origin,
            "note": note,
            "lowest_price": lowest_price,
            "highest_price": highest_price,
            "market_quality": market_quality,
            "current_demand": current_demand,
            "demand_next": demand_next,
            "arrivals_next": arrivals_next
        })

if st.session_state.segments:
    st.markdown("#### Added Market Segments")
    for idx, seg in enumerate(st.session_state.segments):
        st.markdown(f"**{seg['variety']}** from *{seg['origin']}* → {seg['note']}")
        if st.button(f"Remove {seg['variety']} - {seg['origin']}", key=f"del_{idx}"):
            st.session_state.segments.pop(idx)
            st.experimental_rerun()

extra_notes = st.text_area("General Observations (optional)", placeholder="Enter additional context or strategic advice...")

if st.button("Generate Report"):
    report_data = {
        "product": product_choice,
        "notes": extra_notes,
        "segments": st.session_state.segments
    }

    yaml_input = yaml.dump(report_data, allow_unicode=True)

    prompt = f"""
You are a professional market analyst for a European fruit importer. Your job is to write weekly market updates for overseas producers.

STRUCTURE:
- Write one short report per segment.
- Use the fields provided to assess price, demand, quality, and shipment strategy.
- For each segment:
  * Analyze the relation between demand and arrivals.
  * Conclude how the market is evolving.
  * End with a clear shipping advice (e.g., continue, hold, ship selectively).
- Add a general closing note.

FIELD LOGIC:
- If demand ↓ and arrivals ↑ → Market likely to decline.
- If demand ↑ and arrivals ↑ → Stable or improving market.
- If demand → and arrivals ↑ → Risk of saturation.
- Remember: Advice is for arrivals 3 weeks from now.

DATA:
{yaml_input}
"""

    with st.spinner("Generating report..."):
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1200
        )

    report = response.choices[0].message.content.strip()
    st.success("Report generated!")
    st.write(report)

    class PDF(FPDF):
        def header(self):
            self.image("logo.png", 10, 8, 50)
            self.set_font("Helvetica", 'B', 14)
            self.cell(0, 10, f"Market Report - {product_choice} - {datetime.now().strftime('%d %B %Y')}", ln=1, align="R")
            self.ln(10)

        def footer(self):
            self.set_y(-30)
            self.set_font("Helvetica", size=8)
            self.multi_cell(0, 5, "Schrijvershof B.V. · Kwakscheweg 3 · 3261 LG Oud-Beijerland · The Netherlands\nphone +31 (0)186 643000 · internet www.schrijvershof.nl", align="C")
            self.set_y(-15)
            self.multi_cell(0, 5, "Disclaimer: This report is based on best available internal and external information. No rights can be derived from its contents. It is generated using artificial intelligence, based on insights provided by our product specialists. It may be shared freely.", align="C")

    def clean_line(line):
        line = re.sub(r'[^\x00-\x7F]', '', line)
        line = re.sub(r'[-_/]{10,}', '', line)
        return line

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    lines = report.splitlines()
    paragraph = ""

    for line in lines:
        line = clean_line(line.strip())
        if line == "":
            if paragraph:
                pdf.multi_cell(0, 8, paragraph.strip(), align='J')
                pdf.ln(4)
                paragraph = ""
        else:
            paragraph += " " + line

    if paragraph:
        pdf.multi_cell(0, 8, paragraph.strip(), align='J')

    pdf_output = f"report_{product_choice}_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf_bytes = pdf.output(dest='S')
    b64 = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{pdf_output}">📄 Download PDF Report</a>'
    st.markdown(href, unsafe_allow_html=True)

