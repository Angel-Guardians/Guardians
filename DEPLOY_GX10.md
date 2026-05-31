# Deploying Guardian on the DGX Spark (GX10)

Production deployment guide for the full Guardian stack on the **GX10** (NVIDIA DGX
Spark, GB10 Grace Blackwell, 121 GiB unified memory). It serves the **local
Nemotron Nano (NVFP4)** model on TensorRT-LLM and exposes the UI over **Tailscale**.

For the generic cloud/localhost Docker workflow (tests, scripts, pgvector), see
[DOCKER.md](DOCKER.md). This doc covers the GX10-specific parts: the local model
server, the backend on host port **8080**, and Tailscale exposure.

## Topology

Three layers, all on the one box:

| Layer | Container | Host port | Network | Notes |
|-------|-----------|-----------|---------|-------|
| LLM   | `guardian-trtllm`   | 8000        | host   | TensorRT-LLM serving `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4` (OpenAI-compatible). |
| API   | `guardian-backend`  | 8080 → 8000 | bridge | FastAPI + LangGraph. Reaches the model via `host.docker.internal:8000`. |
| UI    | `guardian-frontend` | 3000        | bridge | Next.js. Calls the backend at the baked `NEXT_PUBLIC_API_BASE_URL`. |

A second TRT-LLM container, `guardian-omni-trtllm` (port **8001**), serves the
multimodal "omni" model for the future voice phase. It is **not** part of this
stack — start/stop it independently.

**Why the backend is on 8080.** TRT-LLM owns host port 8000. The backend listens
on 8000 *inside* its container but publishes on **8080** on the host to avoid the
collision.

**How the backend reaches the model.** trtllm uses host networking; the backend is
on a bridge network. It reaches the host-bound model through `host.docker.internal`,
mapped to the docker bridge gateway by `extra_hosts: ["host.docker.internal:host-gateway"]`.
`.env` sets `LLM_BASE_URL=http://host.docker.internal:8000/v1` to match.

## Access URLs (Tailscale)

Both app services bind `0.0.0.0`, so they're reachable on every host interface. The
canonical address is this node's **Tailscale** IP, reachable from any tailnet device
on any network:

- Frontend UI → **http://100.103.166.16:3000**  (MagicDNS: http://gx10-3d68.tailb0d74f.ts.net:3000)
- Backend API → **http://100.103.166.16:8080**
- Health      → http://100.103.166.16:8080/health

> The frontend's API URL is **baked at build time** (`NEXT_PUBLIC_API_BASE_URL`),
> defaulting to the Tailscale IP `http://100.103.166.16:8080`. The browser runs on
> *another* device and calls that directly, so it must be an address that device can
> reach — hence Tailscale, not `localhost`.

**LAN fallback.** The same services are also reachable on the GX10's WiFi IP
(`http://10.10.52.255:{3000,8080}`) for devices on the same WiFi. To make the LAN
the *primary* path, rebuild the frontend with
`NEXT_PUBLIC_API_BASE_URL=http://10.10.52.255:8080` (see §3).

## Prerequisites

- Docker Engine 24+ with the Compose plugin and the **NVIDIA Container Toolkit**
  (so GPU device reservations work).
- The Nemotron model in the HF cache at `~/.cache/huggingface` (~16 GB, pulled once).
- The tuned AutoDeploy config at `~/nano_v3_gb10.yaml` (mounted into trtllm as
  `/workspace/nano_v3.yaml`).
- Tailscale up on the GX10 (`tailscale status` shows this node).
- A `.env` in the repo root (git-ignored) — see §2.

## 1. The model server (TRT-LLM)

The compose `trtllm` service mirrors this tuned launch:

```bash
trtllm-serve serve \
  --host 0.0.0.0 --port 8000 \
  --backend _autodeploy \
  --trust_remote_code \
  --reasoning_parser nano-v3 \
  --tool_parser qwen3_coder \
  --extra_llm_api_options /workspace/nano_v3.yaml \
  nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4
```

Let Compose manage it (§3, fresh boot) **or** run it yourself and bring up only the
app. Model load is slow — a cold start can take several minutes; the compose
healthcheck allows up to ~10 min (`start_period: 600s`, `retries: 40`).

## 2. Configure `.env` (local model)

Switching cloud ↔ local is an `LLM_*`-only change. For the GX10:

```env
LLM_PROVIDER=local
LLM_BASE_URL=http://host.docker.internal:8000/v1
LLM_MODEL=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4
LLM_API_KEY=not-needed
LLM_SUPPORTS_TOOLS=true
LLM_TIMEOUT=120
```

Leave the other sections (Twilio, Kokoro, Whisper, LangSmith) as your environment
needs. `.env` is **not** baked into any image — the backend reads it at runtime via
Compose's `env_file`, and `.dockerignore` keeps it out of the build context.

## 3. Build & launch

**Fresh boot — let Compose start everything (model + app):**

```bash
docker compose up -d --build
```

