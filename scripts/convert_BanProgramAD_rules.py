# scripts/convert_BanProgramAD_rules.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
from pathlib import Path
from datetime import datetime

import requests

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore


SOURCE_URL = "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanProgramAD.list"
BANAD_URL = "https://raw.githubusercontent.com/lightanbaby1131-alt/ClashRule_Auto/refs/heads/main/Clash/Ruleset/AD/BanAD.list"
ADVERTISING_URL = "https://raw.githubusercontent.com/lightanbaby1131-alt/ClashRule_Auto/refs/heads/main/Clash/Ruleset/AD/Advertising.list"
ADGUARD_URL = "https://raw.githubusercontent.com/lightanbaby1131-alt/ClashRule_Auto/refs/heads/main/Clash/Ruleset/AD/AdGuardSDNSFilter.list"

TMP_DIR = Path(".github/tmp")
OUTPUT_DIR = Path("Clash/Ruleset/AD")
OUTPUT_FILE = OUTPUT_DIR / "BanProgramAD.list"

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


def extract_updated_time_acl_style(path: Path) -> str:
    """
    从 ACL4SSR 风格文件中提取：
    "# 更新时间：2026年01月16日 12:51（北京时间）"
    返回 "2026年01月16日 12:51（北京时间）"
    """
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "更新时间" in line and "北京时间" in line:
                text = line.lstrip("#").strip()
                text = text.replace("更新时间：", "").replace("更新时间:", "").strip()
                return text
    return "未知（北京时间）"


def parse_rules(path: Path) -> list[str]:
    """
    解析规则，只保留 OpenClash 可识别的域名类规则，
    并尽量避免 IP 形式的“域名”以降低误杀风险。
    """
    rules: list[str] = []
    seen = set()

    def is_probably_domain(s: str) -> bool:
        # 过滤纯 IP（只含数字和点），保留包含字母或连字符的
        s = s.strip()
        if not s:
            return False
        has_alpha = any(c.isalpha() for c in s)
        has_dot = "." in s
        return has_dot and has_alpha

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if not line.startswith(ALLOWED_PREFIXES):
                continue

            try:
                _type, value = line.split(",", 1)
            except ValueError:
                continue

            if not is_probably_domain(value):
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


def build_header(
    rule_count: int,
    src_update: str,
    banad_update: str,
    advertising_update: str,
    adguard_update: str,
) -> str:
    now_cn = datetime.now(ZoneInfo("Asia/Shanghai"))
    update_time_str = now_cn.strftime("%Y年%m月%d日 %H:%M（北京时间）")

    header_lines = [
        "# BanProgramAD广告拦截规则",
        f"# 更新时间：{update_time_str}",
        "# 原规则来源：",
        f"#   1. BanProgramAD源：{SOURCE_URL}",
        f"#   2. 去重排除源一（BanAD）：{BANAD_URL}",
        f"#   3. 去重排除源二（Advertising）：{ADVERTISING_URL}",
        f"#   4. 去重排除源三（AdGuardSDNSFilter）：{ADGUARD_URL}",
        "# 原规则更新时间：",
        f"#   BanProgramAD源：{src_update}",
        f"#   BanAD源：{banad_update}",
        f"#   Advertising源：{advertising_update}",
        f"#   AdGuardSDNSFilter源：{adguard_update}",
        f"# 规则总数量：{rule_count}",
        "",
    ]
    return "\n".join(header_lines)


def write_output_file(
    rules: list[str],
    src_update: str,
    banad_update: str,
    advertising_update: str,
    adguard_update: str,
) -> None:
    grouped = group_rules_by_type(rules)
    header = build_header(len(rules), src_update, banad_update, advertising_update, adguard_update)

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

    src_tmp = TMP_DIR / "BanProgramAD_source.list"
    banad_tmp = TMP_DIR / "BanAD_source.list"
    advertising_tmp = TMP_DIR / "Advertising_source.list"
    adguard_tmp = TMP_DIR / "AdGuardSDNSFilter_source.list"

    try:
        download_file(SOURCE_URL, src_tmp)
        download_file(BANAD_URL, banad_tmp)
        download_file(ADVERTISING_URL, advertising_tmp)
        download_file(ADGUARD_URL, adguard_tmp)

        src_update = extract_updated_time_acl_style(src_tmp)
        banad_update = extract_updated_time_acl_style(banad_tmp)
        advertising_update = extract_updated_time_acl_style(advertising_tmp)
        adguard_update = extract_updated_time_acl_style(adguard_tmp)

        src_rules = parse_rules(src_tmp)
        banad_rules = set(parse_rules(banad_tmp))
        advertising_rules = set(parse_rules(advertising_tmp))
        adguard_rules = set(parse_rules(adguard_tmp))

        filtered_rules = [
            r
            for r in src_rules
            if r not in banad_rules
            and r not in advertising_rules
            and r not in adguard_rules
        ]

        seen = set()
        final_rules: list[str] = []
        for r in filtered_rules:
            if r not in seen:
                seen.add(r)
                final_rules.append(r)

        write_output_file(final_rules, src_update, banad_update, advertising_update, adguard_update)

    finally:
        clean_tmp_dir()


if __name__ == "__main__":
    main()
