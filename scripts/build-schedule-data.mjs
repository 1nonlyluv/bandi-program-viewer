import ExcelJS from "exceljs";
import fs from "node:fs/promises";
import path from "node:path";

const EMPLOYEE_START = 6;
const EMPLOYEE_END = 25;
const WANTED_OFF_FILL = "FFDAEEF3";
const MEETING_OVERRIDE_DATE = "2026-03-03";
const GROUP_RULES = [
  { start: 14, end: 17, name: "사랑반" },
  { start: 18, end: 20, name: "믿음반" },
  { start: 21, end: 24, name: "소망반" },
];
const KITCHEN_GROUPS = ["소망반", "믿음반", "사랑반"];
const KITCHEN_ANCHOR = new Date("2026-03-01T00:00:00+09:00");

function toIsoDate(date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function normalizeWeight(value) {
  const normalized = Math.round(value * 2) / 2;
  return Number.isInteger(normalized) ? normalized : Number(normalized.toFixed(1));
}

function formatWeight(value) {
  return `${normalizeWeight(value)}`;
}

function monthKeyFromSheet(name) {
  const match = name.match(/(\d{2})년\s*(\d{1,2})월/);
  if (!match) return null;
  return `20${match[1]}-${match[2].padStart(2, "0")}`;
}

function colNumberToName(value) {
  let current = value;
  let result = "";
  while (current > 0) {
    current -= 1;
    result = String.fromCharCode(65 + (current % 26)) + result;
    current = Math.floor(current / 26);
  }
  return result;
}

function columnsBetween(start, end) {
  return Array.from({ length: end - start + 1 }, (_, index) => colNumberToName(start + index));
}

function kitchenDutyGroup(date) {
  const weekOffset = Math.floor((date.getTime() - KITCHEN_ANCHOR.getTime()) / (7 * 24 * 60 * 60 * 1000));
  return KITCHEN_GROUPS[((weekOffset % KITCHEN_GROUPS.length) + KITCHEN_GROUPS.length) % KITCHEN_GROUPS.length];
}

function groupNameFor(monthKey, row) {
  if (monthKey !== "2026-03") return "-";
  const matched = GROUP_RULES.find((rule) => row >= rule.start && row <= rule.end);
  return matched?.name ?? "-";
}

function isSunday(date) {
  return date.getDay() === 0;
}

function cellText(worksheet, ref) {
  const value = worksheet.getCell(ref).text?.trim();
  return value || "";
}

function cellFill(worksheet, ref) {
  const cell = worksheet.getCell(ref);
  const fill = cell.fill;
  if (!fill || fill.type !== "pattern" || fill.pattern !== "solid") return undefined;
  return fill.fgColor?.argb;
}

function classifyRecord(dateIso, rawCode, fill) {
  if (dateIso === MEETING_OVERRIDE_DATE) {
    return { dutyKind: "WORK", workWeight: 1, offWeight: 0, trainingWeight: 0 };
  }

  switch (rawCode) {
    case "D":
    case "직":
    case "원":
    case "회":
    case "의":
      return { dutyKind: "WORK", workWeight: 1, offWeight: 0, trainingWeight: 0 };
    case "교육":
      return { dutyKind: "TRAINING", workWeight: 0, offWeight: 0, trainingWeight: 1 };
    case "경조":
    case "경조사":
      return { dutyKind: "OFF", leaveType: "경조사", workWeight: 0, offWeight: 1, trainingWeight: 0 };
    case "▲":
      return { dutyKind: "OFF", leaveType: "연차", workWeight: 0, offWeight: 1, trainingWeight: 0 };
    case "●":
      return {
        dutyKind: "OFF",
        leaveType: fill === WANTED_OFF_FILL ? "휴무(신청)" : "휴무(지정)",
        workWeight: 0,
        offWeight: 1,
        trainingWeight: 0,
      };
    case "D●":
      return { dutyKind: "OFF", leaveType: "오후반차", workWeight: 0.5, offWeight: 0.5, trainingWeight: 0 };
    case "●D":
      return { dutyKind: "OFF", leaveType: "오전반차", workWeight: 0.5, offWeight: 0.5, trainingWeight: 0 };
    case "D▲":
      return { dutyKind: "OFF", leaveType: "오후연차반차", workWeight: 0.5, offWeight: 0.5, trainingWeight: 0 };
    case "▲D":
      return { dutyKind: "OFF", leaveType: "오전연차반차", workWeight: 0.5, offWeight: 0.5, trainingWeight: 0 };
    default:
      return { dutyKind: "WORK", workWeight: 0, offWeight: 0, trainingWeight: 0 };
  }
}

function validateTemplate(worksheet) {
  return ["B1", "G4", "G5", "C6", "E6"].every((ref) => cellText(worksheet, ref));
}

async function findWorkbookFile(cwd) {
  const entries = await fs.readdir(cwd);
  const workbook = entries.filter((entry) => entry.endsWith(".xlsx")).sort()[0];
  if (!workbook) {
    throw new Error("No .xlsx workbook found in project root");
  }
  return workbook;
}

async function build() {
  const cwd = process.cwd();
  const workbookName = process.argv[2] ?? (await findWorkbookFile(cwd));
  const workbookPath = path.resolve(cwd, workbookName);

  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.readFile(workbookPath);

  const monthsByKey = new Map();
  const columns = columnsBetween(7, 37);

  workbook.worksheets.forEach((worksheet) => {
    const monthKey = monthKeyFromSheet(worksheet.name);
    if (!monthKey) return;
    monthsByKey.set(monthKey, worksheet);
  });

  const months = [];
  const days = [];

  for (const monthKey of [...monthsByKey.keys()].sort()) {
    const worksheet = monthsByKey.get(monthKey);
    if (!worksheet || !validateTemplate(worksheet)) {
      console.warn(`Skipping ${worksheet?.name ?? monthKey}: template cells not found`);
      continue;
    }

    const [year, month] = monthKey.split("-").map(Number);
    const employees = [];

    for (let row = EMPLOYEE_START; row <= EMPLOYEE_END; row += 1) {
      const name = cellText(worksheet, `C${row}`);
      if (!name) continue;
      employees.push({
        row,
        employeeId: `${name}|${cellText(worksheet, `E${row}`)}`,
        name,
        position: cellText(worksheet, `E${row}`),
        groupName: groupNameFor(monthKey, row),
      });
    }

    const monthDates = [];

    for (const column of columns) {
      const dayText = cellText(worksheet, `${column}4`);
      if (!/^\d+$/.test(dayText)) continue;
      const dayNumber = Number(dayText);
      const date = new Date(year, month - 1, dayNumber);
      if (date.getMonth() !== month - 1 || date.getDate() !== dayNumber) {
        console.warn(`Invalid date for ${worksheet.name} ${column}4=${dayText}`);
        continue;
      }

      const dateIso = toIsoDate(date);
      monthDates.push(dateIso);

      if (isSunday(date)) {
        days.push({
          date: dateIso,
          isSundayClosed: true,
          actualWorkCount: 0,
          trainingCount: 0,
          offCount: 0,
          workDisplayText: "-",
          kitchenDutyGroup: kitchenDutyGroup(date),
          offEmployees: [],
          allEmployees: [],
        });
        continue;
      }

      const records = employees.map((employee) => {
        const rawCode = cellText(worksheet, `${column}${employee.row}`);
        const record = classifyRecord(dateIso, rawCode, cellFill(worksheet, `${column}${employee.row}`));
        return {
          employeeId: employee.employeeId,
          name: employee.name,
          position: employee.position,
          groupName: employee.groupName,
          dutyKind: record.dutyKind,
          leaveType: record.leaveType,
          rawCode,
          workWeight: normalizeWeight(record.workWeight),
          offWeight: normalizeWeight(record.offWeight),
          trainingWeight: normalizeWeight(record.trainingWeight),
        };
      });

      const actualWorkCount = normalizeWeight(records.reduce((sum, row) => sum + row.workWeight, 0));
      const trainingCount = normalizeWeight(records.reduce((sum, row) => sum + row.trainingWeight, 0));
      const offCount = normalizeWeight(records.reduce((sum, row) => sum + row.offWeight, 0));

      days.push({
        date: dateIso,
        isSundayClosed: false,
        actualWorkCount,
        trainingCount,
        offCount,
        workDisplayText: trainingCount > 0 ? `${formatWeight(actualWorkCount)} (+ 교육 ${formatWeight(trainingCount)})` : formatWeight(actualWorkCount),
        kitchenDutyGroup: kitchenDutyGroup(date),
        offEmployees: records.filter((row) => row.offWeight > 0),
        allEmployees: records,
      });
    }

    months.push({
      key: monthKey,
      label: `${year}년 ${month}월`,
      dates: monthDates,
    });
  }

  days.sort((left, right) => left.date.localeCompare(right.date));
  months.sort((left, right) => left.key.localeCompare(right.key));

  const payload = {
    generatedAt: new Date().toISOString(),
    sourceFile: path.basename(workbookPath),
    months,
    days,
  };

  const outputDir = path.resolve(cwd, "src/data/generated");
  await fs.mkdir(outputDir, { recursive: true });
  await fs.writeFile(path.join(outputDir, "schedule.json"), `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  console.log(`Generated ${days.length} day entries from ${path.basename(workbookPath)}`);
}

build().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
