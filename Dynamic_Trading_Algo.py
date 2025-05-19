import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
import warnings
from datetime import datetime
import os

warnings.filterwarnings("ignore")

portfolio = {}
HTML_FILE = "dashboard.html"

# Step 1: Load S&P 500 Tickers
def get_sp500_tickers():
    table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    return table[0]['Symbol'].tolist()

# Step 2: Volatility Filter
def is_high_volatility(ticker):
    try:
        data = yf.download(ticker, period='15d')
        data['returns'] = data['Close'].pct_change()
        std_dev = data['returns'].std()
        return std_dev is not None and std_dev > 0.02
    except:
        return False

# Step 3: Technical Analysis Filter
def analyze_stock(ticker):
    try:
        df = yf.download(ticker, period="6mo")
        if len(df) < 50:
            return False

        df.dropna(inplace=True)
        rsi = RSIIndicator(close=df['Close'], window=14)
        sma50 = SMAIndicator(close=df['Close'], window=50)
        sma200 = SMAIndicator(close=df['Close'], window=200)

        df['RSI'] = rsi.rsi()
        df['SMA50'] = sma50.sma_indicator()
        df['SMA200'] = sma200.sma_indicator()

        latest = df.iloc[-1]
        return latest['RSI'] < 30 and latest['SMA50'] > latest['SMA200']
    except:
        return False

# Step 4: Market Filter using VIX
def is_market_favorable():
    vix_data = yf.download("^VIX", period="5d")
    vix_level = float(vix_data['Close'].iloc[-1])  # Ensure scalar float here
    return vix_level < 20, vix_level

# Step 5: Simulate Paper Trades with Sell Condition
def paper_trade(ticker, vix_level):
    try:
        data = yf.download(ticker, period="1d", interval="1m")
        buy_price = data['Close'].iloc[-1]
        sell_threshold = 0.02 + (vix_level / 100)
        stop_loss = 0.01 + (vix_level / 100)
        buy_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        portfolio[ticker] = {
            'buy_price': buy_price,
            'sell_threshold': sell_threshold,
            'stop_loss': stop_loss,
            'buy_time': buy_time
        }
        print(f"[PAPER TRADE] Buying {ticker} at ${buy_price:.2f} | Target +{sell_threshold*100:.1f}%, Stop -{stop_loss*100:.1f}%")
        update_dashboard_html(ticker, buy_price, buy_time, sell_threshold, stop_loss)
    except:
        print(f"[ERROR] Could not simulate buy for {ticker}")

# Step 6: Generate/Update dashboard.html
def update_dashboard_html(ticker, price, time, target, stop):
    row = f"<tr><td>{ticker}</td><td>${price:.2f}</td><td>{time}</td><td>{target*100:.2f}%</td><td>{stop*100:.2f}%</td></tr>"
    if not os.path.exists(HTML_FILE):
        with open(HTML_FILE, 'w') as f:
            f.write("""
            <html><head><title>Paper Trades Dashboard</title>
            <style>table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid #ccc; padding: 8px; }</style>
            </head><body><h2>Paper Trades</h2>
            <table><tr><th>Ticker</th><th>Buy Price</th><th>Buy Time</th><th>Target %</th><th>Stop %</th></tr>
            """ + row + "</table></body></html>")
    else:
        with open(HTML_FILE, 'r') as f:
            html = f.read()
        insert_pos = html.find('</table>')
        updated_html = html[:insert_pos] + row + html[insert_pos:]
        with open(HTML_FILE, 'w') as f:
            f.write(updated_html)

# Step 7: Run Screener
def run_trading_algorithm():
    print("Scanning market...")
    market_ok, vix_level = is_market_favorable()
    if not market_ok:
        print("Market too volatile today. No trades.")
        return

    tickers = get_sp500_tickers()
    print(f"Loaded {len(tickers)} tickers from S&P 500")

    candidates = [t for t in tickers if is_high_volatility(t)]
    print(f"{len(candidates)} tickers passed volatility filter")

    signals = []
    for t in candidates:
        if analyze_stock(t):
            signals.append(t)

    if signals:
        print("Buy signals for:", signals)
        for signal in signals:
            paper_trade(signal, vix_level)
    else:
        print("No valid buy signals today.")

    if portfolio:
        print("\nCurrent Paper Portfolio:")
        for symbol, trade in portfolio.items():
            print(f"{symbol}: Bought at ${trade['buy_price']:.2f} on {trade['buy_time']} | Target +{trade['sell_threshold']*100:.1f}%, Stop -{trade['stop_loss']*100:.1f}%")

if __name__ == "__main__":
    run_trading_algorithm()
