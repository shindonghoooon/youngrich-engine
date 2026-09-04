import re
from pathlib import Path

import pytest

from engine.tracking_models import ThesisStatus


ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "docs" / "specs"
LINK_PATTERN = re.compile(r"\[[^]]+\]\(([^)]+)\)")
CODE_PATH_PATTERN = re.compile(r"`([^`]+)`")


def _local_link_targets(document: Path) -> list[Path]:
    targets: list[Path] = []
    for raw_target in LINK_PATTERN.findall(document.read_text(encoding="utf-8")):
        target = raw_target.strip().strip("<>").split("#", 1)[0]
        if not target or "://" in target or target.startswith(("mailto:", "#")):
            continue
        targets.append((document.parent / target).resolve())
    return targets


@pytest.mark.parametrize(
    "document",
    [ROOT / "PROJECT.md", ROOT / "README.md", ROOT / "docs" / "roadmap.md"],
)
def test_project_navigation_links_resolve(document: Path):
    missing = [str(path.relative_to(ROOT)) for path in _local_link_targets(document) if not path.exists()]
    assert not missing, f"broken links in {document.relative_to(ROOT)}: {missing}"


def test_all_internal_documentation_links_resolve():
    documents = [ROOT / "PROJECT.md", ROOT / "README.md"]
    documents.extend((ROOT / "docs").rglob("*.md"))
    documents.extend((ROOT / "reports").rglob("*.md"))

    missing: list[str] = []
    for document in documents:
        for target in _local_link_targets(document):
            if not target.exists():
                missing.append(
                    f"{document.relative_to(ROOT)} -> {target.relative_to(ROOT)}"
                )
    assert not missing, "broken internal documentation links:\n" + "\n".join(missing)


def test_frozen_spec_headers_and_implementation_paths_are_valid():
    for document in sorted(SPECS.glob("*.md")):
        if document.name == "README.md":
            continue
        text = document.read_text(encoding="utf-8")
        for required in (
            "Status: FROZEN",
            "Version:",
            "Authoritative: YES",
            "Last Updated:",
            "Implementation:",
            "Tests:",
            "Supersedes:",
            "Change Policy:",
        ):
            assert required in text, f"{document.name} lacks {required!r}"

        implementation_line = next(
            line for line in text.splitlines() if line.startswith("Implementation:")
        )
        implementation_paths = CODE_PATH_PATTERN.findall(implementation_line)
        assert implementation_paths, f"{document.name} has no implementation reference"
        for relative_path in implementation_paths:
            assert (ROOT / relative_path).is_file(), (
                f"{document.name} references missing implementation {relative_path}"
            )


def test_research_and_validation_documents_declare_authority_boundaries():
    for document in (ROOT / "docs" / "research").glob("*.md"):
        text = document.read_text(encoding="utf-8")
        assert "Status: RESEARCH" in text
        assert "Authoritative: NO" in text
        assert "Implementation Allowed: NO unless separately approved" in text

    for document in (ROOT / "docs" / "validation").glob("*.md"):
        if document.name == "README.md":
            continue
        text = document.read_text(encoding="utf-8")
        assert "Status: VALIDATION" in text
        assert "Authoritative for Results: YES" in text
        assert "Authoritative for Investment Rules: NO" in text


def test_stable_is_not_a_canonical_thesis_status():
    assert "stable" not in {status.value for status in ThesisStatus}
    tracking_spec = (SPECS / "tracking-engine-v1.md").read_text(encoding="utf-8")
    assert "must never emit or store `STABLE`" in tracking_spec
