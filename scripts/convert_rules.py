import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re
from urllib.parse import urlparse

# -----------------------------
# 规则源定义
# -----------------------------
SOURCES = {
    "easylist_group": [
        ("EasyList", "https://easylist.to/easylist/easylist.txt"),
        ("ACL4SSR BanAD", "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/refs/heads/master/Clash/BanAD.list"),
    ],
    "adguard_group": [
        ("AdGuard Base", "https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt"),
        ("AdGuard Mobile", "https://adguardteam.github.io/AdGuardSDNSFilter/Filters/mobile.txt"),
        ("AdGuard Tracking", "https://adguardteam.github.io/AdGuardSDNSFilter/Filters/tracking.txt"),
    ],
    "advertising_group": [
        ("Advertising", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/Clash/Advertising/Advertising.list")
    ]
}

# 输出路径
OUTPUT_EASYLIST = Path("Clash/Ruleset/AD/EasyList.list")
OUTPUT_ADGUARD = Path("Clash/Ruleset/AD/AdGuard.list")
OUTPUT_ADVERTISING = Path("Clash/Ruleset/AD/Advertising.list")

# 临时目录（必须全部放这里）
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
    if "##" in line or "#@" in line:
        return None

    # EasyList: ||domain.com^
    if line.startswith("||"):
        d = re.split(r"[\^/]", line[2:], 1)[0]
        return d if "." in d else None

    # EasyList: |https://domain.com
    if line.startswith("|http"):
        try:
            host = urlparse(line.lstrip("|")).hostname
            return host if host and "." in host else None
        except:
            return None

    # Clash: DOMAIN-SUFFIX,domain.com
    if line.startswith("DOMAIN-SUFFIX,"):
        d = line.split(",", 1)[1].strip()
        return d if "." in d else None

    # Clash: DOMAIN,domain.com
    if line.startswith("DOMAIN,"):
        d = line.split(",", 1)[1].strip()
        return d if "." in d else None

    # 纯域名
    if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", line):
        return line

    return None


def extract_domains_from_source(name, url):
    lines = fetch(url)
    domains = set()

    for line in lines:
        d = extract_domain(line)
        if d:
            domains.add(d.lower())

    # 保存临时文件（调试用）
    tmp_file = TMP_DIR / f"{name.replace(' ', '_')}.txt"
    tmp_file.write_text("\n".join(sorted(domains)), encoding="utf-8")

    return domains


# -----------------------------
# 主逻辑
# -----------------------------
def main():
    easylist_domains = set()
    adguard_domains = set()
    advertising_domains = set()

    # EasyList + BanAD
    for name, url in SOURCES["easylist_group"]:
        easylist_domains |= extract_domains_from_source(name, url)

    # AdGuard 三个库
    for name, url in SOURCES["adguard_group"]:
        adguard_domains |= extract_domains_from_source(name, url)

    # Advertising 单独库
    for name, url in SOURCES["advertising_group"]:
        advertising_domains |= extract_domains_from_source(name, url)

    # -----------------------------
    # 全局去重（互斥）
    # -----------------------------
    # EasyList 优先级最高
    adguard_domains -= easylist_domains
    advertising_domains -= easylist_domains
    advertising_domains -= adguard_domains

    # -----------------------------
    # 写入三个 .list 文件
    # -----------------------------
    OUTPUT_EASYLIST.parent.mkdir(parents=True, exist_ok=True)

    def write_list(path, title, domains):
        header = [
            f"# 内容：{title}",
            f"# 总数量：{len(domains)} 条",
            f"# 更新时间（北京时间）：{now_bj()}",
            "",
        ]
        rules = [f"DOMAIN-SUFFIX,{d}" for d in sorted(domains)]
        path.write_text("\n".join(header + rules), encoding="utf-8")

    write_list(OUTPUT_EASYLIST, "EasyList + ACL4SSR BanAD", easylist_domains)
    write_list(OUTPUT_ADGUARD, "AdGuard Base + Mobile + Tracking", adguard_domains)
    write_list(OUTPUT_ADVERTISING, "Advertising", advertising_domains)


if __name__ == "__main__":
    main()
