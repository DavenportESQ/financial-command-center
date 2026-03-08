"""
Financial Command Center
A professional financial dashboard built with Dash, Plotly, and yfinance.
"""
import io
import xml.etree.ElementTree as ET
import dash
from dash import dcc, html, Input, Output, State, ctx, no_update, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import time
import os
import requests
# fredapi is optional — install with: pip install fredapi
try:
    from fredapi import Fred as _FredLib
    _FREDAPI_AVAILABLE = True
except ImportError:
    _FREDAPI_AVAILABLE = False
# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
INDICES = {
    "^GSPC": "S&P 500",
    "^DJI": "Dow Jones",
    "^IXIC": "NASDAQ",
    "^RUT": "Russell 2000",
    "^VIX": "VIX",
}
FUTURES = {
    "ES=F":  "S&P 500 Futures",
    "NQ=F":  "NASDAQ Futures",
    "YM=F":  "Dow Futures",
    "RTY=F": "Russell Futures",
    "ZN=F":  "10yr T-Note Futures",
    "GC=F":  "Gold Futures",
    "CL=F":  "Crude Oil Futures",
}
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLE": "Energy",
    "XLY": "Consumer Disc.",
    "XLP": "Consumer Staples",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLC": "Communication",
}
SECTOR_STOCKS = {
    "XLK":  ["AAPL","MSFT","NVDA","AVGO","ORCL","CRM","AMD","QCOM","AMAT","INTC"],
    "XLF":  ["BRK-B","JPM","V","MA","BAC","WFC","GS","MS","BLK","AXP"],
    "XLV":  ["LLY","UNH","JNJ","ABBV","MRK","TMO","ABT","DHR","PFE","AMGN"],
    "XLE":  ["XOM","CVX","COP","SLB","EOG","PSX","MPC","OXY","PXD","HES"],
    "XLY":  ["AMZN","TSLA","HD","MCD","NKE","LOW","SBUX","TJX","BKNG","CMG"],
    "XLP":  ["PG","KO","PEP","COST","WMT","PM","MO","CL","MDLZ","EL"],
    "XLI":  ["GE","RTX","HON","UNP","UPS","CAT","LMT","DE","BA","MMM"],
    "XLB":  ["LIN","APD","SHW","ECL","NEM","FCX","NUE","ALB","CF","IP"],
    "XLRE": ["PLD","AMT","EQIX","CCI","PSA","SPG","O","DLR","WELL","AVB"],
    "XLU":  ["NEE","SO","DUK","SRE","AEP","D","EXC","PCG","WEC","ED"],
    "XLC":  ["META","GOOGL","NFLX","DIS","CMCSA","T","VZ","CHTR","EA","OMC"],
}
TIMEFRAMES = {
    "1D": ("1d", "5m"),
    "5D": ("5d", "15m"),
    "1M": ("1mo", "1h"),
    "3M": ("3mo", "1d"),
    "6M": ("6mo", "1d"),
    "1Y": ("1y", "1d"),
    "5Y": ("5y", "1wk"),
}
# ── Macro Dashboard Constants ─────────────────────────────────────────────────
MACRO_TICKERS = {
    "USO":       {"label": "USO (Oil)",        "color": "#EF4444"},
    "GLD":       {"label": "GLD (Gold)",        "color": "#F59E0B"},
    "HYG":       {"label": "HYG (High Yield)", "color": "#10B981"},
    "LQD":       {"label": "LQD (Inv. Grade)", "color": "#3B82F6"},
    "DX-Y.NYB":  {"label": "DXY (Dollar)",     "color": "#0EA5E9"},
}
TREASURY_TICKER = "^TNX"
# ── FRED API ──────────────────────────────────────────────────────────────────
FRED_API_KEY_FALLBACK = ""
FRED_HY_OAS  = "BAMLH0A0HYM2"
FRED_IG_OAS  = "BAMLC0A0CM"
def _get_fred():
    if not _FREDAPI_AVAILABLE:
        return None
    key = os.environ.get("FRED_API_KEY") or FRED_API_KEY_FALLBACK
    if not key:
        return None
    return _FredLib(api_key=key)
BDC_TICKERS = ["ARCC", "FSK", "OBDC", "GBDC", "BXSL"]
# ── Insider Alerts ────────────────────────────────────────────────────────────
WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "BAC", "TSLA", "BRK-B"]
INSIDER_MIN_VALUE = 10_000   # minimum $ to show a purchase
# ── Market Overview extras ────────────────────────────────────────────────────
BOND_ETFS = {
    "AGG":  "US Agg Bond",
    "TLT":  "20yr+ Treasury",
    "IEF":  "7-10yr Treasury",
    "HYG":  "High Yield Corp",
    "LQD":  "IG Corporate",
}
TREASURY_YIELDS = {
    "^IRX": "3M T-Bill",
    "^FVX": "5yr Yield",
    "^TNX": "10yr Yield",
    "^TYX": "30yr Yield",
}
COMMODITIES = {
    "GC=F": "Gold ($/oz)",
    "SI=F": "Silver ($/oz)",
    "CL=F": "Crude Oil (WTI)",
    "HG=F": "Copper ($/lb)",
    "NG=F": "Nat. Gas",
}
CURRENCIES = {
    "DX-Y.NYB": "DXY Dollar",
    "EURUSD=X": "EUR / USD",
    "GBPUSD=X": "GBP / USD",
    "USDJPY=X": "USD / JPY",
}
# ── COT Markets ───────────────────────────────────────────────────────────────
COT_MARKETS = [
    {"filter": "GOLD",            "label": "Gold",         "color": "#F59E0B"},
    {"filter": "SILVER",          "label": "Silver",       "color": "#94a3b8"},
    {"filter": "CRUDE OIL, LIG",  "label": "Crude Oil",    "color": "#EF4444"},
    {"filter": "E-MINI S&P 500",  "label": "E-Mini S&P",   "color": "#10B981"},
    {"filter": "10-YEAR U.S. T",  "label": "10yr T-Note",  "color": "#63b3ed"},
    {"filter": "EURO FX",         "label": "Euro FX",      "color": "#a78bfa"},
    {"filter": "JAPANESE YEN",    "label": "Yen",          "color": "#0EA5E9"},
    {"filter": "BITCOIN",         "label": "Bitcoin",      "color": "#F97316"},
    {"filter": "NATURAL GAS",     "label": "Nat. Gas",     "color": "#34D399"},
]
# ── 13F Famous Funds ──────────────────────────────────────────────────────────
FAMOUS_FUNDS = {
    "Berkshire Hathaway":       "0001067983",
    "Pershing Square (Ackman)": "0001336528",
    "Bridgewater Associates":   "0001350694",
    "Renaissance Technologies": "0001037389",
    "Third Point (Loeb)":       "0001040570",
    "Appaloosa (Tepper)":       "0001060349",
}
# ── ETF Flow Tracker ──────────────────────────────────────────────────────────
FLOW_ETFS = {
    "SPY": ("S&P 500",         "Equity"),
    "QQQ": ("NASDAQ 100",      "Equity"),
    "IWM": ("Russell 2000",    "Equity"),
    "DIA": ("Dow Jones",       "Equity"),
    "GLD": ("Gold",            "Commodity"),
    "SLV": ("Silver",          "Commodity"),
    "TLT": ("20yr+ Treasury",  "Bond"),
    "IEF": ("7-10yr Treasury", "Bond"),
    "HYG": ("High Yield",      "Bond"),
    "LQD": ("IG Corporate",    "Bond"),
    "VXX": ("VIX ST Futures",  "Volatility"),
    "XLK": ("Technology",      "Sector"),
    "XLE": ("Energy",          "Sector"),
    "XLF": ("Financials",      "Sector"),
    "XLV": ("Health Care",     "Sector"),
}
# ── Options Flow ──────────────────────────────────────────────────────────────
OPTIONS_MIN_VOL        = 100   # minimum contract volume to surface
OPTIONS_VOL_OI_RATIO   = 0.5   # vol/OI threshold for "unusual" flag
OPTIONS_MAX_EXPIRATIONS = 4    # look-ahead expiration dates per ticker
SIGNAL_MATRIX = [
    {"DXY": "↑", "GLD": "↓", "USO": "↓", "read": "Risk-off / Demand destruction working → Bond Bull ✅",  "alert": "success"},
    {"DXY": "↑", "GLD": "↑", "USO": "↑", "read": "Stagflation + Dollar credibility stress ⚠️",            "alert": "warning"},
    {"DXY": "↓", "GLD": "↑", "USO": "↑", "read": "Dollar credibility crisis → Worst case for IG 🔴",      "alert": "danger"},
    {"DXY": "↓", "GLD": "↓", "USO": "↓", "read": "Hard landing / Flight to Treasuries → Cuts coming ✅",  "alert": "success"},
]
STRESS_SCENARIOS = [
    {"scenario": "Demand destruction / soft landing",       "tenyr": "3.75%",     "spread": "+20–40bps",   "net": "+2% to +3%",  "net_color": "#10B981"},
    {"scenario": "Demand destruction / hard landing",       "tenyr": "3.25–3.50%","spread": "+75–100bps",  "net": "Roughly flat", "net_color": "#F59E0B"},
    {"scenario": "Supply shock overwhelms demand destruction","tenyr": "4.25–4.50%","spread": "+100–150bps","net": "-3% to -5%",  "net_color": "#EF4444"},
]
_cache = {}
CACHE_TTL = 30
# ─────────────────────────────────────────────────────────────────────────────
# Cache utility
# ─────────────────────────────────────────────────────────────────────────────
def cached_fetch(key, fetch_fn, ttl=CACHE_TTL):
    now = time.time()
    if key in _cache:
        data, ts = _cache[key]
        if now - ts < ttl:
            return data
    try:
        data = fetch_fn()
        _cache[key] = (data, now)
        return data
    except Exception:
        if key in _cache:
            return _cache[key][0]
        return None
# ─────────────────────────────────────────────────────────────────────────────
# Technical indicators
# ─────────────────────────────────────────────────────────────────────────────
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram
def compute_technical_indicators(df):
    close = df["Close"]
    for window in [20, 50, 200]:
        if len(df) >= window:
            df[f"SMA_{window}"] = close.rolling(window=window).mean()
    if len(df) >= 14:
        df["RSI"] = compute_rsi(close)
    if len(df) >= 26:
        df["MACD"], df["MACD_signal"], df["MACD_hist"] = compute_macd(close)
    return df
# ─────────────────────────────────────────────────────────────────────────────
# Data fetching — existing
# ─────────────────────────────────────────────────────────────────────────────
def fetch_index_data():
    results = []
    for symbol, name in INDICES.items():
        try:
            t = yf.Ticker(symbol)
            info = t.info
            results.append({
                "symbol": symbol,
                "name": name,
                "price": info.get("regularMarketPrice") or info.get("previousClose", 0),
                "change": info.get("regularMarketChange", 0),
                "changePct": info.get("regularMarketChangePercent", 0),
            })
        except Exception:
            results.append({"symbol": symbol, "name": name, "price": None, "change": None, "changePct": None})
    return results

def fetch_futures_data():
    """Fetch futures prices using history() to avoid auth issues."""
    results = []
    for symbol, name in FUTURES.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d", interval="1d")
            if hist.empty or len(hist) < 2:
                results.append({"symbol": symbol, "name": name, "price": None, "change": 0, "changePct": 0})
                continue
            close = float(hist["Close"].iloc[-1])
            prev  = float(hist["Close"].iloc[-2])
            chg   = close - prev
            chg_pct = (chg / prev * 100) if prev else 0
            results.append({"symbol": symbol, "name": name, "price": close, "change": chg, "changePct": chg_pct})
        except Exception:
            results.append({"symbol": symbol, "name": name, "price": None, "change": 0, "changePct": 0})
    return results

def fetch_sector_performance():
    data = {}
    for etf in SECTOR_ETFS:
        try:
            hist = yf.Ticker(etf).history(period="5d", interval="1d")
            if hist.empty or len(hist) < 2:
                data[etf] = 0
            else:
                prev  = float(hist["Close"].iloc[-2])
                close = float(hist["Close"].iloc[-1])
                data[etf] = ((close - prev) / prev * 100) if prev else 0
        except Exception:
            data[etf] = 0
    return data
def fetch_market_breadth():
    try:
        vix_info = yf.Ticker("^VIX").info
        vix = vix_info.get("regularMarketPrice") or vix_info.get("previousClose", 0)
        vix_change = vix_info.get("regularMarketChange", 0)
    except Exception:
        vix, vix_change = None, None
    return {"vix": vix, "vix_change": vix_change}
def fetch_market_extras():
    """Fetch price + day-change for bond ETFs, metals futures, and FX pairs.
    Uses history() which avoids Yahoo Finance crumb/auth issues with .info."""
    all_syms = list(BOND_ETFS) + list(TREASURY_YIELDS) + list(COMMODITIES) + list(CURRENCIES)
    out = {}
    for sym in all_syms:
        try:
            hist = yf.Ticker(sym).history(period="5d", interval="1d")
            if hist.empty or len(hist) < 2:
                out[sym] = {"price": None, "chg_pct": 0, "chg": 0}
                continue
            price = float(hist["Close"].iloc[-1])
            prev  = float(hist["Close"].iloc[-2])
            chg   = price - prev
            chg_pct = (chg / prev * 100) if prev else 0
            out[sym] = {"price": price, "chg_pct": chg_pct, "chg": chg}
        except Exception:
            out[sym] = {"price": None, "chg_pct": 0, "chg": 0}
    return out

def fetch_sector_movers(etf_symbol):
    """Fetch 1-day % change for each constituent stock in a sector ETF."""
    stocks = SECTOR_STOCKS.get(etf_symbol, [])
    if not stocks:
        return {"advancing": [], "declining": []}
    results = []
    for sym in stocks:
        try:
            hist = yf.Ticker(sym).history(period="5d", interval="1d")
            if hist.empty or len(hist) < 2:
                continue
            prev  = float(hist["Close"].iloc[-2])
            close = float(hist["Close"].iloc[-1])
            chg   = ((close - prev) / prev * 100) if prev else 0
            results.append({"symbol": sym, "chg_pct": chg, "price": close})
        except Exception:
            pass
    advancing = sorted([r for r in results if r["chg_pct"] >= 0], key=lambda x: x["chg_pct"], reverse=True)
    declining = sorted([r for r in results if r["chg_pct"] < 0],  key=lambda x: x["chg_pct"])
    return {"advancing": advancing, "declining": declining}

def fetch_gainers_losers():
    result = {"gainers": [], "losers": []}
    try:
        g = yf.screen("day_gainers", count=10)
        result["gainers"] = g.get("quotes", [])[:10]
    except Exception:
        pass
    try:
        l = yf.screen("day_losers", count=10)
        result["losers"] = l.get("quotes", [])[:10]
    except Exception:
        pass
    return result
def fetch_stock_history(symbol, timeframe="1M"):
    period, interval = TIMEFRAMES.get(timeframe, ("1mo", "1h"))
    df = yf.Ticker(symbol).history(period=period, interval=interval)
    return df
def fetch_stock_info(symbol):
    return yf.Ticker(symbol).info
def fetch_benchmark_comparison(symbol, timeframe="1M"):
    """Fetch normalized returns for symbol vs SPY and RSP using history()."""
    period, interval = TIMEFRAMES.get(timeframe, ("1mo", "1h"))
    # Deduplicate in case symbol is SPY or RSP
    tickers = list(dict.fromkeys([symbol, "SPY", "RSP"]))
    frames = {}
    for sym in tickers:
        try:
            hist = yf.Ticker(sym).history(period=period, interval=interval)
            if not hist.empty:
                frames[sym] = hist["Close"]
        except Exception:
            pass
    if not frames:
        return None
    df = pd.DataFrame(frames).dropna(how="all")
    if df.empty or len(df) < 2:
        return None
    return (df / df.iloc[0]) * 100
def fetch_stock_news(symbol):
    return yf.Ticker(symbol).news or []
def fetch_corporate_info(symbol):
    return yf.Ticker(symbol).info
def fetch_calendar_data(symbol):
    t = yf.Ticker(symbol)
    cal = {}
    try:
        cal["calendar"] = t.calendar
    except Exception:
        cal["calendar"] = {}
    try:
        actions = t.actions
        cal["actions"] = actions.tail(5) if actions is not None and len(actions) > 0 else None
    except Exception:
        cal["actions"] = None
    return cal
def fetch_sec_filings(symbol):
    """Fetch latest SEC filings from EDGAR for a given ticker symbol."""
    try:
        # Step 1: resolve ticker → CIK via EDGAR company search
        headers = {"User-Agent": "FinancialCommandCenter/1.0 (contact@example.com)"}
        search_url = (
            f"https://efts.sec.gov/LATEST/search-index?q=%22{symbol}%22"
            f"&dateRange=custom&startdt=2000-01-01&forms=10-K,10-Q,8-K"
        )
        # Use the tickers.json lookup for CIK resolution (faster, canonical)
        tickers_url = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(tickers_url, headers=headers, timeout=8)
        if resp.status_code != 200:
            return []
        tickers_data = resp.json()
        cik = None
        sym_upper = symbol.upper()
        for entry in tickers_data.values():
            if entry.get("ticker", "").upper() == sym_upper:
                cik = str(entry["cik_str"]).zfill(10)
                break
        if not cik:
            return []
        # Step 2: pull submission history for the CIK
        sub_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        sub_resp = requests.get(sub_url, headers=headers, timeout=8)
        if sub_resp.status_code != 200:
            return []
        sub_data = sub_resp.json()
        recent = sub_data.get("filings", {}).get("recent", {})
        forms       = recent.get("form", [])
        dates       = recent.get("filingDate", [])
        accessions  = recent.get("accessionNumber", [])
        descriptions = recent.get("primaryDocument", [])
        filings = []
        target_forms = {"10-K", "10-Q", "8-K", "DEF 14A", "S-1"}
        for form, date, acc, doc in zip(forms, dates, accessions, descriptions):
            if form in target_forms:
                acc_clean = acc.replace("-", "")
                url = (
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{int(cik)}/{acc_clean}/{doc}"
                )
                filings.append({
                    "form":   form,
                    "date":   date,
                    "url":    url,
                    "acc":    acc,
                })
                if len(filings) >= 15:
                    break
        return filings
    except Exception:
        return []
