"""Build the frontier-vs-local comparison table from committed eval logs.

Reads one ``.eval`` log per labelled column and prints a Markdown table of
per-category accuracy (±stderr), so the README results table is *regenerated from
the committed artifacts* rather than transcribed by hand (and so it can never drift
from the logs it claims to summarise).

Run one variant at a time, passing one ``"Label=path"`` per column, e.g.:

    uv run python scripts/compare_runs.py \
        "Frontier — Haiku=logs/<frontier-mcq>.eval" \
        "Local — Qwen2.5-3B=logs/<local-mcq>.eval"

(The exact log filenames behind the committed README table are listed there.)
"""

from __future__ import annotations

import sys

from inspect_ai.log import EvalLog, read_eval_log

# The six regulatory categories, plus the overall aggregate Inspect emits as "all".
CATEGORIES = [
    "clp-classification",
    "dsear",
    "coshh",
    "hierarchy-of-control",
    "risk-assessment-duties",
    "process-safety-method",
]
ROW_KEYS = [*CATEGORIES, "all"]


def extract_scores(log: EvalLog) -> dict[str, tuple[float, float]]:
    """Map each category (and "all") to its ``(accuracy, stderr)`` for one log.

    Inspect flattens grouped metrics into the single scorer's ``metrics`` dict: the
    accuracy for category ``c`` is stored under key ``c``, and its standard error
    under ``c + "2"`` (Inspect disambiguates the duplicate display name created by
    attaching ``grouped(accuracy())`` and ``grouped(stderr())`` together). The
    overall aggregates live under ``"all"`` / ``"all2"``.

    Access the scorer metrics via ``log.results.scores[0].metrics``; each value is
    an object with a ``.value`` float. A log missing an expected category raises,
    so a malformed run fails loudly here rather than producing a half-built table.
    """
    if log.results is None or not log.results.scores:
        print(f"no results in {log.location}", file=sys.stderr)
        return {}

    metrics = log.results.scores[0].metrics
    result: dict[str, tuple[float, float]] = {}
    for key in ROW_KEYS:
        if key not in metrics:
            raise ValueError(f"no accuracy metric for {key} in {log.location}")
        if key + "2" not in metrics:
            raise ValueError(f"no stderr metric for {key} in {log.location}")
        result[key] = (metrics[key].value, metrics[key + "2"].value)

    return result


def format_cell(acc: float, stderr: float) -> str:
    """Render one accuracy/stderr pair the way the README table does."""
    return f"{acc:.3f} (±{stderr:.3f})"


def main(argv: list[str]) -> int:
    # The table uses ± and — ; force UTF-8 so redirecting to a file on Windows
    # (where the console code page is often cp1252) doesn't mangle them.
    sys.stdout.reconfigure(encoding="utf-8")

    if not argv:
        print(
            'usage: compare_runs.py "Label=path.eval" ["Label2=path2.eval" ...]',
            file=sys.stderr,
        )
        return 2

    columns: list[tuple[str, dict[str, tuple[float, float]]]] = []
    for arg in argv:
        label, sep, path = arg.partition("=")
        if not sep:
            print(f"bad column spec (need 'Label=path'): {arg!r}", file=sys.stderr)
            return 2
        columns.append((label, extract_scores(read_eval_log(path))))

    labels = [label for label, _ in columns]
    print("| Category | " + " | ".join(labels) + " |")
    print("| --- | " + " | ".join("---" for _ in columns) + " |")
    for key in ROW_KEYS:
        name = "**Overall**" if key == "all" else f"`{key}`"
        cells = []
        for _, scores in columns:
            cell = format_cell(*scores[key]) if key in scores else "—"
            cells.append(f"**{cell}**" if key == "all" else cell)
        print(f"| {name} | " + " | ".join(cells) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
