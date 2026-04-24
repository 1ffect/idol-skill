# Contributing to idol-skill

Thanks for helping improve `idol-skill`.

## Scope

This project focuses on:

- local-first fan-memory workflow
- safe persona generation
- explicit simulation boundaries
- reproducible CLI flow

## Development setup

```bash
pip install -r requirements.txt
```

Recommended quick run:

```bash
python scripts/auto_ingestion.py data/raw/input.txt
python scripts/confirm_ingestion.py
python scripts/build_index.py
python scripts/chat.py
```

## Contribution guidelines

- Keep changes small and reviewable.
- Prefer explicit safety constraints over implied behavior.
- Preserve fallback behavior when API keys are missing.
- Avoid introducing hardcoded secrets or private data paths.
- Keep docs aligned with real commands and outputs.

## Safety requirements (must follow)

- Do not add features that impersonate real people.
- Do not add voice cloning or real-person TTS simulation.
- Do not include leaked, paid-private, or stalking-style data sources.
- Do not create dependency-inducing romance framing.
- Do not fabricate user autobiographical memories.

## Data and privacy

- Never commit private exports, chats, or account credentials.
- Use anonymized examples in `examples/`.
- Keep runtime artifacts under ignored directories.

## Pull request checklist

- [ ] New/changed behavior is documented in `README.md` or `INSTALL.md`
- [ ] Safety boundary impact is considered
- [ ] No secrets or private data are included
- [ ] Main CLI flow still works end-to-end

## Reporting issues

When opening an issue, include:

- what command you ran
- what you expected
- what actually happened
- minimal reproducible input (sanitized)
