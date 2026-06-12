/**
 * App — 라우터 + QueryClientProvider (design.md §1.1 전체 페이지 라우트).
 * 스캐폴딩 공유 파일 — 구현 에이전트 수정 금지. 페이지 본문은 pages/*.tsx에서 채운다.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import AppShell from "./components/AppShell";
import Chat from "./pages/Chat";
import ChatHistory from "./pages/ChatHistory";
import Connections from "./pages/Connections";
import Dashboard from "./pages/Dashboard";
import Enrichment from "./pages/Enrichment";
import Onboarding from "./pages/Onboarding";
import Permissions from "./pages/Permissions";
import Playground from "./pages/Playground";
import ProfileDetail from "./pages/ProfileDetail";
import ProfileEditor from "./pages/ProfileEditor";
import Profiles from "./pages/Profiles";
import SettingsPage from "./pages/SettingsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // LLM 비결정성 — 자동 재시도는 사용자 명시 동작으로만 (api-spec §12.3)
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* design.md §1.1 — PG-00 ~ PG-08 */}
          <Route element={<AppShell />}>
            <Route path="/" element={<Onboarding />} />
            <Route path="/connections" element={<Connections />} />
            <Route path="/permissions" element={<Permissions />} />
            <Route path="/profiles" element={<Profiles />} />
            <Route path="/profiles/new" element={<ProfileEditor />} />
            <Route path="/profiles/:name/edit" element={<ProfileEditor />} />
            <Route path="/profiles/:name" element={<ProfileDetail />} />
            <Route path="/playground" element={<Playground />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/chat/history" element={<ChatHistory />} />
            <Route path="/enrichment" element={<Enrichment />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
