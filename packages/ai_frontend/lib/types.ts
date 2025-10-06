import type { InferUITool, UIMessage } from "ai";
import { z } from "zod";
import type { ArtifactKind } from "@/components/artifact";
import type {
  lawInterpretationDetail,
  lawInterpretationSearch,
  lawKeywordSearch,
  lawStatuteDetail,
  lawStatuteSearch,
} from "./ai/tools/law";
import type { Suggestion } from "./db/schema";
import type { AppUsage } from "./usage";

export type DataPart = { type: "append-message"; message: string };

export const messageMetadataSchema = z.object({
  createdAt: z.string(),
});

export type MessageMetadata = z.infer<typeof messageMetadataSchema>;

type lawKeywordSearchTool = InferUITool<typeof lawKeywordSearch>;
type lawStatuteSearchTool = InferUITool<typeof lawStatuteSearch>;
type lawStatuteDetailTool = InferUITool<typeof lawStatuteDetail>;
type lawInterpretationSearchTool = InferUITool<
  typeof lawInterpretationSearch
>;
type lawInterpretationDetailTool = InferUITool<
  typeof lawInterpretationDetail
>;

export type ChatTools = {
  lawKeywordSearch: lawKeywordSearchTool;
  lawStatuteSearch: lawStatuteSearchTool;
  lawStatuteDetail: lawStatuteDetailTool;
  lawInterpretationSearch: lawInterpretationSearchTool;
  lawInterpretationDetail: lawInterpretationDetailTool;
};

export type CustomUIDataTypes = {
  textDelta: string;
  imageDelta: string;
  sheetDelta: string;
  codeDelta: string;
  suggestion: Suggestion;
  appendMessage: string;
  id: string;
  title: string;
  kind: ArtifactKind;
  clear: null;
  finish: null;
  usage: AppUsage;
};

export type ChatMessage = UIMessage<
  MessageMetadata,
  CustomUIDataTypes,
  ChatTools
>;

export type Attachment = {
  name: string;
  url: string;
  contentType: string;
};
