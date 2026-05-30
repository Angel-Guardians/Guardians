# Guardian — Developer Guide

A practical guide to running, understanding, and extending this repo.

---

## 1. One-time setup

```bash
# from the repo root
uv sync --extra dev           # install deps (incl. langgraph, langsmith) + dev tools
cp .env.example .env          # then edit .env (see below)
```

If you don't use `uv`, a plain venv works too:

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Configure `.env`

Only the `LLM_*` block matters to run the agent. Default = OpenAI cloud:

```
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...           # <-- your real key
LLM_TEMPERATURE=0.7
```

To run against a local model later (DGX Spark / vLLM / NIM / Ollama), change ONLY
these — no code edits:

```
LLM_PROVIDER=local
LLM_BASE_URL=http://dgx-spark:8000/v1
LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
LLM_API_KEY=not-needed
```

For LangSmith tracing, also set:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=guardian-phase0
```

---

## 2. Running the agent (text mode)

```bash
# interactive: type a message, get a reply
uv run python scripts/phase0.py

# or feed a .txt file (the input source for Phase 1)
uv run python scripts/phase0.py tests/scenarios/test_elenor.txt
```

Needs a valid `LLM_API_KEY` (it makes real model calls). Ctrl-C to quit.

What happens on each message: the text goes to `GuardianAgent.chat()`, which runs
the LangGraph orchestrator (router → one specialist → optional tool calls → reply).

---

## 3. Running the tests

Tests run fully offline — no API key, no network — because they inject a scripted
fake model (`tests/fakes.py:FakeLLM`).

```bash
# the three implemented tests
uv run pytest tests/unit/test_router.py tests/scenarios/test_scenario_01_fall.py -v

# everything (other test files are intentionally skipped stubs for later)
uv run pytest

# or via the Makefile
make test
```

The three passing tests:
- `test_fall_keyword_routes_to_safety_without_calling_model` — a fall is routed to
  Safety by the deterministic keyword path, with zero model calls.
- `test_ambiguous_utterance_falls_through_to_llm` — non-emergency text is classified
  by the LLM router.
- `test_scenario_01_fall_e2e` — full flow: fall transcript → Safety agent →
  `call_911` stub fires → `notify_caregiver` stub fires → calm spoken reply.

Lint/format:

```bash
make lint      # ruff check
make format    # ruff format
```

---

## 4. Architecture: the request lifecycle

A single message flows through three layers. Nothing above the LLM adapter knows
which model provider is in use.

```
scripts/phase0.py  (reads text)
        │
        ▼
GuardianAgent.chat()                         backend/agents/guardian.py
        │  builds state, invokes the graph
        ▼
