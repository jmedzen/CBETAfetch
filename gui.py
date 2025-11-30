import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys
import os
from downloader import SutraDownloader
from process import process_project

class CBGetApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CBETA Sutra Downloader & Processor")
        self.root.geometry("600x500")

        # Create tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        self.download_frame = ttk.Frame(self.notebook)
        self.process_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.download_frame, text='Download')
        self.notebook.add(self.process_frame, text='Process')

        self.setup_download_tab()
        self.setup_process_tab()

        # Log area (shared or separate? Let's make one at the bottom for global status)
        self.log_area = tk.Text(root, height=10, state='disabled')
        self.log_area.pack(fill='x', padx=10, pady=5)
        
        self.downloader = None

    def log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        # Force update to show logs in real-time
        self.root.update_idletasks()

    def setup_download_tab(self):
        frame = self.download_frame
        
        # URL File Selection
        ttk.Label(frame, text="URL List File:").pack(anchor='w', padx=5, pady=2)
        url_frame = ttk.Frame(frame)
        url_frame.pack(fill='x', padx=5, pady=2)
        
        self.url_file_var = tk.StringVar()
        ttk.Entry(url_frame, textvariable=self.url_file_var).pack(side='left', fill='x', expand=True)
        ttk.Button(url_frame, text="Browse", command=self.browse_url_file).pack(side='right', padx=5)

        # Download Dir Selection
        ttk.Label(frame, text="Download Destination:").pack(anchor='w', padx=5, pady=2)
        dest_frame = ttk.Frame(frame)
        dest_frame.pack(fill='x', padx=5, pady=2)
        
        self.download_dir_var = tk.StringVar()
        ttk.Entry(dest_frame, textvariable=self.download_dir_var).pack(side='left', fill='x', expand=True)
        ttk.Button(dest_frame, text="Browse", command=self.browse_download_dir).pack(side='right', padx=5)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        self.download_btn = ttk.Button(btn_frame, text="Start Download", command=self.start_download)
        self.download_btn.pack(side='left', padx=5)
        
        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.cancel_download, state='disabled')
        self.cancel_btn.pack(side='left', padx=5)

    def setup_process_tab(self):
        frame = self.process_frame
        
        # Project Dir Selection
        ttk.Label(frame, text="Project Folder (containing zips):").pack(anchor='w', padx=5, pady=2)
        proj_frame = ttk.Frame(frame)
        proj_frame.pack(fill='x', padx=5, pady=2)
        
        self.project_dir_var = tk.StringVar()
        ttk.Entry(proj_frame, textvariable=self.project_dir_var).pack(side='left', fill='x', expand=True)
        ttk.Button(proj_frame, text="Browse", command=self.browse_project_dir).pack(side='right', padx=5)

        # Options
        self.remove_zip_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Remove Zip files after extraction", variable=self.remove_zip_var).pack(anchor='w', padx=5, pady=5)

        # Buttons
        self.process_btn = ttk.Button(frame, text="Start Processing", command=self.start_process)
        self.process_btn.pack(pady=10)

    # Callbacks
    def browse_url_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if filename:
            self.url_file_var.set(filename)

    def browse_download_dir(self):
        dirname = filedialog.askdirectory()
        if dirname:
            self.download_dir_var.set(dirname)

    def browse_project_dir(self):
        dirname = filedialog.askdirectory()
        if dirname:
            self.project_dir_var.set(dirname)

    def start_download(self):
        url_file = self.url_file_var.get()
        dest_dir = self.download_dir_var.get()
        
        if not url_file or not dest_dir:
            messagebox.showerror("Error", "Please select both URL file and Destination directory.")
            return

        self.download_btn.config(state='disabled')
        self.cancel_btn.config(state='normal')
        self.downloader = SutraDownloader(dest_dir)
        
        def run():
            self.downloader.download_from_file(
                url_file, 
                progress_callback=self.log_callback,
                completion_callback=self.download_finished
            )
        
        threading.Thread(target=run, daemon=True).start()

    def cancel_download(self):
        if self.downloader:
            self.downloader.cancel()
            self.log("Cancelling download...")

    def download_finished(self):
        self.log("Download process finished.")
        self.root.after(0, lambda: self.download_btn.config(state='normal'))
        self.root.after(0, lambda: self.cancel_btn.config(state='disabled'))

    def start_process(self):
        project_dir = self.project_dir_var.get()
        remove_zip = self.remove_zip_var.get()
        
        if not project_dir:
            messagebox.showerror("Error", "Please select a Project directory.")
            return

        self.process_btn.config(state='disabled')
        
        def run():
            try:
                process_project(project_dir, remove_zip=remove_zip, logger=self.log_callback)
            except Exception as e:
                self.log_callback(f"Error during processing: {e}")
            finally:
                self.root.after(0, lambda: self.process_btn.config(state='normal'))
        
        threading.Thread(target=run, daemon=True).start()

    def log_callback(self, msg):
        # Schedule log update in main thread
        self.root.after(0, lambda: self.log(msg))

if __name__ == "__main__":
    root = tk.Tk()
    app = CBGetApp(root)
    root.mainloop()
