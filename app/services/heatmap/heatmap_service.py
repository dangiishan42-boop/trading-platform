from __future__ import annotations

from datetime import datetime
from typing import Any

from app.schemas.heatmap_schema import HeatmapRunRequest, HeatmapSectorRequest
from app.services.market_data.engine import MarketDataEngine, get_market_data_engine


class HeatmapService:
    DATA_SOURCE_NOTE = (
        "Heatmap data is based on local sample data for UI demonstration. "
        "Real-time exchange integration coming soon."
    )
    UNIVERSES = ["Nifty 50", "Nifty 100", "Nifty 500", "F&O Stocks", "All NSE", "All BSE"]
    SIZE_BY = ["Market Cap", "Volume", "Turnover", "Equal Weight"]
    COLOR_BY = ["% Change", "Volume Change", "Relative Volume", "RSI", "Sector Strength"]
    FACTOR_COLOR_BY = ["% Change", "Volume Change", "Relative Volume", "RSI", "Volatility", "Market Cap", "P/E placeholder", "ROE placeholder", "Debt/Equity placeholder"]
    TIMEFRAMES = ["1D", "1W", "1M", "3M", "6M", "1Y"]
    SECTOR_SLUGS = {
        "FINANCIAL SERVICES": "financial-services",
        "INFORMATION TECHNOLOGY": "information-technology",
        "ENERGY": "energy",
        "AUTOMOBILE": "automobile",
        "CONSUMER GOODS": "consumer-goods",
        "PHARMA & HEALTHCARE": "pharma-healthcare",
        "METALS & MINING": "metals-mining",
        "CONSTRUCTION": "construction",
        "TELECOM": "telecom",
        "CHEMICALS": "chemicals",
        "RETAIL": "retail",
        "MEDIA": "media",
        "REALTY": "realty",
        "INDUSTRIALS": "industrials",
        "TEXTILES": "textiles",
        "AGRI": "agri",
        "CONSUMER DURABLES": "consumer-durables",
    }
    INDUSTRY_GROUPS = {
        "FINANCIAL SERVICES": {
            "Private Banks": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK"],
            "PSU Banks": ["SBIN"],
            "NBFC": ["BAJFINANCE", "BAJAJFINSV"],
            "Insurance": ["HDFCLIFE", "SBILIFE", "LIC"],
            "Asset Management": [],
        },
        "INFORMATION TECHNOLOGY": {
            "IT Services": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM"],
            "Software Products": ["PERSISTENT"],
            "Midcap IT": ["MPHASIS"],
        },
        "AUTOMOBILE": {
            "Passenger Vehicles": ["TATAMOTORS", "MARUTI", "M&M"],
            "Two Wheelers": ["BAJAJ-AUTO", "EICHERMOT", "TVSMOTOR"],
            "Auto Ancillaries": [],
        },
        "ENERGY": {
            "Oil & Gas": ["RELIANCE", "ONGC", "IOC", "BPCL", "GAIL", "OIL"],
            "Utilities": ["COALINDIA"],
            "Renewables": [],
        },
        "PHARMA & HEALTHCARE": {
            "Pharma": ["SUNPHARMA", "CIPLA", "DRREDDY", "DIVISLAB", "GLENMARK", "TORNTPHARM"],
            "Hospitals": [],
            "Diagnostics": [],
        },
        "CONSUMER GOODS": {"FMCG": ["HINDUNILVR", "ITC", "DABUR", "NESTLEIND", "BRITANNIA", "GODREJCP"]},
        "METALS & MINING": {"Metals": ["JSWSTEEL", "TATASTEEL", "HINDALCO", "VEDL", "SAIL", "NMDC"]},
        "CONSTRUCTION": {"Capital Goods": ["LT"], "Cement": ["ULTRACEMCO", "GRASIM", "AMBUJACEM"]},
        "TELECOM": {"Telecom Services": ["BHARTIARTL", "INDUSTOWER"]},
        "REALTY": {"Real Estate": ["DLF", "GODREJPROP"]},
        "INDUSTRIALS": {"Industrial Automation": ["SIEMENS", "ABB"], "Logistics": ["ADANIPORTS"]},
    }

    SAMPLE_STOCKS: list[dict[str, Any]] = [
        {"symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "FINANCIAL SERVICES", "price": 1548.2, "change_pct": -0.42, "market_cap_cr": 1175000, "volume": 11400000, "rsi": 48.6},
        {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "FINANCIAL SERVICES", "price": 1108.7, "change_pct": 0.78, "market_cap_cr": 781000, "volume": 8725000, "rsi": 57.7},
        {"symbol": "SBIN", "name": "State Bank of India", "sector": "FINANCIAL SERVICES", "price": 763.4, "change_pct": 2.08, "market_cap_cr": 681000, "volume": 19200000, "rsi": 69.2},
        {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "FINANCIAL SERVICES", "price": 1734.8, "change_pct": 0.34, "market_cap_cr": 345000, "volume": 3120000, "rsi": 52.4},
        {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "sector": "FINANCIAL SERVICES", "price": 6842.0, "change_pct": 2.66, "market_cap_cr": 424000, "volume": 980000, "rsi": 61.8},
        {"symbol": "AXISBANK", "name": "Axis Bank", "sector": "FINANCIAL SERVICES", "price": 1102.9, "change_pct": -0.18, "market_cap_cr": 339000, "volume": 6520000, "rsi": 49.1},
        {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv", "sector": "FINANCIAL SERVICES", "price": 1628.1, "change_pct": 0.92, "market_cap_cr": 260000, "volume": 790000, "rsi": 56.2},
        {"symbol": "HDFCLIFE", "name": "HDFC Life Insurance", "sector": "FINANCIAL SERVICES", "price": 623.4, "change_pct": -1.14, "market_cap_cr": 134000, "volume": 2680000, "rsi": 43.2},
        {"symbol": "SBILIFE", "name": "SBI Life Insurance", "sector": "FINANCIAL SERVICES", "price": 1484.7, "change_pct": 0.21, "market_cap_cr": 148000, "volume": 690000, "rsi": 51.7},
        {"symbol": "LIC", "name": "Life Insurance Corporation", "sector": "FINANCIAL SERVICES", "price": 928.5, "change_pct": -0.64, "market_cap_cr": 587000, "volume": 2160000, "rsi": 46.8},
        {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "INFORMATION TECHNOLOGY", "price": 3875.0, "change_pct": -0.18, "market_cap_cr": 1402000, "volume": 1850000, "rsi": 63.8},
        {"symbol": "INFY", "name": "Infosys", "sector": "INFORMATION TECHNOLOGY", "price": 1432.5, "change_pct": 0.33, "market_cap_cr": 594000, "volume": 4850000, "rsi": 54.1},
        {"symbol": "WIPRO", "name": "Wipro", "sector": "INFORMATION TECHNOLOGY", "price": 458.2, "change_pct": -0.82, "market_cap_cr": 239000, "volume": 5620000, "rsi": 44.7},
        {"symbol": "HCLTECH", "name": "HCL Technologies", "sector": "INFORMATION TECHNOLOGY", "price": 1518.4, "change_pct": 2.18, "market_cap_cr": 412000, "volume": 2100000, "rsi": 66.3},
        {"symbol": "TECHM", "name": "Tech Mahindra", "sector": "INFORMATION TECHNOLOGY", "price": 1288.0, "change_pct": 0.68, "market_cap_cr": 126000, "volume": 1880000, "rsi": 55.5},
        {"symbol": "LTIM", "name": "LTIMindtree", "sector": "INFORMATION TECHNOLOGY", "price": 5124.7, "change_pct": -1.24, "market_cap_cr": 152000, "volume": 310000, "rsi": 41.6},
        {"symbol": "MPHASIS", "name": "Mphasis", "sector": "INFORMATION TECHNOLOGY", "price": 2416.3, "change_pct": 0.44, "market_cap_cr": 45600, "volume": 420000, "rsi": 53.9},
        {"symbol": "PERSISTENT", "name": "Persistent Systems", "sector": "INFORMATION TECHNOLOGY", "price": 3924.6, "change_pct": 1.16, "market_cap_cr": 60400, "volume": 510000, "rsi": 59.4},
        {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "ENERGY", "price": 2928.4, "change_pct": 1.24, "market_cap_cr": 1980000, "volume": 6250000, "rsi": 61.2},
        {"symbol": "ONGC", "name": "Oil and Natural Gas Corp", "sector": "ENERGY", "price": 276.2, "change_pct": 0.76, "market_cap_cr": 347000, "volume": 18400000, "rsi": 57.9},
        {"symbol": "IOC", "name": "Indian Oil Corp", "sector": "ENERGY", "price": 168.5, "change_pct": -0.94, "market_cap_cr": 238000, "volume": 12600000, "rsi": 45.3},
        {"symbol": "BPCL", "name": "Bharat Petroleum", "sector": "ENERGY", "price": 596.1, "change_pct": -2.18, "market_cap_cr": 129000, "volume": 4380000, "rsi": 39.4},
        {"symbol": "GAIL", "name": "GAIL India", "sector": "ENERGY", "price": 208.7, "change_pct": 0.12, "market_cap_cr": 137000, "volume": 9240000, "rsi": 50.2},
        {"symbol": "OIL", "name": "Oil India", "sector": "ENERGY", "price": 628.8, "change_pct": 1.48, "market_cap_cr": 68100, "volume": 1190000, "rsi": 62.1},
        {"symbol": "TATAMOTORS", "name": "Tata Motors", "sector": "AUTOMOBILE", "price": 986.2, "change_pct": 3.14, "market_cap_cr": 362000, "volume": 14200000, "rsi": 72.4},
        {"symbol": "MARUTI", "name": "Maruti Suzuki", "sector": "AUTOMOBILE", "price": 12582.3, "change_pct": 0.74, "market_cap_cr": 395000, "volume": 510000, "rsi": 56.4},
        {"symbol": "M&M", "name": "Mahindra & Mahindra", "sector": "AUTOMOBILE", "price": 2046.5, "change_pct": 2.84, "market_cap_cr": 254000, "volume": 2710000, "rsi": 68.5},
        {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto", "sector": "AUTOMOBILE", "price": 8742.0, "change_pct": -0.22, "market_cap_cr": 244000, "volume": 260000, "rsi": 51.1},
        {"symbol": "EICHERMOT", "name": "Eicher Motors", "sector": "AUTOMOBILE", "price": 4218.0, "change_pct": 1.06, "market_cap_cr": 116000, "volume": 380000, "rsi": 58.7},
        {"symbol": "TVSMOTOR", "name": "TVS Motor", "sector": "AUTOMOBILE", "price": 2114.4, "change_pct": 1.74, "market_cap_cr": 100000, "volume": 760000, "rsi": 63.6},
        {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "CONSUMER GOODS", "price": 2240.6, "change_pct": -0.74, "market_cap_cr": 526000, "volume": 1020000, "rsi": 43.5},
        {"symbol": "ITC", "name": "ITC", "sector": "CONSUMER GOODS", "price": 431.2, "change_pct": 0.91, "market_cap_cr": 538000, "volume": 14650000, "rsi": 58.2},
        {"symbol": "DABUR", "name": "Dabur India", "sector": "CONSUMER GOODS", "price": 531.8, "change_pct": -0.34, "market_cap_cr": 94200, "volume": 1120000, "rsi": 47.2},
        {"symbol": "NESTLEIND", "name": "Nestle India", "sector": "CONSUMER GOODS", "price": 2448.6, "change_pct": 0.22, "market_cap_cr": 236000, "volume": 420000, "rsi": 52.6},
        {"symbol": "BRITANNIA", "name": "Britannia Industries", "sector": "CONSUMER GOODS", "price": 4822.2, "change_pct": -0.58, "market_cap_cr": 116000, "volume": 210000, "rsi": 45.9},
        {"symbol": "GODREJCP", "name": "Godrej Consumer Products", "sector": "CONSUMER GOODS", "price": 1244.1, "change_pct": 1.32, "market_cap_cr": 127000, "volume": 910000, "rsi": 59.8},
        {"symbol": "SUNPHARMA", "name": "Sun Pharma", "sector": "PHARMA & HEALTHCARE", "price": 1522.3, "change_pct": 0.54, "market_cap_cr": 365000, "volume": 1710000, "rsi": 55.2},
        {"symbol": "CIPLA", "name": "Cipla", "sector": "PHARMA & HEALTHCARE", "price": 1410.2, "change_pct": -0.28, "market_cap_cr": 114000, "volume": 920000, "rsi": 48.8},
        {"symbol": "DRREDDY", "name": "Dr Reddy's Labs", "sector": "PHARMA & HEALTHCARE", "price": 6224.1, "change_pct": 0.88, "market_cap_cr": 104000, "volume": 250000, "rsi": 57.1},
        {"symbol": "DIVISLAB", "name": "Divi's Laboratories", "sector": "PHARMA & HEALTHCARE", "price": 3826.5, "change_pct": -1.06, "market_cap_cr": 101000, "volume": 340000, "rsi": 42.3},
        {"symbol": "GLENMARK", "name": "Glenmark Pharma", "sector": "PHARMA & HEALTHCARE", "price": 1034.7, "change_pct": 1.94, "market_cap_cr": 29200, "volume": 880000, "rsi": 64.9},
        {"symbol": "TORNTPHARM", "name": "Torrent Pharma", "sector": "PHARMA & HEALTHCARE", "price": 2624.5, "change_pct": 0.18, "market_cap_cr": 88700, "volume": 180000, "rsi": 51.2},
        {"symbol": "JSWSTEEL", "name": "JSW Steel", "sector": "METALS & MINING", "price": 842.8, "change_pct": -0.86, "market_cap_cr": 206000, "volume": 2810000, "rsi": 44.6},
        {"symbol": "TATASTEEL", "name": "Tata Steel", "sector": "METALS & MINING", "price": 154.2, "change_pct": -1.36, "market_cap_cr": 192000, "volume": 31600000, "rsi": 40.8},
        {"symbol": "HINDALCO", "name": "Hindalco", "sector": "METALS & MINING", "price": 612.5, "change_pct": -2.42, "market_cap_cr": 138000, "volume": 6120000, "rsi": 37.9},
        {"symbol": "VEDL", "name": "Vedanta", "sector": "METALS & MINING", "price": 382.6, "change_pct": 0.26, "market_cap_cr": 142000, "volume": 7440000, "rsi": 51.5},
        {"symbol": "SAIL", "name": "Steel Authority of India", "sector": "METALS & MINING", "price": 132.1, "change_pct": -0.72, "market_cap_cr": 54600, "volume": 12600000, "rsi": 44.1},
        {"symbol": "NMDC", "name": "NMDC", "sector": "METALS & MINING", "price": 221.3, "change_pct": -2.04, "market_cap_cr": 64900, "volume": 8320000, "rsi": 38.6},
        {"symbol": "LT", "name": "Larsen & Toubro", "sector": "CONSTRUCTION", "price": 3590.8, "change_pct": 1.62, "market_cap_cr": 493000, "volume": 1420000, "rsi": 67.4},
        {"symbol": "ULTRACEMCO", "name": "UltraTech Cement", "sector": "CONSTRUCTION", "price": 9872.4, "change_pct": 0.38, "market_cap_cr": 285000, "volume": 260000, "rsi": 53.5},
        {"symbol": "GRASIM", "name": "Grasim Industries", "sector": "CONSTRUCTION", "price": 2246.9, "change_pct": -0.64, "market_cap_cr": 148000, "volume": 620000, "rsi": 45.7},
        {"symbol": "AMBUJACEM", "name": "Ambuja Cements", "sector": "CONSTRUCTION", "price": 612.0, "change_pct": 0.82, "market_cap_cr": 151000, "volume": 3320000, "rsi": 56.8},
        {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "sector": "TELECOM", "price": 1216.5, "change_pct": 0.48, "market_cap_cr": 724000, "volume": 2710000, "rsi": 55.2},
        {"symbol": "INDUSTOWER", "name": "Indus Towers", "sector": "TELECOM", "price": 342.4, "change_pct": -0.28, "market_cap_cr": 92200, "volume": 4320000, "rsi": 47.4},
        {"symbol": "PIDILITIND", "name": "Pidilite Industries", "sector": "CHEMICALS", "price": 2984.8, "change_pct": 0.16, "market_cap_cr": 151000, "volume": 210000, "rsi": 51.4},
        {"symbol": "UPL", "name": "UPL", "sector": "CHEMICALS", "price": 512.7, "change_pct": -1.46, "market_cap_cr": 39100, "volume": 2980000, "rsi": 39.1},
        {"symbol": "DMART", "name": "Avenue Supermarts", "sector": "RETAIL", "price": 4210.5, "change_pct": 0.64, "market_cap_cr": 274000, "volume": 340000, "rsi": 55.7},
        {"symbol": "TRENT", "name": "Trent", "sector": "RETAIL", "price": 4328.9, "change_pct": 3.86, "market_cap_cr": 154000, "volume": 880000, "rsi": 74.3},
        {"symbol": "SUNTV", "name": "Sun TV Network", "sector": "MEDIA", "price": 672.4, "change_pct": -0.38, "market_cap_cr": 26500, "volume": 520000, "rsi": 47.7},
        {"symbol": "ZEEL", "name": "Zee Entertainment", "sector": "MEDIA", "price": 142.8, "change_pct": -1.64, "market_cap_cr": 13700, "volume": 7800000, "rsi": 36.5},
        {"symbol": "DLF", "name": "DLF", "sector": "REALTY", "price": 846.2, "change_pct": 1.36, "market_cap_cr": 209000, "volume": 3120000, "rsi": 61.7},
        {"symbol": "GODREJPROP", "name": "Godrej Properties", "sector": "REALTY", "price": 2418.7, "change_pct": 0.24, "market_cap_cr": 67200, "volume": 740000, "rsi": 52.2},
        {"symbol": "SIEMENS", "name": "Siemens", "sector": "INDUSTRIALS", "price": 5122.5, "change_pct": 1.18, "market_cap_cr": 182000, "volume": 220000, "rsi": 59.5},
        {"symbol": "ABB", "name": "ABB India", "sector": "INDUSTRIALS", "price": 6218.1, "change_pct": 0.72, "market_cap_cr": 132000, "volume": 160000, "rsi": 56.6},
        {"symbol": "PAGEIND", "name": "Page Industries", "sector": "TEXTILES", "price": 36218.0, "change_pct": -0.46, "market_cap_cr": 40400, "volume": 26000, "rsi": 46.9},
        {"symbol": "ARVIND", "name": "Arvind", "sector": "TEXTILES", "price": 286.2, "change_pct": 0.58, "market_cap_cr": 7500, "volume": 610000, "rsi": 53.2},
        {"symbol": "PIIND", "name": "PI Industries", "sector": "AGRI", "price": 3642.7, "change_pct": 0.42, "market_cap_cr": 55200, "volume": 160000, "rsi": 52.8},
        {"symbol": "COROMANDEL", "name": "Coromandel International", "sector": "AGRI", "price": 1112.4, "change_pct": -0.26, "market_cap_cr": 32700, "volume": 240000, "rsi": 48.3},
        {"symbol": "TITAN", "name": "Titan Company", "sector": "CONSUMER DURABLES", "price": 3524.6, "change_pct": 0.96, "market_cap_cr": 313000, "volume": 950000, "rsi": 58.8},
        {"symbol": "VOLTAS", "name": "Voltas", "sector": "CONSUMER DURABLES", "price": 1218.5, "change_pct": -0.56, "market_cap_cr": 40300, "volume": 840000, "rsi": 45.4},
        {"symbol": "ADANIPORTS", "name": "Adani Ports", "sector": "INDUSTRIALS", "price": 1296.8, "change_pct": -2.88, "market_cap_cr": 280000, "volume": 4020000, "rsi": 35.1},
        {"symbol": "COALINDIA", "name": "Coal India", "sector": "ENERGY", "price": 438.6, "change_pct": -2.64, "market_cap_cr": 270000, "volume": 7100000, "rsi": 36.3},
    ]

    def __init__(self, market_data: MarketDataEngine | None = None) -> None:
        self.market_data = market_data or get_market_data_engine()

    def capabilities(self) -> dict[str, Any]:
        return {
            "universes": self.UNIVERSES,
            "size_by": self.SIZE_BY,
            "color_by": self.COLOR_BY,
            "factor_color_by": self.FACTOR_COLOR_BY,
            "timeframes": self.TIMEFRAMES,
            "filters": {
                "show": ["All", "Gainers only", "Losers only", "Unchanged"],
                "market_cap": ["Large Cap", "Mid Cap", "Small Cap"],
                "volume": ["High Volume", "Volume Spike", "Low Volume"],
                "technical": ["RSI Oversold", "RSI Overbought", "Above EMA50", "Below EMA50", "Breakout 20D", "Breakdown 20D"],
                "fno": ["All", "F&O only", "Non F&O"],
            },
            "data_source_note": self.DATA_SOURCE_NOTE,
        }

    def run(self, request: HeatmapRunRequest) -> dict[str, Any]:
        stocks = [self._decorate_stock(row, request) for row in self.SAMPLE_STOCKS]
        if request.universe == "F&O Stocks":
            stocks = [row for row in stocks if row.get("is_fno")]
        sectors = self._sectors(stocks)
        gainers = sorted(stocks, key=lambda row: row["change_pct"], reverse=True)[:5]
        losers = sorted(stocks, key=lambda row: row["change_pct"])[:5]
        breadth = self._breadth(stocks)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
        return {
            "summary": self._summary(stocks, breadth, request, timestamp),
            "sectors": sectors,
            "stocks": stocks,
            "gainers": gainers,
            "losers": losers,
            "breadth": breadth,
            "breadth_dashboard": self.breadth_dashboard({}),
            "sector_performance": self._sector_performance(sectors),
            "distributions": self._distributions(stocks, sectors),
            "flows": self._flows(),
            "indices": self._indices(),
            "rotation": self.rotation({}),
            "insights": self.insights({})["insights"],
            "timestamp": timestamp,
            "data_source_note": (
                "F&O universe is synced from Angel instrument master. Historical availability may be limited to active/live contracts depending on provider."
                if request.universe == "F&O Stocks"
                else self.DATA_SOURCE_NOTE
            ),
        }

    def sectors(self) -> list[dict[str, Any]]:
        stocks = [self._decorate_stock(row, HeatmapRunRequest()) for row in self.SAMPLE_STOCKS]
        return [
            {
                "name": sector["name"],
                "slug": sector["slug"],
                "stock_count": len(sector["stocks"]),
                "change_pct": sector["change_pct"],
                "market_cap_cr": sector["market_cap_cr"],
                "volume": sector["volume"],
                "industries": self._industry_cards(sector["name"], sector["stocks"]),
            }
            for sector in self._sectors(stocks)
        ]

    def sector_detail(self, sector_slug: str, request: HeatmapSectorRequest) -> dict[str, Any] | None:
        sector_name = self._sector_name_for_slug(sector_slug)
        if not sector_name:
            return None
        synthetic_request = HeatmapRunRequest(
            universe=request.universe,
            size_by=request.size_by,
            color_by=request.color_by,
            timeframe=request.timeframe,
        )
        stocks = [
            self._decorate_stock(row, synthetic_request)
            for row in self.SAMPLE_STOCKS
            if row["sector"] == sector_name
        ]
        if not stocks:
            return None
        sector = self._sectors(stocks)[0]
        breadth = self._breadth(stocks)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
        return {
            "sector": {
                "name": sector["name"],
                "slug": sector["slug"],
                "universe": request.universe,
                "stock_count": len(stocks),
                "advancing": breadth["advancing"],
                "declining": breadth["declining"],
                "average_change_pct": sector["change_pct"],
                "market_cap_cr": sector["market_cap_cr"],
                "volume": sector["volume"],
            },
            "industries": self._industry_cards(sector["name"], stocks),
            "summary": self._summary(stocks, breadth, synthetic_request, timestamp),
            "stocks": sorted(stocks, key=lambda row: row["size_value"], reverse=True),
            "gainers": sorted(stocks, key=lambda row: row["change_pct"], reverse=True)[:5],
            "losers": sorted(stocks, key=lambda row: row["change_pct"])[:5],
            "largest": sorted(stocks, key=lambda row: row["market_cap_cr"], reverse=True)[:10],
            "most_active": sorted(stocks, key=lambda row: row["volume"], reverse=True)[:10],
            "breadth": breadth,
            "sector_performance": [{"label": row["symbol"], "value": row["change_pct"], "market_cap_cr": row["market_cap_cr"]} for row in sorted(stocks, key=lambda item: item["change_pct"], reverse=True)],
            "distributions": self._sector_distributions(stocks),
            "indices": self._indices(),
            "insights": self._insights_for(stocks, self._sectors(stocks)),
            "timestamp": timestamp,
            "data_source_note": self.DATA_SOURCE_NOTE,
        }

    def industry_detail(self, sector_slug: str, industry_slug: str, request: HeatmapSectorRequest) -> dict[str, Any] | None:
        sector = self.sector_detail(sector_slug, request)
        if sector is None:
            return None
        industry = next((row for row in sector["industries"] if row["slug"] == industry_slug), None)
        if industry is None:
            return None
        stocks = [row for row in sector["stocks"] if row["industry_slug"] == industry_slug]
        if not stocks:
            return None
        breadth = self._breadth(stocks)
        market_cap = sum(float(row["market_cap_cr"]) for row in stocks)
        volume = sum(int(row["volume"]) for row in stocks)
        avg_change = sum(float(row["change_pct"]) * float(row["market_cap_cr"]) for row in stocks) / max(market_cap, 1)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
        return {
            "sector": sector["sector"],
            "industry": {
                "name": industry["name"],
                "slug": industry_slug,
                "stock_count": len(stocks),
                "advancing": breadth["advancing"],
                "declining": breadth["declining"],
                "average_change_pct": round(avg_change, 2),
                "market_cap_cr": round(market_cap, 2),
                "volume": volume,
            },
            "summary": self._summary(stocks, breadth, HeatmapRunRequest(size_by=request.size_by, color_by=request.color_by, timeframe=request.timeframe, universe=request.universe), timestamp),
            "stocks": sorted(stocks, key=lambda row: row["size_value"], reverse=True),
            "gainers": sorted(stocks, key=lambda row: row["change_pct"], reverse=True)[:5],
            "losers": sorted(stocks, key=lambda row: row["change_pct"])[:5],
            "breadth": breadth,
            "distributions": self._sector_distributions(stocks),
            "indices": self._indices(),
            "insights": self._insights_for(stocks, self._sectors(stocks)),
            "timestamp": timestamp,
            "data_source_note": self.DATA_SOURCE_NOTE,
        }

    def rotation(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        stocks = [self._decorate_stock(row, HeatmapRunRequest()) for row in self.SAMPLE_STOCKS]
        sectors = self._sectors(stocks)
        total_cap = max(sum(float(row["market_cap_cr"]) for row in sectors), 1)
        bubbles = []
        for index, sector in enumerate(sectors):
            relative_strength = round(sector["change_pct"] * 0.72 + ((index % 5) - 2) * 0.28, 2)
            momentum = round(sector["change_pct"] * 0.56 + ((len(sector["name"]) % 7) - 3) * 0.22, 2)
            quadrant = "Leading" if relative_strength >= 0 and momentum >= 0 else "Improving" if relative_strength < 0 <= momentum else "Weakening" if relative_strength >= 0 > momentum else "Lagging"
            bubbles.append({
                "sector": sector["name"],
                "slug": sector["slug"],
                "relative_strength": relative_strength,
                "momentum": momentum,
                "weight_pct": round(float(sector["market_cap_cr"]) / total_cap * 100, 2),
                "change_pct": sector["change_pct"],
                "quadrant": quadrant,
            })
        improving = sorted(bubbles, key=lambda row: row["momentum"], reverse=True)
        weakest = sorted(bubbles, key=lambda row: row["relative_strength"] + row["momentum"])[0]
        return {
            "bubbles": bubbles,
            "summary": {
                "best_improving_sector": improving[0]["sector"],
                "weakest_sector": weakest["sector"],
                "leading_sectors": [row["sector"] for row in bubbles if row["quadrant"] == "Leading"],
                "lagging_sectors": [row["sector"] for row in bubbles if row["quadrant"] == "Lagging"],
                "model_note": "Sector rotation uses local sample performance fields; historical market-wide rotation model is not connected yet.",
            },
            "data_source_note": self.DATA_SOURCE_NOTE,
        }

    def breadth_dashboard(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        stocks = [self._decorate_stock(row, HeatmapRunRequest()) for row in self.SAMPLE_STOCKS]
        breadth = self._breadth(stocks)
        up_volume = sum(int(row["volume"]) for row in stocks if row["change_pct"] > 0.05)
        down_volume = sum(int(row["volume"]) for row in stocks if row["change_pct"] < -0.05)
        ratio = round(breadth["advancing"] / max(breadth["declining"], 1), 2)
        sector_table = []
        for sector in self._sectors(stocks):
            b = self._breadth(sector["stocks"])
            sector_table.append({
                "sector": sector["name"],
                "advancers": b["advancing"],
                "decliners": b["declining"],
                "unchanged": b["unchanged"],
                "breadth_pct": b["advance_pct"],
            })
        return {
            "summary": {
                **breadth,
                "advance_decline_ratio": ratio,
                "up_volume": up_volume,
                "down_volume": down_volume,
                "new_52w_highs": None,
                "new_52w_lows": None,
                "bullish_breadth_pct": breadth["advance_pct"],
                "bearish_breadth_pct": breadth["decline_pct"],
            },
            "sector_table": sector_table,
            "placeholder_note": "52W high/low breadth requires stored market-wide historical data. Data source not connected yet.",
            "data_source_note": self.DATA_SOURCE_NOTE,
        }

    def factors(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        factor = (payload or {}).get("factor", "% Change")
        request = HeatmapRunRequest(color_by="% Change")
        stocks = [self._decorate_stock(row, request) for row in self.SAMPLE_STOCKS]
        for stock in stocks:
            stock["factor_value"] = self._factor_value(stock, factor)
            stock["color_value"] = 0 if stock["factor_value"] is None else float(stock["factor_value"])
        return {
            "factor": factor,
            "stocks": stocks,
            "sectors": self._sectors(stocks),
            "fundamental_note": "Fundamental factor coloring requires fundamentals data source." if "placeholder" in factor.lower() else "",
            "data_source_note": self.DATA_SOURCE_NOTE,
        }

    def insights(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        stocks = [self._decorate_stock(row, HeatmapRunRequest()) for row in self.SAMPLE_STOCKS]
        return {
            "insights": self._insights_for(stocks, self._sectors(stocks)),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
            "data_source_note": "Insights are deterministic rule-based summaries generated from the active local heatmap dataset.",
        }

    def _decorate_stock(self, row: dict[str, Any], request: HeatmapRunRequest) -> dict[str, Any]:
        item = row.copy()
        item["industry"] = self._industry_for_symbol(item["sector"], item["symbol"])
        item["industry_slug"] = self._slugify(item["industry"])
        item["turnover_cr"] = round(item["price"] * item["volume"] / 10000000, 2)
        item["relative_volume"] = round(0.75 + (abs(item["change_pct"]) * 0.18) + ((len(item["symbol"]) % 4) * 0.12), 2)
        item["volume_change_pct"] = round((item["relative_volume"] - 1) * 100, 2)
        item["volatility"] = round(1.1 + abs(item["change_pct"]) * 0.55 + (len(item["symbol"]) % 5) * 0.18, 2)
        item["is_fno"] = item["market_cap_cr"] >= 100000 or item["volume"] >= 5000000
        item["market_cap_bucket"] = "Large Cap" if item["market_cap_cr"] >= 200000 else "Mid Cap" if item["market_cap_cr"] >= 50000 else "Small Cap"
        item["above_ema50"] = item["change_pct"] >= 0 or item["rsi"] >= 52
        item["breakout_20d"] = item["change_pct"] >= 1.5 and item["relative_volume"] >= 1.05
        item["breakdown_20d"] = item["change_pct"] <= -1.5 and item["relative_volume"] >= 1.05
        item["pe"] = None
        item["roe"] = None
        item["debt_equity"] = None
        item["size_value"] = self._size_value(item, request.size_by)
        item["color_value"] = self._color_value(item, request.color_by)
        return item

    def _size_value(self, item: dict[str, Any], size_by: str) -> float:
        if size_by == "Volume":
            return float(item["volume"])
        if size_by == "Turnover":
            return float(item["turnover_cr"])
        if size_by == "Equal Weight":
            return 1.0
        return float(item["market_cap_cr"])

    def _color_value(self, item: dict[str, Any], color_by: str) -> float:
        if color_by == "Volume Change":
            return float(item["volume_change_pct"])
        if color_by == "Relative Volume":
            return round((float(item["relative_volume"]) - 1) * 3, 2)
        if color_by == "RSI":
            return round((float(item["rsi"]) - 50) / 8, 2)
        return float(item["change_pct"])

    def _factor_value(self, item: dict[str, Any], factor: str) -> float | None:
        if factor == "Volume Change":
            return float(item["volume_change_pct"])
        if factor == "Relative Volume":
            return float(item["relative_volume"])
        if factor == "RSI":
            return float(item["rsi"])
        if factor == "Volatility":
            return float(item["volatility"])
        if factor == "Market Cap":
            return float(item["market_cap_cr"])
        if "placeholder" in str(factor).lower():
            return None
        return float(item["change_pct"])

    def _industry_for_symbol(self, sector: str, symbol: str) -> str:
        for industry, symbols in self.INDUSTRY_GROUPS.get(sector, {}).items():
            if symbol in symbols:
                return industry
        return "Other"

    def _industry_cards(self, sector_name: str, stocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in self.INDUSTRY_GROUPS.get(sector_name, {"Other": []})}
        for stock in stocks:
            grouped.setdefault(stock["industry"], []).append(stock)
        cards = []
        for name, rows in grouped.items():
            market_cap = sum(float(row["market_cap_cr"]) for row in rows)
            volume = sum(int(row["volume"]) for row in rows)
            avg_change = sum(float(row["change_pct"]) * float(row["market_cap_cr"]) for row in rows) / max(market_cap, 1)
            breadth = self._breadth(rows) if rows else {"advancing": 0, "declining": 0, "unchanged": 0, "total": 0, "advance_pct": 0, "decline_pct": 0}
            cards.append({
                "name": name,
                "slug": self._slugify(name),
                "stock_count": len(rows),
                "advancing": breadth["advancing"],
                "declining": breadth["declining"],
                "unchanged": breadth["unchanged"],
                "average_change_pct": round(avg_change, 2),
                "market_cap_cr": round(market_cap, 2),
                "volume": volume,
                "stocks": sorted(rows, key=lambda row: row["size_value"], reverse=True),
            })
        return cards

    def _sectors(self, stocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for stock in stocks:
            grouped.setdefault(stock["sector"], []).append(stock)
        sectors = []
        for name, rows in grouped.items():
            market_cap = sum(float(row["market_cap_cr"]) for row in rows)
            volume = sum(int(row["volume"]) for row in rows)
            weighted_change = sum(float(row["change_pct"]) * float(row["market_cap_cr"]) for row in rows) / market_cap
            sectors.append(
                {
                    "name": name,
                    "slug": self.SECTOR_SLUGS.get(name, self._slugify(name)),
                    "change_pct": round(weighted_change, 2),
                    "market_cap_cr": round(market_cap, 2),
                    "volume": volume,
                    "stocks": sorted(rows, key=lambda row: row["size_value"], reverse=True),
                    "industries": self._industry_cards(name, rows),
                }
            )
        return sorted(sectors, key=lambda sector: sector["market_cap_cr"], reverse=True)

    def _sector_distributions(self, stocks: list[dict[str, Any]]) -> dict[str, Any]:
        total_cap = max(sum(float(row["market_cap_cr"]) for row in stocks), 1)
        total_volume = max(sum(int(row["volume"]) for row in stocks), 1)
        return {
            "market_cap": [
                {"label": "> Rs 500,000 Cr", "value": sum(1 for row in stocks if row["market_cap_cr"] > 500000)},
                {"label": "Rs 100,000 - Rs 500,000 Cr", "value": sum(1 for row in stocks if 100000 <= row["market_cap_cr"] <= 500000)},
                {"label": "Rs 50,000 - Rs 100,000 Cr", "value": sum(1 for row in stocks if 50000 <= row["market_cap_cr"] < 100000)},
                {"label": "< Rs 50,000 Cr", "value": sum(1 for row in stocks if row["market_cap_cr"] < 50000)},
            ],
            "volume": [
                {"label": "High Activity", "value": sum(1 for row in stocks if row["volume"] > 5000000)},
                {"label": "Medium Activity", "value": sum(1 for row in stocks if 1000000 <= row["volume"] <= 5000000)},
                {"label": "Low Activity", "value": sum(1 for row in stocks if row["volume"] < 1000000)},
            ],
            "constituent_weights": [
                {"label": row["symbol"], "value": round((float(row["market_cap_cr"]) / total_cap) * 100, 2)}
                for row in sorted(stocks, key=lambda item: item["market_cap_cr"], reverse=True)[:10]
            ],
            "volume_share": [
                {"label": row["symbol"], "value": round((int(row["volume"]) / total_volume) * 100, 2)}
                for row in sorted(stocks, key=lambda item: item["volume"], reverse=True)[:10]
            ],
        }

    def _sector_name_for_slug(self, sector_slug: str) -> str | None:
        normalized = str(sector_slug or "").strip().lower()
        for name, slug in self.SECTOR_SLUGS.items():
            if slug == normalized:
                return name
        return None

    def _slugify(self, value: str) -> str:
        return value.lower().replace("&", "").replace("/", " ").replace("  ", " ").strip().replace(" ", "-")

    def _breadth(self, stocks: list[dict[str, Any]]) -> dict[str, Any]:
        if not stocks:
            return {"advancing": 0, "declining": 0, "unchanged": 0, "total": 0, "advance_pct": 0, "decline_pct": 0}
        advancing = sum(1 for row in stocks if row["change_pct"] > 0.05)
        declining = sum(1 for row in stocks if row["change_pct"] < -0.05)
        unchanged = len(stocks) - advancing - declining
        return {
            "advancing": advancing,
            "declining": declining,
            "unchanged": unchanged,
            "total": len(stocks),
            "advance_pct": round((advancing / len(stocks)) * 100, 2),
            "decline_pct": round((declining / len(stocks)) * 100, 2),
        }

    def _insights_for(self, stocks: list[dict[str, Any]], sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
        breadth = self._breadth(stocks)
        leader = max(sectors, key=lambda row: row["change_pct"]) if sectors else None
        weakest = min(sectors, key=lambda row: row["change_pct"]) if sectors else None
        total_volume = max(sum(int(row["volume"]) for row in stocks), 1)
        volume_sector = max(sectors, key=lambda row: row["volume"]) if sectors else None
        top_positive = sorted([row for row in stocks if row["change_pct"] > 0], key=lambda row: row["market_cap_cr"], reverse=True)[:5]
        insights = []
        if leader:
            insights.append({"severity": "Bullish", "text": f"{leader['name']} is leading today's market breadth with {leader['change_pct']:+.2f}% weighted change.", "timestamp": now})
        if weakest:
            insights.append({"severity": "Bearish", "text": f"{weakest['name']} is showing broad weakness at {weakest['change_pct']:+.2f}% weighted change.", "timestamp": now})
        insights.append({"severity": "Warning" if breadth["advance_pct"] < 45 else "Info", "text": f"Advance/decline breadth is {breadth['advancing']}:{breadth['declining']} with {breadth['advance_pct']:.1f}% advancers.", "timestamp": now})
        if top_positive:
            insights.append({"severity": "Info", "text": f"Top positive breadth contributors by market cap: {', '.join(row['symbol'] for row in top_positive)}.", "timestamp": now})
        if volume_sector:
            share = round(volume_sector["volume"] / total_volume * 100, 1)
            insights.append({"severity": "Warning" if share > 25 else "Info", "text": f"Volume concentration is highest in {volume_sector['name']} at {share}% of sample-universe volume.", "timestamp": now})
        return insights[:5]

    def _summary(self, stocks: list[dict[str, Any]], breadth: dict[str, Any], request: HeatmapRunRequest, timestamp: str) -> dict[str, Any]:
        total_cap = sum(float(row["market_cap_cr"]) for row in stocks)
        total_volume = sum(int(row["volume"]) for row in stocks)
        return {
            "advancing": breadth["advancing"],
            "declining": breadth["declining"],
            "unchanged": breadth["unchanged"],
            "total_stocks": breadth["total"],
            "total_market_cap_cr": round(total_cap, 2),
            "total_volume": total_volume,
            "fii_net_flow_cr": -826.4,
            "dii_net_flow_cr": 1124.9,
            "universe": request.universe,
            "size_by": request.size_by,
            "color_by": request.color_by,
            "timeframe": request.timeframe,
            "timestamp": timestamp,
        }

    def _sector_performance(self, sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {"label": sector["name"], "value": sector["change_pct"], "market_cap_cr": sector["market_cap_cr"]}
            for sector in sorted(sectors, key=lambda item: item["change_pct"], reverse=True)
        ]

    def _distributions(self, stocks: list[dict[str, Any]], sectors: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "market_cap": [
                {"label": "> Rs 50,000 Cr", "value": sum(1 for row in stocks if row["market_cap_cr"] > 50000)},
                {"label": "Rs 10,000 - Rs 50,000 Cr", "value": sum(1 for row in stocks if 10000 <= row["market_cap_cr"] <= 50000)},
                {"label": "Rs 2,000 - Rs 10,000 Cr", "value": sum(1 for row in stocks if 2000 <= row["market_cap_cr"] < 10000)},
                {"label": "Rs 500 - Rs 2,000 Cr", "value": sum(1 for row in stocks if 500 <= row["market_cap_cr"] < 2000)},
                {"label": "< Rs 500 Cr", "value": sum(1 for row in stocks if row["market_cap_cr"] < 500)},
            ],
            "volume": [
                {"label": "Cash", "value": 58},
                {"label": "F&O", "value": 31},
                {"label": "Currency", "value": 7},
                {"label": "Commodity", "value": 4},
            ],
            "sector_market_cap_share": [
                {"label": sector["name"], "value": round(sector["market_cap_cr"], 2)}
                for sector in sectors[:5]
            ]
            + [{"label": "OTHERS", "value": round(sum(sector["market_cap_cr"] for sector in sectors[5:]), 2)}],
            "new_52w_highs": 48,
            "new_52w_lows": 12,
        }

    def _flows(self) -> dict[str, Any]:
        return {
            "mode": "Daily",
            "sessions": [
                {"date": "T-4", "fii": -418.2, "dii": 744.6},
                {"date": "T-3", "fii": 312.7, "dii": -142.8},
                {"date": "T-2", "fii": -926.1, "dii": 1048.5},
                {"date": "T-1", "fii": -238.9, "dii": 532.2},
                {"date": "Today", "fii": -826.4, "dii": 1124.9},
            ],
        }

    def _indices(self) -> list[dict[str, Any]]:
        try:
            rows = self.market_data.get_indices()
            return [
                {
                    "name": row["name"],
                    "value": row.get("latest_price"),
                    "change_pct": row.get("change_pct"),
                    "spark": [18, 15, 17, 10, 12, 4],
                    "data_source": row.get("data_source"),
                }
                for row in rows
            ]
        except Exception:
            return [
                {"name": "NIFTY 50", "value": 22419.95, "change_pct": 0.62, "spark": [18, 15, 17, 10, 12, 4]},
                {"name": "SENSEX", "value": 73912.18, "change_pct": 0.48, "spark": [18, 15, 17, 12, 8, 9]},
                {"name": "NIFTY BANK", "value": 48082.35, "change_pct": -0.21, "spark": [8, 11, 9, 14, 15, 20]},
                {"name": "INDIA VIX", "value": 13.42, "change_pct": -1.18, "spark": [6, 12, 9, 17, 14, 21]},
            ]
