import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
import sys

EASYLIST_URL = "https://easylist.to/easylist/easylist.txt"

CATEGORY_MAP = {
    "General": "通用广告",
    "Tracking": "追踪器",
    "Social": "社交按钮",
}

def detect_category(line: str, current: str) -> str:
    m = re.match(r"^![-\s]*([A-Za-z]+)[-\s]*$", line)
    if m:
        key = m.group(1)
        return CATEGORY_MAP.get(key, current)
    return current

def extract_domain(rule: str) -> str | None:
    rule = rule.strip()

    if not rule or rule.startswith(("!", "@@", "##", "#@#")):
        return None

    m = re.match(r"^\|\|([^\/\^]+)\^", rule)
    if m:
        return f"DOMAIN-SUFFIX,{m.group(1)}"

    m = re.match(r"^\|https?:\/\/([^\/]+)\/", rule)
    if m:
        return f"DOMAIN,{m.group(1)}"

    return None

def convert(outfile: str):
    print("Downloading EasyList...")
    text = requests.get(EASYLIST_URL, timeout=30).text

    current_category = "通用广告"
    categorized = {
        "通用广告": set(),
        "追踪器": set(),
        "社交按钮": set(),
    }

    for line in text.splitlines():
        current_category = detect_category(line, current_category)
        r = extract_domain(line)
        if r:
            categorized[current_category].add(r)

    total_rules = sum(len(v) for v in categorized.values())

    now = datetime.utcnow() + timedelta(hours=8)
    update_time = now.strftime("%Y-%m-%d %H:%M:%S")

    out_lines = [
        "# 内容：广告拦截规则 EasyList",
        f"# 数量：{total_rules} 条",
        f"# 更新时间：{update_time}",
        "",
    ]

    for cat, rules in categorized.items():
        out_lines.append(f"# ===== {cat} =====")
        out_lines.extend(sorted(rules))
        out_lines.append("")

    outfile_path = Path(outfile)
    outfile_path.parent.mkdir(parents=True, exist_ok=True)
    outfile_path.write_text("\n".join(out_lines), encoding="utf-8")

    print(f"Generated {outfile} with {total_rules} rules.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_easylist.py <output_path>")
        sys.exit(1)

    convert(sys.argv[1])
