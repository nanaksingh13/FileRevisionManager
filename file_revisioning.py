import os
import re
import csv
import shutil
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
FILE_NAME_PATTERN = re.compile(r"(\d+)_" + r"(.+?)_\d{2}-\d{2}-\d{4}")

class FileRevisionManager:
    def __init__(self):
        self.FILE_PATHS = {}
        self.observer = Observer()
        self.event_handler = FileModifiedHandler(self)
        self.running = False

    def load_config(self):
        new_file_paths = {}
        config_file = 'file_config.csv'

        # Check if config file exists, if not create it.
        if not os.path.exists(config_file):
            logging.warning(f"{config_file} not found, creating...")
            with open(config_file, mode='w', newline='') as file:
                fieldnames = ['file_path', 'revision_dir']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()

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
            logging.info(f"Loaded configuration")

        except Exception as e:
            logging.error(f"Error reading CSV file: {e}")

        return new_file_paths

    def initialize_revisions_directory(self, file_path, revisions_dir_name):
        print(f"Function received: {file_path}, {revisions_dir_name}")
        try:
            revisions_dir = file_path.parent / revisions_dir_name
            if not revisions_dir.exists():
                revisions_dir.mkdir()
            return revisions_dir
        except Exception as e:
            logging.error(f"Error initializing revisions directory for {file_path}: {e}")
            return None

    def handle_file_modification(self, event):
        try:
            modified_path = Path(event.src_path)
            if modified_path in self.FILE_PATHS.keys():
                revisions_dir_name = self.FILE_PATHS[modified_path]
                revisions_dir = self.initialize_revisions_directory(modified_path, revisions_dir_name)

                if revisions_dir is None:
                    return

                with open(modified_path, "rb") as file:
                    file_contents = file.read()
                    md5_checksum = hashlib.md5(file_contents).hexdigest()

                revision_date = datetime.datetime.now().strftime('%d-%m-%Y')
                revision_counter = 1
                last_file_md5 = None

                for existing_file in sorted(revisions_dir.iterdir(), reverse=True):  # Start from the most recent
                    match = FILE_NAME_PATTERN.search(existing_file.name)
                    if match:
                        last_file_md5 = hashlib.md5(existing_file.read_bytes()).hexdigest()
                        revision_counter = int(match.group(1)) + 1
                        break

                if md5_checksum == last_file_md5:
                    logging.info(f"Duplicate file detected, not creating a new revision for {modified_path}")
                    return

                new_revision_name = f"{str(revision_counter).zfill(3)}_{modified_path.stem}_{revision_date}{modified_path.suffix}"
                shutil.copy2(modified_path, revisions_dir / new_revision_name)
                logging.info(f"New revision created: {new_revision_name}")

        except Exception as e:
            logging.error(f"Error handling file modification for {event.src_path}: {e}")

    def start_monitoring(self):
        if not self.running:
            self.FILE_PATHS = self.load_config()
            if not self.observer:
                self.observer = Observer()
            try:
                for file_path in self.FILE_PATHS.keys():
                    self.observer.schedule(self.event_handler, path=str(file_path.parent), recursive=False)
                self.observer.start()
                self.running = True
                logging.info("Observer started.")
            except Exception as e:
                logging.error(f"Error during monitoring: {e}")

    def stop_monitoring(self):
        if self.running:
            if self.observer:
                self.observer.stop()
                self.observer.join()  # Ensure all threads are finished
                self.observer = None
            self.running = False
            logging.info("Observer stopped.")

    def is_running(self):
        return self.running

    def reload_configuration(self):
        # 1. Stop the current observer.
        self.stop_monitoring()

        # 2. Load the new configuration.
        self.FILE_PATHS = self.load_config()

        # 3. Restart the observer with the updated configuration.
        self.start_monitoring()


class FileModifiedHandler(FileSystemEventHandler):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def on_modified(self, event):
        self.manager.handle_file_modification(event)

if __name__ == '__main__':
    manager = FileRevisionManager()
    manager.start_monitoring()

    try:
        # No infinite loop here, the program will run until interrupted with KeyboardInterrupt
        pass

    except KeyboardInterrupt:
        manager.stop_monitoring()
        logging.info("Observer stopped due to KeyboardInterrupt.")
