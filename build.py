"""
Build script: creates a standalone Windows executable for CS2 Price Scraper.

Usage:
    python build.py

Output:
    dist/CS2PriceScraper/CS2PriceScraper.exe

The resulting folder can be zipped and distributed. Users just double-click
the .exe to run the server from the system tray.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).parent.resolve()
DIST_DIR = ROOT / "dist" / "CS2PriceScraper"
BUILD_DIR = ROOT / "build"

# ---------------------------------------------------------------------------
# Generate icon
# ---------------------------------------------------------------------------
def generate_icon():
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    images = []
    for size in sizes:
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        margin = max(1, size[0] // 16)
        draw.rounded_rectangle(
            [margin, margin, size[0] - margin, size[1] - margin],
            radius=size[0] // 5,
            fill=(10, 10, 15, 255),
            outline=(0, 212, 255, 255),
            width=max(1, size[0] // 20),
        )
        try:
            from PIL import ImageFont
            font_size = max(8, size[0] // 2)
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
        text = "CS"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            ((size[0] - tw) // 2, (size[1] - th) // 2 - 1),
            text,
            font=font,
            fill=(0, 212, 255, 255),
        )
        images.append(img)
    icon_path = ROOT / "app_icon.ico"
    images[0].save(icon_path, format="ICO", sizes=[(i.width, i.height) for i in images], append_images=images[1:])
    return str(icon_path)

# ---------------------------------------------------------------------------
# Build with PyInstaller
# ---------------------------------------------------------------------------
def build():
    print("=" * 60)
    print("Building CS2 Price Scraper standalone executable")
    print("=" * 60)

    # Clean previous builds
    if DIST_DIR.exists():
        print("Cleaning old dist...")
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        print("Cleaning old build...")
        shutil.rmtree(BUILD_DIR)

    # Generate icon
    print("Generating icon...")
    icon_path = generate_icon()
    print(f"  -> {icon_path}")

    # Hidden imports - everything the app needs that PyInstaller might miss
    hiddenimports = [
        # App modules
        "app.main",
        "app.api.v1.endpoints",
        "app.api.v1.auth",
        "app.api.v1.bot",
        "app.core.config",
        "app.core.auth",
        "app.core.logging",
        "app.db.database",
        "app.models.models",
        "app.schemas.schemas",
        "app.services.bot_engine",
        "app.services.steam",
        "app.services.youpin",
        "app.services.buff",
        "app.services.skinport",
        "app.services.scraper",
        # Uvicorn internals
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.loops.uvloop",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.protocols.websockets.wsproto_impl",
        "uvicorn.lifespan.auto",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        # SQLAlchemy
        "sqlalchemy.ext.baked",
        "sqlalchemy.sql.default_comparator",
        # FastAPI / Starlette
        "fastapi.middleware.cors",
        "fastapi.staticfiles",
        "fastapi.templating",
        "starlette.middleware.errors",
        "starlette.middleware.exceptions",
        # Jinja2
        "jinja2.ext",
        # APScheduler
        "apscheduler.triggers.interval",
        "apscheduler.executors.pool",
        "apscheduler.jobstores.memory",
        # Other
        "pkg_resources",
        "bcrypt",
        "jwt",
        "pystray._util.win32",
        "pystray._win32",
    ]

    # Data files to bundle
    datas = [
        (str(ROOT / "templates"), "templates"),
        (str(ROOT / "static"), "static"),
        (str(ROOT / ".env.example"), "."),
    ]

    # Build PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "CS2PriceScraper",
        "--onedir",
        "--windowed",  # No console window on Windows
        f"--icon={icon_path}",
        "--noconfirm",
        "--clean",
    ]

    for hi in hiddenimports:
        cmd.extend(["--hidden-import", hi])

    for src, dst in datas:
        cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])

    cmd.append(str(ROOT / "launcher.py"))

    print("Running PyInstaller...")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))

    if result.returncode != 0:
        print("\nBUILD FAILED")
        sys.exit(1)

    print("\nBuild completed!")
    print(f"Output: {DIST_DIR}")
    print(f"Executable: {DIST_DIR / 'CS2PriceScraper.exe'}")

    # Show size
    exe_path = DIST_DIR / "CS2PriceScraper.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"EXE size: {size_mb:.1f} MB")

    total_size = sum(f.stat().st_size for f in DIST_DIR.rglob("*") if f.is_file()) / (1024 * 1024)
    print(f"Total folder size: {total_size:.1f} MB")

    print("\nYou can now:")
    print(f"  1. Zip the folder: {DIST_DIR}")
    print("  2. Share it. Users double-click CS2PriceScraper.exe to run.")

if __name__ == "__main__":
    build()
