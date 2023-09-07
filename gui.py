import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import csv
import file_revision
from file_revision import FileRevisionManager
import logging


LOG_FILE = "file_revision.log"
MAX_LOG_LINES = 100

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        log_entry = self.format(record)
        self.text_widget.config(state=tk.NORMAL)  # Temporarily enable the widget
        self.text_widget.insert(tk.END, log_entry + '\n')
        self.text_widget.see(tk.END)  # Auto-scroll to the end
        self.text_widget.config(state=tk.DISABLED)  # Disable the widget

class FileRevisionTracker(tk.Tk):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("File Revision Tracker")
        self.geometry("900x700")
        self.manager = FileRevisionManager()
        self.create_file_config_panel()
        self.create_status_panel()
        self.create_log_panel()
        self.thread = threading.Thread(target=self.monitor_files)
        self.thread.daemon = True
        self.thread.start()

    def monitor_files(self):
        self.manager.start_monitoring()

    def create_status_panel(self):
        panel = ttk.LabelFrame(self, text="Status", padding=(10, 5))
        panel.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.status_label = ttk.Label(panel, text="Stopped")
        self.status_label.grid(row=0, column=0, sticky="w")

        ttk.Button(panel, text="Start Monitoring", command=self.start_monitoring).grid(row=1, column=0)
        ttk.Button(panel, text="Stop Monitoring", command=self.stop_monitoring).grid(row=1, column=1)

    def start_monitoring(self):
        self.manager.start_monitoring()
        self.status_label.config(text="Monitoring")

    def stop_monitoring(self):
        self.manager.stop_monitoring()
        self.status_label.config(text="Stopped")

    def create_log_panel(self):
        panel = ttk.LabelFrame(self, text="Log Panel", padding=(10, 5))
        panel.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.log_text = tk.Text(panel, wrap=tk.WORD, height=15, width=100)
        self.log_text.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        scroll = ttk.Scrollbar(panel, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.log_text.config(yscrollcommand=scroll.set)

        # Reading and inserting the last few log entries from the log file
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
            last_lines = lines[-MAX_LOG_LINES:]
            for line in last_lines:
                self.log_text.insert(tk.END, line)
            self.log_text.see(tk.END)  # Auto-scroll to the end

        # Setup the handler to add new logs to the Text widget (only once)
        text_handler = TextHandler(self.log_text)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] - %(message)s')
        text_handler.setFormatter(formatter)
        logging.getLogger().addHandler(text_handler)

        # Disable the text widget to make it readonly
        self.log_text.config(state=tk.DISABLED)

    def refresh_configuration(self):
        # Manually refresh the configuration
        self.manager.reload_configuration()
        messagebox.showinfo("Configuration Reloaded", "Configuration has been manually reloaded.")

    def create_file_config_panel(self):
        panel = ttk.LabelFrame(self, text="File Configuration", padding=(10, 5))
        panel.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Table Columns
        self.table = ttk.Treeview(panel, columns=('File Path', 'Revision Directory'))
        self.table.heading('File Path', text='File Path')
        self.table.heading('Revision Directory', text='Revision Directory')
        self.table.pack(fill=tk.BOTH, expand=True)

        self.load_file_config_data()

        # Buttons for Add, Edit, and Delete
        btn_frame = ttk.Frame(panel)
        btn_frame.pack(fill=tk.X, expand=True)

        ttk.Button(btn_frame, text="Add", command=self.add_file_config).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Edit", command=self.edit_file_config).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Delete", command=self.delete_file_config).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Reload Config", command=self.reload_config).pack(side=tk.RIGHT, padx=10)

    def load_file_config_data(self):
        for item in self.table.get_children():
            self.table.delete(item)

        for path, revision_dir in self.manager.FILE_PATHS.items():
            self.table.insert("", tk.END, values=(path, revision_dir))

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


if __name__ == "__main__":
    app = FileRevisionTracker()
    app.mainloop()
