import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ==========================================
# 1. DARK POOL & HFT LOGICA
# ==========================================
class DarkPoolMatcher:
    def __init__(self, symbol):
        self.symbol = symbol
        self.buy_orders = []
        self.sell_orders = []

    def add_hidden_order(self, side: str, volume: int, limit_price: float):
        if side.upper() == 'BUY':
            self.buy_orders.append({'vol': volume, 'price': limit_price})
        else:
            self.sell_orders.append({'vol': volume, 'price': limit_price})

    def match_orders(self, current_nbbo_mid: float):
        trades = []
        for b in list(self.buy_orders):
            for s in list(self.sell_orders):
                if b['price'] >= current_nbbo_mid >= s['price']:
                    matched_vol = min(b['vol'], s['vol'])
                    trades.append({
                        'symbol': self.symbol,
                        'price': current_nbbo_mid,
                        'volume': matched_vol,
                        'type': 'DARK_MIDPOINT'
                    })
                    b['vol'] -= matched_vol
                    s['vol'] -= matched_vol
                    if b['vol'] == 0: self.buy_orders.remove(b)
                    if s['vol'] == 0: self.sell_orders.remove(s)
                    break
        return trades

class HFTPingingDetector:
    def __init__(self, threshold_small_order=100, cluster_window=5):
        self.threshold = threshold_small_order
        self.cluster_window = cluster_window
        self.recent_prints = []

    def process_print(self, print_data: dict):
        self.recent_prints.append(print_data)
        if len(self.recent_prints) > self.cluster_window:
            self.recent_prints.pop(0)

        small_trades = [p for p in self.recent_prints if p['volume'] <= self.threshold]
        if len(small_trades) >= 3:
            return {
                'signal': 'HFT_PINGING_DETECTED',
                'confidence': 'HIGH',
                'action': 'Instituut verbergt waarschijnlijk een grote order in deze zone.'
            }
        return {'signal': 'NORMAL_FLOW'}

class SmartOrderRouter:
    def __init__(self, dark_pools: list, lit_exchanges: list):
        self.dark_pools = dark_pools
        self.lit_exchanges = lit_exchanges

    def route_institutional_order(self, total_volume: int, max_dark_ratio=0.7):
        dark_volume = int(total_volume * max_dark_ratio)
        lit_volume = total_volume - dark_volume

        slice_dark = dark_volume // len(self.dark_pools) if self.dark_pools else 0
        slice_lit = lit_volume // len(self.lit_exchanges) if self.lit_exchanges else 0

        routing_table = {}
        for dp in self.dark_pools:
            routing_table[dp] = slice_dark
        for lit in self.lit_exchanges:
            routing_table[lit] = slice_lit

        return routing_table

# ==========================================
# 2. STREAMLIT INTERFACE MET LIVE YFINANCE
# ==========================================
st.set_page_config(page_title="Dark Pool & HFT Live Simulator", layout="wide")

st.title("🏦 Live Dark Pool & HFT Simulator")
st.caption("Aangedreven door `yfinance` live marktdata & geïnspireerd door 'Dark Pools' van Scott Patterson")

# Sidebar instellingen
st.sidebar.header("Markt & Order Instellingen")
symbol = st.sidebar.text_input("Ticker Symbol", "AAPL").upper()

# Ophalen van live marktdata via yfinance
@st.cache_data(ttl=30)
def fetch_live_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(period="1d", interval="1m")
        if data.empty:
            return None, None
        last_price = float(data['Close'].iloc[-1])
        avg_volume = int(data['Volume'].mean())
        return last_price, avg_volume
    except Exception as e:
        return None, None

live_price, live_vol = fetch_live_data(symbol)

if live_price is not None:
    st.sidebar.success(f"Live Koers **{symbol}**: ${live_price:.2f}")
else:
    st.sidebar.warning(f"Kon geen live data ophalen voor {symbol}. Default $185.50 gebruikt.")
    live_price = 185.50

total_volume = st.sidebar.number_input("Totaal Order Volume", min_value=1000, max_value=1000000, value=100000, step=5000)
max_dark_ratio = st.sidebar.slider("Maximale Dark Pool Ratio", 0.0, 1.0, 0.6)

tab1, tab2 = st.tabs(["1. Smart Order Router (SOR)", "2. Live Dark Pool Execution & HFT Detection"])

with tab1:
    st.subheader(f"Smart Order Router (SOR) Verdeling voor {symbol}")
    st.write("Verdeelt de grote blokorder over meerdere Lit en Dark venues om marktimpact te beperken.")
    
    sor = SmartOrderRouter(
        dark_pools=['Crossfinder', 'UBS_PIN', 'SigmaX'],
        lit_exchanges=['NASDAQ', 'NYSE']
    )
    routing_plan = sor.route_institutional_order(total_volume=total_volume, max_dark_ratio=max_dark_ratio)
    
    df_routing = pd.DataFrame(list(routing_plan.items()), columns=['Venue', 'Aandelen Volume'])
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(df_routing, use_container_width=True)
    with col2:
        st.bar_chart(df_routing.set_index('Venue'))

with tab2:
    st.subheader(f"Simulatie Dark Pool Execution & HFT Pinging voor {symbol}")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        nbbo_midpoint = st.number_input("Huidige Live NBBO Midpoint ($)", value=round(live_price, 2))
    with col_input2:
        institution_buy_vol = st.number_input("Institutionele Verborgen Kooporder Volume", value=20000)
    
    if st.button("Start Live Dark Pool Simulatie"):
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
                    "Symbol": trade['symbol'],
                    "Volume": trade['volume'],
                    "Prijs": f"${trade['price']:.2f}",
                    "Type": trade['type'],
                    "Signaal": analysis['signal'],
                    "Actie": analysis.get('action', 'Normaal')
                })
        
        df_results = pd.DataFrame(results)
        st.write("### Uitgevoerde Transacties (Dark Pool Tape Prints)")
        st.dataframe(df_results, use_container_width=True)
        
        if any(r['Signaal'] == 'HFT_PINGING_DETECTED' for r in results):
            st.error("🚨 **ALERT: HFT Pinging Gedetecteerd!** High-Frequency Traders proberen de grote ijsbergorder te traceren.")
