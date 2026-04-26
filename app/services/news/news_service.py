from __future__ import annotations

from datetime import datetime
from typing import Any


class NewsService:
    DATA_SOURCE_NOTE = "News data is local/sample for UI demonstration. Real news feed integration coming soon."
    CATEGORIES = ["Economy", "Companies", "Sectors", "Global Markets", "FII/DII", "Earnings", "IPO", "Press Releases"]
    TABS = ["Market News", "My Feed", "Categories", "Companies", "Sectors", "Economy", "Global Markets", "FII/DII", "Earnings", "IPO", "Press Releases"]

    TOP_NEWS = [
        {"time": "09:15", "headline": "RBI keeps repo rate unchanged at 6.50%, maintains neutral stance", "tag": "Economy", "symbol": None, "sentiment": "Neutral", "category": "Economy", "impact": "High", "summary": "Policy-sensitive sectors remain in focus after the rate decision."},
        {"time": "09:38", "headline": "HDFC Bank hits record high; Q1 PAT grows 18% YoY", "tag": "HDFCBANK", "symbol": "HDFCBANK", "sentiment": "Bullish", "category": "HDFCBANK", "impact": "High", "summary": "Banking names lead the large-cap tape in local sample data."},
        {"time": "10:05", "headline": "Reliance Industries to invest Rs 75,000 Cr in green energy projects", "tag": "RELIANCE", "symbol": "RELIANCE", "sentiment": "Bullish", "category": "RELIANCE", "impact": "High", "summary": "Energy transition capex remains a key market narrative."},
        {"time": "10:42", "headline": "IT stocks rally as US Fed hints at rate cuts later this year", "tag": "IT", "symbol": None, "sentiment": "Bullish", "category": "Sectors", "impact": "Medium", "summary": "Export-oriented technology names show improved risk appetite."},
        {"time": "11:20", "headline": "FII inflows continue for 5th straight session", "tag": "FII/DII", "symbol": None, "sentiment": "Bullish", "category": "FII/DII", "impact": "High", "summary": "Foreign flow momentum supports index breadth in the sample dashboard."},
        {"time": "12:10", "headline": "Adani Ports Q1 profit jumps 32% YoY on higher volumes", "tag": "ADANIPORTS", "symbol": "ADANIPORTS", "sentiment": "Bullish", "category": "Companies", "impact": "Medium", "summary": "Operating leverage and cargo growth are highlighted in the sample note."},
        {"time": "13:05", "headline": "Crude oil prices rise on Middle East tensions", "tag": "Commodities", "symbol": None, "sentiment": "Bearish", "category": "Commodities", "impact": "Medium", "summary": "Higher crude can weigh on import-sensitive sectors."},
        {"time": "14:30", "headline": "Pharma stocks under pressure after US FDA warning on imports", "tag": "Pharma", "symbol": None, "sentiment": "Bearish", "category": "Sectors", "impact": "Medium", "summary": "Regulatory headlines keep pharma breadth mixed."},
    ]

    def capabilities(self) -> dict[str, Any]:
        return {"tabs": self.TABS, "categories": self.CATEGORIES, "sections": ["top_news", "featured_insights", "flows", "earnings", "sentiment"], "data_source_note": self.DATA_SOURCE_NOTE}

    def feed(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        query = str((payload or {}).get("query", "")).strip().lower()
        category = str((payload or {}).get("category", "")).strip()
        top_news = self.TOP_NEWS
        if query:
            top_news = [row for row in top_news if query in row["headline"].lower() or query in row["tag"].lower()]
        if category and category != "All":
            top_news = [row for row in top_news if row["category"] == category or row["tag"] == category]
        return {
            "top_news": top_news,
            "featured_insights": self._featured_insights(),
            "sector_news": self._sector_news(),
            "most_read": self._most_read(),
            "fii_dii_flows": self.flows({})["flows"],
            "earnings_calendar": self.earnings({})["earnings"],
            "sentiment": self.sentiment({})["sentiment"],
            "impact_breakdown": self._impact_breakdown(),
            "global_markets": self._global_markets(),
            "commodities": self._commodities(),
            "currency": self._currency(),
            "insider_deals": self._insider_deals(),
            "ticker_items": self._ticker_items(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
            "data_source_note": self.DATA_SOURCE_NOTE,
        }

    def sentiment(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "sentiment": {
                "overall_score": 64,
                "overall_label": "Bullish",
                "items": [
                    {"label": "Overall Market Sentiment", "score": 64, "status": "Bullish"},
                    {"label": "News Sentiment", "score": 61, "status": "Bullish"},
                    {"label": "Social Media Sentiment", "score": 50, "status": "Neutral", "placeholder": True},
                    {"label": "Analyst Sentiment", "score": 58, "status": "Neutral"},
                    {"label": "Options Sentiment (PCR)", "score": 67, "status": "Bullish"},
                ],
            },
            "data_source_note": self.DATA_SOURCE_NOTE,
        }

    def flows(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "flows": [
                {"label": "FII Cash", "amount_cr": 1248.6},
                {"label": "DII Cash", "amount_cr": -428.2},
                {"label": "FII Index Futures", "amount_cr": 682.4},
                {"label": "FII Stock Futures", "amount_cr": -215.8},
                {"label": "FII Index Options", "amount_cr": 318.9},
                {"label": "FII Stock Options", "amount_cr": -96.5},
                {"label": "Net FII/DII", "amount_cr": 820.4},
            ],
            "tabs": ["Cash Market", "F&O Market"],
            "data_source_note": self.DATA_SOURCE_NOTE,
        }

    def earnings(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "earnings": [
                {"symbol": "HDFCBANK", "label": "Q1 FY25 Results", "date": "Sample date", "time_status": "After Market"},
                {"symbol": "INFY", "label": "Q1 FY25 Results", "date": "Sample date", "time_status": "After Market"},
                {"symbol": "TCS", "label": "Q1 FY25 Results", "date": "Sample date", "time_status": "Before Market"},
                {"symbol": "BAJFINANCE", "label": "Q1 FY25 Results", "date": "Sample date", "time_status": "After Market"},
                {"symbol": "DMART", "label": "Q1 FY25 Results", "date": "Sample date", "time_status": "Before Market"},
            ],
            "tabs": ["Today", "Tomorrow", "This Week"],
            "data_source_note": self.DATA_SOURCE_NOTE,
        }

    def _featured_insights(self) -> list[dict[str, Any]]:
        return [
            {"headline": "Market Outlook: Consolidation likely to continue; 23,000 is key resistance for Nifty", "summary": "Local/sample research view flags range-bound trade with banking leadership and selective IT recovery.", "author": "Local Research Desk", "category": "Market Outlook", "featured": True},
            {"headline": "Banking sector outlook remains positive on strong credit growth", "summary": "Credit growth and stable asset quality keep sector sentiment constructive.", "author": "Local Research Desk", "category": "Banks"},
            {"headline": "Top 5 midcap stocks to watch in next trading session", "summary": "Momentum scanner highlights liquidity-backed midcap candidates.", "author": "Local Research Desk", "category": "Midcap"},
            {"headline": "RBI policy impact on NBFC sector: Key takeaways", "summary": "Funding cost sensitivity remains the key factor for NBFC spreads.", "author": "Local Research Desk", "category": "Policy"},
        ]

    def _sector_news(self) -> list[dict[str, Any]]:
        return [
            {"sector": "Banks", "headline": "Private banks lead sample breadth as credit growth stays firm", "time_ago": "12m", "sentiment": "Bullish", "href": "/heatmap/sector/financial-services"},
            {"sector": "IT Services", "headline": "IT services recover on global rate-cut hopes", "time_ago": "24m", "sentiment": "Bullish", "href": "/heatmap/sector/information-technology"},
            {"sector": "Pharma", "headline": "Pharma slips after regulatory caution", "time_ago": "41m", "sentiment": "Bearish", "href": "/heatmap/sector/pharma-healthcare"},
            {"sector": "Auto", "headline": "Auto demand commentary remains mixed", "time_ago": "1h", "sentiment": "Neutral", "href": "/heatmap/sector/automobile"},
            {"sector": "Energy", "headline": "Energy names active as crude rises", "time_ago": "1h", "sentiment": "Neutral", "href": "/heatmap/sector/energy"},
        ]

    def _most_read(self) -> list[str]:
        return ["Nifty eyes 23,000 mark; banking stocks in focus", "RBI keeps rates unchanged; growth forecast revised", "FII inflows drive markets higher for fifth day", "Top largecap gainers and losers today", "Global markets rally on Fed rate cut hopes"]

    def _impact_breakdown(self) -> list[dict[str, Any]]:
        return [{"label": "High Impact", "count": 8, "accent": "red"}, {"label": "Medium Impact", "count": 15, "accent": "amber"}, {"label": "Low Impact", "count": 22, "accent": "green"}, {"label": "Informational", "count": 35, "accent": "blue"}]

    def _global_markets(self) -> list[dict[str, Any]]:
        return [{"name": "Dow Jones", "value": 38942.1, "change_pct": 0.42, "spark": [18, 14, 16, 9, 11, 7]}, {"name": "Nasdaq", "value": 16612.3, "change_pct": 0.88, "spark": [20, 17, 13, 10, 8, 5]}, {"name": "FTSE 100", "value": 8239.4, "change_pct": -0.18, "spark": [8, 10, 11, 9, 13, 15]}, {"name": "Nikkei 225", "value": 38220.7, "change_pct": 0.31, "spark": [16, 15, 12, 10, 9, 8]}]

    def _commodities(self) -> list[dict[str, Any]]:
        return [{"name": "Gold (MCX)", "price": 72140, "change_pct": 0.34}, {"name": "Silver (MCX)", "price": 88920, "change_pct": -0.22}, {"name": "Crude Oil (WTI)", "price": 82.4, "change_pct": 1.1}, {"name": "Natural Gas", "price": 2.72, "change_pct": -0.48}]

    def _currency(self) -> list[dict[str, Any]]:
        return [{"name": "USD/INR", "price": 83.42, "change_pct": 0.04}, {"name": "EUR/INR", "price": 90.18, "change_pct": -0.12}, {"name": "GBP/INR", "price": 105.71, "change_pct": 0.18}, {"name": "JPY/INR", "price": 0.54, "change_pct": -0.08}]

    def _insider_deals(self) -> list[dict[str, Any]]:
        return [{"company": "Reliance Industries", "type": "Block Deal", "amount": "Rs 1,245 Cr"}, {"company": "HDFC Bank", "type": "Insider Buy", "amount": "Rs 125 Cr"}, {"company": "TCS", "type": "Insider Sell", "amount": "Rs 78 Cr"}, {"company": "Larsen & Toubro", "type": "Block Deal", "amount": "Rs 512 Cr"}, {"company": "Infosys", "type": "Insider Buy", "amount": "Rs 95 Cr"}]

    def _ticker_items(self) -> list[str]:
        return ["05:30 PM | Nifty Bank up 1.06% today", "HDFC Bank hits all-time high", "FII inflows continue", "Crude oil up 1.1%", "Rupee closes flat", "RBI keeps rates unchanged", "More updates from local/sample feed"]

    def _ticker_indices(self) -> list[dict[str, Any]]:
        return [{"name": "NIFTY 50", "value": 22419.95, "change": 138.2, "change_pct": 0.62}, {"name": "BANK NIFTY", "value": 48082.35, "change": 506.4, "change_pct": 1.06}, {"name": "SENSEX", "value": 73912.18, "change": 354.1, "change_pct": 0.48}, {"name": "NIFTY MIDCAP 100", "value": 51120.4, "change": -86.2, "change_pct": -0.17}, {"name": "NIFTY SMALLCAP 100", "value": 16740.8, "change": 42.6, "change_pct": 0.26}, {"name": "INDIA VIX", "value": 13.42, "change": -0.16, "change_pct": -1.18}, {"name": "USD/INR", "value": 83.42, "change": 0.03, "change_pct": 0.04}, {"name": "GOLD", "value": 72140, "change": 245, "change_pct": 0.34}, {"name": "CRUDE OIL", "value": 82.4, "change": 0.9, "change_pct": 1.1}]

    def page_data(self) -> dict[str, Any]:
        data = self.feed({})
        data["capabilities"] = self.capabilities()
        data["ticker_indices"] = self._ticker_indices()
        return data
