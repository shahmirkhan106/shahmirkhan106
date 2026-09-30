#!/usr/bin/env python3
"""Fetch the public contribution calendar for a GitHub user and cache it as JSON.

No token, no GraphQL: GitHub serves the same calendar fragment the profile page
renders, at /users/<username>/contributions. Day cells carry data-date and
data-level (0-4); the exact per-day count lives in the matching <tool-tip>.

Only `requests` is needed here, so the daily cron stays light. The portrait
scripts need the heavier image stack and are never run by the workflow.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from collections import OrderedDict
from datetime import datetime, timezone

USERNAME = os.environ.get("GITHUB_USERNAME", "shahmirkhan106")
OUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "contributions.json",
)

CELL_RE = re.compile(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*?data-level="(\d)"')
TIP_RE = re.compile(r'<tool-tip[^>]*data-type="label"[^>]*>([^<]+)</tool-tip>')
COUNT_RE = re.compile(r"(\d+)\s+contribution")
USER_AGENT = "Mozilla/5.0 (compatible; profile-readme-bot/1.0)"


def fetch(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"GitHub returned HTTP {response.status} for {url}")
        return response.read().decode("utf-8", errors="replace")


def parse(html: str) -> list[dict]:
    cells = CELL_RE.findall(html)
    tips = TIP_RE.findall(html)

    if len(tips) != len(cells):
        raise RuntimeError(
            f"day/tooltip mismatch: {len(cells)} cells vs {len(tips)} tool-tips. "
            "GitHub markup likely changed; update the selectors in this script."
        )

    days = []
    for (day, level), tip in zip(cells, tips):
        match = COUNT_RE.search(tip)
        days.append(
            {
                "date": day,
                "level": int(level),
                "count": int(match.group(1)) if match else 0,
            }
        )

    days.sort(key=lambda d: d["date"])
    return days


def streaks(counts: list[int]) -> tuple[int, int]:
    longest = running = 0
    for count in counts:
        running = running + 1 if count > 0 else 0
        longest = max(longest, running)

    current = 0
    for count in reversed(counts):
        if count == 0:
            break
        current += 1
    return longest, current


def monthly(days: list[dict]) -> OrderedDict[str, int]:
    totals: OrderedDict[str, int] = OrderedDict()
    for day in days:
        totals[day["date"][:7]] = totals.get(day["date"][:7], 0) + day["count"]
    return totals


def summarize(days: list[dict]) -> dict:
    counts = [d["count"] for d in days]
    longest, current = streaks(counts)
    best_index = counts.index(max(counts)) if counts else 0
    busiest = max(counts) if counts else 0

    return {
        "total": sum(counts),
        "active_days": sum(1 for c in counts if c > 0),
        "longest_streak": longest,
        "current_streak": current,
        "busiest_day": busiest,
        "busiest_date": days[best_index]["date"] if days else None,
        "range": {"from": days[0]["date"], "to": days[-1]["date"]} if days else {},
        "monthly": dict(monthly(days)),
    }


def main() -> int:
    try:
        days = parse(fetch(USERNAME))
    except Exception as error:  # noqa: BLE001 - surface a clean CI failure
        print(f"error: failed to collect contributions: {error}", file=sys.stderr)
        return 1

    if not days:
        print("error: parsed zero contribution days", file=sys.stderr)
        return 1

    stats = summarize(days)
    payload = {
        "username": USERNAME,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "days": days,
        "stats": stats,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")

    print(
        f"{stats['total']} contributions / {stats['active_days']} active days "
        f"across {len(days)} days ({stats['range']['from']} -> {stats['range']['to']})"
    )
    print(f"wrote {os.path.relpath(OUT_PATH, os.getcwd())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
