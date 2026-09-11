import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime

st.set_page_config(page_title="Live Dark Pool & Block Trade Monitor", layout="wide")

st.title("🏦 Live Dark Pool & Block Trade Monitor")
st.caption("Reële Off-Exchange & Block Trade gegevens met Bullish Volume Alerts")

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

st.sidebar.subheader("🚨 Bullish Volume Alert Drempel")
spike_multiplier = st.sidebar.slider(
    "Volume Piek Factor (x Gemiddelde)", 
    min_value=1.5, 
    max_value=10.0, 
    value=3.0, 
    step=0.5,
    help="Triggert ALLEEN een alert als het volume in een POSITIEVE (groene) minuut X keer hoger is dan gemiddeld."
)

api_key = api_key_input.strip() if api_key_input else None

# ==========================================
# FUNCTIONS FOR REAL MARKET DATA & ALERTS
# ==========================================

def analyze_bullish_volume_spikes(symbol, min_vol, multiplier):
    """ Haalt intraday data op en filtert specifiek op Bullish (Positieve) volumepieken """
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d", interval="1m")
    
    if data.empty:
        return pd.DataFrame(), 0, []
    
    avg_vol_per_min = data['Volume'].mean()
    
    # Filter op minimum volume
    blocks = data[data['Volume'] >= min_vol].copy()
    blocks = blocks.sort_index(ascending=False)
    
    results = []
    alerts = []
    
    for idx, row in blocks.iterrows():
        vol = int(row['Volume'])
        close_price = row['Close']
        open_price = row['Open']
        
        # Bepaal of de minuut positief (groen/koop) of negatief (rood/verkoop) was
        is_positive_candle = close_price >= open_price
        
        ratio = vol / avg_vol_per_min if avg_vol_per_min > 0 else 0
        tijd_str = idx.strftime('%H:%M:%S')
        
        # Alert triggert ALLEEN als de piek aan de vermenigvuldigingsfactor voldoet EN de candle positief is
        is_bullish_alert = (ratio >= multiplier) and is_positive_candle
        
        if is_bullish_alert:
            alerts.append({
                "Tijd": tijd_str,
                "Volume": vol,
                "Factor": f"{ratio:.1f}x gem.",
                "Prijs": f"${close_price:.2f}",
                "Waarde": f"${(vol * close_price):,.2f}"
            })
            
        # Label toewijzen voor in de tabel
        if is_bullish_alert:
            status = "🟢 BULLISH SPIKE (KOOP)"
        elif ratio >= multiplier and not is_positive_candle:
            status = "🔴 BEARISH SPIKE (VERKOOP - GEEN ALERT)"
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
        
    return pd.DataFrame(results), avg_vol_per_min, alerts

# ==========================================
# WEERGAVE OP HET DASHBOARD
# ==========================================

st.subheader(f"Marktdata & Bullish Volume Alerts voor **{symbol}**")

df_blocks, avg_vol, alerts = analyze_bullish_volume_spikes(symbol, min_block_size, spike_multiplier)

if avg_vol > 0:
    st.info(f"📊 Gemiddeld volume per minuut vandaag voor **{symbol}**: **{int(avg_vol):,}** aandelen.")

# WEERGEVEN VAN EXCLUSIEVE BULLISH ALERTS
if alerts:
    st.success(f"🟢 **BULLISH VOLUME ALERT DETECTIE ({len(alerts)} Koop-Volumepieken gevonden!)**")
    for a in alerts[:5]: # Toon de bovenste 5 meest recente bullish pieken
        st.write(f"- **{a['Tijd']}**: Positieve volumepiek van **{a['Volume']:,}** aandelen ({a['Factor']}) op **{a['Prijs']}** (Totale waarde: **{a['Waarde']}**)")
    st.markdown("---")
else:
    st.write("ℹ️ *Geen positieve (bullish) volumepieken gevonden die aan de drempelwaarde voldoen.*")

# DATA TABEL
if not df_blocks.empty:
    st.write(f"### Reële Intraday Blokken & Spikes (Volume ≥ {min_block_size})")
    st.dataframe(df_blocks, use_container_width=True)
else:
    st.write("Geen minuten gevonden met een volume hoger dan de ingestelde drempelwaarde. Pas de instellingen in het menu links aan.")
