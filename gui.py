import streamlit as st
import json
import openai
from config import OPENAI_API_KEY

openai.api_key = st.secrets["OPENAI_API_KEY"]

# Load dropdown choices from config file
with open('./config/options.json', 'r') as file:
    opties = json.load(file)

st.title("Market Report Generator")

# Dropdown menus from JSON configuration
product_choice = st.selectbox("Product", opties["producten"])
product_spec = st.selectbox("Product Specification", opties["product_specificatie"])
market_availability = st.selectbox("Market Availability", opties["markt_beschikbaarheid"])
price_expectation = st.selectbox("Price Expectation for the Coming Weeks", opties["prijs_verwachting"])
price_indication = st.selectbox("Price Indication", opties["prijs_aanduiding"])
arrival_forecast = st.selectbox("Arrival Forecast", opties["aankomst_vooruitzicht"])
origin_change = st.selectbox("Origin Change", opties["herkomst_verandering"])
shipping_advice = st.selectbox("Continue Shipping Advised", opties["verscheping_continuiteit_advies"])
market_sentiment = st.selectbox("Market Sentiment", opties["markt_sentiment"])
market_quality = st.selectbox("Market Quality", opties["markt_kwaliteit"])
consumption = st.selectbox("Consumption", opties["consumptie"])
size_preference = st.selectbox("Size Preference", opties["maat_voorkeur"])

# Free input price fields
lowest_market_price = st.number_input("Lowest Market Price in Euro (€)", min_value=0.0, step=0.1, format="%.2f")
highest_market_price = st.number_input("Highest Market Price in Euro (€)", min_value=0.0, step=0.1, format="%.2f")

# Generate report button
if st.button("Generate Report"):
    prompt = f"""
    You are writing a professional, business-like market report in English for our overseas producers and suppliers. For context: we are a dedicated import/export company based in Holland, selling overseas fruits across Europe to service providers and retailers with minimum volumes on a pallet basis. These reports inform our direct producers about current and expected market conditions in Europe. 

    Create a clear and concise market report with the following data:

    Product: {product_choice}
    Product Specification: {product_spec}
    Market Availability: {market_availability}
    Price Expectation for the Coming Weeks: {price_expectation}
    Price Indication: {price_indication}
    Arrival Forecast: {arrival_forecast}
    Origin Change: {origin_change}
    Continue Shipping Advised: {shipping_advice}
    Market Sentiment: {market_sentiment}
    Market Quality: {market_quality}
    Consumption: {consumption}
    Size Preference: {size_preference}
    Lowest Market Price in Euro: € {lowest_market_price:.2f}
    Highest Market Price in Euro: € {highest_market_price:.2f}

    Conclude the report with clear, professional, and actionable insights relevant to producers, without explicitly mentioning our company's role or location.
    """

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

    # Optionally download the report
    st.download_button("Download Report", report, "market_report.txt")
