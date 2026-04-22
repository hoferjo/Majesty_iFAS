import time
import requests

base = "http://127.0.0.1:8000"

# 1) search timing
for i in range(2):
    t0 = time.time()
    r = requests.get(f"{base}/search", params={"query": "61.02.0100", "mode": "module"}, timeout=30)
    print(f"search[{i}] status={r.status_code} time={time.time()-t0:.3f}s")

# 2) generate structure
t0 = time.time()
r = requests.post(f"{base}/generate-module", json={"artnr": "61.02.0100", "existing_articles_target": "none"}, timeout=180)
print(f"generate-module status={r.status_code} time={time.time()-t0:.3f}s")
print(r.json().get("message", "")[:220])

# 3) generate data with BOM selections (mixed naming)
payload = {
    "artnr": "61.02.0100",
    "mode": "module",
    "selected_headers": [
        "Artikelstamm",
        "Stücklisten",
        "Stücklistenversionen",
        "Stücklistenpositionen",
        "Stücklistenvarianten",
        "Stücklstenauswahlvarianten",
    ],
}
t0 = time.time()
r = requests.post(f"{base}/generate-module-data", json=payload, timeout=300)
print(f"generate-module-data status={r.status_code} time={time.time()-t0:.3f}s")
print(r.json().get("message", "")[:600])

# 4) partlist excel download
r = requests.get(f"{base}/download-partlist-excel", params={"mode": "module"}, timeout=60)
print(f"download-partlist-excel status={r.status_code} bytes={len(r.content)}")
