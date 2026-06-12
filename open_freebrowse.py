#!/usr/bin/env python3
"""
Open FreeBrowse (https://github.com/freesurfer/freebrowse) with FreeSurfer outputs.

Usage:
    python open_freebrowse.py --t1w path_T1w.nii.gz --flair path_FLAIR.nii.gz \
        --pial-lh pial.lh --white-lh white.lh

Or edit the DEFAULT_* variables below and run:
    python open_freebrowse.py
"""

import argparse
import http.server
import json
import shutil
import signal
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

# ── Edit these defaults (set to None to omit) ─────────────────────────────────
DEFAULT_T1W      = "T1w.nii.gz"
DEFAULT_FLAIR    = None
DEFAULT_PIAL_LH  = None
DEFAULT_WHITE_LH = None
DEFAULT_PIAL_RH  = None
DEFAULT_WHITE_RH = None
# ──────────────────────────────────────────────────────────────────────────────

PORT               = 8765
FREEBROWSE_VERSION = "2.4.1"
FREEBROWSE_HTML    = f"freebrowse-{FREEBROWSE_VERSION}.html"
FREEBROWSE_DL_URL  = (
    f"https://freesurfer.github.io/freebrowse/downloads/{FREEBROWSE_HTML}"
)

# Cache only the downloaded HTML (2.7 MB) so we don't re-download every run.
HTML_CACHE_DIR = Path(tempfile.gettempdir()) / "freebrowse_html_cache"


# ── HTTP server with CORS ──────────────────────────────────────────────────────

def _make_handler(serve_dir: Path):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(serve_dir), **kwargs)

        def end_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            super().end_headers()

        def log_message(self, fmt, *args):
            pass  # silence request logs

    return Handler

def _start_server(serve_dir: Path, port: int) -> http.server.HTTPServer:
    server = http.server.HTTPServer(("localhost", port), _make_handler(serve_dir))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ── Setup ──────────────────────────────────────────────────────────────────────

def _download_html() -> Path:
    HTML_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest = HTML_CACHE_DIR / FREEBROWSE_HTML
    if not dest.exists():
        print(f"Downloading FreeBrowse {FREEBROWSE_VERSION} (once)…")
        urllib.request.urlretrieve(FREEBROWSE_DL_URL, dest)
        print("  Done.")
    return dest

def _link_or_copy(src: Path, dst: Path):
    """Symlink src → dst; fall back to copy if symlinks are unsupported."""
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        dst.symlink_to(src.resolve())
    except (OSError, NotImplementedError):
        shutil.copy2(src, dst)

def _served_name(stem: str, src: Path) -> str:
    """Return a served filename that preserves the source's extension(s).

    Preserving the real extension (e.g. .mgz vs .nii.gz) is critical: NiiVue
    infers the file format from the filename and will fail to parse an .mgz
    file that has been renamed to .nii.gz.
    """
    suffixes = "".join(src.suffixes)   # ".mgz"  or  ".nii.gz"
    return stem + suffixes

