import urllib.request, json

url = "http://localhost:8000/api/activity"
try:
    with urllib.request.urlopen(url, timeout=10) as r:
        d = json.loads(r.read())

    lines = []
    lines.append("=== ACTIVITY FEED (first 5) ===")
    for item in d["activity_feed"][:5]:
        ts = item["timestamp"][:19] if item["timestamp"] else "NO_TIMESTAMP"
        lines.append(f"  {item['contact_name'][:25]:<25} | {item['type']:<8} | {ts}")

    lines.append("")
    lines.append("=== RECENT ITEMS ===")
    for item in d["recent_items"]:
        lm = item["last_modified"][:19] if item["last_modified"] else "NO_DATE"
        lines.append(f"  {item['name'][:30]:<30} | {item['type']:<8} | {str(item['status']):<20} | {lm}")

    with open("activity_check.txt", "w") as f:
        f.write("\n".join(lines))
    print("Done - check activity_check.txt")
except Exception as e:
    with open("activity_check.txt", "w") as f:
        f.write(f"ERROR: {e}")
    print(f"Error: {e}")
