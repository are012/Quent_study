from __future__ import annotations

import pandas as pd

from quent.signals.ma_crossover import MovingAverageCrossoverSignalGenerator


def test_executable_signal_is_delayed_one_row_per_ticker() -> None:
    # 상승 가격열에서 raw signal이 true가 된 다음 날에만 executable signal이 true가 된다.
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=6),
            "ticker": ["AAA"] * 6,
            "signal_price": [1, 2, 3, 4, 5, 6],
            "open": [1, 2, 3, 4, 5, 6],
            "close": [1, 2, 3, 4, 5, 6],
        }
    )

    result = MovingAverageCrossoverSignalGenerator(2, 3).generate(frame)

    assert result["raw_signal"].tolist() == [False, False, True, True, True, True]
    assert result["executable_signal"].tolist() == [False, False, False, True, True, True]
