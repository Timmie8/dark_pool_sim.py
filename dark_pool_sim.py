import time
import random
import pandas as pd
import numpy as np

class DarkPoolMatcher:
    """
    Simuleert een Dark Pool orderboek zonder openbare Depth of Book (Level 2/3 data).
    Orders matchen direct op de mid-prijs als er tegenpartijen zijn.
    """
    def __init__(self, symbol):
        self.symbol = symbol
        self.buy_orders = []   # Verborgen kooporders: (volume, limit_price)
        self.sell_orders = []  # Verborgen verkooporders: (volume, limit_price)

    def add_hidden_order(self, side: str, volume: int, limit_price: float):
        if side.upper() == 'BUY':
            self.buy_orders.append({'vol': volume, 'price': limit_price})
        else:
            self.sell_orders.append({'vol': volume, 'price': limit_price})

    def match_orders(self, current_nbbo_mid: float):
        """Matches orders on the Mid-point of National Best Bid/Offer (NBBO)"""
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
    """
    Detecteert HFT 'Pinging' tactieken. HFT-algoritmes sturen kleine testorders 
    (bijv. 100 aandelen) naar Dark Pools om te 'voelen' of er een grote ijsberg/block order aanwezig is.
    """
    def __init__(self, threshold_small_order=100, cluster_window=5):
        self.threshold = threshold_small_order
        self.cluster_window = cluster_window
        self.recent_prints = []

    def process_print(self, print_data: dict):
        self.recent_prints.append(print_data)
        if len(self.recent_prints) > self.cluster_window:
            self.recent_prints.pop(0)

        # Analyseer of er sprake is van pinging
        small_trades = [p for p in self.recent_prints if p['volume'] <= self.threshold]
        
        if len(small_trades) >= 3:
            return {
                'signal': 'HFT_PINGING_DETECTED',
                'confidence': 'HIGH',
                'action': 'Instituut verbergt waarschijnlijk een grote order in deze zone.'
            }
        return {'signal': 'NORMAL_FLOW'}


class SmartOrderRouter:
    """
    Volume-Weighted SOR (Smart Order Router).
    Spreidt grote institutionele orders over Lit (transparante) en Dark markten
    om marktimpact en front-running door HFT's te voorkomen.
    """
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
# DEMO / SIMULATIE RUN
# ==========================================
if __name__ == "__main__":
    print("--- SIMULATIE: DARK POOLS & HFT MECHANICS (Scott Patterson) ---\n")

    # 1. Initieer Smart Order Router voor een blokorder van 100.000 aandelen AAPL
    sor = SmartOrderRouter(
        dark_pools=['Crossfinder', 'UBS_PIN', 'SigmaX'],
        lit_exchanges=['NASDAQ', 'NYSE']
    )
    routing_plan = sor.route_institutional_order(total_volume=100000, max_dark_ratio=0.6)
    
    print("1. SOR ROUTING VERDELING (Anti-Frontrunning):")
    for venue, vol in routing_plan.items():
        print(f"   - Venue [{venue}]: {vol:,} aandelen")
    print("-" * 50)

    # 2. Dark Pool Execution
    pool = DarkPoolMatcher("AAPL")
    nbbo_midpoint = 185.50
    
    # Institutionele koper plaatst een verborgen order in Crossfinder
    pool.add_hidden_order('BUY', volume=20000, limit_price=185.55)
    
    # HFT stuurt kleine verkoop-pings om de koper te lokaliseren
    hft_detector = HFTPingingDetector()
    
    print("\n2. SIMULATIE HFT PINGING IN DARK POOL:")
    simulated_pings = [100, 100, 100, 5000]
    
    for vol in simulated_pings:
        # HFT stuurt order
        pool.add_hidden_order('SELL', volume=vol, limit_price=185.45)
        trades = pool.match_orders(nbbo_midpoint)
        
        for trade in trades:
            analysis = hft_detector.process_print(trade)
            print(f"   [PRINT]: {trade['volume']} aandelen op ${trade['price']} | Signaal: {analysis['signal']}")
            if analysis['signal'] == 'HFT_PINGING_DETECTED':
                print(f"   >>> ALERT: {analysis['action']}")
