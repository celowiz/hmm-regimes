"""Cron reserva: decide se o build pode ser pulado porque o site já foi gerado depois do cron principal de hoje.

Uso: python scripts/backup_gate.py <url do data/summary.json publicado>
Escreve skip=true|false em $GITHUB_OUTPUT. Na dúvida (sem resumo, data ilegível), roda o build.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

BRT = dt.timezone(dt.timedelta(hours=-3))
MAIN_HOUR_BRT = 19  # cron principal: dias úteis por volta das 19h BRT, depois do fechamento


def parse(ts):
    """ISO 8601; sem fuso = UTC (horário do runner do GitHub)."""
    t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def threshold(now):
    """Horário do cron principal mais recente (19h BRT de hoje, ou de ontem se ainda não deu 19h)."""
    n = now.astimezone(BRT)
    day = n.date() if n.hour >= MAIN_HOUR_BRT else n.date() - dt.timedelta(days=1)
    return dt.datetime.combine(day, dt.time(MAIN_HOUR_BRT), BRT)


def already_built(generated_at, now):
    if not generated_at:
        return False
    try:
        return parse(generated_at) >= threshold(now)
    except (TypeError, ValueError):
        return False


def main(url):
    gen = None
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            gen = json.load(r).get("generated_at")
    except Exception as e:
        print(f"resumo publicado indisponível ({type(e).__name__}); segue com o build")
    skip = already_built(gen, dt.datetime.now(dt.timezone.utc))
    print(f"generated_at={gen} → {'pula: já atualizado depois do cron principal' if skip else 'roda o build'}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"skip={'true' if skip else 'false'}\n")


if __name__ == "__main__":
    main(sys.argv[1])