# ─────────────────────────────────────────────────────────────────────────────
# Data fetching — insider alerts
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_cik(symbol, headers):
    """Return zero-padded CIK string for a ticker, or None."""
    resp = requests.get("https://www.sec.gov/files/company_tickers.json",
                        headers=headers, timeout=8)
    if resp.status_code != 200:
        return None
    sym_upper = symbol.upper()
    for entry in resp.json().values():
        if entry.get("ticker", "").upper() == sym_upper:
            return str(entry["cik_str"]).zfill(10)
    return None

def fetch_insider_buys(symbol, days_back=90):
    """
    Fetch Form 4 insider open-market purchase transactions for a ticker via
    SEC EDGAR.  Returns a list of dicts; empty list on any failure.
    """
    headers = {"User-Agent": "FinancialCommandCenter/1.0 (contact@example.com)"}
    purchases = []
    try:
        cik = _resolve_cik(symbol, headers)
        if not cik:
            return purchases

        sub_resp = requests.get(
            f"https://data.sec.gov/submissions/CIK{cik}.json",
            headers=headers, timeout=8,
        )
        if sub_resp.status_code != 200:
            return purchases

        recent      = sub_resp.json().get("filings", {}).get("recent", {})
        forms       = recent.get("form", [])
        dates       = recent.get("filingDate", [])
        accessions  = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        cutoff    = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        cik_int   = int(cik)
        processed = 0

        for form, date, acc, doc in zip(forms, dates, accessions, primary_docs):
            if form != "4":
                continue
            if date < cutoff:
                continue
            if processed >= 20:          # cap per ticker to stay fast
                break
            if not doc.lower().endswith(".xml"):
                continue

            processed += 1
            acc_clean = acc.replace("-", "")
            xml_url   = (f"https://www.sec.gov/Archives/edgar/data/"
                         f"{cik_int}/{acc_clean}/{doc}")
            try:
                xml_resp = requests.get(xml_url, headers=headers, timeout=6)
                if xml_resp.status_code != 200:
                    continue
                root = ET.fromstring(xml_resp.content)
            except Exception:
                continue

            # Reporting-owner identity
            rpt = root.find(".//reportingOwner")
            if rpt is None:
                continue
            name  = (rpt.findtext(".//rptOwnerName") or "Unknown").strip()
            title = (rpt.findtext(".//officerTitle") or "").strip()
            is_dir = rpt.findtext(".//isDirector") == "1"
            role   = title or ("Director" if is_dir else "Insider")

            # Non-derivative open-market purchases (code P, acquired A)
            for txn in root.findall(".//nonDerivativeTransaction"):
                code = (txn.findtext(".//transactionCode") or "").strip()
                acq  = (txn.findtext(
                    ".//transactionAcquiredDisposedCode/value") or "").strip()
                if code != "P" or acq != "A":
                    continue
                try:
                    shares   = float(txn.findtext(".//transactionShares/value") or 0)
                    price    = float(txn.findtext(
                        ".//transactionPricePerShare/value") or 0)
                    txn_date = txn.findtext(".//transactionDate/value") or date
                except (ValueError, TypeError):
                    continue
                value = shares * price
                if value < INSIDER_MIN_VALUE:
                    continue
                purchases.append({
                    "symbol": symbol,
                    "name":   name,
                    "role":   role,
                    "date":   txn_date,
                    "shares": shares,
                    "price":  price,
                    "value":  value,
                    "url":    xml_url,
                })

        time.sleep(0.1)   # gentle rate-limit: 10 req/s max per EDGAR guidelines
    except Exception:
        pass
    return purchases

def fetch_watchlist_insider_buys(tickers, days_back=90):
    all_buys = []
    for sym in tickers:
        buys = cached_fetch(
            f"insider_{sym}_{days_back}",
            lambda s=sym, d=days_back: fetch_insider_buys(s, d),
            ttl=1800,
        )
        if buys:
            all_buys.extend(buys)
    all_buys.sort(key=lambda x: x["value"], reverse=True)
    return all_buys

# ─────────────────────────────────────────────────────────────────────────────
# Data fetching — options flow
# ─────────────────────────────────────────────────────────────────────────────
def fetch_options_flow(symbol, min_vol=OPTIONS_MIN_VOL, vol_oi_thresh=OPTIONS_VOL_OI_RATIO):
    """
    Scan the next OPTIONS_MAX_EXPIRATIONS expiry dates for a ticker and return
    contracts with unusual volume relative to open interest.
    """
    results = []
    try:
        t           = yf.Ticker(symbol)
        expirations = t.options
        if not expirations:
            return results
        spot_info = t.info
        spot      = spot_info.get("regularMarketPrice") or spot_info.get("previousClose") or 0

        cutoff_dt = datetime.now() + timedelta(days=60)
        near_exp  = [e for e in expirations
                     if datetime.strptime(e, "%Y-%m-%d") <= cutoff_dt][:OPTIONS_MAX_EXPIRATIONS]

        for exp in near_exp:
            try:
                chain = t.option_chain(exp)
            except Exception:
                continue
            for contract_type, df in [("CALL", chain.calls), ("PUT", chain.puts)]:
                if df is None or df.empty:
                    continue
                df = df.copy()
                df["volume"]       = pd.to_numeric(df["volume"],       errors="coerce").fillna(0)
                df["openInterest"] = pd.to_numeric(df["openInterest"], errors="coerce").fillna(0)
                df["impliedVolatility"] = pd.to_numeric(
                    df.get("impliedVolatility", 0), errors="coerce").fillna(0)
                df["lastPrice"]    = pd.to_numeric(df["lastPrice"],    errors="coerce").fillna(0)

                df = df[df["volume"] >= min_vol]
                if df.empty:
                    continue

                df["vol_oi"] = df.apply(
                    lambda r: r["volume"] / r["openInterest"]
                    if r["openInterest"] > 0 else float("inf"), axis=1,
                )
                df = df[df["vol_oi"] >= vol_oi_thresh]

                for _, row in df.iterrows():
                    strike    = float(row["strike"])
                    vol       = int(row["volume"])
                    oi        = int(row["openInterest"])
                    iv        = float(row["impliedVolatility"])
                    last      = float(row["lastPrice"])
                    vol_oi    = row["vol_oi"]
                    premium   = vol * last * 100          # approx dollar flow
                    itm       = bool(row.get("inTheMoney", False))

                    # Signal classification
                    if vol_oi >= 2.0 and vol >= 500:
                        signal = "SWEEP"
                    elif vol_oi >= 1.0:
                        signal = "UNUSUAL"
                    else:
                        signal = "NOTABLE"

                    results.append({
                        "symbol":   symbol,
                        "exp":      exp,
                        "strike":   strike,
                        "type":     contract_type,
                        "vol":      vol,
                        "oi":       oi,
                        "vol_oi":   round(vol_oi, 2),
                        "iv":       iv,
                        "last":     last,
                        "premium":  premium,
                        "itm":      itm,
                        "signal":   signal,
                        "spot":     spot,
                    })
    except Exception:
        pass
    return results

def fetch_watchlist_options_flow(tickers):
    all_flow = []
    for sym in tickers:
        flow = cached_fetch(
            f"options_flow_{sym}",
            lambda s=sym: fetch_options_flow(s),
            ttl=300,
        )
        if flow:
            all_flow.extend(flow)
    all_flow.sort(key=lambda x: x["premium"], reverse=True)
    return all_flow

# ─────────────────────────────────────────────────────────────────────────────
# Data fetching — COT positioning
# ─────────────────────────────────────────────────────────────────────────────
def fetch_cot_data():
    """Fetch the latest CFTC COT Legacy Futures-Only report for key markets."""
    COT_API = ("https://publicreporting.cftc.gov/api/odata/v1/"
               "MarketsAndPrices_COTLegacyFuturesOnly")
    try:
        filter_str = " or ".join(
            [f"contains(Market_and_Exchange_Names,'{m['filter']}')"
             for m in COT_MARKETS]
        )
        fields = ",".join([
            "Market_and_Exchange_Names", "As_of_Date_In_Form_YYMMDD",
            "NonComm_Positions_Long_All", "NonComm_Positions_Short_All",
            "Change_in_NonComm_Long_All", "Change_in_NonComm_Short_All",
            "Pct_of_OI_NonComm_Long_All", "Pct_of_OI_NonComm_Short_All",
        ])
        resp = requests.get(COT_API, params={
            "$filter":  filter_str,
            "$select":  fields,
            "$orderby": "As_of_Date_In_Form_YYMMDD desc",
            "$top":     "100",
        }, headers={"Accept": "application/json"}, timeout=20)
        if resp.status_code != 200:
            return []
        rows = resp.json().get("value", [])
    except Exception:
        return []

    def _int(v):
        try: return int(v or 0)
        except (ValueError, TypeError): return 0

    seen, results = set(), []
    for row in rows:
        name = row.get("Market_and_Exchange_Names", "")
        meta = next((m for m in COT_MARKETS if m["filter"] in name), None)
        if meta is None or meta["label"] in seen:
            continue
        seen.add(meta["label"])
        nl = _int(row.get("NonComm_Positions_Long_All"))
        ns = _int(row.get("NonComm_Positions_Short_All"))
        cl = _int(row.get("Change_in_NonComm_Long_All"))
        cs = _int(row.get("Change_in_NonComm_Short_All"))
        results.append({
            "label":     meta["label"],
            "color":     meta["color"],
            "date":      row.get("As_of_Date_In_Form_YYMMDD", ""),
            "net":       nl - ns,
            "net_long":  nl,
            "net_short": ns,
            "chg_net":   cl - cs,
            "pct_long":  float(row.get("Pct_of_OI_NonComm_Long_All") or 0),
            "pct_short": float(row.get("Pct_of_OI_NonComm_Short_All") or 0),
        })
    results.sort(key=lambda x: abs(x["net"]), reverse=True)
    return results

# ─────────────────────────────────────────────────────────────────────────────
# Data fetching — 13F holdings
# ─────────────────────────────────────────────────────────────────────────────
import re as _re

def _strip_ns(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def parse_13f_xml(content):
    """Parse 13F infotable XML → list of holding dicts sorted by value."""
    holdings = []
    try:
        root = ET.fromstring(content)
        for elem in root.iter():
            if _strip_ns(elem.tag) != "infoTable":
                continue
            name, value, shares, cusip = "", 0, 0, ""
            for child in elem:
                tag = _strip_ns(child.tag)
                if tag == "nameOfIssuer":
                    name = (child.text or "").strip()
                elif tag == "value":
                    try: value = int(child.text or 0) * 1000
                    except (ValueError, TypeError): pass
                elif tag == "cusip":
                    cusip = (child.text or "").strip()
                elif tag == "shrsOrPrnAmt":
                    for sub in child:
                        if _strip_ns(sub.tag) == "sshPrnamt":
                            try: shares = int(sub.text or 0)
                            except (ValueError, TypeError): pass
            if name and value > 0:
                holdings.append({"name": name, "cusip": cusip,
                                 "value": value, "shares": shares})
    except Exception:
        pass
    holdings.sort(key=lambda x: x["value"], reverse=True)
    return holdings

def fetch_13f_holdings(cik_str):
    """Fetch the most recent 13F-HR filing for the given CIK via EDGAR."""
    headers = {"User-Agent": "FinancialCommandCenter/1.0 (contact@example.com)"}
    cik_padded = str(cik_str).zfill(10)
    cik_int    = int(cik_str)
    try:
        sub = requests.get(
            f"https://data.sec.gov/submissions/CIK{cik_padded}.json",
            headers=headers, timeout=10).json()
        fund_name = sub.get("name", "Unknown Fund")
        recent    = sub.get("filings", {}).get("recent", {})
        for form, acc, date in zip(
            recent.get("form", []),
            recent.get("accessionNumber", []),
            recent.get("filingDate", []),
        ):
            if form not in ("13F-HR", "13F-HR/A"):
                continue
            acc_clean = acc.replace("-", "")
            base      = (f"https://www.sec.gov/Archives/edgar/data/"
                         f"{cik_int}/{acc_clean}")
            dir_resp  = requests.get(f"{base}/", headers=headers, timeout=10)
            if dir_resp.status_code != 200:
                continue
            # Find XML files in the directory listing, prefer infotable-named ones
            xml_paths = _re.findall(
                r'href="(/Archives/edgar/data/[^"]*\.xml)"',
                dir_resp.text, _re.I,
            )
            xml_paths.sort(key=lambda p: 0 if any(
                kw in p.lower() for kw in ["info", "table", "13f"]) else 1)
            for path in xml_paths:
                xml_resp = requests.get(
                    f"https://www.sec.gov{path}", headers=headers, timeout=10)
                if xml_resp.status_code != 200:
                    continue
                holdings = parse_13f_xml(xml_resp.content)
                if holdings:
                    total = sum(h["value"] for h in holdings)
                    for h in holdings:
                        h["pct"] = h["value"] / total * 100 if total else 0
                    return {"name": fund_name, "date": date,
                            "cik": cik_str, "total": total}, holdings
            break   # only try the most recent 13F-HR
    except Exception:
        pass
    return None, []

# ─────────────────────────────────────────────────────────────────────────────
# Data fetching — short interest
# ─────────────────────────────────────────────────────────────────────────────
def fetch_short_interest(tickers):
    results = []
    for sym in tickers:
        try:
            info       = yf.Ticker(sym).info
            price      = info.get("regularMarketPrice") or info.get("previousClose") or 0
            s_short    = info.get("sharesShort") or 0
            s_prior    = info.get("sharesShortPriorMonth") or 0
            pct_float  = (info.get("shortPercentOfFloat") or 0) * 100
            days_cover = info.get("shortRatio") or 0
            chg_pct    = (s_short - s_prior) / s_prior * 100 if s_prior else 0
            results.append({
                "symbol":       sym,
                "name":         info.get("shortName", sym)[:28],
                "price":        price,
                "shares_short": s_short,
                "short_prior":  s_prior,
                "pct_float":    pct_float,
                "days_cover":   days_cover,
                "change_pct":   chg_pct,
            })
        except Exception:
            results.append({"symbol": sym, "name": sym, "price": 0,
                            "shares_short": 0, "short_prior": 0,
                            "pct_float": 0, "days_cover": 0, "change_pct": 0})
    results.sort(key=lambda x: x["pct_float"], reverse=True)
    return results

# ─────────────────────────────────────────────────────────────────────────────
# Data fetching — ETF flows
# ─────────────────────────────────────────────────────────────────────────────
def fetch_etf_flows():
    results = []
    for sym, (etf_name, category) in FLOW_ETFS.items():
        try:
            info      = yf.Ticker(sym).info
            price     = (info.get("regularMarketPrice") or info.get("navPrice")
                         or info.get("previousClose") or 0)
            chg_1d    = info.get("regularMarketChangePercent") or 0
            shares    = info.get("sharesOutstanding") or 0
            aum       = shares * price
            avg_vol   = info.get("averageVolume") or 1
            day_vol   = info.get("regularMarketVolume") or 0
            vol_ratio = day_vol / avg_vol if avg_vol else 0
            try:
                hist  = yf.Ticker(sym).history(period="5d", interval="1d")
                chg_1w = ((hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100
                          if len(hist) >= 2 else 0)
            except Exception:
                chg_1w = 0
            results.append({
                "symbol":    sym,
                "name":      etf_name,
                "category":  category,
                "price":     price,
                "aum":       aum,
                "chg_1d":    chg_1d,
                "chg_1w":    chg_1w,
                "vol_ratio": vol_ratio,
                "day_vol":   day_vol,
            })
        except Exception:
            pass
    return results

# ─────────────────────────────────────────────────────────────────────────────
# Data fetching — macro dashboard
# ─────────────────────────────────────────────────────────────────────────────
def fetch_macro_prices():
    all_tickers = list(MACRO_TICKERS.keys()) + [TREASURY_TICKER]
    try:
        raw = yf.download(all_tickers, period="2y", interval="1mo",
                          auto_adjust=True, progress=False)
        if "Close" in raw.columns.get_level_values(0):
            df = raw["Close"]
        else:
            df = raw
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()
def fetch_fred_spreads():
    fred = _get_fred()
    if fred is None:
        return None
    try:
        start = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
        hy  = fred.get_series(FRED_HY_OAS, observation_start=start)
        ig  = fred.get_series(FRED_IG_OAS, observation_start=start)
        df  = pd.DataFrame({"HY_OAS": hy, "IG_OAS": ig})
        df  = df.resample("ME").last().dropna()
        df["HYIG_SPREAD"] = df["HY_OAS"] - df["IG_OAS"]
        return df
    except Exception:
        return None
def fetch_bdc_prices():
    rows = []
    for ticker in BDC_TICKERS:
        try:
            info  = yf.Ticker(ticker).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0)
            book  = info.get("bookValue")
            pnav  = round(price / book, 2) if book and book > 0 else None
            signal = ("🟢 Green" if pnav and pnav >= 0.95 else
                      "🟡 Yellow" if pnav and pnav >= 0.85 else
                      "🔴 Red"   if pnav else "–")
            rows.append({
                "Ticker":   ticker,
                "Price":    f"${price:.2f}",
                "Book/NAV": f"${book:.2f}" if book else "N/A",
                "P/NAV":    f"{pnav:.2f}x"  if pnav else "N/A",
                "Signal":   signal,
                "_pnav":    pnav,
            })
        except Exception:
            rows.append({"Ticker": ticker, "Price": "–", "Book/NAV": "–",
                         "P/NAV": "–", "Signal": "–", "_pnav": None})
    return rows
def get_current_macro_signal(df):
    try:
        dxy_col = "DX-Y.NYB"
        if len(df) < 2:
            return None
        latest = df.iloc[-1]
        prev   = df.iloc[-2]
        dxy_up = latest.get(dxy_col, 0) > prev.get(dxy_col, 0)
        gld_up = latest.get("GLD", 0)   > prev.get("GLD", 0)
        uso_up = latest.get("USO", 0)   > prev.get("USO", 0)
        for row in SIGNAL_MATRIX:
            if ((row["DXY"] == "↑") == dxy_up and
                (row["GLD"] == "↑") == gld_up and
                (row["USO"] == "↑") == uso_up):
                return row
    except Exception:
        pass
    return None
# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────
def fmt_number(n):
    if n is None or n == "N/A":
        return "N/A"
    try:
        n = float(n)
    except (ValueError, TypeError):
        return str(n)
    if abs(n) >= 1e12:
        return f"${n / 1e12:.2f}T"
    if abs(n) >= 1e9:
        return f"${n / 1e9:.2f}B"
    if abs(n) >= 1e6:
        return f"${n / 1e6:.2f}M"
    return f"${n:,.0f}"
def fmt_pct(pct):
    if pct is None:
        return html.Span("N/A", className="text-muted")
    arrow = "\u25b2" if pct >= 0 else "\u25bc"
    cls = "text-gain" if pct >= 0 else "text-loss"
    return html.Span(f"{arrow} {abs(pct):.2f}%", className=cls)
def fmt_change(change):
    if change is None:
        return html.Span("N/A", className="text-muted")
    cls = "text-gain" if change >= 0 else "text-loss"
    sign = "+" if change >= 0 else ""
    return html.Span(f"{sign}{change:.2f}", className=cls)
def safe_get(d, key, default="N/A"):
    if not d:
        return default
    val = d.get(key)
    return val if val is not None else default
def truncate_text(text, max_len=300):
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text
# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

*, body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

body {
    background: radial-gradient(ellipse at top left, #0d1b2a 0%, #070d14 60%, #050a10 100%) !important;
    min-height: 100vh;
    color: #e2e8f0;
}

/* ── Cards ── */
.card {
    background: linear-gradient(135deg, rgba(15,23,42,0.9) 0%, rgba(10,18,35,0.95) 100%) !important;
    border: 1px solid rgba(99,179,237,0.1) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04) !important;
    transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.2s ease !important;
}
.card:hover {
    border-color: rgba(99,179,237,0.25) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,179,237,0.08), inset 0 1px 0 rgba(255,255,255,0.06) !important;
}
.card-header {
    background: rgba(255,255,255,0.02) !important;
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 14px 14px 0 0 !important;
    padding: 14px 18px !important;
    letter-spacing: 0.3px;
}

