import type {
  AuditLogResponse,
  PermissionEntry,
  ShareLinkCreateResponse,
  ShareMode,
  ShareResponse,
} from "./types";

export interface ShareCreateRequest {
  resourceId: string;
  actorId: string;
  mode: ShareMode;
  allowDownload: boolean;
  allowComments: boolean;
  isLive: boolean;
  expiresAt?: string | null;
  createLink: boolean;
  linkDomainWhitelist?: string[];
  allowReshare: boolean;
  permissions?: PermissionEntry[];
}

export interface ShareLinkRequest {
  actorId: string;
  domainWhitelist?: string[];
}

export interface ShareRevokeRequest {
  actorId: string;
}

function resolveJsonHeaders(): HeadersInit {
  return {
    "Content-Type": "application/json",
  };
}

async function resolveJsonResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => null)) as T | null;
  if (!response.ok || !payload) {
    throw new Error(payload && (payload as { error?: string }).error
      ? String((payload as { error?: string }).error)
      : `Share service request failed with status ${response.status}`);
  }
  return payload;
}

export async function createShare(request: ShareCreateRequest): Promise<ShareResponse> {
  const response = await fetch("/api/share", {
    method: "POST",
    headers: resolveJsonHeaders(),
    body: JSON.stringify({
      resource_id: request.resourceId,
      actor_id: request.actorId,
      mode: request.mode,
      allow_download: request.allowDownload,
      allow_comments: request.allowComments,
      is_live: request.isLive,
      expires_at: request.expiresAt ?? null,
      create_link: request.createLink,
      link_domain_whitelist:
        request.linkDomainWhitelist && request.linkDomainWhitelist.length > 0
          ? request.linkDomainWhitelist
          : null,
      allow_reshare: request.allowReshare,
      permissions: request.permissions ?? undefined,
    }),
  });

  return resolveJsonResponse<ShareResponse>(response);
}

export async function fetchShare(shareId: string): Promise<ShareResponse> {
  const response = await fetch(`/api/share/${shareId}`);
  return resolveJsonResponse<ShareResponse>(response);
}

export async function revokeShare(
  shareId: string,
  request: ShareRevokeRequest
): Promise<ShareResponse> {
  const response = await fetch(`/api/share/${shareId}/revoke`, {
    method: "POST",
    headers: resolveJsonHeaders(),
    body: JSON.stringify({
      actor_id: request.actorId,
    }),
  });
  return resolveJsonResponse<ShareResponse>(response);
}

export async function createShareLink(
  shareId: string,
  request: ShareLinkRequest
): Promise<ShareLinkCreateResponse> {
  const response = await fetch(`/api/share/${shareId}/links`, {
    method: "POST",
    headers: resolveJsonHeaders(),
    body: JSON.stringify({
      actor_id: request.actorId,
      domain_whitelist:
        request.domainWhitelist && request.domainWhitelist.length > 0
          ? request.domainWhitelist
          : null,
    }),
  });
  return resolveJsonResponse<ShareLinkCreateResponse>(response);
}

export async function fetchAuditLogs(resourceId: string): Promise<AuditLogResponse> {
  const response = await fetch(`/api/share/audit?resourceId=${encodeURIComponent(resourceId)}`);
  return resolveJsonResponse<AuditLogResponse>(response);
}