def _prepare_serve_dir(serve_dir: Path, port: int,
                       t1w: Path | None = None,
                       flair: Path | None = None,
                       pial_lh: Path | None = None,
                       white_lh: Path | None = None,
                       pial_rh: Path | None = None,
                       white_rh: Path | None = None,
                       lesion: Path | None = None) -> None:
    # FreeBrowse HTML — symlink to cached copy
    html_src = _download_html()
    _link_or_copy(html_src, serve_dir / FREEBROWSE_HTML)

    base = f"http://localhost:{port}"
    image_options = []
    meshes = []

    # Volumes
    for stem, src, colormap, opacity in [
        ("T1w",    t1w,    "gray",   1.0),
        ("FLAIR",  flair,  "gray",   0.7),
        ("lesion", lesion, "random", 0.8),
    ]:
        if src is None:
            continue
        name = _served_name(stem, src)
        _link_or_copy(src, serve_dir / name)
        image_options.append({
            "url":      f"{base}/{name}",
            "name":     name,
            "colormap": colormap,
            "opacity":  opacity,
            "visible":  True,
        })

    # Surfaces: pial=yellow, white=orange; same colors for LH and RH
    for served_name, src, color in [
        ("lh.pial",  pial_lh,  [255, 255, 0,   255]),
        ("lh.white", white_lh, [255, 165, 0,   255]),
        ("rh.pial",  pial_rh,  [255, 255, 0,   255]),
        ("rh.white", white_rh, [255, 165, 0,   255]),
    ]:
        if src is None:
            continue
        _link_or_copy(src, serve_dir / served_name)
        meshes.append({
            "url":             f"{base}/{served_name}",
            "name":            served_name,
            "rgba255":         color,
            "opacity":         1,
            "visible":         True,
            "meshShaderIndex": 14,
        })

    scene = {"imageOptionsArray": image_options, "meshes": meshes}
    (serve_dir / "scene.nvd").write_text(json.dumps(scene, indent=2))


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Launch FreeBrowse with FreeSurfer outputs."
    )
    parser.add_argument("--t1w",      default=DEFAULT_T1W,      help="T1w volume (.nii.gz or .mgz)")
    parser.add_argument("--flair",    default=DEFAULT_FLAIR,    help="FLAIR volume (.nii.gz or .mgz)")
    parser.add_argument("--pial-lh",  default=DEFAULT_PIAL_LH,  help="LH pial surface")
    parser.add_argument("--white-lh", default=DEFAULT_WHITE_LH, help="LH white surface")
    parser.add_argument("--pial-rh",  default=DEFAULT_PIAL_RH,  help="RH pial surface")
    parser.add_argument("--white-rh", default=DEFAULT_WHITE_RH, help="RH white surface")
    parser.add_argument("--lesion",   default=None,             help="Lesion mask overlay (.nii.gz or .mgz)")
    parser.add_argument("--port",     default=PORT, type=int,   help=f"Local port (default {PORT})")
    args = parser.parse_args()

    def _resolve(val) -> Path | None:
        return Path(val) if val else None

    optional = {
        "--t1w":      _resolve(args.t1w),
        "--flair":    _resolve(args.flair),
        "--pial-lh":  _resolve(args.pial_lh),
        "--white-lh": _resolve(args.white_lh),
        "--pial-rh":  _resolve(args.pial_rh),
        "--white-rh": _resolve(args.white_rh),
        "--lesion":   _resolve(args.lesion),
    }

    missing = [f"{flag}: {p}" for flag, p in optional.items() if p is not None and not p.exists()]
    if missing:
        print("Error — file(s) not found:")
        for m in missing:
            print(f"  {m}")
        sys.exit(1)

    provided = [flag for flag, p in optional.items() if p is not None]
    if not provided:
        print("Error — no files provided. Use --t1w, --flair, --pial-lh, etc.")
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="freebrowse_serve_") as tmp:
        serve_dir = Path(tmp)

        _prepare_serve_dir(
            serve_dir,
            port=args.port,
            t1w=optional["--t1w"],
            flair=optional["--flair"],
            pial_lh=optional["--pial-lh"],
            white_lh=optional["--white-lh"],
            pial_rh=optional["--pial-rh"],
            white_rh=optional["--white-rh"],
            lesion=optional["--lesion"],
        )

        _start_server(serve_dir, args.port)

        url = (
            f"http://localhost:{args.port}/{FREEBROWSE_HTML}"
            f"?nvd=http://localhost:{args.port}/scene.nvd"
        )
        print(f"Serving at  http://localhost:{args.port}")
        print(f"Opening     {url}")
        time.sleep(0.4)
        webbrowser.open(url)

        print("Server running — press Ctrl+C to stop.")
        try:
            signal.pause()
        except (KeyboardInterrupt, AttributeError):
            # AttributeError: signal.pause() not available on Windows
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                pass
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
