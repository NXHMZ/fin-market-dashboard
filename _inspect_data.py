import json

path = r"C:\Users\80909\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8d4332a65ab5fd4457b0ee\fin_market_aggregator\dashboard.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

marker = "const DATA = "
start = text.find(marker) + len(marker)
brace_start = text.find("{", start)
depth = 0
end = brace_start
for i in range(brace_start, len(text)):
    if text[i] == "{":
        depth += 1
    elif text[i] == "}":
        depth -= 1
        if depth == 0:
            end = i + 1
            break
data = json.loads(text[brace_start:end])

targets = {"cls", "cnstock", "cs", "sse", "stcn", "szse", "csrc"}
print("=== EMPTY PUBLISHED SAMPLES (url + title) ===")
for sid in sorted(targets):
    samples = []
    for it in data["items"]:
        if it.get("source_id", "") == sid and not it.get("published"):
            samples.append((it.get("url", ""), it.get("title", "")))
            if len(samples) >= 5:
                break
    print(f"\n--- {sid} ({len(samples)} shown) ---")
    for url, title in samples:
        print(f"  url={url[:90]}")
        print(f"  title={title[:60]}")

print("\n=== NON-EMPTY csrc samples ===")
for it in data["items"]:
    if it.get("source_id", "") == "csrc" and it.get("published"):
        print(f"  pub='{it.get('published')}' url={it.get('url','')[:80]}")
        print(f"  title={it.get('title','')[:50]}")

print("\n=== SZSE non-empty (if any) ===")
for it in data["items"]:
    if it.get("source_id", "") == "szse" and it.get("published"):
        print(f"  pub='{it.get('published')}' url={it.get('url','')[:80]}")
