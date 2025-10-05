# APP/Scraper/scrape.py


from __future__ import annotations

import os, re, time, random, argparse, json
from datetime import datetime, timedelta, timezone, date
from typing import List, Dict, Any, Set, Optional

from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------- ENV ----------
def _try_load_env(path: str):
    if os.path.exists(path):
        load_dotenv(dotenv_path=path, override=False)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_try_load_env(os.path.join(BASE_DIR, ".env"))
_try_load_env(os.path.join(BASE_DIR, "..", "backend", ".env"))

# ---------- CONSTANTS ----------
DEFAULT_BASE_URL = "https://www.actuarylist.com"
DEFAULT_API_BASE = os.getenv("VITE_API_BASE") or os.getenv("REACT_APP_API_BASE") or "http://localhost:5000"
DEFAULT_API = DEFAULT_API_BASE.rstrip("/") + "/api"

DETAIL_HREF_RE = re.compile(r"/actuarial-jobs/\d+[-/]", re.I)

# For sanity filtering of bogus "tags"
_BAD_TAG_PHRASES = {
    "open menu", "copy link", "get started", "get free job alerts",
    "apply", "apply for this job", "view post", "menu", "share",
}

def parse_relative_time(text: str) -> date | None:
    if not text:
        return None
    s = text.strip().lower()
    s = (s.replace("hours","h").replace("hour","h").replace("hrs","h")
           .replace("days","d").replace("day","d")
           .replace("weeks","w").replace("week","w")
           .replace("months","mo").replace("month","mo")
           .replace("years","y").replace("year","y").replace("yrs","y").replace("yr","y")
           .replace("ago","").strip())
    m = re.match(r"^\s*(\d+)\s*(h|d|w|mo|y)\s*$", s)
    if not m:
        if "just" in s or s == "":
            return datetime.now(timezone.utc).date()
        return None
    qty = int(m.group(1)); unit = m.group(2)
    delta_days = 0 if unit == "h" else qty if unit == "d" else qty*7 if unit == "w" else qty*30 if unit == "mo" else qty*365
    return (datetime.now(timezone.utc) - timedelta(days=delta_days)).date()

def chrome_driver(headless: bool = True) -> webdriver.Chrome:
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-blink-features=AutomationControlled")
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(40)
    driver.implicitly_wait(0)
    return driver

def try_accept_cookies(driver: webdriver.Chrome, timeout: int = 6) -> None:
    texts = ["accept", "agree", "got it", "i accept", "allow"]
    end = time.time() + timeout
    while time.time() < end:
        try:
            for e in driver.find_elements(By.XPATH, "//button | //a"):
                label = (e.text or "").strip().lower()
                if any(t in label for t in texts):
                    e.click(); return
        except Exception:
            pass
        time.sleep(0.5)

def collect_job_links(driver: webdriver.Chrome) -> List[str]:
    anchors = driver.find_elements(By.XPATH, "//a[contains(@href, '/actuarial-jobs/')]")
    hrefs: list[str] = []
    for a in anchors:
        try:
            href = a.get_attribute("href") or ""
            if DETAIL_HREF_RE.search(href) and href not in hrefs:
                hrefs.append(href)
        except Exception:
            continue
    return hrefs

def smooth_scroll(driver: webdriver.Chrome, step_px: int = 600, pause: float = 0.35):
    driver.execute_script("window.scrollBy(0, arguments[0]);", step_px)
    time.sleep(pause + random.uniform(0.05, 0.15))

def scroll_until_enough(driver: webdriver.Chrome, want: int, max_scrolls: int = 40) -> None:
    last_count = 0
    for _ in range(max_scrolls):
        smooth_scroll(driver)
        links = collect_job_links(driver)
        if len(links) >= want:
            return
        if len(links) == last_count:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.8)
        last_count = len(links)

def soup_text_or_none(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for sel in selectors:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)
    return None

def soup_all_texts(soup: BeautifulSoup, selectors: list[str]) -> List[str]:
    out: list[str] = []
    for sel in selectors:
        for el in soup.select(sel):
            t = el.get_text(strip=True)
            if t: out.append(t)
    return out

# ---- Description helpers ----
def _strip_html(html: str) -> str:
    try:
        return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    except Exception:
        return html

def extract_description(soup: BeautifulSoup) -> str | None:
    # 1) JSON-LD description first
    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(sc.string or "")
        except Exception:
            continue
        objs = data if isinstance(data, list) else [data]
        for obj in objs:
            if not isinstance(obj, dict):
                continue
            if obj.get("@type") == "JobPosting" or "description" in obj:
                desc = obj.get("description")
                if desc and isinstance(desc, str):
                    text = _strip_html(desc)
                    if text:
                        return text[:1200]
    # 2) Content blocks
    selectors = [
        "article", ".job-content", "[class*=description]", "[class*=content]",
        "#job-description", ".job__description"
    ]
    chunks = []
    for sel in selectors:
        for el in soup.select(sel):
            text = el.get_text(" ", strip=True)
            if text and len(text) > 60:
                chunks.append(text)
        if chunks:
            break
    if not chunks:
        return None
    desc = " ".join(chunks)
    return desc[:1200]

