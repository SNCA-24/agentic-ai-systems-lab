from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.schemas import RetrievedPolicyDocument


PROJECT_DIR = Path(__file__).resolve().parents[1]
POLICY_DIR = PROJECT_DIR / "data" / "policies"
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "for",
    "i",
    "if",
    "in",
    "is",
    "it",
    "may",
    "of",
    "or",
    "same",
    "the",
    "this",
    "to",
    "was",
    "with",
}
INTENT_KEYWORDS = {
    "duplicate_charge_refund": (
        "duplicate charge",
        "charged twice",
        "same invoice",
        "same service period",
        "invoice",
    ),
    "unclear_refund_request": (
        "cancellation timestamp",
        "after cancellation",
        "post-cancellation",
        "missing evidence",
        "unclear evidence",
        "conflicting evidence",
        "manual review",
        "escalate",
    ),
    "duplicate_charge": (
        "duplicate charge",
        "charged twice",
        "same invoice",
        "same service period",
        "invoice",
    ),
    "cancellation_dispute": (
        "cancellation timestamp",
        "after cancellation",
        "post-cancellation",
        "missing evidence",
        "unclear evidence",
        "conflicting evidence",
        "manual review",
        "escalate",
    ),
}


@dataclass(frozen=True)
class PolicySection:
    source: str
    section_title: str
    section_ref: str
    content: str
    search_text: str


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def _tokenize(value: str) -> list[str]:
    return [token for token in TOKEN_PATTERN.findall(value.lower()) if token not in STOP_WORDS]


def _normalize_text(lines: Iterable[str]) -> str:
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return "\n".join(cleaned_lines)


class PolicyStore:
    def __init__(self, policy_dir: Path | str = POLICY_DIR) -> None:
        self.policy_dir = Path(policy_dir)
        self._sections = self._load_sections()

    @property
    def sections(self) -> list[PolicySection]:
        return list(self._sections)

    def search(
        self,
        query: str,
        intent: str | None = None,
        limit: int = 3,
    ) -> list[RetrievedPolicyDocument]:
        cleaned_request = query.strip()
        if not cleaned_request:
            raise ValueError("query must not be blank")

        scored_sections: list[tuple[float, PolicySection]] = []
        for section in self._sections:
            score = self._score_section(section, cleaned_request, intent)
            if score > 0.0:
                scored_sections.append((score, section))

        scored_sections.sort(
            key=lambda item: (-item[0], item[1].source, item[1].section_title, item[1].section_ref)
        )

        return [
            RetrievedPolicyDocument(
                source=section.source,
                section_title=section.section_title,
                section_ref=section.section_ref,
                score=score,
                content=section.content,
            )
            for score, section in scored_sections[:limit]
        ]

    def retrieve(
        self,
        request_text: str,
        intent: str | None = None,
        limit: int = 3,
    ) -> list[RetrievedPolicyDocument]:
        return self.search(query=request_text, intent=intent, limit=limit)

    def _load_sections(self) -> list[PolicySection]:
        sections: list[PolicySection] = []
        for policy_path in sorted(self.policy_dir.glob("*.md")):
            sections.extend(self._parse_policy(policy_path))
        return sections

    def _parse_policy(self, policy_path: Path) -> list[PolicySection]:
        sections: list[PolicySection] = []
        current_title: str | None = None
        current_lines: list[str] = []

        def flush_current_section() -> None:
            nonlocal current_title, current_lines
            if not current_title:
                current_lines = []
                return
            content = _normalize_text(current_lines)
            if not content:
                current_lines = []
                return
            source = policy_path.name
            section_ref = f"{policy_path.stem}#{_slugify(current_title)}"
            search_text = f"{current_title}\n{content}".lower()
            sections.append(
                PolicySection(
                    source=source,
                    section_title=current_title,
                    section_ref=section_ref,
                    content=content,
                    search_text=search_text,
                )
            )
            current_lines = []

        for raw_line in policy_path.read_text(encoding="utf-8").splitlines():
            heading_match = HEADING_PATTERN.match(raw_line)
            if heading_match:
                heading_level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                if heading_level == 1:
                    continue
                flush_current_section()
                current_title = heading_text
                continue
            current_lines.append(raw_line)

        flush_current_section()
        return sections

    def _score_section(self, section: PolicySection, request_text: str, intent: str | None) -> float:
        request_tokens = _tokenize(request_text)
        intent_tokens = _tokenize(intent or "")
        keywords = list(dict.fromkeys(request_tokens + intent_tokens))
        phrases = self._build_phrases(request_text, intent)

        title_text = section.section_title.lower()
        body_text = section.content.lower()
        full_text = section.search_text

        raw_score = 0.0
        for keyword in keywords:
            if keyword in title_text:
                raw_score += 2.0
            elif keyword in body_text:
                raw_score += 1.0

        for phrase in phrases:
            if phrase in title_text:
                raw_score += 4.0
            elif phrase in full_text:
                raw_score += 2.5

        if "escalat" in body_text and any(term in request_text.lower() for term in ("unclear", "missing", "conflict", "inconsistent")):
            raw_score += 1.5

        if "duplicate charge" in body_text and any(term in request_text.lower() for term in ("twice", "duplicate", "same invoice")):
            raw_score += 1.5

        if raw_score <= 0.0:
            return 0.0

        return min(1.0, round(raw_score / 12.0, 4))

    def _build_phrases(self, request_text: str, intent: str | None) -> list[str]:
        lowered_request = request_text.lower()
        phrases = [
            phrase
            for phrase in (
                "duplicate charge",
                "charged twice",
                "refund window",
                "missing evidence",
                "unclear evidence",
                "conflicting evidence",
                "manual review",
                "after cancellation",
                "cancellation timestamp",
            )
            if phrase in lowered_request
        ]

        if intent:
            phrases.extend(INTENT_KEYWORDS.get(intent, ()))

        return list(dict.fromkeys(phrases))


class LocalPolicyStore(PolicyStore):
    pass


def retrieve_policy_documents(
    request_text: str,
    intent: str | None = None,
    limit: int = 3,
    policy_dir: Path | str = POLICY_DIR,
) -> list[RetrievedPolicyDocument]:
    return PolicyStore(policy_dir=policy_dir).search(
        query=request_text,
        intent=intent,
        limit=limit,
    )
