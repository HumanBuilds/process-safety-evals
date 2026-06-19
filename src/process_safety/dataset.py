"""Dataset loading for the process-safety eval.

Records cross two untyped boundaries: the raw row read from JSONL is a ``dict[str, Any]``,
and ``Sample.metadata`` is itself a ``dict[str, Any]`` at the storage layer. Both are
bridged with a single Pydantic model, :class:`ProcessSafetyMetadata`. ``record_to_sample``
funnels each row *through* the model on the way in, so a malformed row (e.g. an unknown
``category``) fails validation at load time rather than surfacing later inside a scorer.
Solvers and scorers read the metadata back out, typed, via ``sample.metadata_as(...)``.
"""

from pathlib import Path
from typing import Any, Literal

from inspect_ai.dataset import Dataset, Sample, json_dataset
from pydantic import BaseModel

# Dataset location exposed as a module constant (an inspect_evals convention).
DATASET_PATH = Path(__file__).parent / "data" / "process_safety.jsonl"

# Closed string sets: mypy rejects an invalid literal in source, and Pydantic rejects an
# invalid value in the data file, while the JSONL stores the bare string (no Enum mapping).
Variant = Literal["mcq", "reasoning"]
Category = Literal["DSEAR", "COSHH", "CLP", "hierarchy-of-control"]


class ProcessSafetyMetadata(BaseModel):
    """Typed view of a sample's metadata, hydrated via ``Sample.metadata_as``."""

    variant: Variant
    category: Category
    # Grading rubric for the model-graded reasoning variant; empty for mcq items.
    criterion: str = ""
    # Provenance: the regulation or standard the item derives from.
    source: str = ""


def record_to_sample(record: dict[str, Any]) -> Sample:
    """Convert one raw JSONL record into a typed :class:`Sample`.

    Validating the metadata through :class:`ProcessSafetyMetadata` here means a malformed
    row fails loudly at load time, with the offending field named.
    """
    metadata = ProcessSafetyMetadata(
        variant=record["variant"],
        category=record["category"],
        criterion=record.get("criterion", ""),
        source=record.get("source", ""),
    )
    return Sample(
        id=record["id"],
        input=record["input"],
        target=record["target"],
        choices=record.get("choices"),
        metadata=metadata.model_dump(),
    )


def load(variant: Variant) -> Dataset:
    """Load the dataset filtered to a single variant ("mcq" or "reasoning")."""
    ds = json_dataset(str(DATASET_PATH), sample_fields=record_to_sample)
    return ds.filter(lambda s: s.metadata_as(ProcessSafetyMetadata).variant == variant)
