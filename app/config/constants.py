DEFAULT_TIMEFRAME = "1D"
DEFAULT_INITIAL_CAPITAL = 100000.0
DEFAULT_COMMISSION_PCT = 0.1
DATE_COLUMN_CANDIDATES = ["date", "datetime", "timestamp", "Date", "Datetime", "Timestamp"]
OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
ANGEL_SYMBOL_TO_TOKEN = {
    "RELIANCE": "2885",
    "TCS": "11536",
    "INFY": "1594",
    "HDFCBANK": "1333",
    "ICICIBANK": "4963",
    "SBIN": "3045",
    "AXISBANK": "5900",
    "LT": "11483",
    "ITC": "1660",
    "HINDUNILVR": "1394",
    "BAJFINANCE": "317",
    "WIPRO": "3787",
}
ANGEL_SYMBOL_DETAILS = {
    "RELIANCE": {"name": "Reliance Industries", "exchange": "NSE", "token": "2885"},
    "TCS": {"name": "Tata Consultancy Services", "exchange": "NSE", "token": "11536"},
    "INFY": {"name": "Infosys", "exchange": "NSE", "token": "1594"},
    "HDFCBANK": {"name": "HDFC Bank", "exchange": "NSE", "token": "1333"},
    "ICICIBANK": {"name": "ICICI Bank", "exchange": "NSE", "token": "4963"},
    "SBIN": {"name": "State Bank of India", "exchange": "NSE", "token": "3045"},
    "AXISBANK": {"name": "Axis Bank", "exchange": "NSE", "token": "5900"},
    "LT": {"name": "Larsen & Toubro", "exchange": "NSE", "token": "11483"},
    "ITC": {"name": "ITC", "exchange": "NSE", "token": "1660"},
    "HINDUNILVR": {"name": "Hindustan Unilever", "exchange": "NSE", "token": "1394"},
    "BAJFINANCE": {"name": "Bajaj Finance", "exchange": "NSE", "token": "317"},
    "WIPRO": {"name": "Wipro", "exchange": "NSE", "token": "3787"},
}
ANGEL_INDEX_DETAILS = {
    "NIFTY 50": {"name": "NIFTY 50", "exchange": "NSE", "token": None},
    "SENSEX": {"name": "SENSEX", "exchange": "BSE", "token": None},
    "BANK NIFTY": {"name": "BANK NIFTY", "exchange": "NSE", "token": None},
    "FINNIFTY": {"name": "FINNIFTY", "exchange": "NSE", "token": None},
    "NIFTY IT": {"name": "NIFTY IT", "exchange": "NSE", "token": None},
    "NIFTY AUTO": {"name": "NIFTY AUTO", "exchange": "NSE", "token": None},
    "NIFTY FMCG": {"name": "NIFTY FMCG", "exchange": "NSE", "token": None},
    "NIFTY PHARMA": {"name": "NIFTY PHARMA", "exchange": "NSE", "token": None},
    "NIFTY METAL": {"name": "NIFTY METAL", "exchange": "NSE", "token": None},
    "NIFTY ENERGY": {"name": "NIFTY ENERGY", "exchange": "NSE", "token": None},
    "NIFTY REALTY": {"name": "NIFTY REALTY", "exchange": "NSE", "token": None},
    "NIFTY MIDCAP": {"name": "NIFTY MIDCAP", "exchange": "NSE", "token": None},
    "NIFTY SMALLCAP": {"name": "NIFTY SMALLCAP", "exchange": "NSE", "token": None},
    "INDIA VIX": {"name": "INDIA VIX", "exchange": "NSE", "token": None},
}
MARKET_WATCH_SECTOR_MAP = {
    "RELIANCE": "Energy",
    "TCS": "Information Technology",
    "INFY": "Information Technology",
    "WIPRO": "Information Technology",
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "SBIN": "Banking",
    "AXISBANK": "Banking",
    "LT": "Industrials",
    "ITC": "FMCG",
    "HINDUNILVR": "FMCG",
    "BAJFINANCE": "Financial Services",
}
MARKET_WATCH_PEERS = {
    "HDFCBANK": {
        "sector": "Banking",
        "industry": "Private Sector Bank",
        "peers": ["ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK"],
    },
    "ICICIBANK": {
        "sector": "Banking",
        "industry": "Private Sector Bank",
        "peers": ["HDFCBANK", "SBIN", "AXISBANK", "KOTAKBANK"],
    },
    "SBIN": {
        "sector": "Banking",
        "industry": "Public Sector Bank",
        "peers": ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK"],
    },
    "AXISBANK": {
        "sector": "Banking",
        "industry": "Private Sector Bank",
        "peers": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK"],
    },
    "RELIANCE": {
        "sector": "Energy",
        "industry": "Oil, Gas & Diversified",
        "peers": ["ONGC", "IOC", "BPCL"],
    },
    "TCS": {
        "sector": "Information Technology",
        "industry": "IT Services",
        "peers": ["INFY", "WIPRO", "HCLTECH", "TECHM"],
    },
    "INFY": {
        "sector": "Information Technology",
        "industry": "IT Services",
        "peers": ["TCS", "WIPRO", "HCLTECH", "TECHM"],
    },
    "WIPRO": {
        "sector": "Information Technology",
        "industry": "IT Services",
        "peers": ["TCS", "INFY", "HCLTECH", "TECHM"],
    },
}
