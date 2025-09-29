"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { useEffect } from "react";
import {
  identifyAmplitudeUser,
  initializeAmplitude,
  trackAmplitudeEvent,
  trackPageView,
} from "@/lib/analytics/amplitude";

export function AmplitudeProvider() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { data: session } = useSession();

  useEffect(() => {
    initializeAmplitude();
  }, []);

  useEffect(() => {
    if (!session?.user) {
      identifyAmplitudeUser(null);
      return;
    }

    identifyAmplitudeUser(session.user.id, {
      email: session.user.email,
      name: session.user.name,
      plan: session.user.type,
    });
  }, [session?.user]);

  useEffect(() => {
    if (!pathname) {
      return;
    }

    const search = searchParams?.toString();
    trackPageView({
      pathname,
      search: search ? `?${search}` : undefined,
      title: typeof document !== "undefined" ? document.title : undefined,
    });
  }, [pathname, searchParams]);

  useEffect(() => {
    if (!session?.user) {
      return;
    }

    trackAmplitudeEvent("session_active", {
      userId: session.user.id,
      plan: session.user.type,
    });
  }, [session?.user]);

  return null;
}

