/**
 * API 클라이언트 — axios + envelope + X-Connection-Id 인터셉터 (완성본).
 * 스캐폴딩 공유 파일의 인터셉터 구조를 유지하고 아래를 보강했다 (design.md §1.3):
 *
 * - 요청: 활성 커넥션(connectionStore)이 있으면 X-Connection-Id 헤더 자동 첨부 (api-spec §1.2)
 *         sqlLogTag 지정 요청은 SqlLogTerminal에 "실행 중" 라인 표시 (running 스피너)
 * - 응답: 성공 envelope의 executed_sql/elapsed_ms를 SqlLogTerminal 스토어에 누적
 *         (요청 태그 전달 — 미지정 시 요청 경로)
 * - 오류: §1.4 오류 envelope을 ApiError로 정규화 + 오류 토스트 표시
 *         (suppressErrorToast로 백그라운드 폴링은 생략 가능)
 */
import axios, { AxiosError } from "axios";

import { useToastStore } from "../components/Toast";
import { useConnectionStore } from "../store/connectionStore";
import { useSqlLogStore } from "../store/sqlLogStore";
import type { Envelope, ErrorBody, ErrorResponse } from "./types";

// axios config 확장 — SQL 로그 태그/토스트 제어 (요청 단위 옵션)
declare module "axios" {
  export interface AxiosRequestConfig {
    /** SqlLogTerminal 라인 태그 (예: "PG-04/runsql") — 지정 시 실행 중 라인 표시 */
    sqlLogTag?: string;
    /** true면 오류 envelope 토스트 생략 (헤더 셀렉터·건강 폴링 등 백그라운드 호출용) */
    suppressErrorToast?: boolean;
    /** 내부용 — 실행 중 라인 id (요청 인터셉터가 채움) */
    sqlLogRunningId?: number;
  }
}

/** §1.4 오류 envelope을 담는 앱 표준 예외 */
export class ApiError extends Error {
  readonly body: ErrorBody;
  readonly status: number;

  constructor(status: number, body: ErrorBody) {
    super(body.message_ko);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }

  get retryable(): boolean {
    return this.body.retryable;
  }
}

export const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

// 요청 인터셉터 — 활성 커넥션 헤더 첨부 + 실행 중 라인 시작
api.interceptors.request.use((config) => {
  const connectionId = useConnectionStore.getState().activeConnectionId;
  if (connectionId && !config.headers.has("X-Connection-Id")) {
    config.headers.set("X-Connection-Id", connectionId);
  }
  // 태그 지정 요청(실행성 호출)만 실행 중 라인 표시 — 목록 조회 등 잡음 방지
  if (config.sqlLogTag) {
    config.sqlLogRunningId = useSqlLogStore.getState().beginRunning(config.sqlLogTag);
  }
  return config;
});

// 응답 인터셉터 — SQL 로그 누적(실행 중 라인 치환) + 오류 정규화 + 오류 토스트
api.interceptors.response.use(
  (response) => {
    const envelope = response.data as Partial<Envelope>;
    const config = response.config;
    const hasSqls = Array.isArray(envelope?.executed_sql) && envelope.executed_sql.length > 0;
    const payload = hasSqls
      ? {
          sqls: envelope.executed_sql as string[],
          elapsedMs: envelope.elapsed_ms ?? null,
          sourcePath: config.url ?? "",
          ok: true,
          tag: config.sqlLogTag,
        }
      : null;
    const log = useSqlLogStore.getState();
    if (config.sqlLogRunningId != null) {
      log.resolveRunning(config.sqlLogRunningId, payload);
    } else if (payload) {
      log.append(payload);
    }
    return response;
  },
  (error: AxiosError<ErrorResponse>) => {
    const config = error.config;
    const body = error.response?.data?.error;
    const log = useSqlLogStore.getState();
    const payload =
      body && Array.isArray(body.executed_sql) && body.executed_sql.length > 0
        ? {
            sqls: body.executed_sql,
            elapsedMs: null,
            sourcePath: config?.url ?? "",
            ok: false,
            errorCode: body.code,
            tag: config?.sqlLogTag,
          }
        : null;
    if (config?.sqlLogRunningId != null) {
      log.resolveRunning(config.sqlLogRunningId, payload);
    } else if (payload) {
      log.append(payload);
    }
    // 오류 envelope → 토스트 (message_ko + hint_ko) — design §3 공통 오류 상태
    if (!config?.suppressErrorToast) {
      if (body) {
        useToastStore.getState().push({
          status: "error",
          title: body.message_ko,
          body: body.hint_ko ?? body.code,
        });
      } else {
        useToastStore.getState().push({
          status: "error",
          title: "서버에 연결할 수 없습니다",
          body: error.message,
        });
      }
    }
    if (body) {
      return Promise.reject(new ApiError(error.response?.status ?? 500, body));
    }
    return Promise.reject(error);
  },
);

/** 요청 단위 옵션 — SQL 로그 태그/토스트 제어 */
export interface RequestOpts {
  /** SqlLogTerminal 라인 태그 (예: "PG-04/runsql") */
  sqlLogTag?: string;
  /** true면 오류 토스트 생략 (페이지가 인라인으로 오류 표시할 때) */
  suppressErrorToast?: boolean;
}

/** envelope GET 헬퍼 */
export async function getEnvelope<T>(
  url: string,
  params?: object,
  opts?: RequestOpts,
): Promise<Envelope<T>> {
  const res = await api.get<Envelope<T>>(url, { params, ...opts });
  return res.data;
}

/** envelope POST 헬퍼 */
export async function postEnvelope<T>(
  url: string,
  body?: unknown,
  opts?: RequestOpts,
): Promise<Envelope<T>> {
  const res = await api.post<Envelope<T>>(url, body, { ...opts });
  return res.data;
}

/** envelope PUT 헬퍼 */
export async function putEnvelope<T>(
  url: string,
  body?: unknown,
  opts?: RequestOpts,
): Promise<Envelope<T>> {
  const res = await api.put<Envelope<T>>(url, body, { ...opts });
  return res.data;
}

/** envelope PATCH 헬퍼 */
export async function patchEnvelope<T>(
  url: string,
  body?: unknown,
  opts?: RequestOpts,
): Promise<Envelope<T>> {
  const res = await api.patch<Envelope<T>>(url, body, { ...opts });
  return res.data;
}

/** envelope DELETE 헬퍼 */
export async function deleteEnvelope<T>(url: string, opts?: RequestOpts): Promise<Envelope<T>> {
  const res = await api.delete<Envelope<T>>(url, { ...opts });
  return res.data;
}
