import pandas as pd
import plotly.graph_objects as go

class ChartService:
    def equity_curve(self, equity_curve: list[dict], title: str) -> str:
        frame = pd.DataFrame(equity_curve)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=frame["timestamp"], y=frame["equity"], mode="lines", name="Equity"))
        fig.update_layout(title=f"Equity Curve - {title}", xaxis_title="Time", yaxis_title="Equity", template="plotly_white")
        return fig.to_html(include_plotlyjs="cdn", full_html=False)

    def drawdown_curve(self, equity_curve: list[dict], title: str) -> str:
        frame = pd.DataFrame(equity_curve)
        frame["peak_equity"] = frame["equity"].cummax()
        frame["drawdown_pct"] = (
            ((frame["peak_equity"] - frame["equity"]) / frame["peak_equity"].replace(0, pd.NA)) * 100
        ).fillna(0).round(2)

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=frame["timestamp"],
                y=frame["drawdown_pct"],
                mode="lines",
                name="Drawdown",
                fill="tozeroy",
                line={"color": "#c53b3b"},
            )
        )
        fig.update_layout(
            title=f"Drawdown - {title}",
            xaxis_title="Time",
            yaxis_title="Drawdown %",
            template="plotly_white",
        )
        fig.update_yaxes(rangemode="tozero")
        return fig.to_html(include_plotlyjs="cdn", full_html=False)

    def price_chart(self, df: pd.DataFrame, title: str) -> str:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], mode="lines", name="Close"))
        fig.update_layout(title=title, xaxis_title="Date", yaxis_title="Price", template="plotly_white")
        return fig.to_html(include_plotlyjs="cdn", full_html=False)
