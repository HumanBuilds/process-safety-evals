"""Offline end-to-end tests for the process-safety eval.

Every test runs against the ``mockllm/model`` provider, so the suite executes in CI with no
API key and no network (the AISI ``inspect_evals`` contributing convention). Each variant has:

- a *success* test — the pipeline runs to completion and produces scores; and
- an *error-handling* test — a malformed model/grader response is handled gracefully rather
  than crashing the run.

A few dataset-validation tests cover the typed loader's failure paths directly.
"""

from collections.abc import Iterator
from typing import Any

import pytest

# `eval` here is Inspect's eval-runner (it shadows the builtin); it executes tasks, not code.
from inspect_ai import eval
from inspect_ai.model import Model, ModelOutput, get_model
from inspect_ai.scorer import CORRECT, INCORRECT
from pydantic import ValidationError

from process_safety.dataset import record_to_sample
from process_safety.task import process_safety_mcq, process_safety_reasoning


def _mock(content: str) -> Model:
    """A ``mockllm`` model that returns the same ``content`` for every generation.

    The infinite generator means the model never runs out of responses regardless of how many
    samples (or grader calls) a test drives through it.
    """

    def outputs() -> Iterator[ModelOutput]:
        while True:
            yield ModelOutput.from_content(model="mockllm", content=content)

    return get_model("mockllm/model", custom_outputs=outputs())


# --- MCQ variant -----------------------------------------------------------------------


def test_mcq_runs_end_to_end() -> None:
    """The deterministic MCQ pipeline runs and scores every sample."""
    log = eval(process_safety_mcq(), model="mockllm/model", limit=2)[0]
    assert log.status == "success"
    assert log.samples is not None
    assert len(log.samples) == 2
    assert all(sample.scores for sample in log.samples)


def test_mcq_handles_unparseable_answer() -> None:
    """A model reply with no selectable option is scored incorrect, not crashed on."""
    log = eval(process_safety_mcq(), model=_mock("I would rather not choose."), limit=2)[0]
    assert log.status == "success"
    assert log.samples is not None
    for sample in log.samples:
        assert sample.scores is not None
        score = next(iter(sample.scores.values()))
        assert score.value == INCORRECT


# --- Reasoning variant -----------------------------------------------------------------


def test_reasoning_runs_end_to_end() -> None:
    """The model-graded pipeline runs; a grader verdict of ``GRADE: C`` scores correct."""
    log = eval(
        process_safety_reasoning(),
        model="mockllm/model",
        model_roles={"grader": _mock("The hazard and control are both right. GRADE: C")},
        limit=2,
    )[0]
    assert log.status == "success"
    assert log.samples is not None
    assert len(log.samples) == 2
    for sample in log.samples:
        assert sample.scores is not None
        score = next(iter(sample.scores.values()))
        assert score.value == CORRECT


def test_reasoning_handles_missing_grade() -> None:
    """The grader returns prose with no ``GRADE:`` token.

    ``model_graded_qa`` cannot extract a grade from this reply. The run should still finish
    and each sample should be scored — the failure must degrade gracefully, not crash.
    """
    log = eval(
        process_safety_reasoning(),
        model="mockllm/model",
        model_roles={"grader": _mock("I am not sure how to grade this submission.")},
        limit=2,
    )[0]
    assert log.status == "success"
    assert log.samples is not None
    assert len(log.samples) == 2
    for sample in log.samples:
        assert sample.scores is not None
        score = next(iter(sample.scores.values()))
        assert score.value == INCORRECT


# --- Dataset validation ----------------------------------------------------------------


def _base_mcq_record() -> dict[str, Any]:
    """A minimal, valid raw MCQ record used as a starting point for the validation tests."""
    return {
        "id": "mcq-test",
        "variant": "mcq",
        "category": "dsear",
        "source": "test source",
        "question": "Which regulation governs this?",
        "choices": ["alpha", "beta"],
        "answer": "alpha",
        "difficulty": "easy",
        "confidence": "high",
    }


def test_record_to_sample_maps_answer_to_choice_letter() -> None:
    """A valid MCQ record's answer text resolves to its choice letter for ``choice()``."""
    sample = record_to_sample(_base_mcq_record())
    assert sample.target == "A"  # "alpha" is the first choice


def test_record_to_sample_rejects_unknown_category() -> None:
    """An out-of-set category fails Pydantic validation at load time, not later."""
    record = _base_mcq_record()
    record["category"] = "not-a-real-category"
    with pytest.raises(ValidationError):
        record_to_sample(record)


def test_record_to_sample_rejects_answer_not_in_choices() -> None:
    """An MCQ answer that matches none of the choices is a dataset error and is raised."""
    record = _base_mcq_record()
    record["answer"] = "gamma"
    with pytest.raises(ValueError, match="not one of choices"):
        record_to_sample(record)
