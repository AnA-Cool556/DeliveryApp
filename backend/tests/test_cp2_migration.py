import unittest

from app.users import split_name
from scripts.traffic_gen import TrafficStats
from scripts.set_migration_phase import VALID_PHASES


class TestCP2MigrationHelpers(unittest.TestCase):
    def test_split_name(self) -> None:
        self.assertEqual(split_name("John Doe"), ("John", "Doe"))
        self.assertEqual(split_name("Madonna"), ("Madonna", ""))
        self.assertEqual(split_name("John Middle Doe"), ("John", "Middle Doe"))
        self.assertEqual(split_name("   Alice   Smith   "), ("Alice", "Smith"))
        self.assertEqual(split_name(""), ("", ""))
        self.assertEqual(split_name("   "), ("", ""))

    def test_valid_phases(self) -> None:
        expected = {"expand", "dual_write", "backfill", "switch_read", "contract"}
        self.assertEqual(VALID_PHASES, expected)

    def test_traffic_stats_recording(self) -> None:
        stats = TrafficStats()
        stats.record(status_code=200, latency_ms=10.0, has_missing_field=False)
        stats.record(status_code=201, latency_ms=20.0, has_missing_field=False)
        stats.record(status_code=404, latency_ms=15.0, has_missing_field=False)
        stats.record(status_code=500, latency_ms=100.0, has_missing_field=False)

        self.assertEqual(stats.total, 4)
        self.assertEqual(stats.status_2xx, 2)
        self.assertEqual(stats.status_4xx, 1)
        self.assertEqual(stats.status_5xx, 1)
        self.assertEqual(stats.missing_fields, 0)

    def test_traffic_stats_percentiles(self) -> None:
        stats = TrafficStats()
        for i in range(1, 101):
            stats.record(status_code=200, latency_ms=float(i), has_missing_field=False)

        self.assertAlmostEqual(stats.p(50), 50.5, delta=1.0)
        self.assertAlmostEqual(stats.p(90), 90.1, delta=1.0)
        self.assertAlmostEqual(stats.p(99), 99.01, delta=1.0)


if __name__ == "__main__":
    unittest.main()
