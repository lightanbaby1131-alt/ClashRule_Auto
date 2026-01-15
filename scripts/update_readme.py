from pathlib import Path
import re

def parse_header_info(path: Path):
    info = {
        "total": 0,
        "added": 0,
        "removed": 0,
        "updated_at": "",
        "title": "",
    }
    if not path.exists():
        return info

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("# 内容："):
            info["title"] = line.replace("# 内容：", "").strip()
        elif line.startswith("# 总数量："):
            m = re.search(r"(\d+)", line)
            if m:
                info["total"] = int(m.group(1))
        elif line.startswith("# 新增："):
            m = re.search(r"(\d+)", line)
            if m:
                info["added"] = int(m.group(1))
        elif line.startswith("# 删除："):
            m = re.search(r"(\d+)", line)
            if m:
                info["removed"] = int(m.group(1))
        elif line.startswith("# 更新时间（北京时间）："):
            info["updated_at"] = line.replace("# 更新时间（北京时间）：", "").strip()
    return info

def read_diff_file(path: Path, limit: int = 50):
    if not path.exists():
        return []
    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(lines) > limit:
        return lines[:limit] + [f"... 共 {len(lines)} 条，已截断显示"]
    return lines

def main():
    easylist_info = parse_header_info(Path("Clash/Ruleset/AD/easylist.list"))
    adv_info = parse_header_info(Path("Clash/Ruleset/AD/Advertising_Merge.list"))

    easylist_added = read_diff_file(Path("easylist_added.txt"))
    easylist_removed = read_diff_file(Path("easylist_removed.txt"))
    adv_added = read_diff_file(Path("advertising_added.txt"))
    adv_removed = read_diff_file(Path("advertising_removed.txt"))

    latest_update = adv_info["updated_at"] or easylist_info["updated_at"]

    lines = []

    lines.append("# 🚀 Clash 广告规则自动更新")
    lines.append("")
    lines.append("本项目每天自动更新以下规则文件：")
    lines.append("")
    lines.append("- `Clash/Ruleset/AD/easylist.list`")
    lines.append("- `Clash/Ruleset/AD/Advertising_Merge.list`")
    lines.append("")
    lines.append("所有规则均自动下载 → 提取 → 合并 → 去重 → 计算 diff → 输出。")
    lines.append("")
    lines.append("## 📅 最近更新时间（北京时间）")
    lines.append("")
    lines.append(f"`{latest_update}`")
    lines.append("")
    lines.append("## 📦 规则文件概览")
    lines.append("")
    lines.append("| 文件名 | 描述 | 总数 | 新增 | 删除 | 最后更新时间 |")
    lines.append("|--------|------|------|------|------|--------------|")
    lines.append(f"| easylist.list | {easylist_info['title']} | {easylist_info['total']} | {easylist_info['added']} | {easylist_info['removed']} | {easylist_info['updated_at']} |")
    lines.append(f"| Advertising_Merge.list | {adv_info['title']} | {adv_info['total']} | {adv_info['added']} | {adv_info['removed']} | {adv_info['updated_at']} |")
    lines.append("")
    lines.append("## 📄 easylist.list 详细变更")
    lines.append("")
    lines.append("### 新增域名（部分展示）")
    lines.append("")
    if easylist_added:
        lines.append("```")
        lines.extend(easylist_added)
        lines.append("```")
    else:
        lines.append("_本次无新增规则_")
    lines.append("")
    lines.append("### 删除域名（部分展示）")
    lines.append("")
    if easylist_removed:
        lines.append("```")
        lines.extend(easylist_removed)
        lines.append("```")
    else:
        lines.append("_本次无删除规则_")
    lines.append("")
    lines.append("## 📄 Advertising_Merge.list 详细变更")
    lines.append("")
    lines.append("### 新增域名（部分展示）")
    lines.append("")
    if adv_added:
        lines.append("```")
        lines.extend(adv_added)
        lines.append("```")
    else:
        lines.append("_本次无新增规则_")
    lines.append("")
    lines.append("### 删除域名（部分展示）")
    lines.append("")
    if adv_removed:
        lines.append("```")
        lines.extend(adv_removed)
        lines.append("```")
    else:
        lines.append("_本次无删除规则_")
    lines.append("")

    Path("README.md").write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    main()
