# TODOS

## Review

### Citation canonicalization spike

**What:** Define and prototype a canonical citation layer for Korean cases/statutes so verifier, gold set, and UI all point at the same normalized source identity.

**Why:** Claim verification and conflict handling will drift if 사건번호, 사건명, 법원명, and 선고일 variants are treated as different sources.

**Context:** The approved design depends on claim-level verification, conflict policy, and provenance rendering. Those all assume the system can map multiple citation spellings to one canonical key. Start by defining a normalized key shape and collecting common variant patterns from the existing corpus and APIs.

**Effort:** M
**Priority:** P1
**Depends on:** None

### Source availability and licensing spike

**What:** Verify that the official and practical data sources for Korean statutes/case law are reliable enough, and permitted enough, to support a verifier-first product.

**Why:** If source coverage, uptime, terms, or access patterns are too weak, the verifier architecture fails before UX matters.

**Context:** The current plan assumes law.go.kr, internal corpora, and official legal sources are sufficient for claim-level verification. Before investing deeper in Gate 1 web UX, confirm coverage, access stability, usage restrictions, and real-world adequacy for target lawyer questions.

**Effort:** M
**Priority:** P1
**Depends on:** None

### Gold-set adjudication protocol

**What:** Define who builds the legal evaluation set, how disagreements are resolved, and what counts as fabricated, stale, partial, or unavailable.

**Why:** Without a real adjudication protocol, the evaluation will look rigorous while still encoding reviewer opinion.

**Context:** The design already calls for a gold set and double review, but the scoring process is still underspecified. Document reviewer roles, disagreement handling, borderline-case policy, and error taxonomy so future regression tests and pilot claims are reproducible.

**Effort:** M
**Priority:** P1
**Depends on:** Citation canonicalization spike, Source availability and licensing spike

## Completed
