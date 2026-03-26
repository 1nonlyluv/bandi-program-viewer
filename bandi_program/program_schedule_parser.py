from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from shuttle_schedule_parser import XlsxSheet, normalize_text, workbook_sheet_refs


CATEGORY_MAP = {
    "신체": "physical",
    "인지": "cognitive",
    "재활": "rehab",
    "사회적응": "social",
}
GROUP_MAP = {
    "사랑": "sarang",
    "사랑반": "sarang",
    "믿음": "mideum",
    "믿음반": "mideum",
    "소망": "somang",
    "소망반": "somang",
    "전체": "all",
}


def collapse_spaces(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value.strip())


def normalize_line(value: str) -> str:
    return collapse_spaces(value.replace("\xa0", " "))


def column_letter_to_number(value: str) -> int:
    number = 0
    for char in value:
        number = number * 26 + ord(char) - 64
    return number


def num_to_col(number: int) -> str:
    value = ""
    while number:
        number, rem = divmod(number - 1, 26)
        value = chr(65 + rem) + value
    return value


def split_cell_ref(ref: str) -> tuple[str, int]:
    match = re.fullmatch(r"([A-Z]+)(\d+)", ref)
    if not match:
        raise ValueError(f"Invalid cell reference: {ref}")
    return match.group(1), int(match.group(2))


def derive_year(path: str | Path) -> int:
    match = re.search(r"(20\d{2})", Path(path).name)
    if match:
        return int(match.group(1))
    return datetime.now().year


def normalize_week_label(value: Any) -> str:
    text = normalize_text(value).strip()
    text = text.strip("() ")
    return collapse_spaces(text)


def parse_day_header(value: str, year: int) -> dict[str, str]:
    text = normalize_line(value)
    match = re.search(r"(\d{1,2})/(\d{1,2})", text)
    if not match:
        raise ValueError(f"Unable to parse day header: {value!r}")
    month = int(match.group(1))
    day = int(match.group(2))
    manager_match = re.search(r"강당[:：]\s*([^\s]+)", text)
    manager = manager_match.group(1) if manager_match else ""
    weekday_label = ""
    return {
        "date": f"{year:04d}-{month:02d}-{day:02d}",
        "venueManager": manager,
        "weekday": weekday_label,
        "label": text,
    }


def detect_program_grid(sheet: XlsxSheet) -> tuple[int, tuple[str, ...], str, str]:
    header_row = None
    for row in range(1, min(sheet.max_row, 12) + 1):
        for col_idx in range(1, min(sheet.max_col, column_letter_to_number("J")) + 1):
            ref = f"{num_to_col(col_idx)}{row}"
            if normalize_line(normalize_text(sheet.value(ref, merged=False))) == "요일":
                header_row = row
                break
        if header_row is not None:
            break
    if header_row is None:
        raise ValueError("Unable to detect weekday header row.")

    day_columns: list[str] = []
    for col_idx in range(1, sheet.max_col + 1):
        ref = f"{num_to_col(col_idx)}{header_row}"
        text = normalize_line(normalize_text(sheet.value(ref, merged=False)))
        if re.search(r"\d{1,2}/\d{1,2}", text):
            day_columns.append(num_to_col(col_idx))
    if not day_columns:
        next_row = header_row + 1
        for col_idx in range(1, sheet.max_col + 1):
            ref = f"{num_to_col(col_idx)}{next_row}"
            text = normalize_line(normalize_text(sheet.value(ref, merged=False)))
            if re.search(r"\d{1,2}/\d{1,2}", text):
                day_columns.append(num_to_col(col_idx))
        if day_columns:
            header_row = next_row
    if not day_columns:
        raise ValueError("Unable to detect day header columns.")

    first_day_col_num = column_letter_to_number(day_columns[0])
    time_col = num_to_col(first_day_col_num - 1)
    section_col = num_to_col(first_day_col_num - 2)
    return header_row, tuple(day_columns), time_col, section_col


def detect_week_label(sheet: XlsxSheet) -> str:
    for row in range(1, min(sheet.max_row, 8) + 1):
        for col_idx in range(1, min(sheet.max_col, column_letter_to_number("J")) + 1):
            text = normalize_week_label(sheet.value(f"{num_to_col(col_idx)}{row}"))
            if "주차" in text:
                return text
    return ""


def to_weekday_label(date_text: str) -> str:
    dt = datetime.strptime(date_text, "%Y-%m-%d")
    return "월화수목금토일"[dt.weekday()]


