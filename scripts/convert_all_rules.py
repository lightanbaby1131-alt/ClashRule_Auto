import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re
from urllib.parse import urlparse

# -----------------------------
# 规则源定义（广告 + 应用净化）
# -----------------------------
SOURCES = {
    "EasyList": [
        ("EasyList", "https://easylist.to/easylist/easylist.txt"),
        ("ACL4SSR_BanAD", "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanAD.list"),
    ],
    "AdGuard": [
        ("AdGuard_Base", "https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt"),
        ("AdGuard_DNS_Filter", "https://adguardteam.github.io/AdGuardSDNSFilter/Filters/rules.txt"),
    ],
    "Advertising": [
        ("Advertising", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Advertising/Advertising.list")
    ],
    "AppPurify": [
        ("ACL4SSR_BanProgramAD", "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanProgramAD.list"),
        ("ACL4SSR_BanEasyList", "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyList.list"),
        ("ACL4SSR_BanEasyListChina", "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyListChina.list"),
        ("ACL4SSR_BanEasyPrivacy", "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyPrivacy.list"),
        ("BM_AdBlock", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/AdBlock/AdBlock.list"),
        ("BM_VideoAds", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/VideoAds/VideoAds.list"),
        ("BM_App", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/App/App.list"),
        ("CatsTeam_DNS", "https://raw.githubusercontent.com/Cats-Team/AdRules/main/dns.txt"),
        ("CatsTeam_App", "https://raw.githubusercontent.com/Cats-Team/AdRules/main/app.txt"),
    ]
}

# 输出路径
OUTPUT_DIR = Path("Clash/Ruleset/AD")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILES = {
    "EasyList": OUTPUT_DIR / "EasyList.list",
    "AdGuard": OUTPUT_DIR / "AdGuard.list",
    "Advertising": OUTPUT_DIR / "Advertising.list",
    "AppPurify": OUTPUT_DIR / "AppPurify.list",
}

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


def extract_domain(line):
    line = line.strip()

    if not line or line.startswith("!") or line.startswith("@@"):
        return None
    if "##" in line or "#@" in line:
        return None

    if line.startswith("||"):
        d = re.split(r"[\^/]", line[2:], 1)[0]
        return d if "." in d else None

    if line.startswith("|http"):
        try:
            host = urlparse(line.lstrip("|")).hostname
            return host if host and "." in host else None
        except:
            return None

    if line.startswith("DOMAIN-SUFFIX,"):
        return line.split(",", 1)[1].strip()

    if line.startswith("DOMAIN,"):
        return line.split(",", 1)[1].strip()

    if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", line):
        return line

    return None


def extract_group(group_name, sources):
    domains = set()

    for name, url in sources:
        try:
            lines = fetch(url)
        except:
            continue

        for line in lines:
            d = extract_domain(line)
            if d:
                domains.add(d.lower())

    tmp_file = TMP_DIR / f"{group_name}.txt"
    tmp_file.write_text("\n".join(sorted(domains)), encoding="utf-8")

    return domains


# -----------------------------
# 主逻辑
# -----------------------------
def main():
    groups = {}

    # 读取四组规则
    for group_name, src in SOURCES.items():
        groups[group_name] = extract_group(group_name, src)

    # -----------------------------
    # 四组文件互相去重
    # -----------------------------
    groups["AdGuard"] -= groups["EasyList"]
    groups["Advertising"] -= groups["EasyList"] | groups["AdGuard"]
    groups["AppPurify"] -= groups["EasyList"] | groups["AdGuard"] | groups["Advertising"]

    # -----------------------------
    # 写入四个最终文件
    # -----------------------------
    for group_name, domains in groups.items():
        path = OUTPUT_FILES[group_name]

        header = [
            f"# 内容：{group_name} 规则（自动合并 + 去重）",
            f"# 总数量：{len(domains)} 条",
            f"# 更新时间（北京时间）：{now_bj()}",
            "",
        ]

        rules = [f"DOMAIN-SUFFIX,{d}" for d in sorted(domains)]
        path.write_text("\n".join(header + rules), encoding="utf-8")


if __name__ == "__main__":
    main()
