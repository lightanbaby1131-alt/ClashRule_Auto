import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re

# -----------------------------
# 全球直连规则源（已补充 GitHub 最权威规则）
# -----------------------------
DIRECT_SOURCES = {
    "LocalAreaNetwork": [
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/LocalAreaNetwork.list",
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Lan/Lan.list",
    ],
    "UnBan": [
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/UnBan.list",
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Direct/Direct.list",
        "https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/direct.txt",
    ]
}

# 可选：你可以在这里补充自己的直连域名
EXTRA_DIRECT = {
    "LocalAreaNetwork": [],
    "UnBan": [],
}

OUTPUT_DIR = Path("Clash/Ruleset/Direct")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TMP_DIR = Path(".github/tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)


def now_bj():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y年%m月%d日 %H:%M")


def fetch(url):
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.text.splitlines()


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


def main():
    for group, urls in DIRECT_SOURCES.items():
        domains = set()

        for url in urls:
            try:
                lines = fetch(url)
            except:
                continue

            for line in lines:
                d = extract_domain(line)
                if d:
                    domains.add(d.lower())

        for d in EXTRA_DIRECT.get(group, []):
            domains.add(d.lower())

        tmp_file = TMP_DIR / f"{group}.txt"
        tmp_file.write_text("\n".join(sorted(domains)), encoding="utf-8")

        output_file = OUTPUT_DIR / f"{group}.list"

        header = [
            f"# 内容：{group} 全球直连规则（自动合并 + 去重）",
            f"# 总数量：{len(domains)} 条",
            f"# 更新时间（北京时间）：{now_bj()}",
            "",
        ]

        rules = [f"DOMAIN-SUFFIX,{d}" for d in sorted(domains)]
        output_file.write_text("\n".join(header + rules), encoding="utf-8")


if __name__ == "__main__":
    main()
