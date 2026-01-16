#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ---------------- 基本配置 ----------------

# 临时文件目录
TMP_DIR = ".github/tmp"
# 输出目录与文件
OUTPUT_DIR = "Clash/Ruleset/AD"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "EasyList.list")

# 需要排重的已有规则文件（避免重复）
EXISTING_RULE_URL = "https://raw.githubusercontent.com/lightanbaby1131-alt/Online-Clash/refs/heads/main/Ruleset/Advertising.list"

# EasyList 系列规则源（可按需增减）
# 这些 URL 来自 EasyList 官方及其 GitHub 仓库/订阅地址
SOURCES = [
    {
        "name": "EasyList",
        "url": "https://easylist-downloads.adblockplus.org/easylist.txt",
    },
    {
        "name": "EasyPrivacy",
        "url": "https://easylist-downloads.adblockplus.org/easyprivacy.txt",
    },
    {
        "name": "Fanboy's Social",
        "url": "https://easylist-downloads.adblockplus.org/fanboy-social.txt",
    },
    # 中文规则：EasyList China / CJXList
    {
        "name": "CJXList (EasyList China)",
        "url": "https://raw.githubusercontent.com/cjx82630/cjxlist/master/cjx-ublock.txt",
    },
]


# ---------------- 工具函数 ----------------

def safe_request(url: str) -> str:
    """下载文本内容，返回字符串。"""
    headers = {"User-Agent": "Mozilla/5.0 (GitHub Actions EasyList Converter)"}
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=60) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="ignore")
    except (URLError, HTTPError) as e:
        print(f"[WARN] 下载失败: {url} -> {e}")
        return ""


def ensure_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def cleanup_tmp() -> None:
    """删除临时目录及其内容。"""
    if os.path.isdir(TMP_DIR):
        shutil.rmtree(TMP_DIR, ignore_errors=True)


def extract_last_modified(lines) -> str:
    """
    从规则文件注释中提取“Last modified/Last updated”等信息。
    常见格式：! Last modified: 2025-01-01 10:00 UTC
    """
    pattern = re.compile(r"^\s*[!#]\s*(Last\s+(modified|updated)\s*:\s*)(.+)$", re.IGNORECASE)
    for line in lines:
        m = pattern.match(line)
        if m:
            return m.group(3).strip()
    return "未知"


def is_comment_or_empty(line: str) -> bool:
    line = line.strip()
    if not line:
        return True
    if line.startswith(("!", "#", "[", ";")):
        return True
    return False


def is_cosmetic_filter(line: str) -> bool:
    """
    过滤掉元素隐藏/脚本规则等（避免误杀）：
    - ##, #@#, #?#, #$#, :style, :has, :matches-css 等
    """
    if "##" in line or "#@#" in line or "#?#" in line or "#$#" in line:
        return True
    # 简单排除明显的 CSS / 脚本规则
    if "::" in line or ":style(" in line or ":has(" in line or "##+" in line:
        return True
    return False


def extract_hostname_from_url_pattern(pattern: str) -> str | None:
    """
    从类似 |https://example.com^ 或 http://example.com/path 的规则中提取域名。
    只在域名部分是“干净”的情况下使用，避免误杀。
    """
    # 去掉前导的 | 或 @|
    pattern = pattern.lstrip("|@")
    # 去掉协议
    pattern = re.sub(r"^https?://", "", pattern)
    # 截断到第一个 / 或 ^
    pattern = re.split(r"[\/^]", pattern, 1)[0]
    hostname = pattern.strip()
    # 只接受由字母数字、点、连字符组成的域名
    if re.fullmatch(r"[A-Za-z0-9.-]+", hostname) and "." in hostname:
        return hostname.lower()
    return None


def convert_adblock_rule_to_domains(line: str) -> list[str]:
    """
    将 Adblock 规则行转换为 OpenClash 可识别的域名规则：
    - DOMAIN-SUFFIX,example.com
    - DOMAIN,example.com
    - DOMAIN-KEYWORD,keyword
    为避免误杀，策略尽量保守。
    """
    line = line.strip()
    results: list[str] = []

    # 1. 以 || 开头的典型域名/域名后缀规则
    if line.startswith("||"):
        # 形如 ||example.com^
        body = line[2:]
        # 去掉尾部的 ^ 或其他分隔符
        body = re.split(r"[\^/|]", body, 1)[0]
        body = body.strip()
        if re.fullmatch(r"[A-Za-z0-9.-]+", body) and "." in body:
            # 直接作为域名后缀
            results.append(f"DOMAIN-SUFFIX,{body.lower()}")
        return results

    # 2. 以单竖线开头的 URL 规则（|https://example.com^）
    if line.startswith("|"):
        hostname = extract_hostname_from_url_pattern(line)
        if hostname:
            results.append(f"DOMAIN,{hostname}")
        return results

    # 3. 不带前缀的纯域名/主机名（极少数规则会这样写）
    if re.fullmatch(r"[A-Za-z0-9.-]+", line) and "." in line:
        results.append(f"DOMAIN-SUFFIX,{line.lower()}")
        return results

    # 4. 带通配符的规则，尝试提取“安全”的关键字作为 DOMAIN-KEYWORD
    # 例如：*adserver.example.com^ -> 关键字 adserver.example.com
    if "*" in line or "^" in line:
        # 提取中间的“干净”片段
        tokens = re.split(r"[\^\*\|/]", line)
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            # 只接受较“干净”的 token，避免误杀
            if re.fullmatch(r"[A-Za-z0-9.-]+", token) and len(token) >= 4:
                # 如果看起来像域名
                if "." in token:
                    results.append(f"DOMAIN-SUFFIX,{token.lower()}")
                else:
                    results.append(f"DOMAIN-KEYWORD,{token.lower()}")
                break
        return results

    # 其他复杂规则（如正则、脚本）直接忽略，避免误杀
    return results


