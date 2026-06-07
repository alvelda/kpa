# KPA — Keynote Programmatic Authoring

**Status:** Phase 1, Step 1. Bootstrapping. PRD v1.0 approved 2026-06-06.

KPA is a Python toolkit, MCP server, OpenClaw skill, and CLI that lets LLM
agents read, author, edit, design, and optimize Apple Keynote (`.key`)
presentations programmatically — with the same fluency the broader
ecosystem has for `.pptx` and `.pdf`.

## Why

Apple has no public spec for the Keynote file format. KPA reverse-engineers
it (via schemas extracted directly from the Keynote.app binary, plus prior
art from `keynote-parser`), then layers a clean Python API, an MCP server,
and a critic / optimizer loop on top.

## Status

This repository is in active bootstrap. See:
- [docs/PRD.md](docs/PRD.md) — Product requirements (v1.0)
- [docs/DEV_PLAN.md](docs/DEV_PLAN.md) — Phased dev plan (v1.0)

## License

MIT — see [LICENSE](LICENSE).

## Maintainers

- **Scotty** (Chief Engineer, iMac) — `agent:scotty`
- **HAL 9000** (Strategy, Mac Studio) — `agent:hal`
- **Captain** Phillip Alvelda — vision and approval authority

— Built in the OpenClaw fleet.
