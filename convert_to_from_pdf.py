import os
import subprocess
import platform
from PIL import Image
from fpdf import FPDF
from pdf2docx import Converter
import sys
import fitz
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import logging
from datetime import datetime

# --- Backend Logging Setup ---
LOG_DIR_NAME = "Logs"
USER_LOG_FILENAME = "user_log.txt"
DEBUG_LOG_FILENAME = "debug_log.txt"

# Determine script directory for consistent file handling when run as .exe
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)  # Running as bundled .exe
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # Running as .py script

# # Determine script directory for placing log files
# try:
#     SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# except NameError: # Fallback for environments where __file__ is not defined (e.g. interactive)
#     SCRIPT_DIR = os.getcwd()

LOG_DIR = os.path.join(SCRIPT_DIR, LOG_DIR_NAME)

def get_log_filename(base_filename):
    # Returns the log filename based on the current date
    today = datetime.now().strftime('%Y%m%d')
    return f"{os.path.splitext(base_filename)[0]}_{today}{os.path.splitext(base_filename)[1]}"

USER_LOG_FILE_PATH = os.path.join(LOG_DIR, USER_LOG_FILENAME)
DEBUG_LOG_FILE_PATH = os.path.join(LOG_DIR, DEBUG_LOG_FILENAME)

def setup_logging():
    if not os.path.exists(LOG_DIR):
        try:
            os.makedirs(LOG_DIR)
        except OSError as e:
            print(f"Critical: Could not create log directory {LOG_DIR}. Error: {e}", file=sys.stderr)
            class DummyLogger:
                def info(self, msg): pass
                def debug(self, msg): pass
                def error(self, msg, exc_info=False): pass
                def exception(self, msg): pass
            return DummyLogger(), DummyLogger()

    # Check if log files need to be renamed (i.e., if they exist and are from a previous day)
    for log_file in [USER_LOG_FILE_PATH, DEBUG_LOG_FILE_PATH]:
        if os.path.exists(log_file):
            # Get the last modified time of the log file
            last_modified = datetime.fromtimestamp(os.path.getmtime(log_file))
            if last_modified.date() < datetime.now().date():
                # Rename the log file to include the date
                new_filename = get_log_filename(os.path.basename(log_file))
                new_path = os.path.join(LOG_DIR, new_filename)
                try:
                    os.rename(log_file, new_path)
                    print(f"Renamed log file {log_file} to {new_path}")
                except OSError as e:
                    print(f"Error renaming log file {log_file}: {e}", file=sys.stderr)

    # User Logger
    user_logger = logging.getLogger('UserLogger')
    user_logger.setLevel(logging.INFO)
    user_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == USER_LOG_FILE_PATH for h in user_logger.handlers):
        try:
            user_file_handler = logging.FileHandler(USER_LOG_FILE_PATH, encoding='utf-8')
            user_file_handler.setFormatter(user_formatter)
            user_logger.addHandler(user_file_handler)
        except Exception as e:
            print(f"Error setting up user_log file handler: {e}", file=sys.stderr)

    # Debug Logger
    debug_logger = logging.getLogger('DebugLogger')
    debug_logger.setLevel(logging.DEBUG)
    debug_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == DEBUG_LOG_FILE_PATH for h in debug_logger.handlers):
        try:
            debug_file_handler = logging.FileHandler(DEBUG_LOG_FILE_PATH, encoding='utf-8')
            debug_file_handler.setFormatter(debug_formatter)
            debug_logger.addHandler(debug_file_handler)
        except Exception as e:
            print(f"Error setting up debug_log file handler: {e}", file=sys.stderr)
            
    return user_logger, debug_logger

user_log, debug_log = setup_logging()
# --- End Backend Logging Setup ---

def create_folders():
    folders = ['All', 'Pdf', 'Office', 'Image', 'Txt', 'Other_Unprocessed']
    # SCRIPT_DIR is already defined globally
    
    user_log.info("Ensuring output folders exist.")
    debug_log.debug(f"Script directory for folders: {SCRIPT_DIR}")
    
    for folder in folders:
        folder_path = os.path.join(SCRIPT_DIR, folder)
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                user_log.info(f"Created folder: {folder_path}")
                debug_log.debug(f"Created folder: {folder_path}")
            except OSError as e:
                user_log.error(f"Failed to create folder {folder_path}: {e}")
                debug_log.exception(f"OSError while creating folder {folder_path}")
        else:
            debug_log.debug(f"Folder already exists: {folder_path}")
    return SCRIPT_DIR

def get_unique_filename(directory, filename):
    base_name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = f"{base_name}{ext}"
    new_path = os.path.join(directory, new_filename)
    
    original_new_path = new_path
    while os.path.exists(new_path):
        new_filename = f"{base_name}_{counter}{ext}"
        new_path = os.path.join(directory, new_filename)
        counter += 1
    
    if new_path != original_new_path:
        debug_log.debug(f"Filename conflict for {original_new_path}. Renamed to {new_path}")
        
    return new_path

def sort_output_file(output_path, script_dir):
    user_log.info(f"Sorting output file: {os.path.basename(output_path)}")
    debug_log.debug(f"sort_output_file called with output_path='{output_path}', script_dir='{script_dir}'")

    all_folder = os.path.join(script_dir, 'All')
    base_name = os.path.basename(output_path)
    
    try:
        all_path = get_unique_filename(all_folder, base_name)
        shutil.copy2(output_path, all_path)
        user_log.info(f"Copied '{base_name}' to 'All' folder as '{os.path.basename(all_path)}'")
        debug_log.debug(f"Copied {output_path} to {all_path}")
    except Exception as e:
        user_log.error(f"Failed to copy {base_name} to 'All' folder: {e}")
        debug_log.exception(f"Error copying {output_path} to {all_path}")
        raise # Re-raise to indicate failure in sorting

    ext = os.path.splitext(output_path)[1].lower()
    if ext == '.pdf':
        dest_folder_name = 'Pdf'
    elif ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
        dest_folder_name = 'Office'
    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        dest_folder_name = 'Image'
    elif ext == '.txt':
        dest_folder_name = 'Txt'
    else:
        dest_folder_name = 'Other_Unprocessed'
    
    user_log.info(f"Categorized '{base_name}' to '{dest_folder_name}' type.")
    dest_folder_path = os.path.join(script_dir, dest_folder_name)
    
    try:
        dest_path = get_unique_filename(dest_folder_path, base_name)
        shutil.copy2(output_path, dest_path)
        user_log.info(f"Copied '{base_name}' to '{dest_folder_name}' folder as '{os.path.basename(dest_path)}'")
        debug_log.debug(f"Copied {output_path} to {dest_path}")
    except Exception as e:
        user_log.error(f"Failed to copy {base_name} to '{dest_folder_name}' folder: {e}")
        debug_log.exception(f"Error copying {output_path} to {dest_path}")
        # If copy to specific folder fails, the 'All' copy still exists.
        # Decide if this is a critical failure. For now, we'll let 'All' copy persist.
        # We might not want to remove the original if this step fails.
        # However, the function expects to return two paths.
        # For simplicity, we'll let it proceed and the original might not be removed.
        # A more robust solution might involve cleanup or different return values.

    try:
        os.remove(output_path)
        debug_log.debug(f"Removed original temporary output file: {output_path}")
    except Exception as e:
        user_log.warning(f"Failed to remove temporary file {output_path}: {e}") # Warning, as copies exist
        debug_log.exception(f"Error removing temporary file {output_path}")
        
    return [all_path, dest_path]


