"""Keep the advertised tool count honest.

The README, the docs and the --help text all quote a tool count. They drifted
to "157" and "190+" while the server actually registered 230, so users were
told one number and shown another. This pins the claims to what is really
registered: add a tool, and these fail until the docs are updated.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# Files that quote a tool count, and the pattern that captures it.
COUNT_SOURCES = [
    (REPO / "README.md", r"\*\*(\d+)\+? tools\*\*"),
    (REPO / "ludus_mcp/server/main.py", r"List all (\d+) available FastMCP tools"),
    (REPO / "ludus_mcp/server/main.py", r"AVAILABLE TOOL CATEGORIES \((\d+) tools total\)"),
    (REPO / "ludus_mcp/cli/main.py", r"(\d+) FastMCP tools across"),
]


def _registered_tool_count() -> int:
    """Count the tools the server actually registers."""
    import asyncio
    import os

    os.environ.setdefault("LUDUS_API_KEY", "dummy")
    os.environ.setdefault("LUDUS_API_URL", "https://ludus.example:8080")

    from ludus_mcp.server.main import _get_tool_names, _initialize_mcp_server

    mcp = _initialize_mcp_server()
    return len(asyncio.run(_get_tool_names(mcp)))


@pytest.fixture(scope="module")
def actual_count():
    return _registered_tool_count()


def test_readme_tool_count_matches_reality(actual_count):
    readme = (REPO / "README.md").read_text()
    match = re.search(r"\*\*(\d+)\+? tools\*\*", readme)
    assert match, "README no longer states a tool count in the expected form"
    assert int(match.group(1)) == actual_count, (
        f"README advertises {match.group(1)} tools but the server registers "
        f"{actual_count}. Update the README."
    )


@pytest.mark.parametrize("path,pattern", COUNT_SOURCES)
def test_quoted_counts_agree_with_server(path, pattern, actual_count):
    text = path.read_text()
    matches = re.findall(pattern, text)
    assert matches, f"{path.name} no longer quotes a count matching {pattern!r}"
    for found in matches:
        assert int(found) == actual_count, (
            f"{path.name} says {found} tools; the server registers {actual_count}."
        )


def test_module_count_matches_mounted_modules():
    """The docs quote a module count too; keep it tied to the mount list."""
    main = (REPO / "ludus_mcp/server/main.py").read_text()
    block = main[main.index("tool_modules = ["):]
    block = block[: block.index("]")]
    mounted = re.findall(r'\("([^"]+)",', block)
    # core is created directly rather than mounted, so it is not in the list
    total_modules = len(mounted) + 1

    quoted = re.findall(r"across (\d+) modules", main)
    assert quoted, "main.py no longer quotes a module count"
    for found in quoted:
        assert int(found) == total_modules, (
            f"main.py says {found} modules; {total_modules} are registered."
        )


def _documented_tool_names() -> dict[str, set[str]]:
    """Collect `tool_name` cells from the tool tables in the docs."""
    names: dict[str, set[str]] = {}
    for doc in [REPO / "docs/tools-reference.md"]:
        found = set()
        in_tool_table = False
        for line in doc.read_text().splitlines():
            # only tables headed "| Tool | Description |" list tool names; the
            # parameter table uses the same row shape for things like `user_id`
            if re.match(r"\|\s*Tool\s*\|\s*Description\s*\|", line):
                in_tool_table = True
                continue
            if in_tool_table:
                if not line.startswith("|"):
                    in_tool_table = False
                    continue
                m = re.match(r"\|\s*`([a-z][a-z0-9_]*)`\s*\|", line)
                if m:
                    found.add(m.group(1))
        names[doc.name] = found
    return names


def test_documented_tool_names_all_exist(actual_count):
    """Docs listing tools that do not exist send assistants after phantom names.

    The reference previously advertised `apply_blueprint`, `get_console_ticket`,
    `run_diagnostics`, `migrate_sqlite` and `migrate_sdn` -- none of which were
    ever registered.
    """
    import asyncio
    import os

    os.environ.setdefault("LUDUS_API_KEY", "dummy")
    from ludus_mcp.server.main import _get_tool_names, _initialize_mcp_server

    registered = set(asyncio.run(_get_tool_names(_initialize_mcp_server())))

    problems = []
    for doc, documented in _documented_tool_names().items():
        missing = sorted(documented - registered)
        if missing:
            problems.append(f"{doc}: documents non-existent tools {missing}")

    assert not problems, "\n".join(problems)


def test_every_registered_tool_is_documented():
    """112 real tools were once absent from the reference entirely."""
    import asyncio
    import os

    os.environ.setdefault("LUDUS_API_KEY", "dummy")
    from ludus_mcp.server.main import _get_tool_names, _initialize_mcp_server

    registered = set(asyncio.run(_get_tool_names(_initialize_mcp_server())))
    documented = _documented_tool_names()["tools-reference.md"]

    undocumented = sorted(registered - documented)
    assert not undocumented, (
        f"{len(undocumented)} tools are not in docs/tools-reference.md: {undocumented}"
    )
