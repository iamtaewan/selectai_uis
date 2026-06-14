/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 기본 컴파트먼트 OCID (선택) — 미설정 시 빈 값, 화면에서 직접 입력 */
  readonly VITE_DEFAULT_COMPARTMENT_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
