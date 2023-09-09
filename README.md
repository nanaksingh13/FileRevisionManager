# File Revision Management System

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Watchdog Version](https://img.shields.io/badge/watchdog-2.1%2B-green)

A Python script for monitoring and managing file revisions based on file modifications. This script uses the Watchdog library to track changes in specified files and directories, creating new revisions with timestamps when changes occur.

## Features

- Continuous monitoring of specified files and directories.
- Automatic creation of new file revisions upon modification.
- Configuration management through a CSV file.
- Duplicate file prevention based on MD5 checksum.
- Flexible and customizable for different file revision needs.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Watchdog library (version 2.1 or higher)

### Installation

1. Clone this repository to your local machine:

   ```shell
   git clone https://github.com/nanaksingh13/FileRevisionManager.git
   ```

2. Install the required dependencies:

   ```shell
   pip install watchdog
   pip install hashlib
   pip install tkinter
   pip install pathlib
   ```

### Usage

1. Run the script:

   ```shell
   python file_revision.py
   ```

2. The script will continuously monitor the specified files and directories for changes and create revisions as needed.

### Upcoming Feature


## Author

- Nanak Singh
- GitHub: [nanaksingh13](https://github.com/nanaksingh13)
