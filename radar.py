import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sqlite3
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
SITE_DATA_DIR = ROOT / "site_data"
DOCS_DIR = ROOT / "docs"
DB_PATH = DATA_DIR / "radar.sqlite3"
NEWS_JSON = DOCS_DIR / "data" / "news.json"
HISTORY_JSON = DOCS_DIR / "data" / "history.json"
DAILY_DOCS_DIR = DOCS_DIR / "data" / "daily"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def make_id(url, title):
    raw = (url or title).strip().lower().encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def fetch_url(url, timeout=20):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SemiCSPRadar/0.2 (+local research dashboard)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def child_text(item, names):
    lowered_names = {name.lower() for name in names}
    for name in names:
        node = item.find(name)
        if node is not None and node.text:
            return node.text
    for node in item:
        bare = node.tag.split("}")[-1].lower()
        if bare in lowered_names and node.text:
            return node.text
    return ""


def parse_feed(source, raw):
    root = ET.fromstring(raw)
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    parsed = []
    for item in items[:40]:
        title = normalize_text(child_text(item, ["title"]))
        link = normalize_text(child_text(item, ["link"]))
        if not link:
            link_node = item.find("{http://www.w3.org/2005/Atom}link")
            if link_node is not None:
                link = link_node.attrib.get("href", "")
        published = normalize_text(
            child_text(item, ["pubDate", "published", "updated", "date"])
        )
        description = normalize_text(
            child_text(item, ["description", "summary", "content"])
        )
        if not title:
            continue
        parsed.append(
            {
                "id": make_id(link, title),
                "title": title,
                "title_zh": "",
                "source": source["name"],
                "url": link,
                "published": published,
                "region": source["region"],
                "segments": [],
                "companies": [],
                "importance": 1,
                "summary_zh": description[:260],
                "investment_takeaway": "",
                "raw_text": f"{title} {description}",
            }
        )
    return parsed


def parse_news_feed(source, raw, limit=8):
    root = ET.fromstring(raw)
    items = root.findall(".//item")
    parsed = []
    for item in items[:limit]:
        title = normalize_text(child_text(item, ["title"]))
        link = normalize_text(child_text(item, ["link"]))
        published = normalize_text(child_text(item, ["pubDate", "published", "updated", "date"]))
        description = normalize_text(child_text(item, ["description", "summary", "content"]))
        if title:
            parsed.append(
                {
                    "title": title,
                    "source": source["name"],
                    "url": link,
                    "published": published,
                    "summary": description[:160],
                }
            )
    return parsed


def fetch_yahoo_quote(entry):
    symbol = entry["symbol"]
    raw = fetch_url(YAHOO_CHART_URL.format(symbol=symbol))
    payload = json.loads(raw.decode("utf-8"))
    result = payload["chart"]["result"][0]
    meta = result["meta"]
    price = meta.get("regularMarketPrice")
    previous = meta.get("chartPreviousClose") or meta.get("previousClose")
    change = None
    change_percent = None
    if price is not None and previous:
        change = price - previous
        change_percent = change / previous * 100
    return {
        "symbol": symbol,
        "name": entry["name"],
        "group": entry["group"],
        "price": price,
        "previous_close": previous,
        "change": change,
        "change_percent": change_percent,
        "currency": meta.get("currency", "TWD"),
        "market_state": meta.get("marketState", ""),
        "updated_at": meta.get("regularMarketTime"),
        "plain_read": build_quote_plain_read(entry["name"], change_percent),
    }


def build_quote_plain_read(name, change_percent):
    if change_percent is None:
        return f"{name}暫無可比對的最新漲跌資料。"
    if change_percent > 1.5:
        return f"{name}明顯上漲，代表市場今天對相關題材或資金面較樂觀。"
    if change_percent > 0.2:
        return f"{name}小幅上漲，屬於偏強但仍需觀察量能的走勢。"
    if change_percent < -1.5:
        return f"{name}明顯下跌，短線風險意識升高，需留意是否為大盤或族群同步修正。"
    if change_percent < -0.2:
        return f"{name}小幅下跌，代表短線買盤較保守。"
    return f"{name}變動不大，市場暫時沒有明確方向。"


