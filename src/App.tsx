import { HashRouter, Navigate, Route, Routes, useParams } from "react-router-dom";
import { CalendarPage } from "./pages/CalendarPage";
import { SummaryPage } from "./pages/SummaryPage";
import { getDay, getToday, getTomorrow, isValidIsoDate } from "./lib/schedule";

function DateRoutePage() {
  const params = useParams<{ date: string }>();
  const date = params.date;
  return <SummaryPage day={date && isValidIsoDate(date) ? getDay(date) : null} eyebrow="선택한 날짜의 근무 현황" />;
}

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<SummaryPage day={getToday()} eyebrow="오늘의 근무 현황" />} />
        <Route path="/tomorrow" element={<SummaryPage day={getTomorrow()} eyebrow="내일의 근무 현황" />} />
        <Route path="/date/:date" element={<DateRoutePage />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  );
}
