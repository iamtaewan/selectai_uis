/**
 * 앱 진입점 — tokens.css 최우선 import (style.md §7.1).
 * 스캐폴딩 공유 파일 — 구현 에이전트 수정 금지.
 */
import React from "react";
import ReactDOM from "react-dom/client";

import "./styles/tokens.css";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
