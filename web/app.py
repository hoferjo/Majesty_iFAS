from pathlib import Path
from fastapi import Body
import sys
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import shutil
import os
import json


settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
etl_dir = Path(__file__).parent.parent / "etl"
sys.path.append(str(etl_dir))

from etl.transform import process_module_structure

app = FastAPI()

# Get the absolute path to the web directory
web_dir = Path(__file__).parent.absolute()

# Mount static files (JS, CSS)
app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    template_path = web_dir / "templates" / "index.html"
    return open(template_path, "r", encoding="utf-8").read()

@app.get("/settings", response_class=HTMLResponse)
def settings():
    template_path = web_dir / "templates" / "settings.html"
    return open(template_path, "r", encoding="utf-8").read()

@app.post("/upload-file")
def upload_file(file: UploadFile = File(...)):
    upload_dir = "data/uploaded_files"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "status": "uploaded"}


# --- Search endpoint ---
import csv
from fastapi import Query
from fastapi.responses import JSONResponse

from fastapi import Query
@app.get("/search")
def search(query: str = Query(..., min_length=1), mode: str = Query("article")):
    # Path to the artikelstamm CSV (adjust as needed)
    csv_path = Path(__file__).parent.parent / "data" / "raw" / "artikelstamm" / "artikelstamm_majesty_2026_03_30.csv"
    results = []
    # Map search fields for each mode
    if mode == "article":
        search_fields = ["artnr", "zeichnr", "artbez1", "artbez2", "artbez3"]
    elif mode == "module":
        # For now, use the same fields; adjust as needed for real module data
        search_fields = ["artnr", "zeichnr", "artbez1", "artbez2", "artbez3"]
    else:
        search_fields = ["artnr", "zeichnr", "artbez1", "artbez2", "artbez3"]
    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                if any(query.lower() in str(row.get(field, '')).lower() for field in search_fields):
                    # Only include artnr, artbez1, zeichnr in the result
                    filtered = {
                        "artnr": row.get("artnr", ""),
                        "artbez1": row.get("artbez1", ""),
                        "zeichnr": row.get("zeichnr", "")
                    }
                    results.append(filtered)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    return {"results": results}



# --- Generate Module endpoint ---
@app.post("/generate-module")
def generate_module(data: dict = Body(...)):
    artnr = data.get("artnr")
    if not artnr:
        return {"status": "error", "message": "No artnr provided"}
    # Define paths
    base = Path(__file__).parent.parent
    artikelstamm_path = base / "data" / "raw" / "artikelstamm" / "artikelstamm_majesty_2026_03_30.csv"
    stueckliste_path = base / "data" / "raw" / "stücklistenstamm" / "20410917_stuelipo.csv"
    article_list_path = base / "data" / "processed" / "csv" / "cache" / "article_list.csv"
    partlist_path = base / "data" / "processed" / "csv" / "cache" / "partlist.csv"
    try:
        process_module_structure(str(artnr), str(artikelstamm_path), str(stueckliste_path), str(article_list_path), str(partlist_path))
        return {"status": "success", "message": f"Module for {artnr} processed."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/download-partlist-tree")
def download_partlist_tree(artnr: str):
    base = Path(__file__).parent.parent
    tree_txt_path = base / "data" / "processed" / "csv" / "cache" / "partlist_tree.txt"
    if not tree_txt_path.exists():
        print(f"[ERROR] partlist_tree.txt not found at {tree_txt_path}")
        return JSONResponse(status_code=404, content={"error": f"partlist_tree.txt not found."})
    # Serve as partlist_tree(<rootnr>).txt
    download_name = f"partlist_tree({artnr}).txt"
    return FileResponse(str(tree_txt_path), filename=download_name, media_type="text/plain")