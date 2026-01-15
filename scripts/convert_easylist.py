import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
import sys

EASYLIST_URL = "https://easylist.to/easylist/easylist.txt"

def extract_domain(line: str) -> str | None:
    line = line.strip()
    if not line or line.startswith(("!", "#", "@@", "##", "[", ";")):
        return None

    m = re.match(r"^\|\|([^\/\^]+)\^", line)
    if m:
        return f"DOMAIN-SUFFIX,{m.group(1)}"

    m = re.match(r"^\|https?:\/\/([^\/]+)\/", line)
    if m:
        return f"DOMAIN,{m.group(1)}"

    m = re.match(r"^([^\/\^]+)$", line)
    if m and "." in m.group(1):
        return f"DOMAIN-SUFFIX,{m.group(1)}"

    return None

def parse_header(text: str):
    version = "Unknown"
    last_modified_raw = None

    for line in text.splitlines()[:30]:
        if line.startswith("! Version:"):
            version = line.replace("! Version:", "").strip()
        if line.startswith("! Last modified:"):
            last_modified_raw = line.replace("! Last modified:", "").strip()

    if last_modified_raw:
        try:
            from datetime import datetime, timedelta
            dt_utc = datetime.strptime(last_modified_raw, "%d %b %Y %H:%M UTC")
            dt_beijing = dt_utc + timedelta(hours=8)
            last_modified = dt_beijing.strftime("%Y年%m月%d日 %H:%M")
        except:
            last_modified = last_modified_raw
    else:
        last_modified = "Unknown"

    return version, last_modified

def convert(outfile: str):
    outfile_path = Path(outfile)

    # 旧规则集合，用于 diff
    old_rules = set()
    if outfile_path.exists():
        for line in outfile_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("DOMAIN"):
                old_rules.add(line.strip())

    print("Downloading EasyList...")
    text = requests.get(EASYLIST_URL, timeout=30).text

    version, last_modified = parse_header(text)

    new_rules = set()
    for line in text.splitlines():
        d = extract_domain(line)
        if d:
            new_rules.add(d)

    added = new_rules - old_rules
    removed = old_rules - new_rules

    added_count = len(added)
    removed_count = len(removed)
    total = len(new_rules)

    now = datetime.utcnow() + timedelta(hours=8)
    update_time = now.strftime("%Y年%m月%d日 %H:%M")

    out_lines = [
        "# 内容：广告拦截规则 EasyList",
        f"# 总数量：{total} 条",
        f"# 新增：{added_count} 条",
        f"# 删除：{removed_count} 条",
        f"# 更新时间（北京时间）：{update_time}",
        f"# 原规则来源：{EASYLIST_URL}",
        f"# 原规则版本：{version}",
        f"# 原规则更新时间（北京时间）：{last_modified}",
        "",
        "# ===== 广告规则 =====",
    ]
    out_lines.extend(sorted(new_rules))

    outfile_path.parent.mkdir(parents=True, exist_ok=True)
    outfile_path.write_text("\n".join(out_lines), encoding="utf-8")

    print(f"Generated {outfile} with {total} rules.")

    # 写 diff 详细列表
    Path("easylist_added.txt").write_text("\n".join(sorted(added)), encoding="utf-8")
    Path("easylist_removed.txt").write_text("\n".join(sorted(removed)), encoding="utf-8")

    # 提交信息
    commit_msg = f"EasyList广告规则（新增 {added_count}，删除 {removed_count}）"
    Path("commit_message_easylist.txt").write_text(commit_msg, encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_easylist.py <output_path>")
        sys.exit(1)

    convert(sys.argv[1])
