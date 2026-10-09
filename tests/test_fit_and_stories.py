"""vouch_fit (fit, eligibility, liveness) and the story bank checks."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "vouch" / "scripts"))

import vouch_ats  # noqa: E402
import vouch_common as vc  # noqa: E402
import vouch_corpus  # noqa: E402
import vouch_fit  # noqa: E402

CORPUS = ROOT / "examples" / "corpus"
JD = (ROOT / "examples" / "jd-backend.txt").read_text(encoding="utf-8")


def test_fit_scores_coverage_and_lists_true_gaps():
    r = vouch_fit.assess_fit(JD, vc.load_corpus(CORPUS), vouch_fit.load_profile(CORPUS))
    assert 1.0 <= r["score"] <= 5.0
    assert "kafka" in r["gaps"] and "kafka" not in r["must_covered"]
    assert "postgresql" in r["must_covered"]
    assert r["records"]


def test_spelling_variants_and_versions_are_known():
    vocab = {"node.js", "vue 3", "scss", "postgresql 18"}
    for term in ("node", "nodejs", "vue", "vuejs", "sass", "postgresql", "postgres"):
        assert vouch_ats._known_to_corpus(term, vocab), term


def test_eligibility_quotes_blockers_and_softens_contradictions():
    e = vouch_fit.check_eligibility("We are unable to provide visa sponsorship for this role.", {})
    assert e["verdict"] == "blocker" and "sponsorship" in e["findings"][0]["quote"]
    both = vouch_fit.check_eligibility(
        "No visa sponsorship. A relocation package is provided for the right person.", {})
    assert both["verdict"] == "warning" and both["contradictory"]
    boiler = vouch_fit.check_eligibility(
        "Applicants must be authorized to work in the country in which they apply.", {})
    assert boiler["verdict"] == "warning"


def test_language_warning_skips_languages_the_profile_lists():
    jd = "Fluent German is required. Fluency in English."
    assert vouch_fit.check_eligibility(jd, {})["verdict"] == "warning"
    profile = {"languages": ["English C1", "German B2"]}
    assert vouch_fit.check_eligibility(jd, profile)["verdict"] == "clear"
    ru = {"languages": ["Русский — родной", "Английский C1"]}
    assert vouch_fit.check_eligibility("Fluent English required.", ru)["verdict"] == "clear"


def test_liveness_reads_saved_pages(tmp_path):
    closed = tmp_path / "closed.html"
    closed.write_text("<h1>Engineer</h1><p>We are no longer accepting applications.</p>")
    assert vouch_fit.check_live(str(closed))["status"] == "closed"
    ru = tmp_path / "ru.html"
    ru.write_text("<p>Вакансия закрыта</p>", encoding="utf-8")
    assert vouch_fit.check_live(str(ru))["status"] == "closed"
    open_ = tmp_path / "open.html"
    open_.write_text('<script type="application/ld+json">{"validThrough": "2999-01-01"}</script>'
                     "<p>Apply now. Your application form has been filled out? Submit it.</p>")
    assert vouch_fit.check_live(str(open_))["status"] == "open"


def test_expired_valid_through():
    page = '{"@type": "JobPosting", "validThrough": "2026-01-31T00:00:00Z"}'
    assert vouch_fit.expired_valid_through(page, now=datetime(2026, 3, 1, tzinfo=timezone.utc))
    assert not vouch_fit.expired_valid_through(page, now=datetime(2025, 3, 1, tzinfo=timezone.utc))


def test_ats_api_urls():
    assert vouch_fit._api_url("https://job-boards.greenhouse.io/acme/jobs/123") == \
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs/123"
    lever = "https://jobs.lever.co/acme/0b5f3d2e-1111-2222-3333-444455556666"
    assert vouch_fit._api_url(lever).startswith("https://api.lever.co/v0/postings/acme/")


def test_example_story_is_clean_and_ranked():
    corpus, stories = vc.load_corpus(CORPUS), vc.load_stories(CORPUS)
    assert [s["id"] for s in stories] == ["st-001"]
    assert stories[0]["anchors"] == ["northwind-001"] and "900 ms" in stories[0]["situation"]
    assert vouch_corpus.check_stories(corpus, stories) == []
    (story, hits), = vouch_corpus.rank_stories(stories, corpus, JD)
    assert "postgresql" in hits


def test_story_with_a_new_figure_or_dangling_anchor_fails(tmp_path):
    for f in CORPUS.glob("*.md"):
        shutil.copy(f, tmp_path / f.name)
    text = (CORPUS / "_stories.md").read_text(encoding="utf-8")
    text = text.replace("900 ms to 140 ms", "900 ms to 95 ms")
    text += "\n### st-002 · Ghost\n- anchors: [northwind-999]\n- situation: x\n- action: y\n- result: z\n"
    (tmp_path / "_stories.md").write_text(text, encoding="utf-8")
    issues = vouch_corpus.check_stories(vc.load_corpus(tmp_path), vc.load_stories(tmp_path))
    assert any("st-001" in i and "95" in i for i in issues)
    assert any("st-002" in i and "northwind-999" in i for i in issues)


def test_location_region_is_checked_against_the_profile():
    jd = "Senior Engineer - Remote Europe\nWe welcome applicants based anywhere in Europe."
    far = vouch_fit.check_eligibility(jd, {"location": "Lima, Peru · open to relocation"})
    assert far["verdict"] == "warning" and far["findings"][0]["kind"] == "location"
    assert vouch_fit.check_eligibility(jd, {"location": "Lisbon, Portugal"})["verdict"] == "clear"
    assert vouch_fit.check_eligibility("Remote (US only).", {})["verdict"] == "warning"
    assert vouch_fit.check_eligibility("Questions? Contact us only by email.", {})["verdict"] == "clear"


def test_thin_terms_live_only_in_a_stack_list(tmp_path):
    (tmp_path / "acme.md").write_text(
        "---\ncompany: Acme\nid: acme\nrole: Engineer\nstart: 2020-01\nend: present\n"
        "stack: [MongoDB, Python, XeLaTeX]\n---\n\n## Records\n\n"
        "### acme-001 · Reports\n- what: Built PDF reports in Python with XeLaTeX.\n"
        "- stack: [Python, XeLaTeX]\n", encoding="utf-8")
    jd = "Requirements: Python, MongoDB, LaTeX."
    r = vouch_fit.assess_fit(jd, vc.load_corpus(tmp_path))
    assert r["thin"] == ["mongodb"]


def test_verify_reads_an_html_cv(tmp_path):
    import vouch_verify

    page = tmp_path / "cv.html"
    page.write_text(
        "<style>x{}</style><h2>Experience</h2><ul><li>Rewrote the public tracking API "
        "from Django to FastAPI &amp; Redis.</li></ul><h2>Skills</h2><ul><li>Python, Go, Rust, Kafka</li></ul>",
        encoding="utf-8")
    md = vc.read_text_arg(str(page))
    assert vouch_verify.cv_claims(md) == ["Rewrote the public tracking API from Django to FastAPI & Redis."]
