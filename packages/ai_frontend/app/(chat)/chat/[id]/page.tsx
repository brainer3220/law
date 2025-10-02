import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { auth } from "@/app/(auth)/auth";
import { Chat } from "@/components/chat";
import { DataStreamHandler } from "@/components/data-stream-handler";
import { DEFAULT_CHAT_MODEL } from "@/lib/ai/models";
import { getChatById, getMessagesByChatId } from "@/lib/db/queries";
import { convertToUIMessages } from "@/lib/utils";

export default async function Page(props: { params: Promise<{ id: string }> }) {
  const params = await props.params;
  const { id } = params;
  const chat = await getChatById({ id });

  if (!chat) {
    notFound();
  }

  const session = await auth();

  if (!session) {
    redirect(`/login?redirectUrl=${encodeURIComponent(`/chat/${id}`)}`);
  }

  if (chat.visibility === "private") {
    if (!session.user) {
      return notFound();
    }

    if (session.user.id !== chat.userId) {
      return notFound();
    }
  }

  const messagesFromDb = await getMessagesByChatId({
    id,
  });

  const uiMessages = convertToUIMessages(messagesFromDb);

  const cookieStore = await cookies();
  const chatModelFromCookie = cookieStore.get("chat-model");
  const onboardingCompleteCookie = cookieStore.get("onboarding-complete");
  const shouldShowOnboarding =
    onboardingCompleteCookie?.value !== "true" && uiMessages.length === 0;
  const initialChatModel = chatModelFromCookie?.value ?? DEFAULT_CHAT_MODEL;

  return (
    <>
      <Chat
        autoResume={true}
        id={chat.id}
        initialChatModel={initialChatModel}
        initialLastContext={chat.lastContext ?? undefined}
        initialMessages={uiMessages}
        initialShowOnboarding={shouldShowOnboarding}
        initialVisibilityType={chat.visibility}
        isReadonly={session?.user?.id !== chat.userId}
      />
      <DataStreamHandler />
    </>
  );
}