# ---- Location helpers ----
def _looks_like_country_code(s: str) -> bool:
    # e.g. "UK", "GB", "HK", "US", "GB UK"
    return bool(re.fullmatch(r"[A-Z]{2,3}(?:\s+[A-Z]{2,3})*", s.strip()))

def _location_from_json_ld(soup: BeautifulSoup) -> list[str]:
    out: list[str] = []
    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(sc.string or "")
        except Exception:
            continue
        objs = data if isinstance(data, list) else [data]
        for obj in objs:
            if not isinstance(obj, dict):
                continue
            jl = obj.get("jobLocation")
            if not jl:
                continue
            jls = jl if isinstance(jl, list) else [jl]
            for j in jls:
                if not isinstance(j, dict):
                    continue
                addr = j.get("address") or {}
                if isinstance(addr, dict):
                    pieces = []
                    for k in ("addressLocality", "addressRegion", "addressCountry"):
                        v = addr.get(k)
                        if v and isinstance(v, str):
                            pieces.append(v.strip())
                    if pieces:
                        out.append(", ".join(pieces))
    # unique
    uniq, seen = [], set()
    for v in out:
        if v and v not in seen:
            seen.add(v); uniq.append(v)
    return uniq

def _location_from_links(soup: BeautifulSoup) -> list[str]:
    vals: list[str] = []
    for a in soup.select(
        "a[href^='/countries/'], a[href^='/cities/'], "
        "a[href^='/job-locations/'], a[href^='/locations/'], "
        "[class*=location] a[href*='/']"
    ):
        t = a.get_text(strip=True)
        if not t:
            continue
        if _looks_like_country_code(t) and len(t) > 10:
            continue
        if len(t) > 50:
            continue
        vals.append(t)
    # unique, short
    uniq, seen = [], set()
    for v in vals:
        if v and v not in seen:
            seen.add(v); uniq.append(v)
    return uniq

def _location_from_labels(soup: BeautifulSoup) -> list[str]:
    # Look for "City:" / "Country:" text blocks
    text = soup.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    city = country = region = None
    for ln in lines[:160]:
        low = ln.lower()
        if low.startswith("city:"):
            city = ln.split(":", 1)[1].strip()
        elif low.startswith("country:"):
            country = ln.split(":", 1)[1].strip()
        elif low.startswith("region:"):
            region = ln.split(":", 1)[1].strip()
        elif "remote" in low and not (city or country or region):
            country = "Remote"
    vals = []
    if city and country:
        vals.append(f"{city}, {country}")
    elif city and region:
        vals.append(f"{city}, {region}")
    elif country:
        vals.append(country)
    elif city:
        vals.append(city)
    elif region:
        vals.append(region)
    return vals

def collect_location(soup: BeautifulSoup) -> str | None:
    # Priority: JSON-LD → anchors → labels → Remote (if present)
    for source in (_location_from_json_ld, _location_from_links, _location_from_labels):
        vals = source(soup)
        vals = [v for v in vals if v and not _looks_like_country_code(v)]
        if vals:
            s = ", ".join(vals)
            return s[:300]  # DB safety
    # last-chance: look for the word "remote"
    if "remote" in soup.get_text(" ", strip=True).lower():
        return "Remote"
    return None

# ---- Tags (leave as before; improved 'chip' parsing) ----
def collect_tags(soup: BeautifulSoup) -> list[str]:
    tags: list[str] = []
    # known buckets (& generic .chip/.tag)
    for sel in [
        "a[href^='/keywords/']",
        "a[href^='/sectors/']",
        "a[href^='/job-types/']",
        "a[href^='/experience-levels/']",
        ".chip", ".badge", ".pill", ".tag", "[class*=tag]"
    ]:
        for el in soup.select(sel):
            # ignore anything obviously part of location or a button
            if el.find_parent(attrs={"class": re.compile("location", re.I)}):
                continue
            cls = " ".join(el.get("class", []))
            if re.search(r"\b(btn|button|menu|alert|apply)\b", cls, re.I):
                continue
            t = el.get_text(" ", strip=True)
            if not t or len(t) > 30:
                continue
            low = t.lower()
            if low in _BAD_TAG_PHRASES or _looks_like_country_code(t):
                continue
            tags.append(t)
    # unique & cap
    uniq, seen = [], set()
    for t in tags:
        if t and t not in seen:
            seen.add(t); uniq.append(t)
    return uniq[:12]

