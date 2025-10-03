import { geolocation } from "@vercel/functions";
import {
  APICallError,
  convertToModelMessages,
  createUIMessageStream,
  JsonToSseTransformStream,
  smoothStream,
  stepCountIs,
  streamText,
  type LanguageModelUsage,
  type ModelMessage,
} from "ai";
import { unstable_cache as cache } from "next/cache";
import { after } from "next/server";
import {
  createResumableStreamContext,
  type ResumableStreamContext,
} from "resumable-stream";
import type { ModelCatalog } from "tokenlens/core";
import { fetchModels } from "tokenlens/fetch";
import { getUsage } from "tokenlens/helpers";
import { auth, type UserType } from "@/app/(auth)/auth";
import type { VisibilityType } from "@/components/visibility-selector";
import { getEntitlementsForUserType } from "@/lib/ai/entitlements";
import type { ChatModel } from "@/lib/ai/models";
import { type RequestHints, systemPrompt } from "@/lib/ai/prompts";
import { myProvider } from "@/lib/ai/providers";
import { createDocument } from "@/lib/ai/tools/create-document";
import { getWeather } from "@/lib/ai/tools/get-weather";
import {
  lawInterpretationDetail,
  lawInterpretationSearch,
  lawKeywordSearch,
  lawStatuteDetail,
  lawStatuteSearch,
} from "@/lib/ai/tools/law";
import { requestSuggestions } from "@/lib/ai/tools/request-suggestions";
import { updateDocument } from "@/lib/ai/tools/update-document";
import { isProductionEnvironment } from "@/lib/constants";
import {
  createStreamId,
  deleteChatById,
  getChatById,
  getMessageCountByUserId,
  getMessagesByChatId,
  saveChat,
  saveMessages,
  updateChatLastContextById,
} from "@/lib/db/queries";
import { ChatSDKError } from "@/lib/errors";
import type { ChatMessage } from "@/lib/types";
import type { AppUsage } from "@/lib/usage";
import { convertToUIMessages, generateUUID } from "@/lib/utils";
import { generateTitleFromUserMessage } from "../../actions";
import { type PostRequestBody, postRequestBodySchema } from "./schema";

export const maxDuration = 60;

let globalStreamContext: ResumableStreamContext | null = null;

const DEFAULT_MAX_TOOL_STEPS = 6;

/**
 * Maximum number of tool-invocation steps the agent may take before we force a
 * final assistant response. Operators can tune this via AI_MAX_TOOL_STEPS (or
 * NEXT_PUBLIC_AI_MAX_TOOL_STEPS) without touching the agent loop.
 */
export const MAX_TOOL_STEPS = (() => {
  const rawValue =
    process.env.AI_MAX_TOOL_STEPS ?? process.env.NEXT_PUBLIC_AI_MAX_TOOL_STEPS;

  if (!rawValue) {
    return DEFAULT_MAX_TOOL_STEPS;
  }

  // Strict validation: must be a positive integer string
  if (!/^\d+$/.test(rawValue)) {
    if (typeof console !== "undefined" && typeof console.warn === "function") {
      console.warn(
        `[MAX_TOOL_STEPS] Invalid environment variable value: "${rawValue}". Must be a positive integer. Using default (${DEFAULT_MAX_TOOL_STEPS}).`
      );
    }
    return DEFAULT_MAX_TOOL_STEPS;
  }

  const parsed = Number.parseInt(rawValue, 10);

  if (!Number.isFinite(parsed) || parsed <= 0) {
    if (typeof console !== "undefined" && typeof console.warn === "function") {
      console.warn(
        `[MAX_TOOL_STEPS] Environment variable value is not a positive integer: "${rawValue}". Using default (${DEFAULT_MAX_TOOL_STEPS}).`
      );
    }
    return DEFAULT_MAX_TOOL_STEPS;
  }

  return parsed;
})();

