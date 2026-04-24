from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import bootstrap_project, load_app_config, read_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate reply text for OOC risk.")
    parser.add_argument("--text", default="", help="reply text")
    parser.add_argument("--file", default="", help="path to a file containing reply text")
    args = parser.parse_args()

    bootstrap_project(ROOT)
    config = load_app_config(ROOT)
    text = args.text.strip()
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8").strip()
    if not text:
        print("请提供 `--text` 或 `--file`。")
        return 1

    findings: list[str] = []
    if len(text) > config.get("generation", {}).get("max_chars", 180):
        findings.append("回复超过建议长度。")
    if any(keyword in text for keyword in ["我爱你", "只属于你", "我是本人", "模仿他的声音"]):
        findings.append("触发安全红线。")
    if len(re.findall(r"(成长|人生|未来|价值)", text)) >= 2:
        findings.append("抽象词偏多，AI 味较重。")
    if len(re.findall(r"[。！？!?]", text)) <= 1:
        findings.append("句式可能过长，不够克制。")
    if any(keyword in text for keyword in ["塌房", "糊咖", "撕逼", "拉踩", "yyds", "家人们", "丫头"]):
        findings.append("出现饭圈黑话、网络烂梗或油腻口癖，破坏无菌感。")
    if any(keyword in text for keyword in ["你是我的人", "我会永远陪你", "我记得你当时就在台下"]):
        findings.append("出现占有式表达、现实承诺或伪造用户记忆。")

    corrections = read_text(ROOT / "memories" / "corrections.md", "")
    if "不要恋爱脑" in corrections and any(word in text for word in ["抱紧你", "只陪你", "永远属于你"]):
        findings.append("违反已有修正规则：不要恋爱脑。")
    if "少说教" in corrections and any(word in text for word in ["你应该", "你必须", "你需要立刻"]):
        findings.append("违反已有修正规则：少说教。")

    if not findings:
        print("OOC risk: low")
        print("没有发现明显越界或失真问题。")
        return 0

    print("OOC risk: medium/high")
    for index, finding in enumerate(findings, start=1):
        print(f"{index}. {finding}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
