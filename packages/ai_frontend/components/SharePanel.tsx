"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createShare,
  createShareLink,
  fetchAuditLogs,
  fetchShare,
  revokeShare,
  type ShareCreateRequest,
} from "@/lib/share/client";
import type {
  AuditLogEntry,
  ShareLink,
  ShareLinkCreateResponse,
  ShareMode,
  ShareResponse,
} from "@/lib/share/types";
import { cn, formatDate } from "@/lib/utils";

const SHARE_MODES: Array<{
  value: ShareMode;
  label: string;
  description: string;
}> = [
  {
    value: "private",
    label: "비공개",
    description: "소유자와 명시적으로 권한을 부여한 사용자만 접근합니다.",
  },
  {
    value: "org",
    label: "조직 공유",
    description: "같은 조직 ID를 가진 사용자에게 열람 권한을 부여합니다.",
  },
  {
    value: "unlisted",
    label: "링크 공유",
    description: "토큰 기반 링크를 가진 사람만 접근할 수 있습니다.",
  },
  {
    value: "public",
    label: "공개",
    description: "별도 인증 없이 누구나 열람이 가능합니다.",
  },
  {
    value: "embed",
    label: "임베드",
    description: "임베드 토큰을 활용해 외부 서비스에 삽입합니다.",
  },
];

type SharePanelProps = {
  open: boolean;
  onClose: () => void;
  threadId: string | null;
};

type ShareStatus = "idle" | "loading" | "ready";

const CHATKIT_SESSION_COOKIE = "chatkit_session_id";