/* ── Navbar ── */
.navbar {
    background: rgba(5,10,20,0.92) !important;
    backdrop-filter: blur(20px);
    box-shadow: 0 1px 0 rgba(99,179,237,0.12), 0 4px 20px rgba(0,0,0,0.4) !important;
}
.navbar-brand {
    background: linear-gradient(90deg, #63b3ed, #4fd1c5);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 700 !important;
    letter-spacing: 2.5px !important;
}

/* ── Tabs ── */
.nav-tabs {
    border-bottom: 1px solid rgba(255,255,255,0.06) !important;
    gap: 4px;
}
.nav-tabs .nav-link {
    color: #64748b !important;
    border: none !important;
    font-weight: 600;
    letter-spacing: 0.8px;
    font-size: 0.82rem;
    padding: 10px 18px !important;
    border-radius: 8px 8px 0 0 !important;
    transition: color 0.2s, background 0.2s !important;
}
.nav-tabs .nav-link:hover {
    color: #94a3b8 !important;
    background: rgba(255,255,255,0.03) !important;
}
.nav-tabs .nav-link.active {
    color: #63b3ed !important;
    background: rgba(99,179,237,0.06) !important;
    border-bottom: 2px solid #63b3ed !important;
}

/* ── Color tokens ── */
.text-gain { color: #4fd1c5 !important; }
.text-loss { color: #fc8181 !important; }

/* ── Stat rows ── */
.stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.stat-row:last-child { border-bottom: none; }
.stat-label { color: #64748b; font-size: 0.8rem; font-weight: 500; letter-spacing: 0.2px; }
.stat-value { color: #e2e8f0; font-weight: 600; font-size: 0.82rem; font-family: 'JetBrains Mono', monospace !important; }

/* ── Index cards ── */
.index-card {
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
.index-card:hover { transform: translateY(-3px) !important; }

/* ── News cards ── */
.news-card { transition: border-color 0.2s ease, box-shadow 0.2s ease !important; }
.news-card:hover {
    border-color: rgba(99,179,237,0.35) !important;
    box-shadow: 0 4px 20px rgba(99,179,237,0.08) !important;
}

/* ── Macro cards ── */
.macro-stat-card { border-top-width: 2px !important; border-radius: 14px !important; }
.macro-table td, .macro-table th {
    padding: 10px 14px;
    font-size: 0.8rem;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.macro-table th {
    color: #64748b;
    font-weight: 600;
    letter-spacing: 0.6px;
    font-size: 0.72rem;
    text-transform: uppercase;
}
.macro-table tbody tr:hover { background: rgba(99,179,237,0.04); }

/* ── Buttons ── */
.btn-outline-success {
    border-color: rgba(79,209,197,0.4) !important;
    color: #4fd1c5 !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px;
    transition: all 0.2s ease !important;
}
.btn-outline-success:hover, .btn-outline-success.active, .btn-outline-success:not(.btn-outline-success) {
    background: rgba(79,209,197,0.12) !important;
    border-color: #4fd1c5 !important;
    box-shadow: 0 0 12px rgba(79,209,197,0.15) !important;
}
.btn-success {
    background: linear-gradient(135deg, #4fd1c5, #38b2ac) !important;
    border: none !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 12px rgba(79,209,197,0.3) !important;
}

/* ── Input ── */
.form-control {
    background: rgba(15,23,42,0.8) !important;
    border: 1px solid rgba(99,179,237,0.2) !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    font-weight: 500;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.form-control:focus {
    border-color: rgba(99,179,237,0.5) !important;
    box-shadow: 0 0 0 3px rgba(99,179,237,0.1) !important;
    background: rgba(15,23,42,0.95) !important;
}

/* ── Badges ── */
.badge {
    font-weight: 600 !important;
    letter-spacing: 0.4px;
    padding: 5px 10px !important;
    border-radius: 6px !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99,179,237,0.2); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,179,237,0.35); }

/* ── Loading spinner ── */
.dash-spinner { color: #63b3ed !important; }

/* ── Alert ── */
.alert {
    border-radius: 10px !important;
    border-width: 1px !important;
    font-size: 0.85rem;
}
.alert-success { background: rgba(79,209,197,0.08) !important; border-color: rgba(79,209,197,0.25) !important; color: #81e6d9 !important; }
.alert-warning { background: rgba(246,173,85,0.08) !important; border-color: rgba(246,173,85,0.25) !important; color: #fbd38d !important; }
.alert-danger  { background: rgba(252,129,129,0.08) !important; border-color: rgba(252,129,129,0.25) !important; color: #feb2b2 !important; }
.alert-secondary { background: rgba(100,116,139,0.08) !important; border-color: rgba(100,116,139,0.2) !important; }

/* ── Switch ── */
.form-check-input:checked { background-color: #4fd1c5 !important; border-color: #4fd1c5 !important; }
"""
# ─────────────────────────────────────────────────────────────────────────────
# App initialization
# ─────────────────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
)
server = app.server  # exposed for gunicorn
app.title = "Financial Command Center"
app.index_string = (
    "<!DOCTYPE html><html><head>{%metas%}<title>Financial Command Center</title>"
    "<link rel='preconnect' href='https://fonts.googleapis.com'>"
    "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
    "{%favicon%}{%css%}<style>" + CUSTOM_CSS + "</style></head>"
    "<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>"
)
# ─────────────────────────────────────────────────────────────────────────────
# Layout builders — existing tabs
# ─────────────────────────────────────────────────────────────────────────────
def create_navbar():
    return dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand(
                [html.I(className="fas fa-chart-line me-2"), "FINANCIAL COMMAND CENTER"],
                style={"fontWeight": "bold", "letterSpacing": "3px", "fontSize": "1.05rem"},
            ),
            dbc.Nav([
                html.Span(id="market-status-badge"),
                html.Span(id="last-update-time", className="text-muted ms-3",
                           style={"fontSize": "0.8rem"}),
                dbc.Switch(id="auto-refresh-toggle", label="Auto-refresh",
                           value=True, className="ms-3 text-muted", style={"fontSize": "0.8rem"}),
            ], className="ms-auto d-flex align-items-center"),
        ], fluid=True),
        color="dark", dark=True, className="mb-3",
        style={"borderBottom": "2px solid #00bc8c"},
    )
def create_flow_data_tab():
    CARD_HDR = {"fontSize": "0.9rem", "fontWeight": "600"}
    IGRP_TXT = {"fontSize": "0.82rem", "backgroundColor": "#1e293b",
                 "color": "#94a3b8", "border": "1px solid rgba(0,188,140,0.3)"}
    IGRP_INP = {"backgroundColor": "#161c2d", "color": "#e2e8f0",
                 "border": "1px solid rgba(0,188,140,0.3)", "fontSize": "0.85rem"}
    return html.Div([
        html.Div([
            html.I(className="fas fa-water me-2 text-info"),
            html.Span("FLOW DATA", style={"fontWeight": "700", "letterSpacing": "2px",
                                          "fontSize": "0.95rem"}),
            html.Span(" — COT positioning · 13F holdings · short interest · ETF flows",
                      className="text-muted ms-2", style={"fontSize": "0.78rem"}),
        ], className="mb-3"),
        dbc.Tabs([
            # ── COT ──────────────────────────────────────────────────────────
            dbc.Tab(label="COT POSITIONING", tab_id="flow-cot",
                    label_style={"fontSize": "0.82rem"}, children=[
                dbc.Row([dbc.Col(dbc.Button(
                    [html.I(className="fas fa-sync me-2"), "Load COT Data"],
                    id="load-cot-btn", color="info", size="sm", className="mt-3 mb-3",
                ))]),
                dcc.Loading(
                    html.Div(html.P("Click 'Load COT Data' to fetch the latest CFTC report.",
                                    className="text-muted small p-2"),
                             id="cot-content"),
                    color="#00bc8c",
                ),
            ]),
            # ── 13F ──────────────────────────────────────────────────────────
            dbc.Tab(label="13F HOLDINGS", tab_id="flow-13f",
                    label_style={"fontSize": "0.82rem"}, children=[
                dbc.Row([
                    dbc.Col([dbc.Select(
                        id="fund-select",
                        options=[{"label": k, "value": v} for k, v in FAMOUS_FUNDS.items()],
                        placeholder="Select a famous fund…",
                        style={**IGRP_INP, "height": "31px"},
                    )], lg=4, className="mt-3 mb-2"),
                    dbc.Col([dbc.InputGroup([
                        dbc.InputGroupText("Custom CIK", style=IGRP_TXT),
                        dbc.Input(id="custom-cik-input", type="text",
                                  placeholder="e.g. 0001067983", style=IGRP_INP),
                    ], size="sm")], lg=5, className="mt-3 mb-2"),
                    dbc.Col([dbc.Button(
                        [html.I(className="fas fa-download me-2"), "Load 13F"],
                        id="load-13f-btn", color="info", size="sm",
                        className="w-100 mt-3",
                    )], lg=3),
                ], className="mb-3 align-items-end"),
                dcc.Loading(
                    html.Div(html.P("Select a fund or enter a CIK above.",
                                    className="text-muted small p-2"),
                             id="holdings-content"),
                    color="#00bc8c",
                ),
            ]),
            # ── Short Interest ────────────────────────────────────────────────
            dbc.Tab(label="SHORT INTEREST", tab_id="flow-short",
                    label_style={"fontSize": "0.82rem"}, children=[
                dbc.Row([
                    dbc.Col([dbc.InputGroup([
                        dbc.InputGroupText("Watchlist", style=IGRP_TXT),
                        dbc.Input(id="short-interest-input", value=", ".join(WATCHLIST),
                                  type="text", style=IGRP_INP),
                    ], size="sm")], lg=9, className="mt-3 mb-2"),
                    dbc.Col([dbc.Button(
                        [html.I(className="fas fa-search me-2"), "Scan"],
                        id="load-short-btn", color="info", size="sm", className="w-100 mt-3",
                    )], lg=3),
                ], className="mb-3 align-items-end"),
                dcc.Loading(
                    html.Div(html.P("Enter tickers and click Scan.",
                                    className="text-muted small p-2"),
                             id="short-interest-content"),
                    color="#00bc8c",
                ),
            ]),
            # ── ETF Flows ─────────────────────────────────────────────────────
            dbc.Tab(label="ETF FLOWS", tab_id="flow-etf",
                    label_style={"fontSize": "0.82rem"}, children=[
                dbc.Row([dbc.Col(dbc.Button(
                    [html.I(className="fas fa-sync me-2"), "Load ETF Data"],
                    id="load-etf-btn", color="info", size="sm", className="mt-3 mb-3",
                ))]),
                dcc.Loading(
                    html.Div(html.P("Click 'Load ETF Data' to fetch AUM & flow data.",
                                    className="text-muted small p-2"),
                             id="etf-flows-content"),
                    color="#00bc8c",
                ),
            ]),
        ], id="flow-subtabs", active_tab="flow-cot"),
    ])

def create_options_flow_tab():
    return html.Div([
        html.Div([
            html.I(className="fas fa-bolt me-2 text-warning"),
            html.Span("OPTIONS FLOW TRACKER",
                      style={"fontWeight": "700", "letterSpacing": "2px", "fontSize": "0.95rem"}),
            html.Span(" — unusual volume vs open interest via Yahoo Finance",
                      className="text-muted ms-2", style={"fontSize": "0.78rem"}),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText(
                        "Watchlist",
                        style={"fontSize": "0.82rem", "backgroundColor": "#1e293b",
                               "color": "#94a3b8", "border": "1px solid rgba(0,188,140,0.3)"},
                    ),
                    dbc.Input(
                        id="options-watchlist-input",
                        value=", ".join(WATCHLIST),
                        type="text",
                        debounce=False,
                        style={"backgroundColor": "#161c2d", "color": "#e2e8f0",
                               "border": "1px solid rgba(0,188,140,0.3)", "fontSize": "0.85rem"},
                    ),
                ], size="sm"),
            ], lg=5, className="mb-2"),
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("Min Vol", style={
                        "fontSize": "0.82rem", "backgroundColor": "#1e293b",
                        "color": "#94a3b8", "border": "1px solid rgba(0,188,140,0.3)"}),
                    dbc.Input(id="options-min-vol", value="100", type="number", min=1,
                              style={"backgroundColor": "#161c2d", "color": "#e2e8f0",
                                     "border": "1px solid rgba(0,188,140,0.3)",
                                     "fontSize": "0.85rem", "width": "80px"}),
                    dbc.InputGroupText("Vol/OI ≥", style={
                        "fontSize": "0.82rem", "backgroundColor": "#1e293b",
                        "color": "#94a3b8", "border": "1px solid rgba(0,188,140,0.3)"}),
                    dbc.Input(id="options-vol-oi", value="0.5", type="number",
                              min=0.1, step=0.1,
                              style={"backgroundColor": "#161c2d", "color": "#e2e8f0",
                                     "border": "1px solid rgba(0,188,140,0.3)",
                                     "fontSize": "0.85rem", "width": "70px"}),
                ], size="sm"),
            ], lg=4, className="mb-2"),
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-search-dollar me-2"), "Scan Flow"],
                    id="scan-options-btn", color="warning", size="sm", className="w-100",
                ),
            ], lg=3, className="mb-2"),
        ], className="mb-3 align-items-center"),
        dbc.Row([dbc.Col(html.Div(id="options-summary-cards"), className="mb-3")]),
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-table me-2"),
                "Unusual Options Activity",
                html.Span(
                    " — sorted by premium flow, ITM strikes highlighted",
                    className="text-muted ms-2", style={"fontSize": "0.72rem", "fontWeight": "400"},
                ),
                dbc.ButtonGroup([
                    dbc.Button("All",   id="opt-filter-all",  size="sm", color="secondary",
                               outline=False, className="ms-3", style={"fontSize": "0.72rem"}),
                    dbc.Button("Calls", id="opt-filter-calls", size="sm", color="success",
                               outline=True, style={"fontSize": "0.72rem"}),
                    dbc.Button("Puts",  id="opt-filter-puts",  size="sm", color="danger",
                               outline=True, style={"fontSize": "0.72rem"}),
                ], className="float-end"),
            ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
            dbc.CardBody(
                dcc.Loading(
                    html.Div(
                        html.P(
                            "Enter tickers and click 'Scan Flow' to detect unusual options activity.",
                            className="text-muted small p-2 mb-0",
                        ),
                        id="options-flow-table",
                    ),
                    color="#00bc8c",
                ),
                className="p-2",
            ),
        ]),
        dcc.Store(id="options-flow-store"),
        dcc.Store(id="options-filter-store", data="ALL"),
    ])

def create_insider_alerts_tab():
    return html.Div([
        html.Div([
            html.I(className="fas fa-user-secret me-2 text-warning"),
            html.Span("INSIDER BUYING ALERTS",
                      style={"fontWeight": "700", "letterSpacing": "2px", "fontSize": "0.95rem"}),
            html.Span(" — Form 4 filings via SEC EDGAR (free, no key)",
                      className="text-muted ms-2", style={"fontSize": "0.78rem"}),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText(
                        "Watchlist",
                        style={"fontSize": "0.82rem", "backgroundColor": "#1e293b",
                               "color": "#94a3b8", "border": "1px solid rgba(0,188,140,0.3)"},
                    ),
                    dbc.Input(
                        id="watchlist-input",
                        value=", ".join(WATCHLIST),
                        type="text",
                        debounce=False,
                        style={"backgroundColor": "#161c2d", "color": "#e2e8f0",
                               "border": "1px solid rgba(0,188,140,0.3)", "fontSize": "0.85rem"},
                    ),
                ], size="sm"),
            ], lg=7, className="mb-2"),
            dbc.Col([
                dbc.Select(
                    id="insider-days-select",
                    options=[
                        {"label": "Last 30 days", "value": "30"},
                        {"label": "Last 60 days", "value": "60"},
                        {"label": "Last 90 days", "value": "90"},
                    ],
                    value="90",
                    style={"backgroundColor": "#161c2d", "color": "#e2e8f0",
                           "border": "1px solid rgba(0,188,140,0.3)", "fontSize": "0.85rem",
                           "height": "31px"},
                ),
            ], lg=2, className="mb-2"),
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-satellite-dish me-2"), "Scan Insiders"],
                    id="scan-insiders-btn", color="warning", size="sm",
                    className="w-100",
                ),
            ], lg=3, className="mb-2"),
        ], className="mb-3 align-items-center"),
        dbc.Row([
            dbc.Col(html.Div(id="insider-summary-cards"), className="mb-3"),
        ]),
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-table me-2"),
                "Recent Open-Market Purchases",
                html.Span(
                    " — transaction code P, acquired (A), min $10 K",
                    className="text-muted ms-2", style={"fontSize": "0.72rem", "fontWeight": "400"},
                ),
            ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
            dbc.CardBody(
                dcc.Loading(
                    html.Div(
                        html.P(
                            "Enter watchlist tickers above and click 'Scan Insiders' "
                            "to fetch Form 4 data from SEC EDGAR.",
                            className="text-muted small p-2 mb-0",
                        ),
                        id="insider-alerts-table",
                    ),
                    color="#00bc8c",
                ),
                className="p-2",
            ),
        ]),
    ])

def create_market_overview_tab():
    return html.Div([
        dcc.Store(id="selected-sector-store"),
        # ── Row 1: Stock Indices + Futures (full width) ───────────────────────
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-chart-bar me-2"),
                "Major Indices & Futures",
            ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
            dbc.CardBody([
                html.Span("Cash Indices", className="text-muted",
                           style={"fontSize": "0.7rem", "letterSpacing": "0.5px"}),
                dcc.Loading(html.Div(id="indices-container"), color="#00bc8c"),
                html.Hr(style={"borderColor": "rgba(255,255,255,0.08)", "margin": "8px 0"}),
                html.Span("Futures  (extended & overnight)",
                           className="text-muted",
                           style={"fontSize": "0.7rem", "letterSpacing": "0.5px"}),
                dcc.Loading(
                    dbc.Row(id="futures-container", className="g-2 mt-1"),
                    color="#00bc8c",
                ),
            ], className="p-2"),
        ], className="mb-3"),
        # ── Row 2: Bond ETFs + Treasury Yields (full width) ───────────────────
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-landmark me-2"),
                "Bond ETFs & Treasury Yields",
            ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
            dbc.CardBody([
                html.Span("ETF Prices", className="text-muted",
                           style={"fontSize": "0.7rem", "letterSpacing": "0.5px"}),
                dcc.Loading(
                    dbc.Row(id="bonds-container", className="g-2 mt-1 mb-2"),
                    color="#00bc8c",
                ),
                html.Hr(style={"borderColor": "rgba(255,255,255,0.08)", "margin": "4px 0 8px"}),
                html.Span("Treasury Yields  (▲ = rising rate, bps change)",
                           className="text-muted",
                           style={"fontSize": "0.7rem", "letterSpacing": "0.5px"}),
                dcc.Loading(
                    dbc.Row(id="yields-container", className="g-2 mt-1"),
                    color="#00bc8c",
                ),
            ], className="p-2"),
        ], className="mb-3"),
        # ── Row 3: Metals/Commodities + Currencies (full width) ───────────────
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-coins me-2"),
                "Metals, Commodities & Currencies",
            ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
            dbc.CardBody([
                html.Span("Commodities", className="text-muted",
                           style={"fontSize": "0.7rem", "letterSpacing": "0.5px"}),
                dcc.Loading(
                    dbc.Row(id="metals-container", className="g-2 mt-1 mb-2"),
                    color="#00bc8c",
                ),
                html.Hr(style={"borderColor": "rgba(255,255,255,0.08)", "margin": "4px 0 8px"}),
                html.Span("Currencies", className="text-muted",
                           style={"fontSize": "0.7rem", "letterSpacing": "0.5px"}),
                dcc.Loading(
                    dbc.Row(id="currencies-container", className="g-2 mt-1"),
                    color="#00bc8c",
                ),
            ], className="p-2"),
        ], className="mb-3"),
        # ── Row 4: Sector Performance — clickable cards (full width) ──────────
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-th me-2"),
                "Sector Performance  ",
                html.Span("click a sector to see stock breakdown",
                           style={"fontSize": "0.72rem", "color": "#64748b", "fontStyle": "italic"}),
            ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
            dbc.CardBody([
                dcc.Loading(html.Div(id="sector-btns-container"), color="#00bc8c"),
                html.Div(id="sector-movers-container"),
            ], className="p-2"),
        ], className="mb-3"),
        # ── Top Movers (full width, below sector) ─────────────────────────────
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-fire me-2"),
                "Top Movers",
            ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
            dbc.CardBody(
                dcc.Loading(html.Div([
                    dbc.Tabs([
                        dbc.Tab(html.Div(id="gainers-table"), label="Gainers",
                                tab_id="tab-gainers", label_style={"fontSize": "0.8rem"}),
                        dbc.Tab(html.Div(id="losers-table"), label="Losers",
                                tab_id="tab-losers", label_style={"fontSize": "0.8rem"}),
                    ], active_tab="tab-gainers"),
                ]), color="#00bc8c"),
                className="p-2",
            ),
        ], className="mb-3"),
    ])
def create_trading_dashboard_tab():
    tf_buttons = dbc.ButtonGroup([
        dbc.Button(tf, id=f"tf-{tf}", color="success", outline=True, size="sm", className="me-1")
        for tf in TIMEFRAMES
    ], className="me-3")
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.Input(id="stock-input", placeholder="Enter ticker (e.g. AAPL)",
                              value="AAPL", type="text", debounce=True,
                              style={"backgroundColor": "#161c2d", "color": "#fff", "border": "1px solid rgba(0,188,140,0.3)"}),
                    dbc.Button([html.I(className="fas fa-search me-1"), "Go"],
                               id="stock-search-btn", color="success", size="sm"),
                ], size="sm"),
            ], lg=3, className="mb-2"),
            dbc.Col(tf_buttons, lg=6, className="mb-2 d-flex align-items-center"),
            dbc.Col(html.Div(id="current-price-display", className="text-end"), lg=3, className="mb-2"),
        ], className="mb-3 align-items-center"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody(
                        dcc.Loading(dcc.Graph(id="candlestick-chart",
                                              config={"displayModeBar": False},
                                              style={"height": "480px"}), color="#00bc8c"),
                        className="p-1",
                    ),
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Card(dbc.CardBody(
                        dcc.Loading(dcc.Graph(id="rsi-chart", config={"displayModeBar": False},
                                              style={"height": "200px"}), color="#00bc8c"),
                        className="p-1",
                    ), className="mb-3"), lg=6),
                    dbc.Col(dbc.Card(dbc.CardBody(
                        dcc.Loading(dcc.Graph(id="macd-chart", config={"displayModeBar": False},
                                              style={"height": "200px"}), color="#00bc8c"),
                        className="p-1",
                    ), className="mb-3"), lg=6),
                ]),
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-balance-scale me-2"),
                        "Benchmark Comparison — SPY vs RSP (Equal Weight)",
                    ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
                    dbc.CardBody(
                        dcc.Loading(dcc.Graph(id="benchmark-chart",
                                              config={"displayModeBar": False},
                                              style={"height": "260px"}), color="#00bc8c"),
                        className="p-1",
                    ),
                ], className="mb-3"),
            ], lg=9),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-info-circle me-2"),
                        "Key Statistics",
                    ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
                    dbc.CardBody(
                        dcc.Loading(html.Div(id="stats-panel"), color="#00bc8c"),
                    ),
                ]),
            ], lg=3),
        ]),
    ])
def create_news_tab():
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-newspaper me-2"),
                        "Latest News",
                    ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
                    dbc.CardBody(
                        dcc.Loading(html.Div(id="news-feed"), color="#00bc8c"),
                        style={"maxHeight": "700px", "overflowY": "auto"},
                    ),
                ]),
            ], lg=7),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-building me-2"),
                        "Company Profile",
                    ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
                    dbc.CardBody(
                        dcc.Loading(html.Div(id="company-profile"), color="#00bc8c"),
                    ),
                ], className="mb-3"),
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-calendar-alt me-2"),
                        "Upcoming Events",
                    ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
                    dbc.CardBody(
                        dcc.Loading(html.Div(id="upcoming-events"), color="#00bc8c"),
                    ),
                ], className="mb-3"),
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-exchange-alt me-2"),
                        "Recent Corporate Actions",
                    ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
                    dbc.CardBody(
                        dcc.Loading(html.Div(id="corporate-actions"), color="#00bc8c"),
                    ),
                ], className="mb-3"),
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-file-alt me-2"),
                        "SEC Filings",
                        html.Span(
                            " via EDGAR",
                            className="text-muted ms-2",
                            style={"fontSize": "0.72rem", "fontWeight": "400"},
                        ),
                    ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
                    dbc.CardBody(
                        dcc.Loading(
                            html.Div(id="sec-filings"),
                            color="#00bc8c",
                        ),
                        style={"maxHeight": "320px", "overflowY": "auto"},
                    ),
                ]),
            ], lg=5),
        ]),
    ])
# ─────────────────────────────────────────────────────────────────────────────
# Layout builder — macro dashboard tab
# ─────────────────────────────────────────────────────────────────────────────
def create_macro_dashboard_tab():
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-globe me-2 text-info"),
                    html.Span("MACRO DASHBOARD", style={"fontWeight": "700", "letterSpacing": "2px", "fontSize": "0.95rem"}),
                    html.Span(" — Private Credit Stress Monitor",
                              className="text-muted ms-2", style={"fontSize": "0.8rem"}),
                ]),
            ], lg=8),
            dbc.Col([
                dbc.Button([html.I(className="fas fa-sync-alt me-1"), "Refresh"],
                           id="macro-refresh-btn", color="success", outline=True,
                           size="sm", className="float-end"),
                html.Div(id="macro-last-updated",
                         className="text-muted text-end mt-1",
                         style={"fontSize": "0.75rem"}),
            ], lg=4),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col(html.Div(id="macro-signal-banner"), width=12),
        ], className="mb-3"),
        dbc.Row(id="macro-stat-cards", className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-chart-line me-2"),
                        "USO / GLD / HYG / LQD / DXY — Indexed to 100",
                        html.Span(" | 10yr Yield on right axis",
                                  className="text-muted ms-2", style={"fontSize": "0.75rem"}),
                    ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
                    dbc.CardBody(
                        dcc.Loading(
                            dcc.Graph(id="macro-main-chart",
                                      config={"displayModeBar": True,
                                              "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
                                      style={"height": "460px"}),
                            color="#00bc8c"
                        ),
                        className="p-1",
                    ),
                ], className="mb-3"),
            ], width=12),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-university me-2"),
                        "BDC Private Credit Proxy",
                    ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
                    dbc.CardBody(
                        dcc.Loading(html.Div(id="macro-bdc-table"), color="#00bc8c"),
                        className="p-2",
                    ),
                ], className="mb-3"),
            ], lg=5),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-map-signs me-2"),
                        "Signal Matrix",
                    ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
                    dbc.CardBody([
                        html.Table([
                            html.Thead(html.Tr([
                                html.Th("DXY"), html.Th("GLD"), html.Th("USO"),
                                html.Th("Regime Read"),
                            ])),
                            html.Tbody([
                                html.Tr([
                                    html.Td(r["DXY"], style={"textAlign": "center", "color": "#e2e8f0"}),
                                    html.Td(r["GLD"], style={"textAlign": "center", "color": "#e2e8f0"}),
                                    html.Td(r["USO"], style={"textAlign": "center", "color": "#e2e8f0"}),
                                    html.Td(r["read"], style={
                                        "color": "#10B981" if r["alert"] == "success" else
                                                 "#F59E0B" if r["alert"] == "warning" else "#EF4444",
                                        "fontSize": "0.78rem",
                                    }),
                                ]) for r in SIGNAL_MATRIX
                            ]),
                        ], className="macro-table w-100"),
                    ], className="p-2"),
                ], className="mb-3"),
            ], lg=7),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-check-circle me-2"),
                        "Demand Destruction Offset Indicators",
                    ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
                    dbc.CardBody([
                        html.Ul([
                            html.Li([html.Strong("USO >$90 for 6+ weeks"), " → demand destruction math activating"],
                                    style={"fontSize": "0.82rem", "color": "#cbd5e1", "marginBottom": "6px"}),
                            html.Li([html.Strong("Weekly jobless claims trending higher"), " → consumer pullback confirmed"],
                                    style={"fontSize": "0.82rem", "color": "#cbd5e1", "marginBottom": "6px"}),
                            html.Li([html.Strong("Core PCE MoM <0.2%"), " → Fed green light to cut"],
                                    style={"fontSize": "0.82rem", "color": "#cbd5e1", "marginBottom": "6px"}),
                            html.Li([html.Strong("10yr breaks below 4.00%"), " with conviction → bond model activates"],
                                    style={"fontSize": "0.82rem", "color": "#cbd5e1", "marginBottom": "6px"}),
                            html.Li([html.Strong("DXY up + GLD down"), " → classic risk-off, demand destruction intact"],
                                    style={"fontSize": "0.82rem", "color": "#cbd5e1", "marginBottom": "6px"}),
                            html.Li([html.Strong("DXY down + GLD up"), " → dollar credibility crisis, worst IG outcome"],
                                    style={"fontSize": "0.82rem", "color": "#EF4444", "marginBottom": "0"}),
                        ], style={"paddingLeft": "16px", "marginBottom": "0"}),
                    ], className="p-3"),
                ], className="mb-3"),
            ], lg=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-shield-alt me-2"),
                        "IG Portfolio Stress Scenarios  ",
                        html.Span("(YTW 4.75%, Duration ~7yr)",
                                  className="text-muted", style={"fontSize": "0.75rem"}),
                    ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
                    dbc.CardBody([
                        html.Table([
                            html.Thead(html.Tr([
                                html.Th("Scenario"),
                                html.Th("10yr Target"),
                                html.Th("IG Spread Δ"),
                                html.Th("Net Effect"),
                            ])),
                            html.Tbody([
                                html.Tr([
                                    html.Td(s["scenario"], style={"color": "#e2e8f0"}),
                                    html.Td(s["tenyr"],    style={"color": "#10B981"}),
                                    html.Td(s["spread"],   style={"color": "#F59E0B"}),
                                    html.Td(s["net"],      style={"color": s["net_color"], "fontWeight": "700"}),
                                ]) for s in STRESS_SCENARIOS
                            ]),
                        ], className="macro-table w-100"),
                    ], className="p-2"),
                ], className="mb-3"),
            ], lg=8),
        ]),
        dcc.Store(id="macro-data-store"),
        dcc.Interval(id="macro-auto-refresh", interval=15 * 60 * 1000, n_intervals=0),
    ], style={"padding": "4px 0"})
# ─────────────────────────────────────────────────────────────────────────────
# Main layout
# ─────────────────────────────────────────────────────────────────────────────
app.layout = dbc.Container([
    create_navbar(),
    dbc.Tabs([
        dbc.Tab(create_market_overview_tab(),   label="MARKET OVERVIEW",
                tab_id="tab-market",  label_style={"fontSize": "0.85rem"}),
        dbc.Tab(create_trading_dashboard_tab(), label="TRADING DASHBOARD",
                tab_id="tab-trading", label_style={"fontSize": "0.85rem"}),
        dbc.Tab(create_news_tab(),              label="NEWS & CORPORATE",
                tab_id="tab-news",    label_style={"fontSize": "0.85rem"}),
        dbc.Tab(create_macro_dashboard_tab(),   label="MACRO DASHBOARD",
                tab_id="tab-macro",   label_style={"fontSize": "0.85rem"}),
        dbc.Tab(create_insider_alerts_tab(),   label="INSIDER ALERTS",
                tab_id="tab-insider", label_style={"fontSize": "0.85rem", "color": "#F59E0B"}),
        dbc.Tab(create_options_flow_tab(),     label="OPTIONS FLOW",
                tab_id="tab-options", label_style={"fontSize": "0.85rem", "color": "#a78bfa"}),
        dbc.Tab(create_flow_data_tab(),        label="FLOW DATA",
                tab_id="tab-flow",    label_style={"fontSize": "0.85rem", "color": "#38bdf8"}),
    ], id="main-tabs", active_tab="tab-market", className="mb-3"),
    dcc.Store(id="active-symbol", data="AAPL"),
    dcc.Store(id="active-timeframe", data="1M"),
    dcc.Interval(id="auto-refresh", interval=60 * 1000, n_intervals=0),
], fluid=True, className="px-4 pb-4")
# ─────────────────────────────────────────────────────────────────────────────
# Rendering helpers — existing
# ─────────────────────────────────────────────────────────────────────────────
def render_index_card(item):
    price = item.get("price")
    if price is None:
        return dbc.Col(dbc.Card(dbc.CardBody(
            [html.H6(item["name"], className="text-muted mb-1"),
             html.Span("Unavailable", className="text-muted")],
            className="p-2 text-center",
        ), className="index-card"), xs=6, sm=4, lg=True)
    change = item.get("change", 0) or 0
    pct = item.get("changePct", 0) or 0
    color_cls = "text-gain" if change >= 0 else "text-loss"
    arrow = "\u25b2" if change >= 0 else "\u25bc"
    return dbc.Col(dbc.Card(dbc.CardBody([
        html.H6(item["name"], className="text-muted mb-1", style={"fontSize": "0.8rem"}),
        html.H4(f"{price:,.2f}", className="mb-0", style={"fontWeight": "700"}),
        html.Div([
            html.Span(f"{'+' if change >= 0 else ''}{change:.2f}", className=f"{color_cls} me-2",
                       style={"fontSize": "0.85rem"}),
            html.Span(f"{arrow} {abs(pct):.2f}%", className=color_cls,
                       style={"fontSize": "0.85rem"}),
        ]),
    ], className="p-2 text-center"), className="index-card"), xs=6, sm=4, lg=True)
def render_movers_table(quotes):
    if not quotes:
        return html.P("No data available.", className="text-muted small p-2")
    rows = []
    for i, q in enumerate(quotes[:8]):
        sym = q.get("symbol", "?")
        name = q.get("shortName", q.get("longName", ""))
        if len(name) > 20:
            name = name[:18] + ".."
        price = q.get("regularMarketPrice", 0)
        pct = q.get("regularMarketChangePercent", 0)
        color_cls = "text-gain" if pct >= 0 else "text-loss"
        rows.append(html.Tr([
            html.Td(str(i + 1), className="text-muted", style={"width": "25px"}),
            html.Td(html.Strong(sym), className="text-info"),
            html.Td(name, className="text-muted", style={"fontSize": "0.75rem"}),
            html.Td(f"{price:.2f}", className="text-end"),
            html.Td(f"{pct:+.2f}%", className=f"{color_cls} text-end fw-bold"),
        ]))
    return html.Table([
        html.Thead(html.Tr([
            html.Th("#", style={"width": "25px"}), html.Th("Sym"), html.Th("Name"),
            html.Th("Price", className="text-end"), html.Th("Chg%", className="text-end"),
        ], className="text-muted", style={"fontSize": "0.75rem"})),
        html.Tbody(rows),
    ], className="table table-sm table-borderless mb-0",
       style={"fontSize": "0.8rem"})
def render_news_item(item):
    content = item.get("content", item)
    title = content.get("title", "No title")
    summary = content.get("summary", "")
    pub_date = content.get("pubDate", "")
    provider = content.get("provider", {})
    if isinstance(provider, dict):
        provider = provider.get("displayName", "Unknown")
    url_obj = content.get("canonicalUrl", {})
    url = url_obj.get("url", "#") if isinstance(url_obj, dict) else str(url_obj) if url_obj else "#"
    if pub_date:
        try:
            dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            pub_date = dt.strftime("%b %d, %H:%M")
        except Exception:
            pub_date = str(pub_date)[:16]
    return dbc.Card([
        dbc.CardBody([
            html.H6(html.A(title, href=url, target="_blank",
                            className="text-info text-decoration-none"),
                     className="mb-1", style={"fontSize": "0.9rem"}),
            html.P(truncate_text(summary, 200), className="text-muted small mb-1"),
            html.Small(f"{provider} \u2022 {pub_date}", className="text-muted"),
        ], className="p-2"),
    ], className="mb-2 news-card")
def render_sec_filings(filings):
    """Render a styled list of SEC filings."""
    if not filings:
        return html.P("No filings found or EDGAR unavailable.", className="text-muted small")
    FORM_COLORS = {
        "10-K":    ("#63b3ed", "Annual Report"),
        "10-Q":    ("#4fd1c5", "Quarterly Report"),
        "8-K":     ("#f6ad55", "Current Report"),
        "DEF 14A": ("#a78bfa", "Proxy Statement"),
        "S-1":     ("#fc8181", "IPO Registration"),
    }
    rows = []
    for f in filings:
        form  = f["form"]
        color, label = FORM_COLORS.get(form, ("#94a3b8", form))
        rows.append(html.Tr([
            html.Td(
                dbc.Badge(form, style={
                    "backgroundColor": f"rgba({_hex_to_rgb(color)},0.15)",
                    "color": color,
                    "border": f"1px solid rgba({_hex_to_rgb(color)},0.4)",
                    "fontWeight": "600",
                    "fontSize": "0.7rem",
                    "padding": "3px 7px",
                    "borderRadius": "5px",
                }),
                style={"whiteSpace": "nowrap", "paddingRight": "8px"},
            ),
            html.Td(
                html.Span(label, style={"fontSize": "0.75rem", "color": "#64748b"}),
            ),
            html.Td(
                html.Span(f["date"], style={"fontSize": "0.75rem", "color": "#94a3b8",
                                             "fontFamily": "JetBrains Mono, monospace"}),
            ),
            html.Td(
                html.A(
                    [html.I(className="fas fa-external-link-alt me-1"), "View"],
                    href=f["url"], target="_blank",
                    style={"fontSize": "0.72rem", "color": "#63b3ed",
                           "textDecoration": "none"},
                ),
                className="text-end",
            ),
        ], style={"borderBottom": "1px solid rgba(255,255,255,0.04)"}))
    return html.Table(
        [html.Thead(html.Tr([
            html.Th("Form",        style={"color": "#475569", "fontSize": "0.7rem", "fontWeight": "600", "letterSpacing": "0.5px", "paddingBottom": "6px"}),
            html.Th("Type",        style={"color": "#475569", "fontSize": "0.7rem", "fontWeight": "600", "letterSpacing": "0.5px", "paddingBottom": "6px"}),
            html.Th("Filed",       style={"color": "#475569", "fontSize": "0.7rem", "fontWeight": "600", "letterSpacing": "0.5px", "paddingBottom": "6px"}),
            html.Th("",            style={"paddingBottom": "6px"}),
        ])),
         html.Tbody(rows)],
        className="w-100", style={"borderCollapse": "collapse"},
    )
def _hex_to_rgb(hex_color):
    """Convert #rrggbb to 'r,g,b' string for use in rgba()."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"
def render_stats_panel(info):
    if not info:
        return html.P("No data available.", className="text-muted")
    def fmt_stat(val, prefix="", suffix="", decimals=2):
        if val is None or val == "N/A":
            return "N/A"
        try:
            return f"{prefix}{float(val):,.{decimals}f}{suffix}"
        except (ValueError, TypeError):
            return str(val)
    stats = [
        ("Market Cap", fmt_number(safe_get(info, "marketCap", None))),
        ("P/E (TTM)", fmt_stat(safe_get(info, "trailingPE", None))),
        ("P/E (Fwd)", fmt_stat(safe_get(info, "forwardPE", None))),
        ("52W High", fmt_stat(safe_get(info, "fiftyTwoWeekHigh", None), prefix="$")),
        ("52W Low", fmt_stat(safe_get(info, "fiftyTwoWeekLow", None), prefix="$")),
        ("Avg Volume", fmt_number(safe_get(info, "averageVolume", None))),
        ("Beta", fmt_stat(safe_get(info, "beta", None))),
        ("Div Yield", fmt_stat(
            (safe_get(info, "dividendYield", None) or 0) * 100 if safe_get(info, "dividendYield", None) else None,
            suffix="%")),
        ("EPS (TTM)", fmt_stat(safe_get(info, "trailingEps", None), prefix="$")),
        ("Target", fmt_stat(safe_get(info, "targetMeanPrice", None), prefix="$")),
        ("Analyst", str(safe_get(info, "recommendationKey", "N/A")).upper()),
    ]
    return html.Div([
        html.Div([
            html.Span(label, className="stat-label"),
            html.Span(str(value), className="stat-value"),
        ], className="stat-row") for label, value in stats
    ])
def render_extra_cards(data, tickers_map, price_fmt="{:.2f}"):
    """Render a compact horizontal strip of price/change cards for a ticker group."""
    cards = []
    for sym, label in tickers_map.items():
        d       = data.get(sym, {})
        price   = d.get("price")
        chg_pct = d.get("chg_pct", 0) or 0
        chg     = d.get("chg", 0) or 0
        color   = "#10B981" if chg_pct >= 0 else "#EF4444"
        arrow   = "▲" if chg_pct >= 0 else "▼"
        try:
            price_str = ("$" + price_fmt.format(price)) if price is not None else "—"
        except Exception:
            price_str = "—"
        cards.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.Div(label, style={"fontSize": "0.7rem", "color": "#64748b",
                                               "marginBottom": "2px", "whiteSpace": "nowrap"}),
                        html.Div(price_str,
                                 style={"fontSize": "0.95rem", "fontWeight": "700",
                                        "color": "#e2e8f0",
                                        "fontFamily": "JetBrains Mono, monospace"}),
                        html.Div(
                            f"{arrow} {abs(chg_pct):.2f}%",
                            style={"fontSize": "0.75rem", "color": color, "fontWeight": "600"},
                        ),
                    ], className="p-2"),
                    style={"borderTop": f"2px solid {color}"},
                ),
                xs=6, sm=4, lg=True, className="mb-2",
            )
        )
    return cards

def render_yield_cards(data, yields_map):
    """Render compact yield cards showing level in % and change in basis points."""
    cards = []
    for sym, label in yields_map.items():
        d     = data.get(sym, {})
        price = d.get("price")          # yield level, e.g. 4.52 means 4.52%
        chg   = d.get("chg", 0) or 0   # absolute change in yield (pct-points)
        bps   = round(chg * 100, 1)    # convert to basis points
        # Rising yields = bad for bond prices → red; falling → green
        color = "#EF4444" if bps > 0 else "#10B981" if bps < 0 else "#94a3b8"
        arrow = "▲" if bps > 0 else "▼" if bps < 0 else "—"
        price_str = f"{price:.2f}%" if price is not None else "—"
        bps_str   = f"{arrow} {abs(bps):.1f}bps"
        cards.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.Div(label, style={"fontSize": "0.7rem", "color": "#64748b",
                                               "marginBottom": "2px", "whiteSpace": "nowrap"}),
                        html.Div(price_str,
                                 style={"fontSize": "0.95rem", "fontWeight": "700",
                                        "color": "#e2e8f0",
                                        "fontFamily": "JetBrains Mono, monospace"}),
                        html.Div(bps_str, style={"fontSize": "0.75rem", "color": color,
                                                  "fontWeight": "600"}),
                    ], className="p-2"),
                    style={"borderTop": f"2px solid {color}"},
                ),
                xs=6, sm=3, lg=True, className="mb-2",
            )
        )
    return cards

def render_sector_cards(sectors):
    """Render clickable sector cards using pattern-matching IDs."""
    if not sectors:
        return html.P("Sector data unavailable.", className="text-muted small")
    cards = []
    for etf, label in SECTOR_ETFS.items():
        chg = sectors.get(etf, 0) or 0
        color  = "#10B981" if chg >= 0 else "#EF4444"
        arrow  = "▲" if chg >= 0 else "▼"
        cards.append(
            dbc.Col(
                dbc.Button(
                    [
                        html.Div(label, style={"fontSize": "0.72rem", "color": "#000000", "marginBottom": "2px"}),
                        html.Div(
                            f"{arrow} {abs(chg):.2f}%",
                            style={"fontSize": "1rem", "fontWeight": "700", "color": color},
                        ),
                    ],
                    id={"type": "sector-btn", "index": etf},
                    n_clicks=0,
                    color="dark",
                    className="w-100 text-start",
                    style={"borderTop": f"3px solid {color}", "borderRadius": "6px",
                           "padding": "8px 10px", "cursor": "pointer"},
                ),
                xs=6, sm=4, md=3, lg=2, className="mb-2",
            )
        )
    return dbc.Row(cards, className="g-2")

def render_sector_movers(movers, sector_name):
    """Render advancing / declining two-column breakdown for a sector."""
    if not movers:
        return html.Div()

    def stock_row(s):
        chg = s["chg_pct"]
        color = "#10B981" if chg >= 0 else "#EF4444"
        arrow = "▲" if chg >= 0 else "▼"
        return html.Div([
            html.Span(s["symbol"], style={"fontWeight": "600", "color": "#e2e8f0",
                                          "fontSize": "0.85rem", "minWidth": "60px",
                                          "display": "inline-block"}),
            html.Span(f"  ${s['price']:.2f}", style={"color": "#94a3b8", "fontSize": "0.8rem",
                                                      "marginLeft": "6px"}),
            html.Span(f"  {arrow}{abs(chg):.2f}%", style={"color": color, "fontSize": "0.8rem",
                                                             "marginLeft": "6px", "fontWeight": "600"}),
        ], style={"padding": "3px 0", "borderBottom": "1px solid rgba(255,255,255,0.04)"})

    advancing = movers.get("advancing", [])
    declining = movers.get("declining", [])
    return html.Div([
        html.Div([
            html.Span(f"  {sector_name} — Stock Breakdown",
                      style={"color": "#94a3b8", "fontSize": "0.8rem", "fontStyle": "italic"}),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-arrow-up me-1", style={"color": "#10B981"}),
                    html.Span(f"Advancing ({len(advancing)})",
                              style={"color": "#10B981", "fontWeight": "600", "fontSize": "0.85rem"}),
                ], className="mb-2"),
                html.Div([stock_row(s) for s in advancing] or [html.Span("None", className="text-muted small")]),
            ], md=6),
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-arrow-down me-1", style={"color": "#EF4444"}),
                    html.Span(f"Declining ({len(declining)})",
                              style={"color": "#EF4444", "fontWeight": "600", "fontSize": "0.85rem"}),
                ], className="mb-2"),
                html.Div([stock_row(s) for s in declining] or [html.Span("None", className="text-muted small")]),
            ], md=6),
        ]),
    ], style={"padding": "12px", "background": "rgba(255,255,255,0.03)",
               "borderRadius": "6px", "marginTop": "8px"})

