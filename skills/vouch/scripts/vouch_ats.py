#!/usr/bin/env python3
"""ATS pass simulation — pure code, offline, reproducible. No model calls.

What an applicant-tracking system does with a CV, approximated by the parts that
are knowable without a vendor's closed model:

  1. parse    — the delivered PDF/DOCX becomes plain text the way ATS parsers
                read it (pdftotext / pandoc / pypdf, whichever is available).
                Columns, tables or a font without a text layer silently drop
                content here; a recruiter then sees an empty profile.
  2. keywords — recruiters search by literal terms, and ranking weighs the
                posting's must-haves above its nice-to-haves.

The Vouch part: every missing requirement is classified. A term the CORPUS knows
but the CV lacks is the draft dropping a real fact (fixable). A term the corpus
does not know is a true gap: the score stays lower, and nothing may be added to
raise it. The score is a proxy for "would this be parsed and found", not any
vendor's number.

    python vouch_ats.py CV.pdf|CV.docx|CV.md JD.txt [--corpus DIR] [--title TITLE] [--json]
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vouch_common as vc  # noqa: E402

logger = logging.getLogger(__name__)

# --- JD term extraction (shape-based, no curated tech list) ----------------------

_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9+#./\-]{1,29}")
# "B1+", "C1" — language levels, not technologies.
_LANG_LEVEL = re.compile(r"^[a-z]\d\+?$")
# "M+" / "K+" left over from "$10M+", "5K+ users" — a quantity, not a technology.
_QUANTITY = re.compile(r"^[kmb]\+$")

# Words that pass the shape test but name no technology. A capitalized word is
# accepted as tech unless it is listed here, because JD bullets routinely OPEN
# with the stack ("- Kotlin and Jetpack Compose") — rejecting sentence-openers
# wholesale would drop exactly the terms the gate exists to catch. The cost of
# the inverse error is bounded: a stray noise term is one line in a report a
# human reads, so this list covers JD prose, not the technology space.
_NOT_TECH = {
    "a", "an", "and", "the", "we", "you", "your", "our", "us", "they", "their",
    "this", "that", "these", "those", "it", "its", "as", "at", "by", "for",
    "from", "in", "into", "of", "on", "or", "to", "with", "within", "without",
    "about", "across", "after", "before", "during", "over", "under", "per",
    "who", "what", "when", "where", "why", "how", "if", "then", "than",
    "experience", "experienced", "team", "teams", "role", "roles", "job",
    "jobs", "work", "working", "years", "year", "skills", "skill", "ability",
    "requirements", "qualifications", "responsibilities", "benefits",
    "bachelor", "master", "phd", "degree", "senior", "junior", "staff", "lead",
    "principal", "engineer", "engineering", "developer", "development",
    "software", "product", "products", "company", "candidate", "candidates",
    "position", "opportunity", "please", "must", "should", "will", "can",
    "have", "has", "are", "is", "be", "being", "been", "not", "nice", "plus",
    "strong", "good", "great", "excellent", "deep", "solid", "proven",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "sunday", "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "remote", "hybrid", "onsite", "office", "full-time", "part-time",
    # Verbs and nouns that routinely open a JD bullet.
    "build", "building", "design", "designing", "own", "ownership", "drive",
    "collaborate", "partner", "ship", "shipping", "deliver", "ensure",
    "develop", "maintain", "write", "support", "help", "define", "improve",
    "create", "manage", "mentor", "contribute", "understanding", "knowledge",
    "familiarity", "familiar", "proficiency", "fluency", "fluent", "passion",
    "passionate", "track", "record", "bonus", "preferred", "required",
    "minimum", "ideally", "comfortable", "impact", "scale", "growth",
    "mission", "culture", "salary", "equity", "visa", "relocation",
    "sponsorship", "apply", "join", "hiring", "interview", "recruiter",
    "location", "english", "communication", "stakeholders", "customers",
    "implement", "set", "harden", "document", "review", "reviews", "plan",
    "run", "learn", "teach", "share", "grow", "solve", "debug",
    "get", "got", "see", "saw", "applied", "find", "found", "take", "took",
    "make", "made", "do", "did", "done", "use", "used", "using", "look", "looking",
    "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "pero", "si",
    "en", "de", "del", "al", "por", "con", "para", "como", "más", "muy",
    "este", "esta", "estos", "estas", "su", "sus", "se", "lo", "qué", "es", "son",
    "fue", "ha", "hay", "ya", "que", "te", "tu", "tus", "mi", "mis",
    "banco", "banca", "institucion", "institución", "s.a", "c.v", "col", "colonia",
    "careers",
}



def _is_tech_shaped(token: str) -> bool:
    """Shape test for a technology name — no whitelist to keep up to date."""
    low = token.lower()
    if low in _NOT_TECH or len(token) < 2 or _LANG_LEVEL.match(low) or _QUANTITY.match(low):
        return False
    # "and/or", "dense/sparse/hybrid" — a slash phrase whose parts are prose.
    # "CI/CD" survives because neither part is.
    if "/" in low and any(part in _NOT_TECH for part in low.split("/") if part):
        return False
    if any(ch.isdigit() for ch in token) or any(ch in "+#./" for ch in token):
        return True
    if token.isupper() and 2 <= len(token) <= 6:  # AWS, SQL, LLM, GCP
        return True
    if any(ch.isupper() for ch in token[1:]):  # TypeScript, PostgreSQL, NestJS
        return True
    return token[0].isupper()  # Kotlin, Django, Rails


def extract_jd_requirements(jd_text: str) -> list[str]:
    """Technology/skill terms the JD names, independent of the corpus.

    This is what makes a gap a real gap: `extract_jd_terms` can only ever find
    what the corpus already knows, so it can never report a technology the
    corpus has never heard of.
    """
    found: dict[str, None] = {}  # ordered set
    for m in _TOKEN.finditer(jd_text):
        token = m.group(0).strip(".-/")
        if _is_tech_shaped(token):
            found.setdefault(token.lower(), None)
    return list(found)


def _known_to_corpus(term: str, vocabulary: set[str]) -> bool:
    """Does the corpus know this term at all?

    Direct hit, trivial plural, or a word inside a multi-word corpus term —
    the corpus says "rest api", so a JD asking for "API" is not a gap. Missing
    this made ordinary words ("api", "apis") read as gaps and depressed the
    coverage score for JDs the corpus in fact covers.
    """
    if term in vocabulary:
        return True
    # "latex" vs the corpus's "xelatex": a longer name ending in the term.
    # 4+ letters only, so "go" never matches "django".
    if len(term) >= 4 and any(v.endswith(term) and v != term for v in vocabulary):
        return True
    singular = term[:-1] if term.endswith("s") and len(term) > 3 else ""
    if singular and singular in vocabulary:
        return True
    for known in vocabulary:
        if " " in known or "/" in known or "-" in known:
            parts = re.split(r"[ /\-]+", known)
            if term in parts or (singular and singular in parts):
                return True
    return False



# --- corpus vocabulary terms ---

_WORD = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")
_STOP = {
    "the", "and", "for", "with", "you", "our", "are", "will", "have", "this",
    "that", "your", "from", "they", "their", "what", "who", "how", "can", "all",
    "job", "role", "team", "work", "years", "experience", "skills", "ability",
}

# Higher weight where the corpus author curated the match surface.
_WEIGHT = {"jd_keywords": 3.0, "skills": 2.0, "stack": 2.0, "what": 1.0}


def extract_jd_terms(jd_text: str, vocabulary: set[str]) -> set[str]:
    """Deterministic JD term extraction: corpus vocabulary terms present in the JD.

    Matches multi-word vocab terms (e.g. "react query", "design system") and
    single tokens. Lexical and reproducible; an LLM JD-parse is a future option.
    """
    text = jd_text.lower()
    tokens = {t for t in _WORD.findall(text) if t not in _STOP and len(t) > 1}
    found: set[str] = set()
    for term in vocabulary:
        t = term.lower()
        if " " in t or "/" in t:
            if t in text:  # phrase match
                found.add(t)
        elif t in tokens:
            found.add(t)
    return found



# Composite weights (code-owned). Parsing is a gate in reality — an unparsed CV
# is never found — but a partial parse (no phone) still gets searched, so it is
# weighted rather than multiplied in.
PARSE_WEIGHT = 0.35
MUST_WEIGHT = 0.50
NICE_WEIGHT = 0.15

# --- 1. text extraction -------------------------------------------------------


def extract_text(path: Path) -> str | None:
    """Plain text the way an ATS parser sees the file; None when no tool for that
    format is available (the caller then falls back to the markdown)."""
    suffix = path.suffix.lower()
    if suffix in (".md", ".txt"):
        return markdown_to_text(path.read_text(encoding="utf-8"))
    if suffix == ".pdf":
        if shutil.which("pdftotext"):
            return _run(["pdftotext", "-enc", "UTF-8", str(path), "-"])
        try:  # pure-Python fallback (claude.ai's sandbox ships pypdf)
            from pypdf import PdfReader

            return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        except ImportError:
            return None
    if suffix == ".docx":
        if shutil.which("pandoc"):
            return _run(["pandoc", str(path), "--from=docx", "--to=plain", "--wrap=none"])
        try:
            import zipfile

            with zipfile.ZipFile(path) as z:  # stdlib: word/document.xml paragraphs
                xml = z.read("word/document.xml").decode("utf-8", "replace")
            return re.sub(r"<[^>]+>", "", re.sub(r"</w:p>", "\n", xml))
        except (KeyError, OSError, zipfile.BadZipFile):
            return None
    return None


def _run(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=60, check=True)
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("text extraction failed: %s", exc)
        return None
    return out.stdout.decode("utf-8", errors="replace")


_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def markdown_to_text(md: str) -> str:
    """Markdown stripped to roughly what a renderer shows — the fallback source
    when no rendered file is available (no pandoc/xelatex)."""
    text = _FRONTMATTER.sub("", md)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links → label
    text = re.sub(r"^[#>\s]*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    return re.sub(r"[*_`]", "", text)


# --- 2. parse checks ----------------------------------------------------------

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\d)\+?\d[\d\s().-]{7,}\d(?!\d)")
_MONTH = (
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
    r"|(?:янв|фев|мар|апр|ма[йя]|июн|июл|авг|сен|окт|ноя|дек)[а-я]*\.?"
)
# "Mar 2021", "03/2021", "03.2021", "2021", and ISO "2021-04" (the corpus format).
_DATE = rf"(?:(?:{_MONTH})\s+)?(?:\d{{1,2}}[./])?(?:19|20)\d\d(?:-(?:0[1-9]|1[0-2]))?"
_OPEN_END = r"present|current|now|today|настоящее время|н\.\s?в\.|сейчас|по н\.в\."
_DATE_RANGE = re.compile(
    rf"{_DATE}\s*(?:-|–|—|to|по|until)\s*(?:{_DATE}|{_OPEN_END})", re.IGNORECASE
)
# Section headings an ATS segmenter recognizes, EN + RU.
_SECTIONS = {
    "experience": r"(?:work |professional )?experience|employment|опыт(?: работы)?",
    "education": r"education|образование",
    "skills": r"(?:technical |core )?skills|навыки|технологии",
    "summary": r"summary|profile|about(?: me)?|о себе|резюме|профиль",
}
# Font/encoding failures in the text layer: replacement chars, pdfminer cids.
_GARBLED = re.compile(r"�|\(cid:\d+\)")


@dataclass
class ParseReport:
    chars: int = 0
    email: bool = False
    phone: bool = False
    contact_on_top: bool = False  # header contact survived in reading order
    sections: list[str] = field(default_factory=list)
    date_ranges: int = 0
    garbled: bool = False

    @property
    def checks(self) -> dict[str, bool]:
        return {
            "text": self.chars >= 300,
            "email": self.email,
            "phone": self.phone,
            "contact_on_top": self.contact_on_top,
            "sections": {"experience", "skills"} <= set(self.sections),
            "dated_roles": self.date_ranges >= 1,
            "clean_text": not self.garbled,
        }

    @property
    def pct(self) -> float:
        checks = self.checks
        return round(100.0 * sum(checks.values()) / len(checks), 1)


def check_parse(text: str) -> ParseReport:
    r = ParseReport(chars=len(text.strip()))
    email = _EMAIL.search(text)
    r.email = email is not None
    r.phone = _PHONE.search(text) is not None
    # Contact block in the first fifth of the text: a two-column or header/footer
    # layout that an ATS reads out of order pushes it to the end (or drops it).
    r.contact_on_top = bool(email) and email.start() <= max(400, len(text) // 5)
    lines = [ln.strip().lower().rstrip(":") for ln in text.splitlines() if ln.strip()]
    for name, pattern in _SECTIONS.items():
        if any(re.fullmatch(pattern, ln) for ln in lines if len(ln) <= 40):
            r.sections.append(name)
    r.date_ranges = len(_DATE_RANGE.findall(text))
    r.garbled = bool(_GARBLED.search(text))
    return r


# --- 3. JD requirements: must-have vs nice-to-have ----------------------------

_NICE_MARK = re.compile(
    r"nice[ -]to[ -]have|bonus(?: points)?|preferred|would be a plus|is a plus|"
    r"a plus\b|желательно|будет плюсом|плюсом будет|будет преимуществом",
    re.IGNORECASE,
)
_MUST_MARK = re.compile(
    r"requirements|required|must[ -]have|qualifications|responsibilities|"
    r"what you(?:'ll)? (?:bring|need|do)|требования|обязательно|обязанности",
    re.IGNORECASE,
)


# Section headings whose body describes the company, not the role: an ATS
# keyword profile is built from the requirements, and "Nasdaq", "Amsterdam",
# "perks", "equal opportunity" scored as missing must-haves on a real posting.
_BOILERPLATE_HEADING = re.compile(
    r"^\W*(?:about\b|who we are|our (?:story|mission|values|culture|company)|"
    r"why\b|life at|what we offer|we offer|benefits|perks|"
    r"compensation|equal (?:opportunity|employment)|diversity|eeo\b|"
    r"о (?:компании|нас|команде)|мы предлагаем|условия|что мы предлагаем)",
    re.IGNORECASE,
)
# Headings that start the role's own content — they end a skipped section.
# Anything else (a short perk line, a location) keeps skipping, so a perks
# list never leaks back in through its own Title-Case bullets.
_ROLE_HEADING = re.compile(
    r"requirement|qualification|responsibilit|must|nice|bonus|plus|prefer|"
    r"expect|you (?:will|have|bring|need)|you'll|what you|role|position|"
    r"technolog|stack|skills|experience|working on|the job|"
    r"требован|обязанност|задачи|стек|навыки|опыт|ожидаем|будет плюсом",
    re.IGNORECASE,
)
_MAX_HEADING_WORDS = 8


def _is_heading(line: str) -> bool:
    words = line.split()
    return 0 < len(words) <= _MAX_HEADING_WORDS and not line.rstrip().endswith(".")


def strip_boilerplate(jd_text: str) -> str:
    """The JD without its company sections (about us, benefits, legal)."""
    kept: list[str] = []
    skipping = False
    for line in jd_text.splitlines():
        stripped = line.strip().replace("\xa0", " ")
        if _is_heading(stripped):
            if _BOILERPLATE_HEADING.match(stripped):
                skipping = True
                continue
            if skipping and _ROLE_HEADING.search(stripped):
                skipping = False
        if not skipping:
            kept.append(line)
    return "\n".join(kept)


_SENTENCE_START = re.compile(r"(?:^|[.!?:;•*\-–—]\s*|\n\s*)$")
# After a sentence-opening word: a list continues ("Python, Docker", "Go and
# Python", "Kafka.", "Go / Rust"); anything else — a lowercase word, "&", a
# second capitalized word ("Optimising AI performance") — reads as prose.
_LIST_CONTINUES = re.compile(
    # "Go and Python" continues a list; "Architect and develop" is a verb phrase.
    r"[ \t]*(?:[,;./)|]|$|\n|(?:and|or)[ \t]+[A-Z])", re.MULTILINE
)


def _mid_sentence(term: str, text: str) -> bool:
    """A plain capitalized word is a name (Kotlin, Django) when it is capitalized
    mid-sentence somewhere; a word capitalized only where a sentence or bullet
    starts ("Expanding our platform", "While we…") is ordinary prose."""
    for m in re.finditer(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", text,
                         re.IGNORECASE):
        word = m.group(0)
        if word.isupper() and len(word) > 1:  # GPU, SQL — an acronym anywhere
            return True
        if not word[0].isupper():
            continue
        if not _SENTENCE_START.search(text[max(0, m.start() - 4) : m.start()]):
            return True  # capitalized mid-sentence: a name
        if _LIST_CONTINUES.match(text, m.end()):
            return True  # opens a list ("Requirements: Python, Docker")
    return False


def _keep_term(term: str, chunk: str, vocabulary: set[str]) -> bool:
    if term in _NOT_TECH:  # corpus vocab can carry prose ("requirements")
        return False
    if term in vocabulary or not term.isalpha():
        return True  # known to the corpus, or tech-shaped (C++, k8s, ci/cd)
    return _mid_sentence(term, chunk)


def _split_slashed(terms: list[str], vocabulary: set[str]) -> list[str]:
    """"node/vue/typescript" from a title is three requirements, not one; keep a
    real compound ("ci/cd", or one the corpus itself uses) whole."""
    out: list[str] = []
    for t in terms:
        parts = [p for p in t.split("/") if p]
        if "/" in t and t not in vocabulary and (len(parts) >= 3 or all(p in vocabulary for p in parts)):
            out += [p for p in parts if p not in out]
        elif t not in out:
            out.append(t)
    return out


def split_requirements(jd_text: str, vocabulary: set[str]) -> tuple[list[str], list[str]]:
    """(must_have, nice_to_have) terms. Company sections are dropped first; then
    text after a nice-to-have marker counts as nice until a must marker resumes;
    everything else is must — an unstructured JD lists what it needs, not what
    it would merely like."""
    jd_text = strip_boilerplate(jd_text)
    marks = sorted(
        [(m.start(), "nice") for m in _NICE_MARK.finditer(jd_text)]
        + [(m.start(), "must") for m in _MUST_MARK.finditer(jd_text)]
    )
    bounds = [(0, "must"), *marks, (len(jd_text), "end")]
    must: dict[str, None] = {}
    nice: dict[str, None] = {}
    for (start, kind), (end, _) in zip(bounds, bounds[1:], strict=False):
        chunk = jd_text[start:end]
        terms = [*extract_jd_requirements(chunk), *sorted(extract_jd_terms(chunk, vocabulary))]
        for t in _split_slashed(terms, vocabulary):
            if _keep_term(t, chunk, vocabulary):
                (nice if kind == "nice" else must).setdefault(t, None)
    for t in must:  # named as both: the stricter reading wins
        nice.pop(t, None)
    return list(must), list(nice)


# --- 4. keyword presence ------------------------------------------------------

# Spellings an ATS keyword search treats as one term only if the recruiter types
# both — so a CV that says "k8s" misses a "Kubernetes" search. Grouped by
# equivalence; any member present satisfies any member asked for.
_SYNONYMS = [
    {"kubernetes", "k8s"},
    {"javascript", "js"},
    {"typescript", "ts"},
    {"postgresql", "postgres"},
    {"golang", "go"},
    {"node.js", "nodejs", "node"},
    {"react", "react.js", "reactjs"},
    {"vue", "vue.js", "vuejs"},
    {"gcp", "google cloud"},
    {"aws", "amazon web services"},
    {"ci/cd", "ci", "cd"},
    {"llm", "llms"},
    {"ml", "machine learning"},
    {"api", "apis"},
]


def _variants(term: str) -> set[str]:
    out = {term}
    for group in _SYNONYMS:
        if term in group:
            out |= group
    if term.endswith("s") and len(term) > 3:
        out.add(term[:-1])
    return out


def searchable(text: str) -> str:
    """Text as a keyword index sees it: lowercased, words split across a line
    break re-joined, whitespace collapsed — a PDF wraps 'REST\nAPI' or
    hyphenates 'Kuber-\nnetes', and a phrase search must still find them."""
    text = re.sub(r"(\w)-\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).lower()


def term_present(term: str, text_lower: str) -> bool:
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(v)}(?![a-z0-9+#])", text_lower)
        for v in _variants(term.lower())
    )


# --- 5. the report ------------------------------------------------------------


@dataclass
class AtsReport:
    source: str  # "pdf" | "docx" | "markdown" — what was actually parsed
    parse: ParseReport
    must_have: list[str] = field(default_factory=list)
    nice_to_have: list[str] = field(default_factory=list)
    present: list[str] = field(default_factory=list)
    # Missing, but the corpus knows it: the generator dropped a real fact.
    missed_known: list[str] = field(default_factory=list)
    # Missing, and the corpus does not know it: a true gap — never to be added.
    true_gaps: list[str] = field(default_factory=list)
    title_match: bool | None = None
    semantic: float | None = None

    def _pct(self, terms: list[str]) -> float | None:
        if not terms:
            return None
        hit = sum(1 for t in terms if t in self.present)
        return round(100.0 * hit / len(terms), 1)

    @property
    def must_pct(self) -> float | None:
        return self._pct(self.must_have)

    @property
    def nice_pct(self) -> float | None:
        return self._pct(self.nice_to_have)

    @property
    def score(self) -> float:
        """0–100 proxy: parsed + must-haves findable + nice-to-haves findable.
        A side with no terms counts as fully met (nothing to miss)."""
        must = 100.0 if self.must_pct is None else self.must_pct
        nice = 100.0 if self.nice_pct is None else self.nice_pct
        return round(
            PARSE_WEIGHT * self.parse.pct + MUST_WEIGHT * must + NICE_WEIGHT * nice, 1
        )


_SENIORITY = re.compile(
    r"\b(?:senior|junior|middle|mid|lead|staff|principal|sr|jr|head|chief)\b\.?",
    re.IGNORECASE,
)


def title_found(title: str, text_lower: str) -> bool:
    """The JD's job title (minus seniority) appears in the CV — ATS search and
    ranking both lean on title match."""
    title = re.split(r"\s[-–—|]\s", title)[0]  # "… - Remote Europe", "… | Berlin"
    core = _SENIORITY.sub("", re.sub(r"\(.*?\)", "", title)).strip(" ,.-").lower()
    return bool(core) and core in text_lower


def guess_title(jd_text: str) -> str | None:
    """The JD's first line when it reads as a title (short, no sentence)."""
    first = jd_text.strip().splitlines()[0] if jd_text.strip() else ""
    first = re.split(r"[.:]\s", first, maxsplit=1)[0]
    return first if 1 <= len(first.split()) <= 8 else None