def parse_adblock_list(text: str) -> tuple[set[str], str]:
    """
    解析 Adblock 规则列表，返回：
    - 转换后的 OpenClash 规则集合
    - 原规则“Last modified/Last updated”信息（若有）
    """
    lines = text.splitlines()
    last_modified = extract_last_modified(lines)
    rules: set[str] = set()

    for raw in lines:
        line = raw.strip()
        if is_comment_or_empty(line):
            continue
        if is_cosmetic_filter(line):
            continue
        # 忽略正则规则（以 / 开头和结尾）
        if line.startswith("/") and line.endswith("/"):
            continue

        converted = convert_adblock_rule_to_domains(line)
        for r in converted:
            rules.add(r)

    return rules, last_modified


def load_existing_rules(url: str) -> set[str]:
    """加载已有的 Advertising.list，用于去重。"""
    text = safe_request(url)
    existing: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        existing.add(line)
    return existing


# ---------------- 主流程 ----------------

def main() -> None:
    ensure_dir(TMP_DIR)
    ensure_dir(OUTPUT_DIR)

    all_rules: set[str] = set()
    source_meta: list[dict] = []

    # 1. 下载并解析各个规则源
    for src in SOURCES:
        name = src["name"]
        url = src["url"]
        print(f"[INFO] 下载规则源: {name} -> {url}")
        text = safe_request(url)
        if not text:
            print(f"[WARN] 规则源为空，跳过: {name}")
            continue

        # 保存临时文件（可选，仅用于调试）
        tmp_path = os.path.join(TMP_DIR, f"{name.replace(' ', '_')}.txt")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(text)

        rules, last_modified = parse_adblock_list(text)
        print(f"[INFO] {name} 转换得到规则数量: {len(rules)}")

        all_rules.update(rules)
        source_meta.append(
            {
                "name": name,
                "url": url,
                "last_modified": last_modified,
                "count": len(rules),
            }
        )

    print(f"[INFO] 合并后规则总数（未去重已有 Advertising.list）: {len(all_rules)}")

    # 2. 加载已有 Advertising.list，进行去重
    existing_rules = load_existing_rules(EXISTING_RULE_URL)
    print(f"[INFO] 已有 Advertising.list 规则数量: {len(existing_rules)}")

    final_rules = sorted(all_rules - existing_rules)
    print(f"[INFO] 去重后最终规则数量: {len(final_rules)}")

    # 3. 生成头部注释
    # 使用北京时间（Asia/Shanghai）作为更新时间
    now_cn = datetime.now(ZoneInfo("Asia/Shanghai"))
    update_time_str = now_cn.strftime("%Y年%m月%d日 %H:%M")

    header_lines: list[str] = []
    header_lines.append("# EasyList.list广告拦截规则")
    header_lines.append(f"# 更新时间: {update_time_str}")
    header_lines.append("# 原规则来源:")
    for meta in source_meta:
        header_lines.append(f"#   - {meta['name']}: {meta['url']}")
    header_lines.append("# 原规则更新时间:")
    for meta in source_meta:
        header_lines.append(f"#   - {meta['name']}: {meta['last_modified']}")
    header_lines.append(f"# 规则总数量: {len(final_rules)}")
    header_lines.append("# 说明: 本规则仅保守提取域名相关规则，尽量避免误杀。")
    header_lines.append("")

    # 4. 可选分类：按规则类型简单分组，提高可读性
    domain_suffix_rules = [r for r in final_rules if r.startswith("DOMAIN-SUFFIX,")]
    domain_rules = [r for r in final_rules if r.startswith("DOMAIN,")]
    keyword_rules = [r for r in final_rules if r.startswith("DOMAIN-KEYWORD,")]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        # 写入头部
        for line in header_lines:
            f.write(line + "\n")

        # 分类写入
        if domain_suffix_rules:
            f.write("# ===== DOMAIN-SUFFIX 规则 =====\n")
            for r in domain_suffix_rules:
                f.write(r + "\n")
            f.write("\n")

        if domain_rules:
            f.write("# ===== DOMAIN 规则 =====\n")
            for r in domain_rules:
                f.write(r + "\n")
            f.write("\n")

        if keyword_rules:
            f.write("# ===== DOMAIN-KEYWORD 规则 =====\n")
            for r in keyword_rules:
                f.write(r + "\n")
            f.write("\n")

    print(f"[INFO] 已生成: {OUTPUT_FILE}")

    # 5. 删除临时文件目录
    cleanup_tmp()
    print("[INFO] 已清理临时文件目录 .github/tmp")


if __name__ == "__main__":
    main()
