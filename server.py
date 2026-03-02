#!/usr/bin/env python3
import json
import sqlite3
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
DB_PATH = ROOT / "game.db"
CONFIG_PATH = ROOT / "config" / "game_config.json"
STATIC_DIR = ROOT / "static"
INDEX_PATH = ROOT / "templates" / "index.html"

DB_LOCK = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)

    if "theme" not in config or "upgrades" not in config:
        raise ValueError("Config must contain 'theme' and 'upgrades'")

    normalized_upgrades = []
    for item in config["upgrades"]:
        normalized_upgrades.append(
            {
                "id": str(item["id"]),
                "name": str(item["name"]),
                "description": str(item.get("description", "")),
                "base_cost": int(item["base_cost"]),
                "cps": float(item["cps"]),
                "cost_multiplier": float(item.get("cost_multiplier", 1.15)),
            }
        )

    config["upgrades"] = normalized_upgrades
    return config


def init_db(config: dict) -> None:
    with DB_LOCK, sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS game_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                resource_count REAL NOT NULL,
                total_clicks INTEGER NOT NULL,
                last_updated TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS owned_upgrades (
                upgrade_id TEXT PRIMARY KEY,
                quantity INTEGER NOT NULL
            )
            """
        )

        row = conn.execute("SELECT id FROM game_state WHERE id = 1").fetchone()
        if not row:
            conn.execute(
                "INSERT INTO game_state (id, resource_count, total_clicks, last_updated) VALUES (1, 0, 0, ?)",
                (now_iso(),),
            )

        for upgrade in config["upgrades"]:
            conn.execute(
                "INSERT OR IGNORE INTO owned_upgrades (upgrade_id, quantity) VALUES (?, 0)",
                (upgrade["id"],),
            )


def get_owned(conn: sqlite3.Connection) -> dict:
    return {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT upgrade_id, quantity FROM owned_upgrades"
        ).fetchall()
    }


def update_passive_generation(conn: sqlite3.Connection, config: dict) -> None:
    state = conn.execute(
        "SELECT resource_count, total_clicks, last_updated FROM game_state WHERE id = 1"
    ).fetchone()
    if not state:
        return

    resource_count, total_clicks, last_updated = state
    last_dt = datetime.fromisoformat(last_updated)
    elapsed = max((datetime.now(timezone.utc) - last_dt).total_seconds(), 0)

    owned = get_owned(conn)
    cps = 0.0
    for u in config["upgrades"]:
        cps += owned.get(u["id"], 0) * u["cps"]

    resource_count += cps * elapsed
    conn.execute(
        "UPDATE game_state SET resource_count = ?, total_clicks = ?, last_updated = ? WHERE id = 1",
        (resource_count, total_clicks, now_iso()),
    )


def compute_state(config: dict) -> dict:
    with DB_LOCK, sqlite3.connect(DB_PATH) as conn:
        update_passive_generation(conn, config)
        conn.commit()

        resource_count, total_clicks, last_updated = conn.execute(
            "SELECT resource_count, total_clicks, last_updated FROM game_state WHERE id = 1"
        ).fetchone()
        owned = get_owned(conn)

    upgrades = []
    total_cps = 0.0
    for u in config["upgrades"]:
        qty = owned.get(u["id"], 0)
        next_cost = round(u["base_cost"] * (u["cost_multiplier"] ** qty), 2)
        total_cps += qty * u["cps"]
        upgrades.append(
            {
                **u,
                "quantity": qty,
                "next_cost": next_cost,
            }
        )

    return {
        "resource_count": round(resource_count, 2),
        "total_clicks": total_clicks,
        "last_updated": last_updated,
        "cps": round(total_cps, 2),
        "theme": config["theme"],
        "upgrades": upgrades,
    }


def do_click(config: dict) -> dict:
    with DB_LOCK, sqlite3.connect(DB_PATH) as conn:
        update_passive_generation(conn, config)
        conn.execute(
            "UPDATE game_state SET resource_count = resource_count + 1, total_clicks = total_clicks + 1, last_updated = ? WHERE id = 1",
            (now_iso(),),
        )
        conn.commit()
    return compute_state(config)


def buy_upgrade(config: dict, upgrade_id: str) -> tuple[bool, str, dict | None]:
    upgrade = next((u for u in config["upgrades"] if u["id"] == upgrade_id), None)
    if not upgrade:
        return False, "Unknown upgrade.", None

    with DB_LOCK, sqlite3.connect(DB_PATH) as conn:
        update_passive_generation(conn, config)

        qty = conn.execute(
            "SELECT quantity FROM owned_upgrades WHERE upgrade_id = ?",
            (upgrade_id,),
        ).fetchone()[0]
        cost = round(upgrade["base_cost"] * (upgrade["cost_multiplier"] ** qty), 2)

        resource_count = conn.execute(
            "SELECT resource_count FROM game_state WHERE id = 1"
        ).fetchone()[0]

        if resource_count + 1e-9 < cost:
            conn.commit()
            return False, "Not enough resources.", None

        conn.execute(
            "UPDATE game_state SET resource_count = ?, last_updated = ? WHERE id = 1",
            (resource_count - cost, now_iso()),
        )
        conn.execute(
            "UPDATE owned_upgrades SET quantity = quantity + 1 WHERE upgrade_id = ?",
            (upgrade_id,),
        )
        conn.commit()

    return True, "Upgrade purchased.", compute_state(config)


class CookieClickerHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self._serve_file(INDEX_PATH, "text/html; charset=utf-8")
        if parsed.path == "/api/state":
            config = load_config()
            return self._send_json(compute_state(config))
        if parsed.path.startswith("/static/"):
            requested = parsed.path.replace("/static/", "", 1)
            file_path = STATIC_DIR / requested
            if requested.endswith(".js"):
                content_type = "text/javascript; charset=utf-8"
            elif requested.endswith(".css"):
                content_type = "text/css; charset=utf-8"
            else:
                content_type = "application/octet-stream"
            return self._serve_file(file_path, content_type)

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        config = load_config()

        if parsed.path == "/api/click":
            return self._send_json(do_click(config))

        if parsed.path == "/api/buy":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
                upgrade_id = str(payload.get("upgrade_id", ""))
            except (ValueError, UnicodeDecodeError):
                return self._send_json({"error": "Invalid JSON payload."}, status=400)

            ok, message, state = buy_upgrade(config, upgrade_id)
            if not ok:
                return self._send_json({"error": message}, status=400)
            return self._send_json({"message": message, "state": state})

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")


def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    config = load_config()
    init_db(config)
    server = ThreadingHTTPServer((host, port), CookieClickerHandler)
    print(f"Serving on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
