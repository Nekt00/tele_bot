import unittest

from app.utils.deep_links import create_quiz_payload, parse_quiz_payload


class DeepLinkTests(unittest.TestCase):
    def test_round_trip_and_telegram_length_limit(self):
        payload = create_quiz_payload(9_999_999_999, -1_000_000_000_000, "secret")

        self.assertLessEqual(len(payload), 64)
        self.assertEqual(
            parse_quiz_payload(payload, "secret"),
            (9_999_999_999, -1_000_000_000_000),
        )

    def test_tampering_and_wrong_secret_are_rejected(self):
        payload = create_quiz_payload(42, -1001, "secret")

        self.assertIsNone(parse_quiz_payload(payload.replace("-1001", "-1002"), "secret"))
        self.assertIsNone(parse_quiz_payload(payload, "another-secret"))
        self.assertIsNone(parse_quiz_payload("q_invalid", "secret"))
