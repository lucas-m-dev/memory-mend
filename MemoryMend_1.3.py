import os
import sys
import subprocess
import re
import json
import shutil
from datetime import datetime

# Defined required third-party packages
REQUIRED_PACKAGES = ["tqdm"]


def exit_with_error(message, solution=None, url=None):
    """
    Unified error handler to provide context, solutions, and pause before exit.
    """
    print(f"\n[ERROR] {message}")
    if solution:
        print(f"    Solution: {solution}")
    if url:
        print(f"    Get help here: {url}")
    input("\nPress Enter to exit...")
    sys.exit(1)


def install_packages():
    """
    Checks if required external Python packages are installed.
    If not, it automatically installs them using pip.
    """
    print("\n[MemoryMend] Checking required packages...")
    for package in REQUIRED_PACKAGES:
        try:
            # Try to import the package to check if it exists
            __import__(package)
            print(f"Success: '{package}' is installed.")
        except ImportError:
            print(f"Installing '{package}' automatically...")
            try:
                # Run pip install
                subprocess.check_call([sys.executable, "-m", "pip", "install", package],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"Success: '{package}' is installed.")
            except subprocess.CalledProcessError:
                exit_with_error(f"Failed to install '{package}'.", "Check your internet connection.")


def verify_exiftool(base_path):
    """
    Verifies if ExifTool and its required files/folders are present in the root directory.
    Handles 'exiftool(-k).exe' automatically by renaming it.
    """
    print("\n[MemoryMend] Verifying ExifTool presence...")

    # Define platform-specific names
    is_windows = os.name == 'nt'
    standard_name = "exiftool.exe" if is_windows else "exiftool"
    alternative_name = "exiftool(-k).exe" if is_windows else "exiftool(-k)"

    standard_path = os.path.join(base_path, standard_name)
    alternative_path = os.path.join(base_path, alternative_name)

    if os.path.isfile(standard_path):
        print(f"Success: Found '{standard_name}' file")
    elif os.path.isfile(alternative_path):
        os.rename(alternative_path, standard_path)
        print(f"Found {alternative_name}. Renaming it to {standard_name} for compatibility...")
    else:
        exit_with_error(f"{standard_name} or {alternative_name} not found!",
                        "Place the executable in the root folder.",
                        "https://sourceforge.net/projects/exiftool/")
    exiftool_executable = standard_path

    # Check for the 'exiftool_files' folder (Only applicable for Windows)
    if is_windows:
        required_folder = os.path.join(base_path, "exiftool_files")
        if os.path.isdir(required_folder):
            print("Success: Found 'exiftool_files' directory.")
        else:
            exit_with_error("'exiftool_files' folder is missing!",
                            "Extract the full ExifTool package, not just the .exe file.")

    return exiftool_executable


def normalize_json_names(base_path):
    """
    Scans all directories (skipping 'exiftool_files') for anomalous .json names
    and renames them using a Universal Regex so they match their corresponding image/video files.
    """
    print("\n[MemoryMend] Scanning directories for anomalous JSON names...")

    # UNIVERSAL REGEX PATTERN
    # Matches: BaseName + [Optional Extension] + [Optional Google Suffix] + (Number) + .json
    universal_pattern = re.compile(
        r'^(.*?)(\.[a-zA-Z0-9_-]+)?(\.suppl|\.supplemental-metadata)?\((\d+)\)\.json$',
        re.IGNORECASE
    )

    json_files = []

    # Pre-scan to gather all JSON files for the progress bar
    for root, dirs, files in os.walk(base_path):
        # Prevent stepping into the exiftool_files directory
        if 'exiftool_files' in dirs:
            dirs.remove('exiftool_files')

        for filename in files:
            if filename.lower().endswith('.json'):
                json_files.append((root, filename))

    if not json_files:
        print("Notice: No JSON files found in the directory.")
        return
    print(f"Found {len(json_files)} JSON files. Checking for naming anomalies...")
    renamed_count = 0

    # Import tqdm dynamically here
    from tqdm import tqdm

    # Process files with a progress bar
    for root, filename in tqdm(json_files, desc="Normalizing", unit="file"):
        old_filepath = os.path.join(root, filename)

        # Apply the Universal Regex
        match = universal_pattern.match(filename)

        if match:
            base_name = match.group(1)
            extension = match.group(2) or ""
            google_suffix = match.group(3) or ""
            number = match.group(4)

            # Reconstruct the name perfectly
            new_filename = f"{base_name}({number}){extension}{google_suffix}.json"

            new_filepath = os.path.join(root, new_filename)

            # Safety check: avoid overwriting if the target already exists
            if not os.path.exists(new_filepath):
                try:
                    os.rename(old_filepath, new_filepath)
                    renamed_count += 1
                except Exception as e:
                    tqdm.write(f"[ERROR] Could not rename {filename}: {e}")
            else:
                tqdm.write(f"[WARNING] Target file already exists, skipped: {new_filename}")

    print(f"Success: Normalized {renamed_count} anomalous JSON file names.")


