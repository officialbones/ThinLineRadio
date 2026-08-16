"""Background QThreads for Pulse, health, remote probes, and Publer."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from address import find_new_address_hits
from config import Config
from health import check_remote_health, check_scanner_health
from publer import fetch_recent_posts
from pulse import fetch_activity


class PulseWorker(QThread):
    updated = Signal(object)  # ActivitySnapshot
    addresses = Signal(object)  # list[AddressHit]
    failed = Signal(str)

    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._stop = False
        self._seen_call_ids: set[str] = set()
        self._seen_addresses: set[str] = set()
        self._prime = True

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        while not self._stop:
            try:
                snapshot = fetch_activity(self._config, window_minutes=5)
                self.updated.emit(snapshot)
                hits = find_new_address_hits(
                    self._config,
                    snapshot.transcriptions,
                    self._seen_call_ids,
                    self._seen_addresses,
                )
                if self._prime:
                    # First poll: seed seen sets without flooding the overlay.
                    self._prime = False
                elif hits:
                    self.addresses.emit(hits)
            except Exception as exc:  # noqa: BLE001
                self.failed.emit(str(exc))
            self._interruptible_sleep(self._config.pulse_poll_seconds)

    def _interruptible_sleep(self, seconds: int) -> None:
        # Wake often so stop() is responsive.
        remaining = max(1, int(seconds))
        while remaining > 0 and not self._stop:
            chunk = min(1, remaining)
            self.msleep(chunk * 1000)
            remaining -= chunk


class ScannerHealthWorker(QThread):
    updated = Signal(object)  # ScannerHealth

    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        while not self._stop:
            result = check_scanner_health(self._config)
            self.updated.emit(result)
            self._interruptible_sleep(self._config.health_poll_seconds)

    def _interruptible_sleep(self, seconds: int) -> None:
        remaining = max(1, int(seconds))
        while remaining > 0 and not self._stop:
            chunk = min(1, remaining)
            self.msleep(chunk * 1000)
            remaining -= chunk


class RemoteHealthWorker(QThread):
    updated = Signal(object)  # RemoteHealth

    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        while not self._stop:
            result = check_remote_health(self._config)
            self.updated.emit(result)
            self._interruptible_sleep(self._config.health_poll_seconds)

    def _interruptible_sleep(self, seconds: int) -> None:
        remaining = max(1, int(seconds))
        while remaining > 0 and not self._stop:
            chunk = min(1, remaining)
            self.msleep(chunk * 1000)
            remaining -= chunk


class PublerWorker(QThread):
    updated = Signal(object)  # list[PublerPost]
    failed = Signal(str)

    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        while not self._stop:
            posts, error = fetch_recent_posts(self._config, limit=3)
            if error and not posts:
                self.failed.emit(error)
            else:
                self.updated.emit(posts)
                if error:
                    self.failed.emit(error)
            self._interruptible_sleep(self._config.publer_poll_seconds)

    def _interruptible_sleep(self, seconds: int) -> None:
        remaining = max(1, int(seconds))
        while remaining > 0 and not self._stop:
            chunk = min(1, remaining)
            self.msleep(chunk * 1000)
            remaining -= chunk
