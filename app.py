import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime

st.set_page_config(page_title="Live Dark Pool & Block Trade Monitor", layout="wide")

st.title("🏦 Live Dark Pool & Block Trade Monitor")
st.caption("Reële Off-Exchange & Block Trade gegevens (FINRA TRF / SIP / Yahoo Intraday)")

# ==========================================
# API KEY & CONFIGURATIE
# ==========================================

default_api_key = st.secrets.get("POLYGON_API_KEY", "")

st.sidebar.header("⚙️ Instellingen & Alerts")

api_key_input = st.sidebar.text_input(
    "Polygon.io API Key (Optioneel)", 
    value=default_api_key, 
    type="password"
)

symbol = st.sidebar.text_input("Ticker Symbol", "NVDA").upper()
min_block_size = st.sidebar.number_input(
    "Minimaal Volume per Blok", 
    min_value=100, 
    value=2000, 
    step=500
)

st.sidebar.subheader("🚨 Volume Spike Alert Drempel")
spike_multiplier = st.sidebar.slider(
    "Volume Piek Factor (x Gemiddelde)", 
    min_value=1.5, 
    max_value=10.0, 
    value=3.0, 
    step=0.5,
    help="Triggert een alert als het volume in 1 minuut X keer hoger is dan het daggemiddelde per minuut."
)

api_key = api_key_input.strip() if api_key_input else None

# ==========================================
# FUNCTIONS FOR REAL MARKET DATA & ALERTS
# ==========================================

def analyze_yfinance_blocks_and_spikes(symbol, min_vol, multiplier):
    """ Haalt live intraday data op via Yahoo Finance en berekent volume-spikes """
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d", interval="1m")
    
    if data.empty:
        return pd.DataFrame(), 0, []
    
    # Gemiddeld volume per minuut berekenen
    avg_vol_per_min = data['Volume'].mean()
    
    # Filter op minimum volume
    blocks = data[data['Volume'] >= min_vol].copy()
    blocks = blocks.sort_index(ascending=False)
    
    results = []
    alerts = []
    
    for idx, row in blocks.iterrows():
        vol = int(row['Volume'])
        price = row['Close']
        ratio = vol / avg_vol_per_min if avg_vol_per_min > 0 else 0
        tijd_str = idx.strftime('%H:%M:%S')
        
        is_spike = ratio >= multiplier
        
        if is_spike:
            alerts.append({
                "Tijd": tijd_str,
                "Volume": vol,
                "Factor": f"{ratio:.1f}x gem.",
                "Prijs": f"${price:.2f}",
                "Waarde": f"${(vol * price):,.2f}"
            })
            
        results.append({
            "Tijd": tijd_str,
            "Symbol": symbol,
            "Volume (1m)": vol,
            "vs Gemiddeld": f"{ratio:.1f}x",
            "Sluitprijs": f"${price:.2f}",
            "Totale Waarde ($)": f"${(vol * price):,.2f}",
            "Status": "🔥 VOLUME SPIKE" if is_spike else "Normaal Blok"
        })
        
    return pd.DataFrame(results), avg_vol_per_min, alerts

# ==========================================
# WEERGAVE OP HET DASHBOARD
# ==========================================

st.subheader(f"Marktdata & Volume Alerts voor **{symbol}**")

df_blocks, avg_vol, alerts = analyze_yfinance_blocks_and_spikes(symbol, min_block_size, spike_multiplier)

if avg_vol > 0:
    st.info(f"📊 Gemiddeld volume per minuut vandaag voor **{symbol}**: **{int(avg_vol):,}** aandelen.")

# WEERGEVEN VAN ALERTS
if alerts:
    st.error(f"🚨 **ALERT DETECTIE ({len(alerts)} Volumepieken gevonden!)**")
    for a in alerts[:3]: # Toon de bovenste 3 meest recente pieken
        st.write(f"- **{a['Tijd']}**: Piek van **{a['Volume']:,}** aandelen ({a['Factor']}) op **{a['Prijs']}** (Totale waarde: **{a['Waarde']}**)")
    st.markdown("---")

# DATA TABEL
if not df_blocks.empty:
    st.write(f"### Reële Intraday Blokken & Spikes (Volume ≥ {min_block_size})")
    st.dataframe(df_blocks, use_container_width=True)
else:
    st.write("Geen minuten gevonden met een volume hoger dan de ingestelde drempelwaarde. Pas de instellingen in het menu links aan.")
