import os
import re
import csv
import shutil
import time
import datetime
import logging
import hashlib
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Logging setup
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(levelname)s] - %(message)s',
                    handlers=[logging.FileHandler("file_revision.log"),
                              logging.StreamHandler()])

FILE_PATHS = {}
LATEST_SUFFIX = "(Latest)"
CONFIG_RELOAD_INTERVAL = 10  # Reload the config file every 10 seconds


def load_config():
    new_file_paths = {}
    config_file = 'file_config.csv'

    # Check if config file exists, if not create it.
    if not os.path.exists(config_file):
        logging.warning(f"{config_file} not found, creating...")

        # Create default csv file
        with open(config_file, mode='w', newline='') as file:
            fieldnames = ['file_path', 'revision_dir']
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            writer.writeheader()
            # Add default rows here if necessary
            # writer.writerow({'file_path': 'default_path', 'revision_dir': 'default_revision_dir'})

    try:
        with open(config_file, mode='r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                file_path = Path(row['file_path'])

                if not file_path.exists():
                    logging.warning(f"File path does not exist: {file_path}")
                    continue

                if not file_path.parent.exists():
                    logging.warning(f"Directory for file does not exist: {file_path.parent}")
                    continue

                new_file_paths[file_path] = row['revision_dir']

    except Exception as e:
        logging.error(f"Error reading CSV file: {e}")

    return new_file_paths

def initialize_revisions_directory(file_path, revisions_dir_name):
    try:
        revisions_dir = file_path.parent / revisions_dir_name
        if not revisions_dir.exists():
            revisions_dir.mkdir()
        return revisions_dir
    except Exception as e:
        logging.error(f"Error initializing revisions directory for {file_path}: {e}")
        return None


def handle_file_modification(event):
    try:
        modified_path = Path(event.src_path)
        if modified_path in FILE_PATHS.keys():
            revisions_dir_name = FILE_PATHS[modified_path]
            revisions_dir = initialize_revisions_directory(modified_path, revisions_dir_name)
            if revisions_dir is None:
                return

            # Calculate MD5 checksum of the modified file
            with open(modified_path, "rb") as file:
                file_contents = file.read()
                md5_checksum = hashlib.md5(file_contents).hexdigest()

            revision_date = datetime.datetime.now().strftime('%d-%m-%Y')
            revision_counter = 1
            last_file_md5 = None

            # Find the last file in the revisions directory and get its MD5 checksum
            for existing_file in revisions_dir.iterdir():
                match = re.search(r"(\d+)_" + re.escape(modified_path.stem), existing_file.name)
                if match:
                    last_file_md5 = hashlib.md5(existing_file.read_bytes()).hexdigest()
                    existing_counter = int(match.group(1))
                    revision_counter = max(revision_counter, existing_counter + 1)

            # Compare the MD5 checksum of the modified file with the last file's MD5 checksum
            if md5_checksum == last_file_md5:
                logging.info(f"Duplicate file detected, not creating a new revision for {modified_path}")
                return

            new_revision_name = f"{str(revision_counter).zfill(3)}_{modified_path.stem}_{revision_date}{modified_path.suffix}"
            shutil.copy2(modified_path, revisions_dir / new_revision_name)
            logging.info(f"New revision created: {new_revision_name}")

    except Exception as e:
        logging.error(f"Error handling file modification for {event.src_path}: {e}")


class FileModifiedHandler(FileSystemEventHandler):
    def on_modified(self, event):
        handle_file_modification(event)

if __name__ == '__main__':
    event_handler = FileModifiedHandler()
    observer = Observer()

    try:
        while True:
            new_file_paths = load_config()
            if new_file_paths != FILE_PATHS:
                FILE_PATHS = new_file_paths
                logging.info("Configuration reloaded.")

                observer.stop()
                observer = Observer()

                for dir_path in set(file_path.parent for file_path in FILE_PATHS.keys()):
                    if not dir_path.exists():
                        logging.warning(f"Skipping non-existent directory: {dir_path}")
                        continue
                    observer.schedule(event_handler, path=str(dir_path), recursive=False)

                observer.start()
                logging.info("Observer started.")

            time.sleep(CONFIG_RELOAD_INTERVAL)

    except KeyboardInterrupt:
        observer.stop()
        logging.info("Observer stopped due to KeyboardInterrupt.")

    observer.join()
    logging.info("Observer thread has joined.")
