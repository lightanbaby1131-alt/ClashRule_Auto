import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 多规则源
RULE_SOURCES = {
    "EasyList": "https://easylist.to/easylist/easylist.txt",
    "EasyPrivacy": "https://easylist.to/easylist/easyprivacy.txt",
    "Fanboy Annoyance": "https://easylist-downloads.adblockplus.org/fanboy-annoyance.txt",
    "Fanboy Social": "https://easylist-downloads.adblockplus.org/fanboy-social.txt",
    "AdGuard Base": "https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt",
}

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

def parse_header(text: str):
    version = "Unknown"
    last_modified_raw = None

    for line in text.splitlines()[:30]:
        if line.startswith("! Version:"):
            version = line.replace("! Version:", "").strip()
        if line.startswith("! Last modified:"):
            last_modified_raw = line.replace("! Last modified:", "").strip()

    if last_modified_raw:
        try:
            dt_utc = datetime.strptime(last_modified_raw, "%d %b %Y %H:%M UTC")
            dt_beijing = dt_utc + timedelta(hours=8)
            last_modified = dt_beijing.strftime("%Y年%m月%d日 %H:%M")
        except:
            last_modified = last_modified_raw
    else:
        last_modified = "Unknown"

    return version, last_modified

def convert(outfile: str):
    categorized = {
        "通用广告": set(),
        "追踪器": set(),
        "社交按钮": set(),
    }

    source_info = {}

    for name, url in RULE_SOURCES.items():
        print(f"Downloading {name}...")
        text = requests.get(url, timeout=30).text

        version, last_modified = parse_header(text)
        source_info[name] = {
            "url": url,
            "version": version,
            "last_modified": last_modified,
        }

        current_category = "通用广告"

        for line in text.splitlines():
            current_category = detect_category(line, current_category)
            r = extract_domain(line)
            if r:
                categorized[current_category].add(r)

    total_rules = sum(len(v) for v in categorized.values())

    now = datetime.utcnow() + timedelta(hours=8)
    update_time = now.strftime("%Y年%m月%d日 %H:%M")

    out_lines = [
        "# 内容：广告拦截规则（多源合并版）",
        f"# 总数量：{total_rules} 条",
        f"# 更新时间（北京时间）：{update_time}",
        "",
        "# 规则来源：",
    ]

    for name, info in source_info.items():
        out_lines.append(f"# - {name}")
        out_lines.append(f"#   URL：{info['url']}")
        out_lines.append(f"#   版本：{info['version']}")
        out_lines.append(f"#   更新时间：{info['last_modified']}")
        out_lines.append("#")

    for cat, rules in categorized.items():
        out_lines.append(f"# ===== {cat} =====")
        out_lines.extend(sorted(rules))
        out_lines.append("")

    outfile_path = Path(outfile)
    outfile_path.parent.mkdir(parents=True, exist_ok=True)
    outfile_path.write_text("\n".join(out_lines), encoding="utf-8")

    print(f"Generated {outfile} with {total_rules} rules.")

    Path("commit_message.txt").write_text("Easylist广告拦截规则（多源合并）", encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_easylist.py <output_path>")
        sys.exit(1)

    convert(sys.argv[1])
