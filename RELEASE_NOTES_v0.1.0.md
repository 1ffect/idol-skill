# idol-skill v0.1.0

First public open-source release.

## Highlights

- Open-source-ready repository structure for Agent Skill usage
- GitHub installation path documented with `.claude/skills` as primary target
- Cursor-compatible installation path documented
- Local-first CLI workflow documented end-to-end
- Safety-first constraints explicitly documented

## Included capabilities

- auto ingestion and preview confirmation flow
- memory layering and retrieval
- persona matrix routing
- low-weight augmentation pipeline with fallback
- OOC correction loop
- bias room and IF timeline modes

## Documentation updates

- `README.md` rewritten for public onboarding
- `INSTALL.md` added with install and verification steps
- `CONTRIBUTING.md` added for external contributors

## Security and privacy posture

- runtime artifacts and local state paths moved into ignore rules
- no hardcoded keys found in source scanning
- fallback mode supported without API keys

## Upgrade notes

- Replace demo input with your own sanitized public materials
- Keep `allow_web` disabled by default unless your deployment policy allows it
