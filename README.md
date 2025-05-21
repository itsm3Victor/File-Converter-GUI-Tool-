# 🧠 Developer README - File Converter (PDF GUI Tool)

This file documents internal implementation and dev-facing notes, especially for debugging, packaging, and modifying the behavior of `convert_to_from_pdf.py`.

---

## ⚙️ Environment & Dependencies

### Required Libraries
Install via pip if working on the source:

```bash
pip install pillow fpdf pdf2docx pymupdf
```

Additional requirements:
- `soffice` (LibreOffice) must be installed and available in PATH to convert Office documents.

---

## 🐞 Logging

Logs are written to:

- `Logs/user_log.txt` — user-visible events and messages
- `Logs/debug_log.txt` — detailed trace for developers

Old logs are auto-rotated daily and renamed with the date (e.g. `user_log_20240520.txt`).

---

## 🔄 Directory Fix for `.exe`

To ensure all files (logs, outputs) are created in the same directory as the `.exe`, this modification was made:

```python
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)  # When frozen as .exe
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # When run as .py
```

This change replaces earlier usage of `os.getcwd()` or `__file__`.

---

## 🧪 Building the Executable

Build using:

```bash
pyinstaller --noconsole --onefile convert_to_from_pdf.py
```

Optional:

```bash
--icon=myicon.ico
```

This will generate the `.exe` under `dist/`.

---

## 📂 Folder Structure After Build

```text
FileConverter/
├── convert_to_from_pdf.exe
├── Logs/
├── Pdf/
├── Image/
├── Txt/
├── Office/
├── Other_Unprocessed/
├── All/
```

---

## 🧩 Known Issues / Limitations

- `soffice` must be manually installed by users.
- Only `.docx` output is supported when converting from PDF to Office.
- GUI supports only single file for non-image formats.
- Temp images for PDF creation are stored briefly and removed after use.

---

## 🔧 Suggestions for Further Dev

- Add drag-and-drop support
- Add progress bar
- Add command-line mode (for power users)
- Bundle requirements via `.spec` file for better PyInstaller compatibility
- Migrate legacy monolihtic framework to microservice

---

👨‍💻 Maintainers: This app is designed with extensibility in mind. Check `FileConverterGUI` for UI handling and `convert_*` functions for backend logic.