def parse_time_rows(sheet: XlsxSheet, time_col: str) -> list[int]:
    rows: list[int] = []
    for row in range(1, sheet.max_row + 1):
        value = normalize_text(sheet.value(f"{time_col}{row}", merged=False))
        if re.fullmatch(r"\d{1,2}:\d{2}~\d{1,2}:\d{2}", value):
            rows.append(row)
    return rows


def parse_clock_range(value: str) -> tuple[str, str, int, int]:
    start_text, end_text = value.split("~", 1)
    start_minutes = parse_clock(start_text)
    end_minutes = parse_clock(end_text)
    return start_text, end_text, start_minutes, end_minutes


def parse_clock(value: str) -> int:
    hour_text, minute_text = value.split(":", 1)
    return int(hour_text) * 60 + int(minute_text)


def is_common_block(sheet: XlsxSheet, row: int, day_columns: tuple[str, ...]) -> bool:
    if not day_columns:
        return False
    parent_refs = [sheet.merged_parent.get(f"{col}{row}", f"{col}{row}") for col in day_columns]
    return len(set(parent_refs)) == 1 and parent_refs[0] == f"{day_columns[0]}{row}"


def section_for_row(sheet: XlsxSheet, row: int, section_col: str) -> str:
    return normalize_line(normalize_text(sheet.value(f"{section_col}{row}"))) or "공통"


def group_ids_from_text(text: str) -> list[str]:
    found: list[str] = []
    for token in re.findall(r"\(([^)]+)\)", text):
        normalized = token.replace(" ", "")
        if normalized in CATEGORY_MAP:
            continue
        if "강당담당" in normalized or "식사준비" in normalized or "혈압" in normalized or "체온체크" in normalized:
            continue
        parts = [part for part in re.split(r"[,/]", normalized) if part]
        for part in parts:
            if part in GROUP_MAP:
                group_id = GROUP_MAP[part]
                if group_id not in found:
                    found.append(group_id)
    return found


def category_from_text(text: str, title: str) -> str:
    compact = text.replace(" ", "")
    for token, category_id in CATEGORY_MAP.items():
        if f"({token})" in compact or compact.startswith(token):
            return category_id
    if "맞춤형-" in compact:
        return "custom"
    inferred_title = title.replace(" ", "")
    if any(keyword in inferred_title for keyword in ("식사",)):
        return "meal"
    if any(keyword in inferred_title for keyword in ("송영", "등영", "건강관리")):
        return "service"
    if any(keyword in inferred_title for keyword in ("체조", "하키", "볼링", "투호", "오자미", "요가", "워크메이트", "블랙홀", "공놀이", "농구", "핸드골프")):
        return "physical"
    if any(keyword in inferred_title for keyword in ("블록개수", "블록 개수", "다른 그림찾기", "연결하기", "미술활동")):
        return "cognitive"
    if any(keyword in inferred_title for keyword in ("예배", "봉성체", "자율시간", "간식", "명상")):
        return "routine"
    if "재활" in inferred_title:
        return "rehab"
    return "routine"


def parse_staff_line(line: str) -> tuple[str | None, list[str]]:
    clean = normalize_line(line)
    if not clean:
        return None, []
    if ":" in clean:
        role, names = clean.split(":", 1)
        staff = [collapse_spaces(item) for item in names.split(",") if collapse_spaces(item)]
        return collapse_spaces(role), staff
    if clean.endswith("강사"):
        return "강사", [collapse_spaces(clean[: -len("강사")])]
    return None, []


def strip_known_tokens(line: str) -> str:
    clean = normalize_line(line)
    clean = re.sub(r"\([^)]*(?:반|전체|신체|인지|사회적응|재활)[^)]*\)", "", clean)
    return collapse_spaces(clean)


