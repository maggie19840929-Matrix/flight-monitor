# Codex Implementation Tasks

This repo is a **flight price monitor** framework.  All the skeleton code, data
models, and interfaces are already in place.  Your job is to fill in every
`raise NotImplementedError("Codex: ...")` stub, in the order listed below.

Run `python -m pytest tests/` after each section — the existing tests must stay green.

---

## 0  Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## 1  Config parser  (`src/config.py`)

Implement `AppConfig._parse_watch_list()`.

- Iterate `self._raw["watch_list"]`.
- For each entry build a `WatchConfig` dataclass:
  - `trip_type` → `TripType(entry["trip_type"])`
  - `outbound_date` → `date.fromisoformat(entry["outbound"]["date"])`
  - `return_date` → only if `trip_type == roundtrip`
  - `airlines` → `entry.get("airlines", [])` (empty list = all)
- Raise `ValueError` if required keys are missing.

---

## 2  Storage  (`src/storage.py`)

Implement all four methods using the `sqlite3` stdlib (no ORM).

**`_init_schema`** — run the two `CREATE TABLE/INDEX` statements in the module docstring.

**`save(watch_id, result)`**
- If `result` is `FlightLeg`: insert one row.
- If `result` is `RoundTripBundle`: insert two rows (outbound + inbound).
- Use `INSERT OR IGNORE` to avoid duplicate rows on the same `(watch_id, flight_no, scraped_at)`.

**`already_notified(watch_id, flight_no, price, within_hours=4)`**
```sql
SELECT 1 FROM price_history
WHERE watch_id=? AND flight_no=? AND price=?
  AND scraped_at >= datetime('now', '-{within_hours} hours')
LIMIT 1
```

**`prune_old(keep_days)`**
```sql
DELETE FROM price_history WHERE scraped_at < datetime('now', '-{keep_days} days')
```

---

## 3  Notifier message formatter  (`src/notifiers/base.py`)

Implement `format_message(alert)`.  Output Chinese-language text, e.g.:

```
【机票提醒】暑假京沪往返
✈ CA1234  PEK → SHA
📅 2026-07-15  08:00 → 10:00（2小时）
💰 ¥980 含税（携程）
🔗 https://www.ctrip.com/...
```

For `RoundTripBundle` show both legs and total price.

---

## 4  Bark notifier  (`src/notifiers/bark.py`)

```python
url = f"{cfg['server']}/{cfg['device_key']}/{title}/{body}"
params = {
    "sound": cfg.get("sound", ""),
    "icon":  cfg.get("icon", ""),
    "url":   booking_url,   # deep-link, URL-encoded
}
resp = requests.get(url, params=params, timeout=10)
return resp.status_code == 200
```

- `title` = first line of `message`
- `body`  = remaining lines joined with `\n`
- URL-encode the booking_url value.

---

## 5  PushPlus notifier  (`src/notifiers/pushplus.py`)

```python
payload = {
    "token":    cfg["token"],
    "title":    "机票提醒",
    "content":  message.replace("\n", "<br>"),
    "template": cfg.get("template", "html"),
}
resp = requests.post(self._API, json=payload, timeout=15)
return resp.json().get("code") == 200
```

---

## 6  Notifier factory  (`src/notifiers/__init__.py`)

```python
def build_notifiers(cfg):
    out = []
    if cfg.get("bark", {}).get("enabled"):
        out.append(BarkNotifier(cfg["bark"]))
    if cfg.get("pushplus", {}).get("enabled"):
        out.append(PushPlusNotifier(cfg["pushplus"]))
    return out
```

---

## 7  Ctrip searcher  (`src/searchers/ctrip.py`)

### 7a — scrape path (no API key)

POST to the mobile JSON endpoint:

```
POST https://m.ctrip.com/restapi/soa2/15757/json/searchFlights
Content-Type: application/json
```

Request body:
```json
{
  "flightWay": "S",          // S=oneway, D=roundtrip
  "classType": "ALL",
  "hasChild": false,
  "hasBaby": false,
  "searchIndex": 1,
  "airportParams": [
    {"cityType": 0, "dcity": "PEK", "acity": "SHA", "date": "2026-07-15"},
    // add second element for roundtrip
  ]
}
```

Response path: `data.flightItineraryList[].flightSegments[0]`

Key fields to extract:
- `flightNo`, `airlineCode`, `depAirportCode`, `arrAirportCode`
- `depDateTime`, `arrDateTime`
- `priceList[0].price` (lowest cabin price)
- `priceList[0].hyperlink` → booking URL

### 7b — booking URL pattern

```
https://www.ctrip.com/online/clk/toBook.aspx?flighttype=S&ddate=2026-07-15&dcity=PEK&acity=SHA&flightNo=CA1234&classType=Y
```

---

## 8  Qunar searcher  (`src/searchers/qunar.py`)

```
GET https://m.qunar.com/api/flight/searchDomesticOW
    ?fromCity=PEK&toCity=SHA&fromDate=2026-07-15&adult=1&child=0&infant=0
```

Response path: `data.flightList[].priceList[]`

Key fields: `flightNo`, `airlineCode`, `depTime`, `arrTime`, `price`, `deepLink`

`deepLink` is the direct booking URL — use it as-is.

---

## 9  Airline direct scrapers  (`src/searchers/airline_direct.py`)

Use **Playwright** (sync API).  General pattern:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    results = []
    def handle_response(response):
        if "/searchFlight" in response.url:
            results.append(response.json())

    page.on("response", handle_response)
    page.goto("https://www.csair.com/cn/booking/flight_searching.shtml")
    # fill search form, submit, wait for network idle
    page.wait_for_load_state("networkidle")
    browser.close()

