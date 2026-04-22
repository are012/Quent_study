"""백테스트 결과에서 수익률, 위험, 거래 특성 지표를 계산하는 모듈."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def calculate_metrics(
    equity_curve: pd.DataFrame,
    cash: pd.DataFrame,
    fills: pd.DataFrame,
    trades: pd.DataFrame,
    market_data: pd.DataFrame,
    initial_capital: float,
    benchmark: str | None = None,
) -> dict[str, float | int | str | None]:
    """감사 추적에 필요한 핵심 성과지표를 한 번에 계산한다."""

    if equity_curve.empty:
        return {}
    # equity를 날짜 인덱스로 바꿔 수익률/드로다운 계산의 기준 시계열로 사용한다.
    equity = equity_curve.set_index("date")["equity"].astype(float)
    returns = equity.pct_change().fillna(0.0)
    # 최종 자산과 누적수익률은 모든 성과지표의 출발점이다.
    final_equity = float(equity.iloc[-1])
    total_return = final_equity / initial_capital - 1.0
    # 짧은 샘플에서도 0으로 나누지 않도록 최소 연수는 내부 헬퍼가 보정한다.
    years = _years(equity.index)
    cagr = (final_equity / initial_capital) ** (1 / years) - 1 if years > 0 else 0.0
    # 일봉 수익률을 252 거래일 기준으로 연환산한다.
    annual_return = float(returns.mean() * 252)
    volatility = float(returns.std(ddof=0) * math.sqrt(252))
    # Sortino는 음수 수익률의 변동성만 사용한다.
    downside = returns[returns < 0]
    downside_vol = float(downside.std(ddof=0) * math.sqrt(252)) if not downside.empty else 0.0
    drawdown = calculate_drawdown(equity)
    max_drawdown = float(drawdown.min())

    # 완료된 매도 거래가 없으면 pnl 시리즈는 빈 값으로 처리한다.
    pnl = trades["pnl"].astype(float) if not trades.empty and "pnl" in trades else pd.Series(dtype=float)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = float(wins.sum()) if not wins.empty else 0.0
    gross_loss = abs(float(losses.sum())) if not losses.empty else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (math.inf if gross_profit > 0 else 0.0)

    # turnover는 총 체결금액을 평균 equity로 나눠 계산한다.
    fill_notional = fills["notional"].astype(float).sum() if not fills.empty else 0.0
    avg_equity = float(equity.mean())
    exposure = (
        float(equity_curve["exposure"].astype(float).mean())
        if "exposure" in equity_curve and not equity_curve.empty
        else 0.0
    )
    cash_weight = (
        float(cash["cash_weight"].astype(float).mean())
        if not cash.empty and "cash_weight" in cash
        else None
    )
    # 벤치마크가 지정되면 해당 ticker의 buy-and-hold와 비교한다.
    benchmark_return = _benchmark_return(market_data, benchmark)

    # JSON으로 저장될 값을 단순 숫자/문자/None 중심으로 반환한다.
    return {
        "initial_capital": float(initial_capital),
        "final_equity": final_equity,
        "total_return": float(total_return),
        "cagr": float(cagr),
        "annual_return": annual_return,
        "volatility": volatility,
        "max_drawdown": max_drawdown,
        "max_drawdown_duration": max_drawdown_duration(drawdown),
        "sharpe": annual_return / volatility if volatility > 0 else None,
        "sortino": annual_return / downside_vol if downside_vol > 0 else None,
        "calmar": cagr / abs(max_drawdown) if max_drawdown < 0 else None,
        "total_pnl": final_equity - initial_capital,
        "trade_count": int(len(trades)),
        "win_rate": float((pnl > 0).mean()) if not pnl.empty else 0.0,
        "average_win": float(wins.mean()) if not wins.empty else 0.0,
        "average_loss": float(losses.mean()) if not losses.empty else 0.0,
        "profit_factor": profit_factor,
        "turnover": float(fill_notional / avg_equity) if avg_equity > 0 else 0.0,
        "market_exposure": exposure,
        "average_cash_weight": cash_weight,
        "buy_hold_return": benchmark_return,
        "excess_return_vs_buy_hold": total_return - benchmark_return
        if benchmark_return is not None
        else None,
        "var_95": float(np.percentile(returns, 5)) if len(returns) else None,
    }


def calculate_drawdown(equity: pd.Series) -> pd.Series:
    """equity curve에서 고점 대비 하락률 시계열을 계산한다."""

    # 누적 최고점을 기준으로 현재 equity가 얼마나 내려왔는지 본다.
    running_max = equity.cummax()
    return equity / running_max - 1.0


def max_drawdown_duration(drawdown: pd.Series) -> int:
    """드로다운이 0보다 작은 상태가 가장 오래 이어진 기간을 센다."""

    longest = 0
    current = 0
    for value in drawdown:
        if value < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return int(longest)


def _years(index: pd.Index) -> float:
    """날짜 인덱스 길이를 연 단위 기간으로 환산한다."""

    if len(index) < 2:
        return 0.0
    days = (pd.Timestamp(index[-1]) - pd.Timestamp(index[0])).days
    return max(days / 365.25, 1 / 365.25)


def _benchmark_return(market_data: pd.DataFrame, benchmark: str | None) -> float | None:
    """지정 ticker 또는 입력 종목 평균의 buy-and-hold 수익률을 계산한다."""

    if market_data.empty:
        return None
    data = market_data.sort_values(["ticker", "date"])
    if benchmark is not None and benchmark in set(data["ticker"]):
        group = data[data["ticker"] == benchmark]
        return float(group["close"].iloc[-1] / group["close"].iloc[0] - 1.0)
    returns = []
    for _, group in data.groupby("ticker", sort=False):
        if len(group) > 1:
            returns.append(float(group["close"].iloc[-1] / group["close"].iloc[0] - 1.0))
    return float(np.mean(returns)) if returns else None
