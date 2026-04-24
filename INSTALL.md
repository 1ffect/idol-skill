<a id="install-doc"></a>
# INSTALL

本文档对齐 `colleague-skill` 的安装体验，主路径使用 `.claude/skills`（兼容 Cursor）。

## 1) 安装到当前项目（推荐）

在你的项目 git 根目录执行：

```bash
mkdir -p .claude/skills
git clone https://github.com/1ffect/idol-skill.git .claude/skills/idol-skill
```

重启 Agent 会话后即可使用。

## 2) 全局安装（所有项目可用）

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/1ffect/idol-skill.git ~/.claude/skills/idol-skill
```

## 3) Cursor 兼容说明

Cursor 会自动识别 `.claude/skills` 与 `~/.claude/skills`。  
如需使用 Cursor 原生目录，也可改为：

```bash
mkdir -p .cursor/skills
git clone https://github.com/1ffect/idol-skill.git .cursor/skills/idol-skill
```

## 4) 依赖安装

进入 skill 目录后：

```bash
pip install -r requirements.txt
```

## 5) 快速验证

```bash
python scripts/auto_ingestion.py data/raw/input.txt
python scripts/confirm_ingestion.py
python scripts/build_index.py
python scripts/chat.py
```

如果没有 API key，系统会自动 fallback 到 rule-based 流程。
