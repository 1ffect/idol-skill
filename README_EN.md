# idol-skill

> For you, I return to that summer, a thousand times.

`idol-skill` is an Agent Skill + local CLI project that distills public materials and fan memory into an idealized companion persona anchored to a chosen peak era.

<p align="center">
  <a href="./README.md#data-sources">[ Data Sources ]</a> ｜ 
  <a href="./INSTALL.md#install-doc">[ Install ]</a> ｜ 
  <a href="./README.md#usage">[ Usage ]</a> ｜ 
  <a href="./README.md#demo">[ Demo ]</a> ｜ 
  <a href="./README.md">[ 中文 ]</a>
</p>

## Positioning

- Project type: Agent Skill repository (repo root is the skill root)
- Runtime: local Python CLI
- Recommended install path: `.claude/skills/idol-skill` (Cursor compatible)

## Install

```bash
mkdir -p .claude/skills
git clone https://github.com/1ffect/idol-skill.git .claude/skills/idol-skill
```

Then restart your agent session and invoke with `/idol-skill`.

## Quick Usage

```bash
pip install -r requirements.txt
python scripts/auto_ingestion.py data/raw/input.txt
python scripts/confirm_ingestion.py
python scripts/build_index.py
python scripts/chat.py
```

## Demo

**Input**

> I am exhausted today.

**idol-skill**

> Take a breath first.  
> You did enough for today.  
> We can finish the rest tomorrow.

## Safety Boundaries

- No impersonation of a real person
- No voice cloning
- No private/leaked/stalker materials
- No dependency-building or exclusivity framing

## License

This project is released under the license in `LICENSE`.
