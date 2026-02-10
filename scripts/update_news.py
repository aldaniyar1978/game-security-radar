#!/usr/bin/env python3
import feedparser
import json
import os
from datetime import datetime
import hashlib

# RSS feeds to monitor
FEEDS = [
    {
        "url": "https://feeds.feedburner.com/TheHackersNews",
        "source": "The Hacker News",
    },
    {
        "url": "https://www.bleepingcomputer.com/feed/",
        "source": "BleepingComputer",
    },
    {
        "url": "https://www.darkreading.com/rss.xml",
        "source": "Dark Reading",
    },
]

NEWS_FILE = "docs/news.json"
MAX_ITEMS = 50  # Keep only latest 50 items

def generate_id(title, url):
    """Generate unique ID from title and URL"""
    content = f"{title}{url}"
    return hashlib.md5(content.encode()).hexdigest()[:12]

def extract_tags(title, summary):
    """Extract relevant tags from title and summary"""
    text = f"{title} {summary}".lower()
    tags = []
    
    # Security keywords
    if any(word in text for word in ['phishing', 'scam']):
        tags.append('Phishing')
    if any(word in text for word in ['malware', 'trojan', 'rat', 'infostealer']):
        tags.append('Malware')
    if any(word in text for word in ['ransomware', 'extortion']):
        tags.append('Ransomware')
    if any(word in text for word in ['vulnerability', 'cve', 'exploit']):
        tags.append('Vulnerability')
    if any(word in text for word in ['breach', 'leak', 'hack']):
        tags.append('Data breach')
    
    # Gaming keywords
    if any(word in text for word in ['steam', 'valve']):
        tags.append('Steam')
    if any(word in text for word in ['gaming', 'gamer', 'game']):
        tags.append('Gaming')
    if any(word in text for word in ['cheat', 'aimbot', 'wallhack']):
        tags.append('Cheats')
    if any(word in text for word in ['account', 'credential']):
        tags.append('Account takeover')
    
    return tags if tags else ['Cybersecurity']

def load_existing_news():
    """Load existing news.json"""
    if os.path.exists(NEWS_FILE):
        with open(NEWS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"lastUpdated": "", "items": []}

def save_news(data):
    """Save news.json"""
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def fetch_and_update():
    """Fetch RSS feeds and update news.json"""
    data = load_existing_news()
    existing_ids = {item['id'] for item in data['items']}
    new_count = 0
    
    for feed_info in FEEDS:
        print(f"Fetching {feed_info['source']}...")
        try:
            feed = feedparser.parse(feed_info['url'])
            
            for entry in feed.entries[:10]:  # Latest 10 from each feed
                item_id = generate_id(entry.title, entry.link)
                
                if item_id in existing_ids:
                    continue
                
                # Parse date
                pub_date = entry.get('published_parsed') or entry.get('updated_parsed')
                if pub_date:
                    date_str = datetime(*pub_date[:6]).strftime('%Y-%m-%d')
                else:
                    date_str = datetime.now().strftime('%Y-%m-%d')
                
                # Extract summary
                summary = entry.get('summary', '')
                if len(summary) > 200:
                    summary = summary[:197] + '...'
                
                # Create news item
                news_item = {
                    "id": item_id,
                    "date": date_str,
                    "title": entry.title,
                    "summary": summary or entry.title,
                    "url": entry.link,
                    "source": feed_info['source'],
                    "tags": extract_tags(entry.title, summary)
                }
                
                data['items'].insert(0, news_item)
                existing_ids.add(item_id)
                new_count += 1
                print(f"  Added: {entry.title[:60]}...")
        
        except Exception as e:
            print(f"  Error fetching {feed_info['source']}: {e}")
    
    # Keep only latest MAX_ITEMS
    data['items'] = data['items'][:MAX_ITEMS]
    data['lastUpdated'] = datetime.now().strftime('%Y-%m-%d')
    
    save_news(data)
    print(f"\nUpdated news.json: {new_count} new items, {len(data['items'])} total")

if __name__ == '__main__':
    fetch_and_update()
