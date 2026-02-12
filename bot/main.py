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
    url = article["url"]
    scripts = []

    # Общие вспомогательные переменные
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # --- Ransomware / Malware / Data breach ---
    if any(t in security_tags for t in ["Ransomware", "Malware", "Data breach"]):
        # Логи Windows (PowerShell)
        scripts.append(
            {
                "name": "PowerShell: поиск подозрительных процессов и автозапуска",
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
        # Логи Linux (bash)
        scripts.append(
            {
                "name": "Linux: поиск подозрительных процессов и бинарей",
                "language": "bash",
                "body": r"""
ps aux | egrep "crypto|minerd|xmrig|kdevtmpfsi" | grep -v egrep || echo "No obvious miners found"

find / -xdev -type f -perm -4000 2>/dev/null
""".strip(),
            }
        )

    # --- Vulnerability / CVE / exploit ---
    if "Vulnerability" in security_tags:
        scripts.append(
            {
                "name": "Поиск обращения к URL из новости в web-логах (Linux)",
                "language": "bash",
                "body": rf"""
# Замените access.log на путь к вашим логам
grep -i "{url}" /var/log/nginx/access.log* /var/log/apache2/access.log* 2>/dev/null || echo "No hits for indicator"
""".strip(),
            }
        )

    # --- Cloud / AWS S3 ---
    if "Cloud" in tech_tags or "AWS" in article["summary"].upper() or "S3" in article["summary"]:
        scripts.append(
            {
                "name": "AWS CLI: базовая проверка публичных бакетов S3",
                "language": "bash",
                "body": r"""
# Требуется настроенный AWS CLI и права на просмотр S3
aws s3api list-buckets --query "Buckets[].Name" --output text | tr '\t' '\n' | while read B; do
  echo "Bucket: $B"
  aws s3api get-bucket-acl --bucket "$B" --query "Grants[].Grantee.URI" --output text 2>/dev/null |
    egrep "AllUsers|AuthenticatedUsers" && echo "  [!] Bucket may be publicly accessible"
done
""".strip(),
            }
        )

    # --- VMware / ESXi ---
    if "VMware" in tech_tags:
        scripts.append(
            {
                "name": "ESXi: проверка неавторизованных SSH-доступов",
                "language": "bash",
                "body": r"""
# Пример для ESXi: анализ SSH-логов (если включено логирование)
grep -i "sshd" /var/log/auth.log /var/log/messages* 2>/dev/null | egrep "Failed|Accepted"
""".strip(),
            }
        )

    # --- Phishing / Account takeover / M365 ---
    if any(t in security_tags for t in ["Phishing", "Account takeover"]) or "M365" in tech_tags:
        scripts.append(
            {
                "name": "M365: поиск подозрительных входов (пример AzureAD / Entra)",
                "language": "powershell",
                "body": r"""
# Требуется модуль AzureAD / MSGraph и права чтения логов
Search-UnifiedAuditLog -StartDate (Get-Date).AddDays(-3) -EndDate (Get-Date) -Operations UserLoggedIn |
  Where-Object { $_.ClientIP -notlike "your_country_ip_range*" } |
  Select-Object UserId, ClientIP, Operation, CreationDate
""".strip(),
            }
        )

    # --- Generic fallback ---
    if not scripts:
        scripts.append(
            {
                "name": "Generic: поиск IOC из новости в логах",
                "language": "bash",
                "body": rf"""
# Замените PATTERN на домены/IP/URL из статьи:
grep -Ei "PATTERN" /var/log/* 2>/dev/null || echo "No hits for pattern"
""".strip(),
            }
        )

    return scripts


def build_recommendations(article):
    text = f"{article['title']} {article['summary']}".lower()
    security_tags = article.get("tags", [])
    tech_tags = classify_stack(text)

    recos = []

    # Базовые рекомендации по типу новости
    if "Ransomware" in security_tags:
        recos.extend(
            [
                "Проверить актуальность резервных копий и возможность восстановления без выкупа.",
                "Провести инвентарь открытых RDP/VPN-доступов и ограничить их по MFA и сети.",
                "Проверить наличие инструментов EDR/XDR на всех критичных узлах.",
            ]
        )
    if "Malware" in security_tags:
        recos.extend(
            [
                "Запустить внеплановое антивирусное сканирование на серверах и рабочих станциях.",
                "Собрать и проанализировать подозрительные бинарные файлы из Temp/AppData для реверса или отправки в песочницу.",
            ]
        )
    if "Vulnerability" in security_tags:
        recos.extend(
            [
                "Сопоставить затронутые версии ПО из новости с реально используемыми в инфраструктуре.",
                "При отсутствии патча — внедрить временные меры: WAF-правила, ограничение доступа, сегментация.",
            ]
        )
    if "Data breach" in security_tags:
        recos.extend(
            [
                "Проверить, используются ли затронутые сервисы/подрядчики в вашей организации.",
                "Оценить необходимость смены паролей и ротации ключей/токенов, связанных с затронутым сервисом.",
            ]
        )
    if "Phishing" in security_tags or "Account takeover" in security_tags:
        recos.extend(
            [
                "Провести таргетированное обучение сотрудников по новым шаблонам фишинга.",
                "Проверить политики MFA и невозможность обхода через устаревшие протоколы (POP/IMAP, legacy auth).",
            ]
        )

    if not recos:
        recos.append(
            "Оценить релевантность новости для вашей среды и сопоставить указанные техники с используемыми технологиями."
        )

    scripts = build_scripts(article, tech_tags, security_tags)

    return {
        "id": article["id"],
        "date": article["date"],
        "title": article["title"],
        "url": article["url"],
        "source": article["source"],
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
