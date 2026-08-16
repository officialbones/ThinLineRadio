"""Lightweight tests that do not require a display."""

from __future__ import annotations

import unittest

from address import extract_addresses
from models import Transcription, parse_timestamp


class AddressExtractTests(unittest.TestCase):
    def test_house_number(self) -> None:
        hits = extract_addresses("ENGINE 3 RESPOND TO 123 MAIN STREET FOR A FIRE ALARM")
        self.assertTrue(any("123 MAIN STREET" in h.upper() for h in hits))

    def test_intersection(self) -> None:
        hits = extract_addresses("UNITS AT MAIN STREET AND OAK AVENUE")
        self.assertTrue(hits)


class TimestampTests(unittest.TestCase):
    def test_ms(self) -> None:
        ts = parse_timestamp(1_700_000_000_000)
        self.assertIsNotNone(ts)
        self.assertEqual(ts.tzinfo is not None, True)

    def test_transcription_from_api(self) -> None:
        row = Transcription.from_api(
            {
                "callId": "99",
                "systemId": 11,
                "systemLabel": "Jay",
                "talkgroupLabel": "Fire Dispatch",
                "timestamp": 1700000000,
                "transcript": "TEST",
                "hasTones": True,
            }
        )
        self.assertEqual(row.call_id, "99")
        self.assertTrue(row.has_tones)


if __name__ == "__main__":
    unittest.main()
