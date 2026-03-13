import { Link } from "react-router-dom";

export function HeaderNav() {
  return (
    <header className="site-header">
      <Link className="brand" to="/">
        근퇴 관리
      </Link>
      <nav className="site-nav">
        <Link to="/">오늘</Link>
        <Link to="/tomorrow">내일</Link>
        <Link to="/calendar">월간 캘린더</Link>
      </nav>
    </header>
  );
}
