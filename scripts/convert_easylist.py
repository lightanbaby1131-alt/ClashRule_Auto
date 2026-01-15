import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
import difflib
import re
from urllib.parse import urlparse

# 原 EasyList
EASYLIST_URL = "https://easylist.to/easylist/easylist.txt"

# 新增：ACL4SSR BanAD
ACL4SSR_BANAD_URL = "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/refs/heads/master/Clash/BanAD.list"

# 输出路径（OpenClash 规则集）
OUTPUT = Path("Clash/Ruleset/AD/EasyList.list")

# 临时目录（不提交）
TMP_DIR = Path(".github/tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)
PREV = TMP_DIR / "EasyList_prev.txt"


def now_beijing():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz)


def fetch(url):
    resp = requests.get(url, timeout=60)
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

    # 1) ||domain.com^
    if line.startswith("||"):
        body = line[2:]
        body = re.split(r"[\^/]", body, 1)[0]
        if "." in body and not body.startswith("."):
            return body

    # 2) |https://domain.com/xxx
    if line.startswith("|http"):
        url = line.lstrip("|")
        try:
            parsed = urlparse(url)
            host = parsed.hostname
            if host and "." in host:
                return host
        except:
            pass

    # 3) DOMAIN-SUFFIX,domain.com
    if line.startswith("DOMAIN-SUFFIX,"):
        d = line.split(",", 1)[1].strip()
        if "." in d:
            return d

    # 4) 纯域名
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

    return domains


def diff_stats(old, new):
    diff = difflib.ndiff(old, new)
    add = sum(1 for d in diff if d.startswith("+ "))
    diff = difflib.ndiff(old, new)
    remove = sum(1 for d in diff if d.startswith("- "))
    return add, remove


def main():
    # 下载 EasyList
    easy_lines = fetch(EASYLIST_URL)
    version, last_modified_utc = parse_meta(easy_lines)

    # 下载 ACL4SSR BanAD
    banad_lines = fetch(ACL4SSR_BANAD_URL)

    # 提取域名
    domains_easy = extract_domains(easy_lines)
    domains_banad = extract_domains(banad_lines)

    # 合并去重
    all_domains = sorted(domains_easy | domains_banad)

    # 转换为 OpenClash 规则格式
    rules = [f"DOMAIN-SUFFIX,{d}" for d in all_domains]
    total = len(rules)

    # diff
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
        "# 内容：广告拦截规则 EasyList + ACL4SSR BanAD",
        f"# 总数量：{total} 条",
        f"# 新增：{added} 条",
        f"# 删除：{removed} 条",
        f"# 更新时间（北京时间）：{now_bj}",
        f"# 原规则来源1：{EASYLIST_URL}",
        f"# 原规则来源2：{ACL4SSR_BANAD_URL}",
        f"# 原规则版本：{version or '未知'}",
        f"# 原规则更新时间（北京时间）：{src_bj}",
        "",
    ]

    # 写入最终文件
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(header + rules), encoding="utf-8")

    # 保存纯规则用于 diff
    PREV.write_text("\n".join(rules), encoding="utf-8")


if __name__ == "__main__":
    main()
