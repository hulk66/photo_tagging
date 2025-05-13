# Script to correct EXIF dates in image files based on filename patterns.
# This script uses the exiftool library to read and write EXIF data.


import os
import re
from datetime import datetime
import exiftool
import logging
from logging.handlers import RotatingFileHandler
import argparse
from tagger import get_image_files
from tqdm import tqdm



# Add logging to the script
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler("date_correction.log", maxBytes=10**7, backupCount=5),
        # logging.StreamHandler()
    ]
)

def dates_differ_more_than_24_hours(date1, date2):
    """
    Check if two dates differ by more than 24 hours.
    """
    return abs((date1 - date2).total_seconds()) > 24 * 3600

def set_exif_date(file_path, date, modify=True):
    try:
        # Use exiftool to set the date
        with exiftool.ExifToolHelper() as helper:            
            tags = helper.get_tags(file_path, tags=["DateTimeOriginal", "CreateDate", "ModifyDate"])
            if not "EXIF:DateTimeOriginal" in tags[0] or not "EXIF:CreateDate" in tags[0]:
                logger.info(f"File {file_path} does not have EXIF DateTimeOriginal or CreateDate tags.")
                date_str = date.strftime("%Y:%m:%d %H:%M:%S")
                logger.info(f"Setting EXIF date for {file_path} to {date_str}")
                if modify:
                    helper.set_tags(file_path, {"EXIF:DateTimeOriginal": date_str, "EXIF:CreateDate": date_str, "EXIF:ModifyDate": date_str})
            else:
                logger.debug(f"File {file_path} already has EXIF DateTimeOriginal and CreateDate tags.")
                # Date is in Exif data, now check if it is the same as the one in the filename
                date_org_str = tags[0]["EXIF:DateTimeOriginal"]
                create_date_str = tags[0]["EXIF:CreateDate"]
                modify_date_str = tags[0]["EXIF:ModifyDate"]
                # convert date string to datetime object
                date_org = datetime.strptime(date_org_str, "%Y:%m:%d %H:%M:%S")
                create_date = datetime.strptime(create_date_str, "%Y:%m:%d %H:%M:%S")
                modify_date = datetime.strptime(modify_date_str, "%Y:%m:%d %H:%M:%S")
         
                if dates_differ_more_than_24_hours(date, date_org) or dates_differ_more_than_24_hours(date, create_date):
                    # set the date
                    logger.info("Date differs more than 24 hours, updating EXIF date")
                    if modify:
                        helper.set_tags(file_path, {"EXIF:DateTimeOriginal": date, "EXIF:CreateDate": date_org_str, "EXIF:ModifyDate": date_org_str})
                    logger.debug(f"Updated {file_path} from {date_org_str} to {date}")
                else:
                    logger.debug(f"Date already correct for {file_path}: {date_org_str}")
    except Exception as e:
        logger.error(f"Failed to set EXIF date for {file_path}: {e}")

def find_and_set_exif_date(directory):
    logger.info(f"Scanning directory: {directory}")
    files = get_image_files(directory)
    counter = 0
    total = len(files)
    for image_path in tqdm(files, desc="Processing images...", leave=False):

        # strip the path to get the file name
        _, file = os.path.split(image_path)
        matched = False
        if file.lower().endswith(('.jpg', '.heic')):
            date_pattern = re.compile(r'((\d{2})-(\d{2})-(\d{2}) (\d{2})[-\.](\d{2})[-\.](\d{2})(.*))')
            match = date_pattern.search(file)
            if match:
                matched = True
                logger.debug(f"Matched date pattern in file: {file}")
                _, yy, mm, dd, hh, minute, ss, _ = match.groups()
                yyyy = f"20{yy}"
                date = datetime(int(yyyy), int(mm), int(dd), int(hh), int(minute), int(ss))
                set_exif_date(image_path, date, True)
            date_pattern = re.compile(r'((IMG|PANO)_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})(.*))')
            match = date_pattern.search(file)
            if match:
                matched = True
                logger.debug(f"Matched IMG/PANO pattern in file: {file}")
                _, _, yyyy, mm, dd, hh, minute, ss, _ = match.groups()
                date = datetime(int(yyyy), int(mm), int(dd), int(hh), int(minute), int(ss))
                set_exif_date(image_path, date, True)

        if not matched:
            logger.debug(f"No date pattern matched for file: {file}")
        logger.info(f"Processed {counter}/{total} images")
        counter += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Correct EXIF dates in image files based on filename patterns.")
    parser.add_argument("directory", type=str, help="Directory to scan for image files.")
    args = parser.parse_args()
    directory = args.directory
    if not os.path.isdir(directory):
        logger.error(f"Provided directory does not exist: {directory}")
        exit(1)
    logger.debug("Starting date correction script")
    find_and_set_exif_date(directory)
    logger.debug("Date correction script completed")