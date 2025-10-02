import { tool } from "ai";
import { z } from "zod";
import {
  callLawMcpTool,
  type LawMcpHit,
  type LawMcpHitsPayload,
} from "./law-mcp-client";

type GenericRecord = Record<string, unknown>;

export type LawKeywordSearchResult = LawMcpHitsPayload;

export type LawStatuteSearchResult = LawMcpHitsPayload & {
  response?: GenericRecord | null;
};

export type LawStatuteDetailResult = LawMcpHitsPayload & {
  detail?: GenericRecord | null;
};

export type LawInterpretationSearchResult = LawMcpHitsPayload & {
  response?: GenericRecord | null;
};

export type LawInterpretationDetailResult = LawMcpHitsPayload & {
  detail?: GenericRecord | null;
};

const hitsLimitDescription =
  "Optional maximum number of results. Defaults to 5 if omitted.";

const keywordSearchSchema = z.object({
  query: z
    .string()
    .min(1)
    .describe("Korean legal keyword query or statute citation to search for."),
  k: z
    .number()
    .int()
    .positive()
    .max(20)
    .optional()
    .describe(hitsLimitDescription),
  context_chars: z
    .number()
    .int()
    .min(0)
    .max(2000)
    .optional()
    .describe(
      "Optional snippet expansion length. When provided, snippets include the specified number of characters around each match."
    ),
});

const statuteSearchSchema = z.object({
  query: z
    .string()
    .min(1)
    .describe("Keyword, 법령명, 혹은 조문 번호 등을 포함한 검색어."),
  search: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("law.go.kr 검색 범주. 미지정 시 기본값을 사용합니다."),
  display: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("페이지당 결과 수."),
  page: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("조회할 페이지 (1부터 시작)."),
  sort: z
    .string()
    .optional()
    .describe("정렬 기준. law.go.kr API와 동일한 파라미터를 사용합니다."),
  ef_yd: z
    .string()
    .optional()
    .describe("시행일(YYYYMMDD)."),
  anc_yd: z
    .string()
    .optional()
    .describe("제정일(YYYYMMDD)."),
  anc_no: z
    .string()
    .optional()
    .describe("제정번호."),
  rr_cls_cd: z
    .string()
    .optional()
    .describe("법령 구분 코드."),
  nb: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("법령 번호."),
  org: z
    .string()
    .optional()
    .describe("소관 부처 코드."),
  knd: z
    .string()
    .optional()
    .describe("법령 종류 코드."),
  ls_chap_no: z
    .string()
    .optional()
    .describe("편/장 번호."),
  gana: z
    .string()
    .optional()
    .describe("가나다순 검색을 위한 초성."),
  oc: z
    .string()
    .optional()
    .describe("법령 API OpenAPI Key. 환경 변수 LAW_GO_KR_OC 대신 직접 지정할 수 있습니다."),
});

const statuteDetailSchema = z.object({
  law_id: z
    .string()
    .optional()
    .describe("law.go.kr 법령 ID. law_statute_search 결과의 doc_id에서 확인 가능합니다."),
  mst: z.string().optional().describe("법령구분(MST) 코드."),
  lm: z.string().optional().describe("법령 마스터 ID."),
  ld: z
    .number()
    .int()
    .nonnegative()
    .optional()
    .describe("법령 본문 조회 시 필요한 ld 파라미터."),
  ln: z
    .number()
    .int()
    .nonnegative()
    .optional()
    .describe("조문 번호."),
  jo: z
    .number()
    .int()
    .nonnegative()
    .optional()
    .describe("항 번호."),
  lang: z.string().optional().describe("언어 코드. 기본값은 한국어."),
  oc: z
    .string()
    .optional()
    .describe("법령 API OpenAPI Key. 환경 변수 LAW_GO_KR_OC 대신 지정할 수 있습니다."),
});

const interpretationSearchSchema = z.object({
  query: z
    .string()
    .optional()
    .describe("법령해석례 키워드 또는 문장."),
  search: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("검색 범주."),
  display: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("페이지당 결과 수."),
  page: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("조회할 페이지."),
  inq: z
    .string()
    .optional()
    .describe("질의자."),
  rpl: z
    .number()
    .int()
    .nonnegative()
    .optional()
    .describe("회신번호."),
  gana: z
    .string()
    .optional()
    .describe("가나다 초성 검색."),
  itmno: z
    .number()
    .int()
    .nonnegative()
    .optional()
    .describe("항목 번호."),
  reg_yd: z
    .string()
    .optional()
    .describe("접수일(YYYYMMDD)."),
  expl_yd: z
    .string()
    .optional()
    .describe("회신일(YYYYMMDD)."),
  sort: z
    .string()
    .optional()
    .describe("정렬 기준."),
  oc: z
    .string()
    .optional()
    .describe("법령 API OpenAPI Key."),
});

const interpretationDetailSchema = z.object({
  interpretation_id: z
    .string()
    .optional()
    .describe("법령해석례 ID."),
  lm: z.string().optional().describe("법령 마스터 ID."),
  oc: z
    .string()
    .optional()
    .describe("법령 API OpenAPI Key."),
});

export const lawKeywordSearch = tool({
  description:
    "OpenSearch 기반 법령·판례 키워드 검색. 질문에 답하기 전에 관련 스니펫과 출처를 확보할 때 사용하세요.",
  inputSchema: keywordSearchSchema,
  execute: async (args, { abortSignal }) => {
    return callLawMcpTool<LawKeywordSearchResult>("keyword_search", args, {
      signal: abortSignal,
    });
  },
});

export const lawStatuteSearch = tool({
  description:
    "law.go.kr 법령 검색 API 래퍼. 특정 법령이나 조문을 빠르게 찾고 싶을 때 사용하세요.",
  inputSchema: statuteSearchSchema,
  execute: async (args, { abortSignal }) => {
    return callLawMcpTool<LawStatuteSearchResult>("law_statute_search", args, {
      signal: abortSignal,
    });
  },
});

export const lawStatuteDetail = tool({
  description:
    "law.go.kr 법령 본문 조회. law_statute_search에서 받은 식별자로 상세 조문을 가져옵니다.",
  inputSchema: statuteDetailSchema,
  execute: async (args, { abortSignal }) => {
    return callLawMcpTool<LawStatuteDetailResult>("law_statute_detail", args, {
      signal: abortSignal,
    });
  },
});

export const lawInterpretationSearch = tool({
  description:
    "법제처 법령해석례 검색. 쟁점별 유사 해석례를 찾아 근거를 확보하세요.",
  inputSchema: interpretationSearchSchema,
  execute: async (args, { abortSignal }) => {
    return callLawMcpTool<LawInterpretationSearchResult>(
      "law_interpretation_search",
      args,
      { signal: abortSignal }
    );
  },
});

export const lawInterpretationDetail = tool({
  description:
    "법령해석례 본문 조회. 해석례 ID나 law_interpretation_search 결과를 바탕으로 전문을 확인합니다.",
  inputSchema: interpretationDetailSchema,
  execute: async (args, { abortSignal }) => {
    return callLawMcpTool<LawInterpretationDetailResult>(
      "law_interpretation_detail",
      args,
      { signal: abortSignal }
    );
  },
});

export type LawToolResults =
  | LawKeywordSearchResult
  | LawStatuteSearchResult
  | LawStatuteDetailResult
  | LawInterpretationSearchResult
  | LawInterpretationDetailResult;

export type { LawMcpHit };
