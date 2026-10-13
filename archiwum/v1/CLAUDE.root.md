# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Layout

This directory contains:
- **`deepfellow-infra/`** — the DeepFellow framework codebase (AI infrastructure platform)
- **`deepfellow-router/`** — the thesis work repo (data, eval, docs, future router code)
- **`koncepcja.md` / `koncepcja.pdf`** — single source of truth for the thesis concept, architecture, plan and current status

All development commands below run from inside `deepfellow-infra/`.

## Commands (run from `deepfellow-infra/`)

```bash
# Development server (localhost:8086, hot reload)
just dev

# Tests
just test                        # with coverage report
just ntest                       # parallel workers
just test tests/path/test_foo.py # single file
just test -k "test_name"         # single test by name

# Code quality (all must pass before committing)
just ruff            # lint
just ruff-format     # format
just pyright         # type checking

# Full pre-commit check suite
just check           # license-check + ruff + ruff-format + pyright + auth checks
just pre-commit      # runs all pre-commit hooks

# UI rebuild (after webui changes)
just ui-rebuild
```

All commands use `uv run` internally — no manual venv activation needed.

## Architecture

**DeepFellow Infra** is an on-premises AI service orchestration platform exposing OpenAI-compatible endpoints (`/v1/models`, `/v1/messages`, `/v1/embeddings`, `/v1/audio/*`, `/v1/images/*`).

### Request Flow

```
HTTP request → FastAPI (server/main.py)
  → auth dependency (server/utils/dependencies.py)
  → router (server/api/openai.py)
  → EndpointRegistry.execute_*() (server/endpointregistry.py)
  → concrete Service (server/services/*_service.py)
  → upstream model / container
  → StreamingResponse
```

### Key Modules

| Module | Purpose |
|---|---|
| `server/lifecycle.py` | FastAPI lifespan — startup/shutdown, all initialization |
| `server/applicationcontext.py` | Wires together all managers and registries |
| `server/serviceprovider.py` | Loads/saves `services.json`; handles v1→v2 migration |
| `server/services_manager.py` | Runtime registry of active service instances |
| `server/endpointregistry.py` | Maps model names to service instances |
| `server/config.py` | `AppSettings` — all env vars via pydantic-settings |
| `server/docker.py` | Async Docker orchestration (aiodocker) |
| `server/portservice.py` | Allocates free ports for containerized services |
| `server/models/api.py` | Pydantic request/response models for all API endpoints |

### Service Types

All services implement `BaseService` (`server/services/base_service.py`). Containerized services extend `Base2Service`. The 18 concrete implementations include: `OllamaService`, `VllmService`, `LlamaCppService`, `ClaudeService`, `OpenAIService`, `GoogleAIService`, `StableDiffusionService`, `CoquiService`, `McpService`, `RerankService`, `RemoteService`, `CustomService`, etc.

Service configuration is stored in `services.json` and loaded at startup.

### WebSocket Mesh

`server/websockets/parent_infra.py` handles optional upstream mesh connection (`DF_CONNECT_TO_MESH_URL`). Multiple infra nodes can form a hierarchy.

### Frontend

`webui/` is a React 19 + TypeScript SPA (Vite, TanStack Router/Query, Tailwind, shadcn/ui). Built output is copied to `static/` and served by FastAPI. Rebuild with `just ui-rebuild`.

## Configuration

Copy `example.env` to `.env` (`just env-copy`) and set:
- `DF_INFRA_API_KEY` — auth for `/v1/*` endpoints
- `DF_INFRA_ADMIN_API_KEY` — auth for admin/management endpoints
- `DF_STORAGE_DIR` — where models and service data are stored
- `DF_NVIDIA_GPUS_COUNT` — GPU count available to containers

## Code Conventions

- Python 3.13, strict pyright, ruff with comprehensive rules
- Every Python file must have the DeepFellow license header (enforced by `just license-check`)
- Conventional commits enforced by pre-commit hook
- No mock DB in tests — integration tests hit real services where applicable

## Thesis Context

The research goal is building a **semantic query router** as a new `RouterService` in this framework, served via `/v1/chat/completions?model=router`. Details: `../koncepcja.md`. Architecture:
- **Classifier**: heuristics → embedding similarity → small zero-shot model (cascade)
- **Router**: SIMPLE → Qwen 1.5B (local), COMPLEX → Llama 3 70B
- **Map-Reduce**: decomposition pipeline for COMPLEX multi-step queries
- Config-driven via YAML (thresholds, weights, model assignments)