export function SharePanel({ open, onClose, threadId }: SharePanelProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [resourceId, setResourceId] = useState("");
  const [mode, setMode] = useState<ShareMode>("unlisted");
  const [allowDownload, setAllowDownload] = useState(false);
  const [allowComments, setAllowComments] = useState(true);
  const [allowReshare, setAllowReshare] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const [expiresAtInput, setExpiresAtInput] = useState("");
  const [domainInput, setDomainInput] = useState("");
  const [domainWhitelist, setDomainWhitelist] = useState<string[]>([]);
  const [share, setShare] = useState<ShareResponse | null>(null);
  const [shareStatus, setShareStatus] = useState<ShareStatus>("idle");
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [creatingShare, setCreatingShare] = useState(false);
  const [creatingLink, setCreatingLink] = useState(false);
  const [revokingShare, setRevokingShare] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [lastLinkResponse, setLastLinkResponse] =
    useState<ShareLinkCreateResponse | null>(null);
  const [storedShareId, setStoredShareId] = useState<string | null>(null);

  const storageKey = useMemo(() => {
    if (!threadId) {
      return null;
    }
    return `share:thread:${threadId}`;
  }, [threadId]);

  const latestActiveLink = useMemo<ShareLink | undefined>(() => {
    if (!share) {
      return undefined;
    }
    const active = share.links.find((link) => !link.revoked_at);
    return active ?? share.links.slice(-1)[0];
  }, [share]);

  const actorId = useMemo(() => {
    if (typeof document === "undefined") {
      return "anonymous";
    }
    const cookieValue = getCookie(CHATKIT_SESSION_COOKIE);
    return cookieValue ?? "anonymous";
  }, [storedShareId, open]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const handleClickOutside = (event: MouseEvent) => {
      if (!panelRef.current) {
        return;
      }
      if (
        event.target instanceof Node &&
        !panelRef.current.contains(event.target)
      ) {
        onClose();
      }
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open, onClose]);

  useEffect(() => {
    if (!open) {
      return;
    }
    setErrorMessage(null);
    setSuccessMessage(null);
    if (threadId) {
      setResourceId(threadId);
    } else if (!resourceId) {
      setResourceId("");
    }
  }, [open, threadId]);

  useEffect(() => {
    if (!open || !storageKey) {
      return;
    }
    try {
      const stored = localStorage.getItem(storageKey);
      if (!stored) {
        setStoredShareId(null);
        setShare(null);
        setShareStatus("idle");
        return;
      }
      const parsed = JSON.parse(stored) as { shareId?: string } | null;
      if (parsed?.shareId) {
        setStoredShareId(parsed.shareId);
      } else {
        setStoredShareId(null);
      }
    } catch (error) {
      console.warn("[SharePanel] Failed to parse stored share id", error);
      setStoredShareId(null);
    }
  }, [open, storageKey]);

  useEffect(() => {
    if (!open) {
      return;
    }
    if (!storedShareId) {
      setShare(null);
      setShareStatus("idle");
      return;
    }

    let cancelled = false;
    const load = async () => {
      setShareStatus("loading");
      setErrorMessage(null);
      try {
        const response = await fetchShare(storedShareId);
        if (cancelled) {
          return;
        }
        setShare(response);
        setShareStatus("ready");
      } catch (error) {
        console.error("[SharePanel] Failed to fetch share", error);
        if (!cancelled) {
          setErrorMessage(
            error instanceof Error ? error.message : "공유 정보를 불러오지 못했습니다."
          );
          setShare(null);
          setShareStatus("idle");
          if (storageKey) {
            localStorage.removeItem(storageKey);
          }
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [open, storedShareId, storageKey]);

  const loadAuditLogs = useCallback(async (resource: string) => {
    try {
      const response = await fetchAuditLogs(resource);
      setAuditLogs(response.results.slice(0, 15));
    } catch (error) {
      console.error("[SharePanel] Failed to load audit logs", error);
    }
  }, []);

  useEffect(() => {
    if (!share) {
      return;
    }
    setMode(share.mode);
    setAllowDownload(share.allow_download);
    setAllowComments(share.allow_comments);
    setIsLive(share.is_live);
    setExpiresAtInput(
      share.expires_at ? toLocalDateTimeInput(share.expires_at) : ""
    );
    if (latestActiveLink?.domain_whitelist) {
      setDomainWhitelist(latestActiveLink.domain_whitelist);
    }
    if (share.resource?.id) {
      setResourceId(share.resource.id);
      void loadAuditLogs(share.resource.id);
    }
  }, [share, latestActiveLink, loadAuditLogs]);

  const persistShareId = useCallback(
    (id: string | null) => {
      if (!storageKey) {
        return;
      }
      if (!id) {
        localStorage.removeItem(storageKey);
        return;
      }
      localStorage.setItem(storageKey, JSON.stringify({ shareId: id }));
    },
    [storageKey]
  );

  const handleCreateShare = useCallback(async () => {
    if (!resourceId.trim()) {
      setErrorMessage("리소스 ID를 입력하세요.");
      return;
    }
    setCreatingShare(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    const payload: ShareCreateRequest = {
      resourceId: resourceId.trim(),
      actorId,
      mode,
      allowDownload,
      allowComments,
      isLive,
      expiresAt: expiresAtInput ? fromLocalDateTimeInput(expiresAtInput) : null,
      createLink: true,
      linkDomainWhitelist: domainWhitelist,
      allowReshare,
    };

    try {
      const response = await createShare(payload);
      setShare(response);
      persistShareId(response.id);
      setStoredShareId(response.id);
      setSuccessMessage("공유를 생성했습니다. 링크가 준비되었습니다.");
      setShareStatus("ready");
      if (response.resource?.id) {
        void loadAuditLogs(response.resource.id);
      }
    } catch (error) {
      console.error("[SharePanel] Failed to create share", error);
      setErrorMessage(
        error instanceof Error ? error.message : "공유 생성에 실패했습니다."
      );
    } finally {
      setCreatingShare(false);
    }
  }, [
    resourceId,
    actorId,
    mode,
    allowDownload,
    allowComments,
    isLive,
    expiresAtInput,
    domainWhitelist,
    allowReshare,
    persistShareId,
    loadAuditLogs,
  ]);

  const handleCreateLink = useCallback(async () => {
    if (!share?.id) {
      setErrorMessage("먼저 공유를 생성하세요.");
      return;
    }
    setCreatingLink(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const response = await createShareLink(share.id, {
        actorId,
        domainWhitelist,
      });
      setLastLinkResponse(response);
      setSuccessMessage("새 공유 링크를 발급했습니다.");
      setShare((prev) =>
        prev
          ? {
              ...prev,
              links: [...prev.links, response.link],
            }
          : prev
      );
    } catch (error) {
      console.error("[SharePanel] Failed to create share link", error);
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "공유 링크 발급에 실패했습니다."
      );
    } finally {
      setCreatingLink(false);
    }
  }, [share, actorId, domainWhitelist]);

  const handleRevoke = useCallback(async () => {
    if (!share?.id) {
      return;
    }
    setRevokingShare(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const response = await revokeShare(share.id, { actorId });
      setShare(response);
      persistShareId(response.id);
      setSuccessMessage("공유를 회수했습니다.");
    } catch (error) {
      console.error("[SharePanel] Failed to revoke share", error);
      setErrorMessage(
        error instanceof Error ? error.message : "공유 회수에 실패했습니다."
      );
    } finally {
      setRevokingShare(false);
    }
  }, [share, actorId, persistShareId]);

  const handleAddDomain = useCallback(() => {
    const value = domainInput.trim();
    if (!value) {
      return;
    }
    setDomainWhitelist((prev) => {
      if (prev.includes(value)) {
        return prev;
      }
      return [...prev, value];
    });
    setDomainInput("");
  }, [domainInput]);

  const handleRemoveDomain = useCallback((domain: string) => {
    setDomainWhitelist((prev) => prev.filter((item) => item !== domain));
  }, []);

  const handleCopyLink = useCallback(
    async (url: string) => {
      try {
        await navigator.clipboard.writeText(url);
        setSuccessMessage("클립보드에 링크를 복사했습니다.");
      } catch (error) {
        console.error("[SharePanel] Failed to copy share link", error);
        setErrorMessage("링크 복사에 실패했습니다.");
      }
    },
    []
  );

  if (!open) {
    return null;
  }

  return (
    <div
      ref={panelRef}
      className="absolute right-5 top-5 z-50 w-full max-w-md max-h-[85vh] overflow-y-auto rounded-xl border border-slate-200 bg-white/95 p-5 shadow-xl backdrop-blur dark:border-slate-700 dark:bg-slate-900/95"
    >
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            공유 설정
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Share 서비스와 연결해 대화/문서를 배포하세요.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        >
          <span className="sr-only">닫기</span>
          ×
        </button>
      </div>

      <section aria-label="share-messages" className="mt-3 space-y-2">
        {errorMessage ? (
          <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
            {errorMessage}
          </div>
        ) : null}
        {successMessage ? (
          <div className="rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
            {successMessage}
          </div>
        ) : null}
      </section>

      <section aria-label="resource" className="mt-4 space-y-3">
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
          리소스 ID
          <input
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:focus:border-slate-400 dark:focus:ring-slate-700"
            value={resourceId}
            placeholder="ex) conversation UUID"
            onChange={(event) => setResourceId(event.target.value)}
          />
        </label>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          ChatKit 스레드 ID를 그대로 사용하거나, Share 서비스에서 생성한 리소스 UUID를
          입력하세요.
        </p>
      </section>

      <section aria-label="share-mode" className="mt-5 space-y-3">
        <div>
          <h3 className="text-sm font-medium text-slate-700 dark:text-slate-200">
            공유 모드
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Share 서비스의 ShareMode(enum)와 매핑됩니다.
          </p>
        </div>
        <div className="space-y-2">
          {SHARE_MODES.map((option) => (
            <label
              key={option.value}
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2 transition",
                mode === option.value
                  ? "border-slate-800 bg-slate-100 dark:border-slate-200 dark:bg-slate-800"
                  : "border-slate-200 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600"
              )}
            >
              <input
                type="radio"
                name="share-mode"
                value={option.value}
                checked={mode === option.value}
                onChange={() => setMode(option.value)}
                className="mt-1"
              />
              <span>
                <span className="block text-sm font-medium text-slate-800 dark:text-slate-100">
                  {option.label}
                </span>
                <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">
                  {option.description}
                </span>
              </span>
            </label>
          ))}
        </div>
      </section>

      <section aria-label="share-options" className="mt-5 space-y-2">
        <h3 className="text-sm font-medium text-slate-700 dark:text-slate-200">
          추가 옵션
        </h3>
        <div className="space-y-2">
          <CheckboxRow
            label="다운로드 허용"
            description="PDF/원문 다운로드를 허용합니다."
            checked={allowDownload}
            onChange={setAllowDownload}
          />
          <CheckboxRow
            label="댓글 허용"
            description="공유 받은 사용자가 댓글을 남길 수 있습니다."
            checked={allowComments}
            onChange={setAllowComments}
          />
          <CheckboxRow
            label="실시간 동기화"
            description="최신 버전을 실시간으로 반영합니다."
            checked={isLive}
            onChange={setIsLive}
          />
          <CheckboxRow
            label="재공유 허용"
            description="공유 받은 사용자가 추가로 링크를 발급할 수 있습니다."
            checked={allowReshare}
            onChange={setAllowReshare}
          />
        </div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
          만료 시각
          <input
            type="datetime-local"
            value={expiresAtInput}
            onChange={(event) => setExpiresAtInput(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:focus:border-slate-400 dark:focus:ring-slate-700"
          />
          <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">
            비워두면 ShareSettings.default_link_ttl_days 값이 적용됩니다.
          </span>
        </label>
      </section>

      <section aria-label="domain-whitelist" className="mt-5 space-y-3">
        <div>
          <h3 className="text-sm font-medium text-slate-700 dark:text-slate-200">
            링크 도메인 화이트리스트
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            링크 발급 시 ShareLink.domain_whitelist 필드로 전달됩니다.
          </p>
        </div>
        <div className="flex gap-2">
          <input
            value={domainInput}
            onChange={(event) => setDomainInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                handleAddDomain();
              }
            }}
            className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:focus:border-slate-400 dark:focus:ring-slate-700"
            placeholder="example.com"
          />
          <button
            type="button"
            onClick={handleAddDomain}
            className="rounded-md border border-slate-300 bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700"
          >
            추가
          </button>
        </div>
        {domainWhitelist.length > 0 ? (
          <ul className="flex flex-wrap gap-2">
            {domainWhitelist.map((domain) => (
              <li
                key={domain}
                className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-100"
              >
                <span>{domain}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveDomain(domain)}
                  className="text-slate-500 transition hover:text-slate-800 dark:hover:text-slate-200"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            비워두면 링크에 도메인 제한이 적용되지 않습니다.
          </p>
        )}
      </section>

      <section aria-label="share-actions" className="mt-6 space-y-2">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleCreateShare}
            disabled={creatingShare}
            className="flex-1 rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
          >
            {creatingShare ? "생성 중..." : "공유 생성"}
          </button>
          <button
            type="button"
            onClick={handleCreateLink}
            disabled={creatingLink || !share}
            className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
          >
            {creatingLink ? "발급 중..." : "새 링크 발급"}
          </button>
        </div>
        <button
          type="button"
          onClick={handleRevoke}
          disabled={revokingShare || !share}
          className="w-full rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:text-red-400 dark:border-red-900 dark:bg-red-950 dark:text-red-200 dark:hover:bg-red-900"
        >
          {revokingShare ? "회수 중..." : "공유 회수"}
        </button>
      </section>

      <section aria-label="share-summary" className="mt-6 space-y-4">
        <header>
          <h3 className="text-sm font-medium text-slate-700 dark:text-slate-200">
            공유 정보
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            ShareService.create_share → ShareResponse 구조와 매핑됩니다.
          </p>
        </header>
        {shareStatus === "loading" ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            공유 정보를 불러오는 중입니다...
          </p>
        ) : share ? (
          <div className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
            <div className="space-y-1">
              <InfoRow label="공유 ID" value={share.id} />
              <InfoRow
                label="리소스"
                value={`${share.resource.type ?? "resource"} · ${
                  share.resource.title ?? share.resource.id
                }`}
              />
              <InfoRow
                label="모드"
                value={SHARE_MODES.find((item) => item.value === share.mode)?.label}
              />
              <InfoRow
                label="생성자"
                value={`${share.created_by} · ${formatDate(share.created_at)}`}
              />
              <InfoRow
                label="만료일"
                value={
                  share.expires_at
                    ? formatDate(share.expires_at)
                    : "만료 설정 없음"
                }
              />
              <InfoRow
                label="상태"
                value={
                  share.revoked_at
                    ? `회수됨 (${formatDate(share.revoked_at)})`
                    : "활성"
                }
              />
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                발급된 링크
              </h4>
              {share.links.length === 0 ? (
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  아직 발급된 링크가 없습니다. 새 링크를 만들어 보세요.
                </p>
              ) : (
                <ul className="mt-2 space-y-2 text-xs">
                  {share.links.map((link) => (
                    <li
                      key={link.id}
                      className="rounded-md border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-slate-700 dark:text-slate-100">
                          {link.id}
                        </span>
                        <span
                          className={cn(
                            "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                            link.revoked_at
                              ? "bg-red-50 text-red-600 dark:bg-red-950 dark:text-red-200"
                              : "bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-200"
                          )}
                        >
                          {link.revoked_at ? "revoked" : "active"}
                        </span>
                      </div>
                      <p className="mt-1">
                        생성일: {formatDate(link.created_at)}
                        {link.revoked_at
                          ? ` · 회수: ${formatDate(link.revoked_at)}`
                          : null}
                      </p>
                      {link.domain_whitelist && link.domain_whitelist.length > 0 ? (
                        <p className="mt-1">
                          허용 도메인: {link.domain_whitelist.join(", ")}
                        </p>
                      ) : (
                        <p className="mt-1 text-slate-500 dark:text-slate-400">
                          도메인 제한 없음
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {lastLinkResponse ? (
              <div className="rounded-md border border-emerald-200 bg-white px-3 py-2 text-xs text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200">
                <div className="flex items-center justify-between">
                  <span className="font-semibold">마지막으로 발급한 링크</span>
                  <button
                    type="button"
                    onClick={() => handleCopyLink(lastLinkResponse.url)}
                    className="text-[11px] font-semibold text-emerald-700 underline underline-offset-2 transition hover:text-emerald-600 dark:text-emerald-300 dark:hover:text-emerald-200"
                  >
                    복사
                  </button>
                </div>
                <p className="mt-1 break-all text-emerald-800 dark:text-emerald-100">
                  {lastLinkResponse.url}
                </p>
                <p className="mt-1 text-slate-500 dark:text-slate-400">
                  토큰: {lastLinkResponse.token}
                </p>
              </div>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            아직 공유 정보가 없습니다. 설정을 구성한 뒤 &lsquo;공유 생성&rsquo;을 눌러보세요.
          </p>
        )}
      </section>

      <section aria-label="audit-logs" className="mt-6 space-y-3">
        <header>
          <h3 className="text-sm font-medium text-slate-700 dark:text-slate-200">
            감사 로그
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            ShareService.list_audit_logs → AuditLogResponse.results (최근 15건)
          </p>
        </header>
        {auditLogs.length === 0 ? (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            아직 감사 로그가 없습니다.
          </p>
        ) : (
          <ul className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200">
            {auditLogs.map((log) => (
              <li
                key={log.id}
                className="rounded-md border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold text-slate-800 dark:text-slate-100">
                    {log.action}
                  </span>
                  <span className="text-[11px] text-slate-500 dark:text-slate-400">
                    {formatDate(log.created_at)}
                  </span>
                </div>
                <div className="mt-1 space-y-1 text-slate-600 dark:text-slate-300">
                  <p>Actor: {log.actor_id ?? "system"}</p>
                  {log.ip ? <p>IP: {log.ip}</p> : null}
                  {log.ua ? <p>UA: {log.ua}</p> : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

type CheckboxRowProps = {
  label: string;
  description: string;
  checked: boolean;
  onChange: (next: boolean) => void;
};

function CheckboxRow({ label, description, checked, onChange }: CheckboxRowProps) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 px-3 py-2 transition hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-1"
      />
      <span>
        <span className="block text-sm font-medium text-slate-700 dark:text-slate-100">
          {label}
        </span>
        <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">
          {description}
        </span>
      </span>
    </label>
  );
}

type InfoRowProps = {
  label: string;
  value?: string | null;
};

function InfoRow({ label, value }: InfoRowProps) {
  return (
    <p className="flex flex-col text-xs text-slate-600 dark:text-slate-300">
      <span className="font-semibold text-slate-700 dark:text-slate-100">
        {label}
      </span>
      <span className="mt-0.5 break-words">
        {value ?? <span className="text-slate-400">정보 없음</span>}
      </span>
    </p>
  );
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }
  const pattern = `(?:^|; )${name}=([^;]*)`;
  const match = document.cookie.match(new RegExp(pattern));
  return match ? decodeURIComponent(match[1]) : null;
}

function toLocalDateTimeInput(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60 * 1000);
  return local.toISOString().slice(0, 16);
}

function fromLocalDateTimeInput(value: string): string {
  const date = new Date(value);
  return date.toISOString();
}
