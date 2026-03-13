import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { HeaderNav } from "../components/HeaderNav";
import { OffTable } from "../components/OffTable";
import { formatDateLabel, formatMetric, formatWeekdayLabel } from "../lib/date";
import { getDaysForMonth, getInitialMonth, getScheduleData } from "../lib/schedule";
import type { DaySummary } from "../types";

export function CalendarPage() {
  const schedule = getScheduleData();
  const initialMonth = getInitialMonth();
  const [activeMonth, setActiveMonth] = useState(initialMonth?.key ?? "");

  const days = useMemo(() => getDaysForMonth(activeMonth), [activeMonth]);
  const [selectedDate, setSelectedDate] = useState(days.find((day) => !day.isSundayClosed)?.date ?? days[0]?.date ?? "");

  const selectedDay =
    days.find((day) => day.date === selectedDate) ??
    days.find((day) => !day.isSundayClosed) ??
    days[0] ??
    null;

  const handleMonthChange = (nextMonth: string) => {
    const nextDays = getDaysForMonth(nextMonth);
    setActiveMonth(nextMonth);
    setSelectedDate(nextDays.find((day) => !day.isSundayClosed)?.date ?? nextDays[0]?.date ?? "");
  };

  return (
    <main className="page-shell">
      <HeaderNav />

      <section className="calendar-layout">
        <div className="calendar-header">
          <div>
            <p className="eyebrow">월별 근무 캘린더</p>
            <h1>날짜별 근무 / 휴무 / 주방 담당 반</h1>
          </div>

          <div className="calendar-controls">
            <select className="month-select" value={activeMonth} onChange={(event) => handleMonthChange(event.target.value)}>
              {schedule.months.map((month) => (
                <option key={month.key} value={month.key}>
                  {month.label}
                </option>
              ))}
            </select>

            <Link className="action-link subtle" to="/">
              오늘 화면
            </Link>
          </div>
        </div>

        <div className="calendar-content">
          <div className="calendar-grid">
            {days.map((day) => (
              <button
                key={day.date}
                type="button"
                className={`day-card ${day.isSundayClosed ? "closed" : ""} ${selectedDay?.date === day.date ? "selected" : ""}`}
                onClick={() => setSelectedDate(day.date)}
              >
                <span className="day-number">
                  {new Date(day.date).getDate()} <small>{formatWeekdayLabel(day.date)}</small>
                </span>
                <span className="day-meta">{day.isSundayClosed ? "센터 휴무" : `근무 ${day.workDisplayText}`}</span>
                <span className="day-meta">{day.isSundayClosed ? "집계 제외" : `휴무 ${formatMetric(day.offCount)}`}</span>
                <span className="day-meta">{day.isSundayClosed ? "" : day.kitchenDutyGroup}</span>
              </button>
            ))}
          </div>

          <aside className="calendar-detail">
            {!selectedDay ? (
              <p className="detail-empty">선택 가능한 날짜가 없습니다.</p>
            ) : (
              <>
                <p className="eyebrow">선택 날짜</p>
                <h2>{formatDateLabel(selectedDay.date)}</h2>

                {selectedDay.isSundayClosed ? (
                  <>
                    <div className="status-banner">센터 휴무</div>
                    <p className="detail-empty">일요일은 근퇴 집계를 표시하지 않습니다.</p>
                  </>
                ) : (
                  <>
                    <div className="mini-metrics">
                      <div>
                        <span>실근무</span>
                        <strong>{formatMetric(selectedDay.actualWorkCount)}</strong>
                      </div>
                      <div>
                        <span>교육</span>
                        <strong>{formatMetric(selectedDay.trainingCount)}</strong>
                      </div>
                      <div>
                        <span>휴무</span>
                        <strong>{formatMetric(selectedDay.offCount)}</strong>
                      </div>
                    </div>

                    <div className="kitchen-inline">
                      금주 주방 담당 반: <strong>{selectedDay.kitchenDutyGroup}</strong>
                    </div>

                    <div className="calendar-actions">
                      <Link className="action-link subtle" to={`/date/${selectedDay.date}`}>
                        이 날짜 상세 보기
                      </Link>
                    </div>

                    <OffTable rows={selectedDay.offEmployees} />
                  </>
                )}
              </>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}
