import { useState } from "react";
import { Link } from "react-router-dom";
import { HeaderNav } from "../components/HeaderNav";
import { OffTable } from "../components/OffTable";
import { SummaryCards } from "../components/SummaryCards";
import { formatDateLabel, shiftIsoDate } from "../lib/date";
import type { DaySummary } from "../types";

type Props = {
  day: DaySummary | null;
  eyebrow: string;
};

export function SummaryPage({ day, eyebrow }: Props) {
  const [isExpanded, setExpanded] = useState(false);

  if (!day) {
    return (
      <main className="page-shell">
        <HeaderNav />
        <section className="empty-state">
          <h1>데이터 없음</h1>
          <p>선택한 날짜의 근무표 데이터가 없습니다.</p>
        </section>
      </main>
    );
  }

  const previousDate = shiftIsoDate(day.date, -1);
  const nextDate = shiftIsoDate(day.date, 1);

  return (
    <main className="page-shell">
      <HeaderNav />

      <section className="hero">
        <div className="hero-top">
          <p className="eyebrow">{eyebrow}</p>
          <h1 className="hero-date">{formatDateLabel(day.date)}</h1>
        </div>

        <SummaryCards day={day} onToggleOffTable={() => setExpanded((value) => !value)} />

        {day.isSundayClosed ? (
          <div className="status-banner">일요일은 센터 휴무입니다.</div>
        ) : null}

        <section className="kitchen-card">
          <div className="kitchen-label">금주의 주방 담당 반</div>
          <div className="kitchen-value">{day.kitchenDutyGroup}</div>
        </section>

        <div className="action-row">
          <Link className="action-link subtle" to={`/date/${previousDate}`}>
            어제로 가기
          </Link>
          <Link className="action-link subtle" to="/">
            진짜 오늘
          </Link>
          <Link className="action-link" to={`/date/${nextDate}`}>
            내일 보기
          </Link>
          <Link className="action-link" to="/calendar">
            월별 근무 캘린더 보기
          </Link>
        </div>
      </section>

      <section className="detail-panel">
        <div className="detail-head">
          <div>
            <p className="eyebrow">휴무자 상세</p>
            <h2>{formatDateLabel(day.date)}</h2>
          </div>
          {!day.isSundayClosed ? (
            <button className="toggle-button" type="button" onClick={() => setExpanded((value) => !value)}>
              {isExpanded ? "휴무자 접기" : "휴무자 보기"}
            </button>
          ) : null}
        </div>

        {day.isSundayClosed ? (
          <p className="detail-empty">일요일은 센터 휴무이므로 근퇴 상세를 표시하지 않습니다.</p>
        ) : isExpanded ? (
          <OffTable rows={day.offEmployees} />
        ) : (
          <p className="detail-empty">휴무자 보기를 눌러 상세 목록을 펼치세요.</p>
        )}
      </section>
    </main>
  );
}
