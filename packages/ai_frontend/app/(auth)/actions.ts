"use server";

import { z } from "zod";

import { createUser, getUser } from "@/lib/db/queries";

import { signIn } from "./auth";

const authFormSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
});

export type LoginActionState = {
  status: "idle" | "in_progress" | "success" | "failed" | "invalid_data";
};

export const login = async (
  _: LoginActionState,
  formData: FormData
): Promise<LoginActionState> => {
  try {
    const validatedData = authFormSchema.parse({
      email: formData.get("email"),
      password: formData.get("password"),
    });

    const redirectUrl = formData.get("redirectUrl");
    const callbackUrl =
      typeof redirectUrl === "string" && redirectUrl.startsWith("/")
        ? redirectUrl
        : undefined;

    const signInResult = await signIn("credentials", {
      email: validatedData.email,
      password: validatedData.password,
      redirect: false,
      ...(callbackUrl ? { callbackUrl } : {}),
    });

    if (hasSignInFailed(signInResult)) {
      return { status: "failed" };
    }

    return { status: "success" };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return { status: "invalid_data" };
    }

    return { status: "failed" };
  }
};

export type RegisterActionState = {
  status:
    | "idle"
    | "in_progress"
    | "success"
    | "failed"
    | "user_exists"
    | "invalid_data";
};

export const register = async (
  _: RegisterActionState,
  formData: FormData
): Promise<RegisterActionState> => {
  try {
    const validatedData = authFormSchema.parse({
      email: formData.get("email"),
      password: formData.get("password"),
    });

    const [user] = await getUser(validatedData.email);

    if (user) {
      return { status: "user_exists" } as RegisterActionState;
    }
    await createUser(validatedData.email, validatedData.password);

    const redirectUrl = formData.get("redirectUrl");
    const callbackUrl =
      typeof redirectUrl === "string" && redirectUrl.startsWith("/")
        ? redirectUrl
        : undefined;

    const signInResult = await signIn("credentials", {
      email: validatedData.email,
      password: validatedData.password,
      redirect: false,
      ...(callbackUrl ? { callbackUrl } : {}),
    });

    if (hasSignInFailed(signInResult)) {
      return { status: "failed" };
    }

    return { status: "success" };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return { status: "invalid_data" };
    }

    return { status: "failed" };
  }
};

const LOGIN_PATH = "/login";

const signInBaseUrl =
  process.env.NEXTAUTH_URL ??
  process.env.NEXT_PUBLIC_APP_URL ??
  "http://localhost:3000";

type SignInResult = Awaited<ReturnType<typeof signIn>>;

function hasSignInFailed(result: SignInResult): boolean {
  if (
    result &&
    typeof result === "object" &&
    "error" in result &&
    typeof result.error === "string" &&
    result.error
  ) {
    return true;
  }

  const resultUrl = extractUrlFromSignIn(result);

  if (!resultUrl) {
    return false;
  }

  try {
    const parsedUrl = new URL(resultUrl, signInBaseUrl);

    if (parsedUrl.searchParams.get("error")) {
      return true;
    }

    if (parsedUrl.pathname === LOGIN_PATH) {
      return true;
    }
  } catch {
    // Ignore invalid URLs and treat them as non-failures.
  }

  return false;
}

function extractUrlFromSignIn(result: SignInResult): string | undefined {
  if (typeof result === "string") {
    return result;
  }

  if (
    result &&
    typeof result === "object" &&
    "url" in result &&
    typeof result.url === "string"
  ) {
    return result.url;
  }

  return undefined;
}
