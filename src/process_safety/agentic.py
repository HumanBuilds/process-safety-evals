"""Dataset loading for the agentic process-safety variant.

Where :mod:`.dataset` serves single-turn Q&A, this module serves scenarios the model has to
investigate. Each sample ships a small set of files into a Docker sandbox — some carrying the
information needed to answer, some noise. The model uses ``bash`` and ``python`` tools (wired
up in :mod:`.task`) to read the files, run a calculation, and submit an answer. The
signal-vs-noise mix is what makes this measure finding and computing the right answer under
clutter, rather than recalling a fact.

Two untyped boundaries are bridged here, as in :mod:`.dataset`: the raw JSONL row
(``dict[str, Any]``) and ``Sample.metadata`` (also ``dict[str, Any]``). Each row goes through
:class:`AgenticMetadata`, so a malformed scenario fails at load time with the offending field
named, rather than deep inside the agent loop.

File wiring: a scenario's files live on disk under ``data/agentic/<id>/``. Each row lists them
by name; :func:`record_to_agentic_sample` turns those into a ``Sample.files`` mapping
``"/data/<name>" -> "<local path>"``, which Inspect copies into the sandbox before the solver
runs. They stay as real files (not JSON blobs) so they remain diffable and auditable.
"""

from pathlib import Path
from typing import Any

from inspect_ai.dataset import Dataset, MemoryDataset, Sample
from pydantic import BaseModel, ConfigDict

from process_safety.dataset import Category, Confidence, Difficulty

# Scenario data location and the path the files are mounted at inside the sandbox.
AGENTIC_DATASET_PATH = Path(__file__).parent / "data" / "agentic.jsonl"
AGENTIC_DATA_DIR = AGENTIC_DATASET_PATH.parent / "agentic"
SANDBOX_DATA_DIR = "/data"

# The sandbox spec for the agentic task. Inspect resolves this relative compose file
# when the task runs; tests override it with the built-in "local" sandbox so CI needs
# no Docker.
SANDBOX_COMPOSE = Path(__file__).parents[2] / "sandbox" / "compose.yaml"


class AgenticMetadata(BaseModel):
    """Typed view of an agentic scenario's metadata, hydrated via ``Sample.metadata_as``.

    Reuses the shared ``Category`` so per-category reporting lines up with the MCQ and reasoning
    variants. ``relevant_files`` records which of the shipped files carry the answer — currently
    documentation, and available later for an intermediate "did it open the right file" check.
    """

    # Inspect's metadata_as() requires the model to be frozen.
    model_config = ConfigDict(frozen=True)

    category: Category
    source: str
    difficulty: Difficulty
    confidence: Confidence
    expert_notes: str = ""
    relevant_files: tuple[str, ...] = ()


def record_to_agentic_sample(record: dict[str, Any]) -> Sample:
    """Convert one raw agentic JSONL record into a typed :class:`Sample`.

    Builds the ``files`` mapping from the scenario's on-disk files and validates loudly: every
    listed file must exist, and every ``relevant_files`` entry must be one of the listed
    ``files`` (a typo there would silently disable a future intermediate check). The rubric is
    carried as the sample ``target`` so ``model_graded_qa`` reads it from ``target.text``, the
    same convention the reasoning variant uses.
    """
    scenario_id: str = record["id"]
    scenario_dir = AGENTIC_DATA_DIR / scenario_id
    file_names: list[str] = record["files"]
    relevant: list[str] = record.get("relevant_files", [])

    files: dict[str, str] = {}
    for name in file_names:
        local_path = scenario_dir / name
        if not local_path.is_file():
            raise ValueError(
                f"agentic item {scenario_id!r} lists missing file {name!r} ({local_path})"
            )
        files[f"{SANDBOX_DATA_DIR}/{name}"] = str(local_path)

    unknown_relevant = set(relevant) - set(file_names)
    if unknown_relevant:
        raise ValueError(
            f"agentic item {scenario_id!r} marks files relevant that it does not ship: "
            f"{sorted(unknown_relevant)}"
        )

    metadata = AgenticMetadata(
        category=record["category"],
        source=record["source"],
        difficulty=record["difficulty"],
        confidence=record["confidence"],
        expert_notes=record.get("expert_notes", ""),
        relevant_files=tuple(relevant),
    )

    return Sample(
        id=scenario_id,
        input=record["question"],
        target=record["criterion"],
        files=files,
        metadata=metadata.model_dump(),
    )


def load_agentic() -> Dataset:
    """Load the agentic scenarios as a :class:`Dataset`.

    Read as JSONL by hand rather than via ``json_dataset`` because each row's files must
    be resolved against its scenario directory before the ``Sample`` is built.
    """
    import json

    samples = [
        record_to_agentic_sample(json.loads(line))
        for line in AGENTIC_DATASET_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return MemoryDataset(samples)
