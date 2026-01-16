import os
import shutil
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# 源规则地址
SOURCES = {
    "BanAD": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/refs/heads/master/Clash/BanAD.list",
    "BanEasyList": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/refs/heads/master/Clash/BanEasyList.list",
    "BanEasyListChina": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/refs/heads/master/Clash/BanEasyListChina.list",
    "BanEasyPrivacy": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/refs/heads/master/Clash/BanEasyPrivacy.list",
}

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".github", "tmp")
OUTPUT_DIR = os.path.join(BASE_DIR, "Clash", "Ruleset", "AD")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "BanAD.list")


def ensure_dirs():
    os.makedirs(TMP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_source(name, url):
    """下载源规则并保存到临时文件，返回文件路径和可能的更新时间信息"""
    print(f"Fetching {name} from {url}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    tmp_path = os.path.join(TMP_DIR, f"{name}.list")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(resp.text)

    # 尝试从内容中解析更新时间（如果有）
    last_update = None
    for line in resp.text.splitlines():
        l = line.strip()
        if not l.startswith("#"):
            continue
        # 常见格式尝试匹配
        if "Last Modified" in l or "Last Update" in l or "更新时间" in l:
            last_update = l.lstrip("#").strip()
            break

    return tmp_path, last_update


def parse_rules_from_file(path):
    """只提取 OpenClash 可识别的安全规则行，避免误杀"""
    valid_prefixes = ("DOMAIN-SUFFIX,", "DOMAIN,", "DOMAIN-KEYWORD,")
    rules = {
        "DOMAIN-SUFFIX": set(),
        "DOMAIN": set(),
        "DOMAIN-KEYWORD": set(),
    }

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # 只保留标准三种前缀
            if line.startswith(valid_prefixes):
                parts = line.split(",", 1)
                if len(parts) != 2:
                    continue
                rule_type, value = parts[0].strip(), parts[1].strip()
                if not value:
                    continue

                # 简单过滤明显非域名/关键字的内容，降低误杀
                if "://" in value or "/" in value or " " in value:
                    continue

                if rule_type in rules:
                    rules[rule_type].add(value)

    return rules


def merge_rules(all_rules_list):
    merged = {
        "DOMAIN-SUFFIX": set(),
        "DOMAIN": set(),
        "DOMAIN-KEYWORD": set(),
    }
    for rules in all_rules_list:
        for k in merged.keys():
            merged[k].update(rules.get(k, set()))
    return merged


def build_header(now_cn, source_updates, total_count):
    """
    生成文件头部注释：
    - EasyList.list广告拦截规则
    - 更新时间（北京时间）
    - 原规则来源
    - 原规则更新时间（有几个写几个）
    - 规则总数量
    """
    lines = []
    lines.append("# EasyList.list广告拦截规则")
    lines.append(f"# 更新时间：{now_cn.strftime('%Y年%m月%d日 %H:%M')}（北京时间）")
    lines.append("# 原规则来源：")
    for name, url in SOURCES.items():
        lines.append(f"#   {name}: {url}")

    lines.append("# 原规则更新时间：")
    for name, info in source_updates.items():
        if info:
            lines.append(f"#   {name}: {info}")
        else:
            lines.append(f"#   {name}: 未提供")

    lines.append(f"# 规则总数量：{total_count}")
    lines.append("")  # 空行分隔
    return "\n".join(lines)


def write_output(merged_rules, source_updates):
    # 统计总数量
    total_count = sum(len(v) for v in merged_rules.values())

    # 当前北京时间
    now_cn = datetime.now(ZoneInfo("Asia/Shanghai"))

    header = build_header(now_cn, source_updates, total_count)

    # 尽量提高可读性：按类型分块 + 排序
    lines = [header]

    if merged_rules["DOMAIN-SUFFIX"]:
        lines.append("# ===== DOMAIN-SUFFIX 规则 =====")
        for v in sorted(merged_rules["DOMAIN-SUFFIX"]):
            lines.append(f"DOMAIN-SUFFIX,{v}")
        lines.append("")

    if merged_rules["DOMAIN"]:
        lines.append("# ===== DOMAIN 规则 =====")
        for v in sorted(merged_rules["DOMAIN"]):
            lines.append(f"DOMAIN,{v}")
        lines.append("")

    if merged_rules["DOMAIN-KEYWORD"]:
        lines.append("# ===== DOMAIN-KEYWORD 规则 =====")
        for v in sorted(merged_rules["DOMAIN-KEYWORD"]):
            lines.append(f"DOMAIN-KEYWORD,{v}")
        lines.append("")

    content = "\n".join(lines).rstrip() + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Wrote merged rules to {OUTPUT_FILE} with {total_count} entries.")


def cleanup_tmp():
    """删除所有临时文件目录 .github/tmp/"""
    if os.path.isdir(TMP_DIR):
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        print(f"Temporary directory {TMP_DIR} removed.")


def main():
    ensure_dirs()

    all_rules = []
    source_updates = {}

    try:
        for name, url in SOURCES.items():
            tmp_path, last_update = fetch_source(name, url)
            source_updates[name] = last_update
            rules = parse_rules_from_file(tmp_path)
            all_rules.append(rules)

        merged = merge_rules(all_rules)
        write_output(merged, source_updates)
    finally:
        # 无论成功与否都尝试清理临时文件
        cleanup_tmp()


if __name__ == "__main__":
    main()
