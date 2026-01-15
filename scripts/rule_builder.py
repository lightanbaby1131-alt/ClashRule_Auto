#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests

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

        # 跳过注释
        if not line or line.startswith("!") or line.startswith("#"):
            continue

        # 去掉 hosts 格式
        line = re.sub(r"^(0\.0\.0\.0|127\.0\.0\.1)\s+", "", line)

        # 匹配域名
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
# 4. 主流程：下载 → 提取 → 去重 → 生成文件
# -----------------------------
def main():
    all_files_data = {}

    # 下载并处理每个规则文件
    for filename, urls in RULE_SOURCES.items():
        domains = set()
        for url in urls:
            text = download(url)
            domains |= extract_domains(text)
        all_files_data[filename] = domains

    # -----------------------------
    # 5. 文件之间相互去重
    # -----------------------------
    filenames = list(all_files_data.keys())

    for i in range(len(filenames)):
        for j in range(len(filenames)):
            if i != j:
                all_files_data[filenames[i]] -= all_files_data[filenames[j]]

    # -----------------------------
    # 6. 写入最终 .list 文件
    # -----------------------------
    for filename, domains in all_files_data.items():
        with open(filename, "w", encoding="utf-8") as f:
            for d in sorted(domains):
                f.write(d + "\n")

    print("规则构建完成，共生成 5 个 .list 文件。")

if __name__ == "__main__":
    main()
