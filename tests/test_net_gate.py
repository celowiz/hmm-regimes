import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from backup_gate import expected_trading_day, has_latest  # noqa: E402
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


def test_pregao_esperado():
    # 21:07 BRT de quinta 22/10 (00:07Z de sexta) → quinta
    assert expected_trading_day(dt.datetime(2026, 10, 23, 0, 7, tzinfo=UTC)) == dt.date(2026, 10, 22)
    # 10:00 BRT de sexta → ainda não fechou: quinta
    assert expected_trading_day(dt.datetime(2026, 10, 23, 13, 0, tzinfo=UTC)) == dt.date(2026, 10, 22)
    # 01:23 BRT de sábado 24/10 (04:23Z) → sexta 23/10
    assert expected_trading_day(dt.datetime(2026, 10, 24, 4, 23, tzinfo=UTC)) == dt.date(2026, 10, 23)
    # 08:07 BRT de segunda → sexta
    assert expected_trading_day(dt.datetime(2026, 10, 26, 11, 7, tzinfo=UTC)) == dt.date(2026, 10, 23)


def test_has_latest_olha_a_data_dos_dados():
    # gerado depois das 19h, mas com o pregão anterior → NÃO pula (o gate antigo, por generated_at, pularia)
    sab = dt.datetime(2026, 10, 24, 4, 23, tzinfo=UTC)
    assert not has_latest("2026-10-22", sab)
    assert has_latest("2026-10-23", sab)
    assert has_latest("2026-10-23T00:00:00", sab)
    assert not has_latest(None, sab)
    assert not has_latest("lixo", sab)
