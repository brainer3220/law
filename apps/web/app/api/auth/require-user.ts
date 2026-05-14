import { createClient } from "@/lib/supabase/server";

export async function getAuthenticatedUserId(): Promise<string | null> {
  try {
    const supabase = await createClient();
    const {
      data: { user },
      error,
    } = await supabase.auth.getUser();
    if (error || !user?.id) {
      return null;
    }
    return user.id;
  } catch (error) {
    console.error("[auth] Failed to resolve authenticated user", error);
    return null;
  }
}

export async function requireAuthenticatedUserId(): Promise<string | Response> {
  const userId = await getAuthenticatedUserId();
  if (!userId) {
    return Response.json({ error: "Authentication required" }, { status: 401 });
  }
  return userId;
}
