# Majesty_iFAS Installation Guide

## Prerequisites
- Python 3.8 or newer
- Git

## Installation Steps

1. **Clone the repository:**
   ```sh
   git clone <your-repo-url>
   cd Majesty_iFAS
   ```

2. **Create a virtual environment (recommended):**
   ```sh
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   # Or on Unix/macOS:
   # source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configuration:**
   - Review and update `config/settings.yaml` if needed for your environment (paths, filenames).

5. **Run the application:**
   - For the main script:
     ```sh
     python main.py
     ```
   - For the web app (if using FastAPI):
     ```sh
     uvicorn web.app:app --reload
     ```

6. **(Optional) Start/Stop scripts:**
   - Use `start_server.bat`, `stop_server.bat`, and `restart_server.bat` for server management on Windows.

## Notes
- Data and output folders are ignored by git. Place your input files in the correct `data/raw` subfolders.
- If you encounter issues with missing packages, ensure your virtual environment is activated and run the install command again.

---

For further help, contact the project maintainer.
