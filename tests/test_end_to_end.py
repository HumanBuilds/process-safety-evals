"""Offline end-to-end tests for the process-safety eval.

Every test runs against the ``mockllm/model`` provider, so the suite executes in CI with no API
key and no network (the AISI ``inspect_evals`` contributing convention). Each variant has two
tests: a success test, where the pipeline runs to completion and produces scores; and an
error-handling test, where a malformed model/grader response is scored rather than crashing the
run. A few dataset-validation tests cover the typed loader's failure paths directly.
"""

from collections.abc import Iterator
from typing import Any

import pytest

# `eval` here is Inspect's eval-runner (it shadows the builtin); it executes tasks, not code.
from inspect_ai import eval
from inspect_ai.model import Model, ModelOutput, get_model
from inspect_ai.scorer import CORRECT, INCORRECT
from pydantic import ValidationError

from process_safety.agentic import record_to_agentic_sample
from process_safety.dataset import record_to_sample
from process_safety.task import (
    process_safety_agentic,
    process_safety_mcq,
    process_safety_reasoning,
)


def _mock(content: str) -> Model:
    """A ``mockllm`` model that returns the same ``content`` for every generation.

    The infinite generator means the model never runs out of responses regardless of how many
    samples (or grader calls) a test drives through it.
    """

    def outputs() -> Iterator[ModelOutput]:
        while True:
            yield ModelOutput.from_content(model="mockllm", content=content)

    return get_model("mockllm/model", custom_outputs=outputs())


def _mock_submit(answer: str) -> Model:
    """A ``mockllm`` model that immediately calls the ``submit`` tool with ``answer``.

    ``basic_agent`` ends its tool-use loop as soon as the model submits, so this mock drives
    the agentic pipeline to completion without ever touching ``bash``/``python`` — letting the
    end-to-end test exercise the loop, scorer, and metrics with no real sandbox execution.
    """

    def outputs() -> Iterator[ModelOutput]:
        while True:
            yield ModelOutput.for_tool_call(
                model="mockllm",
                tool_name="submit",
                tool_arguments={"answer": answer},
            )

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


# --- Agentic variant -------------------------------------------------------------------


def test_agentic_runs_end_to_end() -> None:
    """The sandboxed agentic pipeline runs on the ``local`` sandbox (no Docker in CI).

    The model under test submits an answer immediately; the grader returns ``GRADE: C``. This
    confirms the ``basic_agent`` loop, file-shipping, scorer, and metrics all wire together.
    """
    log = eval(
        process_safety_agentic(),
        model=_mock_submit("8-hr TWA is ~48 mg/m3, below the 50 WEL (COSHH/EH40): compliant."),
        model_roles={"grader": _mock("Time-weighting and limit are right. GRADE: C")},
        sandbox="local",
        limit=1,
    )[0]
    assert log.status == "success"
    assert log.samples is not None
    for sample in log.samples:
        assert sample.scores is not None
        score = next(iter(sample.scores.values()))
        assert score.value == CORRECT


# --- Agentic dataset validation --------------------------------------------------------


def _base_agentic_record() -> dict[str, Any]:
    """A minimal agentic record pointing at the committed ``agt-001`` scenario files."""
    return {
        "id": "agt-001",
        "category": "coshh",
        "source": "test source",
        "question": "Determine compliance.",
        "criterion": "Computes the 8-hour TWA and compares to the WEL.",
        "difficulty": "medium",
        "confidence": "high",
        "files": ["exposure_log.csv", "eh40_extract.txt"],
        "relevant_files": ["exposure_log.csv"],
    }


def test_record_to_agentic_sample_maps_files_into_sandbox() -> None:
    """Listed files resolve to a ``/data/<name>`` -> local-path mapping for the sandbox."""
    sample = record_to_agentic_sample(_base_agentic_record())
    assert sample.files is not None
    assert "/data/exposure_log.csv" in sample.files
    assert sample.files["/data/exposure_log.csv"].endswith("exposure_log.csv")
    # The rubric is carried as the target so model_graded_qa can grade against it.
    assert sample.target == "Computes the 8-hour TWA and compares to the WEL."


def test_record_to_agentic_sample_rejects_missing_file() -> None:
    """A listed file that does not exist on disk is a dataset error and is raised."""
    record = _base_agentic_record()
    record["files"] = ["exposure_log.csv", "does_not_exist.txt"]
    with pytest.raises(ValueError, match="missing file"):
        record_to_agentic_sample(record)


def test_record_to_agentic_sample_rejects_unknown_relevant_file() -> None:
    """A relevant_files entry not among the shipped files is caught at load time."""
    record = _base_agentic_record()
    record["relevant_files"] = ["not_shipped.txt"]
    with pytest.raises(ValueError, match="relevant"):
        record_to_agentic_sample(record)


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
