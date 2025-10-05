import os, sys, threading, time
from flask import Blueprint, jsonify, request

scrape_bp = Blueprint("scrape_bp", __name__)

# Make the Scraper package importable
SCRAPER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Scraper"))
if SCRAPER_DIR not in sys.path:
    sys.path.append(SCRAPER_DIR)

try:
    from scrape import run as scraper_run  # file is Scraper/scrape.py
    _import_error = None
except Exception as e:
    scraper_run = None
    _import_error = str(e)

_state = {
    "running": False,
    "fetched": 0,
    "limit": 0,
    "error": None,
    "started_at": None,
    "finished_at": None,
}
_lock = threading.Lock()


def _on_progress(current: int, limit: int):
    with _lock:
        _state["fetched"] = int(current)
        _state["limit"] = int(limit or 0)


def _runner(limit: int, headless: bool, api_base: str, base_url: str):
    global _state
    try:
        scraper_run(
            limit=limit,
            headless=headless,
            save_mode="api",
            api_base=api_base,
            base_url=base_url,
            on_progress=_on_progress,
        )
        with _lock:
            _state["running"] = False
            _state["finished_at"] = time.time()
    except Exception as e:
        with _lock:
            _state["running"] = False
            _state["error"] = str(e)
            _state["finished_at"] = time.time()


@scrape_bp.post("/scrape/start")
def start_scrape():
    if _import_error or not scraper_run:
        return jsonify({"ok": False, "error": f"Scraper import failed: {_import_error or 'unknown'}"}), 500

    data = request.get_json(silent=True) or {}
    limit = max(1, int(data.get("limit", 50)))
    headless = bool(data.get("headless", True))
    api_base = data.get("api_base") or request.url_root.rstrip("/") + "/api"
    base_url = data.get("base_url") or "https://www.actuarylist.com/experience-levels/senior-actuary"

    with _lock:
        if _state["running"]:
            return jsonify({"ok": False, "error": "already-running", "status": _state}), 409
        _state.update({
            "running": True,
            "fetched": 0,
            "limit": limit,
            "error": None,
            "started_at": time.time(),
            "finished_at": None,
        })

    t = threading.Thread(target=_runner, args=(limit, headless, api_base, base_url), daemon=True)
    t.start()
    return jsonify({"ok": True, "status": _state})


@scrape_bp.get("/scrape/status")
def scrape_status():
    with _lock:
        return jsonify({"ok": True, "status": _state})