function mergeUsage(
  current: LanguageModelUsage | undefined,
  incoming: LanguageModelUsage | undefined
): LanguageModelUsage | undefined {
  if (!incoming) {
    return current ? { ...current } : undefined;
  }

  if (!current) {
    return { ...incoming };
  }

  const merged: Partial<LanguageModelUsage> = { ...current };

  for (const key of Object.keys(incoming) as Array<keyof LanguageModelUsage>) {
    const incomingValue = incoming[key];

    if (typeof incomingValue === "number") {
      const existingValue = merged[key];
      merged[key] =
        typeof existingValue === "number"
          ? existingValue + incomingValue
          : incomingValue;
    } else if (merged[key] === undefined) {
      merged[key] = incomingValue;
    }
  }

  return merged as LanguageModelUsage;
}

const getTokenlensCatalog = cache(
  async (): Promise<ModelCatalog | undefined> => {
    try {
      return await fetchModels();
    } catch (err) {
      console.warn(
        "TokenLens: catalog fetch failed, using default catalog",
        err
      );
      return; // tokenlens helpers will fall back to defaultCatalog
    }
  },
  ["tokenlens-catalog"],
  { revalidate: 24 * 60 * 60 } // 24 hours
);

function getRedisUrl() {
  return process.env.REDIS_URL ?? process.env.UPSTASH_REDIS_REST_URL;
}

function hasValidRedisConfiguration() {
  const redisUrl = getRedisUrl();

  if (!redisUrl) {
    return false;
  }

  try {
    // Ensure the provided value is a well-formed URL. This prevents
    // placeholders such as "****" from triggering runtime errors in
    // environments where secrets are redacted.
    new URL(redisUrl);
    return true;
  } catch {
    return false;
  }
}

export function getStreamContext() {
  if (!globalStreamContext) {
    if (!hasValidRedisConfiguration()) {
      console.log(
        " > Resumable streams are disabled due to missing or invalid Redis configuration"
      );
      return null;
    }

    try {
      globalStreamContext = createResumableStreamContext({
        waitUntil: after,
      });
    } catch (error: any) {
      if (error?.code === "ERR_INVALID_URL") {
        console.log(
          " > Resumable streams are disabled due to invalid Redis URL"
        );
      } else if (error?.message?.includes?.("REDIS_URL")) {
        console.log(
          " > Resumable streams are disabled due to missing REDIS_URL"
        );
      } else {
        console.error(error);
      }
    }
  }

  return globalStreamContext;
}

