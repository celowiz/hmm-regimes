import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from backup_gate import already_built, threshold  # noqa: E402
from net import backoff, retry  # noqa: E402

UTC = dt.timezone.utc


def test_backoff_deterministico():
    assert backoff(4, 3, 3) == [3, 9, 27]
    assert backoff(1, 3, 3) == []


def test_retry_recupera_e_espera_em_ordem():
    calls, waits = [], []

    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("x")
        return "ok"

    assert retry(fn, attempts=4, base=2, factor=2, sleep=waits.append, log=lambda m: None) == "ok"
    assert len(calls) == 3 and waits == [2, 4]


def test_retry_repassa_a_ultima_falha():
    waits = []

    def fn():
        raise TimeoutError("fora")

    with pytest.raises(TimeoutError):
        retry(fn, attempts=3, base=1, factor=3, sleep=waits.append, log=lambda m: None)
    assert waits == [1, 3]


def test_threshold_19h_brt():
    # 21:07 BRT de terça (00:07Z de quarta) → limiar 19:00 BRT de terça
    now = dt.datetime(2026, 10, 21, 0, 7, tzinfo=UTC)
    assert threshold(now) == dt.datetime(2026, 10, 20, 22, 0, tzinfo=UTC)
    # 10:00 BRT → limiar 19:00 BRT do dia anterior
    assert threshold(dt.datetime(2026, 10, 21, 13, 0, tzinfo=UTC)) == dt.datetime(2026, 10, 20, 22, 0, tzinfo=UTC)


def test_already_built():
    now = dt.datetime(2026, 10, 21, 0, 7, tzinfo=UTC)
    assert already_built("2026-10-20T22:40:00Z", now)          # principal rodou (atrasado) → pula
    assert already_built("2026-10-20T22:40", now)              # sem fuso = UTC
    assert already_built("2026-10-20T19:40:00-03:00", now)
    assert not already_built("2026-10-20T21:59:59Z", now)      # antes do cron principal
    assert not already_built("2026-10-19T23:00:00Z", now)      # ontem → roda
    assert not already_built(None, now)
    assert not already_built("lixo", now)
