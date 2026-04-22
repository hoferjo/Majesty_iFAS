import requests

base = "http://127.0.0.1:8000"
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
r = requests.post(f"{base}/generate-module-data", json=payload, timeout=120)
print(r.status_code)
print(r.json())
