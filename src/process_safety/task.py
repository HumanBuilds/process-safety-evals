"""Task definitions for the process-safety eval.

Two ``@task`` variants share the one hand-authored dataset (see :mod:`.dataset`):

- :func:`process_safety_mcq` — multiple-choice hazard classification and regulatory
  reasoning, scored deterministically with ``choice()``.
- :func:`process_safety_reasoning` — free-response failure-mode reasoning, scored with
  ``model_graded_qa()`` against each item's hand-authored ``criterion``.

Three methodological choices are deliberate and called out in the README:

1. *Criterion carried by ``target``.* Each reasoning sample's rubric is stored as its
   ``target`` (see :mod:`.dataset`); ``model_graded_qa`` reads the criterion from
   ``target.text``, so the rubric reaches the grader prompt without extra wiring.
2. *Separate grader role.* The reasoning scorer grades via ``model_role="grader"`` so the
   model under test never grades its own output. The grader model is bound at run time, e.g.
   ``inspect eval ... --model-role grader=anthropic/claude-sonnet-4-6``.
3. *Per-category reporting.* Both tasks attach ``grouped(..., "category")`` metrics, which
   emit per-category scores *and* an overall aggregate — so a single headline number never
   hides a category-level weakness.

``temperature=0.0`` is set on the model under test for reproducibility; the grader is a
separate model and is configured independently at run time.
"""

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig
from inspect_ai.scorer import accuracy, choice, grouped, model_graded_qa, stderr
from inspect_ai.solver import generate, multiple_choice, system_message

from process_safety.dataset import load

# Persona for the reasoning variant. Anchors the model in the UK regulatory frame the dataset
# is authored against, without leaking any item-specific answer.
REASONING_SYSTEM_MESSAGE = (
    "You are a chartered UK process-safety engineer. Reason about chemical-process hazards "
    "and the governing UK safety regulation (DSEAR, COSHH, GB CLP, and the hierarchy of "
    "control). For each scenario, identify the principal hazard and justify the appropriate "
    "safeguard, citing the relevant regulation where it applies. Be precise and concise."
)

# Instructions handed to the grader model by ``model_graded_qa``. The grading prompt also
# carries each item's ``criterion`` (via the sample target) and the model's answer; these
# instructions tell the grader *how* to apply that criterion and how to format its verdict.
# The grade pattern downstream expects a final line of the form ``GRADE: C`` / ``GRADE: P`` /
# ``GRADE: I`` (C = correct, P = partially correct, I = incorrect), so the instructions must
# require that exact format. The instructions deliberately bias toward caution: an answer
# that sounds plausible but misidentifies the hazard or control is penalised rather than
# given the benefit of the doubt, which matters for a safety eval.
GRADER_INSTRUCTIONS = (
    "Carefully read the model's answer and compare it against the provided grading criterion. "
    "Evaluate, with step-by-step reasoning, whether the answer fully meets, partially meets, or "
    "does not meet the criterion. Err on the side of caution when evaluating partial compliance. "
    "A plausible-sounding answer or partially correct answer that also makes an inaccurate claim "
    "should be penalized. Provide a brief justification for your evaluation. Finally, assign a "
    "grade in the format 'GRADE: C' for correct, 'GRADE: P' for partially correct, or 'GRADE: I' "
    "for incorrect."
)


@task
def process_safety_mcq() -> Task:
    """Multiple-choice hazard classification and regulatory reasoning (deterministic)."""
    return Task(
        dataset=load("mcq"),
        solver=multiple_choice(),
        scorer=choice(),
        metrics=[grouped(accuracy(), "category"), grouped(stderr(), "category")],
        config=GenerateConfig(temperature=0.0),
    )


@task
def process_safety_reasoning() -> Task:
    """Free-response failure-mode reasoning, model-graded against each item's criterion."""
    return Task(
        dataset=load("reasoning"),
        solver=[system_message(REASONING_SYSTEM_MESSAGE), generate()],
        scorer=model_graded_qa(
            instructions=GRADER_INSTRUCTIONS,
            partial_credit=True,
            model_role="grader",
        ),
        metrics=[grouped(accuracy(), "category"), grouped(stderr(), "category")],
        config=GenerateConfig(temperature=0.0),
    )
