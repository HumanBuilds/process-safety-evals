# Local open-weights serving

Serves a small open-weights model locally so both eval variants can be run against it and
compared with the frontier API baseline. vLLM runs inside a container; Inspect runs on the
host and attaches over HTTP through its `vllm/` provider. See [`compose.yaml`](compose.yaml).

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

- **Weight download dominates first boot.** The ~6 GB of model weights download over an
  unauthenticated Hugging Face connection (~1.7 MB/s here; vLLM warns to set `HF_TOKEN` for
  higher limits). The `hf-cache` named volume persists the weights, so subsequent boots skip
  the download. Production deployments pre-stage weights to a local registry or mirror rather
  than pulling per boot.
- **Inference latency (measured from the committed logs).** vLLM batches Inspect's concurrent
  requests, keeping per-sample latency low despite CPU-only inference:

  | Variant | Samples | Wall time | Per-sample | Model output tokens |
  | --- | --- | --- | --- | --- |
  | MCQ | 25 | 9 s | 0.4 s | 125 |
  | Reasoning | 36 (12 × 3 epochs) | 157 s | 4.4 s | 13,550 (~86 tok/s aggregate) |

  Reasoning wall time also includes the frontier grader's API round-trips, which overlap
  generation.
- **CPU backend; the iGPU is unused.** Docker Desktop does not pass the AMD Radeon 8060S
  through to the container, so inference is CPU-only. GPU acceleration on this APU would
  require a ROCm vLLM build under WSL. The serving interface — OpenAI-compatible endpoint,
  `--max-model-len`, KV-cache sizing, request batching — is backend-independent.
- **Host dependency.** Pointing Inspect at any OpenAI-compatible server requires the `openai`
  client, since the `vllm/` provider subclasses Inspect's `OpenAICompatibleAPI`.
- **Benign warnings.** `get_mempolicy / numa_*: Operation not permitted` arise from NUMA
  binding being disallowed inside the container and do not affect results.

## CI

CI runs against `mockllm/model` only — offline, deterministic, no weights. The local-model
run is a manual step: it requires a multi-GB image, a multi-GB model download, and minutes of
CPU inference, none of which belong on every push.
