import csv
import json
from pathlib import Path
from file_revision import FileRevisionManager

# Append file configurations from a CSV file to the current data.
def import_config_from_csv(filename, current_data):
    manager = FileRevisionManager()

    with open(filename, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            current_data[row['file_path']] = row['revision_dir']

    return current_data

# Append file configurations from a JSON file to the current data.
def import_config_from_json(filename, current_data):
    with open(filename, 'r') as file:
        data = json.load(file)

    current_data.update(data)  # Update the current data with the imported data
    return current_data


def export_config_to_csv(filename, file_paths):
    """Export file configurations to a CSV file."""
    with open(filename, 'w', newline='') as file:
        fieldnames = ['file_path', 'revision_dir']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for path, revision_dir in file_paths.items():
            writer.writerow({'file_path': path, 'revision_dir': revision_dir})

def export_config_to_json(filename, file_paths):
    """Export file configurations to a JSON file."""
    with open(filename, 'w') as file:
        json.dump(file_paths, file, indent=4)