def open_file(filepath):
    user_log.info(f"Attempting to open file: {filepath}")
    debug_log.debug(f"open_file called for: {filepath}")
    system = platform.system()
    try:
        if system == 'Darwin':       # macOS
            subprocess.call(('open', filepath))
        elif system == 'Windows':    # Windows
            os.startfile(filepath)
        else:                        # linux variants
            subprocess.call(('xdg-open', filepath))
        user_log.info(f"Successfully initiated opening of {filepath}")
    except Exception as e:
        user_log.error(f"Could not open file {filepath}: {e}")
        debug_log.exception(f"Exception in open_file for {filepath}")


def handle_output_file(output_path, final_output, multiple_files=False):
    script_dir = create_folders() # Ensures folders (and Logs folder via setup_logging) exist
    sorted_files_aggregate = []
    
    operation_description = f"main output hint: {os.path.basename(output_path)}, final output(s): {final_output if isinstance(final_output, str) else [os.path.basename(f) for f in final_output]}"
    user_log.info(f"Handling output file(s). {operation_description}")
    debug_log.debug(f"handle_output_file: output_path='{output_path}', final_output='{final_output}', multiple_files={multiple_files}")

    if multiple_files:
        if not isinstance(final_output, list): # Ensure final_output is a list for multiple_files
            final_output = [final_output]
            debug_log.warning(f"handle_output_file: multiple_files is True but final_output was not a list. Corrected.")

        for i, file_item in enumerate(final_output):
            user_log.info(f"Sorting file {i+1}/{len(final_output)}: {os.path.basename(file_item)}")
            debug_log.debug(f"Sorting multiple file item: {file_item}")
            try:
                sorted_paths_for_item = sort_output_file(file_item, script_dir)
                sorted_files_aggregate.extend(sorted_paths_for_item)
            except Exception as e:
                user_log.error(f"Failed to sort file item {file_item}: {e}")
                debug_log.exception(f"Error in sort_output_file for item {file_item} within handle_output_file loop")
                # Continue with other files if one fails
    else:
        user_log.info(f"Sorting single file: {os.path.basename(final_output)}")
        debug_log.debug(f"Sorting single file item: {final_output}")
        try:
            sorted_files_aggregate = sort_output_file(final_output, script_dir)
        except Exception as e:
            user_log.error(f"Failed to sort file {final_output}: {e}")
            debug_log.exception(f"Error in sort_output_file for {final_output} within handle_output_file")
            # If single file sort fails, sorted_files_aggregate might be empty or incomplete.
            # The function will return what it has.
            
    user_log.info(f"File processing and sorting finished. Resulting paths (includes duplicates if sorted to multiple locations): {sorted_files_aggregate}")
    
    opened_files_log = []
    # Only open unique files from the 'All' folder
    unique_all_files_to_open = {f for f in sorted_files_aggregate if os.path.dirname(f).endswith('All')}

    for file_to_open in unique_all_files_to_open:
        open_file(file_to_open) # open_file handles its own logging
        opened_files_log.append(os.path.basename(file_to_open))

    if opened_files_log:
        user_log.info(f"Automatically opened files in 'All' folder: {', '.join(opened_files_log)}")
    else:
        user_log.info("No files were automatically opened (either none in 'All' folder or opening failed).")
        
    return sorted_files_aggregate

def convert_office_to_pdf(input_path, output_path):
    user_log.info(f"Converting Office file '{os.path.basename(input_path)}' to PDF.")
    debug_log.debug(f"Executing soffice for {input_path} to {output_path}")
    try:
        # Ensure output directory exists
        outdir = os.path.dirname(output_path)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
            debug_log.debug(f"Created output directory for soffice: {outdir}")

        process = subprocess.run([
            'soffice', '--headless', '--convert-to', 'pdf', f'--outdir',
            outdir, input_path
        ], check=True, capture_output=True, text=True, timeout=120) # Added timeout
        
        # soffice might create output with original name in outdir, not necessarily output_path name
        # We need to find the generated PDF.
        # Assuming soffice replaces extension with .pdf
        expected_pdf_name = os.path.splitext(os.path.basename(input_path))[0] + ".pdf"
        generated_pdf_path = os.path.join(outdir, expected_pdf_name)

        if os.path.exists(generated_pdf_path):
            if generated_pdf_path != output_path:
                 # If soffice used a different name, rename/move it to the expected output_path
                shutil.move(generated_pdf_path, output_path)
                debug_log.debug(f"Moved/Renamed soffice output from {generated_pdf_path} to {output_path}")
            user_log.info(f"Successfully converted '{os.path.basename(input_path)}' to PDF: '{os.path.basename(output_path)}'")
            debug_log.debug(f"soffice output for {input_path}: STDOUT: {process.stdout}, STDERR: {process.stderr}")
            return output_path
        else:
            err_msg = f"soffice conversion seemed to succeed but expected output PDF not found: {generated_pdf_path}"
            user_log.error(err_msg)
            debug_log.error(f"{err_msg}. soffice STDOUT: {process.stdout}, STDERR: {process.stderr}")
            raise FileNotFoundError(err_msg)

    except subprocess.CalledProcessError as e:
        err_msg = f"LibreOffice/soffice conversion failed for {os.path.basename(input_path)}. Error: {e.stderr or e.stdout or 'No output'}"
        user_log.error(err_msg)
        debug_log.error(f"soffice command failed. Return code: {e.returncode}. Stderr: {e.stderr}. Stdout: {e.stdout}")
        raise # Re-raise to be caught by GUI
    except subprocess.TimeoutExpired:
        err_msg = f"LibreOffice/soffice conversion timed out for {os.path.basename(input_path)}."
        user_log.error(err_msg)
        debug_log.error(err_msg)
        raise ValueError(err_msg)
    except FileNotFoundError: # This catches if 'soffice' itself is not found
        err_msg = "LibreOffice (soffice) not found. Please ensure it is installed and in your system's PATH."
        user_log.error(err_msg)
        debug_log.error(err_msg)
        raise ValueError(err_msg) # Raise a more specific error for the GUI
    except Exception as e:
        err_msg = f"An unexpected error occurred during Office to PDF conversion of {os.path.basename(input_path)}: {str(e)}"
        user_log.error(err_msg)
        debug_log.exception(err_msg)
        raise ValueError(err_msg)


