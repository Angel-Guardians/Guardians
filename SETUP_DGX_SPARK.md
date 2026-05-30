# Running Guardian on the NVIDIA DGX Spark

Goal: keep developing on your laptop while the **LLM runs on the Spark**. The app
only ever talks to an OpenAI-compatible URL, so this is purely an `.env` switch.

## 1. SSH in and check the box has internet

```bash
ssh <user>@<spark-host>
curl -fsSL https://ollama.com >/dev/null && echo "internet OK" || echo "NO internet"
nvidia-smi          # confirm the GPU is visible
```

## 2. Install + start Ollama on the Spark

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &                       # serves an OpenAI-compatible API on :11434
```

## 3. Pull a model (Nemotron, or any tag you have)

```bash
ollama pull nemotron                 # then confirm the exact name:
ollama list                          # use the NAME column as LLM_MODEL
ollama run nemotron "say hello"      # smoke test the model itself
```

## 4. Tunnel the Spark's Ollama to your laptop

On your **laptop** (so `localhost:11434` points at the Spark):

```bash
ssh -N -L 11434:localhost:11434 <user>@<spark-host>
```

## 5. Point Guardian at it

In `.env` on your laptop:

```ini
LLM_PROVIDER=local
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=nemotron            # exact tag from `ollama list`
LLM_API_KEY=not-needed
LLM_SUPPORTS_TOOLS=true       # set false if the model's tool-calling is flaky
```

Restart `guardian-backend`. `GET /health` shows it's up; `scripts/try_live.py`
confirms the model is actually choosing tools. Nothing else changes.

### vLLM / NVIDIA NIM instead of Ollama
Serve on the Spark and set `LLM_BASE_URL=http://<spark-host>:8000/v1` and
`LLM_MODEL=<served-model-id>`. Same seam, higher throughput.

### Tips
- Tool-calling reliability varies by local model. If agents stop calling tools,
  set `LLM_SUPPORTS_TOOLS=false` and the agents degrade to plain spoken replies.
- Keep `LANGSMITH_TRACING=true` to compare cloud vs. Spark latency/quality per turn.
