"""
CS2 Price Scraper - System Tray Launcher

Double-click to run. The app starts in your system tray, auto-opens
your browser, and runs the server + trading bot in the background.
"""

import sys
import os
import time
import json
import subprocess
import threading
import webbrowser
import urllib.request
from pathlib import Path
from datetime import datetime

# pystray for system tray
try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("ERROR: pystray and Pillow are required. Run: pip install pystray Pillow")
    input("Press Enter to exit...")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
APP_NAME = "CS2 Price Scraper"
HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"
CHECK_INTERVAL = 0.5  # seconds between server-ready polls
MAX_WAIT = 30         # max seconds to wait for server

# Determine where the app files live
if getattr(sys, "frozen", False):
    # PyInstaller bundle
    # sys._MEIPASS points to the _internal directory with bundled code+assets
    _meipass = getattr(sys, "_MEIPASS", None)
    if _meipass:
        BASE_DIR = Path(_meipass)
    else:
        BASE_DIR = Path(sys.executable).parent
    # Keep data/logs next to the EXE so they persist across updates
    DATA_DIR = Path(sys.executable).parent / "data"
else:
    BASE_DIR = Path(__file__).parent.resolve()
    DATA_DIR = BASE_DIR / "data"

LOG_FILE = DATA_DIR / "launcher.log"
SERVER_LOG = DATA_DIR / "server.log"

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

_ensure_data_dir()

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    print(line.strip())

# ---------------------------------------------------------------------------
# Generate a simple tray icon dynamically (no external file needed)
# ---------------------------------------------------------------------------
def _create_icon(size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Dark rounded-square background
    margin = 4
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=14,
        fill=(10, 10, 15, 255),
        outline=(0, 212, 255, 255),
        width=3,
    )
    # Simple "CS" text in cyan
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("arial.ttf", size // 2)
    except Exception:
        font = ImageFont.load_default()
    text = "CS"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size - tw) // 2, (size - th) // 2 - 2),
        text,
        font=font,
        fill=(0, 212, 255, 255),
    )
    return img

# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------
_server_proc = None          # subprocess handle (dev mode only)
_server_thread = None        # threading.Thread handle (frozen mode only)
_server_stop_event = threading.Event()
_server_lock = threading.Lock()
_server_ready = threading.Event()

_IS_FROZEN = getattr(sys, "frozen", False)

def _server_log_thread(proc):
    """Stream server stdout/stderr to a log file so the user can inspect it."""
    try:
        with open(SERVER_LOG, "w", encoding="utf-8") as f:
            for line in proc.stdout:
                f.write(line)
                f.flush()
    except Exception:
        pass

def _run_uvicorn_in_thread():
    """Run uvicorn in-process (background thread). Used when frozen to avoid
    spawning the EXE again, which would create an infinite fork loop."""
    import uvicorn
    import logging

    # Configure logging before uvicorn tries to, preventing formatter conflicts
    # when running inside a PyInstaller bundle.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    for noisy in ("uvicorn.access", "uvicorn.error", "httpx", "httpcore", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    log("Uvicorn starting in background thread...")
    try:
        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=PORT,
            log_level="warning",
            access_log=False,
            log_config=None,  # Don't let uvicorn configure its own logging
        )
    except Exception as e:
        log(f"Uvicorn thread error: {e}")

def start_server():
    global _server_proc, _server_thread
    with _server_lock:
        if _server_proc is not None or (_server_thread is not None and _server_thread.is_alive()):
            log("Server already running.")
            return

        log("Starting CS2 Price Scraper server...")

        if _IS_FROZEN:
            # FROZEN: Run uvicorn in a background thread.
            # DO NOT use subprocess — sys.executable is the EXE itself,
            # which would re-run launcher.py and create an infinite fork bomb.
            _server_thread = threading.Thread(target=_run_uvicorn_in_thread, daemon=True)
            _server_thread.start()
            log("Server thread started (in-process).")
        else:
            # DEV: Use subprocess so Ctrl+C in terminal kills it cleanly.
            env = os.environ.copy()
            cwd = str(BASE_DIR)
            cmd = [
                sys.executable, "-m", "uvicorn",
                "app.main:app",
                "--host", HOST,
                "--port", str(PORT),
                "--no-access-log",
            ]
            _server_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            t = threading.Thread(target=_server_log_thread, args=(_server_proc,), daemon=True)
            t.start()
            log(f"Server PID: {_server_proc.pid}")

