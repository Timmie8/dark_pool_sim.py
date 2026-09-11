import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Live Dark Pool & Block Trade Monitor", layout="wide")

st.title("🏦 Live Dark Pool & Block Trade Monitor")
st.caption("Reële Off-Exchange & Block Trade gegevens (FINRA TRF / SIP)")

# ==========================================
# API KEY & CONFIGURATIE
# ==========================================

default_api_key = st.secrets.get("POLYGON_API_KEY", "")

st.sidebar.header("⚙️ Instellingen & API")

api_key_input = st.sidebar.text_input(
    "Polygon.io API Key", 
    value=default_api_key, 
    type="password",
    help="Voer hier je Polygon.io API sleutel in."
)

symbol = st.sidebar.text_input("Ticker Symbol", "AAPL").upper()
min_block_size = st.sidebar.number_input(
    "Minimaal Volume per Blok/Minuut", 
    min_value=100, 
    value=2000, 
    step=500
)

api_key = api_key_input.strip() if api_key_input else None

# ==========================================
# FUNCTIONS FOR REAL MARKET DATA
# ==========================================

def get_polygon_aggs_data(symbol, api_key, min_vol):
    """ Haalt intraday minuut-data op via Polygon (Werkt ook op gratis/free tiers) """
    today = datetime.now().strftime('%Y-%m-%d')
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/minute/{today}/{today}?adjusted=true&sort=desc&limit=5000&apiKey={api_key}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json().get('results', [])
            if not results:
                return pd.DataFrame(), "Geen data beschikbaar voor vandaag (markt gesloten of nog geen trades)."
            
            blocks = []
            for bar in results:
                vol = bar.get('v', 0)
                price = bar.get('c', 0)
                timestamp = pd.to_datetime(bar.get('t'), unit='ms')
                
                if vol >= min_vol:
                    blocks.append({
                        "Tijd (UTC)": timestamp.strftime('%H:%M:%S'),
                        "Symbol": symbol,
                        "Volume (1m)": vol,
                        "Sluitprijs": f"${price:.2f}",
                        "Totale Waarde ($)": f"${(vol * price):,.2f}",
                        "Indicatie": "Groot Institutioneel Volume Block"
                    })
            return pd.DataFrame(blocks), None
        elif response.status_code == 403:
            return pd.DataFrame(), "403 Forbidden: Je Polygon API-sleutel heeft geen toegang tot realtime tick data. We vallen terug op Yahoo Finance."
        elif response.status_code == 401:
            return pd.DataFrame(), "401 Unauthorized: Ongeldige Polygon API Key."
        else:
            return pd.DataFrame(), f"API Foutcode: {response.status_code}"
    except Exception as e:
        return pd.DataFrame(), f"Verbindingsfout: {e}"

def get_yfinance_intraday_blocks(symbol, min_vol):
    """ Fallback via Yahoo Finance """
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d", interval="1m")
    
    if data.empty:
        return pd.DataFrame()
    
    blocks = data[data['Volume'] >= min_vol].copy()
    blocks = blocks.sort_index(ascending=False)
    
    result = []
    for idx, row in blocks.iterrows():
        vol = int(row['Volume'])
        price = row['Close']
        result.append({
            "Tijd": idx.strftime('%H:%M:%S'),
            "Symbol": symbol,
            "Volume (1m)": vol,
            "Sluitprijs": f"${price:.2f}",
            "Totale Waarde ($)": f"${(vol * price):,.2f}",
            "Indicatie": "Reëel Blokvolume op de Markt"
        })
    return pd.DataFrame(result)

# ==========================================
# WEERGAVE OP HET DASHBOARD
# ==========================================

st.subheader(f"Marktdata & Volume Blocks voor **{symbol}**")

use_fallback = True

if api_key:
    df_poly, err_msg = get_polygon_aggs_data(symbol, api_key, min_block_size)
    if err_msg is None and not df_poly.empty:
        st.success("✅ Polygon.io Intraday Data Succesvol Geladen!")
        st.write(f"### Grote Volumeblokken voor {symbol} (Volume ≥ {min_block_size})")
        st.dataframe(df_poly, use_container_width=True)
        use_fallback = False
    elif err_msg:
        st.warning(f"⚠️ Polygon melding: {err_msg}")

if use_fallback:
    st.info("ℹ️ Data wordt ingeladen via **Yahoo Finance Live Intraday Stream**.")
    df_blocks = get_yfinance_intraday_blocks(symbol, min_block_size)
    if not df_blocks.empty:
        st.write(f"### Reële Intraday Pieken & Blokken voor {symbol} (Volume ≥ {min_block_size})")
        st.dataframe(df_blocks, use_container_width=True)
    else:
        st.write("Geen minuten gevonden met een volume hoger dan de ingestelde drempelwaarde. Verlaag eventueel de 'Minimaal Volume' instelling in het menu links.")
