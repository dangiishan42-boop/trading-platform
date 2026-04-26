class DataSyncTasks:
    def run(self) -> str:
        return "sync_complete"

    def warm_fno_quote_cache(self, session=None, limit: int = 25) -> str:
        if session is None:
            return "fno_warm_cache_skipped"
        from app.services.data.instrument_master_service import InstrumentMasterService
        from app.services.market_data.engine import get_market_data_engine

        underlyings = InstrumentMasterService().fno_underlyings(session, limit=limit)["items"]
        instruments = [
            {"symbol": row.symbol, "token": row.equity_token, "exchange": row.exchange}
            for row in underlyings
            if row.equity_token
        ]
        if instruments:
            get_market_data_engine().get_quotes_bulk_fast(instruments, session=session)
        return "fno_warm_cache_complete"
