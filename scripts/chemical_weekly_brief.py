#!/usr/bin/env python3
import csv
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / ".automation" / "chemical-monitor-state.json"
STATUS_PATH = REPO_ROOT / ".automation" / "chemical-monitor-status.md"
POSTS_DIR = REPO_ROOT / "_posts"

if ZoneInfo:
    try:
        TZ = ZoneInfo("Asia/Seoul")
    except Exception:  # pragma: no cover
        TZ = dt.timezone(dt.timedelta(hours=9), name="KST")
else:  # pragma: no cover
    TZ = dt.timezone(dt.timedelta(hours=9), name="KST")


def env(name, default=""):
    return os.environ.get(name, default)


def request_text(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ChemicalMonitorBot/1.0)"
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "ignore")


def load_state():
    if not STATE_PATH.exists():
        return {
            "last_seen_post_id": 0,
            "alert_issue_opened": False,
            "suspended": False,
            "suspended_reason": "",
            "suspended_on": "",
            "review_after": "",
        }
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def strip_html(raw):
    text = re.sub(r"<br\s*/?>", "\n", raw)
    text = re.sub(r"</p\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_posts(page_html, channel):
    posts = []
    marker = f'data-post="{channel}/'
    starts = [m.start() for m in re.finditer(re.escape(marker), page_html)]
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(page_html)
        chunk = page_html[start:end]

        post_match = re.search(rf'data-post="{re.escape(channel)}/(\d+)"', chunk)
        time_match = re.search(r'<time datetime="([^"]+)"', chunk)
        text_match = re.search(
            r'<div class="tgme_widget_message_text js-message_text" dir="auto">(.*)</div>\s*</div>\s*<div class="tgme_widget_message_footer',
            chunk,
            re.S,
        )
        if not post_match or not time_match:
            continue

        post_id = post_match.group(1)
        iso_dt = time_match.group(1)
        raw_text = text_match.group(1) if text_match else ""
        text = strip_html(raw_text or "")
        posts.append(
            {
                "id": int(post_id),
                "dt": dt.datetime.fromisoformat(iso_dt),
                "text": text,
                "url": f"https://t.me/{channel}/{post_id}",
            }
        )
    return posts


def fetch_posts(channel, start_dt, max_pages=10):
    seen = {}
    before = None
    for _ in range(max_pages):
        url = f"https://t.me/s/{channel}"
        if before:
            url += f"?before={before}"
        html_page = request_text(url)
        posts = parse_posts(html_page, channel)
        if not posts:
            break
        for post in posts:
            seen[post["id"]] = post
        oldest = min(post["id"] for post in posts)
        oldest_dt = min(post["dt"] for post in posts)
        if oldest_dt.astimezone(TZ) < start_dt:
            break
        before = oldest
    return sorted(seen.values(), key=lambda item: item["id"])


def read_csv_rows(csv_url):
    content = request_text(csv_url)
    reader = csv.DictReader(content.splitlines())
    return list(reader)


def normalize(s):
    return re.sub(r"\s+", "", (s or "")).lower()


def parse_holdings(rows):
    name_col = env("HOLDINGS_NAME_COLUMN", "name")
    ticker_col = env("HOLDINGS_TICKER_COLUMN", "ticker")
    sector_col = env("HOLDINGS_SECTOR_COLUMN", "sector")
    manual_names = [x.strip() for x in env("CHEMICAL_HOLDINGS", "").split(",") if x.strip()]
    chemical_keywords = [
        x.strip().lower()
        for x in env(
            "CHEMICAL_FILTER_KEYWORDS",
            "화학,석유화학,정유,에너지,태양광,소재,배터리소재,이차전지소재",
        ).split(",")
        if x.strip()
    ]

    holdings = []
    for row in rows:
        name = (row.get(name_col) or "").strip()
        ticker = (row.get(ticker_col) or "").strip()
        sector = (row.get(sector_col) or "").strip()
        if not name and not ticker:
            continue

        is_chemical = False
        if manual_names:
            is_chemical = name in manual_names or ticker in manual_names
        else:
            sector_norm = sector.lower()
            is_chemical = any(keyword in sector_norm for keyword in chemical_keywords)

        if is_chemical:
            holdings.append(
                {
                    "name": name,
                    "ticker": ticker,
                    "sector": sector,
                }
            )
    return holdings


def find_relevant_posts(posts, holdings):
    matches = []
    for post in posts:
        matched = []
        text_norm = normalize(post["text"])
        for holding in holdings:
            probes = [holding["name"], holding["ticker"]]
            probes = [p for p in probes if p]
            if any(normalize(probe) in text_norm for probe in probes):
                matched.append(holding["name"] or holding["ticker"])
        if matched:
            post = dict(post)
            post["matched_holdings"] = sorted(set(matched))
            matches.append(post)
    return matches


def date_slug(value):
    return value.strftime("%Y-%m-%d")


def summarize_text(text, limit=420):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def make_week_window(now_local):
    today = now_local.date()
    current_week_monday = today - dt.timedelta(days=today.weekday())
    start = dt.datetime.combine(
        current_week_monday - dt.timedelta(days=7), dt.time.min, tzinfo=TZ
    )
    end = dt.datetime.combine(
        current_week_monday, dt.time.min, tzinfo=TZ
    )
    return start, end


def make_watch_window(now_local, hours=12):
    end = now_local
    start = now_local - dt.timedelta(hours=hours)
    return start, end


def ensure_posts_dir():
    POSTS_DIR.mkdir(parents=True, exist_ok=True)


def post_exists(filename):
    return (POSTS_DIR / filename).exists()


def write_post(filename, content):
    ensure_posts_dir()
    path = POSTS_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path


def make_front_matter(title, categories, tags):
    body = [
        "---",
        f'title: "{title}"',
        'excerpt_separator: "<!--more-->"',
        "categories:",
    ]
    for category in categories:
        body.append(f"  - {category}")
    body.append("tags:")
    for tag in tags:
        body.append(f"  - {tag}")
    body.append("---")
    return "\n".join(body)


def build_weekly_post(start_local, end_local, all_posts, matched_posts, holdings):
    title = f"윤재성 에너지/화학 주간 정리 ({date_slug(start_local.date())} ~ {date_slug((end_local - dt.timedelta(days=1)).date())})"
    lines = [
        make_front_matter(
            title,
            ["investing", "chemicals"],
            ["telegram", "energy_youn", "chemical-stocks", "weekly-digest"],
        ),
        "",
        f"지난주 채널 글을 기준으로, 내 보유 화학주와 연결될 수 있는 포인트를 정리했다.",
        "",
        "<!--more-->",
        "",
        "## 기준 기간",
        "",
        f"- Asia/Seoul 기준 {date_slug(start_local.date())} 00:00 ~ {date_slug((end_local - dt.timedelta(days=1)).date())} 23:59",
        f"- 채널: https://t.me/s/{env('TELEGRAM_CHANNEL', 'energy_youn')}",
        "",
        "## 현재 감시 중인 화학주",
        "",
    ]
    if holdings:
        for holding in holdings:
            label = holding["name"]
            if holding["ticker"]:
                label += f" ({holding['ticker']})"
            if holding["sector"]:
                label += f" - {holding['sector']}"
            lines.append(f"- {label}")
    else:
        lines.append("- 없음")

    lines.extend(["", "## 이번 주 채널 핵심", ""])
    if all_posts:
        for post in all_posts[:10]:
            local_dt = post["dt"].astimezone(TZ).strftime("%Y-%m-%d %H:%M")
            lines.append(f"### {local_dt}")
            lines.append("")
            lines.append(f"- 링크: {post['url']}")
            lines.append(f"- 요약: {summarize_text(post['text'])}")
            lines.append("")
    else:
        lines.append("- 이번 주 수집된 채널 글이 없었다.")
        lines.append("")

    lines.extend(["## 보유 종목 직접 언급", ""])
    if matched_posts:
        for post in matched_posts:
            local_dt = post["dt"].astimezone(TZ).strftime("%Y-%m-%d %H:%M")
            matches = ", ".join(post["matched_holdings"])
            lines.append(f"### {local_dt} / {matches}")
            lines.append("")
            lines.append(f"- 링크: {post['url']}")
            lines.append(f"- 언급 종목: {matches}")
            lines.append(f"- 내용 정리: {summarize_text(post['text'], limit=520)}")
            lines.append("")
    else:
        lines.append("- 보유 종목명이 직접 언급된 글은 찾지 못했다.")
        lines.append("")

    lines.extend(
        [
            "## 체크 포인트",
            "",
            "- 직접 언급이 없더라도 유가, 정제마진, 태양광, 원재료 가격, 중국 수급, 미국 정책 변화는 화학주 전반에 영향을 줄 수 있다.",
            "- 실제 투자 판단 전에는 최신 공시, 실적 일정, 가격 흐름을 별도로 확인하는 것이 안전하다.",
            "",
        ]
    )
    return title, "\n".join(lines).rstrip() + "\n"


def build_watch_post(post):
    match_label = ", ".join(post["matched_holdings"])
    local_date = post["dt"].astimezone(TZ).strftime("%Y-%m-%d")
    title = f"에너지/화학 채널 모니터링: {match_label} 언급 ({local_date})"
    lines = [
        make_front_matter(
            title,
            ["investing", "chemicals"],
            ["telegram", "energy_youn", "chemical-stocks", "alert"],
        ),
        "",
        f"보유 화학주와 연결된 채널 글이 올라와 짧게 정리한다.",
        "",
        "<!--more-->",
        "",
        "## 매칭 종목",
        "",
        f"- {match_label}",
        "",
        "## 채널 글",
        "",
        f"- 시각: {post['dt'].astimezone(TZ).strftime('%Y-%m-%d %H:%M')} Asia/Seoul",
        f"- 링크: {post['url']}",
        f"- 요약: {summarize_text(post['text'], limit=700)}",
        "",
    ]
    return title, "\n".join(lines).rstrip() + "\n"


def write_status_note(holdings_count, review_after):
    content = "\n".join(
        [
            "# Chemical Monitor Status",
            "",
            f"- Updated: {dt.datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}",
            f"- Chemical holdings detected: {holdings_count}",
            "- Status: suspended",
            f"- Review after: {review_after}",
            "",
            "Chemical holdings were not found in the configured sheet.",
            "Automation is suspended until the portfolio is reviewed.",
            "",
        ]
    )
    STATUS_PATH.write_text(content, encoding="utf-8")


def github_api_request(method, path, payload):
    token = env("GITHUB_TOKEN")
    repo = env("GITHUB_REPOSITORY")
    if not token or not repo:
        return None
    url = f"https://api.github.com/repos/{repo}/{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "chemical-monitor-bot",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "ignore")


def open_review_issue(review_after):
    payload = {
        "title": "화학주 보유 없음: 자동화 중지 검토 필요",
        "body": "\n".join(
            [
                "자동 모니터링 시트에서 화학주 보유를 찾지 못했습니다.",
                "",
                f"- 검토 가능 시점: {review_after}",
                "- 조치: 일주일 후 삭제할지, 유지할지 확인 필요",
            ]
        ),
    }
    try:
        github_api_request("POST", "issues", payload)
        return True
    except Exception:
        return False


def handle_no_holdings(state):
    review_after = (dt.datetime.now(TZ) + dt.timedelta(days=7)).strftime("%Y-%m-%d")
    state["suspended"] = True
    state["suspended_reason"] = "No chemical holdings found in configured sheet"
    state["suspended_on"] = dt.datetime.now(TZ).strftime("%Y-%m-%d")
    state["review_after"] = review_after
    write_status_note(0, review_after)
    if not state.get("alert_issue_opened"):
        if open_review_issue(review_after):
            state["alert_issue_opened"] = True
    save_state(state)


def run_weekly(state, holdings, channel):
    now_local = dt.datetime.now(TZ)
    start_local, end_local = make_week_window(now_local)
    posts = fetch_posts(channel, start_local)
    weekly_posts = [
        p for p in posts if start_local <= p["dt"].astimezone(TZ) < end_local
    ]
    matched_posts = find_relevant_posts(weekly_posts, holdings)
    title, content = build_weekly_post(start_local, end_local, weekly_posts, matched_posts, holdings)
    filename = f"{date_slug(now_local.date())}-chemical-weekly-digest.md"
    if post_exists(filename):
        return 0
    write_post(filename, content)
    return 1


def run_watch(state, holdings, channel):
    now_local = dt.datetime.now(TZ)
    start_local, _ = make_watch_window(now_local, hours=int(env("WATCH_LOOKBACK_HOURS", "12")))
    posts = fetch_posts(channel, start_local)
    new_posts = [p for p in posts if p["id"] > int(state.get("last_seen_post_id", 0))]
    matched = find_relevant_posts(new_posts, holdings)
    created = 0
    for post in matched:
        local_day = post["dt"].astimezone(TZ).date()
        filename = f"{date_slug(local_day)}-chemical-monitor-{post['id']}.md"
        if post_exists(filename):
            continue
        _, content = build_watch_post(post)
        write_post(filename, content)
        created += 1
    if new_posts:
        state["last_seen_post_id"] = max(p["id"] for p in new_posts)
        save_state(state)
    return created


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else env("CHEMICAL_MONITOR_MODE", "watch")
    csv_url = env("GOOGLE_SHEETS_CSV_URL")
    channel = env("TELEGRAM_CHANNEL", "energy_youn")
    if not csv_url:
        print("Missing GOOGLE_SHEETS_CSV_URL", file=sys.stderr)
        return 2

    state = load_state()
    if state.get("suspended"):
        print(f"suspended: {state.get('suspended_reason', '')}")
        return 0

    rows = read_csv_rows(csv_url)
    holdings = parse_holdings(rows)

    if not holdings:
        handle_no_holdings(state)
        print("No chemical holdings found; monitor suspended.")
        return 0

    if mode == "weekly":
        created = run_weekly(state, holdings, channel)
    elif mode == "watch":
        created = run_watch(state, holdings, channel)
    else:
        print(f"Unsupported mode: {mode}", file=sys.stderr)
        return 2

    print(f"mode={mode} created={created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
