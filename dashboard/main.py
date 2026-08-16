#!/usr/bin/env python3
"""ThinLine vertical ops dashboard — native PySide6 9:16 kiosk."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

# Allow `python main.py` from the dashboard directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from config import load_config
from ui.window import DashboardWindow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ThinLine vertical ops dashboard")
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Run in a 9:16 window instead of fullscreen",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Override window width (default 1080)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Override window height (default 1920)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    if args.width or args.height:
        config = replace(
            config,
            window_width=args.width or config.window_width,
            window_height=args.height or config.window_height,
        )

    # High-DPI for wall monitors
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("ThinLine Vertical Ops")
    app.setStyle("Fusion")

    window = DashboardWindow(config, windowed=args.windowed)
    if args.windowed:
        window.show()
    else:
        window.showFullScreen()
    window.start_workers()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
