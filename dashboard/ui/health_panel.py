"""Health monitor panels (Piece 3)."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from models import ProbeResult, RemoteHealth, ScannerHealth

LOCAL_TZ = ZoneInfo("America/Indiana/Indianapolis")


def _age_text(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    rem = seconds % 60
    if minutes < 60:
        return f"{minutes}m {rem}s ago"
    hours = minutes // 60
    return f"{hours}h {minutes % 60}m ago"


class ProbeRow(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.name = QLabel("")
        self.name.setObjectName("Meta")
        self.status = QLabel("—")
        self.status.setObjectName("StatusUNKNOWN")
        self.detail = QLabel("")
        self.detail.setObjectName("HealthDetail")
        self.detail.setWordWrap(True)
        layout.addWidget(self.name, stretch=0)
        layout.addWidget(self.status, stretch=0)
        layout.addWidget(self.detail, stretch=1)

    def set_probe(self, probe: ProbeResult) -> None:
        self.name.setText(probe.name)
        self.status.setText(probe.status.value)
        self.status.setObjectName(f"Status{probe.status.value}")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.detail.setText(probe.detail)


class HealthPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        title = QLabel("Health")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        columns = QHBoxLayout()
        columns.setSpacing(10)

        self.scanner_frame = QFrame()
        self.scanner_frame.setObjectName("Panel")
        scanner_layout = QVBoxLayout(self.scanner_frame)
        scanner_layout.setContentsMargins(12, 12, 12, 12)
        scanner_layout.setSpacing(6)
        scanner_layout.addWidget(self._subtitle("Scanner database"))
        self.scanner_status = QLabel("UNKNOWN")
        self.scanner_status.setObjectName("StatusUNKNOWN")
        scanner_layout.addWidget(self.scanner_status)
        self.scanner_talkgroup = QLabel("Last talkgroup: —")
        self.scanner_talkgroup.setObjectName("HealthDetail")
        self.scanner_talkgroup.setWordWrap(True)
        scanner_layout.addWidget(self.scanner_talkgroup)
        self.scanner_age = QLabel("Last call: —")
        self.scanner_age.setObjectName("HealthDetail")
        scanner_layout.addWidget(self.scanner_age)
        self.scanner_error = QLabel("")
        self.scanner_error.setObjectName("Meta")
        self.scanner_error.setWordWrap(True)
        scanner_layout.addWidget(self.scanner_error)
        scanner_layout.addStretch(1)
        columns.addWidget(self.scanner_frame, stretch=1)

        self.remote_frame = QFrame()
        self.remote_frame.setObjectName("Panel")
        remote_layout = QVBoxLayout(self.remote_frame)
        remote_layout.setContentsMargins(12, 12, 12, 12)
        remote_layout.setSpacing(6)
        remote_layout.addWidget(self._subtitle("SDR / ThinLine host"))
        self.remote_overall = QLabel("UNKNOWN")
        self.remote_overall.setObjectName("StatusUNKNOWN")
        remote_layout.addWidget(self.remote_overall)
        self.host_row = ProbeRow()
        self.tlr_row = ProbeRow()
        self.pg_row = ProbeRow()
        remote_layout.addWidget(self.host_row)
        remote_layout.addWidget(self.tlr_row)
        remote_layout.addWidget(self.pg_row)
        remote_layout.addStretch(1)
        columns.addWidget(self.remote_frame, stretch=1)

        root.addLayout(columns, stretch=1)

    @staticmethod
    def _subtitle(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("SectionSub")
        return lbl

    def update_scanner(self, health: ScannerHealth) -> None:
        status = health.status
        self.scanner_status.setText(status.value)
        self.scanner_status.setObjectName(f"Status{status.value}")
        self.scanner_status.style().unpolish(self.scanner_status)
        self.scanner_status.style().polish(self.scanner_status)

        tg = health.talkgroup_label or health.talkgroup_name or "—"
        system = health.system_label or (
            f"systemRef {health.system_ref}" if health.system_ref is not None else "—"
        )
        self.scanner_talkgroup.setText(f"Last talkgroup: {tg}\nSystem: {system}")

        if health.last_call_at:
            local = health.last_call_at.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
            self.scanner_age.setText(
                f"Last call: {local} ({_age_text(health.age_seconds)})"
            )
        else:
            self.scanner_age.setText("Last call: —")
        self.scanner_error.setText(health.error or "")

    def update_remote(self, health: RemoteHealth) -> None:
        overall = health.overall
        self.remote_overall.setText(overall.value)
        self.remote_overall.setObjectName(f"Status{overall.value}")
        self.remote_overall.style().unpolish(self.remote_overall)
        self.remote_overall.style().polish(self.remote_overall)
        self.host_row.set_probe(health.host_probe)
        self.tlr_row.set_probe(health.tlr_probe)
        self.pg_row.set_probe(health.postgres_probe)
