"""Process-safety reasoning eval for Inspect.

A defensive eval measuring how a model reasons about process-safety hazards and UK safety
regulation. Two task variants share one dataset:

- ``process_safety_mcq`` — multiple-choice hazard classification and regulatory reasoning,
  scored with ``choice()``.
- ``process_safety_reasoning`` — free-response failure-mode reasoning, scored with
  ``model_graded_qa()`` against a per-item rubric.
- ``process_safety_agentic`` — sandboxed agentic variant: the model uses ``bash``/``python``
  tools inside a Docker sandbox to investigate a noisy file set, compute the answer, and submit
  it (scored with ``model_graded_qa()``). Uses a separate scenario dataset.

The tasks are imported here so the ``inspect_ai`` entry point (see ``pyproject.toml``)
registers them for discovery, e.g. ``inspect eval process_safety/process_safety_mcq``.
"""

from .task import process_safety_agentic, process_safety_mcq, process_safety_reasoning

__all__: list[str] = [
    "process_safety_agentic",
    "process_safety_mcq",
    "process_safety_reasoning",
]