def fetch_market_snapshot():
    market_config = load_json(CONFIG_DIR / "markets.json")
    errors = []

    def collect(entries):
        collected = []
        for entry in entries:
            try:
                collected.append(fetch_yahoo_quote(entry))
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as exc:
                errors.append({"symbol": entry["symbol"], "error": str(exc)})
        return collected

    news = []
    for source in market_config.get("news_feeds", []):
        try:
            news.extend(parse_news_feed(source, fetch_url(source["url"]), limit=6))
        except (urllib.error.URLError, TimeoutError, ET.ParseError) as exc:
            errors.append({"source": source["name"], "error": str(exc)})

    stocks = collect(market_config.get("stocks", []))
    gainers = sum(1 for stock in stocks if (stock.get("change_percent") or 0) > 0)
    losers = sum(1 for stock in stocks if (stock.get("change_percent") or 0) < 0)

    return {
        "indices": collect(market_config.get("indices", [])),
        "stocks": stocks,
        "news": news[:12],
        "summary": {
            "tracked": len(stocks),
            "gainers": gainers,
            "losers": losers,
            "plain_read": build_market_plain_read(gainers, losers, len(stocks)),
        },
        "errors": errors,
    }


def build_market_plain_read(gainers, losers, total):
    if total == 0:
        return "目前沒有可用的股市報價資料。"
    if gainers > losers * 1.5:
        return "追蹤的半導體供應鏈多數上漲，市場對族群短線風險偏好較高。"
    if losers > gainers * 1.5:
        return "追蹤的半導體供應鏈多數下跌，今天比較像是風險降溫或籌碼修正。"
    return "追蹤股漲跌互見，市場尚未形成一致方向，適合搭配新聞與大盤一起判讀。"


def classify_item(item, taxonomy):
    raw_text = item.get("raw_text") or " ".join(
        [
            item.get("title", ""),
            item.get("title_zh", ""),
            item.get("summary_zh", ""),
            item.get("investment_takeaway", ""),
        ]
    )
    text = raw_text.lower()
    segments = []
    score = 1

    for segment in taxonomy["segments"].values():
        hits = [keyword for keyword in segment["keywords"] if keyword.lower() in text]
        if hits:
            segments.append(segment["label"])
            score += min(len(hits), 2)

    companies = []
    for names in taxonomy["companies"].values():
        for company in names:
            if company.lower() in text and company not in companies:
                companies.append(company)

    if any(term in text for term in ["capex", "capacity", "guidance", "earnings"]):
        score += 1
    if any(term in text for term in ["hbm", "cowos", "export control", "2nm", "3nm"]):
        score += 1
    if item["region"] == "taiwan" and any(
        term in text for term in ["tsmc", "cowos", "ai server", "server"]
    ):
        score += 1

    item["segments"] = segments or item.get("segments") or ["未分類 / 待人工確認"]
    item["companies"] = companies or item.get("companies") or []
    item["importance"] = max(1, min(score, 5))
    item["title_zh"] = item.get("title_zh") or build_zh_title(item)
    item["summary_zh"] = item.get("summary_zh") or build_brief_summary(item)
    item["investment_takeaway"] = item.get("investment_takeaway") or build_takeaway(item)
    item.pop("raw_text", None)
    return item


def build_zh_title(item):
    title = item.get("title", "")
    if re.search(r"[\u4e00-\u9fff]", title):
        return title
    companies = item.get("companies") or []
    segments = item.get("segments") or []
    subject = "、".join(companies[:2]) if companies else ("、".join(segments[:2]) if segments else "半導體供應鏈")
    focus = segments[0] if segments else "產業鏈"
    region = "國際" if item.get("region") == "international" else "台灣"
    return f"{region}觀察：{subject}的{focus}相關動態"


def build_brief_summary(item):
    segment_text = "、".join(item["segments"][:2])
    region = "國際" if item["region"] == "international" else "台灣"
    return (
        f"這則{region}消息與「{segment_text}」相關。"
        "建議先確認原文中的訂單、產能、價格或資本支出訊號，再判斷是否屬於結構性變化。"
    )


