/**
 * Onboarding 페이지 — PG-00 (/) / 공통.
 * 3장 가치 카드 + 사용 모드 선택(localStorage — design.md X4 결정) + 시작 CTA.
 * 저장된 커넥션이 있으면 "계속하기" CTA를 우선 노출한다 (design.md PG-00).
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getEnvelope } from "../api/client";
import type { ConnectionOut } from "../api/types";
import Button from "../components/Button";
import { useConnectionStore } from "../store/connectionStore";

/** 표시 수준 preference는 백엔드 API 없이 localStorage에 저장 (design.md PG-08 X4 결정) */
const MODE_STORAGE_KEY = "selectai.uiMode";

type UiMode = "simple" | "expert";

const VALUE_CARDS: { step: string; title: string; body: string }[] = [
  {
    step: "①",
    title: "연결한다",
    body: "wallet zip 업로드(또는 OCI 자동 다운로드)만으로 ADB 26ai에 연결하고, 검증된 커넥션을 저장·재사용합니다.",
  },
  {
    step: "②",
    title: "질문한다",
    body: "자연어 질문이 SQL이 되고 결과가 됩니다 — runsql·showsql·explainsql·narrate·chat 액션을 한 화면에서 시연합니다.",
  },
  {
    step: "③",
    title: "입증한다",
    body: "테이블 COMMENT 증강 전/후의 생성 SQL을 좌우 비교해 '메타데이터가 좋아지면 정확해진다'를 입증합니다.",
  },
];

export function Onboarding() {
  const navigate = useNavigate();
  const setActiveConnection = useConnectionStore((s) => s.setActiveConnection);
  const [mode, setMode] = useState<UiMode>(() => {
    // 마지막 선택 모드 복원 (인터랙션 원칙 8 — 상태 보존)
    return localStorage.getItem(MODE_STORAGE_KEY) === "expert" ? "expert" : "simple";
  });

  // 저장된 커넥션 유무로 CTA 분기 — 로컬 저장소 조회 (DB 미접속, executed_sql 없음)
  const { data: connections } = useQuery({
    queryKey: ["connections"],
    queryFn: async () => (await getEnvelope<ConnectionOut[]>("/connections")).data,
  });

  useEffect(() => {
    localStorage.setItem(MODE_STORAGE_KEY, mode);
  }, [mode]);

  // last_used_at 내림차순 정렬 응답의 첫 항목 = 마지막 사용 커넥션 (api-spec §2.3 / FR-02)
  const lastConnection = connections?.[0] ?? null;

  const continueWithSaved = () => {
    if (lastConnection) setActiveConnection(lastConnection);
    navigate("/connections");
  };

  return (
    <div className="mx-auto max-w-[880px] py-8 text-center">
      <h2 className="text-3xl font-bold">Select AI Demo Studio</h2>
      <p className="mt-2 text-lg text-[var(--color-neutral-60)]">
        "말로 데이터를 묻는다 — 15분 안에 보여드립니다"
      </p>

      {/* 3장 가치 카드 */}
      <div className="mt-10 grid grid-cols-3 gap-6 text-left">
        {VALUE_CARDS.map((card) => (
          <section
            key={card.step}
            className="rounded-[var(--radius-lg)] border border-[var(--color-neutral-30)] bg-[var(--color-neutral-0)] p-6 shadow-sm"
          >
            <p className="text-2xl">{card.step}</p>
            <h3 className="mt-1 text-lg font-semibold">{card.title}</h3>
            <p className="mt-2 text-sm text-[var(--color-neutral-60)]">{card.body}</p>
          </section>
        ))}
      </div>

      {/* 사용 모드 라디오 — 앱 설정(localStorage) */}
      <fieldset className="mt-10 inline-flex flex-col gap-2 text-left">
        <legend className="mb-2 text-sm font-medium text-[var(--color-neutral-70)]">사용 모드</legend>
        <label className="flex cursor-pointer items-center gap-2 text-sm">
          <input
            type="radio"
            name="ui-mode"
            checked={mode === "simple"}
            onChange={() => setMode("simple")}
          />
          <span>
            <strong>단순 모드</strong> — 준비된 데모만 빠르게 (비기술 사용자 권장)
          </span>
        </label>
        <label className="flex cursor-pointer items-center gap-2 text-sm">
          <input
            type="radio"
            name="ui-mode"
            checked={mode === "expert"}
            onChange={() => setMode("expert")}
          />
          <span>
            <strong>전문가 모드</strong> — SQL과 속성까지 전부 보기
          </span>
        </label>
      </fieldset>

      {/* 주 CTA — 저장 커넥션 유무 분기 (design.md PG-00) */}
      <div className="mt-10 flex flex-col items-center gap-3">
        {lastConnection ? (
          <>
            <Button large onClick={continueWithSaved}>
              {lastConnection.name}으로 계속하기 →
            </Button>
            <Button variant="ghost" onClick={() => navigate("/connections")}>
              새 데이터베이스 연결하기 →
            </Button>
          </>
        ) : (
          <Button large onClick={() => navigate("/connections")}>
            새 데이터베이스 연결하기 →
          </Button>
        )}
      </div>
    </div>
  );
}

export default Onboarding;
