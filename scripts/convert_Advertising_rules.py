#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
from pathlib import Path
from datetime import datetime

import requests

try:
    # Python 3.9+
    from zoneinfo import ZoneInfo
except ImportError:
    # 兼容旧版本（GitHub 默认已足够新，一般用不到）
    from backports.zoneinfo import ZoneInfo  # type: ignore


AD_SOURCE_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/Clash/Advertising/Advertising.list"
BANAD_URL = "https://raw.githubusercontent.com/lightanbaby1131-alt/ClashRule_Auto/refs/heads/main/Clash/Ruleset/AD/BanAD.list"

# 仓库内路径
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
    """确保需要的目录存在。"""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest: Path) -> None:
    """下载远程文件到指定路径。"""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def parse_rules(path: Path) -> list[str]:
    """解析规则文件，返回有效规则行（保持顺序）。"""
    rules: list[str] = []
    seen = set()

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # 只保留 OpenClash 可识别的域名类规则
            if not line.startswith(ALLOWED_PREFIXES):
                continue

            if line not in seen:
                seen.add(line)
                rules.append(line)

    return rules


def group_rules_by_type(rules: list[str]) -> dict[str, list[str]]:
    """按规则类型（DOMAIN / DOMAIN-SUFFIX / DOMAIN-KEYWORD 等）分组，提升可读性。"""
    grouped: dict[str, list[str]] = {}
    for r in rules:
        rule_type = r.split(",", 1)[0].strip()
        grouped.setdefault(rule_type, []).append(r)
    return grouped


def build_header(rule_count: int) -> str:
    """构建文件头部注释。"""
    now_cn = datetime.now(ZoneInfo("Asia/Shanghai"))
    update_time_str = now_cn.strftime("%Y年%m月%d日 %H:%M")

    header_lines = [
        "# Advertising广告拦截规则",
        f"# 更新时间: {update_time_str}（北京时间）",
        "# 原规则来源:",
        f"#   1. {AD_SOURCE_URL}",
        "#   2. 去重排除源: " + BANAD_URL,
        "# 原规则更新时间:",
        "#   1. 以各源文件实际更新时间为准",
        f"# 规则总数量: {rule_count}",
        "",
    ]
    return "\n".join(header_lines)


def write_output_file(rules: list[str]) -> None:
    """写入最终的 Advertising.list 文件。"""
    grouped = group_rules_by_type(rules)
    header = build_header(len(rules))

    lines: list[str] = [header]

    # 尽量提高可读性：按类型分块
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
            lines.append("")  # 分组之间空一行

    # 其他未在预设顺序中的类型
    for t, rs in grouped.items():
        if t in used_types:
            continue
        lines.append(f"# === {t} 规则 ===")
        lines.extend(rs)
        lines.append("")

    content = "\n".join(lines).rstrip() + "\n"
    OUTPUT_FILE.write_text(content, encoding="utf-8")


def clean_tmp_dir():
    """删除本次运行生成的所有临时文件。"""
    if TMP_DIR.exists():
        # 只删除 tmp 目录下的内容，不动目录本身
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
        # 下载源规则
        download_file(AD_SOURCE_URL, ad_tmp)
        download_file(BANAD_URL, banad_tmp)

        # 解析规则
        ad_rules = parse_rules(ad_tmp)
        banad_rules = set(parse_rules(banad_tmp))

        # 去除 BanAD 中已有的所有规则，避免重复
        filtered_rules = [r for r in ad_rules if r not in banad_rules]

        # 再次去重，保证最终文件内部不重复
        seen = set()
        final_rules: list[str] = []
        for r in filtered_rules:
            if r not in seen:
                seen.add(r)
                final_rules.append(r)

        write_output_file(final_rules)

    finally:
        # 无论成功与否都尝试清理临时文件
        clean_tmp_dir()


if __name__ == "__main__":
    main()
