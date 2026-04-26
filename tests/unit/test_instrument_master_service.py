from app.services.data.instrument_master_service import InstrumentMasterService


def test_sync_parser_extracts_equity_and_nfo_records():
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
        {
            "exch_seg": "NFO",
            "symbol": "RELIANCE25APRFUT",
            "name": "RELIANCE",
            "token": "111",
            "instrumenttype": "FUTSTK",
            "expiry": "2025-04-24",
            "lotsize": "250",
        },
        {
            "exch_seg": "NFO",
            "symbol": "RELIANCE25APR2500CE",
            "name": "RELIANCE",
            "token": "112",
            "instrumenttype": "OPTSTK",
            "expiry": "2025-04-24",
            "strike": "250000",
            "lotsize": "250",
        },
        {"exch_seg": "NSE", "symbol": "NIFTY", "name": "NIFTY", "token": "999", "instrumenttype": "AMXIDX"},
    ]

    records = InstrumentMasterService().parse_records(payload)

    assert [record.symbol for record in records] == ["RELIANCE", "TCS", "RELIANCE", "RELIANCE"]
    assert records[0].exchange == "NSE"
    assert records[0].token == "2885"
    assert records[0].lot_size == 1
    assert records[0].tick_size == 5.0
    assert records[2].exchange == "NFO"
    assert records[2].is_future is True
    assert records[2].underlying == "RELIANCE"
    assert records[3].is_option is True
    assert records[3].option_type == "CE"
    assert records[3].strike == 2500


def test_derive_fno_underlyings_returns_unique_symbols():
    service = InstrumentMasterService()
    records = service.parse_records(
        [
            {"exch_seg": "NSE", "symbol": "RELIANCE-EQ", "name": "Reliance Industries", "token": "2885", "instrumenttype": ""},
            {"exch_seg": "NFO", "symbol": "RELIANCE25APRFUT", "name": "RELIANCE", "token": "111", "instrumenttype": "FUTSTK", "expiry": "2025-04-24", "lotsize": "250"},
            {"exch_seg": "NFO", "symbol": "RELIANCE25APR2500PE", "name": "RELIANCE", "token": "113", "instrumenttype": "OPTSTK", "expiry": "2025-04-24", "strike": "250000", "lotsize": "250"},
        ]
    )

    underlyings = service.derive_fno_underlyings(records)

    assert len(underlyings) == 1
    assert underlyings[0].symbol == "RELIANCE"
    assert underlyings[0].equity_token == "2885"
    assert underlyings[0].nearest_future_token == "111"
    assert underlyings[0].has_futures is True
    assert underlyings[0].has_options is True


def test_parser_extracts_many_fno_underlyings_from_nfo_fixture():
    payload = []
    for index, symbol in enumerate(["RELIANCE", "HDFCBANK", "ICICIBANK", "TCS", "INFY", "SBIN"], start=1):
        payload.extend(
            [
                {"exch_seg": "NSE", "symbol": f"{symbol}-EQ", "name": symbol, "token": str(2000 + index), "instrumenttype": ""},
                {"exch_seg": "NFO", "symbol": f"{symbol}25APRFUT", "name": symbol, "token": str(3000 + index), "instrumenttype": "FUTSTK", "expiry": "2025-04-24", "lotsize": "100"},
                {"exch_seg": "NFO", "symbol": f"{symbol}25APR1000CE", "name": symbol, "token": str(4000 + index), "instrumenttype": "OPTSTK", "expiry": "2025-04-24", "strike": "100000", "lotsize": "100"},
            ]
        )

    service = InstrumentMasterService()
    records = service.parse_records(payload)
    underlyings = service.derive_fno_underlyings(records)

    assert len(underlyings) == 6
    assert {row.symbol for row in underlyings} == {"RELIANCE", "HDFCBANK", "ICICIBANK", "TCS", "INFY", "SBIN"}


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
