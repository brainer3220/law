export type ShareMode = "private" | "org" | "unlisted" | "public" | "embed";

export type PermissionRole =
  | "owner"
  | "editor"
  | "commenter"
  | "viewer"
  | "guest";

export interface ShareLink {
  id: string;
  domain_whitelist: string[] | null;
  created_at: string;
  revoked_at: string | null;
}

export interface ShareResponse {
  id: string;
  resource: {
    id: string;
    type: string;
    owner_id: string;
    org_id: string | null;
    title: string | null;
    tags: string[] | null;
    version: string | null;
    snapshot_of: string | null;
    created_at: string;
    updated_at: string | null;
  };
  mode: ShareMode;
  allow_download: boolean;
  allow_comments: boolean;
  is_live: boolean;
  created_by: string;
  created_at: string;
  expires_at: string | null;
  revoked_at: string | null;
  links: ShareLink[];
}

export interface ShareLinkCreateResponse {
  token: string;
  url: string;
  link: ShareLink;
}

export interface ShareCreatePayload {
  resource_id: string;
  actor_id: string;
  mode: ShareMode;
  allow_download: boolean;
  allow_comments: boolean;
  is_live: boolean;
  expires_at: string | null;
  create_link: boolean;
  link_domain_whitelist: string[] | null;
  allow_reshare: boolean;
  permissions?: PermissionEntry[];
}

export interface ShareLinkCreatePayload {
  actor_id: string;
  domain_whitelist?: string[] | null;
}

export interface ShareRevokePayload {
  actor_id: string;
}

export interface PermissionEntry {
  resource_id: string;
  principal_type: "user" | "team" | "org" | "link";
  principal_id: string;
  role: PermissionRole;
}

export interface AuditLogEntry {
  id: string;
  actor_id: string | null;
  action: string;
  resource_id: string | null;
  context_json: Record<string, unknown> | null;
  created_at: string;
  ip: string | null;
  ua: string | null;
}

export interface AuditLogResponse {
  results: AuditLogEntry[];
}
