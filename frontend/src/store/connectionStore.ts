/**
 * 활성 커넥션/기본 프로파일 전역 스토어 골격 (architecture.md — 전역 상태 2개뿐).
 * 활성 커넥션 ID는 api/client.ts의 X-Connection-Id 인터셉터가 참조한다.
 */
import { create } from "zustand";

import type { ConnectionOut } from "../api/types";

interface ConnectionState {
  /** 활성 커넥션 ID — null이면 미연결 (가드 레일: 시연 메뉴 잠금) */
  activeConnectionId: string | null;
  /** 활성 커넥션 메타 (헤더 선택기 표시용) */
  activeConnection: ConnectionOut | null;
  /** 앱 수준 기본 프로파일명 (서버 settings.json과 동기화) */
  defaultProfileName: string | null;
  setActiveConnection: (connection: ConnectionOut | null) => void;
  setDefaultProfileName: (profileName: string | null) => void;
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  activeConnectionId: null,
  activeConnection: null,
  defaultProfileName: null,
  setActiveConnection: (connection) =>
    set({
      activeConnection: connection,
      activeConnectionId: connection?.id ?? null,
    }),
  setDefaultProfileName: (defaultProfileName) => set({ defaultProfileName }),
}));
