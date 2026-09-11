import streamlit as st
import pandas as pd
import numpy as np

# Importeer de logica uit het originele script
from dark_pool_sim import DarkPoolMatcher, HFTPingingDetector, SmartOrderRouter

st.set_page_config(page_title="Dark Pool & HFT Simulator", layout="wide")

st.title("🏦 Dark Pool & HFT Simulator")
st.caption("Gebaseerd op de principes uit 'Dark Pools' van Scott Patterson")

# Sidebar instellingen
st.sidebar.header("Order Instellingen")
symbol = st.sidebar.text_input("Ticker Symbol", "AAPL")
total_volume = st.sidebar.number_input("Totaal Order Volume", min_value=1000, max_value=1000000, value=100000, step=5000)
max_dark_ratio = st.sidebar.slider("Maximale Dark Pool Ratio", 0.0, 1.0, 0.6)

# Tabbladen voor de functionaliteiten
tab1, tab2 = st.tabs(["1. Smart Order Router (SOR)", "2. Dark Pool Execution & HFT Detection"])

with tab1:
    st.subheader("Smart Order Router (SOR) Verdeling")
    st.write("Verdeelt de grote blokorder over meerdere Lit en Dark venues om marktimpact te beperken.")
    
    sor = SmartOrderRouter(
        dark_pools=['Crossfinder', 'UBS_PIN', 'SigmaX'],
        lit_exchanges=['NASDAQ', 'NYSE']
    )
    routing_plan = sor.route_institutional_order(total_volume=total_volume, max_dark_ratio=max_dark_ratio)
    
    # Converteren naar dataframe voor Streamlit weergave
    df_routing = pd.DataFrame(list(routing_plan.items()), columns=['Venue', 'Aandelen Volume'])
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(df_routing, use_container_width=True)
    with col2:
        st.bar_chart(df_routing.set_index('Venue'))

with tab2:
    st.subheader("Simulatie Dark Pool Execution & HFT Pinging")
    
    nbbo_midpoint = st.number_input("NBBO Midpoint Prijs ($)", value=185.50)
    institution_buy_vol = st.number_input("Institutionele Verborgen Kooporder Volume", value=20000)
    
    if st.button("Start Dark Pool Simulatie"):
        pool = DarkPoolMatcher(symbol)
        pool.add_hidden_order('BUY', volume=institution_buy_vol, limit_price=nbbo_midpoint + 0.05)
        
        hft_detector = HFTPingingDetector()
        simulated_pings = [100, 100, 100, 5000]
        
        results = []
        for vol in simulated_pings:
            pool.add_hidden_order('SELL', volume=vol, limit_price=nbbo_midpoint - 0.05)
            trades = pool.match_orders(nbbo_midpoint)
            
            for trade in trades:
                analysis = hft_detector.process_print(trade)
                results.append({
                    "Volume": trade['volume'],
                    "Prijs": f"${trade['price']:.2f}",
                    "Type": trade['type'],
                    "Signaal": analysis['signal'],
                    "Actie": analysis.get('action', 'Normaal')
                })
        
        df_results = pd.DataFrame(results)
        st.write("### Uitgevoerde Transacties (Tape Prints)")
        st.dataframe(df_results, use_container_width=True)
        
        # Check of er een waarschuwing moet komen
        if any(r['Signaal'] == 'HFT_PINGING_DETECTED' for r in results):
            st.error("🚨 **ALERT: HFT Pinging Gedetecteerd!** High-Frequency Traders proberen de grote ijsbergorder te traceren.")
