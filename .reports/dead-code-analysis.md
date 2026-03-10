# Dead Code Analysis

Date: 2026-03-10

Scope: `apps/web`

## Commands Run

```bash
pnpm -C /Users/brainer/Programming/law/apps/web dlx knip --tsConfig tsconfig.json
pnpm -C /Users/brainer/Programming/law/apps/web dlx depcheck --ignores="@tailwindcss/oxide-linux-x64-gnu,lightningcss-linux-x64-gnu"
pnpm -C /Users/brainer/Programming/law/apps/web dlx ts-prune --project tsconfig.json
```

## Verification Gate

Every deletion batch was gated with:

```bash
PYTHONPATH="/Users/brainer/Programming/law/packages/py-shared/src" uv run pytest -q
pnpm -C /Users/brainer/Programming/law/apps/web run lint
pnpm -C /Users/brainer/Programming/law/apps/web exec tsc --noEmit
pnpm -C /Users/brainer/Programming/law/apps/web run build
```

Observed result for every gated run after cleanup batch application:

- `uv run pytest -q`: 58 passed
- `eslint`: 0 errors, 2 pre-existing warnings
- `tsc --noEmit`: passed
- `next build`: passed

Pre-existing lint warnings left unchanged:

- `apps/web/app/workspace/layout.tsx:180` `jsx-a11y/role-supports-aria-props`
- `apps/web/hooks/useRealtimeTranscriber.ts:338` `react-hooks/exhaustive-deps`

## Tool Summary

### knip

Highest-confidence findings:

- Unused files: `apps/web/components/Toast.tsx`, `apps/web/hooks/useLocalStorage.ts`
- Unused exports: `apps/web/app/api/share/service.ts:3`, `apps/web/app/api/share/service.ts:8`, `apps/web/app/api/share/service.ts:38`
- Unused exported types: several module-local prop/type exports plus unused data contracts in `apps/web/lib/types.ts` and `apps/web/lib/share/types.ts`

After the third cleanup pass, knip no longer reports unused files or unused code exports. Remaining knip output is dependency noise only.

Known false positives / noisy results:

- `@supabase/ssr`, `@supabase/supabase-js`, `tailwind-merge`, and `zod` were flagged as unused by knip, but are statically imported in `apps/web/lib/supabase/client.ts:5`, `apps/web/lib/supabase/server.ts:5`, `apps/web/lib/supabase/middleware.ts:5`, `apps/web/lib/auth/AuthContext.tsx:5`, `apps/web/lib/utils.ts:7`, and `apps/web/lib/workspace/client.ts:6`
- Next.js convention files and exports are undercounted by static import analysis

### depcheck

Observed to be noisy/inconsistent in this App Router project.

- It did not produce a trustworthy dependency-only deletion set
- It reported `@material/material-color-utilities` and `@material/web` as unused, but `@material/web` remains cautionary because Material custom elements/types appear in `apps/web/app/workspace/layout.tsx:152`, `apps/web/types/material.d.ts:13`, and `apps/web/app/globals.css:106`
- It previously reported a missing direct dependency for `@openai/chatkit` from `apps/web/lib/config.ts:1`; that has now been fixed by adding the package directly

Manual dependency audit outcome:

- Removed `@material/material-color-utilities` from `apps/web/package.json` and refreshed local install state via `npm uninstall`; full verification still passed
- Added `@openai/chatkit` as a direct dependency in `apps/web/package.json` because `apps/web/lib/config.ts:1` imports it directly; follow-up `depcheck` no longer reports it missing
- Converted `apps/web/lib/config.ts:1` to `import type`, but `knip` still reports `@openai/chatkit` as unused, so that flag appears to be tool noise rather than a dependency mismatch
- Removed `@material/web` from `apps/web/package.json` after confirming there were no imports in source or built `.next` output, and after route smoke checks still rendered `/workspace` successfully without it
- Added `postcss` as a direct dev dependency in `apps/web/package.json` because `apps/web/postcss.config.mjs:2` is an app-owned PostCSS config entrypoint; this clears the prior unlisted-dependency warning, although `depcheck` then classifies it as an unused dev dependency
- Kept `@supabase/ssr`, `@supabase/supabase-js`, `tailwind-merge`, and `zod` because they are statically imported in app code
- Kept `eslint-config-next`, `@tailwindcss/postcss`, `tailwindcss`, `typescript`, `@types/node`, and `@types/react-dom` because they are part of the active lint/build/typecheck toolchain

### ts-prune

Useful for export-level hints, but noisy for Next.js and generated `.next` types.

Strong signals from ts-prune:

- `apps/web/lib/auth/types.ts` exports were unused
- `apps/web/lib/utils.ts:48`, `apps/web/lib/utils.ts:74`, `apps/web/lib/utils.ts:122`, `apps/web/lib/utils.ts:141`, `apps/web/lib/utils.ts:154`, `apps/web/lib/utils.ts:174`, `apps/web/lib/utils.ts:181` exports are unused
- `apps/web/lib/share/types.ts:48`, `apps/web/lib/share/types.ts:62`, `apps/web/lib/share/types.ts:67` exports are unused
- `apps/web/lib/types.ts:78`, `apps/web/lib/types.ts:93`, `apps/web/lib/types.ts:135`, `apps/web/lib/types.ts:146`, `apps/web/lib/types.ts:157` exports are unused