def render_insider_summary(purchases):
    if not purchases:
        return html.Div()
    total_val   = sum(p["value"] for p in purchases)
    largest     = max(purchases, key=lambda x: x["value"])
    ticker_cnts = {}
    for p in purchases:
        ticker_cnts[p["symbol"]] = ticker_cnts.get(p["symbol"], 0) + 1
    most_active = max(ticker_cnts, key=ticker_cnts.get)
    specs = [
        ("fas fa-bell",        "#F59E0B", str(len(purchases)),                         "Total Alerts"),
        ("fas fa-dollar-sign", "#10B981", f"${total_val:,.0f}",                        "Total Insider Buying"),
        ("fas fa-trophy",      "#63b3ed", f"{largest['symbol']} — ${largest['value']:,.0f}", "Largest Purchase"),
        ("fas fa-fire",        "#EF4444", f"{most_active} ({ticker_cnts[most_active]} buys)", "Most Active"),
    ]
    return dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div([html.I(className=f"{icon} me-2", style={"color": color}),
                      html.Span(label, style={"fontSize": "0.72rem", "color": "#64748b"})],
                     className="mb-1"),
            html.Div(val, style={"fontSize": "0.88rem", "fontWeight": "600",
                                 "color": "#e2e8f0", "fontFamily": "JetBrains Mono, monospace"}),
        ], className="p-2")), lg=3, className="mb-2")
        for icon, color, val, label in specs
    ])