LangGraph StateGraph                          backend/agents/graph.py
   START → router ──(conditional edge)──► one specialist node → END
        │                                         │
        │ route() = keyword fast-path             │ ToolCallingAgent.chat()
        │           or LLM classification         │   backend/agents/base.py
        ▼                                         ▼
   backend.llm.LLMClient  ◄───────────────  loop: call model → run tool → repeat
        │  (provider-neutral interface)            │
        ▼                                          ▼
   OpenAICompatibleClient                     ToolRegistry.execute()
     backend/llm/openai_compatible.py           backend/tools/registry.py
        │  (the ONLY file that imports openai)     │  runs stub, returns canned dict
        ▼                                          ▼
   OpenAI / vLLM / NIM / Ollama endpoint      backend/tools/*.py stubs
```

### The three layers

**1. LLM layer — `backend/llm/`** (provider-agnostic)
- `base.py` — neutral data types (`Message`, `ToolSpec`, `ToolCall`, `LLMResponse`)
  and the `LLMClient` interface everything depends on.
- `config.py` — reads all `LLM_*` env vars. The ONLY place model config lives.
- `openai_compatible.py` — the adapter. Converts neutral types ↔ OpenAI wire format.
  The only file allowed to import the `openai` SDK. Provider errors are wrapped into
  `LLMError` here so the rest of the app never catches vendor exceptions.
- `factory.py` — `build_llm()`: config → an `LLMClient`.
- `tracing.py` — provider-neutral LangSmith span decorator.

**2. Tool layer — `backend/tools/`** (stubs today, real integrations later)
- `registry.py` — maps a tool name to (JSON schema + Python function). `execute()`
  runs the function and logs the call.
- `emergency.py`, `health.py`, `reminder.py` — the stub functions. Each returns a
  canned dict and records to a module-level `CALL_LOG` (handy for tests/demos).

**3. Agent layer — `backend/agents/`** (orchestration + behavior)
- `base.py` — `ToolCallingAgent`: the shared tool-calling loop (call model; if it
  requests tools, run them, feed results back, repeat; else return text).
- `safety.py`, `health.py`, `reminder.py`, `behavior.py`, `caregiver_liaison.py`,
  `companion.py` — each is just a system prompt + a tuple of tool names. ~15 lines.
- `graph.py` — builds the LangGraph `StateGraph` (router node + specialist nodes).
- `guardian.py` — `GuardianAgent`: wires the LLM client + registry + agents, holds
  the router logic and conversation history, and invokes the compiled graph.

---

## 5. How to make common edits

### Change how an agent talks
Edit the `SYSTEM_PROMPT` string in that agent's file (e.g. `backend/agents/safety.py`).
Nothing else to touch.

### Add a new tool (stub)
1. Write the function + a `register()` entry in the relevant `backend/tools/*.py`
   (copy the shape of `call_911` in `emergency.py`).
2. Add the tool's name to the `tool_names` tuple of whichever agent(s) should use it.
That's it — the registry and the agent loop pick it up automatically.

### Turn a stub into a real integration
Replace the body of the stub function (e.g. swap `notify_caregiver`'s canned dict
for a real Twilio call). The agent, graph, and LLM layers don't change.

### Add a new specialist agent
1. Create `backend/agents/<name>.py` subclassing `ToolCallingAgent` with a
   `system_prompt` and `tool_names` (copy an existing one).
2. Register it in `GuardianAgent._agents` in `guardian.py`.
3. Add its name to `_ROUTES` and describe it in `_ROUTER_PROMPT` so the router can
   pick it. (Graph wiring is automatic — `build_guardian_graph` adds a node + edge
   for every entry in the agents dict.)

### Adjust routing
- Emergency keywords: edit `_SAFETY_KEYWORDS` in `guardian.py`.
- Classification behavior: edit `_ROUTER_PROMPT` in `guardian.py`.

### Swap the LLM provider
Change the `LLM_*` vars in `.env`. No code edits. (If you ever add a provider that
is NOT OpenAI-compatible, add one adapter file next to `openai_compatible.py` and
one branch in `factory.py`.)

---

## 6. Observability (LangSmith)

With the `LANGSMITH_*` vars set, every call to `GuardianAgent.chat()` produces a
trace in your LangSmith project:
- one span per LangGraph node (so you see which route was chosen, which specialist ran),
- model calls nested underneath with prompts, responses, and token usage,
- tool executions visible in the logs (`[tool] -> name(args)` / `[tool] <- result`).

Tracing is off by default and a no-op when disabled, so tests stay clean.

---

## 7. Gotchas

- Tests need NO API key (they use `FakeLLM`). Running the live agent via
  `scripts/phase0.py` DOES need `LLM_API_KEY`.
- There are stale duplicate agent files at the repo ROOT (`safety.py`, etc.). The
  REAL ones live in `backend/agents/`. Safe to delete the root copies.
- `tests/conftest.py` has unfinished `db_session` / `eleanor` fixtures (they raise
  `NotImplementedError`). The current tests don't use them; don't wire new tests to
  them until they're implemented.
- `test_tool_decorators.py` and parts of `conftest.py` are placeholders for later
  phases — intentionally skipped.
