# idol-skill

> 为了你，千千万万次回到那个夏天。

`idol-skill` 是一个可开源复用的 Agent Skill + CLI 工程：  
把公开物料与用户主观记忆蒸馏为“高光时期的理想化偶像陪伴人格”，并在设计上内置安全边界。

## 开源定位

- **项目类型**: Agent Skill 仓库（根目录即 skill 目录）
- **发布渠道**: GitHub
- **推荐安装路径**: `.claude/skills/idol-skill`（兼容 Cursor）
- **运行方式**: 本地 Python CLI

## 安装（推荐）

在你的项目仓库根目录执行：

```bash
mkdir -p .claude/skills
git clone https://github.com/1ffect/idol-skill.git .claude/skills/idol-skill
```

然后重启会话，在 Agent 中可通过 `/idol-skill` 显式触发（或由模型按描述自动调用）。

> 兼容 Cursor：Cursor 会识别 `.claude/skills` 下的技能目录。  
> 如果你偏好 Cursor 原生目录，也可放到 `.cursor/skills/idol-skill`。

## 本地开发快速开始

```bash
pip install -r requirements.txt
python scripts/auto_ingestion.py data/raw/input.txt
python scripts/confirm_ingestion.py
python scripts/build_index.py
python scripts/chat.py
```

可选体验：

```bash
python scripts/bias_room.py
python scripts/if_timeline.py "写一段平行采访片段"
```

## 核心能力

- `Auto Ingestion`: 原始文本清洗、分段、标签化，先进入待确认区
- `Archive Preview Confirmation`: 先预览后封印，降低脏数据污染
- `Memory Layers`: `core / emotional / dynamic / augmented / corrections`
- `RAG Retrieval`: 结合语义、标签、时代、可信度做检索
- `Persona Matrix`: 四种表达人格模板
- `Stealth Augmentation`: 默认关闭联网，低频低权重补充环境细节
- `OOC Correction`: 用户反馈可回写修正规则

## 安全边界（默认内置）

- 不冒充真人，不做声音克隆
- 不使用私密、付费、泄露、私生素材
- 不制造现实恋爱承诺与关系依赖
- 不伪造用户未提供的真实经历
- 所有“平行时间线”内容必须明确标注为模拟容器

## 项目结构

```text
idol-skill/
├── SKILL.md
├── prompts/
├── scripts/
├── src/
├── templates/
├── memories/
├── config/
├── examples/
├── skills/
├── triggers/
├── data/                 # 本地运行数据目录（多数产物已 gitignore）
├── requirements.txt
└── LICENSE
```

## 环境变量

未配置 API key 也可以运行（自动 fallback）。可选变量：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `IDOL_SKILL_API_KEY`
- `IDOL_SKILL_BASE_URL`

## 开源前检查清单

- [ ] 不提交任何私有聊天记录、导出原文、账号信息
- [ ] 不提交运行态状态文件和向量索引产物
- [ ] 用 `examples/` 提供可公开演示数据
- [ ] 确认 `LICENSE` 与依赖声明完整

## 许可证

本仓库使用 `LICENSE` 中声明的许可协议。