def pair_and_execute_exiftool(base_path, exiftool_executable):
    """
    Scans for normalized JSON files, extracts the 'photoTakenTime' timestamp,
    pairs them with their corresponding media files, and runs ExifTool in bulk mode.
    Returns a list of successfully processed JSON and media file paths for cleanup.
    """
    json_files = []
    processed_jsons = []  # Track JSON files successfully paired
    processed_medias = []  # Track media files successfully updated

    # 1. Gather all JSON files
    for root, dirs, files in os.walk(base_path):
        if 'exiftool_files' in dirs:
            dirs.remove('exiftool_files')

        for filename in files:
            if filename.lower().endswith('.json'):
                json_files.append((root, filename))

    if not json_files:
        print("Notice: No JSON files available for pairing.")
        return processed_jsons, processed_medias
    print(f"\nFound {len(json_files)} JSON files. Extracting timestamps and pairing...")

    from tqdm import tqdm

    paired_count = 0
    missing_media_count = 0
    args_file_path = os.path.join(base_path, "exiftool_args.txt")

    # 2. Open the arguments file with UTF-8 encoding (crucial for foreign characters in folders)
    with open(args_file_path, "w", encoding="utf-8") as arg_file:
        # Require utf8 charset for file paths
        arg_file.write("-charset\nfilename=utf8\n")

        for root, json_filename in tqdm(json_files, desc="Pairing", unit="file"):
            json_filepath = os.path.join(root, json_filename)

            # Determine the corresponding media filename
            # Remove '.json'
            media_filename = json_filename[:-5]

            # Dynamic regex to remove any variation or truncation of '.supplemental-metadata'
            media_filename = re.sub(
                r'\.(supplemental-metadata|supplemental-metadat|supplemental-metada|supplemental-metad|supplemental-meta|supplemental-met|supplemental-me|supplemental-m|supplemental-|supplemental|supplementa|supplement|supplemen|suppleme|supplem|supple|suppl|supp|sup|su|s)$',
                '', media_filename, flags=re.IGNORECASE
            )

            media_filepath = os.path.join(root, media_filename)

            # Check if the media file actually exists next to the JSON
            if os.path.exists(media_filepath):
                try:
                    # Open and parse the JSON to find the timestamp
                    with open(json_filepath, "r", encoding="utf-8") as jf:
                        data = json.load(jf)

                    timestamp_str = data.get("photoTakenTime", {}).get("timestamp")

                    if timestamp_str:
                        # Convert Unix timestamp to ExifTool format (YYYY:MM:DD HH:MM:SS)
                        timestamp_int = int(timestamp_str)
                        dt_object = datetime.fromtimestamp(timestamp_int)
                        exif_date_format = dt_object.strftime("%Y:%m:%d %H:%M:%S")

                        # Write the instructions for this specific file to the ExifTool Batch File
                        arg_file.write("-overwrite_original\n")
                        arg_file.write(f"-AllDates={exif_date_format}\n")
                        arg_file.write(f"-FileCreateDate={exif_date_format}\n")
                        arg_file.write(f"-FileModifyDate={exif_date_format}\n")
                        arg_file.write(f"{media_filepath}\n")
                        arg_file.write("-execute\n")

                        paired_count += 1
                        # Save absolute paths to avoid discrepancies during cleanup
                        processed_jsons.append(os.path.abspath(json_filepath))
                        processed_medias.append(os.path.abspath(media_filepath))
                except Exception as e:
                    tqdm.write(f"[ERROR] Failed to read timestamp from {json_filename}: {e}")
            else:
                missing_media_count += 1

    print(f"\nSuccess: Paired {paired_count} files successfully.")
    if missing_media_count > 0:
        print(f"Notice: {missing_media_count} JSON files had no corresponding media file (ignored).")

    # 3. Execute ExifTool in Bulk Mode
    if paired_count > 0:
        print("\n[MemoryMend] Sending data to ExifTool for mass metadata execution...")
        print("             This might take a while depending on the number of files. Please wait.")

        try:
            # Run ExifTool pointing to the argument file we just created
            subprocess.run(
                [exiftool_executable, "-@", args_file_path],
                stdout=subprocess.DEVNULL,  # Hides the massive ExifTool output
                stderr=subprocess.STDOUT
            )
            print("\nSuccess: ExifTool execution completed successfully!")
            print("Your files have been restored to their original dates.")
        except Exception as e:
            print(f"\n[ERROR] ExifTool failed to execute: {e}")

    # 4. Cleanup the temporary args file
    if os.path.exists(args_file_path):
        os.remove(args_file_path)

    return processed_jsons, processed_medias


