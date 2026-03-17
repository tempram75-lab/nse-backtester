from flask import Flask, render_template, jsonify, request
import yfinance as yf
import pandas as pd
import ta
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)

STOCKS = [
    "RELIANCE.NS", "INFY.NS", "WIPRO.NS", "ICICIBANK.NS", "HDFC.NS",
    "BAJAJFINSV.NS", "ITC.NS", "AXISBANK.NS", "LT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "ASIANPAINT.NS", "HCLTECH.NS", "TATASTEEL.NS", "TECHM.NS",
    "KOTAKBANK.NS", "TITAN.NS", "HEROMOTOCO.NS", "POWERGRID.NS", "JSWSTEEL.NS",
    "BAJAJ-AUTO.NS", "NTPC.NS", "SBILIFE.NS", "ADANIPORTS.NS", "BHARTIARTL.NS",
    "SBIN.NS", "TATACONSUM.NS", "M&MFIN.NS", "ADANIGREEN.NS", "SHRIRAMFIN.NS",
    "TATAPOWER.NS", "CIPLA.NS", "DIVISLAB.NS", "HINDPETRO.NS", "EICHERMOT.NS",
    "INDIGO.NS", "GRASIM.NS", "INDUSTOWER.NS", "BRITANNIA.NS", "DRREDDY.NS",
    "LTTS.NS", "NESTLEIND.NS", "SHREECEM.NS", "UPL.NS", "DMART.NS",
    "ONGC.NS", "COALINDIA.NS", "ZEEL.NS", "INDIGOIND.NS", "GODREJCP.NS"
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stocks')
def get_stocks():
    return jsonify(STOCKS)

@app.route('/api/backtest', methods=['POST'])
def backtest():
    data = request.json
    symbol = data.get('symbol')
    strategy = data.get('strategy')
    start = data.get('start_date')
    end = data.get('end_date')
    
    try:
        print(f"Fetching {symbol} from {start} to {end}...")
        df = yf.download(symbol, start=start, end=end, progress=False)
        
        if len(df) == 0:
            return {'error': 'No data found for this symbol'}, 400
        
        # Calculate indicators
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['BB_High'] = df['Close'].rolling(20).mean() + (df['Close'].rolling(20).std() * 2)
        df['BB_Low'] = df['Close'].rolling(20).mean() - (df['Close'].rolling(20).std() * 2)
        df['VWAP'] = (df['Close'] * df['Volume']).rolling(20).mean() / df['Volume'].rolling(20).mean()
        df['MACD'] = ta.trend.macd_diff(df['Close'])
        df['Volume_MA'] = df['Volume'].rolling(20).mean()
        
        trades = []
        
        if strategy == 'rsi':
            for i in range(1, len(df)):
                rsi = df['RSI'].iloc[i]
                rsi_prev = df['RSI'].iloc[i-1]
                
                if pd.notna(rsi) and pd.notna(rsi_prev):
                    if rsi_prev <= 30 and rsi > 30:
                        trades.append({
                            'date': str(df.index[i].date()),
                            'signal': 'BUY',
                            'price': float(df['Close'].iloc[i]),
                            'reason': f'RSI Oversold → Recovery (RSI: {rsi:.1f})'
                        })
                    elif rsi_prev >= 70 and rsi < 70:
                        trades.append({
                            'date': str(df.index[i].date()),
                            'signal': 'SELL',
                            'price': float(df['Close'].iloc[i]),
                            'reason': f'RSI Overbought → Reversal (RSI: {rsi:.1f})'
                        })
        
        elif strategy == 'ma':
            for i in range(1, len(df)):
                sma20 = df['SMA20'].iloc[i]
                sma50 = df['SMA50'].iloc[i]
                sma20_prev = df['SMA20'].iloc[i-1]
                sma50_prev = df['SMA50'].iloc[i-1]
                
                if pd.notna(sma20) and pd.notna(sma50) and pd.notna(sma20_prev) and pd.notna(sma50_prev):
                    if sma20_prev <= sma50_prev and sma20 > sma50:
                        trades.append({
                            'date': str(df.index[i].date()),
                            'signal': 'BUY',
                            'price': float(df['Close'].iloc[i]),
                            'reason': 'Golden Cross (SMA20 > SMA50)'
                        })
                    elif sma20_prev >= sma50_prev and sma20 < sma50:
                        trades.append({
                            'date': str(df.index[i].date()),
                            'signal': 'SELL',
                            'price': float(df['Close'].iloc[i]),
                            'reason': 'Death Cross (SMA20 < SMA50)'
                        })
        
        elif strategy == 'bollinger':
            for i in range(1, len(df)):
                close = df['Close'].iloc[i]
                bb_high = df['BB_High'].iloc[i]
                bb_low = df['BB_Low'].iloc[i]
                
                if pd.notna(bb_high) and pd.notna(bb_low):
                    if close < bb_low:
                        trades.append({
                            'date': str(df.index[i].date()),
                            'signal': 'BUY',
                            'price': float(close),
                            'reason': 'Price Below Bollinger Lower Band'
                        })
                    elif close > bb_high:
                        trades.append({
                            'date': str(df.index[i].date()),
                            'signal': 'SELL',
                            'price': float(close),
                            'reason': 'Price Above Bollinger Upper Band'
                        })
        
        elif strategy == 'vwap':
            for i in range(1, len(df)):
                close = df['Close'].iloc[i]
                vwap = df['VWAP'].iloc[i]
                close_prev = df['Close'].iloc[i-1]
                vwap_prev = df['VWAP'].iloc[i-1]
                
                if pd.notna(vwap) and pd.notna(vwap_prev):
                    if close_prev < vwap_prev and close > vwap:
                        trades.append({
                            'date': str(df.index[i].date()),
                            'signal': 'BUY',
                            'price': float(close),
                            'reason': 'Price Above VWAP'
                        })
                    elif close_prev > vwap_prev and close < vwap:
                        trades.append({
                            'date': str(df.index[i].date()),
                            'signal': 'SELL',
                            'price': float(close),
                            'reason': 'Price Below VWAP'
                        })
        
        total_return = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100
        
        return {
            'dates': [str(d.date()) for d in df.index],
            'close': df['Close'].round(2).tolist(),
            'sma20': df['SMA20'].round(2).tolist(),
            'sma50': df['SMA50'].round(2).tolist(),
            'sma200': df['SMA200'].round(2).tolist(),
            'rsi': df['RSI'].round(2).tolist(),
            'bb_high': df['BB_High'].round(2).tolist(),
            'bb_low': df['BB_Low'].round(2).tolist(),
            'vwap': df['VWAP'].round(2).tolist(),
            'macd': df['MACD'].round(4).tolist(),
            'trades': trades[:50],
            'metrics': {
                'total_return': round(total_return, 2),
                'total_trades': len(trades),
                'start_price': round(df['Close'].iloc[0], 2),
                'end_price': round(df['Close'].iloc[-1], 2),
                'highest': round(df['Close'].max(), 2),
                'lowest': round(df['Close'].min(), 2),
                'avg_volume': round(df['Volume'].mean(), 0)
            }
        }
    
    except Exception as e:
        print(f"Error: {e}")
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
