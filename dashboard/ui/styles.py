"""Shared stylesheet tokens for the vertical kiosk."""

STYLESHEET = """
QWidget#Root {
    background-color: #0b1218;
    color: #e8eef4;
    font-family: "Segoe UI", "Helvetica Neue", sans-serif;
}

QLabel#Brand {
    color: #7fd0ff;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: 2px;
}

QLabel#SectionTitle {
    color: #f2f6fa;
    font-size: 26px;
    font-weight: 700;
}

QLabel#SectionSub {
    color: #9aabba;
    font-size: 15px;
}

QFrame#Panel {
    background-color: #121c26;
    border: 1px solid #1f3040;
    border-radius: 10px;
}

QLabel#Meta {
    color: #8fa3b5;
    font-size: 13px;
}

QLabel#CallSystem {
    color: #7fd0ff;
    font-size: 14px;
    font-weight: 600;
}

QLabel#CallTalkgroup {
    color: #f0f4f8;
    font-size: 16px;
    font-weight: 700;
}

QLabel#CallTranscript {
    color: #d5dde6;
    font-size: 14px;
}

QLabel#BadgeTone {
    color: #ffb454;
    font-size: 12px;
    font-weight: 700;
}

QLabel#StatusOK {
    color: #3dde8c;
    font-size: 22px;
    font-weight: 800;
}

QLabel#StatusDEGRADED {
    color: #ffb454;
    font-size: 22px;
    font-weight: 800;
}

QLabel#StatusDOWN, QLabel#StatusUNKNOWN {
    color: #ff5e6c;
    font-size: 22px;
    font-weight: 800;
}

QLabel#HealthDetail {
    color: #c7d3de;
    font-size: 14px;
}

QLabel#PublerText {
    color: #e8eef4;
    font-size: 14px;
}

QLabel#PublerMeta {
    color: #8fa3b5;
    font-size: 12px;
}

QFrame#Overlay {
    background-color: rgba(6, 10, 14, 230);
    border: 2px solid #2b4b66;
    border-radius: 14px;
}

QLabel#OverlayTitle {
    color: #7fd0ff;
    font-size: 22px;
    font-weight: 800;
}

QLabel#OverlayAddress {
    color: #ffffff;
    font-size: 20px;
    font-weight: 700;
}

QLabel#OverlaySnippet {
    color: #c7d3de;
    font-size: 14px;
}

QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    background: #0b1218;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2a3d50;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""
