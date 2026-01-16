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

TMP_DIR = ".github/tmp"
OUTPUT_DIR = "Clash/Ruleset/AD"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "EasyList.list")

EXISTING_RULE_URL = "https://raw.githubusercontent.com/lightanbaby1131-alt/Online-Clash/refs/heads/main/Ruleset/Advertising.list"

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
    {
        "name": "CJXList (EasyList China)",
        "url": "https://raw.githubusercontent.com/cjx82630/cjxlist/master/cjx-ublock.txt",
    },
]

# 广告相关 keyword 白名单（只从非常确定的场景中提取）
AD_KEYWORD_WHITELIST = {
    "ad", "ads", "adserver", "advert", "advertising",
    "track", "tracking", "analytics", "stat", "stats",
    "banner", "doubleclick", "click", "impression",
}


# ---------------- 工具函数 ----------------

def safe_request(url: str) -> str:
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
    if os.path.isdir(TMP_DIR):
        shutil.rmtree(TMP_DIR, ignore_errors=True)


def extract_last_modified(lines) -> str:
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


def is_cosmetic_or_script_filter(line: str) -> bool:
    if "##" in line or "#@#" in line or "#?#" in line or "#$#" in line:
        return True
    if "::" in line or ":style(" in line or ":has(" in line or "##+" in line:
        return True
    return False


def is_regex_rule(line: str) -> bool:
    return line.startswith("/") and line.endswith("/") and len(line) > 2


def contains_resource_suffix(line: str) -> bool:
    # 常见静态资源后缀，基本都是路径规则
    return any(ext in line.lower() for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".mp4", ".js", ".css"))


def contains_size_pattern(line: str) -> bool:
    # 匹配常见广告尺寸：160x600, 300x250, 728x90 等
    return re.search(r"\b\d{2,4}x\d{2,4}\b", line) is not None


def is_ip(s: str) -> bool:
    # 简单 IPv4 检测
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", s):
        parts = s.split(".")
        return all(0 <= int(p) <= 255 for p in parts)
    # IPv6 直接忽略
    if ":" in s:
        return True
    return False


def is_valid_domain(domain: str) -> bool:
    domain = domain.strip().lower()
    # 必须包含点
    if "." not in domain:
        return False
    # 不能是 IP
    if is_ip(domain):
        return False
    # 不能包含非法字符
    if not re.fullmatch(r"[a-z0-9.-]+", domain):
        return False
    # 每一段不能以 - 开头或结尾
    labels = domain.split(".")
    for label in labels:
        if not label:
            return False
        if label[0] == "-" or label[-1] == "-":
            return False
    # 不允许整体以数字开头（避免尺寸/奇怪 host）
    if labels[0][0].isdigit():
        return False
    return True


def extract_domain_from_url_like(pattern: str) -> str | None:
    # 去掉前导 | 或 @|
    pattern = pattern.lstrip("|@")
    # 去掉协议
    pattern = re.sub(r"^https?://", "", pattern, flags=re.IGNORECASE)
    # 截断到第一个 / 或 ^
    pattern = re.split(r"[\/^]", pattern, 1)[0]
    candidate = pattern.strip().lower()
    if is_valid_domain(candidate):
        return candidate
    return None


def extract_domain_from_double_pipe(line: str) -> str | None:
    # ||example.com^ 形式
    body = line[2:]
    body = re.split(r"[\^/|]", body, 1)[0]
    candidate = body.strip().lower()
    if is_valid_domain(candidate):
        return candidate
    return None


def extract_bare_domain(line: str) -> str | None:
    candidate = line.strip().lower()
    if is_valid_domain(candidate):
        return candidate
    return None