export async function POST(request: Request) {
  let requestBody: PostRequestBody;

  try {
    const json = await request.json();
    requestBody = postRequestBodySchema.parse(json);
  } catch (_) {
    return new ChatSDKError("bad_request:api").toResponse();
  }

  try {
    const {
      id,
      message,
      selectedChatModel,
      selectedVisibilityType,
    }: {
      id: string;
      message: ChatMessage;
      selectedChatModel: ChatModel["id"];
      selectedVisibilityType: VisibilityType;
    } = requestBody;

    const session = await auth();

    if (!session?.user) {
      return new ChatSDKError("unauthorized:chat").toResponse();
    }

    const userType: UserType = session.user.type;

    const messageCount = await getMessageCountByUserId({
      id: session.user.id,
      differenceInHours: 24,
    });

    if (messageCount > getEntitlementsForUserType(userType).maxMessagesPerDay) {
      return new ChatSDKError("rate_limit:chat").toResponse();
    }

    const chat = await getChatById({ id });

    if (chat) {
      if (chat.userId !== session.user.id) {
        return new ChatSDKError("forbidden:chat").toResponse();
      }
    } else {
      const title = await generateTitleFromUserMessage({
        message,
      });

      await saveChat({
        id,
        userId: session.user.id,
        title,
        visibility: selectedVisibilityType,
      });
    }

    const messagesFromDb = await getMessagesByChatId({ id });
    const uiMessages = [...convertToUIMessages(messagesFromDb), message];

    const { longitude, latitude, city, country } = geolocation(request);

    const requestHints: RequestHints = {
      longitude,
      latitude,
      city,
      country,
    };

    await saveMessages({
      messages: [
        {
          chatId: id,
          id: message.id,
          role: "user",
          parts: message.parts,
          attachments: [],
          createdAt: new Date(),
        },
      ],
    });

    const streamId = generateUUID();
    await createStreamId({ streamId, chatId: id });

    let finalMergedUsage: AppUsage | undefined;

    const stream = createUIMessageStream({
      execute: async ({ writer: dataStream }) => {
        const languageModel = myProvider.languageModel(selectedChatModel);
        const systemPromptValue = systemPrompt({
          selectedChatModel,
          requestHints,
        });
        const baseMessages = convertToModelMessages(uiMessages);

        const telemetryConfig = {
          isEnabled: isProductionEnvironment,
          functionId: "stream-text",
        };

        const toolset = {
          getWeather,
          createDocument: createDocument({ session, dataStream }),
          updateDocument: updateDocument({ session, dataStream }),
          requestSuggestions: requestSuggestions({
            session,
            dataStream,
          }),
          lawKeywordSearch,
          lawStatuteSearch,
          lawStatuteDetail,
          lawInterpretationSearch,
          lawInterpretationDetail,
        };

        const enabledToolNames: Array<keyof typeof toolset> =
          selectedChatModel === "chat-model-reasoning"
            ? []
            : [
                "getWeather",
                "createDocument",
                "updateDocument",
                "requestSuggestions",
                "lawKeywordSearch",
                "lawStatuteSearch",
                "lawStatuteDetail",
                "lawInterpretationSearch",
                "lawInterpretationDetail",
              ];

        let aggregatedUsage: LanguageModelUsage | undefined;

        const publishUsage = async () => {
          if (!aggregatedUsage) {
            return;
          }

          const usageSnapshot: LanguageModelUsage = { ...aggregatedUsage };
          const { modelId } = languageModel;
          let usageForClient: AppUsage = {
            ...usageSnapshot,
            ...(modelId ? { modelId } : {}),
          } as AppUsage;

          try {
            const providers = await getTokenlensCatalog();

            if (modelId && providers) {
              const summary = getUsage({
                modelId,
                usage: usageSnapshot,
                providers,
              });
              usageForClient = {
                ...usageSnapshot,
                ...summary,
                modelId,
              } as AppUsage;
            }
          } catch (err) {
            console.warn("TokenLens enrichment failed", err);
          }

          finalMergedUsage = usageForClient;
          dataStream.write({ type: "data-usage", data: usageForClient });
        };

        const handleStreamFinish = async ({
          usage,
          totalUsage,
        }: {
          usage: LanguageModelUsage;
          totalUsage?: LanguageModelUsage;
        }) => {
          aggregatedUsage = mergeUsage(
            aggregatedUsage,
            totalUsage ?? usage
          );
          await publishUsage();
        };

        const createAgentStream = ({
          messages,
          stopWhen,
          toolChoice,
          activeTools,
        }: {
          messages: ModelMessage[];
          stopWhen: ReturnType<typeof stepCountIs>;
          toolChoice?: "none";
          activeTools?: Array<keyof typeof toolset>;
        }) =>
          streamText({
            model: languageModel,
            system: systemPromptValue,
            messages,
            stopWhen,
            toolChoice,
            experimental_activeTools: activeTools ?? enabledToolNames,
            experimental_transform: smoothStream({ chunking: "word" }),
            tools: toolset,
            experimental_telemetry: telemetryConfig,
            onFinish: handleStreamFinish,
          });

        const initialResult = createAgentStream({
          messages: baseMessages,
          // Allow one extra step so the agent can reply after hitting the tool limit.
          stopWhen: stepCountIs(MAX_TOOL_STEPS + 1),
        });

        dataStream.merge(
          initialResult.toUIMessageStream({
            sendReasoning: true,
          })
        );

        await initialResult.consumeStream();

        const initialSteps = await initialResult.steps;
        const lastInitialStep = initialSteps.at(-1);

        const unfinishedToolRun =
          lastInitialStep?.toolCalls?.length &&
          (!lastInitialStep.text || lastInitialStep.text.trim().length === 0);

        if (unfinishedToolRun && lastInitialStep) {
          console.info(
            `Agent exhausted ${MAX_TOOL_STEPS} tool steps; requesting a concluding assistant turn.`
          );

          const continuationMessages: ModelMessage[] = [
            ...baseMessages,
            ...lastInitialStep.response.messages,
          ];

          const continuationResult = createAgentStream({
            messages: continuationMessages,
            stopWhen: stepCountIs(1),
            toolChoice: "none",
            activeTools: [],
          });

          dataStream.merge(
            continuationResult.toUIMessageStream({
              sendReasoning: true,
            })
          );

          await continuationResult.consumeStream();

          const continuationSteps = await continuationResult.steps;
          const continuationFinalStep = continuationSteps.at(-1);

          const continuationUnfinished =
            continuationFinalStep?.toolCalls?.length &&
            (!continuationFinalStep.text ||
              continuationFinalStep.text.trim().length === 0);

          if (continuationUnfinished) {
            throw new ChatSDKError(
              "offline:chat",
              "Agent run ended without a final assistant message after the tool ceiling was reached."
            );
          }
        }
      },
      generateId: generateUUID,
      onFinish: async ({ messages }) => {
        await saveMessages({
          messages: messages.map((currentMessage) => ({
            id: currentMessage.id,
            role: currentMessage.role,
            parts: currentMessage.parts,
            createdAt: new Date(),
            attachments: [],
            chatId: id,
          })),
        });

        if (finalMergedUsage) {
          try {
            await updateChatLastContextById({
              chatId: id,
              context: finalMergedUsage,
            });
          } catch (err) {
            console.warn("Unable to persist last usage for chat", id, err);
          }
        }
      },
      onError: () => {
        return "Oops, an error occurred!";
      },
    });

    // const streamContext = getStreamContext();

    // if (streamContext) {
    //   return new Response(
    //     await streamContext.resumableStream(streamId, () =>
    //       stream.pipeThrough(new JsonToSseTransformStream())
    //     )
    //   );
    // }

    return new Response(stream.pipeThrough(new JsonToSseTransformStream()));
  } catch (error) {
    const vercelId = request.headers.get("x-vercel-id");

    if (error instanceof ChatSDKError) {
      return error.toResponse();
    }

    if (error instanceof APICallError) {
      const { statusCode, responseBody, message } = error;
      const responseText =
        typeof responseBody === "string" && responseBody.length > 0
          ? responseBody
          : undefined;
      const cause = responseText ?? message;

      if (statusCode === 429) {
        return new ChatSDKError("rate_limit:provider", cause).toResponse();
      }

      if (
        statusCode === 401 ||
        statusCode === 403 ||
        (statusCode === 400 && responseText?.includes("API key not valid"))
      ) {
        return new ChatSDKError("unauthorized:provider", cause).toResponse();
      }
    }

    // Check for Vercel AI Gateway credit card error
    if (
      error instanceof Error &&
      error.message?.includes(
        "AI Gateway requires a valid credit card on file to service requests"
      )
    ) {
      return new ChatSDKError("bad_request:activate_gateway").toResponse();
    }

    console.error("Unhandled error in chat API:", error, { vercelId });
    return new ChatSDKError("offline:chat").toResponse();
  }
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  if (!id) {
    return new ChatSDKError("bad_request:api").toResponse();
  }

  const session = await auth();

  if (!session?.user) {
    return new ChatSDKError("unauthorized:chat").toResponse();
  }

  const chat = await getChatById({ id });

  if (chat?.userId !== session.user.id) {
    return new ChatSDKError("forbidden:chat").toResponse();
  }

  const deletedChat = await deleteChatById({ id });

  return Response.json(deletedChat, { status: 200 });
}
