import unittest

from src.objects.clock import Clock


class ClockTestCase(unittest.TestCase):
    def test_hour_difference(self):
        self.assertEqual(Clock("1PM") - Clock("4PM"), 3)
        self.assertEqual(Clock("12PM") - Clock("2PM"), 2)
        self.assertEqual(Clock("12AM") - Clock("1AM"), 1)


if __name__ == "__main__":
    unittest.main()
