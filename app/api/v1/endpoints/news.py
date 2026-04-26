from fastapi import APIRouter

from app.schemas.news_schema import (
    NewsCapabilitiesResponse,
    NewsEarningsResponse,
    NewsFeedResponse,
    NewsFlowsResponse,
    NewsRequest,
    NewsSentimentResponse,
)
from app.services.news.news_service import NewsService

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/capabilities", response_model=NewsCapabilitiesResponse)
def capabilities():
    return NewsService().capabilities()


@router.post("/feed", response_model=NewsFeedResponse)
def feed(payload: NewsRequest):
    return NewsService().feed(payload.model_dump())


@router.post("/sentiment", response_model=NewsSentimentResponse)
def sentiment(payload: dict = {}):
    return NewsService().sentiment(payload)


@router.post("/flows", response_model=NewsFlowsResponse)
def flows(payload: dict = {}):
    return NewsService().flows(payload)


@router.post("/earnings", response_model=NewsEarningsResponse)
def earnings(payload: dict = {}):
    return NewsService().earnings(payload)
