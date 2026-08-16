"""Main fullscreen 9:16 window."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from config import Config
from models import ActivitySnapshot, AddressHit, PublerPost, RemoteHealth, ScannerHealth
from ui.activity import ActivityPanel
from ui.health_panel import HealthPanel
from ui.overlay import AddressOverlay
from ui.publer_panel import PublerPanel
from ui.styles import STYLESHEET
from workers import PublerWorker, PulseWorker, RemoteHealthWorker, ScannerHealthWorker


class DashboardWindow(QWidget):
    def __init__(self, config: Config, windowed: bool = False) -> None:
        super().__init__()
        self._config = config
        self._windowed = windowed
        self.setObjectName("Root")
        self.setWindowTitle("ThinLine Vertical Ops")
        self.setStyleSheet(STYLESHEET)
        self.resize(config.window_width, config.window_height)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        brand_row = QHBoxLayout()
        brand = QLabel("THINLINE · COUNTY PULSE")
        brand.setObjectName("Brand")
        brand_row.addWidget(brand)
        brand_row.addStretch(1)
        self.clock = QLabel("")
        self.clock.setObjectName("SectionSub")
        brand_row.addWidget(self.clock)
        root.addLayout(brand_row)

        self.activity = ActivityPanel()
        root.addWidget(self.activity, stretch=45)

        self.health = HealthPanel()
        root.addWidget(self.health, stretch=25)

        self.publer = PublerPanel()
        root.addWidget(self.publer, stretch=20)

        self.overlay = AddressOverlay(self)
        self.overlay.set_overlay_seconds(config.address_overlay_seconds)
        self.overlay.hide()

        QShortcut(QKeySequence("Escape"), self, activated=self.close)
        QShortcut(QKeySequence("Q"), self, activated=self.close)

        self._pulse = PulseWorker(config, self)
        self._pulse.updated.connect(self._on_activity)
        self._pulse.addresses.connect(self._on_addresses)
        self._pulse.failed.connect(self.activity.set_error)

        self._scanner = ScannerHealthWorker(config, self)
        self._scanner.updated.connect(self._on_scanner)

        self._remote = RemoteHealthWorker(config, self)
        self._remote.updated.connect(self._on_remote)

        self._publer = PublerWorker(config, self)
        self._publer.updated.connect(self._on_publer)
        self._publer.failed.connect(self.publer.set_error)

        from PySide6.QtCore import QTimer

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()

    def start_workers(self) -> None:
        self._pulse.start()
        self._scanner.start()
        self._remote.start()
        self._publer.start()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._layout_overlay()
        if not self._windowed:
            self.showFullScreen()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._layout_overlay()

    def _layout_overlay(self) -> None:
        margin = 40
        self.overlay.setGeometry(
            margin,
            margin,
            max(200, self.width() - margin * 2),
            max(200, int(self.height() * 0.62)),
        )

    def _tick_clock(self) -> None:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo("America/Indiana/Indianapolis"))
        self.clock.setText(now.strftime("%a %b %d · %H:%M:%S"))

    def _on_activity(self, snapshot: ActivitySnapshot) -> None:
        self.activity.update_snapshot(snapshot)

    def _on_addresses(self, hits: list[AddressHit]) -> None:
        if hits:
            self.overlay.enqueue(hits)

    def _on_scanner(self, health: ScannerHealth) -> None:
        self.health.update_scanner(health)

    def _on_remote(self, health: RemoteHealth) -> None:
        self.health.update_remote(health)

    def _on_publer(self, posts: list[PublerPost]) -> None:
        self.publer.update_posts(posts)

    def closeEvent(self, event) -> None:  # noqa: N802
        for worker in (self._pulse, self._scanner, self._remote, self._publer):
            worker.stop()
            worker.wait(3000)
        super().closeEvent(event)
