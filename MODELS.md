# Models — what we run now, and the path to NVIDIA Nemotron

Short version: **the live conversational app uses one model behind one seam.**
Set it in `.env`; nothing in the code names a model. Everything below explains
what that model is today and what to switch it to for the DGX Spark / Nemotron
track.

---

## The one thing that matters

All model config lives in `backend/llm/config.py`, driven by `LLM_*` env vars.
The only file that imports `openai` is `backend/llm/openai_compatible.py`. Because
the endpoint is OpenAI-*compatible*, the same code talks to OpenAI cloud **and** a
local Ollama / NIM server — you change `.env`, not code.

| Env var            | Today (OpenAI)            | DGX Spark (Nemotron via Ollama) |
|--------------------|---------------------------|---------------------------------|
| `LLM_BASE_URL`     | `https://api.openai.com/v1` | `http://localhost:11434/v1`   |
| `LLM_MODEL`        | `gpt-4o-mini`             | `nemotron-3-nano:4b` (see below)|
| `LLM_API_KEY`      | `sk-...`                 | `not-needed`                    |
| `LLM_PROVIDER`     | `openai`                 | `local` (label only)            |
| `LLM_SUPPORTS_TOOLS` | `true`                 | `true` (verify per model)       |

That table **is** the migration. The rest of this doc is detail.

---

## What runs today

One model serves every role — the router and all six specialists call the same
`LLM_MODEL`. The default is **`gpt-4o-mini`** (OpenAI): cheap, fast, reliable
tool-calling, zero infra. Good enough to demo the whole graph end to end.

> Heads-up on a stale-looking file: `backend/config.py` still lists
> `llm_model_generalist = "llama3.1:8b..."`, `llm_model_clinical = "meditron:7b"`,
> `llm_model_classifier = "phi3.5:mini"`, and `whisper_model`. **These are not used
> by the conversational path.** They are leftovers from the original tiered design
> (a per-role model split + local STT) that the merged build does not wire up. The
> live path reads `backend/llm/config.py` only. Treat `backend/config.py`'s model
> fields as aspirational until/unless someone re-introduces per-role models.

---

## The Nemotron family (current, late-2025/2026)

NVIDIA's open **Nemotron 3** line is the natural target for the Spark track. All
are OpenAI-compatible through Ollama, so they drop into the seam above.

| Model | Size | Best as | Notes |
|-------|------|---------|-------|
| `nemotron-3-nano:4b` | 4B dense | **router / classifier / fast specialists** | Unified reasoning + non-reasoning; small enough to be snappy on the Spark. Best first move. |
| `nemotron-cascade-2` | 30B MoE (3B active) | mid-tier specialists | Good quality/speed balance for the conversational agents. |
| `nemotron-3-super` | 120B MoE (12B active) | **headline specialist quality** | The Spark's 128 GB unified memory can hold this; 12B active keeps it usable. Stretch goal / "wow" demo model. |
| `nemotron` (Llama-3.1-Nemotron-70B) | 70B dense | alt generalist | Older but solid, 128K context. |
| `nemotron-3-nano-omni` | 4B multimodal | future (vision/audio sub-agents) | Only if we add multimodal inputs. |

There is **no medical-specialized Nemotron**. The old plan's `meditron:7b`
"clinical" role has no Nemotron equivalent — keep clinical reasoning as careful
prompting on a general Nemotron, or as an external tool, rather than a separate
model.

---

## Recommended migration, by effort

**Tier 0 — flip the switch (≈15 min, no code).**
Stand up Ollama on the Spark (`ollama pull nemotron-3-nano:4b`), SSH-tunnel
`:11434`, set the three `.env` vars above. The whole app now runs on Nemotron with
a single model. This is the demo-ready milestone — do this first. See
`SETUP_DGX_SPARK.md`.

**Tier 1 — verify tool-calling (≈1–2 hrs).**
Local models vary in how reliably they emit tool calls. Run `scripts/try_live.py`
and watch that safety actually calls `call_911` and health calls `log_vital`. If a
model is flaky, set `LLM_SUPPORTS_TOOLS=false` to fall back to text-only, or move
up a size (nano → cascade-2 → super). Budget the most time here; it's the only
real risk in the swap.

**Tier 2 — per-role models (optional, ~half a day).**
Today every agent shares one `LLM_MODEL`. If you want the router on a tiny fast
model and specialists on a bigger one, add a `model` override per agent: the seam
already accepts a `model` override in `openai_compatible.py` (`overrides.pop("model", ...)`),
so the plumbing exists — you'd add a per-agent field (e.g. on `ToolCallingAgent`)
and pass it through. Recommended split: `nemotron-3-nano:4b` for the router/classifier,
`nemotron-cascade-2` or `nemotron-3-super` for the specialists. Only worth doing if
single-model latency or quality is a problem in the demo.

**Tier 3 — NIM instead of Ollama (optional).**
For production-grade throughput, NVIDIA NIM serves the same models behind the same
OpenAI-compatible API. Same `.env` swap, point `LLM_BASE_URL` at the NIM endpoint.
Not needed for the hackathon.

---

## Rule of thumb

Start at Tier 0 with `nemotron-3-nano:4b` — it gets the entire app onto NVIDIA
hardware with no code change and is fast enough to feel live. Spend your time on
Tier 1 (confirming tool calls), and only reach for `nemotron-3-super` or per-role
models if the demo needs the extra quality.

---

Sources:
- [Nemotron AI Models | NVIDIA Developer](https://developer.nvidia.com/nemotron)
- [nemotron-3-nano (Ollama)](https://ollama.com/library/nemotron-3-nano)
- [nemotron-3-super (Ollama)](https://ollama.com/library/nemotron-3-super)
- [nemotron / Llama-3.1-Nemotron-70B (Ollama)](https://ollama.com/library/nemotron)
- [NVIDIA Nemotron 3 Nano Omni — NVIDIA Technical Blog](https://developer.nvidia.com/blog/nvidia-nemotron-3-nano-omni-powers-multimodal-agent-reasoning-in-a-single-efficient-open-model/)
