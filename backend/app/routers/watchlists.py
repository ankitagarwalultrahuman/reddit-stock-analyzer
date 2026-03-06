"""Watchlist metadata router."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_watchlists():
    from watchlist_manager import list_watchlists

    return list_watchlists()
