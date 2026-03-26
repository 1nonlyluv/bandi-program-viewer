import unittest
from pathlib import Path

from program_schedule_normalizer import normalize_payload
from program_schedule_parser import derive_year, parse_common_entry, parse_day_header, parse_program_cell, parse_program_sheet


class ProgramScheduleParserHelpersTests(unittest.TestCase):
    def test_parse_day_header(self) -> None:
        parsed = parse_day_header("3/9 강당:김은비", 2026)
        self.assertEqual(parsed["date"], "2026-03-09")
        self.assertEqual(parsed["venueManager"], "김은비")

    def test_derive_year_from_filename(self) -> None:
        self.assertEqual(derive_year("주간프로그램 계획표(2026-1).xlsx"), 2026)

    def test_parse_standard_program_cell(self) -> None:
        parsed = parse_program_cell("종이접기(인지)\n나는낭만고양이\n(믿음반)\n준비:강선진")
        self.assertEqual(parsed["title"], "종이접기")
        self.assertEqual(parsed["subtitle"], "나는낭만고양이")
        self.assertEqual(parsed["categoryId"], "cognitive")
        self.assertEqual(parsed["groupIds"], ["mideum"])
        self.assertEqual(parsed["staffRole"], "준비")
        self.assertEqual(parsed["staff"], ["강선진"])

    def test_parse_custom_program_cell(self) -> None:
        parsed = parse_program_cell("맞춤형-오감담\n단단한마음화분\n(믿음반)\n고현선강사")
        self.assertEqual(parsed["title"], "단단한마음화분")
        self.assertEqual(parsed["subtitle"], "맞춤형-오감담")
        self.assertEqual(parsed["categoryId"], "custom")
        self.assertEqual(parsed["groupIds"], ["mideum"])
        self.assertEqual(parsed["staffRole"], "강사")
        self.assertEqual(parsed["staff"], ["고현선"])

    def test_parse_category_first_program_cell(self) -> None:
        parsed = parse_program_cell("(인지)\n몇시일까요?\n(소망,사랑반)\n준비:강선진")
        self.assertEqual(parsed["title"], "몇시일까요?")
        self.assertEqual(parsed["categoryId"], "cognitive")
        self.assertEqual(parsed["groupIds"], ["somang", "sarang"])

    def test_parse_common_entry_does_not_extract_staff(self) -> None:
        parsed = parse_common_entry("오전 등원서비스/건강관리(혈압,체온체크) 담당-변해미")
        self.assertEqual(parsed["staffRole"], "")
        self.assertEqual(parsed["staff"], [])

    def test_normalize_payload_splits_collapsed_morning_block(self) -> None:
        payload = {
            "days": [
                {
                    "date": "2026-03-24",
                    "blocks": [
                        {
                            "id": "2026-03-24-1000",
                            "start": "10:00",
                            "end": "10:30",
                            "startMin": 600,
                            "endMin": 630,
                            "section": "오전",
                            "entries": [
                                {
                                    "id": "2026-03-24-1000-all",
                                    "title": "오전 등원서비스/건강관리",
                                    "subtitle": "혈압, 체온체크 / 명상의 시간(티타임) / 오전간식 / 건강체조1",
                                    "categoryId": "service",
                                    "groupIds": ["all"],
                                    "staff": ["변해미"],
                                    "staffRole": "담당",
                                    "location": "강당",
                                    "tags": [],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        normalized = normalize_payload(payload)
        starts = [block["start"] for block in normalized["days"][0]["blocks"]]
        self.assertEqual(starts, ["08:00", "09:30", "10:00", "10:10"])

    def test_normalize_payload_applies_2026_03_24_program_corrections(self) -> None:
        payload = {
            "days": [
                {
                    "date": "2026-03-24",
                    "blocks": [
                        {
                            "id": "2026-03-24-1030",
                            "start": "10:30",
                            "end": "11:30",
                            "startMin": 630,
                            "endMin": 690,
                            "section": "오전",
                            "entries": [],
                        },
                        {
                            "id": "2026-03-24-1130",
                            "start": "11:30",
                            "end": "12:40",
                            "startMin": 690,
                            "endMin": 760,
                            "section": "공통",
                            "entries": [{"id": "x", "title": "", "subtitle": "", "categoryId": "meal", "groupIds": ["all"], "staff": [], "staffRole": "", "location": "강당", "tags": []}],
                        },
                        {
                            "id": "2026-03-24-1240",
                            "start": "12:40",
                            "end": "13:40",
                            "startMin": 760,
                            "endMin": 820,
                            "section": "공통",
                            "entries": [{"id": "x2", "title": "자율시간", "subtitle": "", "categoryId": "routine", "groupIds": ["all"], "staff": [], "staffRole": "", "location": "강당", "tags": []}],
                        },
                        {
                            "id": "2026-03-24-1500",
                            "start": "15:00",
                            "end": "16:00",
                            "startMin": 900,
                            "endMin": 960,
                            "section": "오후",
                            "entries": [],
                        },
                    ],
                }
            ]
        }
        normalized = normalize_payload(payload)
        block_1030 = normalized["days"][0]["blocks"][0]
        self.assertEqual([entry["title"] for entry in block_1030["entries"]], ["재활", "꽃 타령", "농구"])
        block_1500 = normalized["days"][0]["blocks"][3]
        self.assertEqual([entry["groupIds"] for entry in block_1500["entries"]], [["sarang"], ["mideum", "somang"]])

    def test_normalize_payload_applies_2026_03_26_program_corrections(self) -> None:
        payload = {
            "days": [
                {
                    "date": "2026-03-26",
                    "weekday": "목",
                    "blocks": [
                        {
                            "id": "2026-03-26-1030",
                            "start": "10:30",
                            "end": "11:30",
                            "startMin": 630,
                            "endMin": 690,
                            "section": "오전",
                            "entries": [],
                        },
                        {
                            "id": "2026-03-26-1400",
                            "start": "14:00",
                            "end": "15:00",
                            "startMin": 840,
                            "endMin": 900,
                            "section": "오후",
                            "entries": [],
                        },
                        {
                            "id": "2026-03-26-1500",
                            "start": "15:00",
                            "end": "16:00",
                            "startMin": 900,
                            "endMin": 960,
                            "section": "오후",
                            "entries": [],
                        },
                    ],
                }
            ]
        }

        normalized = normalize_payload(payload)
        block_1030 = normalized["days"][0]["blocks"][0]
        self.assertEqual([entry["title"] for entry in block_1030["entries"]], ["재활", "알록달록 색깔고리놀이", "다트게임"])
        block_1400 = normalized["days"][0]["blocks"][1]
        self.assertEqual([entry["title"] for entry in block_1400["entries"]], ["점선따라 그리기", "요가교실", "재활"])
        block_1500 = normalized["days"][0]["blocks"][2]
        self.assertEqual([entry["groupIds"] for entry in block_1500["entries"]], [["sarang"], ["mideum", "somang"]])
        self.assertEqual([entry["title"] for entry in block_1500["entries"]], ["농구", "점선따라 그리기"])

    def test_parse_program_sheet_reads_march_week4_xlsx(self) -> None:
        workbook = Path("주간프로그램 계획표_3월4주차.xlsx")
        parsed = parse_program_sheet(workbook)
        day_0326 = next(day for day in parsed["days"] if day["date"] == "2026-03-26")
        block_1030 = next(block for block in day_0326["blocks"] if block["start"] == "10:30")
        self.assertEqual([entry["title"] for entry in block_1030["entries"]], ["재활", "알록달록 색깔고리놀이", "다트게임"])
        block_1500 = next(block for block in day_0326["blocks"] if block["start"] == "15:00")
        self.assertEqual([entry["groupIds"] for entry in block_1500["entries"]], [["sarang"], ["mideum", "somang"]])
        self.assertEqual([entry["title"] for entry in block_1500["entries"]], ["농구", "점선따라 그리기"])

        day_0323 = next(day for day in parsed["days"] if day["date"] == "2026-03-23")
        block_1400 = next(block for block in day_0323["blocks"] if block["start"] == "14:00")
        self.assertEqual(
            [entry["title"] for entry in block_1400["entries"]],
            ["재활", "예배", "다른 그림찾기", "고리던지기"],
        )


if __name__ == "__main__":
    unittest.main()
