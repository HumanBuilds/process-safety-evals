# process-safety-evals

[![CI](https://github.com/HumanBuilds/process-safety-evals/actions/workflows/ci.yml/badge.svg)](https://github.com/HumanBuilds/process-safety-evals/actions/workflows/ci.yml)

An [Inspect](https://inspect.aisi.org.uk/) eval that tests how a model reasons about
process-safety hazards and UK safety regulation: hazard classification, control selection
under the hierarchy of control, and applying DSEAR, COSHH, and CLP-GHS.

## Scope

Every item tests hazard identification, control selection, or regulatory application. None
asks how to cause harm or synthesise anything hazardous. The eval rewards recognising and
mitigating risk, not creating it.

## The two variants

Both run over one dataset (`src/process_safety/data/process_safety.jsonl`):

- `process_safety_mcq` — multiple-choice hazard classification and regulatory reasoning,
  scored with `choice()`.
- `process_safety_reasoning` — free-response failure-mode reasoning, scored with
  `model_graded_qa()` against a per-item rubric.

A third variant, `process_safety_agentic`, runs the same kind of question inside a sandbox
over its own scenario dataset — see [Sandboxed agentic variant](#sandboxed-agentic-variant).

### Why it's built this way

- MCQ and model-graded reasoning measure different things. MCQ covers the knowledge with one
  right answer and needs no judge model. Free response covers what an answer key can't grade:
  whether the model picks out the principal hazard and justifies the right safeguard.
- The reasoning scorer grades via `model_role="grader"`, bound at run time to a model other
  than the one under test, so a model never grades itself. Each item's rubric rides along as
  the sample `target`, which is what `model_graded_qa()` reads, so no extra wiring is needed.
- Both tasks report per category — `grouped(accuracy(), "category")` and
  `grouped(stderr(), "category")` — so a weak category shows up instead of averaging away
  into one headline number.
- MCQ items are authored with the correct option first, so the loader shuffles each item's
  choices before scoring (fixed seed for reproducibility). Without that, always picking "A"
  would score 100%.
- The dataset is generated, not scraped. An agent researched each item against primary sources,
  then two models from different providers reviewed it adversarially, followed by a manual pass
  over the flagged items. Each item's `source` field cites the regulation or standard it comes
  from (full citations in [`SOURCES.md`](src/process_safety/data/SOURCES.md)). Most of the
  underlying regulation is long-standing, so it's likely present in training data — this isn't a
  contamination-resistant set (see [Limitations](#limitations--future-work)).

## Usage

Requires [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev          # create the virtualenv and install runtime + dev deps
cp .env.example .env         # then add your ANTHROPIC_API_KEY
```

`.env.example` also sets the model under test and the grader model; Inspect reads `.env`
automatically. Run each variant with:

```bash
# Multiple choice (deterministic; no grader needed)
uv run inspect eval src/process_safety/task.py@process_safety_mcq

# Free-response reasoning (model-graded; grader bound to a separate model)
uv run inspect eval src/process_safety/task.py@process_safety_reasoning --epochs 3

# Inspect the transcripts and grader reasoning in the local log viewer
uv run inspect view
```

Models can be overridden on the command line, e.g.
`--model anthropic/claude-sonnet-4-6 --model-role grader=anthropic/claude-opus-4-8`.

To run the same variants against a locally-served open-weights model instead of the API,
see [`serving/`](serving/README.md), which starts a vLLM container and points Inspect at it.

## Results (frontier baseline)

Model under test: `anthropic/claude-haiku-4-5` at `temperature=0`. Reasoning grader:
`anthropic/claude-sonnet-4-6` (a separate, stronger model). Run date: 2026-06-19,
`inspect-ai==0.3.240`. MCQ: 1 epoch (the deterministic scorer is stable at `temperature=0`).
Reasoning: 3 epochs (see [Methodology](#methodology)).

| Category | MCQ accuracy (±stderr) | Reasoning accuracy (±stderr) |
| --- | --- | --- |
| `clp-classification` | 1.000 (±0.000) | 0.750 (±0.250) |
| `dsear` | 0.750 (±0.250) | 1.000 (±0.000) |
| `coshh` | 0.750 (±0.250) | 0.750 (±0.250) |
| `hierarchy-of-control` | 1.000 (±0.000) | 0.833 (±0.167) |
| `risk-assessment-duties` | 1.000 (±0.000) | 0.583 (±0.083) |
| `process-safety-method` | 1.000 (±0.000) | 0.917 (±0.083) |
| **Overall** | **0.920 (±0.055)** | **0.806 (±0.064)** |

MCQ: n = 25 items (5 in `clp-classification`, 4 in each other category), answer positions
shuffled. Reasoning: n = 12 items (2 per category) × 3 epochs = 36 graded trials. Accuracy
counts partial-credit grades as 0.5. This is one small-model run on a small dataset, so treat
it as illustrative rather than a leaderboard entry. The MCQ score holds with choices shuffled,
so it reflects reasoning, not answer position.

The runs behind this table are committed for provenance. Open them with `inspect view` to
replay every transcript and the grader's reasoning:
[MCQ log](logs/2026-06-19T15-03-49-00-00_process-safety-mcq_UgYJZE8pvSg95HXUptfcZK.eval) ·
[reasoning log (3 epochs)](logs/2026-06-19T14-26-54-00-00_process-safety-reasoning_6guq3rVzym4rU3GwpkF7or.eval).

## Local open-weights comparison

Both variants also run, unchanged, against a locally-served open-weights model,
`Qwen/Qwen2.5-3B-Instruct` (Apache-2.0), served with vLLM behind an OpenAI-compatible
endpoint — see [`serving/`](serving/README.md) for the container, reproducibility pins, and
operational notes. Inspect attaches over HTTP through its `vllm/` provider, so only the model
under test changes. For the reasoning variant the grader stays on the frontier
`claude-sonnet-4-6`, so any gap is the model under test, not the judge.

The tables below are regenerated from the committed logs by
[`scripts/compare_runs.py`](scripts/compare_runs.py), not transcribed by hand.

**MCQ** — deterministic `choice()`, 1 epoch:

| Category | Frontier — Haiku | Local — Qwen2.5-3B |
| --- | --- | --- |
| `clp-classification` | 1.000 (±0.000) | 0.200 (±0.200) |
| `dsear` | 0.750 (±0.250) | 0.750 (±0.250) |
| `coshh` | 0.750 (±0.250) | 0.750 (±0.250) |
| `hierarchy-of-control` | 1.000 (±0.000) | 1.000 (±0.000) |
| `risk-assessment-duties` | 1.000 (±0.000) | 0.750 (±0.250) |
| `process-safety-method` | 1.000 (±0.000) | 1.000 (±0.000) |
| **Overall** | **0.920 (±0.055)** | **0.720 (±0.092)** |

**Reasoning** — model-graded by `claude-sonnet-4-6`, 3 epochs:

| Category | Frontier — Haiku | Local — Qwen2.5-3B |
| --- | --- | --- |
| `clp-classification` | 0.750 (±0.250) | 0.583 (±0.417) |
| `dsear` | 1.000 (±0.000) | 0.500 (±0.000) |
| `coshh` | 0.750 (±0.250) | 0.500 (±0.000) |
| `hierarchy-of-control` | 0.833 (±0.167) | 0.583 (±0.083) |
| `risk-assessment-duties` | 0.583 (±0.083) | 0.500 (±0.000) |
| `process-safety-method` | 0.917 (±0.083) | 0.500 (±0.000) |
| **Overall** | **0.806 (±0.064)** | **0.528 (±0.054)** |

Two things stand out:

- On MCQ, the gap is concentrated in one category. Qwen matches the frontier model on four of
  six categories and collapses on `clp-classification` (1.000 → 0.200). Assigning GHS hazard
  classes and categories is precise recall the small model lacks; it keeps pace on the more
  reasoning-shaped categories. Most of the 20-point overall gap is that one category.
- On reasoning, the local model hits a partial-credit ceiling. Most local cells sit at exactly
  0.500 (±0.000): across all three epochs the grader awarded partial credit, because the model
  identifies the hazard domain but misses the governing regulation or the specific safeguard.
  The zero standard error marks this as a capability ceiling, not grader noise.

Grader sensitivity is why the grader stays on the frontier model. Re-grading the same
local-model answers with the local 3B in the grader seat raises the reasoning score from 0.528
to 0.750: the weaker judge often can't tell when an answer omits the governing regulation, so
it grades more leniently ([log](logs/2026-06-20T16-39-55-00-00_process-safety-reasoning_4yzXsnYMu224F2ZxcHPq2Z.eval),
1 epoch). Degrading both seats together would hide the capability gap, so the headline
comparison swaps only the model under test.

The local runs are committed for provenance (replay with `inspect view`):
[MCQ](logs/2026-06-20T15-57-32-00-00_process-safety-mcq_C7drrLJBwkCX9WgruuPFgF.eval) ·
[reasoning, frontier grader](logs/2026-06-20T16-06-46-00-00_process-safety-reasoning_fBdBNn3T3FtQcbfUAki3ng.eval) ·
[reasoning, local grader](logs/2026-06-20T16-39-55-00-00_process-safety-reasoning_4yzXsnYMu224F2ZxcHPq2Z.eval).

## Sandboxed agentic variant

`process_safety_agentic` turns the single-turn Q&A into an agentic task. The model runs in a
Docker sandbox with `bash` and `python` tools and has to investigate files to answer a
process-safety question. Each scenario ships a mix of relevant files and noise — a worker's
exposure log and a workplace exposure-limit reference, plus an unrelated substance's data file
and the site canteen menu. The model finds what matters, computes the answer, and submits it;
the submission is graded against the scenario's rubric with the same `model_graded_qa()` scorer
as the reasoning variant. It runs over its own dataset
(`src/process_safety/data/agentic.jsonl`, with each scenario's files under `data/agentic/<id>/`).

Inspect issues every command from outside the sandbox, so inference is separated from
execution and the container bounds everything the model can do.

### Sandbox design

Defined in [`sandbox/compose.yaml`](sandbox/compose.yaml):

- `network_mode: none` — no internet. The model can only use the files Inspect copies into
  `/data`; it can't fetch the real regulation, phone home, or be influenced by anything off-box.
- `read_only` root + writable tmpfs — the image's binaries and libraries are immutable; only
  `/data` (scenario files), `/tmp` (scratch), and `/root` (a writable HOME) are writable, so
  the model can't tamper with the toolchain.
- `cpus` / `mem_limit` — a runaway computation can't starve the host.
- stdlib only — no `pip` at runtime (no network), so scenarios are authored to need only the
  Python standard library.

### Running it

```bash
# Requires Docker. The first run pulls the small python:3.12-slim image.
uv run inspect eval src/process_safety/task.py@process_safety_agentic \
  --model anthropic/claude-haiku-4-5 \
  --model-role grader=anthropic/claude-sonnet-4-6
```

CI does not run this variant (it needs Docker). The offline test suite exercises the same
agent loop and scorer on Inspect's built-in `local` sandbox instead, so CI stays green without
Docker.

### What the runs showed: frontier vs local

On the worked scenario `agt-001` (a workplace-exposure-limit compliance check), the frontier
and local models diverged completely — a much sharper gap than the graded one in the
[MCQ/reasoning comparison](#local-open-weights-comparison). Grader held at `claude-sonnet-4-6`
for both.

| Model under test | Score | Behaviour (with tool calls executing) |
| --- | --- | --- |
| `claude-haiku-4-5` (frontier) | **1.000** | `ls`'d `/data`, `cat`'d the real files, hit the missing-`pandas` error once and fell back to the standard library, computed the 8-hour TWA (48.1 mg/m³ — time-weighting correctly and including the zero-exposure break), concluded exposure was below the 50 mg/m³ limit, cited COSHH/EH40. |
| `Qwen2.5-3B-Instruct` (local) | **0.000** | Never inspected the directory. Repeatedly tried to `read_csv` filenames that don't exist (`exposure_data.csv`, `air_concentration_data.csv`); retried `import pandas` eight times despite a clear `ModuleNotFoundError`; read no real file; fabricated the answer (0.8 against a made-up 0.5 limit, wrong regime DSEAR). |

Logs (replay with `inspect view`):
[haiku](logs/2026-06-20T17-28-34-00-00_process-safety-agentic_4qJBjhzRbeEFHHzYE8ZCj8.eval) ·
[Qwen2.5-3B (tool calls fixed)](logs/2026-06-20T18-24-43-00-00_process-safety-agentic_HJ63xXUBLNNzQqEueBzGKB.eval).

A serving issue had to be ruled out first. In the initial local run, Qwen's tool calls weren't
executing at all: under the full agentic prompt the 3B model emitted malformed output — several
`<tool_call>` blocks plus a stray `<|im_start|>` turn-delimiter in one completion — which
vLLM's hermes parser couldn't extract, so Inspect saw plain text and ran nothing
([log](logs/2026-06-20T17-42-15-00-00_process-safety-agentic_jewKtDKpqPmi4WCLmT26sC.eval)).
Direct endpoint tests showed the parser works on clean output, so the cause was the small model
running past its tool call. Adding `--stop-seqs "<|im_start|>"` halts generation at the fake
turn boundary, leaving a clean tool call the parser can extract; after that the tool calls
executed normally. The run was re-done with tools actually executing before drawing any
conclusion, to keep this serving-robustness issue separate from a capability claim.

With tools executing, the gap is a capability one. The small model can emit tool calls — once
parsing was fixed it issued eight of them — but it can't run the loop. It never inspects the
environment (assumes filenames instead of `ls`/`cat`), doesn't adapt to feedback (retries
`pandas` after repeated `ModuleNotFoundError`s), and fabricates an answer rather than admitting
it has no data. The scenario is built so guessing fails: a naive mean of the sampled readings
(55 mg/m³) reads as exceeded, and only the correct time-weighted average (48.1) is below the
limit — but the local model never got far enough to attempt the calculation. The single-turn
gap (0.920 → 0.720) shows the small model knows less; the agentic variant shows it can't be
trusted to act on what it knows.

Operational notes:

- Serving for tool use is a separate, more fragile capability. The MCQ/reasoning variants run
  against the vLLM container as-is, but the agentic variant needs it started with
  `--enable-auto-tool-choice --tool-call-parser hermes` (Qwen2.5's tool-call format; without
  them vLLM returns a 400 on `tool_choice="auto"`), and the local run also needs
  `--stop-seqs "<|im_start|>"` to stop the 3B model running past its tool calls into malformed,
  unparseable output. The frontier model needs neither. See [`serving/`](serving/README.md).
- No network forces dependency choices up front. Both models reached for `pandas` (absent in the
  minimal image); haiku fell back to the standard library in one turn, the 3B model never did.
- The eval machinery carried over unchanged. The same rubric-as-`target`, separate grader role,
  and per-category metrics work for the agentic variant — only the solver and sandbox are new.

## Methodology

- 3 epochs for the reasoning variant. The MCQ variant uses a deterministic `choice()` scorer at
  `temperature=0` and returns the same answer every run, so extra epochs add nothing. The
  model-graded variant has two stochastic parts — residual model-under-test nondeterminism and
  the grader's own variance — so it runs for 3 epochs and the per-sample grades are averaged
  (Inspect's default epoch reducer) before metrics. This tightens the standard error on a small
  (n = 12) set and, more usefully, surfaces which rubric clauses are ambiguous.
- Borderline items surfaced by epochs. Three reasoning items (`rsn-008`, `rsn-010`, `rsn-011`)
  flipped between partial and full credit across epochs. In each case the grader reached two
  defensible verdicts on an answer sitting exactly on a criterion's threshold (e.g. whether
  naming *Edwards v NCB* is required, or what counts as "design detail"). These are
  rubric-tightening opportunities, tracked as future work, not grader noise.

## Limitations & future work

- Small N. ~37 items is enough to be non-trivial and give a per-category signal, but not enough
  for tight confidence intervals. The intended signal is item quality and per-category reasoning,
  not scale.
- Likely contamination. The items are grounded in long-standing UK regulation, so much of the
  underlying material is probably already in training data; treat single-turn scores as a
  reasoning check, not evidence the model hasn't seen the facts. The agentic variant is harder
  to answer from memory, since it requires reading the supplied files and computing. See
  [grader drift & contamination resistance](#grader-drift--contamination-resistance) for what
  would make a future version more contamination-resistant.
- The agentic variant is one worked scenario. `agt-001` exercises the full sandbox pipeline
  end-to-end and shows the signal-vs-noise and compute design, but it's a single item. The next
  step is several scenarios across categories, each with its own file set and an optional
  intermediate "did it open the right file" check.
- Single grader. One grader model is a single point of judgement. The borderline items above
  would benefit from rubric tightening and, at larger scale, a multi-grader or human-adjudicated
  panel. The [grader-sensitivity result](#local-open-weights-comparison) shows how much judge
  capability alone moves the score.
- Registration. The eval follows the [`inspect_evals`](https://github.com/UKGovernmentBEIS/inspect_evals)
  contributing conventions (README template, `mockllm/model` tests, pinned deps, justified
  epochs, per-category results) so it can be registered there as an external eval.

### Grader drift & contamination resistance

Two failure modes threaten a model-graded eval like this one over time. Both are out of scope
here, but worth stating:

- Grader drift — the grader's behaviour changes (a provider updates the model behind an alias,
  or the grader is upgraded), so the same answer scores differently across dates. Mitigations:
  pin the grader to an immutable dated snapshot rather than a floating alias; calibrate it
  periodically against a human-labelled gold subset; re-grade stored transcripts when the grader
  changes so historical runs stay comparable; and tighten rubric thresholds (see the borderline
  items above) to leave less room for the judge to waver.
- Contamination — models can recall answers instead of reasoning. This already applies here:
  the items rest on long-standing regulation that is likely in current training data, and
  publishing the set only widens that. A future version could push back on it by keeping a
  private hold-out split and watching for a public-vs-hold-out gap; embedding a canary string to
  detect leakage and let cooperating labs exclude the data; rotating and versioning items over
  time; using parametric item templates whose specifics vary per run; and leaning on multi-step
  reasoning items, which are harder to memorise than fact lookups. The agentic variant points the
  same way — answering it needs the supplied files, not recall.

## Provenance & safety

Every `source` field traces to a primary source (HSE or legislation.gov.uk), confirmed current
as of June 2026; full citations and caveats are in
[`SOURCES.md`](src/process_safety/data/SOURCES.md). The dataset was generated by agent research
against those sources, then adversarially reviewed by two models from different providers and
checked by hand over the flagged items.

This is a defensive eval: it measures hazard recognition, control selection, and regulatory
application only. No item gives uplift toward causing harm or synthesising hazardous materials.

## Development

Quality gates (all run in CI on push and PR):

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest          # end-to-end tests run offline against mockllm/model
```

## License

MIT — see [LICENSE](LICENSE).
