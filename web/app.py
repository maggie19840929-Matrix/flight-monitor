"""
本地配置 Web UI — 运行后访问 http://localhost:5050
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from flask import Flask, jsonify, render_template, request
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

app = Flask(__name__)


def _load() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _save(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/config")
def get_config():
    return jsonify(_load())


@app.post("/api/watch")
def add_watch():
    cfg = _load()
    data = request.json
    cfg.setdefault("watch_list", []).append(data)
    _save(cfg)
    return jsonify({"ok": True})


@app.put("/api/watch/<watch_id>")
def update_watch(watch_id: str):
    cfg = _load()
    data = request.json
    for i, w in enumerate(cfg.get("watch_list", [])):
        if w["id"] == watch_id:
            cfg["watch_list"][i] = data
            _save(cfg)
            return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "not found"}), 404


@app.delete("/api/watch/<watch_id>")
def delete_watch(watch_id: str):
    cfg = _load()
    cfg["watch_list"] = [w for w in cfg.get("watch_list", []) if w["id"] != watch_id]
    _save(cfg)
    return jsonify({"ok": True})


@app.post("/api/settings")
def save_settings():
    cfg = _load()
    data = request.json
    cfg["scheduler"]["interval_minutes"] = int(data.get("interval_minutes", 15))
    cfg["notifiers"]["bark"]["device_key"] = data.get("bark_key", "")
    cfg["notifiers"]["bark"]["enabled"] = bool(data.get("bark_key", ""))
    cfg["notifiers"]["pushplus"]["token"] = data.get("pushplus_token", "")
    cfg["notifiers"]["pushplus"]["enabled"] = bool(data.get("pushplus_token", ""))
    _save(cfg)
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("配置页面已启动 → http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=False)
