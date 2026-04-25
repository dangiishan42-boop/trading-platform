from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.dependencies import get_session
from app.models.watchlist_model import Watchlist, WatchlistItem
from app.schemas.watchlist_schema import (
    WatchlistCreateRequest,
    WatchlistItemCreateRequest,
    WatchlistItemResponse,
    WatchlistResponse,
    WatchlistUpdateRequest,
)

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


def _watchlist_response(watchlist: Watchlist, items: list[WatchlistItem]) -> WatchlistResponse:
    return WatchlistResponse(
        id=watchlist.id,
        name=watchlist.name,
        created_at=watchlist.created_at,
        updated_at=watchlist.updated_at,
        items=[
            WatchlistItemResponse(
                id=item.id,
                watchlist_id=item.watchlist_id,
                symbol=item.symbol,
                exchange=item.exchange,
                token=item.token,
                display_name=item.display_name,
                created_at=item.created_at,
            )
            for item in items
        ],
    )


def _get_watchlist_or_404(session: Session, watchlist_id: int) -> Watchlist:
    watchlist = session.get(Watchlist, watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return watchlist


def _ensure_default_watchlist(session: Session) -> None:
    exists = session.exec(select(Watchlist).limit(1)).first()
    if exists is not None:
        return

    default_watchlist = Watchlist(name="Default")
    session.add(default_watchlist)
    session.commit()


@router.get("", response_model=list[WatchlistResponse])
def list_watchlists(session: Session = Depends(get_session)):
    _ensure_default_watchlist(session)
    watchlists = session.exec(select(Watchlist).order_by(Watchlist.created_at, Watchlist.id)).all()
    responses = []
    for watchlist in watchlists:
        items = session.exec(
            select(WatchlistItem)
            .where(WatchlistItem.watchlist_id == watchlist.id)
            .order_by(WatchlistItem.created_at, WatchlistItem.id)
        ).all()
        responses.append(_watchlist_response(watchlist, items))
    return responses


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def create_watchlist(payload: WatchlistCreateRequest, session: Session = Depends(get_session)):
    watchlist = Watchlist(name=payload.name)
    session.add(watchlist)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A watchlist with this name already exists",
        ) from exc
    session.refresh(watchlist)
    return _watchlist_response(watchlist, [])


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
def update_watchlist(
    watchlist_id: int,
    payload: WatchlistUpdateRequest,
    session: Session = Depends(get_session),
):
    watchlist = _get_watchlist_or_404(session, watchlist_id)
    watchlist.name = payload.name
    watchlist.updated_at = datetime.utcnow()
    session.add(watchlist)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A watchlist with this name already exists",
        ) from exc
    session.refresh(watchlist)
    items = session.exec(
        select(WatchlistItem).where(WatchlistItem.watchlist_id == watchlist.id).order_by(WatchlistItem.created_at)
    ).all()
    return _watchlist_response(watchlist, items)


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist(watchlist_id: int, session: Session = Depends(get_session)):
    watchlist = _get_watchlist_or_404(session, watchlist_id)
    items = session.exec(select(WatchlistItem).where(WatchlistItem.watchlist_id == watchlist.id)).all()
    for item in items:
        session.delete(item)
    session.delete(watchlist)
    session.commit()
    return None


@router.post("/{watchlist_id}/items", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
def add_watchlist_item(
    watchlist_id: int,
    payload: WatchlistItemCreateRequest,
    session: Session = Depends(get_session),
):
    watchlist = _get_watchlist_or_404(session, watchlist_id)
    duplicate = session.exec(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist.id,
            WatchlistItem.symbol == payload.symbol,
            WatchlistItem.exchange == payload.exchange,
        )
    ).first()
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Symbol already exists in this watchlist")

    item = WatchlistItem(
        watchlist_id=watchlist.id,
        symbol=payload.symbol,
        exchange=payload.exchange,
        token=payload.token,
        display_name=payload.display_name,
    )
    watchlist.updated_at = datetime.utcnow()
    session.add(watchlist)
    session.add(item)
    session.commit()
    session.refresh(item)
    return WatchlistItemResponse(
        id=item.id,
        watchlist_id=item.watchlist_id,
        symbol=item.symbol,
        exchange=item.exchange,
        token=item.token,
        display_name=item.display_name,
        created_at=item.created_at,
    )


@router.delete("/{watchlist_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_watchlist_item(watchlist_id: int, item_id: int, session: Session = Depends(get_session)):
    watchlist = _get_watchlist_or_404(session, watchlist_id)
    item = session.get(WatchlistItem, item_id)
    if item is None or item.watchlist_id != watchlist.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist item not found")

    watchlist.updated_at = datetime.utcnow()
    session.add(watchlist)
    session.delete(item)
    session.commit()
    return None
