#!/usr/bin/env python3
"""GitHubのcommit数（全リポジトリ・private含む）を日ごとに数えて、Beeminderの目標へ送る。

使い方:
  python3 beeminder_commits.py            # 直近7日分を数えて送る
  python3 beeminder_commits.py --dry-run  # 数えるだけ。送らない
  python3 beeminder_commits.py --days 14  # 遡る日数を変える

仕組み:
  - 数えるのは GitHub の commit 検索（author:chris9609）。private repo も返る。
    ただし各リポジトリの「デフォルトブランチ」のcommitだけ（ブランチ作業はマージされてから数えられる）。
  - 日付の区切りは JST。commitの author date を JST に直して日ごとに集計する。
  - Beeminder には1日1点。requestid を「gh-YYYYMMDD」に固定しているので、
    同じ日を何度送っても点は増えず、値だけ最新の数に更新される（毎時回しても重複しない）。
  - 遡って毎回送り直すので、Macがスリープしていて取りこぼした日も次の実行で埋まる。

鍵:
  - GitHub: `gh auth token`（ghのログインをそのまま使う）
  - Beeminder: macOSキーチェーンの「beeminder-token」（平文ファイルは置かない）
"""
import argparse
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

GITHUB_USER = "chris9609"
BEEMINDER_USER = "chris9609"
GOAL = "commits"
GOAL_START = "2026-09-28"  # これより前の日は送らない（目標開始前のcommitで貯金を水増ししない）
JST = timezone(timedelta(hours=9))


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()


def github_token():
    return run(["/opt/homebrew/bin/gh", "auth", "token"])


def beeminder_token():
    return run(["security", "find-generic-password", "-s", "beeminder-token", "-a", BEEMINDER_USER, "-w"])


def http(method, url, headers=None, data=None):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def count_commits(first_day, last_day):
    """first_day〜last_day（JSTの日付）のcommit数を日ごとに返す。"""
    # 検索の日付指定はJSTではないので、前後1日広めに取ってから自分でJSTに直して切る
    q = f"author:{GITHUB_USER} author-date:{first_day - timedelta(days=1)}..{last_day + timedelta(days=1)}"
    headers = {"Authorization": f"Bearer {github_token()}", "Accept": "application/vnd.github+json"}
    counts = Counter()
    page = 1
    while True:
        url = "https://api.github.com/search/commits?" + urllib.parse.urlencode(
            {"q": q, "per_page": 100, "page": page})
        res = http("GET", url, headers)
        for item in res["items"]:
            day = datetime.fromisoformat(item["commit"]["author"]["date"]).astimezone(JST).date()
            if first_day <= day <= last_day:
                counts[day] += 1
        if len(res["items"]) < 100 or page * 100 >= res["total_count"]:
            break
        page += 1
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()

    today = datetime.now(JST).date()
    start = max(today - timedelta(days=args.days - 1), datetime.fromisoformat(GOAL_START).date())
    counts = count_commits(start, today)

    points = []
    day = start
    while day <= today:
        points.append({
            "daystamp": day.strftime("%Y%m%d"),
            "value": counts[day],
            "comment": "auto: GitHub commits",
            "requestid": f"gh-{day:%Y%m%d}",
        })
        day += timedelta(days=1)

    stamp = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    print(f"[{stamp}] " + "  ".join(f"{p['daystamp'][4:]}={p['value']}" for p in points))
    if args.dry_run:
        print("  (dry-run: 送信していない)")
        return

    url = f"https://www.beeminder.com/api/v1/users/{BEEMINDER_USER}/goals/{GOAL}/datapoints/create_all.json"
    res = http("POST", url, data={"auth_token": beeminder_token(), "datapoints": json.dumps(points)})
    print(f"  送信: {len(res) if isinstance(res, list) else res}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"鍵の取得に失敗: {' '.join(e.cmd[:3])} … {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
