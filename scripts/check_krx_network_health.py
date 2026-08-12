from __future__ import annotations

import json
import socket
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
STATUS_PATH = ROOT / "data" / "network_health.json"
TIMEZONE = ZoneInfo("Asia/Seoul")

HOSTS = [
    "data.krx.co.kr",
    "comp.fnguide.com",
    "news.google.com",
    "fchart.stock.naver.com",
]


def _check_host(host: str) -> dict[str, object]:
    try:
        infos = socket.getaddrinfo(host, None)
        addresses = sorted({info[4][0] for info in infos if info[4]})
        return {
            "host": host,
            "ok": True,
            "addresses": addresses[:4],
            "error": "",
        }
    except Exception as exc:
        return {
            "host": host,
            "ok": False,
            "addresses": [],
            "error": str(exc),
        }


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    checked_at = datetime.now(TIMEZONE).isoformat()
    checks = [_check_host(host) for host in HOSTS]
    ok_count = sum(1 for item in checks if item["ok"])
    status = {
        "checked_at": checked_at,
        "ok_count": ok_count,
        "total_count": len(checks),
        "healthy": ok_count == len(checks),
        "checks": checks,
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"KRX network health @ {checked_at}")
    for item in checks:
        if item["ok"]:
            print(f"- OK  {item['host']} -> {', '.join(item['addresses'])}")
        else:
            print(f"- FAIL {item['host']} -> {item['error']}")

    return 0 if status["healthy"] else 1


if __name__ == "__main__":
    sys.exit(main())
