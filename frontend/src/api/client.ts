/**
 * API 클라이언트 골격 — axios + envelope + X-Connection-Id 인터셉터.
 * 스캐폴딩 공유 파일 — 인터셉터 구조 변경 금지, 헬퍼 추가는 허용.
 *
 * - 요청: 활성 커넥션(connectionStore)이 있으면 X-Connection-Id 헤더 자동 첨부 (api-spec §1.2)
 * - 응답: 성공 envelope의 executed_sql/elapsed_ms를 SqlLogTerminal 스토어에 누적 (design.md §1.3)
 * - 오류: §1.4 오류 envelope을 ApiError로 정규화
 */
import axios, { AxiosError } from "axios";

import { useConnectionStore } from "../store/connectionStore";
import { useSqlLogStore } from "../store/sqlLogStore";
import type { Envelope, ErrorBody, ErrorResponse } from "./types";

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

// 요청 인터셉터 — 활성 커넥션 헤더 첨부
api.interceptors.request.use((config) => {
  const connectionId = useConnectionStore.getState().activeConnectionId;
  if (connectionId && !config.headers.has("X-Connection-Id")) {
    config.headers.set("X-Connection-Id", connectionId);
  }
  return config;
});

// 응답 인터셉터 — SQL 로그 누적 + 오류 정규화
api.interceptors.response.use(
  (response) => {
    const envelope = response.data as Partial<Envelope>;
    if (Array.isArray(envelope?.executed_sql) && envelope.executed_sql.length > 0) {
      useSqlLogStore.getState().append({
        sqls: envelope.executed_sql,
        elapsedMs: envelope.elapsed_ms ?? null,
        sourcePath: response.config.url ?? "",
        ok: true,
      });
    }
    return response;
  },
  (error: AxiosError<ErrorResponse>) => {
    const body = error.response?.data?.error;
    if (body) {
      if (Array.isArray(body.executed_sql) && body.executed_sql.length > 0) {
        useSqlLogStore.getState().append({
          sqls: body.executed_sql,
          elapsedMs: null,
          sourcePath: error.config?.url ?? "",
          ok: false,
          errorCode: body.code,
        });
      }
      return Promise.reject(new ApiError(error.response?.status ?? 500, body));
    }
    return Promise.reject(error);
  },
);

/** envelope GET 헬퍼 */
export async function getEnvelope<T>(url: string, params?: object): Promise<Envelope<T>> {
  const res = await api.get<Envelope<T>>(url, { params });
  return res.data;
}

/** envelope POST 헬퍼 */
export async function postEnvelope<T>(url: string, body?: unknown): Promise<Envelope<T>> {
  const res = await api.post<Envelope<T>>(url, body);
  return res.data;
}

/** envelope PUT 헬퍼 */
export async function putEnvelope<T>(url: string, body?: unknown): Promise<Envelope<T>> {
  const res = await api.put<Envelope<T>>(url, body);
  return res.data;
}

/** envelope PATCH 헬퍼 */
export async function patchEnvelope<T>(url: string, body?: unknown): Promise<Envelope<T>> {
  const res = await api.patch<Envelope<T>>(url, body);
  return res.data;
}

/** envelope DELETE 헬퍼 */
export async function deleteEnvelope<T>(url: string): Promise<Envelope<T>> {
  const res = await api.delete<Envelope<T>>(url);
  return res.data;
}
