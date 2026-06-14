/**
 * 활성 커넥션/기본 프로파일/표시 모드 전역 스토어 (architecture.md — 전역 상태 최소화).
 * - 활성 커넥션 ID는 api/client.ts의 X-Connection-Id 인터셉터가 참조한다.
 * - 단순/전문가 모드, SQL 투명 모드는 표시 수준 preference — design.md X4 결정에 따라
 *   백엔드 API 없이 localStorage에만 동기화한다 (zustand persist).
 * - 기본 프로파일은 서버 settings.json(GET/PUT /settings/default-profile)과 동기화.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { ConnectionOut } from "../api/types";

/** 단순(P2 기본) / 전문가(P1·P3) 모드 — design.md §1.2 */
export type UiMode = "simple" | "expert";

interface ConnectionState {
  /** 활성 커넥션 ID — null이면 미연결 (가드 레일: 시연 메뉴 잠금) */
  activeConnectionId: string | null;
  /** 활성 커넥션 메타 (헤더 선택기 표시용) */
  activeConnection: ConnectionOut | null;
  /** 앱 수준 기본 프로파일명 (서버 settings.json과 동기화) */
  defaultProfileName: string | null;
  /** 단순/전문가 모드 — localStorage 동기화 */
  mode: UiMode;
  /** SQL 투명 모드 — 각 화면 인라인 SQL 미리보기/펼침 기본 상태 (design §1.3과 독립) */
  sqlTransparent: boolean;
  setActiveConnection: (connection: ConnectionOut | null) => void;
  setDefaultProfileName: (profileName: string | null) => void;
  /** 모드 전환 — 전문가 모드는 SQL 투명 모드 기본 켜짐 (design 인터랙션 원칙 1) */
  setMode: (mode: UiMode) => void;
  setSqlTransparent: (on: boolean) => void;
  toggleSqlTransparent: () => void;
}

export const useConnectionStore = create<ConnectionState>()(
  persist(
    (set) => ({
      activeConnectionId: null,
      activeConnection: null,
      defaultProfileName: null,
      mode: "simple",
      sqlTransparent: false,
      setActiveConnection: (connection) =>
        set({
          activeConnection: connection,
          activeConnectionId: connection?.id ?? null,
        }),
      setDefaultProfileName: (defaultProfileName) => set({ defaultProfileName }),
      setMode: (mode) => set({ mode, sqlTransparent: mode === "expert" }),
      setSqlTransparent: (sqlTransparent) => set({ sqlTransparent }),
      toggleSqlTransparent: () => set((state) => ({ sqlTransparent: !state.sqlTransparent })),
    }),
    {
      name: "selectai-ui-prefs",
      // 표시 preference + 활성 커넥션 ID를 영속화.
      // activeConnectionId를 저장해 새로고침 직후에도 X-Connection-Id 헤더가 즉시 붙는다
      // (미저장 시 커넥션 복원 전 마운트 쿼리가 CONNECTION_REQUIRED로 실패). 커넥션 메타 객체는
      // stale 가능성이 있어 저장하지 않고, AppShell에서 커넥션 목록 로드 후 id로 매칭 복원한다.
      partialize: (state) => ({
        mode: state.mode,
        sqlTransparent: state.sqlTransparent,
        activeConnectionId: state.activeConnectionId,
      }),
    },
  ),
);