def parse_program_cell(text: str) -> dict[str, Any]:
    raw_lines = [normalize_line(line) for line in text.splitlines() if normalize_line(line)]
    staff_role = ""
    staff: list[str] = []
    content_lines: list[str] = []

    for line in raw_lines:
        role, staff_names = parse_staff_line(line)
        if role:
            staff_role = role
            staff = staff_names
            continue
        if re.fullmatch(r"\((?:신체|인지|사회적응|재활)\)", line.replace(" ", "")):
            content_lines.append(line)
            continue
        content_lines.append(line)

    title = ""
    subtitle = ""
    category_hint_line = ""

    if not content_lines:
        title = normalize_line(text)
    elif content_lines[0].startswith("맞춤형-"):
        subtitle = content_lines[0]
        custom_lines = [strip_known_tokens(line) for line in content_lines[1:]]
        custom_lines = [line for line in custom_lines if line]
        title = " ".join(custom_lines) if custom_lines else content_lines[0].split("-", 1)[-1]
    elif content_lines[0].startswith("("):
        category_hint_line = content_lines[0]
        title = strip_known_tokens(content_lines[1] if len(content_lines) > 1 else "")
        subtitle = strip_known_tokens(content_lines[2] if len(content_lines) > 2 else "")
    else:
        title = strip_known_tokens(content_lines[0])
        if len(content_lines) > 1:
            subtitle = strip_known_tokens(content_lines[1])

    title = collapse_spaces(title) or "제목 없음"
    subtitle = collapse_spaces(subtitle)
    category_id = category_from_text("\n".join(content_lines) + "\n" + category_hint_line, title)
    group_ids = group_ids_from_text(text) or ["all"]

    return {
        "title": title,
        "subtitle": subtitle,
        "categoryId": category_id,
        "groupIds": group_ids,
        "staff": staff,
        "staffRole": staff_role,
    }


def parse_common_entry(text: str) -> dict[str, Any]:
    cleaned = normalize_line(text)
    match = re.match(r"^(.*?)\s*\((.*?)\)\s*$", cleaned)
    title = cleaned
    subtitle = ""
    if match:
        title = collapse_spaces(match.group(1))
        subtitle = collapse_spaces(match.group(2))
    category_id = category_from_text(cleaned, title)
    return {
        "title": title or cleaned,
        "subtitle": subtitle,
        "categoryId": category_id,
        "groupIds": ["all"],
        "staff": [],
        "staffRole": "",
    }


def merged_row_bounds(sheet: XlsxSheet, ref: str) -> tuple[int, int]:
    _, base_row = split_cell_ref(ref)
    min_row = base_row
    max_row = base_row
    for cell_ref, parent_ref in sheet.merged_parent.items():
        if parent_ref != ref:
            continue
        _, row = split_cell_ref(cell_ref)
        min_row = min(min_row, row)
        max_row = max(max_row, row)
    return min_row, max_row


def assign_block_row(start_row: int, end_row: int, time_rows: list[int]) -> int:
    overlapping = [row for row in time_rows if start_row <= row <= end_row]
    if overlapping:
        return overlapping[0]
    previous = [row for row in time_rows if row <= start_row]
    return previous[-1] if previous else time_rows[0]


def collect_entries_by_block(
    sheet: XlsxSheet,
    col: str,
    time_rows: list[int],
    parser,
) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    seen_refs: set[str] = set()
    for row in range(time_rows[0], sheet.max_row + 1):
        ref = f"{col}{row}"
        source_ref = sheet.merged_parent.get(ref, ref)
        source_col, source_row = split_cell_ref(source_ref)
        if source_col != col or source_ref in seen_refs:
            continue
        seen_refs.add(source_ref)
        raw = normalize_text(sheet.value(ref))
        if not raw:
            continue
        block_row = assign_block_row(*merged_row_bounds(sheet, source_ref), time_rows)
        parsed = parser(raw)
        parsed["id"] = source_ref
        grouped.setdefault(block_row, []).append((source_row, parsed))
    return {
        block_row: [parsed for _, parsed in sorted(entries, key=lambda item: item[0])]
        for block_row, entries in grouped.items()
    }


