import { formatMetric } from "../lib/date";
import type { DaySummary } from "../types";

type Props = {
  day: DaySummary;
  onToggleOffTable: () => void;
};

export function SummaryCards({ day, onToggleOffTable }: Props) {
  return (
    <div className="metric-grid">
      <article className="metric-card">
        <div className="metric-label">근무자</div>
        <div className="metric-value has-tooltip" data-tooltip="실 근무자 수 + 교육 수">
          {day.isSundayClosed ? "-" : day.workDisplayText}
        </div>
        <div className="metric-subtext">
          {day.isSundayClosed ? "센터 휴무" : `휴무 ${formatMetric(day.offCount)}`}
        </div>
      </article>

      <button
        type="button"
        className={`metric-card accent ${day.isSundayClosed ? "disabled" : "clickable"}`}
        onClick={day.isSundayClosed ? undefined : onToggleOffTable}
      >
        <div className="metric-label">휴무자</div>
        <div className="metric-value">{day.isSundayClosed ? "-" : formatMetric(day.offCount)}</div>
        <div className="metric-subtext">{day.isSundayClosed ? "센터 휴무" : "상세 보기"}</div>
      </button>
    </div>
  );
}
