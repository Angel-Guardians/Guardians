# Extending Guardian

Four common extension points. Each is a localized change; nothing else moves.

## Add a tool
1. Create `backend/tools/<area>.py` with your callable(s) returning a JSON-able
   `dict`, plus a `register(registry)` that adds a `ToolSpec` (see `civic.py` or
   `emergency.py` as templates).
2. Add your module to the loop in `backend/tools/registry.py:build_default_registry`.
3. Bind it to the agents that should use it by adding the tool name to their
   `tool_names` tuple (e.g. `backend/agents/health.py`).
That's it — the model now sees the tool and the tool loop runs it.

## Edit a prompt
Prompts live in `backend/agents/prompts/`, not inline in the agent files.
- Change an agent's wording: edit its file (e.g. `prompts/safety.py`).
- Change Eleanor's details (meds, contact, history): edit `PATIENT_CONTEXT` in
  `prompts/_base.py` once — every agent picks it up. Never paste patient info into
  individual prompts again.
- A/B a new version: add `"v2": with_context("...")` to that agent's `VERSIONS`
  dict, then set that agent's line in `prompts/active.toml` to `"v2"`. No agent
  code change — `active.toml` is the one place that picks which version is live.

## Add a sub-agent
1. Add the prompt: create `backend/agents/prompts/<name>.py` with a `VERSIONS` dict
   (compose the shared block via `with_context(...)`), then register it in
   `prompts/__init__.py` (`PROMPTS` + `ACTIVE`).
2. Create `backend/agents/<name>.py`: subclass `ToolCallingAgent`, set `name`,
   `system_prompt = get_prompt("<name>")`, `tool_names`, `voice_profile`,
   `escalation_ceiling`.
3. Register it in `backend/agents/guardian.py`: add to the `_agents` dict, add the
   route name to `_ROUTES`, and add a line to `_ROUTER_PROMPT` describing when to
   pick it. The LangGraph wiring in `graph.py` is automatic from the `_agents` dict.

## Add a persona / person-history (RAG)
1. Drop a markdown note at `data/personas/<id>.md` (free-form sections; see
   `eleanor.md`).
2. `recall_history(query, persona_id="<id>")` finds it immediately via keyword
   recall — no DB needed. For real embeddings, set `MEMORY_BACKEND=pgvector`,
   `pip install -e ".[rag]"`, start Postgres (`docker compose up -d postgres`),
   and implement `backend/memory/vector_store.py:recall` (the tool already calls it
   and falls back to keyword if it's absent).

## Add a scenario / demo input
- Conversational: a `.txt` file you pass to `scripts/phase0.py`, or a line in
  `scripts/try_live.py:INPUTS`.
- Vitals: `POST /vitals/ingest` (the watch contract) or extend
  `scripts/inject_vital.py`.

## Not yet wired (open for the team)
`backend/orchestrator/` (event-driven supervisor), `backend/always_on/` (wake word
+ STT capture), and `backend/workers/` (slow-time anomaly detection) are scaffolds
that still raise `NotImplementedError`. The conversational path does **not** depend
on them. Wire them to the same `GuardianAgent` when you add always-on sensing.