**Model already running (the usual case here)** — bring up only the app so the
running `guardian-trtllm` is left untouched. (It shares the container name **and**
host port 8000 with the compose `trtllm` service, so starting that service would
collide.)

```bash
docker compose up -d --build --no-deps backend frontend
```

**Clean recreate** (after editing `.env` or backend code — the image bundles the
source, and `env_file` is re-read on recreate):

```bash
docker compose up -d --build --force-recreate --no-deps backend frontend
```

> **Repointing the UI.** `NEXT_PUBLIC_API_BASE_URL` is read at **build** time, so a
> URL change requires a frontend rebuild:
> ```bash
> docker compose build frontend && docker compose up -d --no-deps frontend
> # one-off override:
> NEXT_PUBLIC_API_BASE_URL=http://10.10.52.255:8080 docker compose build frontend
> ```

## 4. Verify

```bash
TS=100.103.166.16

# Backend healthy + model wired up
curl -s http://$TS:8080/health
# -> {"status":"ok","guardian":"ready"}

# A real turn routed to the local model (~20 s; reasoning model)
curl -s -X POST http://$TS:8080/turn/ \
  -H 'Content-Type: application/json' \
  -d '{"text":"I feel a little dizzy. What should I do?","patient_id":1}'
# -> {"route":"...","reply":"...","tool_calls":[]}

# Frontend serves
curl -s -o /dev/null -w '%{http_code}\n' http://$TS:3000/   # 200

# CORS admits the Tailscale frontend origin
curl -s -i -X OPTIONS http://$TS:8080/turn/ \
  -H "Origin: http://$TS:3000" \
  -H 'Access-Control-Request-Method: POST' | grep -i access-control-allow-origin
# -> access-control-allow-origin: http://100.103.166.16:3000
```

## 5. Operations

```bash
docker compose logs -f backend                            # API logs
docker compose ps                                         # status
docker compose restart backend                            # re-read .env, reconnect model
docker compose down                                       # stop app (+ trtllm if compose-managed)
git pull && docker compose up -d --build --no-deps backend frontend   # redeploy app
```

### Persistence
The SQLite DB lives on the persistent `guardian-data` volume. The `backend` service
sets `DATABASE_URL: sqlite:////app/data/guardian.db` (4 slashes = **absolute** path)
in its compose `environment:` block, which overrides the relative
`DATABASE_URL=sqlite:///./guardian.db` in `.env`. The relative `.env` value would
resolve to `/app/guardian.db` — *outside* the volume mounted at `/app/data` — and
be lost on `docker compose down`/recreate; the absolute override keeps the DB inside
the volume so runtime data (not just the Eleanor #1 / Sarah #2 re-seed) survives.

> The `.env` value stays relative on purpose — host / non-Docker runs write
> `./guardian.db` at the repo root. Only the container is repointed at the volume.

Verify after a recreate:

```bash
docker compose up -d --force-recreate --no-deps backend
docker exec guardian-backend ls -la /app/data        # guardian.db is here
# survives a full down/up (model server left untouched):
docker compose down && docker compose up -d --no-deps backend frontend
```

## 6. GPU / unified memory

The GB10 has **one unified 121 GiB pool** shared by CPU and GPU (so `nvidia-smi`
reports no discrete VRAM — query the system pool with `free -h` instead). With both
the text Nemotron (:8000) and the omni model (:8001) loaded, ~92 GiB is in use,
~29 GiB free. Before adding STT/TTS, lower the text model's KV-cache slice —
`kv_cache_config.free_gpu_memory_fraction` (currently `0.88`) in `~/nano_v3_gb10.yaml`
— and re-check headroom. STT/TTS arrive as their own services on their own ports
(see the commented block at the bottom of `docker-compose.yml`).

## 7. Troubleshooting

- **`/health` shows `unconfigured`** — the GuardianAgent didn't build; check `LLM_*`
  in `.env` and `docker compose logs backend`.
- **`/turn` errors or times out** — the model isn't up at `:8000`, or it's still
  loading. On the host: `curl localhost:8000/health`; `docker logs guardian-trtllm`.
- **Backend can't reach the model** — confirm `extra_hosts: host.docker.internal:host-gateway`
  and `LLM_BASE_URL=http://host.docker.internal:8000/v1`. From inside:
  `docker exec guardian-backend python -c "import urllib.request;print(urllib.request.urlopen('http://host.docker.internal:8000/v1/models').status)"`.
- **Frontend calls fail in the browser (CORS or wrong host)** — the bundle was built
  with the wrong `NEXT_PUBLIC_API_BASE_URL`, or the browser's origin isn't allowed.
  Rebuild the frontend with the right URL; CORS allows `:3000` on localhost, RFC1918
  LAN, and Tailscale (`100.x` / `*.ts.net`) — see `backend/config.py`.
- **`port is already allocated` (8000) / name `guardian-trtllm` in use** — a trtllm
  is already running. Use `--no-deps backend frontend` (don't start the compose
  `trtllm`), or `docker rm -f guardian-trtllm` first.
