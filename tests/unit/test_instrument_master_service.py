from app.services.data.instrument_master_service import InstrumentMasterService


def test_sync_parser_filters_equity_nse_bse_records():
    payload = [
        {
            "exch_seg": "NSE",
            "symbol": "RELIANCE-EQ",
            "name": "RELIANCE INDUSTRIES",
            "token": "2885",
            "instrumenttype": "",
            "lotsize": "1",
            "tick_size": "5.000000",
        },
        {
            "exch_seg": "BSE",
            "symbol": "TCS",
            "name": "TATA CONSULTANCY SERVICES",
            "token": "532540",
            "instrumenttype": "EQ",
            "lotsize": "1",
            "tick_size": "1.000000",
        },
        {"exch_seg": "NFO", "symbol": "RELIANCE25APR", "name": "FUT", "token": "1", "instrumenttype": "FUTSTK"},
        {"exch_seg": "NSE", "symbol": "NIFTY", "name": "NIFTY", "token": "999", "instrumenttype": "AMXIDX"},
    ]

    records = InstrumentMasterService().parse_records(payload)

    assert [record.symbol for record in records] == ["RELIANCE", "TCS"]
    assert records[0].exchange == "NSE"
    assert records[0].token == "2885"
    assert records[0].lot_size == 1
    assert records[0].tick_size == 5.0


def test_fallback_mapping_resolves_without_synced_master():
    instrument = InstrumentMasterService().resolve(
        None,
        query="Reliance",
        exchange="NSE",
        token=None,
    )

    assert instrument is not None
    assert instrument.symbol == "RELIANCE"
    assert instrument.token == "2885"
