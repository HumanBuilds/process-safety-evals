"""Task definitions for the process-safety eval.

Two ``@task`` variants share the one dataset (see :mod:`.dataset`):

- :func:`process_safety_mcq` — multiple-choice hazard classification and regulatory
  reasoning, scored with ``choice()``.
- :func:`process_safety_reasoning` — free-response failure-mode reasoning, scored with
  ``model_graded_qa()`` against each item's ``criterion``.

Three choices worth flagging (all covered in the README):

1. The rubric rides on ``target``. Each reasoning sample stores its rubric as the sample
   ``target`` (see :mod:`.dataset`); ``model_graded_qa`` reads the criterion from
   ``target.text``, so it reaches the grader prompt with no extra wiring.
2. Separate grader role. The reasoning scorer grades via ``model_role="grader"`` so a model
   never grades its own output. The grader is bound at run time, e.g.
   ``inspect eval ... --model-role grader=anthropic/claude-sonnet-4-6``.
3. Per-category reporting. Both tasks attach ``grouped(..., "category")`` metrics, which emit
   per-category scores alongside the overall aggregate, so a weak category isn't hidden by the
   headline number.

``temperature=0.0`` is set on the model under test for reproducibility; the grader is a
separate model, configured independently at run time.
"""

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig
from inspect_ai.scorer import accuracy, choice, grouped, model_graded_qa, stderr
from inspect_ai.solver import basic_agent, generate, multiple_choice, system_message
from inspect_ai.tool import bash, python

from process_safety.agentic import SANDBOX_COMPOSE, load_agentic
from process_safety.dataset import load

# Persona for the reasoning variant. Anchors the model in the UK regulatory frame the dataset
# is written against, without leaking any item-specific answer.
REASONING_SYSTEM_MESSAGE = (
    "You are a chartered UK process-safety engineer. Reason about chemical-process hazards "
    "and the governing UK safety regulation (DSEAR, COSHH, GB CLP, and the hierarchy of "
    "control). For each scenario, identify the principal hazard and justify the appropriate "
    "safeguard, citing the relevant regulation where it applies. Be precise and concise."
)

# Instructions handed to the grader by ``model_graded_qa``. The grading prompt also carries
# each item's ``criterion`` (via the sample target) and the model's answer; these instructions
# tell the grader how to apply that criterion and how to format its verdict. The grade pattern
# downstream expects a final line of the form ``GRADE: C`` / ``GRADE: P`` / ``GRADE: I``
# (C = correct, P = partially correct, I = incorrect), so the instructions require that exact
# format. They bias toward caution: a plausible-sounding answer that misidentifies the hazard
# or control is penalised rather than given the benefit of the doubt, which is the right
# default for a safety eval.
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


# Briefing handed to the agent in the sandboxed variant. How much this says about the /data
# directory and what counts as a good answer is the main design lever: it decides whether the
# task measures investigate-and-compute capability or just instruction-following. It does not
# name the relevant files or reveal the method (time-weighting, which substance, which limit),
# so a model has to investigate rather than follow a recipe.
AGENTIC_SYSTEM_MESSAGE = (
    "You are a chartered UK process-safety engineer. "
    "Reason about chemical-process hazards and the governing UK safety regulation "
    "(DSEAR, COSHH, GB CLP, and the hierarchy of control). "
    "Using the relevant files in /data, carefully reason and compute the answer to the "
    "question, making sure to provide all the necessary information in the required format. "
    "You have bash and python tools to read the files and run any calculation; the sandbox "
    "has no internet, so work only from the files provided. "
    "When you have your answer, call the submit() tool to report it. "
    "Be precise and concise."
)


@task
def process_safety_agentic() -> Task:
    """Sandboxed agentic variant: the model investigates files and computes the answer.

    Each sample ships a set of files into a Docker sandbox (some carrying the answer, some
    noise; see :mod:`.agentic`). The model gets ``bash`` and ``python`` tools that run inside
    the sandbox and has to read the files, run the calculation, and submit a final answer,
    which is graded against the scenario's criterion just as the reasoning variant is.
    ``basic_agent`` drives the tool-use loop and ends on ``submit()``; ``message_limit`` bounds
    a run so a stuck agent terminates rather than looping forever.

    The sandbox is the Docker spec in ``sandbox/compose.yaml`` (network-isolated, read-only
    root). Tests override it with the built-in ``local`` sandbox so CI needs no Docker.
    """
    return Task(
        dataset=load_agentic(),
        solver=basic_agent(
            init=system_message(AGENTIC_SYSTEM_MESSAGE),
            tools=[bash(timeout=60), python(timeout=60)],
            message_limit=20,
        ),
        scorer=model_graded_qa(
            instructions=GRADER_INSTRUCTIONS,
            partial_credit=True,
            model_role="grader",
        ),
        metrics=[grouped(accuracy(), "category"), grouped(stderr(), "category")],
        sandbox=("docker", str(SANDBOX_COMPOSE)),
        config=GenerateConfig(temperature=0.0),
    )
