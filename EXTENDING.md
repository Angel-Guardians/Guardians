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

## Add a sub-agent
1. Create `backend/agents/<name>.py`: subclass `ToolCallingAgent`, set
   `name`, `system_prompt`, `tool_names`, `voice_profile`, `escalation_ceiling`.
2. Register it in `backend/agents/guardian.py`: add to the `_agents` dict, add the
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
