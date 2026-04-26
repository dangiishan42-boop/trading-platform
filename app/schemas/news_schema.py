from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NewsRequest(BaseModel):
    query: str = ""
    category: str = "All"
    tab: str = "Market News"


class NewsCapabilitiesResponse(BaseModel):
    tabs: list[str]
    categories: list[str]
    sections: list[str]
    data_source_note: str


class NewsFeedResponse(BaseModel):
    top_news: list[dict[str, Any]]
    featured_insights: list[dict[str, Any]]
    sector_news: list[dict[str, Any]]
    most_read: list[str]
    fii_dii_flows: list[dict[str, Any]]
    earnings_calendar: list[dict[str, Any]]
    sentiment: dict[str, Any]
    impact_breakdown: list[dict[str, Any]]
    global_markets: list[dict[str, Any]]
    commodities: list[dict[str, Any]]
    currency: list[dict[str, Any]]
    insider_deals: list[dict[str, Any]]
    ticker_items: list[str]
    timestamp: str
    data_source_note: str = Field(default="News data is local/sample for UI demonstration. Real news feed integration coming soon.")


class NewsSentimentResponse(BaseModel):
    sentiment: dict[str, Any]
    data_source_note: str


class NewsFlowsResponse(BaseModel):
    flows: list[dict[str, Any]]
    tabs: list[str]
    data_source_note: str


class NewsEarningsResponse(BaseModel):
    earnings: list[dict[str, Any]]
    tabs: list[str]
    data_source_note: str