False positives / expected noise:

- `apps/web/middleware.ts`, `apps/web/next.config.ts`, `apps/web/app/**/page.tsx`, and generated `.next/types/**`
- module-local exported prop interfaces used only inside their own files

## Severity Classification

### SAFE

Cleaned:

- Deleted `apps/web/hooks/useLocalStorage.ts` - no references found by repo search; verified by gated test/build run
- Deleted `apps/web/components/Toast.tsx` - no references found by repo search; verified by gated test/build run
- Deleted `apps/web/lib/auth/types.ts` - no references found by repo search; verified by gated test/build run
- Internalized share-service-only exports in `apps/web/app/api/share/service.ts` and removed unused `parseShareServiceJson`
- Removed unused helpers from `apps/web/lib/utils.ts`: `highlightText`, `parsePinCite`, `maskPII`, `formatFileSize`, `debounce`, `deepClone`, `chunkArray`
- Removed unused payload interfaces from `apps/web/lib/share/types.ts`: `ShareCreatePayload`, `ShareLinkCreatePayload`, `ShareRevokePayload`
- Removed unused app-wide interfaces from `apps/web/lib/types.ts`: `DocumentMetadata`, `Matter`, `CitationVerificationResult`, `UserPermissions`, `AuditLogEntry`
- Removed unused dependency `@material/material-color-utilities` from `apps/web/package.json`
- Removed unused dependency `@material/web` from `apps/web/package.json`
- Added direct dependency `@openai/chatkit` to `apps/web/package.json` to match actual imports in `apps/web/lib/config.ts:1`
- Added direct dev dependency `postcss` to `apps/web/package.json` to match `apps/web/postcss.config.mjs:2`
- Converted `apps/web/lib/config.ts:1` to a type-only import for `StartScreenPrompt`

No remaining safe code-deletion candidates were confirmed in this pass beyond dependency review.

### CAUTION

- `apps/web/app/demo/page.tsx` - likely demo-only, but it is still a real route
- Demo-only component chain rooted from `apps/web/app/demo/page.tsx`: `apps/web/components/SearchBar.tsx`, `apps/web/components/StatusBadge.tsx`, `apps/web/components/ClauseDiffCard.tsx`, `apps/web/components/CitationPopover.tsx`, `apps/web/components/ClaimEvidenceMatrix.tsx`, `apps/web/components/PolicyViolationAlert.tsx`, `apps/web/components/ProvenanceFooter.tsx`, plus adjacent demo-support components

### DANGER

- `apps/web/middleware.ts`
- `apps/web/next.config.ts`
- `apps/web/next-env.d.ts`
- `apps/web/types/material.d.ts`
- All Next App Router entrypoints in `apps/web/app/**/page.tsx`, `apps/web/app/**/layout.tsx`, and `apps/web/app/**/route.ts`

These are convention-driven entrypoints or ambient type files and should not be deleted based on import graphs alone.

## Cleanup Applied

Deleted:

- `apps/web/hooks/useLocalStorage.ts`
- `apps/web/components/Toast.tsx`
- `apps/web/lib/auth/types.ts`

Refactored to remove dead exports and dead helpers:

- `apps/web/app/api/share/service.ts`
- `apps/web/lib/utils.ts`
- `apps/web/lib/share/types.ts`
- `apps/web/lib/types.ts`

Refactored to internalize module-local types and props:

- `apps/web/components/CitationPopover.tsx`
- `apps/web/components/ClaimEvidenceMatrix.tsx`
- `apps/web/components/ClauseDiffCard.tsx`
- `apps/web/components/EvidenceCard.tsx`
- `apps/web/components/LoadingSpinner.tsx`
- `apps/web/components/PolicyViolationAlert.tsx`
- `apps/web/components/ProvenanceFooter.tsx`
- `apps/web/components/RiskBadge.tsx`
- `apps/web/components/SearchBar.tsx`
- `apps/web/components/StatusBadge.tsx`
- `apps/web/hooks/useColorScheme.ts`
- `apps/web/hooks/useRealtimeTranscriber.ts`

Dependency cleanup applied:

- `apps/web/package.json`
- `apps/web/package-lock.json`

Verification-enabler fixes applied before cleanup runs:

- Removed an unused import and corrected `FormData` typing in `apps/web/app/api/transcribe/route.ts`
- Replaced timer types with runtime-safe `ReturnType<typeof setInterval>` / `ReturnType<typeof setTimeout>` in `apps/web/app/api/transcribe/live/route.ts` and `apps/web/lib/utils.ts`

These fixes were required because the existing verification gate did not pass before cleanup.

## Recommendation

Next safest follow-up work would be refining remaining noisy dependency/tooling signals, especially documenting `knip` false positives for `@openai/chatkit` and deciding whether to ignore known build-tool false positives from `depcheck` for `postcss`, `tailwindcss`, and related dev tooling.
