"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { CitationPopover } from "@/components/CitationPopover";
import { ClaimEvidenceMatrix } from "@/components/ClaimEvidenceMatrix";
import { EvidenceCard } from "@/components/EvidenceCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { ProvenanceFooter } from "@/components/ProvenanceFooter";
import { UserMenu } from "@/components/auth/UserMenu";
import { useAuth } from "@/lib/auth/AuthContext";
import type {
  AnswerState,
  Claim,
  ClaimEvidenceCell,
  EvidenceSource,
  LegalAnswer,
  NextStepItem,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { ArrowLeftIcon } from "@heroicons/react/24/outline";

type LegalChatApiResponse = {
  choices?: Array<{ message?: { content?: string | null } }>;
  law?: {
    legal_answer?: LegalAnswer;
    citations?: Array<Record<string, unknown>>;
    evidence?: Array<Record<string, unknown>>;
  };
  error?: string;
};

const ANSWER_STATE_LABELS: Record<AnswerState, string> = {
  "answer-ready": "근거 충분",
  "answer-limited": "부분 검증",
  "refusal-with-next-step": "결론 보류",
  "system-error": "시스템 오류",
};

const ANSWER_STATE_DESCRIPTIONS: Record<AnswerState, string> = {
  "answer-ready": "모든 핵심 주장에 검증 가능한 근거가 연결되었습니다.",
  "answer-limited": "일부 주장만 검증되었습니다. 제한사항을 꼭 확인하세요.",
  "refusal-with-next-step": "결론을 강행하지 않고, 다음 확인 경로를 제안합니다.",
  "system-error": "검색 또는 검증 엔진이 실패해 답변을 보류했습니다.",
};

export default function PilotPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [question, setQuestion] = useState(
    "근로시간 면제 관련 최신 판례와 법령상 기준을 알려줘"
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LegalAnswer | null>(null);

  const cells = useMemo<ClaimEvidenceCell[]>(() => {
    if (!result) {
      return [];
    }
    return buildCells(result.claims, result.evidence);
  }, [result]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setError("질문을 입력해 주세요.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/api/legal-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: trimmed }],
          stream: false,
          top_k: 5,
          max_iters: 3,
        }),
      });
      const payload = (await response.json().catch(() => null)) as LegalChatApiResponse | null;
      if (!response.ok || !payload) {
        throw new Error(payload?.error ?? "법률 QA 응답을 가져오지 못했습니다.");
      }
      const legalAnswer = payload.law?.legal_answer;
      if (!legalAnswer) {
        throw new Error("구조화된 legal_answer payload가 없습니다.");
      }
      setResult(legalAnswer);
    } catch (submitError) {
      setResult(null);
      setError(
        submitError instanceof Error
          ? submitError.message
          : "법률 QA 응답을 처리하지 못했습니다."
      );
    } finally {
      setPending(false);
    }
  };

  if (loading) {
    return (
      <div className="material-screen">
        <div className="material-loading">
          <LoadingSpinner size="lg" label="파일럿 화면을 준비하는 중입니다..." />
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <main className="material-screen p-6">
        <div className="mx-auto max-w-2xl rounded-2xl border border-gray-200 bg-white p-8 shadow-sm dark:border-gray-800 dark:bg-slate-900">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            파일럿 법률 QA
          </h1>
          <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">
            실제 파일럿 화면은 로그인한 사용자만 볼 수 있습니다.
          </p>
          <button
            type="button"
            onClick={() => router.push("/auth/login")}
            className="mt-6 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white dark:bg-slate-100 dark:text-slate-900"
          >
            로그인하러 가기
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 px-4 py-6 dark:bg-slate-950 sm:px-6">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <button
              type="button"
              onClick={() => router.push("/")}
              className="mb-3 inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
            >
              <ArrowLeftIcon className="h-4 w-4" aria-hidden="true" />
              메인으로 돌아가기
            </button>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              evidence-gated legal QA 파일럿
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-gray-600 dark:text-gray-400">
              답변을 강행하지 않고, claim 단위 근거와 검증 상태를 먼저 보여주는 얇은 파일럿 화면입니다.
            </p>
          </div>
          <UserMenu />
        </header>

        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-slate-900">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <label className="block text-sm font-semibold text-gray-900 dark:text-gray-100">
              법률 질문
            </label>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              rows={4}
              className="w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 outline-none ring-0 transition focus:border-slate-500 dark:border-gray-700 dark:bg-slate-950 dark:text-gray-100"
              placeholder="예: 근로시간 면제 관련 최신 판례와 법령상 기준을 알려줘"
            />
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={pending}
                className="rounded-full bg-slate-900 px-5 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900"
              >
                {pending ? "검증 중..." : "근거 기반으로 답변 받기"}
              </button>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                출처가 부족하면 결론을 멈추고 다음 단계를 보여줍니다.
              </span>
            </div>
          </form>
        </section>

        {error && (
          <section className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">
            {error}
          </section>
        )}

        {pending && (
          <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-slate-900">
            <LoadingSpinner size="lg" label="검색과 근거 검증을 진행하는 중입니다..." />
          </section>
        )}

        {result && (
          <>
            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-slate-900">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div
                    className={cn(
                      "inline-flex rounded-full px-3 py-1 text-xs font-semibold",
                      stateColorClass(result.answerState)
                    )}
                  >
                    {ANSWER_STATE_LABELS[result.answerState]}
                  </div>
                  <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">
                    {ANSWER_STATE_DESCRIPTIONS[result.answerState]}
                  </p>
                </div>
                <div className="min-w-[220px] rounded-2xl bg-gray-50 p-4 text-xs text-gray-600 dark:bg-slate-950 dark:text-gray-400">
                  <div>Claims: {result.claims.length}</div>
                  <div className="mt-1">Evidence: {result.evidence.length}</div>
                  <div className="mt-1">Next steps: {result.nextSteps.length}</div>
                </div>
              </div>

              {result.answer ? (
                <div className="mt-5 rounded-2xl bg-gray-50 p-4 text-sm leading-7 text-gray-800 dark:bg-slate-950 dark:text-gray-200">
                  {renderAnswerWithClaims(result.answer, result.claims, result.evidence)}
                </div>
              ) : (
                <div className="mt-5 rounded-2xl border border-dashed border-gray-300 p-4 text-sm text-gray-700 dark:border-gray-700 dark:text-gray-300">
                  {result.reason ?? "검증 가능한 근거가 충분하지 않아 결론을 보류했습니다."}
                </div>
              )}

              {result.missingEvidence.length > 0 && (
                <div className="mt-5">
                  <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    누락되거나 부족한 근거
                  </h2>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-600 dark:text-gray-400">
                    {result.missingEvidence.map((issue) => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}

              {result.nextSteps.length > 0 && (
                <div className="mt-5">
                  <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    다음 단계
                  </h2>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    {result.nextSteps.map((step) => (
                      <NextStepCard key={`${step.type}-${step.label}-${step.value}`} step={step} />
                    ))}
                  </div>
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-slate-900">
              <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
                Claim x Evidence 매핑
              </h2>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                어떤 claim이 어느 근거와 연결되는지 먼저 봅니다. 여기서 비면, 답변은 믿지 않는 게 맞습니다.
              </p>
              <div className="mt-4">
                <ClaimEvidenceMatrix claims={result.claims} evidence={result.evidence} cells={cells} />
              </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
              <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-slate-900">
                <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
                  근거 카드
                </h2>
                <div className="mt-4 space-y-3">
                  {result.evidence.map((item) => (
                    <EvidenceCard key={item.id} evidence={item} />
                  ))}
                </div>
              </div>
              <div className="rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-slate-900">
                <ProvenanceFooter provenance={result.provenance} />
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}

function renderAnswerWithClaims(
  answer: string,
  claims: Claim[],
  evidence: EvidenceSource[]
) {
  const filteredClaims = claims.filter((claim) => claim.text.trim().length > 0);
  if (filteredClaims.length === 0) {
    return <p>{answer}</p>;
  }
  return (
    <div className="space-y-3">
      {filteredClaims.map((claim) => {
        const linkedEvidence = evidence.filter((item) => claim.evidenceIds.includes(item.id));
        return (
          <p key={claim.id}>
            <CitationPopover
              text={claim.text}
              evidence={linkedEvidence}
              status={claim.status}
            />
          </p>
        );
      })}
    </div>
  );
}

function buildCells(claims: Claim[], evidence: EvidenceSource[]): ClaimEvidenceCell[] {
  return claims.flatMap((claim) =>
    evidence.map((item) => ({
      claimId: claim.id,
      evidenceId: item.id,
      relevance: claim.evidenceIds.includes(item.id)
        ? claim.status === "verified"
          ? 0.95
          : claim.status === "partial"
            ? 0.65
            : claim.status === "stale"
              ? 0.55
              : 0.35
        : 0.15,
      isSupporting: claim.evidenceIds.includes(item.id),
    }))
  );
}

function stateColorClass(answerState: AnswerState): string {
  switch (answerState) {
    case "answer-ready":
      return "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300";
    case "answer-limited":
      return "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300";
    case "refusal-with-next-step":
      return "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-200";
    case "system-error":
      return "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-300";
  }
}

function NextStepCard({ step }: { step: NextStepItem }) {
  return (
    <article className="rounded-2xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-slate-950">
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {step.type}
      </div>
      <div className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
        {step.label}
      </div>
      <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">{step.value}</div>
    </article>
  );
}