def build_takeaway(item):
    segments = set(item["segments"])
    if "CSP / 雲端需求" in segments:
        return "投資觀察重點在 CSP CapEx、AI 叢集擴建，以及 GPU/ASIC 需求是否轉成供應鏈訂單。"
    if "先進封裝 / 測試" in segments:
        return "投資觀察重點在 CoWoS/先進封裝產能、載板與測試稼動率，這通常是 AI 加速器供給瓶頸。"
    if "記憶體 / HBM" in segments:
        return "投資觀察重點在 HBM 價格、良率、客戶認證與供應合約年限。"
    if "政策 / 地緣政治" in segments:
        return "投資觀察重點在出口管制、補貼與區域產能配置，可能影響長期供應鏈重組。"
    if item["region"] == "taiwan":
        return "投資觀察重點在台灣供應鏈是否取得 AI 伺服器、封裝、測試或零組件增量訂單。"
    return "投資觀察重點在此消息是否影響需求能見度、產能瓶頸、價格或供應鏈議價能力。"


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                first_seen TEXT NOT NULL
            )
            """
        )


def save_items(items):
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        for item in items:
            conn.execute(
                """
                INSERT OR REPLACE INTO items (id, payload, first_seen)
                VALUES (
                    ?,
                    ?,
                    COALESCE((SELECT first_seen FROM items WHERE id = ?), ?)
                )
                """,
                (item["id"], json.dumps(item, ensure_ascii=False), item["id"], now),
            )


def load_recent(limit=120):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT payload FROM items ORDER BY first_seen DESC LIMIT ?", (limit,)
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def summarize_items(items):
    return {
        "total": len(items),
        "international": sum(1 for item in items if item.get("region") == "international"),
        "taiwan": sum(1 for item in items if item.get("region") == "taiwan"),
        "high_importance": sum(1 for item in items if int(item.get("importance", 0)) >= 4),
    }


def read_history():
    if HISTORY_JSON.exists():
        return load_json(HISTORY_JSON)
    return {"days": []}


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def archive_daily_payload(payload, run_date):
    date_dir = SITE_DATA_DIR / "daily" / run_date
    write_json(date_dir / "news.json", payload)
    write_json(DAILY_DOCS_DIR / run_date / "news.json", payload)

    history = read_history()
    day_entry = {
        "date": run_date,
        "generated_at": payload["generated_at"],
        "summary": summarize_items(payload["items"]),
        "path": f"data/daily/{run_date}/news.json",
    }
    history["days"] = [day for day in history.get("days", []) if day.get("date") != run_date]
    history["days"].append(day_entry)
    history["days"].sort(key=lambda day: day["date"], reverse=True)

    write_json(HISTORY_JSON, history)
    write_json(SITE_DATA_DIR / "history.json", history)
    return date_dir


def write_dashboard_data(items, market):
    generated_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    run_date = generated_at[:10]
    payload = {
        "generated_at": generated_at,
        "date": run_date,
        "market": market,
        "items": items,
    }
    write_json(NEWS_JSON, payload)
    return archive_daily_payload(payload, run_date)


def run_fetch(use_sample=False):
    sources = load_json(CONFIG_DIR / "sources.json")
    taxonomy = load_json(CONFIG_DIR / "taxonomy.json")
    init_db()

    fetched = []
    errors = []
    if use_sample:
        fetched = load_json(DATA_DIR / "sample_items.json")
    else:
        for group in ("international", "taiwan"):
            for source in sources[group]:
                try:
                    raw = fetch_url(source["url"])
                    fetched.extend(parse_feed(source, raw))
                except (urllib.error.URLError, TimeoutError, ET.ParseError) as exc:
                    errors.append({"source": source["name"], "error": str(exc)})

    classified = [classify_item(dict(item), taxonomy) for item in fetched]
    classified.sort(key=lambda item: item.get("importance", 0), reverse=True)
    save_items(classified)
    recent = load_recent()
    recent = [ensure_display_fields(item) for item in recent]
    market = fetch_market_snapshot()
    archive_dir = write_dashboard_data(recent, market)

    print(f"items_fetched={len(fetched)}")
    print(f"items_saved={len(classified)}")
    print(f"dashboard_data={NEWS_JSON}")
    print(f"daily_archive={archive_dir}")
    if market.get("errors"):
        print("market_errors=" + json.dumps(market["errors"], ensure_ascii=False))
    if errors:
        print("fetch_errors=" + json.dumps(errors, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Semiconductor and CSP daily radar")
    parser.add_argument("--sample", action="store_true", help="Use bundled sample items")
    args = parser.parse_args()
    run_fetch(use_sample=args.sample)


def ensure_display_fields(item):
    if not item.get("title_zh"):
        item["title_zh"] = build_zh_title(item)
    if not item.get("summary_zh"):
        item["summary_zh"] = build_brief_summary(item)
    if not item.get("investment_takeaway"):
        item["investment_takeaway"] = build_takeaway(item)
    return item


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
