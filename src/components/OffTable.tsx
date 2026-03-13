import { formatMetric } from "../lib/date";
import type { EmployeeDayRecord } from "../types";

type Props = {
  rows: EmployeeDayRecord[];
};

export function OffTable({ rows }: Props) {
  if (!rows.length) {
    return <p className="detail-empty">휴무자가 없습니다.</p>;
  }

  return (
    <table className="off-table">
      <thead>
        <tr>
          <th>이름</th>
          <th>직위</th>
          <th>소속</th>
          <th>휴무 종류</th>
          <th>환산</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={`${row.employeeId}-${row.rawCode}-${row.leaveType ?? "none"}`}>
            <td>{row.name}</td>
            <td>{row.position}</td>
            <td>{row.groupName}</td>
            <td>{row.leaveType ?? "-"}</td>
            <td>{formatMetric(row.offWeight)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
