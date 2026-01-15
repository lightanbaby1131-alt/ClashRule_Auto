import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re

# -----------------------------
# AI 规则源（已加入你的 ForeignAI 来源）
# -----------------------------
AI_SOURCES = {
    "OpenAI": [
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/OpenAI/OpenAI.list",
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/OpenAI.list",
    ],
    "ChatGPT": [
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/ChatGPT/ChatGPT.list",
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/ChatGPT.list",
    ],
    "GoogleAI": [
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/GoogleAI/GoogleAI.list",
    ],
    "Anthropic": [
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Anthropic/Anthropic.list",
    ],
    "HuggingFace": [
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/HuggingFace/HuggingFace.list",
    ],
    "StabilityAI": [
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/StabilityAI/StabilityAI.list",
    ],
    "Midjourney": [
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Midjourney/Midjourney.list",
    ],
    "RunwayML": [
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/RunwayML/RunwayML.list",
    ],
    "Perplexity": [
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Perplexity/Perplexity.list",
    ],
    "DeepL": [
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/DeepL/DeepL.list",
    ],

    # 新增来源（你的 Online-Clash ForeignAI）
    "ForeignAI_Extra": [
        "https://raw.githubusercontent.com/lightanbaby1131-alt/Online-Clash/refs/heads/main/Ruleset/ForeignAI.list"
    ],

    # AI-Domains（纯域名，需要转换）
    "AI_Domains": [
        "https://raw.githubusercontent.com/ai-collection/ai-domains/main/domains.txt"
    ]
}

# 输出路径
OUTPUT = Path("Clash/Ruleset/AI/ForeignAI.list")

# 临时目录
TMP_DIR = Path(".github/tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# 工具函数
# -----------------------------
def now_bj():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y年%m月%d日 %H:%M")


def fetch(url):
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.text.splitlines()


# -----------------------------
# 统一转换为 Clash DOMAIN-SUFFIX 规则
# -----------------------------
def extract_domain(line):
    line = line.strip()

    if not line or line.startswith("!") or line.startswith("@@"):
        return None

    if line.startswith("DOMAIN-SUFFIX,"):
        return line.split(",", 1)[1].strip()

    if line.startswith("DOMAIN,"):
        return line.split(",", 1)[1].strip()

    if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", line):
        return line

    return None


# -----------------------------
# 主逻辑
# -----------------------------
def main():
    grouped_domains = {}
    global_set = set()

    for group, urls in AI_SOURCES.items():
        group_set = set()

        for url in urls:
            try:
                lines = fetch(url)
            except:
                continue

            for line in lines:
                d = extract_domain(line)
                if d:
                    group_set.add(d.lower())

        # 保存临时文件
        tmp_file = TMP_DIR / f"{group}.txt"
        tmp_file.write_text("\n".join(sorted(group_set)), encoding="utf-8")

        grouped_domains[group] = group_set

    # -----------------------------
    # 全局去重
    # -----------------------------
    final_groups = {}

    for group, domains in grouped_domains.items():
        unique = domains - global_set
        global_set |= domains
        final_groups[group] = sorted(unique)

    # -----------------------------
    # 写入最终 ForeignAI.list
    # -----------------------------
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "# 内容：Foreign AI 域名合并规则（分类 + 去重）",
        f"# 总数量：{len(global_set)} 条",
        f"# 更新时间（北京时间）：{now_bj()}",
        "",
    ]

    lines = header

    for group, domains in final_groups.items():
        lines.append(f"# ===== {group} =====")
        for d in domains:
            lines.append(f"DOMAIN-SUFFIX,{d}")
        lines.append("")

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
