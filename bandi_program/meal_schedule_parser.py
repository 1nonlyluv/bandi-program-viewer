from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from shuttle_schedule_parser import XlsxSheet, normalize_text, workbook_sheet_refs


DATE_RE = re.compile(r"(?:(?P<year>20\d{2})\s*년\s*)?(?P<month>\d{1,2})\s*월\s*(?P<day>\d{1,2})\s*일")
MEAL_LABELS = {"아침": "breakfast", "점심": "lunch", "저녁": "dinner"}


def column_name(column_number: int) -> str:
    result = ""
    while column_number:
        column_number, remainder = divmod(column_number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def infer_year(path: str | Path) -> int:
    match = re.search(r"(20\d{2})", Path(path).name)
    return int(match.group(1)) if match else 2026


def parse_date_header(value: Any, default_year: int) -> str:
    match = DATE_RE.search(normalize_text(value))
    if not match:
        return ""
    year = int(match.group("year") or default_year)
    return f"{year:04d}-{int(match.group('month')):02d}-{int(match.group('day')):02d}"


def normalize_menu_item(value: Any) -> str:
    text = normalize_text(value)
    if not text or re.fullmatch(r"\d+\s*kcal", text, re.IGNORECASE):
        return ""
    return text.strip().strip("<>")


def find_date_columns(sheet: XlsxSheet, year: int) -> dict[int, str]:
    for row in range(1, min(sheet.max_row, 12) + 1):
        result: dict[int, str] = {}
        for column_number in range(1, sheet.max_col + 1):
            date = parse_date_header(sheet.value(f"{column_name(column_number)}{row}", merged=False), year)
            if date:
                result[column_number] = date
        if len(result) >= 2:
            return result
    return {}


def parse_meal_sheet(path: str | Path, *, sheet_name: str = "", sheet_path: str = "") -> dict[str, Any]:
    workbook_path = Path(path)
    sheet = XlsxSheet(workbook_path, sheet_name=sheet_name or None, sheet_path=sheet_path or None)
    date_columns = find_date_columns(sheet, infer_year(workbook_path))
    days: dict[str, dict[str, list[str]]] = {date: {} for date in date_columns.values()}
    meal_starts: list[tuple[int, str]] = []

    for row in range(1, sheet.max_row + 1):
        label = normalize_text(sheet.value(f"B{row}", merged=False))
        if label in MEAL_LABELS:
            meal_starts.append((row, MEAL_LABELS[label]))

    for index, (start_row, meal_type) in enumerate(meal_starts):
        end_row = meal_starts[index + 1][0] - 1 if index + 1 < len(meal_starts) else sheet.max_row
        for column_number, date in date_columns.items():
            column = column_name(column_number)
            items: list[str] = []
            for row in range(start_row, end_row + 1):
                item = normalize_menu_item(sheet.value(f"{column}{row}", merged=False))
                if item and item not in items:
                    items.append(item)
            if items:
                days[date][meal_type] = items

    return {
        "meta": {"sourceFile": workbook_path.name, "sheetName": sheet.sheet_name},
        "days": {date: meals for date, meals in days.items() if meals},
    }


def parse_meal_workbook(path: str | Path) -> list[dict[str, Any]]:
    workbook_path = Path(path)
    return [
        parse_meal_sheet(workbook_path, sheet_name=sheet_name, sheet_path=sheet_path)
        for sheet_name, sheet_path in workbook_sheet_refs(workbook_path)
    ]
