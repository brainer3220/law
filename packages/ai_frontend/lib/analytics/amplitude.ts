"use client";

import { Identify, identify, init, setUserId, track } from "@amplitude/analytics-browser";

type EventProperties = Record<string, unknown> | undefined;

let isInitialized = false;
let currentUserId: string | null = null;

const AMPLITUDE_DEFAULT_CONFIG = {
  defaultTracking: {
    attribution: false,
    sessions: true,
    pageViews: false,
    formInteractions: false,
    fileDownloads: false,
  },
};

function sanitizeProperties(properties?: EventProperties): EventProperties {
  if (!properties) {
    return undefined;
  }

  return Object.fromEntries(
    Object.entries(properties).filter(([, value]) => value !== undefined && value !== null)
  );
}

export function initializeAmplitude() {
  if (isInitialized) {
    return;
  }

  if (typeof window === "undefined") {
    return;
  }

  const apiKey = process.env.NEXT_PUBLIC_AMPLITUDE_API_KEY;
  if (!apiKey) {
    return;
  }

  init(apiKey, undefined, AMPLITUDE_DEFAULT_CONFIG);
  isInitialized = true;
}

export function trackAmplitudeEvent(
  eventName: string,
  properties?: EventProperties,
) {
  initializeAmplitude();

  if (!isInitialized) {
    return;
  }

  track(eventName, sanitizeProperties(properties));
}

export function identifyAmplitudeUser(
  userId: string | null | undefined,
  traits?: Record<string, unknown>,
) {
  initializeAmplitude();

  if (!isInitialized) {
    return;
  }

  if (userId && userId !== currentUserId) {
    setUserId(userId);
    currentUserId = userId;
  }

  if (!traits) {
    return;
  }

  const identity = new Identify();
  Object.entries(traits).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      identity.set(key, value);
    }
  });

  identify(identity);
}

export function trackPageView(details: {
  pathname: string;
  search?: string;
  title?: string;
}) {
  const { pathname, search, title } = details;
  trackAmplitudeEvent("page_view", {
    pathname,
    search,
    title,
  });
}

