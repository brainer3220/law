from packages.legal_tools.lexical import (
    LexicalVariant,
    build_query_variants,
    expand_with_synonyms,
    normalize_token,
)
from packages.legal_tools.pg_search import PgDoc, _rrf_fuse


def test_normalize_token_strips_particles():
    assert normalize_token("근로자의") == "근로자"
    assert normalize_token("손해배상은") == "손해배상"


def test_expand_with_synonyms_returns_expected_terms():
    expanded = expand_with_synonyms(["손해배상"])
    assert "손해배상" in expanded
    assert set(expanded) >= {"손해배상", "배상", "손배", "손해보상"}


def test_build_query_variants_includes_synonym_and_phrase():
    variants = build_query_variants("근로자 손해배상")
    names = {v.name for v in variants}
    assert {"base", "title", "synonym", "phrase"}.issubset(names)


def test_rrf_fuse_prioritizes_title_boost():
    base = LexicalVariant(name="base", query="foo", fields=("title", "body"), boost=1.0)
    title = LexicalVariant(name="title", query="foo", fields=("title",), boost=1.25)
    doc1 = PgDoc(id="1", doc_id="doc1", title="A", path="", body="", snippet="", score=1.0)
    doc2 = PgDoc(id="2", doc_id="doc2", title="B", path="", body="", snippet="", score=0.8)
    results = [
        (base, [doc1, doc2]),
        (title, [doc2, doc1]),
    ]
    fused = _rrf_fuse(results, limit=2, offset=0, k=60.0)
    assert [doc.doc_id for doc in fused] == ["doc2", "doc1"]
    assert fused[0].score_components["title"] > fused[0].score_components["base"]
    assert fused[0].score_components["raw:title"] == 0.8
