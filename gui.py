import tkinter as tk
import threading
import csv
import logging
import json
from tkinter import ttk, filedialog, simpledialog
from file_revision import FileRevisionManager
import customtkinter

# Set appearance mode and default color theme
customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("blue")

LOG_FILE = "file_revision.log"
MAX_LOG_LINES = 100

# Define dark mode colors
DARK_BG_COLOR = "#2E2E2E"
DARK_TEXT_COLOR = "#FFFFFF"


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
class FileRevisionTracker(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("File Revision Tracker")
        self.geometry("900x700")
        self.dark_mode = False  # Initially set to light mode
        self.manager = FileRevisionManager()
        self._after_id = None
        customtkinter.set_widget_scaling(1.0)  # Set UI scaling to 100%

        self.init_ui()
        self.thread = threading.Thread(target=self.monitor_files)
        self.thread.daemon = True
        self.thread.start()

    def init_ui(self):
        """Initialize the user interface."""
        self.create_status_panel()
        self.create_file_config_panel()
        self.create_log_panel()
        self.create_dark_mode_button()  # Add this line to create the Dark Mode button


    def create_file_config_panel(self):
        """Panel for file configuration."""
        panel = customtkinter.CTkFrame(self)
        panel.grid(row=1, column=0, padx=10, pady=10, sticky="ew")  # Adjusted row to 1

        # Use customtkinter widgets for the search bar
        self._setup_search_bar(panel)

        # Create a standard tkinter Frame with padding for the file table
        label_frame = tk.Frame(panel)
        label_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Use standard tkinter Treeview widget for the file table
        self._setup_file_table(label_frame)

        # Use customtkinter widgets for the other elements
        self._setup_config_buttons(label_frame)

        self.load_file_config_data()

    def _create_panel(self, title):
        return ttk.LabelFrame(self, text=title, padding=(10, 5))

    def _setup_search_bar(self, parent):
        search_frame = customtkinter.CTkFrame(parent)
        search_frame.pack(pady=10, fill=tk.X, expand=True)

        self.search_var = tk.StringVar()
        self.search_entry = customtkinter.CTkEntry(search_frame, textvariable=self.search_var,
                                                   placeholder_text="Search for files...")
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_var.trace_add("write", lambda *args: self.delayed_search())

        customtkinter.CTkButton(search_frame, text="Reset", command=self.reset_search).pack(side=tk.RIGHT, padx=5)

    def _create_search_entry(self, parent):
        entry = tk.Entry(parent, textvariable=self.search_var, fg='grey')
        entry.insert(0, 'Search for files...')
        entry.bind('<Key>', self.on_key_press)
        entry.bind('<FocusIn>', self.on_entry_click)
        entry.bind('<FocusOut>', self.on_focusout)
        self.search_var.trace_add("write", lambda *args: self.delayed_search())
        return entry

    def _setup_file_table(self, parent):
        self.table = ttk.Treeview(parent, columns=('File Path', 'Revision Directory'), show="headings")
        self.table.heading('File Path', text='File Path')
        self.table.heading('Revision Directory', text='Revision Directory')
        self.table.pack(fill=tk.BOTH, expand=True)

    def _setup_config_buttons(self, parent):
        btn_frame = customtkinter.CTkFrame(parent)
        btn_frame.pack(fill=tk.X, expand=True)

        # Use customtkinter buttons for improved styling
        customtkinter.CTkButton(btn_frame, text="Import", command=self.import_config).pack(side=tk.LEFT, padx=10)
        customtkinter.CTkButton(btn_frame, text="Export", command=self.export_config).pack(side=tk.LEFT, padx=10)
        customtkinter.CTkButton(btn_frame, text="Add", command=self.add_file_config).pack(side=tk.LEFT, padx=10)
        customtkinter.CTkButton(btn_frame, text="Edit", command=self.edit_file_config).pack(side=tk.LEFT, padx=10)
        customtkinter.CTkButton(btn_frame, text="Delete", command=self.delete_file_config).pack(side=tk.LEFT, padx=10)
        customtkinter.CTkButton(btn_frame, text="Reload Config", command=self.reload_config).pack(side=tk.RIGHT,
                                                                                                  padx=10)

    def load_file_config_data(self):
        for item in self.table.get_children():
            self.table.delete(item)

        for path, revision_dir in self.manager.FILE_PATHS.items():
            self.table.insert("", tk.END, values=(path, revision_dir))

    def monitor_files(self):
        self.manager.start_monitoring()

    def create_status_panel(self):
        panel = self._create_panel("Status")
        panel.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.status_label = ttk.Label(panel, text="Monitoring")
        self.status_label.grid(row=0, column=0, sticky="w")

        ttk.Button(panel, text="Start Monitoring", command=self.start_monitoring).grid(row=1, column=0)
        ttk.Button(panel, text="Stop Monitoring", command=self.stop_monitoring).grid(row=1, column=1)

    def create_log_panel(self):
        panel = self._create_panel("Log Panel")
        panel.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        self._setup_log_text(panel)

    def _setup_log_text(self, parent):
        self.log_text = tk.Text(parent, wrap=tk.WORD, height=15, width=100)
        self.log_text.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        scroll = ttk.Scrollbar(parent, command=self.log_text.yview)
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
        file_path, revision_dir = self.table.item(selected_item, "values")
        del self.manager.FILE_PATHS[file_path]
        self.write_to_csv()
        self.load_file_config_data()

    def on_entry_click(self, event):
        if self.search_entry.get().strip() == 'Search for files...':
            self.search_entry.delete(0, "end")
            self.search_entry.config(fg='black')

    def on_key_press(self, event):
        current_text = self.search_entry.get()
        if self.search_entry.get().strip() == 'Search for files...':
            self.search_entry.delete(0, "end")
            self.search_entry.config(fg='black')

    def on_focusout(self, event):
        current_text = self.search_entry.get()
        if current_text == '':
            self.search_entry.insert(0, 'Search for files...')
            self.search_entry.config(fg='grey')

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
        # If there's an existing scheduled search, cancel it
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

    def create_dark_mode_button(self):
        dark_mode_button = customtkinter.CTkButton(self, text="Dark Mode", command=self.toggle_dark_mode)
        dark_mode_button.grid(row=3, column=0, padx=10, pady=10, sticky="w")

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.update_dark_mode()

    def update_dark_mode(self):
        # Define colors based on dark or light mode
        if self.dark_mode:
            bg_color = "black"
            text_color = "white"
        else:
            bg_color = "white"
            text_color = "black"

        # Update widget colors
        self.update_widget_colors(self, bg_color, text_color)

    def update_widget_colors(self, widget, bg_color, text_color):
        widget.configure(background=bg_color)  # Use 'background' instead of 'bg_color'
        if hasattr(widget, 'configure_text_color'):
            widget.configure_text_color(text_color)


if __name__ == "__main__":
    app = FileRevisionTracker()
    app.mainloop()
