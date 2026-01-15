import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re

# -----------------------------
# 应用净化规则源（已为你精挑细选）
# -----------------------------
APP_SOURCES = {
    "ACL4SSR": [
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanProgramAD.list",
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanAD.list",
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyList.list",
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyListChina.list",
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyPrivacy.list",
    ],
    "blackmatrix7": [
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Advertising/Advertising.list",
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Hijacking/Hijacking.list",
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/AdBlock/AdBlock.list",
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/VideoAds/VideoAds.list",
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/App/App.list",
    ],
    "CatsTeam": [
        "https://raw.githubusercontent.com/Cats-Team/AdRules/main/dns.txt",
        "https://raw.githubusercontent.com/Cats-Team/AdRules/main/app.txt",
    ]
}

OUTPUT = Path("Clash/Ruleset/AppPurify/AppPurify.list")
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
    all_domains = set()

    for group, urls in APP_SOURCES.items():
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

        tmp_file = TMP_DIR / f"{group}.txt"
        tmp_file.write_text("\n".join(sorted(group_set)), encoding="utf-8")

        all_domains |= group_set

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "# 内容：应用广告净化规则（自动合并 + 去重）",
        f"# 总数量：{len(all_domains)} 条",
        f"# 更新时间（北京时间）：{now_bj()}",
        "",
    ]

    rules = [f"DOMAIN-SUFFIX,{d}" for d in sorted(all_domains)]
    OUTPUT.write_text("\n".join(header + rules), encoding="utf-8")


if __name__ == "__main__":
    main()
