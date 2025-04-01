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

        # --- BEGIN AI PROMPT (FIXED FORMAT) ---
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
- Do not state or imply that one origin is primary unless this is explicitly stated.
- Do not advise suppliers to adjust size or variety preferences based solely on the current market, especially if an origin change is coming. Mention the uncertainty instead.

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
        # --- END AI PROMPT ---

        with st.spinner("Generating report..."):
            response = openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )

        report = response.choices[0].message.content.strip()
        st.success("Report generated!")
        st.write(report)
        st.download_button("Download Report", report, "market_report.txt")

        all_rows = worksheet.get_all_records()
        bcc_emails = [row["email"] for row in all_rows if product_choice in row.get("products", "") or (product_choice in ["Oranges", "Lemons", "Mandarins", "Pomelos", "Grapefruits"] and "Citrus" in row.get("products", ""))]

        if bcc_emails:
            bcc_string = ",".join(bcc_emails)
            subject = f"Market Report – {product_choice} – {datetime.now().strftime('%d %B %Y')}"
            html_body = f"""
            <html>
            <body>
            <p>Dear Partner,<br><br>
            Please find below this week's update concerning the <b>{product_choice.lower()}</b> market.<br>
            Should you have any questions or wish to discuss planning or expectations, feel free to contact us.<br><br>
            ---<br>
            <pre>{report}</pre><br>
            ---<br><br>
            Best regards,<br>
            <b>Schrijvershof Team</b><br><br>
            <i>Disclaimer: This report is based on best available internal and external information. No rights can be derived from its contents. This report is generated using artificial intelligence, based on data and insights provided by our product specialists. It may be freely shared or forwarded with others.</i>
            </p>
            </body>
            </html>
            """

            eml_content = f"""Subject: {subject}
BCC: {bcc_string}
Content-Type: text/html

{html_body}"""

            eml_bytes = eml_content.encode("utf-8")
            st.download_button("\ud83d\udce9 Download Outlook Email (.eml)", data=eml_bytes, file_name="market_report.eml", mime="message/rfc822")

            mailto_link = f"mailto:?bcc={bcc_string}&subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(report)}"
            st.markdown(f"[\ud83d\udce7 Send via Outlook]({mailto_link})", unsafe_allow_html=True)
        else:
            st.warning("No email addresses found for this product.")
        st.success("Final report ready!")
        st.write(final_report)
        st.download_button("Download Report", final_report, "market_report.txt")
