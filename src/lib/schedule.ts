import rawData from "../data/generated/schedule.json";
import type { DaySummary, MonthSummary, ScheduleData } from "../types";
import { parseIsoDate, toIsoDate } from "./date";

const data = rawData as ScheduleData;
const dayMap = new Map(data.days.map((day) => [day.date, day]));

export function getScheduleData() {
  return data;
}

export function getDay(date: string) {
  return dayMap.get(date) ?? null;
}

export function getToday() {
  return getDay(toIsoDate(new Date()));
}

export function getTomorrow() {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  return getDay(toIsoDate(date));
}

export function getLatestDay() {
  return data.days[data.days.length - 1] ?? null;
}

export function getMonth(key: string) {
  return data.months.find((month) => month.key === key) ?? null;
}

export function getInitialMonth(): MonthSummary | null {
  const currentMonth = toIsoDate(new Date()).slice(0, 7);
  return getMonth(currentMonth) ?? data.months[data.months.length - 1] ?? null;
}

export function getDaysForMonth(key: string) {
  const month = getMonth(key);
  if (!month) return [];
  return month.dates.map((date) => getDay(date)).filter(Boolean) as DaySummary[];
}

export function isValidIsoDate(value?: string) {
  if (!value) return false;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = parseIsoDate(value);
  return toIsoDate(date) === value && dayMap.has(value);
}
