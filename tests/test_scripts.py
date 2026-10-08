"""The scripts' contracts, on the fictional example corpus. Offline, stdlib + pytest."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "vouch" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vouch_ats  # noqa: E402
import vouch_common as vc  # noqa: E402
import vouch_corpus  # noqa: E402
import vouch_verify  # noqa: E402

CORPUS = ROOT / "examples" / "corpus"
CV = (ROOT / "examples" / "cv-draft.md").read_text(encoding="utf-8")
JD = (ROOT / "examples" / "jd-backend.txt").read_text(encoding="utf-8")


def corpus():
    return vc.load_corpus(CORPUS)


# --- corpus ---------------------------------------------------------------------


def test_corpus_parses_records_metrics_and_wrapped_fields():
    recs = {r["id"]: r for r in vc.all_records(corpus())}
    assert set(recs) == {"northwind-001", "northwind-002", "northwind-003",
                         "shopkit-001", "shopkit-002"}
    r = recs["northwind-001"]
    assert r["what"].endswith("moved reads to a Redis cache.")  # wrapped line kept
    assert [m["provenance"] for m in r["metrics"]] == ["verifiable", "estimate"]
    assert r["metrics"][0]["value"] == "p95 latency 900 ms → 140 ms (Grafana)"
    assert "I led the design" in r["team"]
    assert "REST API" in r["jd_keywords"]


def test_record_provenance_takes_the_most_cautious_metric():
    recs = {r["id"]: r for r in vc.all_records(corpus())}
    assert vc.record_provenance(recs["northwind-001"]) == "estimate"
    assert vc.record_provenance(recs["shopkit-001"]) == "from-cv"
    assert vc.record_provenance(recs["northwind-003"]) == "verifiable"  # no metrics


def test_frontmatter_block_lists_and_quotes():
    fm, body = vc.parse_frontmatter('---\ncompany: "A, Inc"\nstack:\n  - Go\n  - Rust\n---\nbody')
    assert fm == {"company": "A, Inc", "stack": ["Go", "Rust"]} and body == "body"


def test_lint_flags_untagged_figures_as_hints(tmp_path):
    (tmp_path / "x.md").write_text(
        "---\nid: x\nrole: Dev\nstart: 2020-01\nend: present\n---\n## Records\n\n"
        "### x-001 · Thing\n- what: Cut costs by 40% for 1200 users in 2023.\n- stack: [Go]\n",
        encoding="utf-8",
    )
    errors, hints = vouch_corpus.lint(vc.load_corpus(tmp_path))
    assert not errors
    assert any("40%" in h and "1200" in h for h in hints)
    assert not any("2023" in h for h in hints)  # a year is not a result


def test_lint_reports_duplicate_ids(tmp_path):
    rec = "### d-001 · T\n- what: x\n- stack: [Go]\n"
    for name in ("a", "b"):
        (tmp_path / f"{name}.md").write_text(
            f"---\nid: {name}\nrole: R\n---\n## Records\n\n{rec}", encoding="utf-8")
    errors, _ = vouch_corpus.lint(vc.load_corpus(tmp_path))
    assert any("d-001 also used" in e for e in errors)


# --- verify ---------------------------------------------------------------------


def test_cv_claims_skip_skills_and_short_bullets():
    claims = vouch_verify.cv_claims(CV)
    assert len(claims) == 6  # 5 bullets + the summary sentence
    assert not any("Python, FastAPI" in c for c in claims)
    assert claims[-1].startswith("Backend engineer with event-driven")


def test_judge_sees_employers_and_the_users_own_terms():
    text, _ = vouch_verify.build_packet(CV, corpus(), "cv", "")
    assert "## EMPLOYERS" in text and "Northwind Logistics (northwind): Senior Backend Engineer" in text
    assert "also described as:" in text and "REST API" in text


def test_letter_claims_skip_salutation_and_employer_sentences():
    letter = ("Dear Acme team,\n\nAcme builds payment rails for 40 countries.\n\n"
              "I led a team of 3 that rewrote a FastAPI service and cut latency to 140 ms.\n\n"
              "Best regards,\nAlex")
    claims = vouch_verify.letter_claims(letter, vc.vocabulary(corpus()), company="Acme")
    assert claims == ["I led a team of 3 that rewrote a FastAPI service and cut latency to 140 ms."]


def test_small_corpus_goes_to_the_judge_whole():
    text, claims = vouch_verify.build_packet(CV, corpus(), "cv", "")
    assert text.count("\n### ") == 5  # every record, so cross-language claims still match
    assert "## CLAIMS" in text and claims[0]["n"] == 1


def test_report_maps_verdicts_through_the_provenance_policy():
    _, claims = vouch_verify.build_packet(CV, corpus(), "cv", "")
    verdicts = "\n".join([
        '{"n": 1, "supported": true, "evidence_id": "northwind-001", "reason": "ok"}',
        '{"n": 2, "supported": false, "evidence_id": null, "reason": "Pub/Sub, not Kafka"}',
        "garbled answer for 3",
        '{"n": 4, "supported": true, "evidence_id": "shopkit-001", "reason": "from old CV"}',
        '{"n": 5, "supported": "yes", "evidence_id": "shopkit-002", "reason": "ok"}',
    ])
    actions = [r["action"] for r in vouch_verify.build_report(claims, verdicts, corpus())]
    # 1: its figures are the verifiable metric (the record's other metric is an
    #    estimate — that must not soften this line). 4: "12%" is the from-cv metric.
    #    5: no figure, nothing to soften.
    #    6: the summary sentence got no verdict: unverified, never a pass.
    assert actions == ["keep", "remove_or_verify", "unverified", "flag", "keep", "unverified"]


def test_claim_provenance_reads_the_metrics_the_claim_repeats():
    recs = {r["id"]: r for r in vc.all_records(corpus())}
    nw = recs["northwind-001"]
    assert vc.claim_provenance("cut p95 from 900 ms to 140 ms", nw) == "verifiable"
    assert vc.claim_provenance("migrated about 40 integrations", nw) == "estimate"
    assert vc.claim_provenance("rewrote the API in FastAPI", nw) == "verifiable"  # no figure
    assert vc.claim_provenance("served 5 million users", nw) == "estimate"  # unmatched: cautious
    assert vc.claim_provenance("anything", None) is None
    assert vc.claim_provenance("working in Python since 2018", nw) == "verifiable"  # a year


def test_report_cli_roundtrip(tmp_path):
    packet = tmp_path / "p.md"
    cv = tmp_path / "cv.md"
    cv.write_text(CV, encoding="utf-8")
    assert vouch_verify.main(["packet", str(cv), "--corpus", str(CORPUS), "--out", str(packet)]) == 0
    claims = json.loads((tmp_path / "p.md.claims.json").read_text(encoding="utf-8"))
    assert len(claims) == 6
    verdicts = tmp_path / "v.jsonl"
    verdicts.write_text('{"n": 2, "supported": false, "evidence_id": null, "reason": "x"}')
    assert vouch_verify.main(["report", str(packet), str(verdicts), "--corpus", str(CORPUS)]) == 0


# --- ATS ------------------------------------------------------------------------


def test_ats_splits_dropped_facts_from_true_gaps():
    r = vouch_ats.simulate(vouch_ats.markdown_to_text(CV), JD, corpus(),
                           title=vouch_ats.guess_title(JD))
    assert r.parse.pct == 100.0  # ISO "2021-04 – present" counts as a dated role
    assert "mentoring" in r.missed_known or "mentoring" in r.present
    assert "rust" in r.true_gaps  # nice-to-have the corpus doesn't have
    for noise in ("amsterdam", "competitive", "flexible"):  # "About us" section skipped
        assert noise not in r.must_have + r.nice_to_have
    # The fabricated Kafka line is *found* by the ATS — catching it is verify's job.
    assert "kafka" in r.present


def test_ats_reads_docx_without_pandoc(tmp_path, monkeypatch):
    import zipfile

    doc = tmp_path / "cv.docx"
    with zipfile.ZipFile(doc, "w") as z:
        z.writestr("word/document.xml", "<w:p><w:t>Python FastAPI</w:t></w:p><w:p><w:t>Kafka</w:t></w:p>")
    monkeypatch.setattr(vouch_ats.shutil, "which", lambda name: None)
    assert "Python FastAPI" in vouch_ats.extract_text(doc)


# --- regressions from the first real-corpus run (Reedsy posting) -----------------


def test_names_and_bare_digits_are_not_figures():
    rec = {"metrics": [{"value": "API cost ~4x lower with 8 GPUs", "provenance": "estimate"},
                       {"value": "p95 120 ms", "provenance": "verifiable"}]}
    assert vc.claim_provenance("ran vLLM on 4× A100 with FP8 quantization", rec) == "estimate"
    assert vc.claim_provenance("ran vLLM on A100 with FP8 quantization", rec) == "verifiable"
    assert vc.claim_provenance("p95 down to 120 ms on 8 nodes", rec) == "verifiable"


def test_slashed_title_terms_and_verb_openers():
    jd = ("Senior Software Engineer (Node/Vue/TypeScript)\nRESPONSIBILITIES\n"
          " - Architect and develop highly scalable web applications;\n"
          " - Evaluate and improve performance;\nREQUIREMENTS\n - Go and Python, CI/CD.")
    must, _ = vouch_ats.split_requirements(jd, set())
    assert {"node", "vue", "typescript", "go", "python", "ci/cd"} <= set(must)
    assert "node/vue/typescript" not in must
    assert "architect" not in must and "evaluate" not in must


def test_judge_sees_employer_location():
    text, _ = vouch_verify.build_packet(CV, corpus(), "cv", "")
    assert "Senior Backend Engineer 2021-04 – present · Lisbon / Remote" in text


def test_title_match_ignores_location_suffix():
    title = "Senior Software Engineer (Node/Vue/TypeScript) - Remote Europe"
    assert vouch_ats.title_found(title, "alex example software engineer lisbon")
