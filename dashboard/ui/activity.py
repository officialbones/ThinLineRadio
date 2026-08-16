"""Activity feed panel (Piece 1)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from models import ActivitySnapshot, Transcription

LOCAL_TZ = ZoneInfo("America/Indiana/Indianapolis")


def _fmt_time(ts: datetime | None) -> str:
    if ts is None:
        return "—"
    return ts.astimezone(LOCAL_TZ).strftime("%H:%M:%S")


class CallCard(QFrame):
    def __init__(self, row: Transcription, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        top = QHBoxLayout()
        system = QLabel(row.system_label or "Unknown system")
        system.setObjectName("CallSystem")
        top.addWidget(system)
        top.addStretch(1)
        time_lbl = QLabel(_fmt_time(row.timestamp))
        time_lbl.setObjectName("Meta")
        top.addWidget(time_lbl)
        layout.addLayout(top)

        tg = QLabel(row.talkgroup_label or f"TG {row.talkgroup_id or '—'}")
        tg.setObjectName("CallTalkgroup")
        tg.setWordWrap(True)
        layout.addWidget(tg)

        if row.has_tones or row.alert_summary:
            badge = QLabel(
                "TONES / ALERT"
                + (f" — {row.alert_summary}" if row.alert_summary else "")
            )
            badge.setObjectName("BadgeTone")
            badge.setWordWrap(True)
            layout.addWidget(badge)

        text = row.transcript or "(no transcript)"
        if len(text) > 280:
            text = text[:277] + "…"
        body = QLabel(text)
        body.setObjectName("CallTranscript")
        body.setWordWrap(True)
        layout.addWidget(body)


class ActivityPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("What’s happening")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.meta = QLabel("Waiting for first Pulse pull…")
        self.meta.setObjectName("SectionSub")
        header.addWidget(self.meta)
        root.addLayout(header)

        self.summary = QLabel("")
        self.summary.setObjectName("Meta")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.container)
        self.scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self.scroll, stretch=1)

    def set_error(self, message: str) -> None:
        self.meta.setText(f"Pulse error: {message}")

    def update_snapshot(self, snapshot: ActivitySnapshot) -> None:
        fetched = snapshot.fetched_at.astimezone(LOCAL_TZ).strftime("%H:%M:%S")
        count = len(snapshot.transcriptions)
        self.meta.setText(f"{count} calls · last pull {fetched}")

        parts: list[str] = []
        if snapshot.by_system:
            top_systems = ", ".join(
                f"{name} ({n})" for name, n in list(snapshot.by_system.items())[:5]
            )
            parts.append(f"Systems: {top_systems}")
        if snapshot.by_talkgroup:
            top_tg = ", ".join(
                f"{name} ({n})" for name, n in list(snapshot.by_talkgroup.items())[:4]
            )
            parts.append(f"Busy: {top_tg}")
        if snapshot.tone_count:
            parts.append(f"Tones/alerts: {snapshot.tone_count}")
        if snapshot.error:
            parts.append(f"Partial errors: {snapshot.error}")
        self.summary.setText("  ·  ".join(parts) if parts else "No traffic in the last 5 minutes.")

        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for row in snapshot.transcriptions[:40]:
            self.list_layout.addWidget(CallCard(row))
        self.list_layout.addStretch(1)
