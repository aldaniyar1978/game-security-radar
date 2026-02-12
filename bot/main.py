#!/usr/bin/env python3
import json
import os
from pathlib import Path
from datetime import datetime

NEWS_FILE = Path("docs/news.json")
SEEN_FILE = Path("data/seen_articles.json")
RECO_FILE = Path("docs/security_recommendations.json")


def load_news():
    if not NEWS_FILE.exists():
        return []
    data = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
    return data.get("items", [])


def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
    return set()


def save_seen(seen_ids):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(
        json.dumps(sorted(list(seen_ids)), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_existing_recos():
    if RECO_FILE.exists():
        return json.loads(RECO_FILE.read_text(encoding="utf-8"))
    return {"lastUpdated": "", "items": []}


def classify_stack(text: str):
    text_l = text.lower()
    tech = []

    if any(w in text_l for w in ["windows", "microsoft", "win32", "ntlm"]):
        tech.append("Windows")
    if any(w in text_l for w in ["linux", "ubuntu", "debian", "centos", "red hat", "rhel"]):
        tech.append("Linux")
    if any(w in text_l for w in ["nginx", "apache", "iis", "httpd"]):
        tech.append("WebServer")
    if any(w in text_l for w in ["vmware", "esxi", "vcenter", "vsphere"]):
        tech.append("VMware")
    if any(w in text_l for w in ["aws", "s3", "bucket", "azure", "gcp", "cloud"]):
        tech.append("Cloud")
    if any(w in text_l for w in ["office 365", "m365", "exchange online"]):
        tech.append("M365")

    if not tech:
        tech.append("Generic")
    return tech


def build_scripts(article, tech_tags, security_tags):
    title = article["title"]
    url = article.get("url", "")
    scripts = []

    # Generic helpers
    # Ransomware / Malware / Data breach
    if any(t in security_tags for t in ["Ransomware", "Malware", "Data breach"]):
        scripts.append(
            {
                "name": "PowerShell: hunt for suspicious processes and autoruns",
                "language": "powershell",
                "body": r"""
Get-WmiObject Win32_Process |
  Where-Object { $_.Path -and ($_.Path -like "*AppData*" -or $_.Path -like "*Temp*") } |
  Select-Object ProcessId, Name, Path

Get-CimInstance Win32_StartupCommand |
  Select-Object Name, Command, Location
""".strip(),
            }
        )
        scripts.append(
            {
                "name": "Linux: hunt for suspicious processes and SUID binaries",
                "language": "bash",
                "body": r"""
ps aux | egrep "crypto|minerd|xmrig|kdevtmpfsi" | grep -v egrep || echo "No obvious miners found"

find / -xdev -type f -perm -4000 2>/dev/null
""".strip(),
            }
        )

    # Vulnerability / exploit
    if "Vulnerability" in security_tags and url:
        scripts.append(
            {
                "name": "Search for requests related to this article URL in web logs (Linux)",
                "language": "bash",
                "body": rf"""
# Replace access.log paths with your actual web server logs
grep -i "{url}" /var/log/nginx/access.log* /var/log/apache2/access.log* 2>/dev/null || echo "No hits for indicator"
""".strip(),
            }
        )

    # Cloud / AWS S3
    if "Cloud" in tech_tags:
        scripts.append(
            {
                "name": "AWS CLI: basic public S3 bucket exposure check",
                "language": "bash",
                "body": r"""
# Requires configured AWS CLI with permissions to list and read S3 ACLs
aws s3api list-buckets --query "Buckets[].Name" --output text | tr '\t' '\n' | while read B; do
  echo "Bucket: $B"
  aws s3api get-bucket-acl --bucket "$B" --query "Grants[].Grantee.URI" --output text 2>/dev/null |
    egrep "AllUsers|AuthenticatedUsers" && echo "  [!] Bucket may be publicly accessible"
done
""".strip(),
            }
        )

    # VMware / ESXi
    if "VMware" in tech_tags:
        scripts.append(
            {
                "name": "ESXi / Linux: review SSH authentication attempts",
                "language": "bash",
                "body": r"""
# Example SSH log review (adjust paths for your system)
grep -i "sshd" /var/log/auth.log /var/log/messages* 2>/dev/null | egrep "Failed|Accepted"
""".strip(),
            }
        )

    # M365 / Phishing / Account takeover
    if any(t in security_tags for t in ["Phishing", "Account takeover"]):
        scripts.append(
            {
                "name": "M365: search for suspicious sign‑ins in unified audit log",
                "language": "powershell",
                "body": r"""
# Requires Exchange Online / Security & Compliance modules and permissions to read audit logs
Search-UnifiedAuditLog -StartDate (Get-Date).AddDays(-3) -EndDate (Get-Date) -Operations UserLoggedIn |
  Where-Object { $_.ClientIP -notlike "YOUR_TRUSTED_RANGE*" } |
  Select-Object UserId, ClientIP, Operation, CreationDate
""".strip(),
            }
        )

    # Generic fallback
    if not scripts:
        scripts.append(
            {
                "name": "Generic: search for IOCs from the article across logs",
                "language": "bash",
                "body": r"""
# Replace PATTERN with domains/IPs/URLs or other indicators extracted from the article:
grep -Ei "PATTERN" /var/log/* 2>/dev/null || echo "No hits for pattern"
""".strip(),
            }
        )

    return scripts



def build_recommendations(article):
    text = f"{article['title']} {article.get('summary', '')}".lower()
    security_tags = article.get("tags", [])
    tech_tags = classify_stack(text)

    recos = []

    # Ransomware
    if "Ransomware" in security_tags:
        recos.extend(
            [
                "Validate the integrity and recoverability of recent backups for all critical systems.",
                "Review exposed RDP/VPN entry points and restrict access using MFA and network segmentation.",
                "Ensure EDR/XDR coverage and logging are enabled on all high-value assets.",
            ]
        )

    # Malware
    if "Malware" in security_tags:
        recos.extend(
            [
                "Run an out-of-band malware scan on servers and endpoints, focusing on recent changes.",
                "Collect suspicious binaries from Temp/AppData and submit them to a sandbox or reverse engineering pipeline.",
            ]
        )

    # Vulnerability / CVE
    if "Vulnerability" in security_tags:
        recos.extend(
            [
                "Map affected product versions from the article to the software actually deployed in your environment.",
                "If no vendor patch is available, implement temporary mitigations such as WAF rules, strict access control, and additional segmentation.",
            ]
        )

    # Data breach
    if "Data breach" in security_tags:
        recos.extend(
            [
                "Verify whether the impacted service, vendor, or product is used inside your organization.",
                "Assess the need to rotate passwords, keys, and tokens associated with the affected service.",
            ]
        )

    # Phishing / Account takeover
    if "Phishing" in security_tags or "Account takeover" in security_tags:
        recos.extend(
            [
                "Run targeted awareness for users most likely to be impacted by the described phishing templates.",
                "Review MFA policies and disable legacy authentication protocols (POP/IMAP/SMTP basic auth, other non‑MFA flows).",
            ]
        )

    if not recos:
        recos.append(
            "Assess the relevance of this story to your environment and map the described techniques to your technology stack."
        )

    scripts = build_scripts(article, tech_tags, security_tags)

    return {
        "id": article["id"],
        "date": article["date"],
        "title": article["title"],
        "url": article.get("url", ""),
        "source": article.get("source", ""),
        "summary": article.get("summary", ""),
        "tags": security_tags,
        "tech": tech_tags,
        "recommendations": recos,
        "scripts": scripts,
    }



def main():
    news = load_news()
    if not news:
        print("No news found, exiting.")
        return

    seen = load_seen()
    existing = load_existing_recos()
    items = existing.get("items", [])

    new_count = 0
    for article in news:
        if article["id"] in seen:
            continue
        rec = build_recommendations(article)
        items.insert(0, rec)
        seen.add(article["id"])
        new_count += 1
        print(f"[+] Added recommendations for: {article['title'][:80]}")

    if new_count == 0:
        print("No new articles to process.")
        return

    existing["items"] = items[:200]
    existing["lastUpdated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    RECO_FILE.parent.mkdir(parents=True, exist_ok=True)
    RECO_FILE.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    save_seen(seen)
    print(f"Updated {RECO_FILE} with {new_count} items.")


if __name__ == "__main__":
    main()