def build_flat_entries(days: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for day in days:
        for block in day["blocks"]:
            for entry in block["entries"]:
                flat.append(
                    {
                        "id": entry["id"],
                        "date": day["date"],
                        "weekday": day["weekday"],
                        "start": block["start"],
                        "end": block["end"],
                        "startMin": block["startMin"],
                        "endMin": block["endMin"],
                        "section": block["section"],
                        "title": entry["title"],
                        "subtitle": entry["subtitle"],
                        "categoryId": entry["categoryId"],
                        "groupIds": entry["groupIds"],
                        "staff": entry["staff"],
                        "staffRole": entry["staffRole"],
                        "location": entry["location"],
                        "tags": entry["tags"],
                    }
                )
    return flat


def parse_program_sheet(path: str | Path, *, sheet_name: str | None = None, sheet_path: str | None = None) -> dict[str, Any]:
    workbook = XlsxSheet(Path(path), sheet_name=sheet_name, sheet_path=sheet_path)
    year = derive_year(path)
    header_row, day_columns, time_col, section_col = detect_program_grid(workbook)
    week_label = detect_week_label(workbook)
    day_headers = [parse_day_header(normalize_text(workbook.value(f"{col}{header_row}", merged=False)), year) for col in day_columns]
    for header in day_headers:
        header["weekday"] = to_weekday_label(header["date"])

    time_rows = parse_time_rows(workbook, time_col)
    windows = []
    for index, row in enumerate(time_rows):
        next_row = time_rows[index + 1] if index + 1 < len(time_rows) else row + 1
        windows.append((row, next_row - 1))

    common_entries_by_block = collect_entries_by_block(workbook, day_columns[0], time_rows, parse_common_entry)
    entries_by_day_and_block = {
        col: collect_entries_by_block(workbook, col, time_rows, parse_program_cell)
        for col in day_columns
    }

    days = []
    for col, header in zip(day_columns, day_headers):
        blocks = []
        for start_row, end_row in windows:
            start_text, end_text, start_min, end_min = parse_clock_range(normalize_text(workbook.value(f"{time_col}{start_row}", merged=False)))
            block = {
                "id": f"{header['date']}-{start_text.replace(':', '')}",
                "start": start_text,
                "end": end_text,
                "startMin": start_min,
                "endMin": end_min,
                "section": section_for_row(workbook, start_row, section_col),
                "entries": [],
            }
            if is_common_block(workbook, start_row, day_columns):
                for parsed in common_entries_by_block.get(start_row, []):
                    block["entries"].append(
                        {
                            "id": f"{header['date']}-{start_text.replace(':', '')}-{len(block['entries']) + 1}",
                            "title": parsed["title"],
                            "subtitle": parsed["subtitle"],
                            "categoryId": parsed["categoryId"],
                            "groupIds": parsed["groupIds"],
                            "staff": parsed["staff"],
                            "staffRole": parsed["staffRole"],
                            "location": "강당",
                            "tags": list(dict.fromkeys([parsed["title"]] + parsed["groupIds"] + [parsed["categoryId"]])),
                        }
                    )
            else:
                for idx, parsed in enumerate(entries_by_day_and_block.get(col, {}).get(start_row, []), start=1):
                    block["entries"].append(
                        {
                            "id": f"{header['date']}-{start_text.replace(':', '')}-{idx}",
                            "title": parsed["title"],
                            "subtitle": parsed["subtitle"],
                            "categoryId": parsed["categoryId"],
                            "groupIds": parsed["groupIds"],
                            "staff": parsed["staff"],
                            "staffRole": parsed["staffRole"],
                            "location": "강당",
                            "tags": list(dict.fromkeys([parsed["title"]] + parsed["groupIds"] + [parsed["categoryId"]])),
                        }
                    )
            blocks.append(block)
        days.append(
            {
                "date": header["date"],
                "weekday": header["weekday"],
                "venueManager": header["venueManager"],
                "blocks": blocks,
            }
        )

    return {
        "sourceFile": str(Path(path)),
        "sheetName": workbook.sheet_name,
        "meta": {
            "title": "주간프로그램 계획표",
            "timezone": "Asia/Seoul",
            "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "defaultView": "now",
            "sourceLabel": week_label,
        },
        "taxonomies": {
            "groups": [
                {"id": "sarang", "label": "사랑반", "color": "#F3B6B0"},
                {"id": "mideum", "label": "믿음반", "color": "#B9D7A8"},
                {"id": "somang", "label": "소망반", "color": "#A8D5F2"},
                {"id": "all", "label": "전체", "color": "#E6D7A8"},
            ],
            "categories": [
                {"id": "service", "label": "서비스"},
                {"id": "routine", "label": "일상"},
                {"id": "cognitive", "label": "인지"},
                {"id": "physical", "label": "신체"},
                {"id": "rehab", "label": "재활"},
                {"id": "meal", "label": "식사"},
                {"id": "custom", "label": "맞춤형"},
                {"id": "social", "label": "사회적응"},
            ],
        },
        "days": days,
        "flatEntries": build_flat_entries(days),
    }


def parse_program_workbook(path: str | Path) -> list[dict[str, Any]]:
    workbook_path = Path(path)
    parsed_sheets: list[dict[str, Any]] = []
    for sheet_name, sheet_path in workbook_sheet_refs(workbook_path):
        if "주차" not in sheet_name:
            continue
        parsed_sheets.append(parse_program_sheet(workbook_path, sheet_name=sheet_name, sheet_path=sheet_path))
    return parsed_sheets


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse weekly program XLSX into JSON.")
    parser.add_argument("xlsx_path", help="Path to the weekly program workbook.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    parsed = parse_program_sheet(args.xlsx_path)
    if args.pretty:
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(parsed, ensure_ascii=False))


if __name__ == "__main__":
    main()
