# Local open-weights serving

Serves a small open-weights model locally so both eval variants can run against it and be
compared with the frontier API baseline. vLLM runs inside a container; Inspect runs on the host
and attaches over HTTP through its `vllm/` provider. See [`compose.yaml`](compose.yaml).

## Quickstart

```bash
# Start the server (first boot downloads the model into a cached volume).
docker compose -f serving/compose.yaml up

# In another shell, run either variant against it. The model under test is set on the CLI;
# the reasoning grader stays the frontier model configured in .env.
VLLM_BASE_URL=http://localhost:8000/v1 \
  uv run inspect eval src/process_safety/task.py@process_safety_mcq \
    --model vllm/Qwen/Qwen2.5-3B-Instruct --log-dir logs

VLLM_BASE_URL=http://localhost:8000/v1 \
  uv run inspect eval src/process_safety/task.py@process_safety_reasoning \
    --model vllm/Qwen/Qwen2.5-3B-Instruct --epochs 3 --log-dir logs

# Stop it.
docker compose -f serving/compose.yaml down
```

With `VLLM_BASE_URL` set, Inspect's `vllm/` provider connects to the running server rather
than importing vLLM in-process. The host therefore needs the `openai` client (a pinned
project dependency) but not vLLM itself. The model is overridable:
`VLLM_MODEL=Qwen/Qwen2.5-7B-Instruct docker compose -f serving/compose.yaml up`.

### Tool calling (agentic variant)

The [`process_safety_agentic`](../README.md#sandboxed-agentic-variant) variant also needs the
server to support OpenAI-style tool calling, which `compose.yaml` enables with
`--enable-auto-tool-choice --tool-call-parser hermes` (the tool-call format for Qwen2.5).
Without those flags vLLM returns `400 "auto" tool choice requires ...` and the agent loop can't
run. Serving a model for generation and serving it for tool use are separate capabilities, and
for a small model the second is more fragile (see the stop-sequence note below). Run it against
the running server:

```bash
VLLM_BASE_URL=http://localhost:8000/v1 \
  uv run inspect eval src/process_safety/task.py@process_safety_agentic \
    --model vllm/Qwen/Qwen2.5-3B-Instruct \
    --model-role grader=anthropic/claude-sonnet-4-6 \
    --stop-seqs "<|im_start|>" --log-dir logs
```

The `--stop-seqs "<|im_start|>"` flag is needed for this model. Under the full agentic prompt,
Qwen2.5-3B tends to run past its tool call, emitting extra `<tool_call>` blocks and a stray
`<|im_start|>` turn-delimiter in one completion — malformed output the hermes parser can't
extract, so the tool calls are dropped (returned as plain text) and never execute. Stopping
generation at `<|im_start|>` leaves a single clean tool call the parser can read. The frontier
model doesn't need it. This is a tool-call robustness issue, separate from model capability;
only with it fixed does the run reflect what the model can actually do (it then issues tool
calls but still fails the task — see the
[frontier-vs-local comparison](../README.md#what-the-runs-showed-frontier-vs-local)).

The agentic sandbox (`sandbox/compose.yaml`) is a separate container from this serving one;
Inspect reaches vLLM from the host, so the sandbox's `network_mode: none` doesn't block
inference.

## Reproducibility

The committed comparison numbers were produced with:

| Parameter | Value |
| --- | --- |
| Image | `vllm/vllm-openai-cpu` @ `sha256:6240a6bba604e607300e47490e3477211f968bdf125211bb877d19a70b8fe844` (7.38 GB) |
| vLLM version | `0.23.0` (bundled in the image) |
| Model | `Qwen/Qwen2.5-3B-Instruct` (Apache-2.0) |
| Model revision | `aa8e72537993ba99e69dfaafa59ed015b17504d1` |
| Compute dtype | `bfloat16`, no quantisation |
| Backend | CPU (`device_config=cpu`, `seed=0`) |
| `--max-model-len` | `8192` |
| `VLLM_CPU_KVCACHE_SPACE` | `8` GiB |
| Temperature | `0` (set by Inspect per request) |
| Host | AMD Ryzen AI Max+ (Strix Halo), 32 logical CPUs / 64 GiB to the Docker engine |

Refresh the image digest after a re-pull with
`docker inspect --format '{{index .RepoDigests 0}}' vllm/vllm-openai-cpu:latest-x86_64`.

## Operational characteristics

- First boot is dominated by the weight download. The ~6 GB of model weights download over an
  unauthenticated Hugging Face connection (~1.7 MB/s here; vLLM warns to set `HF_TOKEN` for
  higher limits). The `hf-cache` named volume persists them, so later boots skip the download.
  A production deployment would pre-stage weights to a local registry or mirror rather than
  pulling per boot.
- Inference latency, measured from the committed logs. vLLM batches Inspect's concurrent
  requests, keeping per-sample latency low despite CPU-only inference:

  | Variant | Samples | Wall time | Per-sample | Model output tokens |
  | --- | --- | --- | --- | --- |
  | MCQ | 25 | 9 s | 0.4 s | 125 |
  | Reasoning | 36 (12 × 3 epochs) | 157 s | 4.4 s | 13,550 (~86 tok/s aggregate) |

  Reasoning wall time also includes the frontier grader's API round-trips, which overlap
  generation.
- CPU backend; the iGPU is unused. Docker Desktop doesn't pass the AMD Radeon 8060S through to
  the container, so inference is CPU-only. GPU acceleration on this APU would need a ROCm vLLM
  build under WSL. The serving interface — OpenAI-compatible endpoint, `--max-model-len`,
  KV-cache sizing, request batching — is backend-independent.
- Host dependency. Pointing Inspect at any OpenAI-compatible server needs the `openai` client,
  since the `vllm/` provider subclasses Inspect's `OpenAICompatibleAPI`.
- Benign warnings. `get_mempolicy / numa_*: Operation not permitted` come from NUMA binding
  being disallowed inside the container and don't affect results.

## CI

CI runs against `mockllm/model` only — offline, deterministic, no weights. The local-model
run is a manual step: it requires a multi-GB image, a multi-GB model download, and minutes of
CPU inference, none of which belong on every push.