def simulate(
    cv_text: str,
    jd_text: str,
    corpus: dict,
    *,
    source: str = "markdown",
    title: str | None = None,
    semantic: float | None = None,
) -> AtsReport:
    vocabulary = vc.vocabulary(corpus)
    must, nice = split_requirements(jd_text, vocabulary)
    low = searchable(cv_text)
    report = AtsReport(
        source=source,
        parse=check_parse(cv_text),
        must_have=must,
        nice_to_have=nice,
        semantic=semantic,
    )
    for term in [*must, *nice]:
        if term_present(term, low):
            report.present.append(term)
        elif _known_to_corpus(term, vocabulary):
            report.missed_known.append(term)
        else:
            report.true_gaps.append(term)
    if title:
        report.title_match = title_found(title, low)
    return report




def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="vouch_ats", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cv", help="the delivered CV: .pdf, .docx, or .md/.txt")
    p.add_argument("jd", help="job description text file, or - for stdin")
    p.add_argument("--corpus", help="corpus folder (enables dropped-fact vs true-gap split)")
    p.add_argument("--title", help="job title (default: the JD's first line, if it reads as one)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    path = Path(a.cv).expanduser()
    text = extract_text(path)
    source = path.suffix.lstrip(".").lower() or "text"
    if text is None:
        raise SystemExit(f"cannot read {path.name} here (no pdftotext/pypdf/pandoc) — "
                         "pass the CV as .md or .txt instead")
    jd = vc.read_text_arg(a.jd)
    corpus = vc.load_corpus(a.corpus) if a.corpus else {"root": "", "files": []}
    r = simulate(text, jd, corpus, source=source, title=a.title or guess_title(jd))
    if a.json:
        vc.emit({
            "score": r.score, "source": r.source, "parse_pct": r.parse.pct,
            "parse_checks": r.parse.checks, "must_pct": r.must_pct, "nice_pct": r.nice_pct,
            "title_match": r.title_match, "must_have": r.must_have,
            "nice_to_have": r.nice_to_have, "present": r.present,
            "missed_known": r.missed_known, "true_gaps": r.true_gaps,
        })
        return 0
    failed = [k for k, ok in r.parse.checks.items() if not ok]
    print(f"ATS score {r.score}/100 (proxy, read from {r.source})")
    print(f"  parse {r.parse.pct}%" + (f" — failed: {', '.join(failed)}" if failed else ""))
    print(f"  must-have found {r.must_pct if r.must_pct is not None else 'n/a'}% "
          f"of {len(r.must_have)} · nice-to-have {r.nice_pct if r.nice_pct is not None else 'n/a'}%"
          f" of {len(r.nice_to_have)} · title match: {r.title_match}")
    if r.missed_known:
        print("  dropped facts (your corpus has them; the CV doesn't say them): "
              + ", ".join(r.missed_known))
    if r.true_gaps:
        print("  true gaps (not in your corpus — never add them): " + ", ".join(r.true_gaps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
