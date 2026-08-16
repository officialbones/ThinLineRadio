"""Publer last-posts panel (Piece 4)."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from models import PublerPost

LOCAL_TZ = ZoneInfo("America/Indiana/Indianapolis")


class PublerCard(QFrame):
    def __init__(self, post: PublerPost, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        if post.thumbnail_url:
            thumb = QLabel()
            thumb.setFixedSize(72, 72)
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb.setStyleSheet("background:#1a2836; border-radius:6px;")
            # Thumbnail URL is shown as placeholder; full download kept optional.
            thumb.setText("IMG")
            thumb.setObjectName("Meta")
            layout.addWidget(thumb)

        col = QVBoxLayout()
        col.setSpacing(4)
        text = post.text or "(no text)"
        if len(text) > 180:
            text = text[:177] + "…"
        body = QLabel(text)
        body.setObjectName("PublerText")
        body.setWordWrap(True)
        col.addWidget(body)

        networks = ", ".join(post.networks) if post.networks else "—"
        when = "—"
        if post.when:
            when = post.when.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
        accounts = ", ".join(post.account_names[:2]) if post.account_names else ""
        meta_bits = [networks, when]
        if accounts:
            meta_bits.append(accounts)
        meta = QLabel(" · ".join(meta_bits))
        meta.setObjectName("PublerMeta")
        meta.setWordWrap(True)
        col.addWidget(meta)
        layout.addLayout(col, stretch=1)


class PublerPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Last 3 Publer posts")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.meta = QLabel("Waiting…")
        self.meta.setObjectName("SectionSub")
        header.addWidget(self.meta)
        root.addLayout(header)

        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(8)
        root.addLayout(self.list_layout)
        root.addStretch(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_error(self, message: str) -> None:
        self.meta.setText(message)

    def update_posts(self, posts: list[PublerPost]) -> None:
        self.meta.setText(f"{len(posts)} shown")
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not posts:
            empty = QLabel("No published posts returned.")
            empty.setObjectName("Meta")
            self.list_layout.addWidget(empty)
            return
        for post in posts:
            self.list_layout.addWidget(PublerCard(post))
