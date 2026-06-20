"""Dataset loading for the process-safety eval.

Records cross two untyped boundaries: the raw row read from JSONL is a ``dict[str, Any]``, and
``Sample.metadata`` is itself a ``dict[str, Any]`` at the storage layer. Both go through one
Pydantic model, :class:`ProcessSafetyMetadata`. ``record_to_sample`` runs each row through it on
the way in, so a malformed row (e.g. an unknown ``category``) fails validation at load time
rather than later inside a scorer. Solvers and scorers read the metadata back out, typed, via
``sample.metadata_as(...)``.

The JSONL stores answers as the full option text and questions under ``question``;
``record_to_sample`` adapts these to Inspect's ``Sample`` shape (``input``, plus a ``target``
letter for the ``choice()`` scorer).
"""

from pathlib import Path
from typing import Any, Literal

from inspect_ai.dataset import Dataset, Sample, json_dataset
from pydantic import BaseModel, ConfigDict

# Dataset location exposed as a module constant (an inspect_evals convention).
DATASET_PATH = Path(__file__).parent / "data" / "process_safety.jsonl"

# Choice order is shuffled per sample to remove answer-position bias: the items are authored
# with the correct option first, so without shuffling a model could score well by always
# picking "A". A fixed seed keeps the shuffle reproducible run to run (mirroring temperature=0);
# shuffle_choices remaps each sample's letter target accordingly and is a no-op for reasoning
# items, which have no choices.
CHOICE_SHUFFLE_SEED = 20260619

# Closed string sets: mypy rejects an invalid literal in source, and Pydantic rejects an
# invalid value in the data file, while the JSONL stores the bare string (no Enum mapping).
Variant = Literal["mcq", "reasoning"]
Category = Literal[
    "clp-classification",
    "dsear",
    "coshh",
    "hierarchy-of-control",
    "risk-assessment-duties",
    "process-safety-method",
]
Difficulty = Literal["easy", "medium", "hard"]
Confidence = Literal["low", "medium", "high"]


class ProcessSafetyMetadata(BaseModel):
    """Typed view of a sample's metadata, hydrated via ``Sample.metadata_as``."""

    # Inspect's metadata_as() requires the model to be frozen.
    model_config = ConfigDict(frozen=True)

    variant: Variant
    category: Category
    # Provenance: the regulation or standard the item derives from.
    source: str
    difficulty: Difficulty
    confidence: Confidence
    # Authoring notes / verification caveats; not shown to the model under test.
    expert_notes: str = ""
    # Grading rubric for the model-graded reasoning variant (empty for mcq items). Also
    # carried as the Sample target for reasoning items so model_graded_qa can grade against it.
    criterion: str = ""
    # Per-distractor explanations for mcq items (None for reasoning items).
    distractor_rationale: dict[str, str] | None = None


def _answer_to_target_letter(answer: str, choices: list[str]) -> str:
    """Map an mcq answer (full option text) to its choice letter (A, B, C, ...).

    ``choice()`` scores against the option letter, so the stored answer text must resolve to
    exactly one choice; a mismatch is a dataset error and is raised immediately.
    """
    try:
        index = choices.index(answer)
    except ValueError as exc:
        raise ValueError(f"answer {answer!r} is not one of choices {choices!r}") from exc
    return chr(ord("A") + index)


def record_to_sample(record: dict[str, Any]) -> Sample:
    """Convert one raw JSONL record into a typed :class:`Sample`.

    Validating the metadata through :class:`ProcessSafetyMetadata` here means a malformed
    row fails loudly at load time, with the offending field named.
    """
    variant: Variant = record["variant"]
    choices: list[str] | None = record.get("choices")
    criterion: str = record.get("criterion", "")

    metadata = ProcessSafetyMetadata(
        variant=variant,
        category=record["category"],
        source=record["source"],
        difficulty=record["difficulty"],
        confidence=record["confidence"],
        expert_notes=record.get("expert_notes", ""),
        criterion=criterion,
        distractor_rationale=record.get("distractor_rationale"),
    )

    if variant == "mcq":
        if choices is None:
            raise ValueError(f"mcq item {record['id']!r} is missing 'choices'")
        target = _answer_to_target_letter(record["answer"], choices)
    else:
        # Reasoning items are graded against the rubric rather than a fixed answer.
        target = criterion

    return Sample(
        id=record["id"],
        input=record["question"],
        target=target,
        choices=choices,
        metadata=metadata.model_dump(),
    )


def load(variant: Variant) -> Dataset:
    """Load the dataset filtered to a single variant ("mcq" or "reasoning")."""
    ds = json_dataset(
        str(DATASET_PATH),
        sample_fields=record_to_sample,
        shuffle_choices=CHOICE_SHUFFLE_SEED,
    )
    return ds.filter(lambda s: s.metadata_as(ProcessSafetyMetadata).variant == variant)
