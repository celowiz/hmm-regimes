"""Cron reserva: decide se o build pode ser pulado porque o site publicado já tem o último pregão.

Uso: python scripts/backup_gate.py <url do data/summary.json publicado>
Escreve skip=true|false em $GITHUB_OUTPUT. Na dúvida (sem resumo, data ilegível), roda o build.

Por que olhar a data dos dados (as_of) e não o horário de geração (generated_at)?
O cron principal pode rodar no horário e mesmo assim publicar o pregão anterior (o Yahoo ainda
não tinha o fechamento do dia, por exemplo). Pelo horário de geração o site parecia "atualizado"
e o reserva pulava; pela data dos dados o reserva percebe que falta o pregão de hoje e refaz.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

BRT = dt.timezone(dt.timedelta(hours=-3))
CLOSE_HOUR_BRT = 19  # depois das 19h BRT o fechamento do dia (B3 e NY) já deveria estar disponível


def expected_trading_day(now):
    """Último pregão que o site já deveria mostrar (dias úteis; feriados não entram na conta)."""
    n = now.astimezone(BRT)
    d = n.date() if n.hour >= CLOSE_HOUR_BRT else n.date() - dt.timedelta(days=1)
    while d.weekday() >= 5:  # sábado/domingo → sexta
        d -= dt.timedelta(days=1)
    return d


def has_latest(as_of, now):
    """True se a data dos dados publicados já cobre o último pregão esperado."""
    if not as_of:
        return False
    try:
        return dt.date.fromisoformat(str(as_of)[:10]) >= expected_trading_day(now)
    except (TypeError, ValueError):
        return False


def main(url):
    as_of = None
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            as_of = json.load(r).get("as_of")
    except Exception as e:
        print(f"resumo publicado indisponível ({type(e).__name__}); segue com o build")
    now = dt.datetime.now(dt.timezone.utc)
    skip = has_latest(as_of, now)
    exp = expected_trading_day(now)
    print(f"as_of={as_of}, pregão esperado={exp} → {'pula: já tem o último pregão' if skip else 'roda o build'}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"skip={'true' if skip else 'false'}\n")


if __name__ == "__main__":
    main(sys.argv[1])
