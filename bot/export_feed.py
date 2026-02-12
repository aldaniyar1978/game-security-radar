#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timedelta

RECO_FILE = Path("docs/security_recommendations.json")
FEED_FILE = Path("docs/recommendations_feed.json")

def main():
    if not RECO_FILE.exists():
        print("No recommendations file, exiting.")
        return

    data = json.loads(RECO_FILE.read_text(encoding="utf-8"))
    items = data.get("items", [])

    cutoff = datetime.utcnow() - timedelta(days=3)
    out = []

    for item in items:
        sev = item.get("severity", "Low")
        if sev == "Low":
            continue

        try:
            dt = datetime.fromisoformat(item.get("date", "1970-01-01"))
        except Exception:
            dt = cutoff

        if dt < cutoff:
            continue

        out.append(
            {
                "id": item["id"],
                "date": item.get("date", ""),
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "severity": sev,
                "tags": item.get("tags", []),
                "tech": item.get("tech", []),
                "top_recommendations": item.get("recommendations", [])[:2],
            }
        )

    FEED_FILE.write_text(
        json.dumps({"generatedAt": datetime.utcnow().isoformat() + "Z", "items": out},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Exported {len(out)} items to {FEED_FILE}")

if __name__ == "__main__":
    main()
