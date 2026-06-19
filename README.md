# process-safety-evals

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

The eval exposes two task variants over a single hand-authored dataset:

- **`process_safety_mcq`** — hazard classification and regulatory reasoning (multiple
  choice), scored deterministically with `choice()`.
- **`process_safety_reasoning`** — failure-mode reasoning (free response), scored with
  `model_graded_qa()` against a hand-authored rubric, using a separate grader model role
  so the model under test never grades its own answers.

Results break down per regulatory category (`grouped(accuracy(), "category")`) rather than
collapsing to a single headline number, and the model under test runs at `temperature=0`
for reproducibility.

## Why hand-authored

The dataset is written from domain expertise rather than scraped, which keeps it
contamination-resistant: items are unlikely to appear in any model's training data. Every
item records the regulation or standard it derives from in its `source` field.

## Project status

| Component | Status |
| --- | --- |
| Packaging, tooling (ruff, mypy, pytest), pinned dependencies | Done |
| Typed dataset loader (`record_to_sample`, `metadata_as` contract) | Done |
| Hand-authored dataset (`process_safety.jsonl`, 25 mcq + 12 reasoning) | Done |
| Task definitions, solvers, scorers | Planned |
| End-to-end tests (`mockllm/model`) and CI | Planned |
| Results table for a frontier model | Planned |

## Development

Requires [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev          # create the virtualenv and install runtime + dev deps
cp .env.example .env         # then add your ANTHROPIC_API_KEY
```

Quality gates:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

## License

MIT — see [LICENSE](LICENSE).
