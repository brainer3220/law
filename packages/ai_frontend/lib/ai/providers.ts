import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import {
  customProvider,
  extractReasoningMiddleware,
  wrapLanguageModel,
} from "ai";
import { isTestEnvironment } from "../constants";

const gatewayProvider = (() => {
  const baseURL =
    process.env.OPENAI_COMPATIBLE_BASE_URL ?? "http://127.0.0.1:8080/v1";

  return createOpenAICompatible({
    name: "law-gateway",
    baseURL,
    apiKey: process.env.OPENAI_COMPATIBLE_API_KEY ?? undefined,
  });
})();

const chatModelId = process.env.OPENAI_COMPATIBLE_MODEL ?? "law-gateway";
const reasoningModelId =
  process.env.OPENAI_COMPATIBLE_REASONING_MODEL ?? chatModelId;
const titleModelId =
  process.env.OPENAI_COMPATIBLE_TITLE_MODEL ?? chatModelId;
const artifactModelId =
  process.env.OPENAI_COMPATIBLE_ARTIFACT_MODEL ?? chatModelId;

export const myProvider = isTestEnvironment
  ? (() => {
      const {
        artifactModel,
        chatModel,
        reasoningModel,
        titleModel,
      } = require("./models.mock");
      return customProvider({
        languageModels: {
          "chat-model": chatModel,
          "chat-model-reasoning": reasoningModel,
          "title-model": titleModel,
          "artifact-model": artifactModel,
        },
      });
    })()
  : customProvider({
      languageModels: {
        "chat-model": gatewayProvider.chatModel(chatModelId),
        "chat-model-reasoning": wrapLanguageModel({
          model: gatewayProvider.chatModel(reasoningModelId),
          middleware: extractReasoningMiddleware({ tagName: "think" }),
        }),
        "title-model": gatewayProvider.chatModel(titleModelId),
        "artifact-model": gatewayProvider.chatModel(artifactModelId),
      },
    });