# ---------- MAIN DETAIL EXTRACTOR ----------
def scrape_detail(driver: webdriver.Chrome, url: str) -> Dict[str, Any] | None:
    try:
        driver.get(url)
    except Exception:
        return None
    try:
        WebDriverWait(driver, 15).until(
            EC.any_of(
                EC.presence_of_element_located((By.TAG_NAME, "h1")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(@class,'job')]")),
            )
        )
    except Exception:
        pass

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    # Title & Company
    title = soup_text_or_none(soup, ["h1","h1.job-title","h1[class*=title]","header h1"]) or ""
    title = title.strip()
    # Company: derive from slug if not shown
    company = soup_text_or_none(soup, ["[class*=company] a","[class*=company]","div.company","span.company"]) or ""
    if not company:
        m = re.search(r"/actuarial-jobs/\d+-([a-z0-9\-]+)", url)
        if m:
            slug = m.group(1)
            company = " ".join(part.capitalize() for part in slug.split("-"))
    company = (company or "Unknown").strip()

    # Location (robust)
    location = collect_location(soup) or "Unknown"

    # Dates / type / salary
    rel = soup_text_or_none(soup, ["[class*=posted]","[class*=time]","time","span.time","span.posted"])
    posting_date = parse_relative_time(rel) if rel else None
    salary_text = soup_text_or_none(soup, ["[class*=salary]",".salary","span.salary","div.salary"])
    job_type = soup_text_or_none(soup, ["[class*=job-type]",".job-type","span.job-type"]) or "Full-time"

    # Tags & Description
    tags = collect_tags(soup)
    description = extract_description(soup)

    if not title:
        return None

    return {
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "posting_date": posting_date.isoformat() if posting_date else None,
        "job_type": job_type,
        "tags": tags,
        "salary_text": salary_text,
        "source_url": url,
    }

def bulk_post(api_base: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    url = api_base.rstrip("/") + "/jobs/bulk"
    CHUNK = 50
    total_inserted = total_skipped = total_invalid = total_failed = 0
    details: list[Any] = []

    for i in range(0, len(items), CHUNK):
        chunk = items[i:i+CHUNK]
        try:
            r = requests.post(url, json={"items": chunk}, timeout=90)
            if r.status_code >= 400:
                details.append({"range": [i, i+len(chunk)-1], "status": r.status_code, "body": r.text})
            else:
                data = r.json()
                summary = data.get("summary", {}) or {}
                total_inserted += int(summary.get("inserted", 0))
                total_skipped  += int(summary.get("skipped", 0))
                total_invalid  += int(summary.get("invalid", 0))
                total_failed   += int(summary.get("failed", 0))
                if "results" in data:
                    details.extend(data["results"])
        except Exception as e:
            details.append({"range": [i, i+len(chunk)-1], "error": str(e)})
        time.sleep(0.4)

    return {
        "summary": {
            "inserted": total_inserted,
            "skipped": total_skipped,
            "invalid": total_invalid,
            "failed": total_failed,
        },
        "results": details,
    }

# ---------- MAIN SCRAPE FLOW ----------
def run(limit: int, headless: bool, save_mode: str, api_base: str, base_url: str, on_progress=None):
    driver = chrome_driver(headless=headless)
    collected: Set[str] = set()
    results: List[Dict[str, Any]] = []

    try:
        driver.get(base_url)
        try_accept_cookies(driver)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/actuarial-jobs/')]"))
        )
        target = max(20, limit)
        # Listing shows a finite set per page; this still gives us 20–40 fast.
        scroll_until_enough(driver, want=target, max_scrolls=60)
        all_links = collect_job_links(driver)
        if not all_links:
            print("No job links found on the home page.")
            return {"summary": {"inserted": 0, "skipped": 0, "invalid": 0, "failed": 0}}

        for href in all_links:
            if len(results) >= limit:
                break
            if href in collected:
                continue
            item = scrape_detail(driver, href)
            if not item:
                continue
            collected.add(href)
            results.append(item)
            if on_progress:
                on_progress(len(results), limit)
            if len(results) % 10 == 0:
                print(f"Scraped {len(results)} jobs...")
            time.sleep(0.4 + random.uniform(0.05, 0.2))
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    print(f"Total scraped (pre-dedupe by backend): {len(results)}")

    if save_mode == "api":
        summary = bulk_post(api_base, results)
        print("Bulk summary:", summary)
        return summary
    else:
        print("Direct DB save not implemented in this variant. Use --save api (default).")
        return {"summary": {"inserted": len(results), "skipped": 0, "invalid": 0, "failed": 0}}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=60, help="Number of jobs to fetch")
    parser.add_argument("--headless", action="store_true", help="Run Chrome headless")
    parser.add_argument("--save", choices=["api", "db"], default="api", help="Where to save scraped jobs")
    parser.add_argument("--api-base", type=str, default=DEFAULT_API, help="API base, e.g., http://localhost:5000/api")
    parser.add_argument("--base-url", type=str, default=DEFAULT_BASE_URL, help="Actuary List base URL")
    args = parser.parse_args()

    out = run(
        limit=max(1, args.limit),
        headless=bool(args.headless),
        save_mode=args.save,
        api_base=args.api_base,
        base_url=args.base_url,
    )
    print("Bulk summary:", out)
