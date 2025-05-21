# 📄 File Converter (PDF Tool)

This application provides a simple graphical user interface (GUI) for converting files **to and from PDF** using drag-and-drop or browse functionality. Supported conversions include Office documents, images, text, and PDFs to DOCX, TXT, JPG, and PNG.

## 🚀 Getting Started

### ✅ Requirements
- Windows OS
- No installation needed — just double-click the `.exe` file!

### 📦 How to Run
1. Double-click `convert_to_from_pdf.exe`.
2. The application window will open full screen.
3. Use the **radio buttons** at the top to select:
   - **To PDF**: Convert images, Office files, or text to PDF.
   - **From PDF**: Convert PDF to TXT, DOCX, JPG, or PNG.
4. Click **"Browse"** to select input files.
5. Click **"Convert"** to start processing.
6. Output files will appear in folders created **next to the `.exe`**:
   - `All/`
   - `Pdf/`, `Office/`, `Image/`, `Txt/`, `Other_Unprocessed/`
   - `Logs/` contains usage and debug logs.

### 📁 Output Locations
- All results are saved **in the same directory** as the `.exe`.
- Logs are stored in the `Logs/` folder.
- Output is sorted into appropriate subfolders (`Pdf`, `Image`, etc.).

## 💡 Tips
- To convert multiple files, only images are allowed to be batch-processed together.
- To preview a file listed, just click the path in the GUI.
- You can view and clear logs by clicking the log bar at the bottom.

## 📎 Included Formats

| Input Format | Output Format |
|--------------|----------------|
| `.jpg`, `.png`, `.bmp` | PDF |
| `.doc`, `.docx`, `.xls`, `.ppt` | PDF |
| `.txt` | PDF |
| `.pdf` | `.docx`, `.txt`, `.jpg`, `.png` |

## 🔐 Permissions

No internet access or admin rights required. Everything runs locally.

---

🛠️ Created for easy document conversion by just **double-clicking and selecting** — no terminal needed!