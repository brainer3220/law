import type { InferUITools, ToolSet, UIMessage } from "ai";
import { z } from "zod";
import type { ArtifactKind } from "@/components/artifact";
import type { createDocument } from "./ai/tools/create-document";
import type { getWeather } from "./ai/tools/get-weather";
import type { requestSuggestions } from "./ai/tools/request-suggestions";
import type { updateDocument } from "./ai/tools/update-document";
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

type weatherTool = typeof getWeather;
type createDocumentTool = ReturnType<typeof createDocument>;
type updateDocumentTool = ReturnType<typeof updateDocument>;
type requestSuggestionsTool = ReturnType<typeof requestSuggestions>;
type lawKeywordSearchTool = typeof lawKeywordSearch;
type lawStatuteSearchTool = typeof lawStatuteSearch;
type lawStatuteDetailTool = typeof lawStatuteDetail;
type lawInterpretationSearchTool = typeof lawInterpretationSearch;
type lawInterpretationDetailTool = typeof lawInterpretationDetail;

export type ChatToolImplementations = ToolSet & {
  getWeather: weatherTool;
  createDocument: createDocumentTool;
  updateDocument: updateDocumentTool;
  requestSuggestions: requestSuggestionsTool;
  lawKeywordSearch: lawKeywordSearchTool;
  lawStatuteSearch: lawStatuteSearchTool;
  lawStatuteDetail: lawStatuteDetailTool;
  lawInterpretationSearch: lawInterpretationSearchTool;
  lawInterpretationDetail: lawInterpretationDetailTool;
};

export type ChatTools = InferUITools<ChatToolImplementations>;

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
