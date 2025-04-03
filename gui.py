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
        variety = st.text_input("Variety/Color")
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
    st.download_button("Download Report", report, "market_report.txt")

    all_rows = worksheet.get_all_records()
    bcc_emails = [row["email"] for row in all_rows if product_choice in row.get("products", "") or (product_choice in ["Oranges", "Lemons", "Mandarins", "Pomelos", "Grapefruits"] and "Citrus" in row.get("products", ""))]

    if bcc_emails:
        bcc_string = ",".join(bcc_emails)
        subject = f"Market Report – {product_choice} – {datetime.now().strftime('%d %B %Y')}"

        mail_body = f"""
Dear Partner,

Please find below this week's update concerning the {product_choice.lower()} market.

--- REPORT ---
{report}

--- DISCLAIMER ---
This report is based on best available internal and external information. No rights can be derived from its contents. It is generated using artificial intelligence, based on insights provided by our product specialists. It may be shared freely.

Subscribe to our updates: https://yourapp.streamlit.app/subscribe

Best regards,
Schrijvershof Team
        """

        mailto_link = f"mailto:?bcc={bcc_string}&subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(mail_body)}"
        st.markdown(f"[📧 Send Report via Email]({mailto_link})", unsafe_allow_html=True)

        html_body = f"""
<html>
<body>
<p>Dear Partner,<br><br>
Please find below this week's update concerning the <b>{product_choice.lower()}</b> market.<br><br>
---<br>
<pre>{report}</pre><br>
---<br><br>
Subscribe here: <a href='https://yourapp.streamlit.app/subscribe'>https://yourapp.streamlit.app/subscribe</a><br><br>
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
        st.download_button("Download Outlook Email (.eml)", data=eml_bytes, file_name="market_report.eml", mime="message/rfc822")
    else:
        st.warning("No email addresses found for this product.")