def extract_safe_keyword_from_path(line: str) -> str | None:
    """
    只从非常有限的场景中提取 keyword：
    - 只看路径片段
    - 必须在 AD_KEYWORD_WHITELIST 中
    - 不包含数字/点/下划线/连字符
    """
    # 提取路径部分（去掉协议和域名）
    tmp = line
    tmp = tmp.lstrip("|@")
    tmp = re.sub(r"^https?://", "", tmp, flags=re.IGNORECASE)
    # 去掉域名部分
    parts = tmp.split("/", 1)
    if len(parts) == 1:
        return None
    path = parts[1]

    tokens = re.split(r"[^A-Za-z0-9]+", path)
    for t in tokens:
        t = t.strip().lower()
        if not t:
            continue
        if t in AD_KEYWORD_WHITELIST and re.fullmatch(r"[a-z]+", t):
            return t
    return None


def convert_line_to_rules(line: str) -> list[str]:
    """
    极度保守的转换逻辑：
    1. 优先提取确定的域名（DOMAIN-SUFFIX / DOMAIN）
    2. 仅在非常有限场景下提取 DOMAIN-KEYWORD
    """
    line = line.strip()
    results: list[str] = []

    # 白名单规则 @@ 开头：不提取，避免误杀
    if line.startswith("@@"):
        return results

    # 1. ||example.com^ 形式
    if line.startswith("||"):
        domain = extract_domain_from_double_pipe(line)
        if domain:
            results.append(f"DOMAIN-SUFFIX,{domain}")
        return results

    # 2. |https://example.com^ 形式
    if line.startswith("|"):
        domain = extract_domain_from_url_like(line)
        if domain:
            results.append(f"DOMAIN,{domain}")
        else:
            # 尝试从路径中提取安全 keyword（极少量）
            kw = extract_safe_keyword_from_path(line)
            if kw:
                results.append(f"DOMAIN-KEYWORD,{kw}")
        return results

    # 3. 裸域名
    bare_domain = extract_bare_domain(line)
    if bare_domain:
        results.append(f"DOMAIN-SUFFIX,{bare_domain}")
        return results

    # 4. 其他复杂规则：只在极少数情况下提取 keyword
    # 例如 */track/*, */analytics/*
    kw = extract_safe_keyword_from_path(line)
    if kw:
        results.append(f"DOMAIN-KEYWORD,{kw}")

    return results


def parse_adblock_list(text: str) -> tuple[set[str], str]:
    lines = text.splitlines()
    last_modified = extract_last_modified(lines)
    rules: set[str] = set()

    for raw in lines:
        line = raw.strip()
        if is_comment_or_empty(line):
            continue
        if is_cosmetic_or_script_filter(line):
            continue
        if is_regex_rule(line):
            continue
        if contains_resource_suffix(line):
            continue
        if contains_size_pattern(line):
            continue

        converted = convert_line_to_rules(line)
        for r in converted:
            rules.add(r)

    return rules, last_modified


def load_existing_rules(url: str) -> set[str]:
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

    for src in SOURCES:
        name = src["name"]
        url = src["url"]
        print(f"[INFO] 下载规则源: {name} -> {url}")
        text = safe_request(url)
        if not text:
            print(f"[WARN] 规则源为空，跳过: {name}")
            continue

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

    existing_rules = load_existing_rules(EXISTING_RULE_URL)
    print(f"[INFO] 已有 Advertising.list 规则数量: {len(existing_rules)}")

    final_rules = sorted(all_rules - existing_rules)
    print(f"[INFO] 去重后最终规则数量: {len(final_rules)}")

    # 更新时间固定为“当天北京时间 02:02”
    now_cn = datetime.now(ZoneInfo("Asia/Shanghai")).replace(hour=2, minute=2)
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
    header_lines.append("# 说明: 本规则仅保守提取域名相关规则，尽量避免误杀与误提取。")
    header_lines.append("")

    domain_suffix_rules = [r for r in final_rules if r.startswith("DOMAIN-SUFFIX,")]
    domain_rules = [r for r in final_rules if r.startswith("DOMAIN,")]
    keyword_rules = [r for r in final_rules if r.startswith("DOMAIN-KEYWORD,")]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in header_lines:
            f.write(line + "\n")

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
    cleanup_tmp()
    print("[INFO] 已清理临时文件目录 .github/tmp")


if __name__ == "__main__":
    main()
