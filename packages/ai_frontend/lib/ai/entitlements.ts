import type { UserType } from "@/app/(auth)/auth";
import type { ChatModel } from "./models";

export type Entitlements = {
  maxMessagesPerDay: number;
  availableChatModelIds: ChatModel["id"][];
};

const REGULAR_ENTITLEMENTS: Entitlements = {
  maxMessagesPerDay: 100,
  availableChatModelIds: ["chat-model", "chat-model-reasoning"],
};

const PREMIUM_ENTITLEMENTS: Entitlements = {
  maxMessagesPerDay: 1000,
  availableChatModelIds: ["chat-model", "chat-model-reasoning"],
};

export const getEntitlementsForUserType = (
  userType: UserType
): Entitlements => {
  if (userType === "premium") {
    return PREMIUM_ENTITLEMENTS;
  }

  return REGULAR_ENTITLEMENTS;
};
