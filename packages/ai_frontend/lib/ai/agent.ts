import {
  convertToModelMessages,
  smoothStream,
  stepCountIs,
  streamText,
  type LanguageModel,
  type StreamTextOnFinishCallback,
  type UIMessageStreamWriter,
} from "ai";
import type { Session } from "next-auth";
import { isProductionEnvironment } from "@/lib/constants";
import type { ChatMessage, ChatTools } from "@/lib/types";
import type { ChatModel } from "./models";
import { type RequestHints, systemPrompt } from "./prompts";
import { myProvider } from "./providers";
export const DEFAULT_CHAT_TOOL_NAMES = [
  "getWeather",
  "createDocument",
  "updateDocument",
  "requestSuggestions",
  "lawKeywordSearch",
  "lawStatuteSearch",
  "lawStatuteDetail",
  "lawInterpretationSearch",
  "lawInterpretationDetail",
] as const;

type AgentToolName = (typeof DEFAULT_CHAT_TOOL_NAMES)[number];

type RunAgentOptions = {
  selectedChatModel: ChatModel["id"];
  uiMessages: ChatMessage[];
  requestHints: RequestHints;
  dataStream: UIMessageStreamWriter<ChatMessage>;
  tools: ChatTools;
  onFinish?: StreamTextOnFinishCallback<ChatTools>;
  model?: LanguageModel;
};

export function getAgentActiveTools(
  selectedChatModel: ChatModel["id"]
): AgentToolName[] {
  if (selectedChatModel === "chat-model-reasoning") {
    return [];
  }

  return [...DEFAULT_CHAT_TOOL_NAMES];
}

export async function buildDefaultAgentTools({
  dataStream,
  session,
}: {
  dataStream: UIMessageStreamWriter<ChatMessage>;
  session: Session;
}): Promise<ChatTools> {
  const [weatherModule, createDocumentModule, updateDocumentModule, requestSuggestionsModule, law] =
    await Promise.all([
      import("./tools/get-weather"),
      import("./tools/create-document"),
      import("./tools/update-document"),
      import("./tools/request-suggestions"),
      import("./tools/law"),
    ]);

  const createDocumentFactory =
    createDocumentModule.createDocument ?? createDocumentModule.default;
  const updateDocumentFactory =
    updateDocumentModule.updateDocument ?? updateDocumentModule.default;
  const requestSuggestionsFactory =
    requestSuggestionsModule.requestSuggestions ??
    requestSuggestionsModule.default;

  if (!createDocumentFactory) {
    throw new Error("Failed to load agent tool factory: createDocumentFactory");
  }
  if (!updateDocumentFactory) {
    throw new Error("Failed to load agent tool factory: updateDocumentFactory");
  }
  if (!requestSuggestionsFactory) {
    throw new Error("Failed to load agent tool factory: requestSuggestionsFactory");
  }

  return {
    getWeather: weatherModule.getWeather,
    createDocument: createDocumentFactory({ session, dataStream }),
    updateDocument: updateDocumentFactory({ session, dataStream }),
    requestSuggestions: requestSuggestionsFactory({ session, dataStream }),
    lawKeywordSearch: law.lawKeywordSearch,
    lawStatuteSearch: law.lawStatuteSearch,
    lawStatuteDetail: law.lawStatuteDetail,
    lawInterpretationSearch: law.lawInterpretationSearch,
    lawInterpretationDetail: law.lawInterpretationDetail,
  } satisfies ChatTools;
}

export function runAgent({
  dataStream,
  tools,
  model,
  onFinish,
  requestHints,
  selectedChatModel,
  uiMessages,
}: RunAgentOptions) {
  const languageModel =
    model ?? myProvider.languageModel(selectedChatModel);

  return streamText<ChatTools, never>({
    model: languageModel,
    system: systemPrompt({ selectedChatModel, requestHints }),
    messages: convertToModelMessages(uiMessages),
    stopWhen: stepCountIs(6),
    experimental_activeTools: getAgentActiveTools(selectedChatModel),
    experimental_transform: smoothStream({ chunking: "word" }),
    tools,
    experimental_telemetry: {
      isEnabled: isProductionEnvironment,
      functionId: "stream-text",
    },
    onFinish,
  });
}