def render_insider_table(purchases):
    if not purchases:
        return html.P(
            "No open-market purchases found in the selected period (min $10 K).",
            className="text-muted small p-3",
        )
    TH = {"color": "#475569", "fontSize": "0.7rem", "fontWeight": "600",
          "letterSpacing": "0.5px", "paddingBottom": "8px"}
    header = html.Thead(html.Tr([
        html.Th(c, style=TH)
        for c in ["Ticker", "Insider", "Role", "Date", "Shares", "$/Share", "Total Value", "Signal"]
    ]))
    rows = []
    for p in purchases:
        val = p["value"]
        if val >= 1_000_000:
            badge = dbc.Badge("MAJOR BUY", color="danger",   pill=True)
        elif val >= 100_000:
            badge = dbc.Badge("NOTABLE",   color="warning",  pill=True)
        else:
            badge = dbc.Badge("ROUTINE",   color="secondary", pill=True)
        MONO = {"fontFamily": "JetBrains Mono, monospace", "fontSize": "0.82rem"}
        rows.append(html.Tr([
            html.Td(html.Strong(p["symbol"], style={"color": "#4fd1c5"})),
            html.Td(p["name"],  style={"fontSize": "0.82rem"}),
            html.Td(p["role"],  style={"fontSize": "0.75rem", "color": "#64748b"}),
            html.Td(p["date"],  style=MONO),
            html.Td(f"{p['shares']:,.0f}", style={**MONO, "textAlign": "right"}),
            html.Td(f"${p['price']:,.2f}", style={**MONO, "textAlign": "right"}),
            html.Td(html.Strong(f"${val:,.0f}",
                                style={"color": "#10B981" if val >= 100_000 else "#e2e8f0"}),
                    style={**MONO, "textAlign": "right"}),
            html.Td([badge, html.A(" Form 4", href=p["url"], target="_blank",
                                   className="ms-2",
                                   style={"fontSize": "0.72rem", "color": "#63b3ed"})]),
        ], style={"borderBottom": "1px solid rgba(255,255,255,0.04)"}))
    return html.Div(
        html.Table([header, html.Tbody(rows)], className="w-100",
                   style={"borderCollapse": "collapse"}),
        style={"overflowX": "auto"},
    )