return self._parse_response(results[0] if results else {}, watch)
```

Implement `CAScraper`, `MUScraper`, `CZScraper` following the per-airline details
in `src/searchers/airline_direct.py` module docstring.

---

## 10  Searcher factory  (`src/searchers/__init__.py`)

```python
def build_searchers(sources_cfg, proxy):
    out = []
    if sources_cfg.get("ctrip", {}).get("enabled"):
        out.append(CtripSearcher(sources_cfg["ctrip"], proxy))
    if sources_cfg.get("qunar", {}).get("enabled"):
        out.append(QunarSearcher(sources_cfg["qunar"], proxy))
    if sources_cfg.get("airline_direct", {}).get("enabled"):
        for code, Cls in AIRLINE_SCRAPERS.items():
            out.append(Cls(sources_cfg["airline_direct"], proxy))
    return out
```

---

## 11  Monitor  (`src/monitor.py`)

Implement `run_cycle()`:

```python
def run_cycle(self):
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(self._search_one, searcher, watch): (searcher, watch)
            for watch in self.cfg.watch_list
            for searcher in self.searchers
        }
        for future in concurrent.futures.as_completed(futures):
            _, watch = futures[future]
            try:
                results = future.result()
                self._fire_alerts(watch, results)
            except Exception as exc:
                logger.error("Search failed: %s", exc)

    self.storage.prune_old(self.cfg.storage.get("keep_history_days", 30))
```

---

## 12  Scheduler  (`src/scheduler.py`)

```python
def start(cfg):
    import atexit, signal
    monitor = Monitor(cfg)

    def _within_active_hours():
        h = datetime.now(tz).hour
        return cfg.scheduler["active_hours"]["start"] <= h < cfg.scheduler["active_hours"]["end"]

    def _job():
        if _within_active_hours():
            monitor.run_cycle()

    tz = cfg.scheduler["timezone"]
    sched = BlockingScheduler(timezone=tz)
    sched.add_job(_job, IntervalTrigger(minutes=cfg.scheduler["interval_minutes"]))
    atexit.register(monitor.shutdown)
    signal.signal(signal.SIGTERM, lambda *_: (monitor.shutdown(), sched.shutdown()))
    sched.start()
```

---

## 13  Validation (WatchConfig & FlightLeg)

Fill in the `__post_init__` stubs in `src/models.py`:

- `FlightLeg`: assert `arrival_time > departure_time`; assert `price >= 0`; normalise `airline` to uppercase.
- `WatchConfig` roundtrip: assert `return_date > outbound_date`.

---

## 14  Smoke test

After all stubs are implemented, run:

```bash
# unit tests
python -m pytest tests/ -v

# one-cycle dry run (reads config.yaml; needs valid Bark key or disable all notifiers)
python main.py --once
```

Expected: no exceptions, log lines like:
```
INFO monitor: Starting monitor cycle at 2026-...
INFO monitor: Alert sent via BarkNotifier for CA1234 ¥980
```

---

## Notes for Codex

- **Do not modify** `models.py` field names — downstream code depends on them.
- **Do not add** third-party HTTP libraries beyond `requests` + `playwright`.
- **Respect jitter**: `BaseSearcher._jitter()` is already called in `search()` — do not add extra sleeps.
- If an airline endpoint returns 403 after retry, log a warning and return `[]` (don't raise).
- All timestamps stored to DB must be UTC ISO-8601 strings.

---

## 15  修复 airline_direct 搜索表单（必须补实现）

当前三个航司 Playwright scraper 只打开了首页，**没有填搜索条件**，导致拿不到目标航班数据。
请按以下方式补全每个航司的 `_scrape_with_playwright()`：

### CA（国航）
```python
page.goto("https://www.airchina.com.cn/cn/booking/search-flight.shtml", wait_until="domcontentloaded")
# 填出发地
page.fill('input[name="dCity"]', watch.outbound_origin)
# 填目的地
page.fill('input[name="aCity"]', watch.outbound_destination)
# 填日期
page.fill('input[name="depDate"]', watch.outbound_date.strftime("%Y-%m-%d"))
# 提交
page.click('button[type="submit"]')
page.wait_for_load_state("networkidle", timeout=30000)
```
拦截包含 `searchFlight` 或 `flightList` 的 XHR response 即为数据。

### MU（东航）
```python
url = (
    "https://www.ceair.com/booking/flight-search_V4.html#/"
    f"flight-search?tripType={'RT' if watch.return_date else 'OW'}"
    f"&depCity={watch.outbound_origin}&arrCity={watch.outbound_destination}"
    f"&depDate={watch.outbound_date.isoformat()}"
    + (f"&retDate={watch.return_date.isoformat()}" if watch.return_date else "")
)
page.goto(url, wait_until="domcontentloaded")
page.wait_for_load_state("networkidle", timeout=30000)
```
拦截包含 `/ceas/pc/search` 的 response。

### CZ（南航）
```python
page.goto("https://www.csair.com/cn/booking/flight_searching.shtml", wait_until="domcontentloaded")
page.fill('#deptCity', watch.outbound_origin)
page.fill('#arrvCity', watch.outbound_destination)
page.fill('#deptDate', watch.outbound_date.strftime("%Y-%m-%d"))
if watch.return_date:
    page.fill('#retuDate', watch.return_date.strftime("%Y-%m-%d"))
page.click('#searchBtn')
page.wait_for_load_state("networkidle", timeout=30000)
```
拦截包含 `searchFlight` 的 response。

### 通用要求
- 拦截到 403 时 log warning 并返回 `[]`，不抛异常
- 如果 30s 内无数据响应，返回 `[]`
- 完成后运行 `python main.py --once` 确认日志中出现 airline_direct 的搜索记录
