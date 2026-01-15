#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests
from datetime import datetime
import os

# -----------------------------
# 1. 规则源定义（5 个 .list）
# -----------------------------
RULE_SOURCES = {
    # 广告过滤（AdGuard DNS 规则）
    "AdGuard.list": [
        "https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt"
    ],
    # 综合广告域名（StevenBlack hosts）
    "Advertising.list": [
        "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
    ],
    # App 级广告屏蔽（AdAway）
    "AppPurify.list": [
        "https://raw.githubusercontent.com/AdAway/adaway.github.io/master/hosts.txt"
    ],
    # EasyList 主规则
    "EasyList.list": [
        "https://easylist.to/easylist/easylist.txt"
    ],
    # 隐私防护（BanEasyPrivacy 聚合）
    "BanEasyPrivacy.list": [
        # 你提供的 ACL4SSR 隐私规则
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyPrivacy.list",
        # EasyPrivacy（隐私规则）
        "https://raw.githubusercontent.com/easylist/easylist/master/easyprivacy/easyprivacy_general.txt",
        # Hagezi 隐私/广告增强规则
        "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.txt",
        # BlocklistProject 隐私规则
        "https://raw.githubusercontent.com/blocklistproject/Lists/master/privacy.txt"
    ]
}

# 每个文件的描述，用于写入头部注释，作为“最后提交信息”的区分
FILE_DESCRIPTIONS = {
    "AdGuard.list": "AdGuard DNS 广告过滤规则（去重后专属域名集合）。",
    "Advertising.list": "综合广告域名规则（基于 StevenBlack hosts，去重后专属域名集合）。",
    "AppPurify.list": "App 级广告屏蔽规则（基于 AdAway，去重后专属域名集合）。",
    "EasyList.list": "EasyList 主规则转换的域名列表（去重后专属域名集合）。",
    "BanEasyPrivacy.list": "隐私防护聚合规则（BanEasyPrivacy + 多源隐私列表，去重后专属域名集合）。"
}

# -----------------------------
# 2. OpenClash 可识别域名提取
# -----------------------------
DOMAIN_RE = re.compile(
    r"^(?:\|\|)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:\^)?$"
)

def extract_domains(text: str) -> set:
    domains = set()
    for line in text.splitlines():
        line = line.strip()

        # 注释或空行跳过
        if not line or line.startswith("!") or line.startswith("#"):
            continue

        # hosts 格式前缀去掉
        line = re.sub(r"^(0\.0\.0\.0|127\.0\.0\.1)\s+", "", line)

        # 只保留域名
        m = DOMAIN_RE.match(line)
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
    except Exception:
        return ""

# -----------------------------
# 4. 版本号管理（version.txt）
# -----------------------------
VERSION_FILE = "version.txt"

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
    # 版本号与更新时间
    version = load_version()
    version = bump_version(version)
    updated_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    all_files_data: dict[str, set] = {}

    # 1）下载并处理每个规则文件
    for filename, urls in RULE_SOURCES.items():
        domains = set()
        for url in urls:
            text = download(url)
            if not text:
                continue
            domains |= extract_domains(text)
        all_files_data[filename] = domains

    # 2）文件之间相互去重（按优先级顺序）
    #    前面的文件优先级高，后面的文件会剔除前面已经包含的域名
    ordered_files = list(RULE_SOURCES.keys())
    for i, fname in enumerate(ordered_files):
        current_set = all_files_data[fname]
        # 从当前集合中减去所有“在它之前的文件”中的域名
        for prev_fname in ordered_files[:i]:
            current_set -= all_files_data[prev_fname]
        all_files_data[fname] = current_set

    # 3）写入最终 .list 文件
    for filename in ordered_files:
        domains = all_files_data.get(filename, set())
        description = FILE_DESCRIPTIONS.get(filename, "").strip()

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# File: {filename}\n")
            if description:
                f.write(f"# Description: {description}\n")
            f.write(f"# Version: {version}\n")
            f.write(f"# Updated: {updated_time}\n")
            f.write("# Format: 一行一个域名，OpenClash 可识别。\n")
            f.write("\n")
            for d in sorted(domains):
                f.write(d + "\n")

    print("规则构建完成：")
    for fname in ordered_files:
        print(f"  - {fname}: {len(all_files_data.get(fname, []))} 条域名")
    print(f"版本号 {version}，更新时间 {updated_time}")

if __name__ == "__main__":
    main()
