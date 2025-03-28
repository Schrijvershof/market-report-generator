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
price_indication = st.selectbox("Price Indication", opties["prijs_aanduiding"])
arrival_forecast = st.selectbox("Arrival Forecast", opties["aankomst_vooruitzicht"])
origin_change = st.selectbox("Origin Change", opties["herkomst_verandering"])
shipping_advice = st.selectbox("Continue Shipping Advised", opties["verscheping_continuiteit_advies"])
market_sentiment = st.selectbox("Market Sentiment", opties["markt_sentiment"])
market_quality = st.selectbox("Market Quality", opties["markt_kwaliteit"])
consumption = st.selectbox("Consumption", opties["consumptie"])
size_preference = st.selectbox("Size Preference", opties["maat_voorkeur"])

lowest_market_price = st.number_input("Lowest Market Price in Euro (€)", min_value=0.0, step=0.1, format="%.2f")
highest_market_price = st.number_input("Highest Market Price in Euro (€)", min_value=0.0, step=0.1, format="%.2f")

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
    prompt = f"""
You are writing a professional, business-like market report in English for our overseas producers and suppliers. We are an import/export company based in Holland, selling fruits across Europe to service providers and retailers.

Generate a clear and accurate market report using only the provided data. If a field is not filled in (indicated by '-' or empty), explicitly state "Not provided" in the report. Never invent or assume any missing data.

Here is the provided data:

Product: {product_choice if product_choice != '-' else 'Not provided'}
Product Specification: {product_spec if product_spec != '-' else 'Not provided'}
Market Availability: {market_availability if market_availability != '-' else 'Not provided'}
Price Expectation for the Coming Weeks: {price_expectation if price_expectation != '-' else 'Not provided'}
Price Indication: {price_indication if price_indication != '-' else 'Not provided'}
Arrival Forecast: {arrival_forecast if arrival_forecast != '-' else 'Not provided'}
Origin Change: {origin_change if origin_change != '-' else 'Not provided'}
Continue Shipping Advised: {shipping_advice if shipping_advice != '-' else 'Not provided'}
Market Sentiment: {market_sentiment if market_sentiment != '-' else 'Not provided'}
Market Quality: {market_quality if market_quality != '-' else 'Not provided'}
Consumption: {consumption if consumption != '-' else 'Not provided'}
Size Preference: {size_preference if size_preference != '-' else 'Not provided'}
Lowest Market Price in Euro: € {lowest_market_price if lowest_market_price > 0 else 'Not provided'}
Highest Market Price in Euro: € {highest_market_price if highest_market_price > 0 else 'Not provided'}

Conclude the report using only the provided data, clearly indicating if certain essential information was not provided. Provide professional and actionable insights without inventing or assuming any missing data.
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

