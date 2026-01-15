import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
import sys

RULE_SOURCES = {
    "ACL4SSR BanAD": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanAD.list",
    "NobyDa AD_Block": "https://raw.githubusercontent.com/NobyDa/ND-AD/master/Surge/AD_Block.txt",
    "NobyDa AdRule": "https://raw.githubusercontent.com/NobyDa/Script/master/Surge/AdRule.list",
    "BlackMatrix7 Advertising": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/source/rule/Advertising/Advertising.list",
    "BlackMatrix7 LianXiangJia": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/source/rule/Advertising/LianXiangJia/LianXiangJia.list",
    "scomper reject": "https://raw.githubusercontent.com/scomper/surge-list/master/reject.list",
    "scomper adblock": "https://raw.githubusercontent.com/scomper/surge-list/master/adblock.list",
    "ACL4SSR BanEasyList": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyList.list",
    "ACL4SSR BanEasyListChina": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyListChina.list",
    "ACL4SSR BanProgramAD": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanProgramAD.list",
    "Adblock4limbo": "https://raw.githubusercontent.com/limbopro/Adblock4limbo/main/Adblock4limbo.list",
    "Hackl0us ad-domains": "https://raw.githubusercontent.com/Hackl0us/SS-Rule-Snippet/master/Rulesets/Surge/Custom/ad-domains.list",
    "Hackl0us video-ad": "https://raw.githubusercontent.com/Hackl0us/SS-Rule-Snippet/master/Rulesets/Surge/Custom/video-ad.list",
    "an0na AdBlock": "https://raw.githubusercontent.com/an0na/R/master/Filter/AdBlock.list",
    "sve1r AdReject": "https://raw.githubusercontent.com/sve1r/Rules-For-Quantumult-X/develop/Rules/Advertising/AdReject.list",
    "sve1r Hijacking": "https://raw.githubusercontent.com/sve1r/Rules-For-Quantumult-X/develop/Rules/Advertising/Hijacking.list",
    "ACL4SSR BanEasyPrivacy": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyPrivacy.list",
    "hupu sgmodule": "https://raw.githubusercontent.com/yjqiang/surge_scripts/main/modules/hupu/hupu.sgmodule",
    "Loyalsoldier reject": "https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/reject.txt",
    "zqzess AdBlock": "https://raw.githubusercontent.com/zqzess/rule_for_quantumultX/master/QuantumultX/rules/AdBlock.list",
}

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

def convert(outfile: str):
    outfile_path = Path(outfile)

    old_rules = set()
    if outfile_path.exists():
        for line in outfile_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("DOMAIN"):
                old_rules.add(line.strip())

    merged = set()
    source_info = {}

    for name, url in RULE_SOURCES.items():
        print(f"Downloading {name}...")
        text = requests.get(url, timeout=30).text
        count = 0

        for line in text.splitlines():
            d = extract_domain(line)
            if d:
                merged.add(d)
                count += 1

        source_info[name] = {
            "url": url,
            "count": count,
        }

    new_rules = merged
    added = new_rules - old_rules
    removed = old_rules - new_rules

    added_count = len(added)
    removed_count = len(removed)
    total = len(new_rules)

    now = datetime.utcnow() + timedelta(hours=8)
    update_time = now.strftime("%Y年%m月%d日 %H:%M")

    out_lines = [
        "# 内容：广告拦截规则（多源合并版）",
        f"# 总数量：{total} 条",
        f"# 新增：{added_count} 条",
        f"# 删除：{removed_count} 条",
        f"# 更新时间（北京时间）：{update_time}",
        "",
        "# 规则来源：",
    ]

    for name, info in source_info.items():
        out_lines.append(f"# - {name}")
        out_lines.append(f"#   URL：{info['url']}")
        out_lines.append(f"#   提取规则数：{info['count']}")
        out_lines.append("#")

    out_lines.append("# ===== 广告规则 =====")
    out_lines.extend(sorted(new_rules))

    outfile_path.parent.mkdir(parents=True, exist_ok=True)
    outfile_path.write_text("\n".join(out_lines), encoding="utf-8")

    print(f"Generated {outfile} with {total} rules.")

    Path("advertising_added.txt").write_text("\n".join(sorted(added)), encoding="utf-8")
    Path("advertising_removed.txt").write_text("\n".join(sorted(removed)), encoding="utf-8")

    commit_msg = f"Advertising合并规则（新增 {added_count}，删除 {removed_count}）"
    Path("commit_message_advertising.txt").write_text(commit_msg, encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_advertising_merge.py <output_path>")
        sys.exit(1)

    convert(sys.argv[1])
