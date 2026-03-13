import unittest
from pathlib import Path

from shuttle_schedule_parser import parse_schedule


ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "등송영표_sample.xlsx"


class ShuttleScheduleParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parsed = parse_schedule(SAMPLE)
        cls.vehicles = {vehicle["vehicle_name"]: vehicle for vehicle in cls.parsed["vehicles"]}

    def test_vehicle_headers_and_metadata(self) -> None:
        self.assertEqual(list(self.vehicles), ["1호차", "2호차", "3호차", "4호차", "5호차", "7호차"])
        self.assertEqual(self.vehicles["1호차"]["display_name"], "1호차(716호1749)")
        self.assertEqual(self.vehicles["3호차"]["insurance_company"], "KB손해보험")
        self.assertEqual(self.vehicles["5호차"]["insurance_phone"], "1588-5656")
        self.assertEqual(self.vehicles["7호차"]["vehicle_number"], "163하3128")

    def test_top_level_metadata(self) -> None:
        self.assertEqual(self.parsed["sheet_name"], "등송영표 (2.13)")
        self.assertEqual(self.parsed["operation_order"], ["3", "1", "4", "5", "2"])
        self.assertEqual(self.parsed["dropoff_departure_minutes"], [28, 29, 30, 31, 32])
        self.assertEqual(self.parsed["dropoff_departure_base_time"], "16:29")
        self.assertEqual(self.parsed["totals"], {"pickup": 52, "dropoff": 52})

    def test_vehicle_round_splitting(self) -> None:
        vehicle1 = self.vehicles["1호차"]
        self.assertEqual(vehicle1["pickup_count"], 8)
        self.assertEqual(vehicle1["dropoff_count"], 9)
        self.assertEqual(len(vehicle1["pickup_rounds"]), 2)
        self.assertEqual(len(vehicle1["dropoff_rounds"]), 2)
        self.assertEqual(vehicle1["pickup_rounds"][0]["entries"][0]["name"], "문필남")
        self.assertEqual(vehicle1["pickup_rounds"][1]["entries"][0]["name"], "조정아")

    def test_ignores_vehicle_number_cells_and_6th_car(self) -> None:
        vehicle4 = self.vehicles["4호차"]
        self.assertEqual(vehicle4["vehicle_number"], "76호5003")
        self.assertNotIn("6호차", self.vehicles)

    def test_merged_cell_address_propagation(self) -> None:
        vehicle7 = self.vehicles["7호차"]
        last_round_entries = vehicle7["pickup_rounds"][-1]["entries"]
        self.assertEqual(last_round_entries[1]["name"], "최봉학")
        self.assertEqual(last_round_entries[2]["name"], "김영옥")
        self.assertEqual(last_round_entries[1]["address"], "교동마을 신창A 103/1403")
        self.assertEqual(last_round_entries[2]["address"], "교동마을 신창A 103/1403")

    def test_self_transport_and_long_term_absence_sections(self) -> None:
        self.assertEqual(self.parsed["self_pickup"]["entries"][0]["name"], "차의로")
        self.assertEqual(self.parsed["self_pickup"]["entries"][0]["time"], "자가")
        self.assertEqual(self.parsed["self_dropoff"]["entries"][1]["name"], "이기본")
        self.assertEqual(self.parsed["long_term_absences"][0]["name"], "이건희")
        self.assertEqual(self.parsed["long_term_absences"][-1]["name"], "박수암")

    def test_emphasis_detection(self) -> None:
        vehicle2 = self.vehicles["2호차"]
        highlighted_pickup = vehicle2["pickup_rounds"][0]["entries"][0]
        self.assertTrue(highlighted_pickup["emphasis"])
        self.assertIn("H", highlighted_pickup["emphasis_columns"])


if __name__ == "__main__":
    unittest.main()
