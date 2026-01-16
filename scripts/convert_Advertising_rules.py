#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
from pathlib import Path
from datetime import datetime

import requests

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore


AD_SOURCE_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/Clash/Advertising/Advertising.list"
BANAD_URL = "https://raw.githubusercontent.com/lightanbaby1131-alt/ClashRule_Auto/refs/heads/main/Clash/Ruleset/AD/BanAD.list"

TMP_DIR = Path(".github/tmp")
OUTPUT_DIR = Path("Clash/Ruleset/AD")
OUTPUT_FILE = OUTPUT_DIR / "Advertising.list"

ALLOWED_PREFIXES = (
    "DOMAIN-SUFFIX,",
    "DOMAIN,",
    "DOMAIN-KEYWORD,",
    "DOMAIN-REGEX,",
)


def ensure_dirs():
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest: Path) -> None:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def extract_updated_time_advertising(path: Path) -> str:
    """
    从 Advertising.list 中提取 "# UPDATED: YYYY-MM-DD HH:MM:SS"
    转换为 "YYYY年MM月DD日 HH:MM（北京时间）"
    """
    updated_raw = None

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "UPDATED:" in line:
                updated_raw = line.split("UPDATED:", 1)[1].strip()
                break

    if not updated_raw:
        return "未知（北京时间）"

    try:
        dt = datetime.strptime(updated_raw, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y年%m月%d日 %H:%M（北京时间）")
    except Exception:
        return updated_raw + "（北京时间）"


def extract_updated_time_banad(path: Path) -> str:
    """
    从 BanAD.list 中提取：
    "# 更新时间：2026年01月16日 12:51（北京时间）"
    """
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "更新时间" in line and "北京时间" in line:
                # 直接返回整段格式
                return line.replace("#", "").replace("更新时间：", "").strip()

    return "未知（北京时间）"


def parse_rules(path: Path) -> list[str]:
    rules: list[str] = []
    seen = set()

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if not line.startswith(ALLOWED_PREFIXES):
                continue

            if line not in seen:
                seen.add(line)
                rules.append(line)

    return rules


def group_rules_by_type(rules: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for r in rules:
        rule_type = r.split(",", 1)[0].strip()
        grouped.setdefault(rule_type, []).append(r)
    return grouped


def build_header(rule_count: int, ad_update: str, banad_update: str) -> str:
    now_cn = datetime.now(ZoneInfo("Asia/Shanghai"))
    update_time_str = now_cn.strftime("%Y年%m月%d日 %H:%M（北京时间）")

    header_lines = [
        "# Advertising广告拦截规则",
        f"# 更新时间：{update_time_str}",
        "# 原规则来源：",
        f"#   1. {AD_SOURCE_URL}",
        f"#   2. 去重排除源：{BANAD_URL}",
        "# 原规则更新时间：",
        f"#   Advertising源：{ad_update}",
        f"#   BanAD源：{banad_update}",
        f"# 规则总数量：{rule_count}",
        "",
    ]
    return "\n".join(header_lines)


def write_output_file(rules: list[str], ad_update: str, banad_update: str) -> None:
    grouped = group_rules_by_type(rules)
    header = build_header(len(rules), ad_update, banad_update)

    lines: list[str] = [header]

    type_order = [
        "DOMAIN-SUFFIX",
        "DOMAIN",
        "DOMAIN-KEYWORD",
        "DOMAIN-REGEX",
    ]

    used_types = set()

    for t in type_order:
        if t in grouped:
            used_types.add(t)
            lines.append(f"# === {t} 规则 ===")
            lines.extend(grouped[t])
            lines.append("")

    for t, rs in grouped.items():
        if t in used_types:
            continue
        lines.append(f"# === {t} 规则 ===")
        lines.extend(rs)
        lines.append("")

    content = "\n".join(lines).rstrip() + "\n"
    OUTPUT_FILE.write_text(content, encoding="utf-8")


def clean_tmp_dir():
    if TMP_DIR.exists():
        for child in TMP_DIR.iterdir():
            if child.is_file() or child.is_symlink():
                try:
                    child.unlink()
                except OSError:
                    pass
            elif child.is_dir():
                try:
                    shutil.rmtree(child)
                except OSError:
                    pass


def main():
    ensure_dirs()

    ad_tmp = TMP_DIR / "Advertising_source.list"
    banad_tmp = TMP_DIR / "BanAD_source.list"

    try:
        download_file(AD_SOURCE_URL, ad_tmp)
        download_file(BANAD_URL, banad_tmp)

        # 提取两个源的更新时间
        ad_update = extract_updated_time_advertising(ad_tmp)
        banad_update = extract_updated_time_banad(banad_tmp)

        ad_rules = parse_rules(ad_tmp)
        banad_rules = set(parse_rules(banad_tmp))

        filtered_rules = [r for r in ad_rules if r not in banad_rules]

        seen = set()
        final_rules: list[str] = []
        for r in filtered_rules:
            if r not in seen:
                seen.add(r)
                final_rules.append(r)

        write_output_file(final_rules, ad_update, banad_update)

    finally:
        clean_tmp_dir()


if __name__ == "__main__":
    main()
