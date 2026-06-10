# MemoryMend - Google Takeout Metadata Fixer

MemoryMend is a simple tool designed to fix the date and time of your photos and videos after exporting them via Google Takeout. When you download your data, Google separates the original timestamps from your files, causing your media to display incorrect dates. This script automatically reads the original dates and restores them to your files, while keeping your folders clean and organized.

Please note: This tool specifically restores the **date and time** metadata. It does not alter or restore other metadata, such as GPS locations or camera details.

> Disclaimer: This project is for educational and personal data recovery purposes only. Always make a backup copy of your media folders before running the script.

## Quick Start: Installation and Usage

There is no complex installation required. Follow these steps to fix your media dates:

1. Download the standalone ExifTool executable from the [Official ExifTool Website](https://exiftool.org/).
2. Unzip your Google Takeout archive on your computer. Inside, locate the main folder containing your media, typically named `Google Photos`.
3. Move the following items directly inside that `Google Photos` folder:
   - The `memorymend.py` script.
   - The `exiftool.exe` file.
   - The `exiftool_files` directory (required for Windows users, included in the ExifTool download).
4. Double-click the `memorymend.py` script to run it.
5. A terminal window will open. Simply follow the on-screen prompts and press `Enter` when requested to move through the phases until completed.

---

## Table of Contents
- What Is It?
- How It Works?
- Prerequisites
- Example Output
- Contributing
- License
- Third-Party Licenses

## What Is It?
When exporting photos and videos from Google Photos via Google Takeout, the original "Date Taken" metadata is often stripped from the media files and stored in separate `.json` sidecar files. To make matters worse, Google randomly alters or truncates these JSON filenames (e.g., creating variations like `image(1).jpg` paired with `image.jpg(1).json` or appending truncated strings like `.supplemental-metada.json`).

MemoryMend solves this chaos behind the scenes. It scans your directories, uses an advanced Universal Regex to normalize anomalous JSON names so they perfectly match their media counterparts, reads the original Unix timestamp, and uses ExifTool to inject the correct dates back into your files in a single mass execution block. 

Once updated, it automatically purges the used JSON files and isolates any unpairable files into dedicated folders, leaving your directories completely clean.

## How It Works?
The script executes in four distinct, interactive phases:

1. Phase 1 (System Verifications): Automatically verifies and installs required Python packages (`tqdm`) if missing. It also verifies the presence of ExifTool in the root folder, automatically handling and renaming common variations like `exiftool(-k).exe`.
2. Phase 2 (Normalizing Name Anomalies): Scans all directories using a Universal Regex pattern to fix truncated extensions and misplaced numbering in JSON files, restoring perfect pairing alignment.
3. Phase 3 (Intelligent Pairing & Execution): Extracts the `photoTakenTime` timestamp from the JSON files, matches them to the correct images/videos, generates a temporary optimized batch file, and sends the data to ExifTool for mass metadata correction.
4. Phase 4 (Cleanup & Organize): Deletes all successfully processed JSON files. Any remaining orphaned JSONs or unpaired media files are cleanly moved into local `date_unknown` directories so your main folders remain spotless.

## Prerequisites
- Python 3.x installed on your system.
- ExifTool (by Phil Harvey) executable placed in the same directory as the script.
  - Windows users: Ensure both `exiftool.exe` and the `exiftool_files` folder are in the root directory.

## Example Output
```text
===================================================
      MemoryMend - Google Takeout Metadata Fixer   
===================================================

INITIALIZING PHASE 1: System Verifications

[MemoryMend] Checking required packages...
Success: 'tqdm' is installed.

[MemoryMend] Verifying ExifTool presence...
Success: Found 'exiftool.exe' file
Success: Found 'exiftool_files' directory.

[MemoryMend] Phase 1 Completed!
(press enter to continue)

===================================================

INITIALIZING PHASE 2: Name Normalization
[MemoryMend] Scanning directories for anomalous JSON names...
Found 2538 JSON files. Checking for naming anomalies...
Normalizing: 100%|████████████████████████████████| 2538/2538 [00:01<00:00, file/s]
Success: Normalized 3 anomalous JSON file names.

[MemoryMend] Phase 2 Completed!
(press enter to continue)

===================================================

INITIALIZING PHASE 3: Intelligent Pairing & Execution
Found 2535 JSON files. Extracting timestamps and pairing...
Pairing: 100%|████████████████████████████████████| 2535/2535 [00:02<00:00, file/s]

Success: Paired 2530 files successfully.
Notice: 5 JSON files had no corresponding media file (ignored).

[MemoryMend] Sending data to ExifTool for mass metadata execution...
             This might take a while depending on the number of files. Please wait.

Success: ExifTool execution completed successfully!
Your files have been restored to their original dates.

[MemoryMend] Phase 3 Completed!
(press enter to continue)

===================================================

INITIALIZING PHASE 4: Cleanup & Organize

[MemoryMend] Running workspace cleanup and organization...
Success: Deleted 2530 processed JSON files.
Notice: Moved 5 JSONs and 3 media files to 'date_unknown' folders.

[MemoryMend] Phase 4 Completed!

===================================================
      ALL PROCESSES COMPLETED SUCCESSFULLY!        
===================================================
Press Enter to exit...
```


## Contributing
Pull requests are welcome. Feel free to open issues for suggestions, bug reports, or performance improvements to help optimize the processing workflow.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Third-Party Licenses
This tool relies on the following third-party software:
- ExifTool by Phil Harvey: Distributed under its own licensing terms (Artistic License / GPL).
- tqdm: Fast, Extensible Progress Meter for Python, licensed under the MIT License.