def convert_images_to_pdf(input_paths, output_path):
    user_log.info(f"Converting {len(input_paths)} image(s) to PDF: {os.path.basename(output_path)}")
    debug_log.debug(f"convert_images_to_pdf called with input_paths: {input_paths}, output_path: {output_path}")
    pdf = FPDF()
    
    for i, input_path in enumerate(input_paths):
        debug_log.debug(f"Processing image {i+1}/{len(input_paths)}: {input_path}")
        try:
            image = Image.open(input_path)
            if image.mode == "RGBA":
                image = image.convert("RGB")
                debug_log.debug(f"Converted image {input_path} from RGBA to RGB")
            
            # Using a temporary file for FPDF image processing can be more robust for various formats
            # Ensure temp file has a unique name to avoid clashes if script is run concurrently (less likely for GUI app)
            temp_filename = f"temp_image_for_pdf_{os.path.basename(input_path)}_{i}.jpg"
            temp_path = os.path.join(os.path.dirname(output_path), temp_filename) # Place temp in output dir
            
            image.save(temp_path, "JPEG")
            debug_log.debug(f"Saved temporary JPEG for PDF: {temp_path}")
            
            pdf.add_page()
            # Get image dimensions to scale it appropriately for A4 (210x297 mm)
            img_width_px, img_height_px = image.size
            # Convert pixels to mm (assuming 72 DPI for FPDF, though it's more complex)
            # FPDF uses points (1/72 inch), 1 inch = 25.4 mm
            # For simplicity, fit width to A4 width (210mm) minus margins (e.g., 10mm each side)
            available_width_mm = 210 - 20 # 10mm margin on each side
            
            img_aspect_ratio = img_width_px / img_height_px
            display_width_mm = available_width_mm
            display_height_mm = display_width_mm / img_aspect_ratio

            # If height exceeds A4 height (297mm) minus margins, scale by height instead
            available_height_mm = 297 - 20
            if display_height_mm > available_height_mm:
                display_height_mm = available_height_mm
                display_width_mm = display_height_mm * img_aspect_ratio

            # Center the image
            x_pos = (210 - display_width_mm) / 2
            y_pos = (297 - display_height_mm) / 2
            if y_pos < 10 : y_pos = 10 # Ensure it's within top margin

            pdf.image(temp_path, x=x_pos, y=y_pos, w=display_width_mm)
            os.remove(temp_path)
            debug_log.debug(f"Added {input_path} to PDF and removed temp file {temp_path}")
            
        except Exception as e:
            user_log.error(f"Failed to process image {input_path}: {e}")
            debug_log.exception(f"Error processing image {input_path} for PDF conversion.")
            # Continue to next image if one fails
            
    if not pdf.pages: # Check if any pages were added
        err_msg = "No images were successfully processed to create the PDF."
        user_log.error(err_msg)
        debug_log.error(err_msg + f" Input images: {input_paths}")
        raise ValueError(err_msg)

    try:
        pdf.output(output_path)
        user_log.info(f"Successfully created PDF from images: {os.path.basename(output_path)}")
    except Exception as e:
        user_log.error(f"Failed to save PDF {output_path}: {e}")
        debug_log.exception(f"Error saving PDF {output_path} from images.")
        raise
    return output_path

def convert_text_to_pdf(input_path, output_path):
    user_log.info(f"Converting text file '{os.path.basename(input_path)}' to PDF: {os.path.basename(output_path)}")
    debug_log.debug(f"convert_text_to_pdf: {input_path} -> {output_path}")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Using multi_cell for better handling of long lines and newlines within the line
                pdf.multi_cell(0, 10, txt=line.strip()) # Width 0 means full page width within margins
            user_log.info(f"Successfully read text file '{os.path.basename(input_path)}'.")
    except Exception as e:
        user_log.error(f"Failed to read text file {input_path}: {e}")
        debug_log.exception(f"Error reading text file {input_path} for PDF conversion.")
        raise

    try:
        pdf.output(output_path)
        user_log.info(f"Successfully created PDF from text: {os.path.basename(output_path)}")
    except Exception as e:
        user_log.error(f"Failed to save PDF {output_path} from text: {e}")
        debug_log.exception(f"Error saving PDF {output_path} from text.")
        raise
    return output_path

