import streamlit as st
import json
import openai
import pandas as pd
import matplotlib.pyplot as plt
import io
import urllib.parse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from config import OPENAI_API_KEY

openai.api_key = st.secrets["OPENAI_API_KEY"]

# Laad dropdown keuzes
with open('./config/options.json', 'r') as file:
    opties = json.load(file)

# Google Sheets setup (voor e-mail export)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
gclient = gspread.authorize(credentials)
subsheet = gclient.open_by_url("https://docs.google.com/spreadsheets/d/1rVeFabNieHsKQS7zLZgpwisdiAUaOZX4uQ7BsuTKTHY")
worksheet = subsheet.sheet1

st.title("Market Report Generator")

product_choice = st.selectbox("Product", opties["producten"])

multi_entries = []
if product_choice in ["Grapes", "Citrus"]:
    st.markdown("### Market Segments")
    if "segments" not in st.session_state:
        st.session_state.segments = []

    with st.form("segment_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            variety = st.text_input("Variety/Color")
        with col2:
            origin = st.selectbox("Origin", opties["landen_en_continenten"])
        with col3:
            note = st.text_area("Market Note")

        submitted = st.form_submit_button("Add Segment")
        if submitted and variety and origin and note:
            st.session_state.segments.append({"variety": variety, "origin": origin, "note": note})

    if st.session_state.segments:
        st.markdown("#### Added Market Segments")
        for idx, entry in enumerate(st.session_state.segments):
            st.markdown(f"**{entry['variety']}** from *{entry['origin']}*  → {entry['note']}")
            if st.button(f"Remove {entry['variety']} - {entry['origin']}", key=f"del_{idx}"):
                st.session_state.segments.pop(idx)
                st.experimental_rerun()
else:
    st.session_state.segments = []

product_spec = st.selectbox("Product Specification", opties["product_specificatie"])
market_availability = st.selectbox("Market Availability", opties["markt_beschikbaarheid"])
price_expectation = st.selectbox("Price Expectation", opties["prijs_verwachting"])

col_price1, col_price2, col_price3 = st.columns(3)
with col_price1:
    price_indication = st.selectbox("Price Indication", opties["prijs_aanduiding"])
with col_price2:
    lowest_market_price = st.number_input("Lowest Market Price in Euro (€)", min_value=0.0, step=0.1, format="%.2f")
with col_price3:
    highest_market_price = st.number_input("Highest Market Price in Euro (€)", min_value=0.0, step=0.1, format="%.2f")

arrival_forecast = st.selectbox("Arrival Forecast", opties["aankomst_vooruitzicht"])
origin_change = st.selectbox("Origin Change", opties["herkomst_verandering"])

if origin_change == "Yes":
    col1, col2 = st.columns(2)
    with col1:
        origin_from = st.selectbox("Origin From", opties["landen_en_continenten"])
    with col2:
        origin_towards = st.selectbox("Origin Towards", opties["landen_en_continenten"])
else:
    origin_from = "-"
    origin_towards = "-"

shipping_advice = st.selectbox("Continue Shipping Advised", opties["verscheping_continuiteit_advies"])
market_sentiment = st.selectbox("Market Sentiment", opties["markt_sentiment"])
market_quality = st.selectbox("Market Quality", opties["markt_kwaliteit"])
consumption = st.selectbox("Consumption", opties["consumptie"])
size_preference = st.selectbox("Size Preference", opties["maat_voorkeur"])
extra_notes = st.text_area("Additional Observations / Notes (optional)", placeholder="Enter key observations, market dynamics, or strategic advice...")

if st.button("Generate Report"):
    general_inputs = {
        "Product": product_choice,
        "Product Specification": product_spec,
        "Market Availability": market_availability,
        "Price Expectation": price_expectation,
        "Price Indication": price_indication,
        "Arrival Forecast": arrival_forecast,
        "Origin Change": origin_change,
        "Origin From": origin_from,
        "Origin Towards": origin_towards,
        "Continue Shipping Advised": shipping_advice,
        "Market Sentiment": market_sentiment,
        "Market Quality": market_quality,
        "Consumption": consumption,
        "Size Preference": size_preference,
        "Lowest Market Price": f"€ {lowest_market_price:.2f}" if lowest_market_price > 0 else "-",
        "Highest Market Price": f"€ {highest_market_price:.2f}" if highest_market_price > 0 else "-",
    }

    if all(v == "-" or not v for v in general_inputs.values()) and not st.session_state.segments and not extra_notes.strip():
        st.warning("No report data entered. Please fill in some fields.")
    else:
        base_info = "\n".join([f"{k}: {v}" for k, v in general_inputs.items() if v and v != "-"])

        segment_info = ""
        if st.session_state.segments:
            segment_info = "\n\nMARKET SEGMENTS:\n"
            for seg in st.session_state.segments:
                segment_info += f"- {seg['variety']} from {seg['origin']}: {seg['note']}\n"

        if extra_notes.strip():
            base_info = f"GENERAL CONTEXT:\n{extra_notes.strip()}\n\n---\n\n" + base_info

        report_inputs = f"{segment_info}\n\n{base_info}"

        prompt = f'''
You are assisting a Dutch fruit importing company in writing a weekly market update for overseas producers and exporters. These reports are used to inform and advise suppliers in countries like Brazil, Peru, and South Africa. The fruits are imported into Europe and sold mainly to service providers who handle ripening, packing, and delivery to retail.

IMPORTANT:
- Do NOT assume that the suppliers are currently taking actions unless clearly stated.
- The report should speak from the perspective of the importer, summarizing the current situation in Europe.
- Use simple, direct, and neutral English. Avoid overly formal or technical language.
- The audience does not speak English as their first language.
- Avoid repeating well-known industry facts such as common logistical delays.
- Do not assign blame or agency to specific parties (e.g. "suppliers", "exporters") unless stated.
- Any additional notes provided are general observations and should not be overly tied to the product (e.g., mangoes), unless it clearly is.
- A change in origin is not absolute; multiple countries may still be in supply simultaneously.

RULES:
- Do not fabricate any data. Use only the fields that were actually filled in.
- If all fields are empty or set to '-', respond with: "No data was provided. No report can be generated."
- Do not assume product, origin, or market segments unless they were explicitly selected.

STRUCTURE OF THE REPORT:
1. Summary: Start with a clear overview of the current market situation based on all filled-in form fields (in order of appearance).
2. Conclusion & Advice: End with a short, strategic conclusion and professional advice to the supplier about how to proceed.

DATA TO USE:
{report_inputs}
'''

        with st.spinner("Generating report..."):
            gen_response = openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )

        initial_report = gen_response.choices[0].message.content.strip()

        review_prompt = f'''
Act as a fact-checking assistant. Compare the report to the original prompt and input. If the report includes incorrect facts, makes assumptions not backed by the input, or misrepresents the data, then correct only those parts. Do not shorten or reword for style — only fix factual mismatches.

PROMPT:
{prompt.strip()}

--- GENERATED REPORT ---
{initial_report}
--- END REPORT ---

Your task: return the corrected report, if needed.
'''

        with st.spinner("Reviewing report for factual consistency..."):
            review_response = openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": review_prompt}],
                temperature=0.2,
                max_tokens=1200
            )

        final_report = review_response.choices[0].message.content.strip()

        st.success("Final report ready!")
        st.write(final_report)
        st.download_button("Download Report", final_report, "market_report.txt")
