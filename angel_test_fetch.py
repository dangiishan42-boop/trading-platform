from datetime import datetime, timedelta
import pandas as pd
import pyotp
from SmartApi import SmartConnect

API_KEY = "kdI6dtbR"
CLIENT_ID = "H62003870"
PASSWORD = "2580"
TOTP_SECRET = "6D7VFAARQW4P4FNJGI5IRTHA2Q"

EXCHANGE = "NSE"
SYMBOL_TOKEN = "3045"
INTERVAL = "ONE_DAY"


def main() -> None:
    smart = SmartConnect(api_key=API_KEY)

    totp = pyotp.TOTP(TOTP_SECRET).now()
    session = smart.generateSession(CLIENT_ID, PASSWORD, totp)

    if not session or not session.get("status", False):
        raise RuntimeError(f"Login failed: {session}")

    to_date = datetime.now()
    from_date = to_date - timedelta(days=90)

    params = {
        "exchange": EXCHANGE,
        "symboltoken": SYMBOL_TOKEN,
        "interval": INTERVAL,
        "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
        "todate": to_date.strftime("%Y-%m-%d %H:%M"),
    }

    response = smart.getCandleData(params)

    if not response or not response.get("status", False):
        raise RuntimeError(f"Candle fetch failed: {response}")

    candles = response.get("data", [])
    if not candles:
        raise RuntimeError("No candle data returned")

    df = pd.DataFrame(
        candles,
        columns=["Date", "Open", "High", "Low", "Close", "Volume"]
    )

    df["Date"] = pd.to_datetime(df["Date"])

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna().sort_values("Date").reset_index(drop=True)

    print(df.head())
    print(df.tail())
    print("Rows:", len(df))

    output_file = "angel_fetched_data.csv"
    df.to_csv(output_file, index=False)
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()