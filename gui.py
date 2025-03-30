import streamlit as st
import json
import openai
import pandas as pd
import matplotlib.pyplot as plt
import io
from config import OPENAI_API_KEY

openai.api_key = st.secrets["OPENAI_API_KEY"]

# Laad dropdown keuzes
with open('./config/options.json', 'r') as file:
    opties = json.load(file)

st.title("Market Report Generator")

# UI-keuzes
product_choice = st.selectbox("Product", opties["producten"])
product_spec = st.selectbox("Product Specification", opties["product_specificatie"])
market_availability = st.selectbox("Market Availability", opties["markt_beschikbaarheid"])
price_expectation = st.selectbox("Price Expectation", opties["prijs_verwachting"])

# Prijs indicatie en prijswaarden in één regel
col_price1, col_price2, col_price3 = st.columns(3)
with col_price1:
    price_indication = st.selectbox("Price Indication", opties["prijs_aanduiding"])
with col_price2:
    lowest_market_price = st.number_input("Lowest Market Price in Euro (€)", min_value=0.0, step=0.1, format="%.2f")
with col_price3:
    highest_market_price = st.number_input("Highest Market Price in Euro (€)", min_value=0.0, step=0.1, format="%.2f")

arrival_forecast = st.selectbox("Arrival Forecast", opties["aankomst_vooruitzicht"])
origin_change = st.selectbox("Origin Change", opties["herkomst_verandering"])

# Toon alleen bij origin_change == Yes
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

# Vrij tekstveld voor extra input
extra_notes = st.text_area("Additional Observations / Notes (optional)", placeholder="Enter key observations, market dynamics, or strategic advice...")

uploaded_file = None
mango_chart_buffer = None

if product_choice == "Mangoes":
    st.markdown("---")
    st.subheader("Mango Volumes Upload (Excel)")
    uploaded_file = st.file_uploader("Upload mango volume Excel", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        weeks = df.iloc[1:, 18].astype(str).reset_index(drop=True)
        vol_2022 = pd.to_numeric(df.iloc[1:, 19], errors='coerce').reset_index(drop=True)
        vol_2023 = pd.to_numeric(df.iloc[1:, 20], errors='coerce').reset_index(drop=True)
        vol_2024 = pd.to_numeric(df.iloc[1:, 21], errors='coerce').reset_index(drop=True)
        estimations = pd.to_numeric(df.iloc[1:, 22], errors='coerce').reset_index(drop=True)

        mask = vol_2024.isna() & estimations.notna()
        estimation_weeks = [w for w, m in zip(weeks, mask) if m]
        estimation_vals = estimations[mask].tolist()

        last_known_index = vol_2024.last_valid_index()
        if last_known_index is not None:
            estimation_weeks = [weeks[last_known_index]] + estimation_weeks
            estimation_vals = [vol_2024[last_known_index]] + estimation_vals

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(weeks, vol_2022, label="2022/23", marker="o")
        ax.plot(weeks, vol_2023, label="2023/24", marker="o")
        ax.plot(weeks, vol_2024, label="2024/25 (actual)", marker="o", color="tab:red")

        if len(estimation_weeks) > 1:
            ax.plot(estimation_weeks, estimation_vals, label="2024/25 (estimation)", linestyle="--", marker="o", color="tab:red", alpha=0.6)

        ax.set_title("Mango Departures from South America to EU+UK (Weekly)")
        ax.set_xlabel("Week")
        ax.set_ylabel("Volume")
        ax.legend()
        ax.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        mango_chart_buffer = io.BytesIO()
        plt.savefig(mango_chart_buffer, format='png')
        st.image(mango_chart_buffer)

# Genereer rapport
if st.button("Generate Report"):
    sections = {
        "Product": product_choice,
        "Product Specification": product_spec,
        "Market Availability": market_availability,
        "Price Expectation for the Coming Weeks": price_expectation,
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
        "Lowest Market Price in Euro": f"€ {lowest_market_price:.2f}" if lowest_market_price > 0 else None,
        "Highest Market Price in Euro": f"€ {highest_market_price:.2f}" if highest_market_price > 0 else None,
    }

    report_inputs = "\n".join([f"{k}: {v}" for k, v in sections.items() if v and v != "-"])

    if extra_notes.strip():
        report_inputs = f"""IMPORTANT CONTEXT (use as general market background, not necessarily specific to the product):

{extra_notes.strip()}

---

{report_inputs}"""

    prompt = f"""
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

STRUCTURE OF THE REPORT:
1. Summary: Start with a clear overview of the current market situation based on all filled-in form fields (in order of appearance).
2. Conclusion & Advice: End with a short, strategic conclusion and professional advice to the supplier about how to proceed.

DATA TO USE:

{report_inputs}
"""

    if product_choice == "Mangoes" and mango_chart_buffer is not None:
        prompt += "\n\nVisual representation:\nMango shipping volumes from South America to the EU and UK per week.\nThe red dashed line represents estimated volumes for 2024/25 by Schrijvershof in weeks where actual data is not yet available."

    with st.spinner("Generating report..."):
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800
        )

    report = response.choices[0].message.content.strip()
    st.success("Report generated!")
    st.write(report)
    st.download_button("Download Report", report, "market_report.txt")



