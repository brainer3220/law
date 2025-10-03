import {
  convertToModelMessages,
  smoothStream,
  stepCountIs,
  streamText,
  type LanguageModel,
  type StreamTextOnFinishCallback,
  type Tool,
  type UIMessageStreamWriter,
} from "ai";
import type { Session } from "next-auth";
import { systemPrompt, type RequestHints } from "@/lib/ai/prompts";
import { myProvider } from "@/lib/ai/providers";
import { isProductionEnvironment } from "@/lib/constants";
import type { ChatModel } from "@/lib/ai/models";
import type { ChatMessage } from "@/lib/types";

const DEFAULT_TOOL_ORDER = [
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

export type DefaultToolName = (typeof DEFAULT_TOOL_ORDER)[number];

export type RunAgentTools = Record<string, Tool>;

export type RunAgentOptions = {
  selectedChatModel: ChatModel["id"];
  requestHints: RequestHints;
  uiMessages: ChatMessage[];
  session: Session;
  dataStream: UIMessageStreamWriter<ChatMessage>;
  model?: LanguageModel;
  tools?: RunAgentTools;
  activeTools?: string[];
  onFinish?: StreamTextOnFinishCallback<RunAgentTools>;
  includeDefaultTools?: boolean;
};

async function createDefaultTools({
  session,
  dataStream,
}: Pick<RunAgentOptions, "session" | "dataStream">): Promise<RunAgentTools> {
  const [
    { getWeather },
    { createDocument },
    { updateDocument },
    { requestSuggestions },
    {
      lawKeywordSearch,
      lawStatuteSearch,
      lawStatuteDetail,
      lawInterpretationSearch,
      lawInterpretationDetail,
    },
  ] = await Promise.all([
    import("@/lib/ai/tools/get-weather"),
    import("@/lib/ai/tools/create-document"),
    import("@/lib/ai/tools/update-document"),
    import("@/lib/ai/tools/request-suggestions"),
    import("@/lib/ai/tools/law"),
  ]);

  const tools: RunAgentTools = {
    getWeather,
    createDocument: createDocument({ session, dataStream }),
    updateDocument: updateDocument({ session, dataStream }),
    requestSuggestions: requestSuggestions({ session, dataStream }),
    lawKeywordSearch,
    lawStatuteSearch,
    lawStatuteDetail,
    lawInterpretationSearch,
    lawInterpretationDetail,
  };

  return tools;
}

function mergeTools(
  defaults: RunAgentTools,
  overrides?: RunAgentTools
): RunAgentTools {
  if (!overrides) {
    return defaults;
  }

  return { ...defaults, ...overrides };
}

function resolveActiveTools({
  selectedChatModel,
  providedActiveTools,
  tools,
}: {
  selectedChatModel: RunAgentOptions["selectedChatModel"];
  providedActiveTools?: string[];
  tools: RunAgentTools;
}): string[] {
  if (selectedChatModel === "chat-model-reasoning") {
    return [];
  }

  if (providedActiveTools) {
    return providedActiveTools;
  }

  const defaultTools = DEFAULT_TOOL_ORDER.filter((toolName) =>
    Object.hasOwn(tools, toolName)
  );

  const additionalTools = Object.keys(tools).filter(
    (toolName) => !(DEFAULT_TOOL_ORDER as readonly string[]).includes(toolName)
  );

  return [...defaultTools, ...additionalTools];
}

/**
 * Helper that encapsulates the shared agent configuration used by the chat route.
 */
export async function runAgent({
  selectedChatModel,
  requestHints,
  uiMessages,
  session,
  dataStream,
  model,
  tools: overrideTools,
  activeTools: providedActiveTools,
  onFinish,
  includeDefaultTools = true,
}: RunAgentOptions) {
  const baseTools = includeDefaultTools
    ? await createDefaultTools({ session, dataStream })
    : ({} as RunAgentTools);
  const tools = mergeTools(baseTools, overrideTools);
  const filteredTools = Object.fromEntries(
    Object.entries(tools).filter(([, tool]) => Boolean(tool))
  ) as RunAgentTools;

  const activeTools = resolveActiveTools({
    selectedChatModel,
    providedActiveTools,
    tools: filteredTools,
  });

  return streamText({
    model: model ?? myProvider.languageModel(selectedChatModel),
    system: systemPrompt({ selectedChatModel, requestHints }),
    messages: convertToModelMessages(uiMessages),
    stopWhen: stepCountIs(6),
    activeTools,
    experimental_transform: smoothStream({ chunking: "word" }),
    tools: filteredTools,
    experimental_telemetry: {
      isEnabled: isProductionEnvironment,
      functionId: "stream-text",
    },
    onFinish,
  });
}
