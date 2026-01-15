#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests
from datetime import datetime
import os

# -----------------------------
# 1. 规则源定义
# -----------------------------
RULE_SOURCES = {
    "AdGuard.list": [
        "https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt"
    ],
    "Advertising.list": [
        "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
    ],
    "AppPurify.list": [
        "https://raw.githubusercontent.com/AdAway/adaway.github.io/master/hosts.txt"
    ],
    "EasyList.list": [
        "https://easylist.to/easylist/easylist.txt"
    ],
    "BanEasyPrivacy.list": [
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyPrivacy.list",
        "https://raw.githubusercontent.com/easylist/easylist/master/easyprivacy/easyprivacy_general.txt",
        "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.txt",
        "https://raw.githubusercontent.com/blocklistproject/Lists/master/privacy.txt"
    ]
}

# -----------------------------
# 2. OpenClash 可识别域名提取
# -----------------------------
DOMAIN_RE = re.compile(
    r"^(?:\|\|)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:\^)?$"
)

def extract_domains(text):
    domains = set()
    for line in text.splitlines():
        line = line.strip()

        if not line or line.startswith("!") or line.startswith("#"):
            continue

        line = re.sub(r"^(0\.0\.0\.0|127\.0\.0\.1)\s+", "", line)

        m = DOMAIN_RE.match(line)
        if m:
            domains.add(m.group(1).lower())

    return domains

# -----------------------------
# 3. 下载规则
# -----------------------------
def download(url):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.text
    except:
        return ""

# -----------------------------
# 4. 版本号管理
# -----------------------------
def load_version():
    if not os.path.exists("version.txt"):
        with open("version.txt", "w") as f:
            f.write("1.0.0")
        return "1.0.0"

    with open("version.txt", "r") as f:
        return f.read().strip()

def bump_version(version):
    major, minor, patch = map(int, version.split("."))
    patch += 1
    new_version = f"{major}.{minor}.{patch}"
    with open("version.txt", "w") as f:
        f.write(new_version)
    return new_version

# -----------------------------
# 5. 主流程
# -----------------------------
def main():
    version = load_version()
    version = bump_version(version)
    updated_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    all_files_data = {}

    # 下载并处理每个规则文件
    for filename, urls in RULE_SOURCES.items():
        domains = set()
        for url in urls:
            text = download(url)
            domains |= extract_domains(text)
        all_files_data[filename] = domains

    # 文件之间相互去重
    filenames = list(all_files_data.keys())
    for i in range(len(filenames)):
        for j in range(len(filenames)):
            if i != j:
                all_files_data[filenames[i]] -= all_files_data[filenames[j]]

    # 写入最终 .list 文件
    for filename, domains in all_files_data.items():
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Version: {version}\n")
            f.write(f"# Updated: {updated_time}\n\n")
            for d in sorted(domains):
                f.write(d + "\n")

    print(f"规则构建完成，版本号 {version}，更新时间 {updated_time}")

if __name__ == "__main__":
    main()
