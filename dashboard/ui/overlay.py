"""Address map + Street View overlay (Piece 2)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models import AddressHit


class AddressOverlay(QFrame):
    dismissed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Overlay")
        self.setVisible(False)
        self._queue: list[AddressHit] = []
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._advance)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Address detected")
        title.setObjectName("OverlayTitle")
        header.addWidget(title)
        header.addStretch(1)
        close_btn = QPushButton("Dismiss")
        close_btn.clicked.connect(self._advance)
        header.addWidget(close_btn)
        layout.addLayout(header)

        self.address = QLabel("")
        self.address.setObjectName("OverlayAddress")
        self.address.setWordWrap(True)
        layout.addWidget(self.address)

        self.meta = QLabel("")
        self.meta.setObjectName("Meta")
        self.meta.setWordWrap(True)
        layout.addWidget(self.meta)

        images = QHBoxLayout()
        images.setSpacing(12)
        self.map_label = QLabel("Map unavailable")
        self.map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_label.setMinimumSize(320, 320)
        self.map_label.setStyleSheet("background:#0f1822; border-radius:8px;")
        self.sv_label = QLabel("Street View unavailable")
        self.sv_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sv_label.setMinimumSize(320, 320)
        self.sv_label.setStyleSheet("background:#0f1822; border-radius:8px;")
        images.addWidget(self.map_label, stretch=1)
        images.addWidget(self.sv_label, stretch=1)
        layout.addLayout(images, stretch=1)

        self.snippet = QLabel("")
        self.snippet.setObjectName("OverlaySnippet")
        self.snippet.setWordWrap(True)
        layout.addWidget(self.snippet)

        self._overlay_seconds = 25

    def set_overlay_seconds(self, seconds: int) -> None:
        self._overlay_seconds = max(5, seconds)

    def enqueue(self, hits: list[AddressHit]) -> None:
        self._queue.extend(hits)
        if not self.isVisible():
            self._show_next()

    def _show_next(self) -> None:
        if not self._queue:
            self.hide()
            self.dismissed.emit()
            return
        hit = self._queue.pop(0)
        self.address.setText(hit.formatted_address)
        self.meta.setText(
            f"{hit.system_label} · {hit.talkgroup_label} · call {hit.call_id}"
        )
        self.snippet.setText(hit.transcript_snippet)
        self._set_image(self.map_label, hit.map_path, "Map unavailable")
        self._set_image(self.sv_label, hit.streetview_path, "Street View unavailable")
        self.show()
        self.raise_()
        self._timer.start(self._overlay_seconds * 1000)

    @staticmethod
    def _set_image(label: QLabel, path: str | None, fallback: str) -> None:
        if path:
            pix = QPixmap(path)
            if not pix.isNull():
                label.setPixmap(
                    pix.scaled(
                        480,
                        480,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return
        label.setPixmap(QPixmap())
        label.setText(fallback)

    def _advance(self) -> None:
        self._timer.stop()
        self._show_next()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._advance()
        super().mousePressEvent(event)
