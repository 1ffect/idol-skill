# AGENTS.md

## 项目目标

实现一个可本地 CLI 跑通的 Idol Skill MVP，把公开物料、用户主观记忆和安全低权重补帧组合成一个高光时期的理想化偶像陪伴人格。

## 安装命令

```bash
pip install -r requirements.txt
```

## 运行命令

```bash
python scripts/auto_ingestion.py data/raw/input.txt
python scripts/confirm_ingestion.py
python scripts/build_index.py
python scripts/chat.py
python scripts/generate_skill.py --slug idol-example-export
```

## 测试命令

```bash
python -m compileall .
python scripts/auto_ingestion.py data/raw/input.txt
python scripts/build_index.py
python scripts/stealth_augmentation.py "我好想回到那个夏天"
python scripts/evaluate_ooc.py --text "今天先别撑太满\n去喝点水\n剩下的 明天再慢慢来"
```

## 代码风格

- Python 3.10+
- 使用 `pathlib`
- 重要函数写 docstring
- 文件缺失时自动创建
- JSON / YAML 解析失败要有 fallback
- 没有 API key 时必须允许 rule-based fallback 跑通 demo

## 安全边界

- 不写入真实明星数据
- 不做真人声音克隆
- 不抓取付费/私密平台
- 不输出冒充真人的话术
- 不抓取私生、泄露、住址、行程、恋情、黑料内容
- 不伪造用户私人记忆
- 所有 demo 使用虚构人物

## 完成标准

- Quick Start 可跑通
- `auto_ingestion -> confirm_ingestion -> build_index -> chat` 主链路可运行
- `augmentation` 默认联网关闭
- `corrections` 优先级高于 persona 与 memories
- 修改后必须保证 Quick Start 可跑通
