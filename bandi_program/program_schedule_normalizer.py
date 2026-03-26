from __future__ import annotations

import copy
from typing import Any


def _make_entry(
    entry_id: str,
    title: str,
    subtitle: str,
    category_id: str,
    group_ids: list[str],
    *,
    staff: list[str] | None = None,
    staff_role: str = "",
) -> dict[str, Any]:
    return {
        "id": entry_id,
        "title": title,
        "subtitle": subtitle,
        "categoryId": category_id,
        "groupIds": group_ids,
        "staff": staff or [],
        "staffRole": staff_role,
        "location": "강당",
        "tags": [title] + group_ids + [category_id],
    }


def _replace_text(value: str) -> str:
    text = str(value or "").strip()
    replacements = {
        "등영서비스": "등원서비스",
        "등원서비스": "등원 서비스",
        "송영준비": "송영 준비",
        "송영서비스": "송영 서비스",
        "담당-": "담당: ",
        "준비-": "준비: ",
        "진행-": "진행: ",
        "점심식사 준비": "점심 식사 준비",
        "저녁식사": "저녁 식사",
        "오전간식": "오전 간식",
        "오후간식": "오후 간식",
        "블록개수": "블록 개수",
        "그림찾기": "그림 찾기",
        "혈압,체온체크": "혈압, 체온 체크",
        "혈압, 체온체크": "혈압, 체온 체크",
        "체온체크": "체온 체크",
        "식사준비": "식사 준비",
        "개인위생": "개인 위생",
        "강당담당": "강당 담당",
        "재활-": "재활: ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(entry)
    normalized["title"] = _replace_text(normalized.get("title", ""))
    normalized["subtitle"] = _replace_text(normalized.get("subtitle", ""))
    return normalized


def _normalize_morning_block(day: dict[str, Any]) -> None:
    blocks = day.get("blocks", [])
    if not blocks:
        return
    first = blocks[0]
    entries = first.get("entries", [])
    if (
        first.get("start") != "10:00"
        or first.get("end") != "10:30"
        or not entries
        or entries[0].get("title") not in ("오전 등원서비스/건강관리", "오전 등영서비스/건강관리")
        or "명상의 시간" not in str(entries[0].get("subtitle", ""))
    ):
        return

    morning_staff = list(entries[0].get("staff", []))
    morning_role = entries[0].get("staffRole", "")
    date = day["date"]

    replacement = [
        {
            "id": f"{date}-0800",
            "start": "08:00",
            "end": "09:30",
            "startMin": 480,
            "endMin": 570,
            "section": first.get("section", "오전"),
            "entries": [
                _make_entry(
                    f"{date}-0800-all",
                    "오전 등원서비스/건강관리",
                    "혈압, 체온 체크",
                    "service",
                    ["all"],
                )
            ],
        },
        {
            "id": f"{date}-0930",
            "start": "09:30",
            "end": "10:00",
            "startMin": 570,
            "endMin": 600,
            "section": first.get("section", "오전"),
            "entries": [
                _make_entry(
                    f"{date}-0930-all",
                    "명상의 시간",
                    "티타임",
                    "routine",
                    ["all"],
                )
            ],
        },
        {
            "id": f"{date}-1000",
            "start": "10:00",
            "end": "10:10",
            "startMin": 600,
            "endMin": 610,
            "section": first.get("section", "오전"),
            "entries": [
                _make_entry(
                    f"{date}-1000-all",
                    "오전 간식",
                    "",
                    "routine",
                    ["all"],
                )
            ],
        },
        {
            "id": f"{date}-1010",
            "start": "10:10",
            "end": "10:30",
            "startMin": 610,
            "endMin": 630,
            "section": first.get("section", "오전"),
            "entries": [
                _make_entry(
                    f"{date}-1010-all",
                    "건강체조1",
                    "",
                    "physical",
                    ["all"],
                    staff=morning_staff,
                    staff_role=morning_role,
                )
            ],
        },
    ]
    day["blocks"] = replacement + blocks[1:]


def _normalize_day_text(day: dict[str, Any]) -> None:
    for block in day.get("blocks", []):
        for entry in block.get("entries", []):
            entry.update(_normalize_entry(entry))


def _normalize_fixed_blocks(day: dict[str, Any]) -> None:
    blocks_by_start = {block.get("start"): block for block in day.get("blocks", [])}

    block_1130 = blocks_by_start.get("11:30")
    if block_1130:
        block_1130["start"] = "11:30"
        block_1130["end"] = "12:30"
        block_1130["startMin"] = 690
        block_1130["endMin"] = 750
        block_1130["id"] = f"{day['date']}-1130"

    block_1230 = blocks_by_start.get("12:30")
    if block_1230:
        block_1230["start"] = "12:30"
        block_1230["end"] = "13:30"
        block_1230["startMin"] = 750
        block_1230["endMin"] = 810
        block_1230["id"] = f"{day['date']}-1230"

    block_1240 = blocks_by_start.get("12:40")
    if block_1240:
        block_1240["start"] = "12:30"
        block_1240["end"] = "13:30"
        block_1240["startMin"] = 750
        block_1240["endMin"] = 810
        block_1240["id"] = f"{day['date']}-1230"

    block_0930 = blocks_by_start.get("09:30")
    if block_0930 and block_0930.get("entries"):
        entry = block_0930["entries"][0]
        entry["title"] = "명상의 시간/티타임"
        entry["subtitle"] = ""

    block_1010 = blocks_by_start.get("10:10")
    if block_1010 and block_1010.get("entries"):
        entry = block_1010["entries"][0]
        staff = list(entry.get("staff", []))
        if not staff and "담당:" in str(entry.get("title", "")):
            staff = [str(entry["title"]).split("담당:", 1)[1].strip()]
        entry["title"] = "건강체조1"
        entry["subtitle"] = ""
        entry["staff"] = staff
        entry["staffRole"] = "담당" if staff else ""

    block_1340 = blocks_by_start.get("13:40")
    if block_1340 and block_1340.get("entries"):
        staff: list[str] = []
        for item in block_1340["entries"]:
            if item.get("staff"):
                staff = list(item.get("staff", []))
                break
            if "담당:" in str(item.get("title", "")):
                staff = [str(item["title"]).split("담당:", 1)[1].strip()]
                break
        block_1340["start"] = "13:40"
        block_1340["end"] = "14:00"
        block_1340["startMin"] = 820
        block_1340["endMin"] = 840
        block_1340["id"] = f"{day['date']}-1340"
        block_1340["entries"] = [
            _make_entry(
                f"{day['date']}-1340-1",
                "건강체조2",
                "",
                "physical",
                ["all"],
                staff=staff,
                staff_role="담당" if staff else "",
            ),
        ]

        snack_exists = any(block.get("start") == "13:30" for block in day.get("blocks", []))
        if not snack_exists:
            afternoon_snack_block = {
                "id": f"{day['date']}-1330",
                "start": "13:30",
                "end": "13:40",
                "startMin": 810,
                "endMin": 820,
                "section": block_1340.get("section", "오후"),
                "entries": [
                    _make_entry(
                        f"{day['date']}-1330-1",
                        "오후 간식",
                        "",
                        "routine",
                        ["all"],
                    )
                ],
            }
            blocks = day.get("blocks", [])
            insert_at = blocks.index(block_1340)
            blocks.insert(insert_at, afternoon_snack_block)


def _apply_2026_03_24_corrections(day: dict[str, Any]) -> None:
    if day.get("date") != "2026-03-24":
        return

    blocks_by_start = {block.get("start"): block for block in day.get("blocks", [])}

    block_1030 = blocks_by_start.get("10:30")
    if block_1030:
        block_1030["entries"] = [
            _make_entry("2026-03-24-1030-1", "재활", "", "rehab", ["sarang"]),
            _make_entry("2026-03-24-1030-2", "꽃 타령", "맞춤형-소리담", "custom", ["mideum"], staff=["김소정"], staff_role="강사"),
            _make_entry("2026-03-24-1030-3", "농구", "", "physical", ["somang"]),
        ]

    block_1130 = blocks_by_start.get("11:30")
    if block_1130 and block_1130.get("entries"):
        block_1130["entries"][0]["title"] = "점심 식사 준비"
        block_1130["entries"][0]["subtitle"] = "식사 준비/투약 및 개인 위생, 체온 체크"
        block_1130["entries"][0]["staff"] = []
        block_1130["entries"][0]["staffRole"] = ""

    block_1240 = blocks_by_start.get("12:40")
    if block_1240 and block_1240.get("entries"):
        block_1240["entries"][0]["subtitle"] = "재활: 믿음반/강당 담당: 사랑반"

    block_1500 = blocks_by_start.get("15:00")
    if block_1500:
        block_1500["entries"] = [
            _make_entry("2026-03-24-1500-1", "핸드골프", "", "physical", ["sarang"]),
            _make_entry(
                "2026-03-24-1500-2",
                "블록 개수 세기",
                "",
                "cognitive",
                ["mideum", "somang"],
                staff=["김은비"],
                staff_role="준비",
            ),
        ]

    block_1600 = blocks_by_start.get("16:00")
    if block_1600 and block_1600.get("entries"):
        block_1600["entries"][0]["title"] = "저녁 식사"
        block_1600["entries"][0]["subtitle"] = ""

    block_1700 = blocks_by_start.get("17:00")
    if block_1700 and block_1700.get("entries"):
        block_1700["entries"][0]["subtitle"] = ""


def _apply_2026_03_26_corrections(day: dict[str, Any]) -> None:
    if day.get("date") != "2026-03-26":
        return

    blocks_by_start = {block.get("start"): block for block in day.get("blocks", [])}

    block_1030 = blocks_by_start.get("10:30")
    if block_1030:
        block_1030["entries"] = [
            _make_entry("2026-03-26-1030-1", "재활", "", "rehab", ["sarang"]),
            _make_entry(
                "2026-03-26-1030-2",
                "알록달록 색깔고리놀이",
                "맞춤형-인지담",
                "custom",
                ["mideum"],
                staff=["김소정"],
                staff_role="강사",
            ),
            _make_entry("2026-03-26-1030-3", "다트게임", "", "physical", ["somang"]),
        ]

    block_1400 = blocks_by_start.get("14:00")
    if block_1400:
        block_1400["entries"] = [
            _make_entry("2026-03-26-1400-1", "재활", "", "rehab", ["somang"]),
            _make_entry("2026-03-26-1400-2", "점선따라 그리기", "", "cognitive", ["sarang"], staff=["김은비"], staff_role="준비"),
            _make_entry("2026-03-26-1400-3", "요가교실", "", "physical", ["mideum"], staff=["김은비"], staff_role="진행"),
        ]

    block_1500 = blocks_by_start.get("15:00")
    if block_1500:
        block_1500["entries"] = [
            _make_entry("2026-03-26-1500-1", "농구", "", "physical", ["sarang"]),
            _make_entry(
                "2026-03-26-1500-2",
                "점선따라 그리기",
                "",
                "cognitive",
                ["mideum", "somang"],
                staff=["김은비"],
                staff_role="준비",
            ),
        ]


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(payload)
    for day in normalized.get("days", []):
        _normalize_morning_block(day)
        _normalize_day_text(day)
        _normalize_fixed_blocks(day)
        _apply_2026_03_24_corrections(day)
        _apply_2026_03_26_corrections(day)
        _normalize_day_text(day)
    return normalized
