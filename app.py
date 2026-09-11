import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime

st.set_page_config(page_title="Live Dark Pool & Block Trade Monitor", layout="wide")

st.title("🏦 Live Dark Pool & Block Trade Monitor")
st.caption("Reële Off-Exchange & Block Trade gegevens met Bullish & Bearish Volume Alerts")

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

st.sidebar.subheader("🚨 Volume Alert Drempels")
spike_multiplier = st.sidebar.slider(
    "Volume Piek Factor (x Gemiddelde)", 
    min_value=1.5, 
    max_value=10.0, 
    value=3.0, 
    step=0.5,
    help="Triggert een alert als het volume in 1 minuut X keer hoger is dan gemiddeld."
)

api_key = api_key_input.strip() if api_key_input else None

# ==========================================
# FUNCTIONS FOR REAL MARKET DATA & ALERTS
# ==========================================

def analyze_volume_spikes(symbol, min_vol, multiplier):
    """ Haalt intraday data op en filtert op zowel Bullish als Bearish volumepieken """
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d", interval="1m")
    
    if data.empty:
        return pd.DataFrame(), 0, [], []
    
    avg_vol_per_min = data['Volume'].mean()
    
    # Filter op minimum volume
    blocks = data[data['Volume'] >= min_vol].copy()
    blocks = blocks.sort_index(ascending=False)
    
    results = []
    bullish_alerts = []
    bearish_alerts = []
    
    for idx, row in blocks.iterrows():
        vol = int(row['Volume'])
        close_price = row['Close']
        open_price = row['Open']
        
        # Bepaal of de candle positief (groen/koop) of negatief (rood/verkoop) is
        is_positive_candle = close_price >= open_price
        
        ratio = vol / avg_vol_per_min if avg_vol_per_min > 0 else 0
        tijd_str = idx.strftime('%H:%M:%S')
        
        is_spike = ratio >= multiplier
        
        alert_item = {
            "Tijd": tijd_str,
            "Volume": vol,
            "Factor": f"{ratio:.1f}x gem.",
            "Prijs": f"${close_price:.2f}",
            "Waarde": f"${(vol * close_price):,.2f}"
        }
        
        # Alerts verdelen per categorie
        if is_spike and is_positive_candle:
            bullish_alerts.append(alert_item)
            status = "🟢 BULLISH SPIKE (KOOP)"
        elif is_spike and not is_positive_candle:
            bearish_alerts.append(alert_item)
            status = "🔴 BEARISH SPIKE (VERKOOP)"
        else:
            status = "🟢 Positief Blok" if is_positive_candle else "🔴 Negatief Blok"
            
        results.append({
            "Tijd": tijd_str,
            "Symbol": symbol,
            "Richting": "🟢 KOOP (Groen)" if is_positive_candle else "🔴 VERKOOP (Rood)",
            "Volume (1m)": vol,
            "vs Gemiddeld": f"{ratio:.1f}x",
            "Sluitprijs": f"${close_price:.2f}",
            "Totale Waarde ($)": f"${(vol * close_price):,.2f}",
            "Status": status
        })
        
    return pd.DataFrame(results), avg_vol_per_min, bullish_alerts, bearish_alerts

# ==========================================
# WEERGAVE OP HET DASHBOARD
# ==========================================

st.subheader(f"Marktdata & Volume Alerts voor **{symbol}**")

df_blocks, avg_vol, bull_alerts, bear_alerts = analyze_volume_spikes(symbol, min_block_size, spike_multiplier)

if avg_vol > 0:
    st.info(f"📊 Gemiddeld volume per minuut vandaag voor **{symbol}**: **{int(avg_vol):,}** aandelen.")

# WEERGEVEN VAN ALERTS IN COLUMNS
col_bull, col_bear = st.columns(2)

with col_bull:
    if bull_alerts:
        st.success(f"🟢 **BULLISH KOOP ALERTS ({len(bull_alerts)})**")
        for a in bull_alerts[:3]:
            st.write(f"- **{a['Tijd']}**: Piek van **{a['Volume']:,}** aandelen ({a['Factor']}) op **{a['Prijs']}** (Waarde: **{a['Waarde']}**)")
    else:
        st.write("ℹ️ *Geen Bullish pieken gevonden.*")

with col_bear:
    if bear_alerts:
        st.error(f"🔴 **BEARISH VERKOOP ALERTS ({len(bear_alerts)})**")
        for a in bear_alerts[:3]:
            st.write(f"- **{a['Tijd']}**: Piek van **{a['Volume']:,}** aandelen ({a['Factor']}) op **{a['Prijs']}** (Waarde: **{a['Waarde']}**)")
    else:
        st.write("ℹ️ *Geen Bearish pieken gevonden.*")

st.markdown("---")

# DATA TABEL
if not df_blocks.empty:
    st.write(f"### Reële Intraday Blokken & Spikes (Volume ≥ {min_block_size})")
    st.dataframe(df_blocks, use_container_width=True)
else:
    st.write("Geen minuten gevonden met een volume hoger dan de ingestelde drempelwaarde. Pas de instellingen in het menu links aan.")