def render_options_flow_summary(flow):
    if not flow:
        return html.Div()
    calls    = [f for f in flow if f["type"] == "CALL"]
    puts     = [f for f in flow if f["type"] == "PUT"]
    call_prem = sum(f["premium"] for f in calls)
    put_prem  = sum(f["premium"] for f in puts)
    total_prem = call_prem + put_prem
    bias_pct   = (call_prem / total_prem * 100) if total_prem else 50
    bias_color = "#10B981" if bias_pct >= 55 else "#EF4444" if bias_pct <= 45 else "#F59E0B"
    bias_label = "BULLISH" if bias_pct >= 55 else "BEARISH" if bias_pct <= 45 else "NEUTRAL"
    sweeps = sum(1 for f in flow if f["signal"] == "SWEEP")
    specs = [
        ("fas fa-bolt",         "#F59E0B", str(len(flow)),              "Unusual Contracts"),
        ("fas fa-phone-volume", "#10B981", f"${call_prem:,.0f}",        "Call Premium Flow"),
        ("fas fa-shield-alt",   "#EF4444", f"${put_prem:,.0f}",         "Put Premium Flow"),
        ("fas fa-crosshairs",   bias_color, f"{bias_label} ({bias_pct:.0f}% calls)", "Flow Bias"),
        ("fas fa-fire",         "#a78bfa",  str(sweeps),                "Sweeps Detected"),
    ]
    return dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div([html.I(className=f"{icon} me-2", style={"color": color}),
                      html.Span(label, style={"fontSize": "0.72rem", "color": "#64748b"})],
                     className="mb-1"),
            html.Div(val, style={"fontSize": "0.88rem", "fontWeight": "600",
                                 "color": "#e2e8f0", "fontFamily": "JetBrains Mono, monospace"}),
        ], className="p-2")), lg=2, sm=4, className="mb-2")
        for icon, color, val, label in specs
    ])

def render_options_flow_table(flow, filter_type="ALL"):
    rows_data = [f for f in flow if filter_type == "ALL" or f["type"] == filter_type]
    if not rows_data:
        return html.P("No unusual options activity found.", className="text-muted small p-3")

    TH = {"color": "#475569", "fontSize": "0.7rem", "fontWeight": "600",
          "letterSpacing": "0.5px", "paddingBottom": "8px"}
    header = html.Thead(html.Tr([
        html.Th(c, style=TH)
        for c in ["Ticker", "Type", "Strike", "Spot", "Expiry", "Vol", "OI",
                  "Vol/OI", "IV", "Last", "Premium", "Signal"]
    ]))

    SIGNAL_COLORS = {"SWEEP": "#EF4444", "UNUSUAL": "#F59E0B", "NOTABLE": "#94a3b8"}
    SIGNAL_BADGE  = {"SWEEP": "danger",  "UNUSUAL": "warning",  "NOTABLE": "secondary"}
    rows = []
    for f in rows_data:
        call = f["type"] == "CALL"
        type_badge = dbc.Badge(
            f["type"],
            color="success" if call else "danger",
            pill=True,
            style={"fontSize": "0.68rem"},
        )
        sig_badge = dbc.Badge(
            f["signal"],
            color=SIGNAL_BADGE[f["signal"]],
            pill=True,
            style={"fontSize": "0.68rem"},
        )
        iv_pct  = f"{f['iv'] * 100:.1f}%" if f["iv"] < 10 else f"{f['iv']:.1f}%"
        MONO    = {"fontFamily": "JetBrains Mono, monospace", "fontSize": "0.82rem"}
        itm_style = {"color": "#4fd1c5"} if f["itm"] else {}
        rows.append(html.Tr([
            html.Td(html.Strong(f["symbol"], style={"color": "#4fd1c5"})),
            html.Td(type_badge),
            html.Td(f"${f['strike']:,.2f}",  style={**MONO, **itm_style}),
            html.Td(f"${f['spot']:,.2f}",    style={**MONO, "color": "#64748b"}),
            html.Td(f["exp"],                style={**MONO, "color": "#94a3b8"}),
            html.Td(f"{f['vol']:,}",         style={**MONO, "textAlign": "right"}),
            html.Td(f"{f['oi']:,}",          style={**MONO, "textAlign": "right", "color": "#64748b"}),
            html.Td(
                html.Strong(
                    f"{f['vol_oi']:.2f}x" if f["vol_oi"] != float("inf") else "NEW",
                    style={"color": SIGNAL_COLORS[f["signal"]]},
                ),
                style={**MONO, "textAlign": "right"},
            ),
            html.Td(iv_pct,                  style={**MONO, "color": "#a78bfa"}),
            html.Td(f"${f['last']:.2f}",     style=MONO),
            html.Td(
                html.Strong(f"${f['premium']:,.0f}",
                            style={"color": "#10B981" if call else "#EF4444"}),
                style={**MONO, "textAlign": "right"},
            ),
            html.Td(sig_badge),
        ], style={"borderBottom": "1px solid rgba(255,255,255,0.04)"}))

    return html.Div(
        html.Table([header, html.Tbody(rows)], className="w-100",
                   style={"borderCollapse": "collapse"}),
        style={"overflowX": "auto"},
    )

def render_cot_chart_and_table(cot_data):
    if not cot_data:
        return build_empty_figure("No COT data"), html.P("No data.", className="text-muted")
    labels     = [d["label"] for d in cot_data]
    nets       = [d["net"]   for d in cot_data]
    bar_colors = ["#10B981" if n >= 0 else "#EF4444" for n in nets]
    fig = go.Figure(go.Bar(
        y=labels, x=nets, orientation="h",
        marker=dict(color=bar_colors),
        text=[f"{n:+,.0f}" for n in nets], textposition="outside",
        hovertemplate="<b>%{y}</b><br>Net: %{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        margin=dict(l=100, r=80, t=10, b=30), height=320,
        xaxis=dict(
            title="Net Speculator Position (contracts)",
            gridcolor="rgba(255,255,255,0.04)", tickfont=dict(size=9, color="#64748b"),
            zeroline=True, zerolinecolor="rgba(255,255,255,0.25)", zerolinewidth=1,
        ),
        yaxis=dict(tickfont=dict(size=10, color="#e2e8f0")),
        paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
    )
    TH   = {"color": "#475569", "fontSize": "0.7rem", "fontWeight": "600",
             "letterSpacing": "0.5px", "paddingBottom": "8px"}
    MONO = {"fontFamily": "JetBrains Mono, monospace", "fontSize": "0.82rem"}
    header = html.Thead(html.Tr([html.Th(c, style=TH) for c in
        ["Market", "Report Date", "Net Position", "WoW Δ", "% OI Long", "% OI Short", "Bias"]]))
    rows = []
    for d in cot_data:
        net, chg = d["net"], d["chg_net"]
        rows.append(html.Tr([
            html.Td(html.Strong(d["label"], style={"color": d["color"]})),
            html.Td(d["date"], style={**MONO, "color": "#64748b"}),
            html.Td(html.Strong(f"{net:+,.0f}",
                                style={"color": "#10B981" if net >= 0 else "#EF4444"}),
                    style={**MONO, "textAlign": "right"}),
            html.Td(f"{chg:+,.0f}", style={**MONO, "textAlign": "right",
                                           "color": "#10B981" if chg >= 0 else "#EF4444"}),
            html.Td(f"{d['pct_long']:.1f}%",  style={**MONO, "textAlign": "right", "color": "#10B981"}),
            html.Td(f"{d['pct_short']:.1f}%", style={**MONO, "textAlign": "right", "color": "#EF4444"}),
            html.Td(dbc.Badge("LONG" if net >= 0 else "SHORT",
                              color="success" if net >= 0 else "danger", pill=True)),
        ], style={"borderBottom": "1px solid rgba(255,255,255,0.04)"}))
    table = html.Div(html.Table([header, html.Tbody(rows)], className="w-100",
                                style={"borderCollapse": "collapse"}),
                     style={"overflowX": "auto"})
    return fig, table

def render_13f_table(meta, holdings):
    if not holdings:
        return html.P("No holdings found — filing may use a non-standard format.",
                      className="text-muted small p-3")
    date_str = meta.get("date", "") if meta else ""
    total    = meta.get("total", 0)  if meta else 0
    TH   = {"color": "#475569", "fontSize": "0.7rem", "fontWeight": "600",
             "letterSpacing": "0.5px", "paddingBottom": "8px"}
    MONO = {"fontFamily": "JetBrains Mono, monospace", "fontSize": "0.82rem"}
    header = html.Thead(html.Tr([html.Th(c, style=TH)
        for c in ["#", "Issuer", "CUSIP", "Shares", "Market Value", "% Portfolio"]]))
    rows = []
    for i, h in enumerate(holdings[:30], 1):
        bar_w = min(int(h["pct"] * 5), 100)
        rows.append(html.Tr([
            html.Td(str(i), style={"color": "#64748b", "fontSize": "0.75rem"}),
            html.Td(h["name"], style={"fontSize": "0.85rem", "fontWeight": "600"}),
            html.Td(h["cusip"], style={"fontSize": "0.72rem", "color": "#475569",
                                       "fontFamily": "monospace"}),
            html.Td(f"{h['shares']:,.0f}", style={**MONO, "textAlign": "right", "color": "#64748b"}),
            html.Td(html.Strong(f"${h['value']:,.0f}"), style={**MONO, "textAlign": "right"}),
            html.Td([
                html.Span(f"{h['pct']:.2f}%", style={"fontSize": "0.78rem", "marginRight": "6px"}),
                html.Div(style={"display": "inline-block", "width": f"{bar_w}px", "height": "6px",
                                "backgroundColor": "#00bc8c", "borderRadius": "3px",
                                "opacity": "0.7", "verticalAlign": "middle"}),
            ]),
        ], style={"borderBottom": "1px solid rgba(255,255,255,0.04)"}))
    return html.Div([
        html.Div([
            html.Span(f"As of: {date_str}", className="text-muted me-3", style={"fontSize": "0.78rem"}),
            html.Span(f"Total AUM: ${total/1e9:.2f}B", className="text-info", style={"fontSize": "0.78rem"}),
        ], className="mb-2"),
        html.Div(html.Table([header, html.Tbody(rows)], className="w-100",
                            style={"borderCollapse": "collapse"}),
                 style={"overflowX": "auto"}),
    ])

def render_short_interest_table(data):
    if not data:
        return html.P("No short interest data.", className="text-muted small p-3")
    TH   = {"color": "#475569", "fontSize": "0.7rem", "fontWeight": "600",
             "letterSpacing": "0.5px", "paddingBottom": "8px"}
    MONO = {"fontFamily": "JetBrains Mono, monospace", "fontSize": "0.82rem"}
    header = html.Thead(html.Tr([html.Th(c, style=TH) for c in
        ["Symbol", "Company", "Price", "Shares Short", "Short % Float",
         "Days to Cover", "vs Prior Month", "Signal"]]))
    rows = []
    for d in data:
        pf, dc, chg = d["pct_float"], d["days_cover"], d["change_pct"]
        if pf >= 25:   sig = dbc.Badge("HEAVILY SHORTED", color="danger",    pill=True, style={"fontSize": "0.68rem"})
        elif pf >= 15: sig = dbc.Badge("HIGH SHORT",      color="warning",   pill=True, style={"fontSize": "0.68rem"})
        elif pf >= 10: sig = dbc.Badge("ELEVATED",        color="secondary", pill=True, style={"fontSize": "0.68rem"})
        else:          sig = dbc.Badge("NORMAL",           color="secondary", pill=True, style={"fontSize": "0.68rem", "opacity": "0.5"})
        rows.append(html.Tr([
            html.Td(html.Strong(d["symbol"], style={"color": "#4fd1c5"})),
            html.Td(d["name"], style={"fontSize": "0.8rem", "color": "#94a3b8"}),
            html.Td(f"${d['price']:.2f}", style=MONO),
            html.Td(f"{d['shares_short']:,.0f}", style={**MONO, "textAlign": "right", "color": "#EF4444"}),
            html.Td(html.Strong(f"{pf:.1f}%", style={
                "color": "#EF4444" if pf >= 20 else "#F59E0B" if pf >= 10 else "#94a3b8"}),
                style={**MONO, "textAlign": "right"}),
            html.Td(f"{dc:.1f}d", style={**MONO, "textAlign": "right",
                                          "color": "#EF4444" if dc >= 10 else "#e2e8f0"}),
            html.Td(html.Span(f"{chg:+.1f}%", style={
                "color": "#EF4444" if chg > 5 else "#10B981" if chg < -5 else "#94a3b8",
                "fontSize": "0.82rem", "fontFamily": "monospace"})),
            html.Td(sig),
        ], style={"borderBottom": "1px solid rgba(255,255,255,0.04)"}))
    return html.Div(html.Table([header, html.Tbody(rows)], className="w-100",
                               style={"borderCollapse": "collapse"}),
                    style={"overflowX": "auto"})

def render_etf_flows_table(data):
    if not data:
        return html.P("No ETF data available.", className="text-muted small p-3")
    CATEGORY_ORDER = ["Equity", "Bond", "Commodity", "Sector", "Volatility"]
    by_cat = {}
    for d in data:
        by_cat.setdefault(d["category"], []).append(d)
    TH   = {"color": "#475569", "fontSize": "0.7rem", "fontWeight": "600",
             "letterSpacing": "0.5px", "paddingBottom": "8px"}
    MONO = {"fontFamily": "JetBrains Mono, monospace", "fontSize": "0.82rem"}
    header = html.Thead(html.Tr([html.Th(c, style=TH) for c in
        ["ETF", "Name", "Price", "AUM", "1D %", "1W %", "Vol / Avg", "Activity"]]))
    rows = []
    for cat in CATEGORY_ORDER:
        items = by_cat.get(cat, [])
        if not items:
            continue
        rows.append(html.Tr([html.Td(cat.upper(), colSpan=8, style={
            "color": "#475569", "fontSize": "0.68rem", "fontWeight": "700",
            "letterSpacing": "1px", "paddingTop": "10px", "paddingBottom": "4px",
            "borderBottom": "1px solid rgba(255,255,255,0.08)"})]))
        for d in items:
            d1, d1w, vr = d["chg_1d"], d["chg_1w"], d["vol_ratio"]
            activity = ("HIGH VOL" if vr >= 1.5 else "LOW VOL" if vr < 0.5 else "NORMAL")
            act_color = ("warning" if vr >= 1.5 else "secondary")
            aum_str   = (f"${d['aum']/1e9:.1f}B" if d["aum"] >= 1e9
                         else f"${d['aum']/1e6:.0f}M")
            rows.append(html.Tr([
                html.Td(html.Strong(d["symbol"], style={"color": "#4fd1c5"})),
                html.Td(d["name"], style={"fontSize": "0.8rem", "color": "#94a3b8"}),
                html.Td(f"${d['price']:.2f}", style=MONO),
                html.Td(aum_str, style={**MONO, "color": "#64748b"}),
                html.Td(html.Span(f"{d1:+.2f}%", style={
                    "color": "#10B981" if d1 >= 0 else "#EF4444", **MONO})),
                html.Td(html.Span(f"{d1w:+.2f}%", style={
                    "color": "#10B981" if d1w >= 0 else "#EF4444", **MONO})),
                html.Td(f"{vr:.2f}x", style={**MONO,
                    "color": "#F59E0B" if vr >= 1.5 else "#64748b"}),
                html.Td(dbc.Badge(activity, color=act_color, pill=True,
                                  style={"fontSize": "0.68rem"})),
            ], style={"borderBottom": "1px solid rgba(255,255,255,0.04)"}))
    return html.Div(html.Table([header, html.Tbody(rows)], className="w-100",
                               style={"borderCollapse": "collapse"}),
                    style={"overflowX": "auto"})

def build_sector_heatmap(sector_data):
    if not sector_data:
        return go.Figure().update_layout(**CHART_LAYOUT, paper_bgcolor="rgba(0,0,0,0)")
    sectors = list(sector_data.keys())
    names = [SECTOR_ETFS[s] for s in sectors]
    values = [sector_data[s] for s in sectors]
    fig = go.Figure(data=go.Heatmap(
        z=[values],
        x=names,
        y=[""],
        text=[[f"{n}<br>{v:+.2f}%" for n, v in zip(names, values)]],
        texttemplate="%{text}",
        textfont={"size": 10, "family": "Inter, sans-serif"},
        colorscale=[
            [0.0, "rgba(252,129,129,0.85)"],
            [0.4, "rgba(30,41,59,0.6)"],
            [0.5, "rgba(30,41,59,0.4)"],
            [0.6, "rgba(30,41,59,0.6)"],
            [1.0, "rgba(79,209,197,0.85)"],
        ],
        zmid=0,
        showscale=False,
        hovertemplate="<b>%{x}</b><br>%{z:+.2f}%<extra></extra>",
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        margin=dict(l=10, r=10, t=10, b=40),
        height=130,
        xaxis=dict(tickangle=-30, tickfont=dict(size=9, color="#64748b"), showgrid=False, linecolor="rgba(255,255,255,0.06)"),
        yaxis=dict(visible=False),
    )
    return fig
CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#94a3b8"),
    hoverlabel=dict(
        bgcolor="rgba(10,18,35,0.95)",
        bordercolor="rgba(99,179,237,0.3)",
        font=dict(family="Inter, sans-serif", size=12, color="#e2e8f0"),
    ),
    legend_bgcolor="rgba(0,0,0,0)",
    legend_bordercolor="rgba(255,255,255,0.06)",
)

AXIS_STYLE = dict(
    gridcolor="rgba(255,255,255,0.04)",
    zerolinecolor="rgba(255,255,255,0.06)",
    tickfont=dict(size=10, color="#64748b"),
    linecolor="rgba(255,255,255,0.06)",
)
XAXIS_STYLE = dict(
    **AXIS_STYLE,
    showspikes=True, spikecolor="rgba(99,179,237,0.3)",
    spikethickness=1, spikedash="dot",
)

def build_empty_figure(msg="No data available"):
    fig = go.Figure()
    fig.update_layout(
        **CHART_LAYOUT,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=50, r=20, t=30, b=20),
        annotations=[dict(
            text=msg, xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=13, color="#475569", family="Inter, sans-serif"),
        )],
    )
    return fig