def stop_server():
    global _server_proc, _server_thread
    with _server_lock:
        if _server_proc is not None:
            log("Stopping server (subprocess)...")
            try:
                _server_proc.terminate()
                try:
                    _server_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    _server_proc.kill()
                    _server_proc.wait()
            except Exception as e:
                log(f"Error stopping server: {e}")
            finally:
                _server_proc = None
                _server_ready.clear()
            log("Server stopped.")

        if _server_thread is not None:
            # We can't cleanly stop a uvicorn thread, but setting the event
            # lets any watchers know. The daemon thread dies when main exits.
            _server_stop_event.set()
            _server_ready.clear()
            log("Server thread stop requested.")

def is_server_running() -> bool:
    with _server_lock:
        if _IS_FROZEN:
            return _server_thread is not None and _server_thread.is_alive()
        if _server_proc is None:
            return False
        return _server_proc.poll() is None

def wait_for_server(max_wait: int = MAX_WAIT) -> bool:
    """Poll the health endpoint until the server responds."""
    url = f"{BASE_URL}/api/v1/health"
    start = time.time()
    while time.time() - start < max_wait:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    _server_ready.set()
                    return True
        except Exception:
            pass
        time.sleep(CHECK_INTERVAL)
    return False

def open_browser(path="/"):
    url = f"{BASE_URL}{path}"
    log(f"Opening browser: {url}")
    webbrowser.open(url, new=2)  # new tab

def open_logs():
    """Open the server log file in the default text editor / viewer."""
    if SERVER_LOG.exists():
        os.startfile(str(SERVER_LOG)) if sys.platform == "win32" else os.system(f'open "{SERVER_LOG}"')
    else:
        log("No log file yet.")

def trigger_scan():
    """Tell the bot to run a scan immediately."""
    url = f"{BASE_URL}/api/v1/bot/trigger-scan"
    try:
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            log(f"Scan triggered: {data.get('message', 'OK')}")
    except Exception as e:
        log(f"Scan trigger failed: {e}")

# ---------------------------------------------------------------------------
# Tray menu actions
# ---------------------------------------------------------------------------
def _on_open_dashboard(icon, item):
    if not is_server_running():
        start_server()
    if wait_for_server():
        open_browser("/")
    else:
        log("Server not responding yet.")

def _on_open_bot(icon, item):
    if not is_server_running():
        start_server()
    if wait_for_server():
        open_browser("/bot")
    else:
        log("Server not responding yet.")

def _on_trigger_scan(icon, item):
    if is_server_running() and _server_ready.is_set():
        threading.Thread(target=trigger_scan, daemon=True).start()
    else:
        log("Server not ready. Please wait.")

def _on_open_logs(icon, item):
    open_logs()

def _on_quit(icon, item):
    log("Quitting...")
    stop_server()
    icon.stop()

# ---------------------------------------------------------------------------
# Tray setup
# ---------------------------------------------------------------------------
def setup_tray():
    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", _on_open_dashboard),
        pystray.MenuItem("Open Bot UI", _on_open_bot),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Trigger Bot Scan", _on_trigger_scan),
        pystray.MenuItem("View Logs", _on_open_logs),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", _on_quit),
    )
    icon = pystray.Icon(
        name="cs2_scraper",
        icon=_create_icon(),
        title=APP_NAME,
        menu=menu,
    )
    return icon

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log("=" * 50)
    log(f"{APP_NAME} Launcher started")
    log(f"Base directory: {BASE_DIR}")
    log(f"Data directory: {DATA_DIR}")

    # Start server immediately
    start_server()

    # Wait for it in background so tray appears instantly
    def _wait_and_open():
        if wait_for_server():
            log("Server is ready!")
            open_browser("/bot")
        else:
            log("WARNING: Server did not become ready in time.")
            log(f"Check logs: {SERVER_LOG}")

    threading.Thread(target=_wait_and_open, daemon=True).start()

    # Start tray
    icon = setup_tray()
    log("Tray icon active. Right-click for menu.")
    icon.run()

if __name__ == "__main__":
    main()
