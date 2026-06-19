# process-safety-evals

[![CI](https://github.com/HumanBuilds/process-safety-evals/actions/workflows/ci.yml/badge.svg)](https://github.com/HumanBuilds/process-safety-evals/actions/workflows/ci.yml)

An [Inspect](https://inspect.aisi.org.uk/) evaluation measuring whether a language model
**reasons correctly about process-safety hazards and UK safety regulation** — hazard
classification, control selection under the hierarchy of control, and the application of
DSEAR, COSHH, and CLP-GHS.

## Defensive by design

Every item measures correct **hazard identification**, **control selection**, and
**regulatory application**. **No item probes how to cause harm or synthesise anything
hazardous.** The eval is deliberately positioned on the safe side of the dual-use line:
it rewards recognising and mitigating risk, never creating it.

## The two variants

Both variants run over a single hand-authored dataset (`src/process_safety/data/process_safety.jsonl`):

- **`process_safety_mcq`** — hazard classification and regulatory reasoning (multiple
  choice), scored deterministically with `choice()`.
- **`process_safety_reasoning`** — failure-mode reasoning (free response), scored with
  `model_graded_qa()` against a hand-authored, per-item rubric.

### Design choices

- **Deterministic *and* model-graded.** MCQ pins down knowledge that has one right answer
  and scores it without a judge model. Free-response reasoning captures the part that
  matters most in practice — *can the model identify the principal hazard and justify the
  right safeguard?* — which no fixed answer key can grade.
- **A separate grader role.** The reasoning scorer grades via `model_role="grader"`, bound
  at run time to a *different* model than the one under test, so the model never grades its
  own answers. Each item's rubric is carried as the sample `target`, so it flows into the
  grader prompt automatically.
- **Per-category reporting.** Both tasks attach `grouped(accuracy(), "category")` and
  `grouped(stderr(), "category")`, so results break down per regulatory category rather than
  collapsing to a single headline number that could hide a category-level weakness.
- **Shuffled answer positions.** MCQ items are authored with the correct option first, so the
  loader shuffles each item's choices (fixed seed, for reproducibility) before scoring. Without
  this, a model that simply always picked "A" would score 100%; shuffling ensures the MCQ
  number measures reasoning rather than answer-position bias.
- **Hand-authored, for contamination resistance.** The dataset is written from domain
  expertise rather than scraped, so items are unlikely to appear in any model's training
  data. Every item records the regulation or standard it derives from in its `source` field
  (full citations in [`SOURCES.md`](src/process_safety/data/SOURCES.md)).

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

## Results

Model under test: **`anthropic/claude-haiku-4-5`** at `temperature=0`. Reasoning grader:
**`anthropic/claude-sonnet-4-6`** (a separate, stronger model). Run date: **2026-06-19**,
`inspect-ai==0.3.240`. MCQ: 1 epoch (the deterministic scorer is stable at `temperature=0`).
Reasoning: 3 epochs (see *Methodology* below).

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
counts partial-credit grades as 0.5. These numbers are illustrative of the eval, not a
leaderboard claim — a single small-model run on a small dataset. The MCQ score is unchanged
with choices shuffled, indicating it reflects reasoning rather than answer-position bias.

The runs behind this table are committed for provenance — open them with `inspect view` to
replay every transcript and the grader's reasoning:
[MCQ log](logs/2026-06-19T15-03-49-00-00_process-safety-mcq_UgYJZE8pvSg95HXUptfcZK.eval) ·
[reasoning log (3 epochs)](logs/2026-06-19T14-26-54-00-00_process-safety-reasoning_6guq3rVzym4rU3GwpkF7or.eval).

## Methodology

- **Why 3 epochs for the reasoning variant.** With a deterministic `choice()` scorer at
  `temperature=0`, the MCQ variant returns the same answer every run, so additional epochs
  add nothing. The model-graded variant has two stochastic components — residual
  model-under-test nondeterminism and the grader model's own variance — so it is run for 3
  epochs and the per-sample grades are averaged (Inspect's default epoch reducer) before
  metrics are computed. This both tightens the standard error on a small (n = 12) set and,
  more usefully, exposes *which rubric clauses are ambiguous*.
- **Borderline items surfaced by epochs.** Three reasoning items (`rsn-008`, `rsn-010`,
  `rsn-011`) flipped between partial and full credit across epochs. In every case the grader
  reached *both* defensible verdicts on a candidate answer sitting exactly on a criterion's
  threshold (e.g. whether naming *Edwards v NCB* is required, or what counts as "design
  detail"). These are rubric-tightening opportunities, not grader noise, and are tracked as
  future work.

## Limitations & future work

- **Small N.** ~37 items is enough to be non-trivial and to give a per-category signal, but
  not enough for tight confidence intervals. Quality and contamination resistance are the
  intended signal, not scale.
- **Single grader.** One grader model is a single point of judgement. Borderline items
  (above) would benefit from rubric tightening and, at larger scale, a multi-grader or
  human-adjudicated panel.
- **Phase 3 (planned).** Compare a local open-weights model against the frontier baseline.
- **Phase 4 (planned).** Register the eval in [`inspect_evals`](https://github.com/UKGovernmentBEIS/inspect_evals).

### Grader drift & contamination resistance

Two failure modes threaten a hand-authored, model-graded eval over time, and both are
out of scope here but worth stating:

- **Grader drift** — the grader model's behaviour changes (a provider updates the model
  behind an alias, or the grader is upgraded), so the same answer scores differently across
  dates. Mitigations: pin the grader to an immutable dated snapshot rather than a floating
  alias; calibrate it periodically against a human-labelled gold subset; re-grade stored
  transcripts when the grader changes so historical runs stay comparable; and tighten rubric
  thresholds (see the borderline items above) to leave less room for a judge to waver.
- **Contamination** — once published, the dataset can be scraped into future training data,
  after which models recall answers instead of reasoning. Mitigations: keep a private
  hold-out split and watch for a public-vs-hold-out gap; embed a canary string to detect
  leakage and let cooperating labs exclude the data; rotate and version items over time;
  prefer parametric item templates whose specifics vary per run; and lean on multi-step
  reasoning items, which are harder to memorise than fact lookups. Dated, primary-sourced
  provenance also lets a model with an earlier training cutoff be ruled out as contaminated.

## Provenance & safety

Every `source` field traces to a primary source (HSE or legislation.gov.uk), confirmed
current as of June 2026; full citations and caveats are in
[`SOURCES.md`](src/process_safety/data/SOURCES.md). The dataset is entirely hand-authored.

This is a **defensive** eval: it measures correct hazard recognition, control selection, and
regulatory application only. No item provides uplift toward causing harm or synthesising
hazardous materials.

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