# ─────────────────────────────────────────────────────────────────────────────
# Rendering helpers — macro dashboard
# ─────────────────────────────────────────────────────────────────────────────
def build_macro_chart(df, spreads_df=None):
    if df is None or df.empty:
        return build_empty_figure("Loading macro data...")
    fig = go.Figure()
    for ticker, meta in MACRO_TICKERS.items():
        col = ticker if ticker in df.columns else None
        if col is None:
            continue
        s = df[col].dropna()
        if len(s) == 0:
            continue
        normed = (s / s.iloc[0]) * 100
        fig.add_trace(go.Scatter(
            x=normed.index, y=normed.values,
            name=meta["label"],
            line=dict(color=meta["color"], width=2),
            mode="lines",
            hovertemplate=f"<b>{meta['label']}</b><br>%{{x|%b %Y}}<br>Indexed: %{{y:.1f}}<extra></extra>",
        ))
    if TREASURY_TICKER in df.columns:
        ty = df[TREASURY_TICKER].dropna()
        fig.add_trace(go.Scatter(
            x=ty.index, y=ty.values,
            name="10yr Yield (%)",
            line=dict(color="#7C3AED", width=2, dash="dot"),
            mode="lines",
            yaxis="y2",
            hovertemplate="<b>10yr Yield</b><br>%{x|%b %Y}<br>%{y:.2f}%<extra></extra>",
        ))
    fred_active = False
    if spreads_df is not None and not spreads_df.empty:
        fred_active = True
        if "HY_OAS" in spreads_df.columns:
            fig.add_trace(go.Scatter(
                x=spreads_df.index, y=spreads_df["HY_OAS"],
                name="HY OAS (%)",
                line=dict(color="#F97316", width=1.5, dash="dash"),
                mode="lines",
                yaxis="y3",
                hovertemplate="<b>HY OAS</b><br>%{x|%b %Y}<br>%{y:.2f}%<extra></extra>",
            ))
        if "IG_OAS" in spreads_df.columns:
            fig.add_trace(go.Scatter(
                x=spreads_df.index, y=spreads_df["IG_OAS"],
                name="IG OAS (%)",
                line=dict(color="#A78BFA", width=1.5, dash="dash"),
                mode="lines",
                yaxis="y3",
                hovertemplate="<b>IG OAS</b><br>%{x|%b %Y}<br>%{y:.2f}%<extra></extra>",
            ))
        if "HYIG_SPREAD" in spreads_df.columns:
            fig.add_trace(go.Scatter(
                x=spreads_df.index, y=spreads_df["HYIG_SPREAD"],
                name="HY–IG Spread (%)",
                line=dict(color="#34D399", width=2),
                mode="lines",
                yaxis="y3",
                hovertemplate="<b>HY–IG Spread</b><br>%{x|%b %Y}<br>%{y:.2f}%<extra></extra>",
            ))
    y3_config = dict(
        title=dict(text="OAS Spread (%)", font=dict(size=10, color="#F97316")),
        overlaying="y",
        side="right",
        position=0.97,
        showgrid=False,
        tickformat=".2f",
        tickfont=dict(size=9, color="#F97316"),
    ) if fred_active else dict(visible=False, overlaying="y", side="right")
    fig.update_layout(
        **CHART_LAYOUT,
        margin=dict(l=55, r=90, t=20, b=60),
        height=460,
        legend_orientation="h", legend_y=-0.16, legend_x=0,
        hovermode="x unified",
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.04)",
            tickfont=dict(size=10, color="#64748b"),
            linecolor="rgba(255,255,255,0.06)",
        ),
        yaxis=dict(
            title=dict(text="Indexed (100 = 2yr ago)", font=dict(size=11, color="#64748b")),
            gridcolor="rgba(255,255,255,0.04)",
            tickfont=dict(size=10, color="#64748b"),
        ),
        yaxis2=dict(
            title=dict(text="10yr Yield (%)", font=dict(size=11, color="#a78bfa")),
            overlaying="y",
            side="right",
            showgrid=False,
            tickformat=".2f",
            tickfont=dict(size=10, color="#a78bfa"),
            position=1.0,
        ),
        yaxis3=y3_config,
    )
    return fig
def build_bdc_table(rows):
    if not rows:
        return html.P("Loading BDC data...", className="text-muted small")
    header = html.Thead(html.Tr([
        html.Th(c) for c in ["Ticker", "Price", "Book/NAV", "P/NAV", "Signal"]
    ]))
    body_rows = []
    for r in rows:
        sig = r.get("Signal", "–")
        sig_color = ("#10B981" if "Green"  in sig else
                     "#F59E0B" if "Yellow" in sig else
                     "#EF4444" if "Red"    in sig else "#6c757d")
        body_rows.append(html.Tr([
            html.Td(html.Strong(r["Ticker"]), style={"color": "#38bdf8"}),
            html.Td(r["Price"]),
            html.Td(r["Book/NAV"], style={"color": "#6c757d"}),
            html.Td(r["P/NAV"]),
            html.Td(sig, style={"color": sig_color, "fontWeight": "600"}),
        ]))
    return html.Table(
        [header, html.Tbody(body_rows)],
        className="macro-table w-100",
    )
def build_macro_stat_cards(df):
    if df is None or df.empty:
        return []
    specs = [
        ("USO",        "🛢️ USO (Oil)",   "#EF4444"),
        ("GLD",        "🥇 GLD (Gold)",  "#F59E0B"),
        ("DX-Y.NYB",   "💵 DXY",         "#0EA5E9"),
        (TREASURY_TICKER, "📈 10yr Yield", "#7C3AED"),
    ]
    cards = []
    for ticker, label, color in specs:
        try:
            col    = df[ticker].dropna()
            latest = col.iloc[-1]
            prev   = col.iloc[-2]
            chg    = ((latest - prev) / prev) * 100
            arrow  = "▲" if chg >= 0 else "▼"
            chg_color = "#10B981" if chg >= 0 else "#EF4444"
            val_str = f"{latest:.2f}%" if ticker == TREASURY_TICKER else f"{latest:.2f}"
            cards.append(dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div(label, style={"fontSize": "0.75rem", "color": "#6c757d"}),
                        html.Div(val_str, style={"fontSize": "1.5rem", "fontWeight": "700", "color": "#fff"}),
                        html.Div(f"{arrow} {abs(chg):.2f}% MoM",
                                 style={"fontSize": "0.8rem", "color": chg_color}),
                    ], style={"padding": "12px"}),
                ], className="macro-stat-card",
                   style={"borderTopColor": color}),
            ], lg=3, sm=6, className="mb-2"))
        except Exception:
            pass
    return cards
# ─────────────────────────────────────────────────────────────────────────────
# Callbacks — existing
# ─────────────────────────────────────────────────────────────────────────────
@app.callback(
    [Output("indices-container",      "children"),
     Output("futures-container",      "children"),
     Output("bonds-container",        "children"),
     Output("yields-container",       "children"),
     Output("metals-container",       "children"),
     Output("currencies-container",   "children"),
     Output("sector-btns-container",  "children")],
    [Input("auto-refresh", "n_intervals"),
     Input("main-tabs", "active_tab")],
)
def update_market_overview(n_intervals, active_tab):
    if active_tab != "tab-market" and ctx.triggered_id == "auto-refresh":
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update
    indices = cached_fetch("indices", fetch_index_data, ttl=30)
    if indices:
        idx_cards = dbc.Row([render_index_card(item) for item in indices], className="g-2 mt-1")
    else:
        idx_cards = html.P("Unable to load index data.", className="text-muted")
    futures = cached_fetch("futures", fetch_futures_data, ttl=60)
    fut_cards = [render_index_card(item) for item in futures] if futures else []
    extras       = cached_fetch("market_extras", fetch_market_extras, ttl=60)
    extras       = extras or {}
    bonds_cards  = render_extra_cards(extras, BOND_ETFS)
    yields_cards = render_yield_cards(extras, TREASURY_YIELDS)
    metals_cards = render_extra_cards(extras, COMMODITIES, price_fmt="{:,.2f}")
    fx_cards     = render_extra_cards(extras, CURRENCIES, price_fmt="{:.4f}")
    sectors      = cached_fetch("sectors", fetch_sector_performance, ttl=60)
    sector_btns  = render_sector_cards(sectors)
    return idx_cards, fut_cards, bonds_cards, yields_cards, metals_cards, fx_cards, sector_btns

@app.callback(
    Output("sector-movers-container", "children"),
    Input("selected-sector-store", "data"),
)
def update_sector_movers(selected):
    if not selected:
        return html.Div()
    etf  = selected.get("etf")
    name = selected.get("name", etf)
    if not etf:
        return html.Div()
    movers = cached_fetch(f"sector_movers_{etf}", lambda: fetch_sector_movers(etf), ttl=120)
    return render_sector_movers(movers or {}, name)

@app.callback(
    Output("selected-sector-store", "data"),
    Input({"type": "sector-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def sector_btn_click(n_clicks_list):
    if not any(n_clicks_list):
        return no_update
    triggered = ctx.triggered_id
    if not triggered:
        return no_update
    etf  = triggered["index"]
    name = SECTOR_ETFS.get(etf, etf)
    return {"etf": etf, "name": name}
@app.callback(
    [Output("gainers-table", "children"),
     Output("losers-table", "children")],
    [Input("auto-refresh", "n_intervals"),
     Input("main-tabs", "active_tab")],
)
def update_gainers_losers(n_intervals, active_tab):
    if active_tab != "tab-market" and ctx.triggered_id == "auto-refresh":
        return no_update, no_update
    data = cached_fetch("gainers_losers", fetch_gainers_losers, ttl=60)
    if not data:
        return html.P("Unavailable", className="text-muted small"), html.P("Unavailable", className="text-muted small")
    return render_movers_table(data.get("gainers", [])), render_movers_table(data.get("losers", []))
@app.callback(
    Output("active-symbol", "data"),
    [Input("stock-search-btn", "n_clicks"),
     Input("stock-input", "n_submit")],
    State("stock-input", "value"),
    prevent_initial_call=True,
)
def update_active_symbol(n_clicks, n_submit, value):
    if not value:
        return no_update
    return value.upper().strip()
@app.callback(
    Output("active-timeframe", "data"),
    [Input(f"tf-{tf}", "n_clicks") for tf in TIMEFRAMES],
    prevent_initial_call=True,
)
def update_timeframe(*args):
    triggered = ctx.triggered_id
    if triggered:
        return triggered.replace("tf-", "")
    return no_update
@app.callback(
    [Output("candlestick-chart", "figure"),
     Output("rsi-chart", "figure"),
     Output("macd-chart", "figure"),
     Output("stats-panel", "children"),
     Output("current-price-display", "children")]
    + [Output(f"tf-{tf}", "outline") for tf in TIMEFRAMES],
    [Input("active-symbol", "data"),
     Input("active-timeframe", "data"),
     Input("auto-refresh", "n_intervals"),
     Input("main-tabs", "active_tab")],
)
def update_trading_dashboard(symbol, timeframe, n_intervals, active_tab):
    if active_tab != "tab-trading" and ctx.triggered_id == "auto-refresh":
        empty = build_empty_figure()
        return [empty, empty, empty, html.Span(), html.Span()] + [True] * len(TIMEFRAMES)
    if not symbol:
        empty = build_empty_figure("Enter a ticker symbol")
        return [empty, empty, empty, html.Span(), html.Span()] + [True] * len(TIMEFRAMES)
    if not timeframe:
        timeframe = "1M"
    df = cached_fetch(f"hist_{symbol}_{timeframe}", lambda: fetch_stock_history(symbol, timeframe), ttl=30)
    info = cached_fetch(f"info_{symbol}", lambda: fetch_stock_info(symbol), ttl=60)
    if df is None or df.empty:
        empty = build_empty_figure(f"No data for {symbol}")
        stats = html.P(f"No data for {symbol}", className="text-muted")
        price_disp = html.Span(symbol, className="text-muted")
        return [empty, empty, empty, stats, price_disp] + [True] * len(TIMEFRAMES)
    df = compute_technical_indicators(df)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="Price",
        increasing_line_color="#4fd1c5", decreasing_line_color="#fc8181",
        increasing_fillcolor="rgba(79,209,197,0.7)", decreasing_fillcolor="rgba(252,129,129,0.7)",
    ), row=1, col=1)
    sma_colors = {"SMA_20": "#fbd38d", "SMA_50": "#f6ad55", "SMA_200": "#63b3ed"}
    for sma, color in sma_colors.items():
        if sma in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sma], name=sma.replace("_", " "),
                line=dict(width=1.5, color=color),
                opacity=0.85,
            ), row=1, col=1)
    vol_colors = ["rgba(79,209,197,0.5)" if c >= o else "rgba(252,129,129,0.5)"
                  for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=vol_colors,
                         name="Volume", showlegend=False), row=2, col=1)
    range_breaks = [dict(bounds=["sat", "mon"])]
    if timeframe in ("1D", "5D"):
        range_breaks.append(dict(bounds=[20, 9.5], pattern="hour"))
    fig.update_xaxes(rangebreaks=range_breaks, **XAXIS_STYLE)
    fig.update_yaxes(**AXIS_STYLE)
    fig.update_layout(
        **CHART_LAYOUT,
        xaxis_rangeslider_visible=False,
        margin=dict(l=55, r=20, t=30, b=20),
        legend_orientation="h", legend_y=1.02, legend_x=0,
        legend_font=dict(size=10, color="#94a3b8"),
        height=480,
        yaxis=dict(title=dict(text="Price", font=dict(size=11, color="#64748b")),
                   gridcolor="rgba(255,255,255,0.04)", tickfont=dict(size=10, color="#64748b")),
        yaxis2=dict(title=dict(text="Vol", font=dict(size=10, color="#64748b")),
                    gridcolor="rgba(255,255,255,0.04)", tickfont=dict(size=10, color="#64748b")),
        hovermode="x unified",
    )
    rsi_fig = go.Figure()
    if "RSI" in df.columns:
        rsi_fig.add_hrect(y0=70, y1=100, fillcolor="rgba(252,129,129,0.04)", line_width=0)
        rsi_fig.add_hrect(y0=0, y1=30, fillcolor="rgba(79,209,197,0.04)", line_width=0)
        rsi_fig.add_hline(y=70, line_dash="dot", line_color="rgba(252,129,129,0.4)", line_width=1)
        rsi_fig.add_hline(y=30, line_dash="dot", line_color="rgba(79,209,197,0.4)", line_width=1)
        rsi_fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"], name="RSI",
            line=dict(color="#a78bfa", width=2),
            fill="tozeroy", fillcolor="rgba(167,139,250,0.05)",
        ))
    rsi_fig.update_xaxes(rangebreaks=range_breaks, **XAXIS_STYLE)
    rsi_fig.update_yaxes(**AXIS_STYLE)
    rsi_fig.update_layout(
        **CHART_LAYOUT,
        height=200,
        margin=dict(l=55, r=20, t=30, b=20),
        title=dict(text="RSI (14)", font=dict(size=11, color="#94a3b8")),
        yaxis=dict(range=[0, 100], gridcolor="rgba(255,255,255,0.04)",
                   tickfont=dict(size=9, color="#64748b")),
        showlegend=False,
    )
    macd_fig = go.Figure()
    if "MACD" in df.columns:
        hist_colors = ["rgba(79,209,197,0.6)" if v >= 0 else "rgba(252,129,129,0.6)"
                       for v in df["MACD_hist"]]
        macd_fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name="Histogram",
                                   marker_color=hist_colors))
        macd_fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD",
                                       line=dict(color="#63b3ed", width=2)))
        macd_fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="Signal",
                                       line=dict(color="#f6ad55", width=1.5, dash="dot")))
    macd_fig.update_xaxes(rangebreaks=range_breaks, **XAXIS_STYLE)
    macd_fig.update_yaxes(**AXIS_STYLE)
    macd_fig.update_layout(
        **CHART_LAYOUT,
        height=200,
        margin=dict(l=55, r=20, t=30, b=20),
        title=dict(text="MACD (12, 26, 9)", font=dict(size=11, color="#94a3b8")),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickfont=dict(size=9, color="#64748b")),
        legend_orientation="h", legend_y=1.15, legend_x=0,
        legend_font=dict(size=9, color="#94a3b8"),
        barmode="overlay",
    )
    stats = render_stats_panel(info)
    if info:
        price = info.get("regularMarketPrice") or info.get("previousClose", 0)
        change = info.get("regularMarketChange", 0) or 0
        pct = info.get("regularMarketChangePercent", 0) or 0
        color_cls = "text-gain" if change >= 0 else "text-loss"
        arrow = "\u25b2" if change >= 0 else "\u25bc"
        price_disp = html.Div([
            html.Span(info.get("shortName", symbol), className="text-muted me-2",
                       style={"fontSize": "0.85rem"}),
            html.Span(f"${price:,.2f}", className="fw-bold fs-5 me-2"),
            html.Span(f"{'+' if change >= 0 else ''}{change:.2f} ({arrow}{abs(pct):.2f}%)",
                       className=f"{color_cls}", style={"fontSize": "0.85rem"}),
        ])
    else:
        price_disp = html.Span(symbol, className="text-muted")
    outlines = [tf_key != timeframe for tf_key in TIMEFRAMES]
    return [fig, rsi_fig, macd_fig, stats, price_disp] + outlines
@app.callback(
    Output("benchmark-chart", "figure"),
    [Input("active-symbol", "data"),
     Input("active-timeframe", "data"),
     Input("auto-refresh", "n_intervals"),
     Input("main-tabs", "active_tab")],
)
def update_benchmark_chart(symbol, timeframe, n_intervals, active_tab):
    if active_tab != "tab-trading" and ctx.triggered_id == "auto-refresh":
        return no_update
    if not symbol:
        return build_empty_figure("Enter a ticker symbol")
    if not timeframe:
        timeframe = "1M"
    df = cached_fetch(
        f"benchmark_{symbol}_{timeframe}",
        lambda: fetch_benchmark_comparison(symbol, timeframe),
        ttl=60,
    )
    if df is None or df.empty:
        return build_empty_figure(f"No benchmark data for {symbol}")
    colors = {
        symbol: "#4fd1c5",
        "SPY":  "#63b3ed",
        "RSP":  "#f6ad55",
    }
    fig = go.Figure()
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue
        ret = series.iloc[-1] - 100
        label = f"{col}  {'+' if ret >= 0 else ''}{ret:.1f}%"
        fig.add_trace(go.Scatter(
            x=series.index, y=series.values,
            name=label,
            line=dict(color=colors.get(col, "#94a3b8"), width=2),
            mode="lines",
            hovertemplate=f"<b>{col}</b><br>%{{x}}<br>Indexed: %{{y:.1f}}<extra></extra>",
        ))
    fig.add_hline(y=100, line_dash="dot", line_color="rgba(255,255,255,0.15)", line_width=1)
    fig.update_layout(
        **CHART_LAYOUT,
        margin=dict(l=50, r=20, t=10, b=40),
        height=240,
        yaxis=dict(
            title=dict(text="Indexed (100 = period start)", font=dict(size=10, color="#64748b")),
            gridcolor="rgba(255,255,255,0.04)",
            tickfont=dict(size=9, color="#64748b"),
        ),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickfont=dict(size=9, color="#64748b")),
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10, color="#94a3b8")),
    )
    return fig
