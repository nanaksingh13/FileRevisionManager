import tkinter as tk
import tkinter.ttk as ttk
import threading
import csv
import logging
import json
from tkinter import filedialog, simpledialog
from file_revision import FileRevisionManager
from pathlib import Path


LOG_FILE = "file_revision.log"
MAX_LOG_LINES = 100


class TextHandler(logging.Handler):
    """Handler class for logging messages to a tkinter text widget."""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        log_entry = self.format(record)
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, log_entry + '\n')
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)


class FileRevisionGUI(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_panel = None
        self.scrollable_frame = None
        self.title("File Revision Manager")
        self.geometry("1000x900")
        self.dark_mode = False
        self.manager = FileRevisionManager()
        self._after_id = None
        ttk.Style().configure("TButton", padding=6)
        ttk.Style().configure("TLabel", padding=6)
        ttk.Style().configure("TFrame", padding=6)

        # Initialize status_label as an instance variable
        self.status_label = ttk.Label()

        self.init_ui()
        self.thread = threading.Thread(target=self.monitor_files)
        self.thread.daemon = True
        self.thread.start()

        # Create a label to handle file drops
        self.drop_label = tk.Label(self, text="Drop files here", bd=2, relief="solid", padx=10, pady=10)
        self.drop_label.pack(fill=tk.BOTH, expand=True)
        self.drop_label.bind("<Enter>", self.on_enter)
        self.drop_label.bind("<Leave>", self.on_leave)

        # Bind the <<Drop>> event to handle file drops
        self.drop_label.bind('<<Drop>>', self.handle_drop)

        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

    def init_ui(self):
        """Initialize the user interface."""
        self.create_scrollable_frame()
        self.create_status_panel()
        self.create_file_config_panel()
        self.create_log_panel()

    def create_scrollable_frame(self):
        canvas = tk.Canvas(self)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        self.scrollable_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        canvas.bind("<Configure>", self.on_canvas_configure)

    def on_canvas_configure(self, event):
        self.scrollable_frame.update_idletasks()
        canvas_width = event.width  # Use event.width to get the canvas width
        self.scrollable_frame.config(width=canvas_width)

    def create_status_panel(self):
        panel = ttk.LabelFrame(self, text="Status", padding=(10, 5))
        panel.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)

        self.status_label = ttk.Label(panel, text="Monitoring")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)

        start_button = ttk.Button(panel, text="Start Monitoring", command=self.start_monitoring)
        start_button.pack(side=tk.LEFT, padx=10, pady=5)

        stop_button = ttk.Button(panel, text="Stop Monitoring", command=self.stop_monitoring)
        stop_button.pack(side=tk.LEFT, padx=10, pady=5)

        panel.pack_configure(padx=10, pady=5)

    def create_file_config_panel(self):
        panel = ttk.LabelFrame(self, text="File Configuration", padding=(10, 5))
        panel.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)  # Use pack geometry manager for the file config panel

        # Use ttk.Entry for the search bar
        self._setup_search_bar(panel)

        # Create a standard tkinter Frame with padding for the file table
        label_frame = ttk.Frame(panel)
        label_frame.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)  # Use pack for the label frame

        # Use standard tkinter Treeview widget for the file table
        self._setup_file_table(label_frame)

        # Use ttk.Button for the other elements
        self._setup_config_buttons(label_frame)

        self.load_file_config_data()

    def _setup_file_table(self, parent):
        self.table = ttk.Treeview(parent, columns=('File Path', 'Revision Directory'), show="headings")

        # Customize column headers
        self.table.heading('File Path', text='File Path')
        self.table.heading('Revision Directory', text='Revision Directory')

        # Customize row appearance (e.g., alternating row colors)
        self.table.tag_configure('evenrow', background='#f0f0f0')
        self.table.tag_configure('oddrow', background='#ffffff')

        # Load file configuration data and populate the Treeview
        self.load_file_config_data()
        for i, (path, revision_dir) in enumerate(self.manager.FILE_PATHS.items()):
            tags = ('evenrow', 'oddrow')[i % 2]
            self.table.insert("", tk.END, values=(str(path), revision_dir), tags=tags)

        self.table.pack(fill=tk.BOTH, expand=True)

    def _setup_search_bar(self, parent):
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, ipady=5, expand=True)
        self.search_var.trace_add("write", lambda *args: self.delayed_search())

        reset_button = ttk.Button(search_frame, text="Reset", command=self.reset_search)
        reset_button.pack(side=tk.RIGHT)

    def _setup_config_buttons(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, expand=True)

        ttk.Button(btn_frame, text="Import", command=self.import_config).pack(side=tk.LEFT, padx=1, pady=1)
        ttk.Button(btn_frame, text="Export", command=self.export_config).pack(side=tk.LEFT, padx=1, pady=1)
        ttk.Button(btn_frame, text="Add", command=self.add_file_config).pack(side=tk.LEFT, padx=1, pady=1)
        ttk.Button(btn_frame, text="Edit", command=self.edit_file_config).pack(side=tk.LEFT, padx=1, pady=1)
        ttk.Button(btn_frame, text="Delete", command=self.delete_file_config).pack(side=tk.LEFT, padx=1, pady=1)
        ttk.Button(btn_frame, text="Reload", command=self.reload_config).pack(side=tk.RIGHT, padx=1, pady=1)

    def load_file_config_data(self):
        for item in self.table.get_children():
            self.table.delete(item)

        for path, revision_dir in self.manager.FILE_PATHS.items():
            self.table.insert("", tk.END, values=(path, revision_dir))

    def monitor_files(self):
        self.manager.start_monitoring()

    def create_log_panel(self):
        self.log_panel = ttk.LabelFrame(self, text="Log Panel", padding=(10, 5))
        self.log_panel.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)  # Use pack for the log panel

        self._setup_log_text(self.log_panel)

        # Optionally, add padding for better spacing
        self.log_panel.pack_configure(padx=10, pady=(0, 10))

    def _setup_log_text(self, parent):
        # Create a frame inside the parent Labelframe
        log_frame = tk.Frame(parent)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=15, width=115)
        self.log_text.grid(row=0, column=0, sticky="ew")

        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.log_text.config(yscrollcommand=scroll.set)

        self._load_initial_log_data()
        self._configure_log_handler()

        self.log_text.config(state=tk.DISABLED)

    def _load_initial_log_data(self):
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
            for line in lines[-MAX_LOG_LINES:]:
                self.log_text.insert(tk.END, line)
            self.log_text.see(tk.END)

    def read_csv_file(self):
        config_file = 'file_config.csv'
        try:
            with open(config_file, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    self.manager.FILE_PATHS[row['file_path']] = row['revision_dir']
        except FileNotFoundError:
            logging.error("CSV file not found.")

    def _configure_log_handler(self):
        text_handler = TextHandler(self.log_text)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] - %(message)s')
        text_handler.setFormatter(formatter)
        logging.getLogger().addHandler(text_handler)

    def start_monitoring(self):
        self.manager.start_monitoring()
        self.status_label.config(text="Monitoring")

    def stop_monitoring(self):
        self.manager.stop_monitoring()
        self.status_label.config(text="Stopped")

    def add_file_config(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            revision_dir = simpledialog.askstring("Input", "Enter Revision Directory Name")
            if revision_dir:
                self.manager.FILE_PATHS[file_path] = revision_dir
                self.write_to_csv()
                self.load_file_config_data()

    def _ask_file_path(self):
        try:
            # Attempt to get the dropped file path from the clipboard
            file_path = self.clipboard_get()
            # Clear the clipboard contents
            self.clipboard_clear()
            return file_path
        except tk.TclError:
            # If clipboard_get fails, use file dialog
            return filedialog.askopenfilename()

    def on_enter(self, event):
        self.drop_label.config(bg="lightgray")

    def on_leave(self, event):
        self.drop_label.config(bg="white")

    def handle_drop(self, event):
        file_paths = event.data
        if file_paths:
            for file_path in file_paths:
                revision_dir = simpledialog.askstring("Input", "Enter Revision Directory Name")
                if revision_dir:
                    self.manager.FILE_PATHS[file_path] = revision_dir
                    self.write_to_csv()
                    self.load_file_config_data()

    def edit_file_config(self):
        selected_item = self.table.selection()
        if not selected_item:
            return

        selected_item = selected_item[0]
        file_path, revision_dir = self.table.item(selected_item, "values")
        new_revision_dir = simpledialog.askstring("Input", "Edit Revision Directory Name", initialvalue=revision_dir)

        if new_revision_dir:
            self.manager.FILE_PATHS[file_path] = new_revision_dir
            self.write_to_csv()
            self.load_file_config_data()

    def delete_file_config(self):
        selected_item = self.table.selection()
        if not selected_item:
            return

        selected_item = selected_item[0]
        file_path_str, revision_dir = self.table.item(selected_item, "values")

        # Convert the file_path_str to a WindowsPath object for comparison
        file_path = Path(file_path_str)

        if file_path in self.manager.FILE_PATHS:
            del self.manager.FILE_PATHS[file_path]
            self.write_to_csv()  # Update the CSV file
            self.load_file_config_data()
            logging.info(f"File removed:{file_path}")
        else:
            logging.info(f"Error removing:{file_path}")

    def on_entry_click(self):
        if self.search_entry.get().strip() == 'Search for files...':
            self.search_entry.delete(0, "end")

    def on_key_press(self):
        if self.search_entry.get().strip() == 'Search for files...':
            self.search_entry.delete(0, "end")

    def on_focusout(self):
        current_text = self.search_entry.get()
        if current_text == '':
            self.search_entry.insert(0, 'Search for files...')

    def reset_search(self):
        self.search_var.set("")
        self.load_file_config_data()

    def reload_config(self):
        self.manager.reload_configuration()
        self.load_file_config_data()

    def write_to_csv(self):
        config_file = 'file_config.csv'
        with open(config_file, mode='w', newline='') as file:
            fieldnames = ['file_path', 'revision_dir']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            for path, revision_dir in self.manager.FILE_PATHS.items():
                writer.writerow({'file_path': path, 'revision_dir': revision_dir})

    def search_files(self):
        search_term = self.search_var.get().lower()

        # Clear all items from the table
        for item in self.table.get_children():
            self.table.delete(item)

        # Insert items that match the search term
        for path, revision_dir in self.manager.FILE_PATHS.items():
            if search_term in str(path).lower() or search_term in revision_dir.lower():
                self.table.insert("", tk.END, values=(path, revision_dir))

    def delayed_search(self):
        """Initiate the search after a delay."""
        # If there's an existing-scheduled search, cancel it
        if self._after_id:
            self.after_cancel(self._after_id)

        # Schedule a new search in 300 milliseconds
        self._after_id = self.after(300, self.search_files)

    def import_config(self):
        filetypes = [("CSV files", "*.csv"), ("JSON files", "*.json")]
        filename = filedialog.askopenfilename(filetypes=filetypes)

        if filename.endswith('.csv'):
            self._import_from_csv(filename)
        elif filename.endswith('.json'):
            self._import_from_json(filename)

        self.write_to_csv()

    def export_config(self):
        filetypes = [("CSV files", "*.csv"), ("JSON files", "*.json")]
        filename = filedialog.asksaveasfilename(filetypes=filetypes)

        if filename.endswith('.csv'):
            self._export_to_csv(filename)
        elif filename.endswith('.json'):
            self._export_to_json(filename)

    def _import_from_csv(self, filename):
        with open(filename, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                self.manager.FILE_PATHS[row['file_path']] = row['revision_dir']
        self.load_file_config_data()

    def _export_to_csv(self, filename):
        with open(filename, 'w', newline='') as file:
            fieldnames = ['file_path', 'revision_dir']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for path, revision_dir in self.manager.FILE_PATHS.items():
                writer.writerow({'file_path': path, 'revision_dir': revision_dir})

    def _import_from_json(self, filename):
        with open(filename, 'r') as file:
            data = json.load(file)
            self.manager.FILE_PATHS = data
        self.load_file_config_data()

    def _export_to_json(self, filename):
        with open(filename, 'w') as file:
            json.dump(self.manager.FILE_PATHS, file, indent=4)


if __name__ == "__main__":
    app = FileRevisionGUI()
    app.mainloop()
