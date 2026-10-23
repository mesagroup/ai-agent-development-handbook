#!/usr/bin/env python3
"""Quantitative analysis of system prompts and SOPs.

Parses a markdown system prompt, detects sections/steps, counts directive
keywords (MUST, SHOULD, MAY, etc.), estimates token usage, detects
cross-references between sections, and finds repeated constraint patterns.

Usage:
    python analyze_prompt.py <file_path> [--format json|markdown]
    python analyze_prompt.py <file_path> --format markdown
    cat prompt.md | python analyze_prompt.py - --format json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field

# ---------------------------------------------------------------------------
# Directive patterns
# ---------------------------------------------------------------------------

_DIRECTIVE_PATTERNS = {
    "MUST": re.compile(r"\bMUST\b(?!\s+NOT)"),
    "MUST NOT": re.compile(r"\bMUST NOT\b"),
    "SHALL NOT": re.compile(r"\bSHALL NOT\b"),
    "SHOULD": re.compile(r"\bSHOULD\b(?!\s+NOT)"),
    "SHOULD NOT": re.compile(r"\bSHOULD NOT\b"),
    "MAY": re.compile(r"\bMAY\b"),
    "NEVER": re.compile(r"\bNEVER\b"),
    "CRITICAL": re.compile(r"\bCRITICAL\b"),
    "IMPORTANT": re.compile(r"\bIMPORTANT\b"),
}

# Section header patterns (ordered by specificity)
_STEP_HEADER_RE = re.compile(
    r"^(#{2,4})\s+"
    r"(?:(?:Step\s+)?(\d+[a-z]?)[\.\:\s]+)?"  # Optional step number
    r"(.+)",
    re.MULTILINE,
)

# Cross-reference: "Step N", "step N", "Phase N"
_CROSS_REF_RE = re.compile(r"\b(?:Step|step|Phase|phase|STEP)\s+(\d+[a-z]?)\b")

# Constraint sentence: line starting with "- You MUST/SHOULD/MAY..."
_CONSTRAINT_LINE_RE = re.compile(
    r"^[-*]\s+.*\b(?:MUST|SHOULD|MAY|SHALL|NEVER)\b.*$",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SectionMetrics:
    """Metrics for a single section of the prompt."""

    id: str
    title: str
    level: int  # header level (2=##, 3=###)
    words: int = 0
    chars: int = 0
    lines: int = 0
    directives: dict[str, int] = field(default_factory=dict)
    total_directives: int = 0
    constraint_lines: int = 0
    cross_refs: list[str] = field(default_factory=list)  # referenced section ids

    @property
    def directive_density(self) -> float:
        """Directives per 100 words."""
        return (self.total_directives / self.words * 100) if self.words else 0


@dataclass
class RedundancyGroup:
    """A group of similar constraint phrases found across sections."""

    pattern: str
    occurrences: int
    sections: list[str]


@dataclass
class PromptAnalysis:
    """Complete quantitative analysis of a system prompt."""

    file_path: str
    total_words: int = 0
    total_chars: int = 0
    total_lines: int = 0
    est_tokens: int = 0
    total_directives: dict[str, int] = field(default_factory=dict)
    grand_total_directives: int = 0
    sections: list[SectionMetrics] = field(default_factory=list)
    cross_reference_graph: dict[str, list[str]] = field(default_factory=dict)
    redundancy_groups: list[RedundancyGroup] = field(default_factory=list)
    data_flow_depth: int = 0  # longest chain of forward references


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _count_directives(text: str) -> dict[str, int]:
    counts = {}
    for name, pattern in _DIRECTIVE_PATTERNS.items():
        c = len(pattern.findall(text))
        if c:
            counts[name] = c
    return counts


def _detect_sections(text: str) -> list[tuple[str, str, int, int, int]]:
    """Return list of (id, title, header_level, start, end) for each section."""
    matches = list(_STEP_HEADER_RE.finditer(text))
    sections = []
    for i, m in enumerate(matches):
        hashes = m.group(1)
        level = len(hashes)
        step_num = m.group(2)  # may be None
        title = m.group(3).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        if step_num:
            section_id = f"Step {step_num}"
        else:
            # Use sanitized title as id
            section_id = re.sub(r"[^a-zA-Z0-9]+", "_", title)[:40].strip("_")
        sections.append((section_id, title, level, start, end))
    return sections


def _find_cross_refs(text: str, own_id: str) -> list[str]:
    """Find cross-references to other steps within the text."""
    refs = []
    for m in _CROSS_REF_RE.finditer(text):
        ref_id = f"Step {m.group(1)}"
        if ref_id != own_id and ref_id not in refs:
            refs.append(ref_id)
    return refs


def _detect_redundancy(text: str, sections: list[tuple]) -> list[RedundancyGroup]:
    """Find repeated constraint phrases across sections.

    Strategy: extract key verb+object phrases from constraint lines,
    find phrases appearing in 3+ sections.
    """
    # Extract normalized constraint phrases per section
    phrase_to_sections: dict[str, set[str]] = {}

    # Common constraint verb phrases to track
    tracking_patterns = [
        (
            r"(?:invent|fabricate|hallucinate).*(?:marker|ref|url|citation|identifier)",
            "invent/fabricate markers",
        ),
        (r"(?:preserve|copy|use).*(?:verbatim|exactly|character)", "preserve verbatim"),
        (
            r"(?:modify|alter|truncate|shorten|reconstruct).*(?:marker|ref|url)",
            "modify/alter markers",
        ),
        (r"(?:note|verify|record).*<ref>", "track <ref> values"),
        (r"(?:mention|expose).*(?:tool|service|internal)", "hide tool/service names"),
        (r"(?:invent|guess|approximate).*(?:URL|url|link)", "invent URLs"),
        (r"parallel.*(?:call|message|execution)", "parallel execution"),
        (r"single.*(?:message|query|response)", "single message/query"),
    ]

    for pat_re, label in tracking_patterns:
        compiled = re.compile(pat_re, re.IGNORECASE)
        for section_id, _title, _level, start, end in sections:
            section_text = text[start:end]
            if compiled.search(section_text):
                phrase_to_sections.setdefault(label, set()).add(section_id)

    # Also find repeated exact constraint lines (normalized)
    line_sections: dict[str, set[str]] = {}
    for section_id, _title, _level, start, end in sections:
        section_text = text[start:end]
        for line_match in _CONSTRAINT_LINE_RE.finditer(section_text):
            # Normalize: lowercase, strip bullets and extra spaces
            normalized = re.sub(r"^[-*]\s+", "", line_match.group()).strip().lower()
            normalized = re.sub(r"\s+", " ", normalized)
            if len(normalized) > 30:  # skip very short lines
                line_sections.setdefault(normalized[:80], set()).add(section_id)

    groups = []
    for label, secs in phrase_to_sections.items():
        if len(secs) >= 2:
            groups.append(
                RedundancyGroup(
                    pattern=label,
                    occurrences=len(secs),
                    sections=sorted(secs),
                )
            )

    # Add repeated exact lines
    for normalized, secs in line_sections.items():
        if len(secs) >= 3:
            groups.append(
                RedundancyGroup(
                    pattern=f'repeated line: "{normalized[:60]}..."',
                    occurrences=len(secs),
                    sections=sorted(secs),
                )
            )

    groups.sort(key=lambda g: g.occurrences, reverse=True)
    return groups


def _compute_flow_depth(graph: dict[str, list[str]]) -> int:
    """Compute longest chain of forward references (data flow depth).

    Handles cycles by tracking the current traversal path.
    """
    memo: dict[str, int] = {}

    def _depth(node: str, visiting: frozenset[str]) -> int:
        if node in memo:
            return memo[node]
        if node in visiting:
            return 0  # cycle detected, break it
        children = graph.get(node, [])
        if not children:
            memo[node] = 0
            return 0
        new_visiting = visiting | {node}
        d = 1 + max(_depth(c, new_visiting) for c in children)
        memo[node] = d
        return d

    return max((_depth(n, frozenset()) for n in graph), default=0)


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------


def analyze(text: str, file_path: str = "<stdin>") -> PromptAnalysis:
    """Run full quantitative analysis on a system prompt text."""
    analysis = PromptAnalysis(file_path=file_path)

    # Global metrics
    analysis.total_chars = len(text)
    analysis.total_words = len(text.split())
    analysis.total_lines = text.count("\n") + 1
    analysis.est_tokens = analysis.total_chars // 4
    analysis.total_directives = _count_directives(text)
    analysis.grand_total_directives = sum(analysis.total_directives.values())

    # Per-section analysis
    raw_sections = _detect_sections(text)
    for section_id, title, level, start, end in raw_sections:
        section_text = text[start:end]
        directives = _count_directives(section_text)

        metrics = SectionMetrics(
            id=section_id,
            title=title,
            level=level,
            words=len(section_text.split()),
            chars=len(section_text),
            lines=section_text.count("\n") + 1,
            directives=directives,
            total_directives=sum(directives.values()),
            constraint_lines=len(_CONSTRAINT_LINE_RE.findall(section_text)),
            cross_refs=_find_cross_refs(section_text, section_id),
        )
        analysis.sections.append(metrics)

    # Cross-reference graph (only step sections)
    for s in analysis.sections:
        if s.cross_refs:
            analysis.cross_reference_graph[s.id] = s.cross_refs

    analysis.data_flow_depth = _compute_flow_depth(analysis.cross_reference_graph)

    # Redundancy
    analysis.redundancy_groups = _detect_redundancy(text, raw_sections)

    return analysis


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _format_json(analysis: PromptAnalysis) -> str:
    d = asdict(analysis)
    return json.dumps(d, indent=2, ensure_ascii=False)


def _format_markdown(analysis: PromptAnalysis) -> str:
    lines = []
    lines.append("# Prompt Analysis: Quantitative Report")
    lines.append("")

    # Global summary
    lines.append("## Global Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Words | {analysis.total_words:,} |")
    lines.append(f"| Characters | {analysis.total_chars:,} |")
    lines.append(f"| Lines | {analysis.total_lines:,} |")
    lines.append(f"| Est. tokens | ~{analysis.est_tokens:,} |")
    lines.append(f"| Total directive keywords | {analysis.grand_total_directives} |")
    lines.append(f"| Sections detected | {len(analysis.sections)} |")
    lines.append(f"| Data flow depth | {analysis.data_flow_depth} |")
    lines.append("")

    # Directive breakdown
    lines.append("### Directive Keyword Counts")
    lines.append("")
    for kw in [
        "MUST",
        "MUST NOT",
        "SHALL NOT",
        "SHOULD",
        "SHOULD NOT",
        "MAY",
        "NEVER",
        "CRITICAL",
        "IMPORTANT",
    ]:
        count = analysis.total_directives.get(kw, 0)
        if count:
            lines.append(f"- **{kw}**: {count}")
    lines.append("")

    # Per-section table
    lines.append("## Per-Section Breakdown")
    lines.append("")
    lines.append(
        "| Section | Words | Directives | Density (/100w) | Constraint lines | Cross-refs |"
    )
    lines.append(
        "|---------|-------|-----------|-----------------|-----------------|------------|"
    )
    for s in analysis.sections:
        density = f"{s.directive_density:.1f}"
        xrefs = ", ".join(s.cross_refs) if s.cross_refs else "-"
        indent = "  " * (s.level - 2) if s.level > 2 else ""
        name = f"{indent}{s.id}: {s.title[:50]}"
        lines.append(
            f"| {name} | {s.words} | {s.total_directives} | {density} | {s.constraint_lines} | {xrefs} |"
        )
    lines.append("")

    # Top 5 heaviest sections
    sorted_sections = sorted(
        analysis.sections, key=lambda s: s.total_directives, reverse=True
    )
    lines.append("### Heaviest Sections (by directive count)")
    lines.append("")
    for s in sorted_sections[:5]:
        pct = (
            (s.total_directives / analysis.grand_total_directives * 100)
            if analysis.grand_total_directives
            else 0
        )
        lines.append(
            f"1. **{s.id}** ({s.title[:40]}): {s.total_directives} directives ({pct:.0f}% of total), {s.words} words"
        )
    lines.append("")

    # Cross-reference graph
    if analysis.cross_reference_graph:
        lines.append("## Cross-Reference Graph")
        lines.append("")
        for src, targets in analysis.cross_reference_graph.items():
            lines.append(f"- {src} -> {', '.join(targets)}")
        lines.append(
            f"\nData flow depth: {analysis.data_flow_depth} (longest forward reference chain)"
        )
        lines.append("")

    # Redundancy
    if analysis.redundancy_groups:
        lines.append("## Redundancy Patterns")
        lines.append("")
        lines.append("Constraint themes appearing in multiple sections:")
        lines.append("")
        for g in analysis.redundancy_groups:
            lines.append(
                f"- **{g.pattern}**: {g.occurrences} sections ({', '.join(g.sections)})"
            )
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Analyze a system prompt or SOP")
    parser.add_argument("file", help="Path to the prompt file (use '-' for stdin)")
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    args = parser.parse_args()

    if args.file == "-":
        text = sys.stdin.read()
        file_path = "<stdin>"
    else:
        with open(args.file) as f:
            text = f.read()
        file_path = args.file

    analysis = analyze(text, file_path)

    if args.format == "json":
        print(_format_json(analysis))
    else:
        print(_format_markdown(analysis))


if __name__ == "__main__":
    main()