def cleanup_and_organize(base_path, processed_jsons, processed_medias):
    """
    Cleans up the working directories by:
    1. Deleting all JSON files that were successfully used to pair metadata.
    2. Moving any remaining (orphaned) JSON files and UNPAIRED media files into 'date_unknown' directories.
    """
    print("\n[MemoryMend] Running workspace cleanup and organization...")

    # Convert lists to absolute path sets for ultra-fast lookup
    processed_jsons_set = set(os.path.abspath(p) for p in processed_jsons)
    processed_medias_set = set(os.path.abspath(p) for p in processed_medias)
    current_script = os.path.abspath(__file__)

    # 1. Delete successfully processed JSON files
    deleted_count = 0
    for json_path in processed_jsons_set:
        if os.path.exists(json_path):
            try:
                os.remove(json_path)
                deleted_count += 1
            except Exception as e:
                print(f"[ERROR] Could not delete {json_path}: {e}")

    if deleted_count > 0:
        print(f"Success: Deleted {deleted_count} processed JSON files.")

    # 2. Find and move orphaned JSON files and unmatched media files
    orphaned_json_count = 0
    orphaned_media_count = 0

    for root, dirs, files in os.walk(base_path):
        # Prevent stepping into required or previously created directories
        if 'exiftool_files' in dirs:
            dirs.remove('exiftool_files')
        if 'date_unknown' in dirs:
            dirs.remove('date_unknown')

        # Define the target unknown directory for the current root
        unknown_dir = os.path.join(root, "date_unknown")

        for filename in files:
            filepath = os.path.abspath(os.path.join(root, filename))

            # Safety rule: Ignore the script itself and ExifTool system tools
            if filepath == current_script or filename.lower() in ["exiftool.exe", "exiftool", "exiftool_args.txt"]:
                continue

            if filename.lower().endswith('.json'):
                # If it's a JSON and wasn't successfully used for pairing
                if filepath not in processed_jsons_set:
                    if not os.path.exists(unknown_dir):
                        os.makedirs(unknown_dir)
                    new_filepath = os.path.join(unknown_dir, filename)
                    try:
                        shutil.move(filepath, new_filepath)
                        orphaned_json_count += 1
                    except Exception as e:
                        print(f"[ERROR] Could not move JSON {filename}: {e}")
            else:
                # If it's a media file (or anything else) and wasn't successfully modified
                if filepath not in processed_medias_set:
                    if not os.path.exists(unknown_dir):
                        os.makedirs(unknown_dir)
                    new_filepath = os.path.join(unknown_dir, filename)
                    try:
                        shutil.move(filepath, new_filepath)
                        orphaned_media_count += 1
                    except Exception as e:
                        print(f"[ERROR] Could not move media file {filename}: {e}")

    if orphaned_json_count > 0 or orphaned_media_count > 0:
        print(
            f"Notice: Moved {orphaned_json_count} JSONs and {orphaned_media_count} media files to 'date_unknown' folders.")
    else:
        print("Success: No orphaned files found. Workspace is clean.")


def main():
    """
    Main execution block.
    """
    print("===================================================")
    print("      MemoryMend - Google Takeout Metadata Fixer   ")
    print("===================================================")
    print()
    print("INITIALIZING PHASE 1: System Verifications")

    install_packages()
    root_dir = os.path.dirname(os.path.abspath(__file__))
    exiftool_executable = verify_exiftool(root_dir)

    print("\n[MemoryMend] Phase 1 Completed!")
    input("(press enter to continue)")
    print("\n===================================================\n")
    print("INITIALIZING PHASE 2: Normalizing Name Anomalies")

    normalize_json_names(root_dir)

    print("\n[MemoryMend] Phase 2 Completed!")
    input("(press enter to continue)")
    print("\n===================================================\n")
    print("INITIALIZING PHASE 3: Intelligent Pairing & Execution")

    processed_jsons, processed_medias = pair_and_execute_exiftool(root_dir, exiftool_executable)

    print("\n[MemoryMend] Phase 3 Completed!")
    input("(press enter to continue)")
    print("\n===================================================\n")
    print("INITIALIZING PHASE 4: Cleanup & Organize")

    cleanup_and_organize(root_dir, processed_jsons, processed_medias)

    print("\n[MemoryMend] Phase 4 Completed!")
    print("\n===================================================")
    print("      ALL PROCESSES COMPLETED SUCCESSFULLY!        ")
    print("===================================================")
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()