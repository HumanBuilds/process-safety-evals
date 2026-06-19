"""Process-safety reasoning eval for Inspect.

A defensive eval measuring whether a model reasons correctly about process-safety hazards
and UK safety regulation. Two task variants share one hand-authored dataset:

- ``process_safety_mcq`` — hazard classification and regulatory reasoning (multiple
  choice), scored deterministically with ``choice()``.
- ``process_safety_reasoning`` — failure-mode reasoning (free response), scored with
  ``model_graded_qa()`` against a hand-authored rubric.

The tasks are imported here so the ``inspect_ai`` entry point (see ``pyproject.toml``)
registers them for discovery, e.g. ``inspect eval process_safety/process_safety_mcq``.
"""

from .task import process_safety_mcq, process_safety_reasoning

__all__: list[str] = ["process_safety_mcq", "process_safety_reasoning"]
