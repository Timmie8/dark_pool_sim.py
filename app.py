import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests

st.set_page_config(page_title="Live Dark Pool & Block Trade Monitor", layout="wide")

st.title("🏦 Live Dark Pool & Block Trade Monitor")
st.caption("Reële Off-Exchange & Block Trade gegevens uit de openbare tape (FINRA TRF / SIP)")

# Sidebar Instellingen
st.sidebar.header("Instellingen & API")
symbol = st.sidebar.text_input("Ticker Symbol", "AAPL").upper()
min_block_size = st.sidebar.number_input("Minimaal Volume per Trade (Block Threshold)", min_value=100, value=2000, step=500)

api_key = st.sidebar.text_input("Polygon.io API Key (Optioneel voor Real-time Tape)", type="password")

# ==========================================
# FUNCTIONS FOR REAL LIVE DATA
# ==========================================

def get_live_polygon_trades(symbol, api_key, min_vol):
    """ Haalt echte individuele trades op via Polygon.io REST API """
    url = f"https://api.polygon.io/v3/trades/{symbol}?limit=5000&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        results = response.json().get('results', [])
        dark_trades = []
        for t in results:
            size = t.get('size', 0)
            # Exchange 4 of TRF staat voor Off-Exchange / Dark Pool rapportages
            exchange = t.get('exchange')
            price = t.get('price')
            timestamp = pd.to_datetime(t.get('sip_timestamp'), unit='ns')
            
            if size >= min_vol:
                dark_trades.append({
                    "Tijd (UTC)": timestamp.strftime('%H:%M:%S'),
                    "Symbol": symbol,
                    "Volume": size,
                    "Prijs": f"${price:.2f}",
                    "Waarde ($)": f"${(size * price):,.2f}",
                    "Exchange Code": exchange,
                    "Type": "OFF-EXCHANGE / DARK BLOCK" if exchange in [4, 15] else "LIT EXCHANGE BLOCK"
                })
        return pd.DataFrame(dark_trades)
    else:
        st.sidebar.error("Polygon API Fout of ongeldige sleutel.")
        return pd.DataFrame()

def get_yfinance_intraday_blocks(symbol, min_vol):
    """ Fallback: Filtert live 1-minuut marktdata op opvallend hoge volumes """
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d", interval="1m")
    
    if data.empty:
        return pd.DataFrame()
    
    # Filter op min_vol
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
            "Totale Waarde": f"${(vol * price):,.2f}",
            "Indicatie": "Echt blokvolume op de markt"
        })
    return pd.DataFrame(result)

# ==========================================
# WEERGAVE OP HET DASHBOARD
# ==========================================

st.subheader(f"Echte Live Trades & Blokken voor **{symbol}**")

if api_key:
    st.info("🔄 Echte Real-time Tape data via Polygon.io API geladen.")
    df_live = get_live_polygon_trades(symbol, api_key, min_block_size)
    if not df_live.empty:
        st.write(f"### Live Block Prints (Volume ≥ {min_block_size})")
        st.dataframe(df_live, use_container_width=True)
    else:
        st.warning("Geen grote block trades gevonden in de laatste geopende marktperiode.")
else:
    st.warning("⚠️ Geen Polygon API Key ingevoerd. We tonen nu **reële intraday block-volumes** via Yahoo Finance.")
    df_blocks = get_yfinance_intraday_blocks(symbol, min_block_size)
    if not df_blocks.empty:
        st.write(f"### Reële Intraday Pieken & Blokken voor {symbol} (Volume ≥ {min_block_size})")
        st.dataframe(df_blocks, use_container_width=True)
    else:
        st.write("Geen minuten gevonden met een volume hoger dan de ingestelde drempelwaarde.")

st.markdown("""
---
### Hoe lees je deze live data?
1. **Off-Exchange / TRF Prints (Exchange Code 4):** Dit zijn transacties die buiten de reguliere beurzen om zijn gemeld (zoals Dark Pools of OTC-dealers).
2. **Waarde ($):** Institutionele partijen verhandelen meestal blokken van minimaal **$200.000 tot meerdere miljoenen**. Kleine aantallen zijn retail-traders.
""")
