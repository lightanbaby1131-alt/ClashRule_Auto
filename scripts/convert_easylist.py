import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
import difflib

EASYLIST_URL = "https://easylist.to/easylist/easylist.txt"

# 最终输出文件
OUTPUT = Path("Clash/Ruleset/AD/EasyList.list")

# 临时文件目录（不会提交）
TMP_DIR = Path(".github/tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)

# 上一版规则（用于 diff）
PREV = TMP_DIR / "EasyList_prev.txt"


def now_beijing():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz)


def fetch_easylist():
    resp = requests.get(EASYLIST_URL, timeout=60)
    resp.raise_for_status()
    return resp.text.splitlines()


def parse_meta(lines):
    version = None
    last_modified_utc = None

    for line in lines[:50]:
        if line.startswith("! Version:"):
            version = line.split(":", 1)[1].strip()
        if line.startswith("! Last modified:"):
            last_modified_utc = line.split(":", 1)[1].strip()

    return version, last_modified_utc


def utc_to_beijing(utc_str):
    try:
        dt = datetime.strptime(
            utc_str.replace("UTC", "").strip(), "%d %b %Y %H:%M"
        )
        dt = dt.replace(tzinfo=timezone.utc).astimezone(
            timezone(timedelta(hours=8))
        )
        return dt.strftime("%Y年%m月%d日 %H:%M")
    except:
        return utc_str


def extract_rules(lines):
    rules = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("!"):
            continue
        if line.startswith("["):
            continue
        rules.append(line)
    return rules


def diff_stats(old, new):
    diff = difflib.ndiff(old, new)
    add = sum(1 for d in diff if d.startswith("+ "))
    diff = difflib.ndiff(old, new)
    remove = sum(1 for d in diff if d.startswith("- "))
    return add, remove


def main():
    lines = fetch_easylist()
    version, last_modified_utc = parse_meta(lines)

    rules = extract_rules(lines)
    total = len(rules)

    # 读取上一版
    if PREV.exists():
        old_rules = PREV.read_text(encoding="utf-8").splitlines()
    else:
        old_rules = []

    added, removed = diff_stats(old_rules, rules)

    # 时间
    now_bj = now_beijing().strftime("%Y年%m月%d日 %H:%M")
    src_bj = utc_to_beijing(last_modified_utc) if last_modified_utc else now_bj

    # 头部
    header = [
        "# 内容：广告拦截规则 EasyList",
        f"# 总数量：{total} 条",
        f"# 新增：{added} 条",
        f"# 删除：{removed} 条",
        f"# 更新时间（北京时间）：{now_bj}",
        f"# 原规则来源：{EASYLIST_URL}",
        f"# 原规则版本：{version or '未知'}",
        f"# 原规则更新时间（北京时间）：{src_bj}",
        "",
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # 写入最终 .list
    OUTPUT.write_text("\n".join(header + rules), encoding="utf-8")

    # 保存纯规则用于下次 diff（不会提交）
    PREV.write_text("\n".join(rules), encoding="utf-8")


if __name__ == "__main__":
    main()
