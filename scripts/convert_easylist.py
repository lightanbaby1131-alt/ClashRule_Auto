import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
import difflib
import re
from urllib.parse import urlparse

EASYLIST_URL = "https://easylist.to/easylist/easylist.txt"

# 最终输出：OpenClash 规则集
OUTPUT = Path("Clash/Ruleset/AD/EasyList.list")

# 临时目录（不提交）
TMP_DIR = Path(".github/tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)
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


def extract_domain_from_rule(line: str):
    # 跳过白名单、元素隐藏等
    if line.startswith("@@"):
        return None
    if "##" in line or "#@" in line:
        return None

    # 1) ||domain.com^ 形式
    if line.startswith("||"):
        body = line[2:]
        body = re.split(r"[\^/]", body, 1)[0]
        if "." in body and not body.startswith("."):
            return body

    # 2) |https://domain.com/xxx 或 http://domain.com
    if line.startswith("|http"):
        url = line.lstrip("|")
        try:
            parsed = urlparse(url)
            host = parsed.hostname
            if host and "." in host:
                return host
        except Exception:
            pass

    # 3) 纯域名形式：ad.example.com 或 example.com
    #    不含通配符、不含特殊符号
    if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", line):
        return line

    return None


def extract_domains(lines):
    domains = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("!"):
            continue
        if line.startswith("["):
            continue

        d = extract_domain_from_rule(line)
        if d:
            domains.add(d.lower())

    # 转成 OpenClash 规则集格式：DOMAIN-SUFFIX,domain
    rules = [f"DOMAIN-SUFFIX,{d}" for d in sorted(domains)]
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

    rules = extract_domains(lines)
    total = len(rules)

    if PREV.exists():
        old_rules = PREV.read_text(encoding="utf-8").splitlines()
    else:
        old_rules = []

    added, removed = diff_stats(old_rules, rules)

    now_bj = now_beijing().strftime("%Y年%m月%d日 %H:%M")
    src_bj = utc_to_beijing(last_modified_utc) if last_modified_utc else now_bj

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
    OUTPUT.write_text("\n".join(header + rules), encoding="utf-8")
    PREV.write_text("\n".join(rules), encoding="utf-8")


if __name__ == "__main__":
    main()