def convert_pdf_to_text(input_path, output_path):
    user_log.info(f"Converting PDF '{os.path.basename(input_path)}' to text: {os.path.basename(output_path)}")
    debug_log.debug(f"convert_pdf_to_text: {input_path} -> {output_path}")
    try:
        doc = fitz.open(input_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, page in enumerate(doc):
                f.write(page.get_text())
                debug_log.debug(f"Extracted text from page {i+1} of {input_path}")
        doc.close()
        user_log.info(f"Successfully converted PDF to text: {os.path.basename(output_path)}")
    except Exception as e:
        user_log.error(f"Failed to convert PDF {input_path} to text: {e}")
        debug_log.exception(f"Error during PDF to text conversion for {input_path}.")
        raise
    return output_path

def convert_pdf_to_images(input_path, output_path):
    user_log.info(f"Converting PDF '{os.path.basename(input_path)}' to images (e.g., {os.path.basename(output_path)}).")
    debug_log.debug(f"convert_pdf_to_images: {input_path} -> {output_path} (base name)")
    output_files = []
    try:
        doc = fitz.open(input_path)
        base_name_template, ext = os.path.splitext(output_path) # output_path is a template like 'filename.jpg'
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap()
            # Use get_unique_filename for each page's output
            page_output_filename_base = f"{os.path.basename(base_name_template)}_{page_num+1}"
            page_output_path = get_unique_filename(os.path.dirname(output_path), f"{page_output_filename_base}{ext}")
            
            pix.save(page_output_path)
            output_files.append(page_output_path)
            user_log.info(f"Saved page {page_num+1} from '{os.path.basename(input_path)}' as '{os.path.basename(page_output_path)}'")
            debug_log.debug(f"Saved page {page_num+1} of {input_path} to {page_output_path}")
            
        doc.close()
        if not output_files:
            raise ValueError("No pages found or converted from PDF.")
        user_log.info(f"Successfully converted PDF to {len(output_files)} image(s).")
    except Exception as e:
        user_log.error(f"Failed to convert PDF {input_path} to images: {e}")
        debug_log.exception(f"Error during PDF to images conversion for {input_path}.")
        raise
    return output_files

def convert_pdf_to_office(input_path, output_path):
    user_log.info(f"Converting PDF '{os.path.basename(input_path)}' to DOCX: {os.path.basename(output_path)}")
    debug_log.debug(f"convert_pdf_to_office: {input_path} -> {output_path}")
    if not output_path.endswith('.docx'):
        msg = "Only .docx conversion is supported for office files from PDF."
        user_log.error(msg)
        debug_log.error(msg + f" Output path was: {output_path}")
        raise ValueError(msg)
        
    try:
        cv = Converter(input_path)
        cv.convert(output_path) # This can take time
        cv.close()
        user_log.info(f"Successfully converted PDF to DOCX: {os.path.basename(output_path)}")
    except Exception as e: # pdf2docx can raise various errors
        user_log.error(f"Failed to convert PDF {input_path} to DOCX: {e}")
        debug_log.exception(f"Error during PDF to DOCX conversion for {input_path}.")
        raise
    return output_path

def handle_unsupported_file(input_path):
    # This function is typically called when a conversion type is not matched.
    # The calling function (convert_to_pdf or convert_from_pdf) should log the attempt.
    # This function logs the "unsupported" action and copies the file.
    
    script_dir = create_folders() # Ensures folders exist
    dest_folder = os.path.join(script_dir, 'Other_Unprocessed')
    base_name = os.path.basename(input_path)
    
    try:
        dest_path = get_unique_filename(dest_folder, base_name)
        shutil.copy2(input_path, dest_path)
        msg = f"Unsupported file type for conversion: {os.path.splitext(input_path)[1]}. Copied '{base_name}' to 'Other_Unprocessed' folder."
        user_log.warning(msg) # Warning as it's not an error in this function, but a classification
        debug_log.warning(f"{msg} Full path: {input_path}, Copied to: {dest_path}")
    except Exception as e:
        msg = f"Unsupported file type: {os.path.splitext(input_path)[1]}. Failed to copy to 'Other_Unprocessed': {e}"
        user_log.error(msg)
        debug_log.exception(f"Error copying unsupported file {input_path} to Other_Unprocessed.")
    
    # Raise ValueError to indicate to the caller that the conversion cannot proceed.
    # The caller (GUI) will display this error.
    raise ValueError(f"Unsupported file type: {os.path.splitext(input_path)[1]} for the selected operation.")


def convert_to_pdf(input_paths_raw):
    user_log.info(f"Request to convert to PDF: {input_paths_raw}")
    debug_log.debug(f"convert_to_pdf called with input_paths_raw: {input_paths_raw}")

    if not isinstance(input_paths_raw, list):
        if isinstance(input_paths_raw, str) and ';' in input_paths_raw:
            input_paths = input_paths_raw.split(';')
            debug_log.debug(f"Split input string into multiple paths: {input_paths}")
        else:
            input_paths = [input_paths_raw]
    else: # Already a list
        input_paths = input_paths_raw
    
    if not input_paths or not input_paths[0]: # Check for empty list or empty first path
        msg = "No input file provided for PDF conversion."
        user_log.error(msg)
        debug_log.error(msg)
        raise ValueError(msg)

    # Use the directory of the first input file for the output, or script_dir if path is relative
    first_input_dir = os.path.dirname(input_paths[0])
    if not first_input_dir: # If input is just a filename, assume it's in script_dir or CWD
        first_input_dir = SCRIPT_DIR 
    
    output_base_name = os.path.splitext(os.path.basename(input_paths[0]))[0]
    output_path_template = os.path.join(first_input_dir, output_base_name + ".pdf")
    # Ensure output path is unique before passing to conversion functions
    output_path = get_unique_filename(first_input_dir, os.path.basename(output_path_template))
    debug_log.debug(f"Determined output PDF path: {output_path}")

    exts = [os.path.splitext(path)[1].lower() for path in input_paths]
    image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    office_exts = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
    
    final_output = None
    # Determine file type and validate inputs
    if all(ext in image_exts for ext in exts):
        user_log.info(f"Identified input as image(s) for PDF conversion: {[os.path.basename(p) for p in input_paths]}")
        final_output = convert_images_to_pdf(input_paths, output_path)
    elif len(input_paths) > 1:
        msg = "Multiple files are only supported for image-to-PDF conversion."
        user_log.error(msg + f" Received: {len(input_paths)} files.")
        debug_log.error(msg + f" Files: {input_paths}")
        raise ValueError(msg)
    elif exts[0] in office_exts:
        user_log.info(f"Identified input as Office file for PDF conversion: {os.path.basename(input_paths[0])}")
        final_output = convert_office_to_pdf(input_paths[0], output_path)
    elif exts[0] == '.txt':
        user_log.info(f"Identified input as text file for PDF conversion: {os.path.basename(input_paths[0])}")
        final_output = convert_text_to_pdf(input_paths[0], output_path)
    else:
        # Let handle_unsupported_file log and raise the error
        handle_unsupported_file(input_paths[0]) 
        # Should not be reached due to raise in handle_unsupported_file
        return [] 
        
    if final_output:
        sorted_files = handle_output_file(output_path, final_output) # handle_output_file logs success of sorting
        user_log.info(f"Successfully converted {input_paths_raw} to PDF. Final sorted output(s): {sorted_files}")
        return sorted_files
    else:
        # This case should ideally be covered by exceptions in conversion functions or handle_unsupported_file
        msg = f"Conversion to PDF failed for {input_paths_raw}, no final output generated."
        user_log.error(msg)
        debug_log.error(msg)
        raise RuntimeError(msg) # Or a more specific error

def convert_from_pdf(input_path, output_type):
    user_log.info(f"Request to convert from PDF '{os.path.basename(input_path)}' to '{output_type}'")
    debug_log.debug(f"convert_from_pdf called with input_path: {input_path}, output_type: {output_type}")

    if not input_path:
        msg = "No input PDF file provided for conversion."
        user_log.error(msg)
        debug_log.error(msg)
        raise ValueError(msg)

    # Use the directory of the input file for the output, or script_dir
    input_dir = os.path.dirname(input_path)
    if not input_dir:
        input_dir = SCRIPT_DIR

    filename_base = os.path.splitext(os.path.basename(input_path))[0]
    # Output path here is a template, actual unique names handled by conversion or get_unique_filename
    output_path_template = os.path.join(input_dir, f"{filename_base}.{output_type}")
    # For PDF to images, output_path_template is more of a naming hint for the series of images.
    # For others, it's the direct output file. We'll let conversion functions use get_unique_filename if needed.
    
    final_output_or_list = None
    is_multiple_output = False

    if output_type == 'txt':
        final_output_or_list = convert_pdf_to_text(input_path, output_path_template)
    elif output_type in ['jpg', 'jpeg', 'png']: # Assuming these are image extensions
        # convert_pdf_to_images handles unique naming for each page
        final_output_or_list = convert_pdf_to_images(input_path, output_path_template)
        is_multiple_output = True
    elif output_type in ['doc', 'docx']:
        # Ensure output_path_template is .docx if 'doc' is selected, as we only support .docx
        actual_output_path = os.path.join(input_dir, f"{filename_base}.docx")
        final_output_or_list = convert_pdf_to_office(input_path, actual_output_path)
    else:
        # Let handle_unsupported_file log and raise the error
        handle_unsupported_file(input_path) # Will use input_path to determine unsupported type
        return [] # Should not be reached

    if final_output_or_list:
        # output_path_template is used as a hint for handle_output_file's logging
        sorted_files = handle_output_file(output_path_template, final_output_or_list, multiple_files=is_multiple_output)
        user_log.info(f"Successfully converted PDF '{os.path.basename(input_path)}' to '{output_type}'. Final sorted output(s): {sorted_files}")
        return sorted_files
    else:
        msg = f"Conversion from PDF '{os.path.basename(input_path)}' to '{output_type}' failed, no final output generated."
        user_log.error(msg)
        debug_log.error(msg)
        raise RuntimeError(msg)


class FileConverterGUI:
    def __init__(self, root_tk):
        self.root = root_tk
        self.root.title("File Converter")
        
        # Make window fullscreen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        try:
            self.root.state('zoomed')  # For Windows
        except tk.TclError: # For other OS that might not support 'zoomed'
             debug_log.info("Tkinter state 'zoomed' not supported on this platform, using maximized geometry.")
             # self.root.attributes('-fullscreen', True) # Alternative, but can be too intrusive

        # Variables
        self.file_path = tk.StringVar()
        self.conversion_type = tk.StringVar(value="to-pdf")
        self.output_format = tk.StringVar()

        self.log_history_window = None 
        self.log_history_text_widget = None
        
        # Create GUI elements
        self.create_widgets()
        user_log.info("FileConverterGUI initialized.")
        debug_log.debug("FileConverterGUI __init__ completed.")
        
    def _log_gui_event(self, message, level="INFO", is_error=False, detail_for_debug=None):
        """
        Helper to update GUI log display and write to backend logs.
        `message` is shown in GUI. `detail_for_debug` is for debug log if different.
        """
        self.latest_log_display.config(text=message)
        final_debug_message = detail_for_debug if detail_for_debug else message

        if is_error:
            self.latest_log_display.config(foreground="red")
            user_log.error(message) # Log user-facing error message
            debug_log.error(final_debug_message) # Log potentially more detailed debug message
        else: # INFO
            self.latest_log_display.config(foreground="darkgreen") # Using darkgreen for better readability
            user_log.info(message)
            debug_log.info(final_debug_message)
        
        self.root.update_idletasks() # Ensure GUI updates immediately

    def create_widgets(self):
        debug_log.debug("FileConverterGUI create_widgets started.")
        # Main frame to allow bottom log bar
        main_content_frame = ttk.Frame(self.root)
        main_content_frame.pack(fill=tk.BOTH, expand=True)

        # Conversion type selection
        type_frame = ttk.Frame(main_content_frame, padding="10")
        type_frame.pack(fill=tk.X)
        
        ttk.Label(type_frame, text="Conversion Type:").pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="To PDF", value="to-pdf", 
                       variable=self.conversion_type, command=self.update_formats).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="From PDF", value="from-pdf", 
                       variable=self.conversion_type, command=self.update_formats).pack(side=tk.LEFT)
        
        # Output format selection
        format_frame = ttk.Frame(main_content_frame, padding="10")
        format_frame.pack(fill=tk.X)
        
        ttk.Label(format_frame, text="Output Format:").pack(side=tk.LEFT)
        self.format_dropdown = ttk.Combobox(format_frame, textvariable=self.output_format, state="readonly", width=10)
        self.format_dropdown.pack(side=tk.LEFT, padx=5)
        
        # File selection frame
        file_frame = ttk.Frame(main_content_frame, padding="10")
        file_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Input files
        input_frame = ttk.LabelFrame(file_frame, text="Input Files", padding="5")
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))
        
        input_controls = ttk.Frame(input_frame)
        input_controls.pack(fill=tk.X)
        
        self.file_entry = ttk.Entry(input_controls)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.file_entry.bind('<Return>', lambda e: self.validate_manual_path())
        ttk.Button(input_controls, text="Browse", command=self.browse_file).pack(side=tk.LEFT)
        
        self.file_list = tk.Text(input_frame, height=8, wrap=tk.NONE)
        input_scrollbar_y = ttk.Scrollbar(input_frame, orient="vertical", command=self.file_list.yview)
        input_scrollbar_x = ttk.Scrollbar(input_frame, orient="horizontal", command=self.file_list.xview)
        self.file_list.configure(yscrollcommand=input_scrollbar_y.set, xscrollcommand=input_scrollbar_x.set)
        
        input_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        input_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(0,5)) # pady adjusted for x scrollbar
        
        # Right side - Output files
        output_frame = ttk.LabelFrame(file_frame, text="Output Files", padding="5")
        output_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0))
        
        self.output_list = tk.Text(output_frame, height=8, wrap=tk.NONE)
        output_scrollbar_y = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_list.yview)
        output_scrollbar_x = ttk.Scrollbar(output_frame, orient="horizontal", command=self.output_list.xview)
        self.output_list.configure(yscrollcommand=output_scrollbar_y.set, xscrollcommand=output_scrollbar_x.set)
        
        output_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        output_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.output_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(0,5))
        
        self.file_list.tag_configure("clickable", foreground="blue", underline=1)
        self.file_list.tag_bind("clickable", "<Button-1>", self.preview_file_from_event)
        self.file_list.tag_bind("clickable", "<Enter>", lambda e, w=self.file_list: w.config(cursor="hand2"))
        self.file_list.tag_bind("clickable", "<Leave>", lambda e, w=self.file_list: w.config(cursor=""))

        self.output_list.tag_configure("clickable", foreground="blue", underline=1) 
        self.output_list.tag_bind("clickable", "<Button-1>", self.preview_file_from_event)
        self.output_list.tag_bind("clickable", "<Enter>", lambda e, w=self.output_list: w.config(cursor="hand2"))
        self.output_list.tag_bind("clickable", "<Leave>", lambda e, w=self.output_list: w.config(cursor=""))
        
        # Convert button
        button_frame = ttk.Frame(main_content_frame, padding="10")
        button_frame.pack(fill=tk.X)
        ttk.Button(button_frame, text="Convert", command=self.convert_file).pack()
        
        # Log display bar at the very bottom of the root window
        self.latest_log_display = ttk.Label(self.root, text="Welcome! Select options and files to convert.", wraplength=self.root.winfo_screenwidth() - 40, relief="sunken", padding=5, anchor=tk.W)
        self.latest_log_display.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0), padx=10) # pady to give some space
        self.latest_log_display.bind("<Button-1>", self.toggle_log_history_view)
        self.latest_log_display.bind("<Enter>", lambda e: self.latest_log_display.config(cursor="hand2"))
        self.latest_log_display.bind("<Leave>", lambda e: self.latest_log_display.config(cursor=""))
        
        self.update_formats()
        debug_log.debug("FileConverterGUI create_widgets finished.")
        
    def update_formats(self):
        debug_log.debug(f"Updating formats for conversion type: {self.conversion_type.get()}")
        prev_type = getattr(self, '_prev_type', None)
        curr_type = self.conversion_type.get()
        
        if prev_type is not None and prev_type != curr_type:
            self.file_path.set('')
            self.file_entry.delete(0, tk.END)
            self.file_list.config(state=tk.NORMAL)
            self.file_list.delete(1.0, tk.END)
            self.file_list.config(state=tk.DISABLED)
            self.output_list.config(state=tk.NORMAL)
            self.output_list.delete(1.0, tk.END)
            self.output_list.config(state=tk.DISABLED)
            self._log_gui_event(f"Switched to '{curr_type}' mode. Cleared file lists.")
            debug_log.info(f"Conversion type changed from {prev_type} to {curr_type}. Inputs cleared.")
            
        self._prev_type = curr_type
        
        if curr_type == "to-pdf":
            self.format_dropdown['state'] = 'disabled'
            self.format_dropdown.set('pdf')
            self.output_format.set('pdf') # Ensure underlying var is also set
        else: # from-pdf
            self.format_dropdown['state'] = 'readonly'
            formats = ["txt", "jpg", "png", "docx"] # Added png
            self.format_dropdown['values'] = formats
            if not self.output_format.get() in formats: # Set default if current is invalid
                self.output_format.set(formats[0])
            self.format_dropdown.set(self.output_format.get())


    def _add_path_to_list_widget(self, widget, path):
        widget.config(state=tk.NORMAL)
        widget.insert(tk.END, path + "\n", "clickable")
        widget.config(state=tk.DISABLED)

    def validate_manual_path(self):
        path = self.file_entry.get().strip()
        debug_log.debug(f"Validating manual path: {path}")
        if os.path.exists(path):
            if self.conversion_type.get() == "to-pdf":
                 # For "to-pdf", multiple images are allowed if they are all images.
                 # Manual entry of multiple paths (semicolon separated) could be complex to validate here.
                 # For simplicity, manual entry adds one file at a time or one pre-joined string.
                 # If it's a single file, check its type.
                ext = os.path.splitext(path)[1].lower()
                image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
                office_exts = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
                text_exts = ['.txt']
                allowed_exts = image_exts + office_exts + text_exts
                
                if ';' in path: # User might have pasted multiple paths
                    paths = [p.strip() for p in path.split(';') if p.strip()]
                    all_images = all(os.path.splitext(p)[1].lower() in image_exts for p in paths)
                    if not all_images and len(paths) > 1:
                        messagebox.showerror("Error", "Multiple files via manual entry are only supported if all are images.")
                        self._log_gui_event("Error: Multiple manual paths must all be images.", is_error=True)
                        return
                    self.file_path.set(path) # Store the semicolon-separated string
                    self.file_list.config(state=tk.NORMAL)
                    self.file_list.delete(1.0, tk.END)
                    for p_item in paths:
                         self._add_path_to_list_widget(self.file_list, p_item)
                    self._log_gui_event(f"Added {len(paths)} files from manual input.")

                elif ext not in allowed_exts:
                    messagebox.showerror("Error", f"Unsupported file type for 'To PDF': {ext}")
                    self._log_gui_event(f"Error: Unsupported file type '{ext}' for 'To PDF' from manual input.", is_error=True)
                    return
                else: # Single valid file
                    self.file_path.set(path)
                    self.file_list.config(state=tk.NORMAL)
                    self.file_list.delete(1.0, tk.END) # Clear and add new single file
                    self._add_path_to_list_widget(self.file_list, path)
                    self._log_gui_event(f"Added file: {os.path.basename(path)}")


            else: # from-pdf, must be a single PDF
                if os.path.splitext(path)[1].lower() != '.pdf':
                    messagebox.showerror("Error", "For 'From PDF' conversion, input must be a PDF file.")
                    self._log_gui_event("Error: Manual input for 'From PDF' must be a PDF.", is_error=True)
                    return
                self.file_path.set(path)
                self.file_list.config(state=tk.NORMAL)
                self.file_list.delete(1.0, tk.END)
                self._add_path_to_list_widget(self.file_list, path)
                self._log_gui_event(f"Added PDF: {os.path.basename(path)}")

            self.file_entry.delete(0, tk.END)
        else:
            messagebox.showerror("Error", "Invalid file path. File does not exist.")
            self._log_gui_event(f"Error: Invalid manual file path '{path}'.", is_error=True)
            
    def preview_file_from_event(self, event):
        widget = event.widget
        index = widget.index(f"@{event.x},{event.y}")
        # Get the line number and then the content of that line
        line_num = index.split('.')[0]
        line_content = widget.get(f"{line_num}.0", f"{line_num}.end").strip()
        
        if line_content and os.path.exists(line_content):
            debug_log.info(f"Previewing file from list click: {line_content}")
            open_file(line_content) # open_file has its own logging
        elif line_content:
            self._log_gui_event(f"Cannot preview: File path '{line_content}' no longer exists or is invalid.", is_error=True)
            messagebox.showwarning("Preview Error", f"File path '{line_content}' not found. It might have been moved or deleted.")

            
    def browse_file(self):
        debug_log.debug(f"Browse file called. Conversion type: {self.conversion_type.get()}")
        filetypes = []
        filenames_or_name = None

        if self.conversion_type.get() == "to-pdf":
            image_types_tuple = ("Image files", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff")
            office_types_tuple = ("Office files", "*.doc;*.docx;*.xls;*.xlsx;*.ppt;*.pptx")
            text_types_tuple = ("Text files", "*.txt")
            all_supported_types = f"{image_types_tuple[1]};{office_types_tuple[1]};{text_types_tuple[1]}"
            
            filetypes = [
                ("All supported files", all_supported_types),
                image_types_tuple,
                office_types_tuple,
                text_types_tuple,
                ("All files", "*.*")
            ]
            # Allow multiple file selection only if all are images
            filenames_or_name = filedialog.askopenfilenames(title="Select file(s) to convert to PDF", filetypes=filetypes)
            
            if filenames_or_name: # It's a tuple of paths
                exts = [os.path.splitext(f)[1].lower() for f in filenames_or_name]
                are_all_images = all(ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff'] for ext in exts)
                
                if len(filenames_or_name) > 1 and not are_all_images:
                    messagebox.showerror("Error", "Multiple file selection is only supported if all files are images.")
                    self._log_gui_event("Error: Tried to select multiple non-image files for 'To PDF'.", is_error=True)
                    return
                
                # If single file, or multiple images, proceed
                paths_str = ';'.join(filenames_or_name)
                self.file_path.set(paths_str)
                
                self.file_list.config(state=tk.NORMAL)
                self.file_list.delete(1.0, tk.END)
                for fn in filenames_or_name:
                    self._add_path_to_list_widget(self.file_list, fn)
                self.file_list.config(state=tk.DISABLED)
                self._log_gui_event(f"Selected {len(filenames_or_name)} file(s) for 'To PDF'.")

        else: # from-pdf
            filetypes = [("PDF files", "*.pdf"), ("All files", "*.*")]
            filenames_or_name = filedialog.askopenfilename(title="Select PDF file to convert from", filetypes=filetypes)
            if filenames_or_name: # It's a single path string
                self.file_path.set(filenames_or_name)
                self.file_list.config(state=tk.NORMAL)
                self.file_list.delete(1.0, tk.END)
                self._add_path_to_list_widget(self.file_list, filenames_or_name)
                self.file_list.config(state=tk.DISABLED)
                self._log_gui_event(f"Selected PDF: {os.path.basename(filenames_or_name)}")

    def convert_file(self):
        input_path_str = self.file_path.get()
        debug_log.info(f"Convert button clicked. Input path string: '{input_path_str}'")

        if not input_path_str:
            self._log_gui_event("Please select a file or files for conversion.", level="ERROR", is_error=True)
            messagebox.showerror("Input Error", "No input file(s) selected.")
            return

        # Clear previous output list
        self.output_list.config(state=tk.NORMAL)
        self.output_list.delete(1.0, tk.END)
        self.output_list.config(state=tk.DISABLED)

        try:
            base_input_name = os.path.basename(input_path_str.split(';')[0]) # Use first file for log name
            self._log_gui_event(f"Starting conversion for: {base_input_name}...", 
                                detail_for_debug=f"Starting conversion for full path(s): {input_path_str}")
            
            sorted_files = []
            if self.conversion_type.get() == "to-pdf":
                sorted_files = convert_to_pdf(input_path_str)
            else: # from-pdf
                output_ext = self.output_format.get()
                if not output_ext:
                     self._log_gui_event("Please select an output format for 'From PDF' conversion.", level="ERROR", is_error=True)
                     messagebox.showerror("Input Error", "Output format not selected.")
                     return
                self._log_gui_event(f"Converting '{base_input_name}' from PDF to {output_ext}...",
                                    detail_for_debug=f"Converting '{input_path_str}' from PDF to {output_ext}...")
                sorted_files = convert_from_pdf(input_path_str, output_ext)
            
            # Update output list with the paths (typically from 'All' folder or specific outputs)
            # We want to show the files that are in the 'All' folder primarily, as they are the main result.
            self.output_list.config(state=tk.NORMAL)
            displayed_outputs = []
            unique_all_folder_files = {f for f in sorted_files if os.path.dirname(f).endswith('All')}

            for file_path_in_all in sorted(list(unique_all_folder_files)): # Sort for consistent display
                self._add_path_to_list_widget(self.output_list, file_path_in_all)
                displayed_outputs.append(os.path.basename(file_path_in_all))
            self.output_list.config(state=tk.DISABLED)
                
            success_msg = f"Conversion successful! Output(s): {', '.join(displayed_outputs) if displayed_outputs else 'None'}"
            self._log_gui_event(success_msg, detail_for_debug=f"Conversion successful. All sorted files: {sorted_files}")

        except ValueError as ve: # Expected errors like unsupported type, soffice not found, etc.
            self._log_gui_event(f"Conversion error: {str(ve)}", level="ERROR", is_error=True)
            # Backend function should have logged details via user_log.error and debug_log.error/exception
            messagebox.showerror("Conversion Error", str(ve))
        except subprocess.CalledProcessError as cpe:
            err_details = cpe.stderr.decode(errors='ignore') if cpe.stderr else (cpe.stdout.decode(errors='ignore') if cpe.stdout else "No details from subprocess.")
            self._log_gui_event(f"Office conversion process error: {err_details.strip()[:200]}", level="ERROR", is_error=True)
            debug_log.exception(f"CalledProcessError during conversion of {input_path_str}") # Full trace for debug
            messagebox.showerror("Process Error", f"External process failed: {err_details.strip()[:500]}")
        except RuntimeError as rte: # E.g. if conversion produced no output
            self._log_gui_event(f"Conversion runtime error: {str(rte)}", level="ERROR", is_error=True)
            debug_log.exception(f"RuntimeError during conversion of {input_path_str}")
            messagebox.showerror("Runtime Error", str(rte))
        except Exception as e: # Unexpected errors
            self._log_gui_event(f"An unexpected error occurred: {str(e)}", level="ERROR", is_error=True)
            debug_log.exception(f"Unexpected error in GUI convert_file for {input_path_str}") # Full trace for debug
            messagebox.showerror("Unexpected Error", f"An critical error occurred: {str(e)}")

    def toggle_log_history_view(self, event=None):
        debug_log.debug("Toggling log history view.")
        if self.log_history_window and self.log_history_window.winfo_exists():
            self.log_history_window.destroy()
            self.log_history_window = None
            self.latest_log_display.config(relief="sunken")
            debug_log.info("Closed log history window.")
            return

        self.latest_log_display.config(relief="raised")
        self.log_history_window = tk.Toplevel(self.root)
        self.log_history_window.title("User Activity Log")
        
        # Position and size the log window
        width = self.root.winfo_width() // 2
        height = self.root.winfo_height() // 3
        x_pos = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y_pos = self.root.winfo_y() + (self.root.winfo_height() - height) - 60 # Position above bottom bar
        self.log_history_window.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

        toolbar = ttk.Frame(self.log_history_window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        refresh_button = ttk.Button(toolbar, text="Refresh", command=self.refresh_log_history_view)
        refresh_button.pack(side=tk.LEFT)
        clear_button = ttk.Button(toolbar, text="Clear Log File", command=self.clear_user_log_file)
        clear_button.pack(side=tk.LEFT, padx=5)


        text_frame = ttk.Frame(self.log_history_window)
        text_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=5, pady=(0,5))

        self.log_history_text_widget = tk.Text(text_frame, wrap=tk.WORD, height=15, relief=tk.FLAT)
        scrollbar_y = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_history_text_widget.yview)
        scrollbar_x = ttk.Scrollbar(text_frame, orient="horizontal", command=self.log_history_text_widget.xview)
        self.log_history_text_widget.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.log_history_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.log_history_text_widget.config(state=tk.DISABLED) # Read-only

        self.refresh_log_history_view()
        self.log_history_window.protocol("WM_DELETE_WINDOW", self.on_log_history_close)
        debug_log.info("Opened log history window.")

    def on_log_history_close(self):
        if self.log_history_window:
            self.log_history_window.destroy()
            self.log_history_window = None
            self.latest_log_display.config(relief="sunken")
            debug_log.info("Log history window closed via WM_DELETE_WINDOW.")

    def refresh_log_history_view(self):
        if not (self.log_history_window and self.log_history_window.winfo_exists() and self.log_history_text_widget):
            debug_log.debug("Log history window/widget not available for refresh.")
            return
        debug_log.debug("Refreshing log history view.")
        self.log_history_text_widget.config(state=tk.NORMAL)
        self.log_history_text_widget.delete(1.0, tk.END)
        try:
            if os.path.exists(USER_LOG_FILE_PATH):
                with open(USER_LOG_FILE_PATH, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    self.log_history_text_widget.insert(tk.END, log_content)
                self.log_history_text_widget.see(tk.END) # Scroll to bottom
                debug_log.info(f"Loaded content from {USER_LOG_FILE_PATH} into log history view.")
            else:
                self.log_history_text_widget.insert(tk.END, "User log file not found or is empty.")
                user_log.warning("User log file not found when trying to display history in GUI.")
        except Exception as e:
            error_msg = f"Error reading user log file: {e}"
            self.log_history_text_widget.insert(tk.END, error_msg)
            debug_log.exception(error_msg)
        finally:
            self.log_history_text_widget.config(state=tk.DISABLED)

    def clear_user_log_file(self):
        debug_log.info("Attempting to clear user log file.")
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the user log file? This cannot be undone."):
            try:
                with open(USER_LOG_FILE_PATH, 'w', encoding='utf-8') as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - User log file cleared by user.\n")
                self._log_gui_event("User log file cleared.")
                debug_log.info("User log file cleared successfully by user.")
                self.refresh_log_history_view() # Refresh display
            except Exception as e:
                self._log_gui_event(f"Failed to clear user log file: {e}", is_error=True)
                debug_log.exception("Error clearing user log file.")
                messagebox.showerror("Error", f"Could not clear log file: {e}")
        else:
            debug_log.info("User cancelled clearing of log file.")


if __name__ == "__main__":
    user_log.info("Application started.")
    debug_log.info("Application __main__ block initiated.")
    root = tk.Tk()
    app = FileConverterGUI(root)
    
    def on_closing():
        user_log.info("Application closing.")
        debug_log.info("Application GUI closing sequence initiated.")
        if app.log_history_window and app.log_history_window.winfo_exists():
            app.log_history_window.destroy()
        root.destroy()
        user_log.info("Application closed.")
        debug_log.info("Application GUI destroyed. Exiting.")

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
