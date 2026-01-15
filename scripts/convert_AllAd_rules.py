#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests
from datetime import datetime
import os

# -----------------------------
# 0. 路径设置
# -----------------------------
OUTPUT_DIR = "Clash/Ruleset/AD/"
TMP_DIR = ".github/tmp/"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

VERSION_FILE = os.path.join(TMP_DIR, "version.txt")

# -----------------------------
# 1. 规则源定义（5 个 .list）
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
# 2. Clash/OpenClash 域名提取
# -----------------------------
DOMAIN_RE = re.compile(
    r"(?:\|\|)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:\^)?"
)

def extract_domains(text: str) -> set:
    domains = set()
    for line in text.splitlines():
        line = line.strip()

        if not line or line.startswith("!") or line.startswith("#"):
            continue

        # hosts 格式
        line = re.sub(r"^(0\.0\.0\.0|127\.0\.0\.1)\s+", "", line)

        # Clash 格式（DOMAIN-SUFFIX,xxx）
        if line.startswith("DOMAIN-SUFFIX,"):
            domains.add(line.split(",", 1)[1].strip().lower())
            continue
        if line.startswith("DOMAIN,"):
            domains.add(line.split(",", 1)[1].strip().lower())
            continue

        # Adblock 语法 ||example.com^
        m = DOMAIN_RE.search(line)
        if m:
            domains.add(m.group(1).lower())

    return domains

# -----------------------------
# 3. 下载规则
# -----------------------------
def download(url: str) -> str:
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.text
    except:
        return ""

# -----------------------------
# 4. 版本号管理
# -----------------------------
def load_version() -> str:
    if not os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            f.write("1.0.0")
        return "1.0.0"

    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def bump_version(version: str) -> str:
    major, minor, patch = map(int, version.split("."))
    patch += 1
    new_version = f"{major}.{minor}.{patch}"
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
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

    # 1）下载并处理每个规则文件
    for filename, urls in RULE_SOURCES.items():
        domains = set()
        for url in urls:
            text = download(url)
            if text:
                domains |= extract_domains(text)

        all_files_data[filename] = domains

    # 2）文件之间相互去重（按优先级）
    ordered_files = list(RULE_SOURCES.keys())
    for i, fname in enumerate(ordered_files):
        for prev_fname in ordered_files[:i]:
            all_files_data[fname] -= all_files_data[prev_fname]

    # 3）写入最终 Clash 可识别 .list 文件（DOMAIN-SUFFIX,xxx）
    for filename in ordered_files:
        domains = all_files_data[filename]
        output_path = os.path.join(OUTPUT_DIR, filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# File: {filename}\n")
            f.write(f"# Version: {version}\n")
            f.write(f"# Updated: {updated_time}\n")
            f.write("# Format: DOMAIN-SUFFIX,example.com\n\n")
            for d in sorted(domains):
                f.write(f"DOMAIN-SUFFIX,{d}\n")

    print("规则构建完成：")
    for fname in ordered_files:
        print(f"  - {fname}: {len(all_files_data[fname])} 条域名")
    print(f"版本号 {version}，更新时间 {updated_time}")

if __name__ == "__main__":
    main()