@app.callback(
    Output("news-feed", "children"),
    [Input("active-symbol", "data"),
     Input("auto-refresh", "n_intervals"),
     Input("main-tabs", "active_tab")],
)
def update_news(symbol, n_intervals, active_tab):
    if active_tab != "tab-news" and ctx.triggered_id == "auto-refresh":
        return no_update
    if not symbol:
        return html.P("Enter a ticker to see news.", className="text-muted")
    news = cached_fetch(f"news_{symbol}", lambda: fetch_stock_news(symbol), ttl=60)
    if not news:
        return html.P(f"No news available for {symbol}.", className="text-muted")
    items = news[:12] if isinstance(news, list) else []
    if not items:
        return html.P(f"No news available for {symbol}.", className="text-muted")
    return html.Div([render_news_item(item) for item in items])
@app.callback(
    [Output("company-profile", "children"),
     Output("upcoming-events", "children"),
     Output("corporate-actions", "children"),
     Output("sec-filings", "children")],
    [Input("active-symbol", "data"),
     Input("main-tabs", "active_tab")],
)
def update_corporate_info(symbol, active_tab):
    if not symbol:
        empty = html.P("Enter a ticker.", className="text-muted")
        return empty, empty, empty, empty
    info = cached_fetch(f"corpinfo_{symbol}", lambda: fetch_corporate_info(symbol), ttl=120)
    cal_data = cached_fetch(f"calendar_{symbol}", lambda: fetch_calendar_data(symbol), ttl=120)
    if info:
        profile = html.Div([
            html.H5(info.get("shortName", symbol), className="text-info mb-2"),
            html.Div([
                dbc.Badge(info.get("sector", "N/A"), color="primary", className="me-1"),
                dbc.Badge(info.get("industry", "N/A"), color="secondary"),
            ], className="mb-2"),
            html.Hr(style={"borderColor": "rgba(255,255,255,0.1)"}),
            html.P(truncate_text(info.get("longBusinessSummary", ""), 400),
                    className="small text-muted"),
            html.Div([
                html.Div([html.Span("Employees: ", className="stat-label"),
                           html.Span(f"{info.get('fullTimeEmployees', 'N/A'):,}" if isinstance(
                               info.get("fullTimeEmployees"), int) else "N/A", className="stat-value")],
                          className="stat-row"),
                html.Div([html.Span("Website: ", className="stat-label"),
                           html.A(info.get("website", "N/A"), href=info.get("website", "#"),
                                  target="_blank", className="text-info",
                                  style={"fontSize": "0.85rem"})],
                          className="stat-row"),
            ]),
        ])
    else:
        profile = html.P("No company data available.", className="text-muted")
    calendar = cal_data.get("calendar") if cal_data else None
    if calendar and isinstance(calendar, dict) and len(calendar) > 0:
        event_rows = []
        for key in ["Earnings Date", "Earnings Average", "Earnings High", "Earnings Low",
                     "Dividend Date", "Ex-Dividend Date"]:
            if key in calendar:
                val = calendar[key]
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                event_rows.append(html.Div([
                    html.Span(key + ": ", className="stat-label"),
                    html.Span(str(val), className="stat-value"),
                ], className="stat-row"))
        events = html.Div(event_rows) if event_rows else html.P("No upcoming events.", className="text-muted")
    else:
        events = html.P("No upcoming events.", className="text-muted")
    actions_df = cal_data.get("actions") if cal_data else None
    if actions_df is not None and len(actions_df) > 0:
        rows = []
        for idx_val, row in actions_df.iterrows():
            date_str = idx_val.strftime("%Y-%m-%d") if hasattr(idx_val, "strftime") else str(idx_val)
            div_val = row.get("Dividends", 0)
            split_val = row.get("Stock Splits", 0)
            action_type = ""
            if div_val > 0:
                action_type = f"Dividend: ${div_val:.4f}"
            if split_val > 0:
                action_type += f"{'  |  ' if action_type else ''}Split: {split_val}"
            if action_type:
                rows.append(html.Tr([
                    html.Td(date_str, className="text-muted"),
                    html.Td(action_type),
                ]))
        if rows:
            actions = html.Table([
                html.Thead(html.Tr([html.Th("Date"), html.Th("Action")],
                                    className="text-muted", style={"fontSize": "0.75rem"})),
                html.Tbody(rows),
            ], className="table table-sm table-borderless mb-0", style={"fontSize": "0.8rem"})
        else:
            actions = html.P("No recent actions.", className="text-muted")
    else:
        actions = html.P("No recent actions.", className="text-muted")
    # SEC filings — fetched with longer TTL (filings don't change minute to minute)
    sec_data = cached_fetch(f"sec_{symbol}", lambda: fetch_sec_filings(symbol), ttl=600)
    filings_widget = render_sec_filings(sec_data or [])
    return profile, events, actions, filings_widget
# ─────────────────────────────────────────────────────────────────────────────
# Callbacks — macro dashboard
# ─────────────────────────────────────────────────────────────────────────────
@app.callback(
    Output("macro-data-store", "data"),
    Output("macro-last-updated", "children"),
    [Input("macro-refresh-btn", "n_clicks"),
     Input("macro-auto-refresh", "n_intervals"),
     Input("main-tabs", "active_tab")],
    prevent_initial_call=False,
)
def load_macro_data(n_clicks, n_intervals, active_tab):
    if active_tab != "tab-macro" and ctx.triggered_id == "macro-auto-refresh":
        return no_update, no_update
    df = cached_fetch("macro_prices", fetch_macro_prices, ttl=900)
    if df is None or df.empty:
        return None, "⚠️ Data unavailable"
    spreads = cached_fetch("fred_spreads", fetch_fred_spreads, ttl=900)
    payload = {
        "prices":  df.to_json(date_format="iso"),
        "spreads": spreads.to_json(date_format="iso") if spreads is not None else None,
        "fred_ok": spreads is not None,
    }
    fred_label = " | FRED OAS ✅" if spreads is not None else " | FRED OAS ⚠️ (set FRED_API_KEY)"
    ts = datetime.now().strftime("Updated %b %d %H:%M") + fred_label
    return payload, ts
@app.callback(
    Output("macro-main-chart",    "figure"),
    Output("macro-signal-banner", "children"),
    Output("macro-stat-cards",    "children"),
    Output("macro-bdc-table",     "children"),
    Input("macro-data-store",     "data"),
    prevent_initial_call=False,
)
def update_macro_dashboard(data):
    if not data:
        empty = build_empty_figure("Click Refresh to load macro data")
        return empty, "", [], html.P("Loading...", className="text-muted small")
    prices_json = data.get("prices") if isinstance(data, dict) else data
    df = pd.read_json(io.StringIO(prices_json))
    df.index = pd.to_datetime(df.index)
    spreads_df = None
    if isinstance(data, dict) and data.get("spreads"):
        try:
            spreads_df = pd.read_json(io.StringIO(data["spreads"]))
            spreads_df.index = pd.to_datetime(spreads_df.index)
        except Exception:
            spreads_df = None
    chart = build_macro_chart(df, spreads_df)
    sig = get_current_macro_signal(df)
    extra = ""
    if spreads_df is not None and "HYIG_SPREAD" in spreads_df.columns:
        try:
            latest_spread = spreads_df["HYIG_SPREAD"].dropna().iloc[-1]
            hy_oas        = spreads_df["HY_OAS"].dropna().iloc[-1]
            ig_oas        = spreads_df["IG_OAS"].dropna().iloc[-1]
            spread_color  = ("#10B981" if latest_spread < 2.0 else
                             "#F59E0B" if latest_spread < 3.5 else "#EF4444")
            extra = html.Span([
                "  |  HY OAS: ",
                html.Strong(f"{hy_oas:.2f}%",         style={"color": "#F97316"}),
                "  IG OAS: ",
                html.Strong(f"{ig_oas:.2f}%",         style={"color": "#A78BFA"}),
                "  HY–IG Spread: ",
                html.Strong(f"{latest_spread:.2f}%",  style={"color": spread_color}),
            ], style={"fontSize": "0.82rem"})
        except Exception:
            pass
    if sig:
        banner = dbc.Alert([
            html.I(className="fas fa-broadcast-tower me-2"),
            html.Strong("Current Regime: "),
            sig["read"],
            extra,
        ], color=sig["alert"], className="mb-0 py-2", style={"fontSize": "0.85rem"})
    else:
        banner = dbc.Alert(
            ["Calculating regime signal...", extra],
            color="secondary", className="mb-0 py-2", style={"fontSize": "0.85rem"}
        )
    stat_cards = build_macro_stat_cards(df)
    bdc_rows  = cached_fetch("bdc_data", fetch_bdc_prices, ttl=300)
    bdc_table = build_bdc_table(bdc_rows or [])
    return chart, banner, stat_cards, bdc_table
# ─────────────────────────────────────────────────────────────────────────────
# Utility callbacks
# ─────────────────────────────────────────────────────────────────────────────
@app.callback(
    Output("auto-refresh", "disabled"),
    Input("auto-refresh-toggle", "value"),
)
def toggle_refresh(enabled):
    return not enabled
@app.callback(
    Output("last-update-time", "children"),
    Input("auto-refresh", "n_intervals"),
)
def update_timestamp(n):
    return f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
@app.callback(
    Output("market-status-badge", "children"),
    Input("auto-refresh", "n_intervals"),
)
def update_market_status(n):
    now = datetime.now()
    is_weekday = now.weekday() < 5
    is_market_hours = 9 <= now.hour < 16
    if is_weekday and is_market_hours:
        return dbc.Badge([html.I(className="fas fa-circle me-1"), "MARKET OPEN"],
                          color="success", className="me-2")
    return dbc.Badge([html.I(className="fas fa-circle me-1"), "MARKET CLOSED"],
                      color="danger", className="me-2")
# ─────────────────────────────────────────────────────────────────────────────
# Options flow callbacks
# ─────────────────────────────────────────────────────────────────────────────
@app.callback(
    [Output("options-flow-store",    "data"),
     Output("options-summary-cards", "children")],
    Input("scan-options-btn", "n_clicks"),
    [State("options-watchlist-input", "value"),
     State("options-min-vol",         "value"),
     State("options-vol-oi",          "value")],
    prevent_initial_call=True,
)
def scan_options_flow(n_clicks, watchlist_str, min_vol, vol_oi):
    if not n_clicks or not watchlist_str:
        return [], html.Div()
    tickers  = [t.strip().upper() for t in watchlist_str.split(",") if t.strip()][:10]
    min_vol  = int(min_vol  or OPTIONS_MIN_VOL)
    vol_oi   = float(vol_oi or OPTIONS_VOL_OI_RATIO)
    all_flow = []
    for sym in tickers:
        flow = cached_fetch(
            f"options_flow_{sym}_{min_vol}_{vol_oi}",
            lambda s=sym: fetch_options_flow(s, min_vol, vol_oi),
            ttl=300,
        )
        if flow:
            all_flow.extend(flow)
    all_flow.sort(key=lambda x: x["premium"], reverse=True)
    return all_flow, render_options_flow_summary(all_flow)

@app.callback(
    [Output("options-flow-table",  "children"),
     Output("options-filter-store","data"),
     Output("opt-filter-all",      "outline"),
     Output("opt-filter-calls",    "outline"),
     Output("opt-filter-puts",     "outline")],
    [Input("opt-filter-all",   "n_clicks"),
     Input("opt-filter-calls", "n_clicks"),
     Input("opt-filter-puts",  "n_clicks"),
     Input("options-flow-store", "data")],
    State("options-filter-store", "data"),
    prevent_initial_call=True,
)
def update_options_table(n_all, n_calls, n_puts, flow_data, current_filter):
    triggered = ctx.triggered_id
    if triggered in ("opt-filter-all", "opt-filter-calls", "opt-filter-puts"):
        filt = {"opt-filter-all": "ALL",
                "opt-filter-calls": "CALL",
                "opt-filter-puts": "PUT"}[triggered]
    else:
        filt = current_filter or "ALL"

    flow = flow_data or []
    table = render_options_flow_table(flow, filt)
    # outline=False = active (filled), True = outlined
    return table, filt, filt != "ALL", filt != "CALL", filt != "PUT"

# ─────────────────────────────────────────────────────────────────────────────
# Flow data callbacks
# ─────────────────────────────────────────────────────────────────────────────
@app.callback(
    Output("cot-content", "children"),
    Input("load-cot-btn", "n_clicks"),
    prevent_initial_call=True,
)
def load_cot(n):
    data = cached_fetch("cot_data", fetch_cot_data, ttl=3600)
    if not data:
        return html.P("CFTC API unavailable — try again later.", className="text-muted small p-3")
    fig, table = render_cot_chart_and_table(data)
    report_date = data[0]["date"] if data else ""
    return html.Div([
        html.P(f"CFTC Commitments of Traders — report date: {report_date}",
               className="text-muted small mb-2"),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=fig, config={"displayModeBar": False}),
                              className="p-1"), className="mb-3"),
        dbc.Card([
            dbc.CardHeader("Positioning Detail",
                           style={"fontSize": "0.85rem", "fontWeight": "600"}),
            dbc.CardBody(table, className="p-2"),
        ]),
    ])

@app.callback(
    Output("holdings-content", "children"),
    Input("load-13f-btn", "n_clicks"),
    [State("fund-select",      "value"),
     State("custom-cik-input", "value")],
    prevent_initial_call=True,
)
def load_13f(n, fund_cik, custom_cik):
    cik = (custom_cik or fund_cik or "").strip()
    if not cik:
        return html.P("Select a fund or enter a CIK.", className="text-muted small p-2")
    meta, holdings = cached_fetch(
        f"13f_{cik}",
        lambda c=cik: fetch_13f_holdings(c),
        ttl=3600,
    )
    if not holdings:
        return html.P(
            f"Could not retrieve 13F data for CIK {cik}. "
            "Filing may use a non-standard XML format.",
            className="text-muted small p-3",
        )
    fund_name = meta.get("name", cik) if meta else cik
    total     = meta.get("total", 0)  if meta else 0
    return dbc.Card([
        dbc.CardHeader([
            html.Strong(fund_name, style={"color": "#63b3ed"}),
            html.Span(f"  |  Top {min(30, len(holdings))} of {len(holdings)} positions",
                      className="text-muted ms-3", style={"fontSize": "0.78rem"}),
            html.Span(f"  |  Total: ${total/1e9:.2f}B",
                      className="text-info ms-2", style={"fontSize": "0.78rem"}),
        ], style={"fontSize": "0.9rem"}),
        dbc.CardBody(render_13f_table(meta, holdings), className="p-2"),
    ])

@app.callback(
    Output("short-interest-content", "children"),
    Input("load-short-btn", "n_clicks"),
    State("short-interest-input", "value"),
    prevent_initial_call=True,
)
def load_short_interest(n, tickers_str):
    if not tickers_str:
        return html.Div()
    tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()][:15]
    data = cached_fetch(
        f"short_{'_'.join(tickers)}",
        lambda t=tickers: fetch_short_interest(t),
        ttl=3600,
    )
    return dbc.Card([
        dbc.CardHeader([
            "Short Interest",
            html.Span(" — sorted by Short % Float, updated bi-monthly by FINRA",
                      className="text-muted ms-2", style={"fontSize": "0.72rem"}),
        ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
        dbc.CardBody(render_short_interest_table(data or []), className="p-2"),
    ])

@app.callback(
    Output("etf-flows-content", "children"),
    Input("load-etf-btn", "n_clicks"),
    prevent_initial_call=True,
)
def load_etf_flows(n):
    data = cached_fetch("etf_flows", fetch_etf_flows, ttl=300)
    return dbc.Card([
        dbc.CardHeader([
            "ETF AUM & Flow Indicators",
            html.Span("  |  Vol/Avg ≥ 1.5x = unusual volume",
                      className="text-muted ms-2", style={"fontSize": "0.72rem"}),
        ], style={"fontSize": "0.9rem", "fontWeight": "600"}),
        dbc.CardBody(render_etf_flows_table(data or []), className="p-2"),
    ])

# ─────────────────────────────────────────────────────────────────────────────
# Insider alerts callback
# ─────────────────────────────────────────────────────────────────────────────
@app.callback(
    [Output("insider-alerts-table",  "children"),
     Output("insider-summary-cards", "children")],
    Input("scan-insiders-btn", "n_clicks"),
    [State("watchlist-input",      "value"),
     State("insider-days-select",  "value")],
    prevent_initial_call=True,
)
def scan_insider_buys(n_clicks, watchlist_str, days_str):
    if not n_clicks or not watchlist_str:
        return (html.P("Enter tickers and click Scan.", className="text-muted small p-2"),
                html.Div())
    tickers  = [t.strip().upper() for t in watchlist_str.split(",") if t.strip()][:12]
    days     = int(days_str or 90)
    all_buys = fetch_watchlist_insider_buys(tickers, days)
    return render_insider_table(all_buys), render_insider_summary(all_buys)

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("RENDER") is None  # debug=False on Render, True locally
    print("\n  Financial Command Center starting...")
    print(f"  Open http://localhost:{port} in your browser\n")
    app.run(debug=debug, host="0.0.0.0", port=port)
