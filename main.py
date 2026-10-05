import customtkinter as ctk
import yt_dlp
import imageio_ffmpeg
import threading
import subprocess
import sys
import json
import os
import re
from tkinter import filedialog, messagebox

# --- Settings ---
CONFIG_FILE = "config.json"
APP_TITLE = "YouTube Downloader"
APP_GEOMETRY = "600x450"

# --- Main App Class ---
class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(APP_GEOMETRY)
        self.resizable(False, False)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # State variables
        self.ffmpeg_path = ""
        self.current_info_dict = None
        self.available_formats = []

        self.build_ui()

        # Start startup tasks in background
        threading.Thread(target=self.startup_tasks, daemon=True).start()

    def build_ui(self):
        # Title
        self.title_label = ctk.CTkLabel(self, text="YouTube Downloader", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # URL Input
        self.url_var = ctk.StringVar()
        self.url_var.trace_add("write", self.on_url_change)
        self.url_entry = ctk.CTkEntry(self, placeholder_text="Paste YouTube URL here...", textvariable=self.url_var, width=450)
        self.url_entry.grid(row=1, column=0, padx=20, pady=10)

        # Status Label
        self.status_label = ctk.CTkLabel(self, text="Initializing...", text_color="gray")
        self.status_label.grid(row=2, column=0, padx=20, pady=5)

        # Format Selection
        self.format_var = ctk.StringVar(value="Video")
        self.format_menu = ctk.CTkOptionMenu(self, values=["Video", "Audio"], variable=self.format_var, command=self.on_format_change, width=150)
        self.format_menu.grid(row=3, column=0, padx=20, pady=10)

        # Quality Selection
        self.quality_var = ctk.StringVar(value="Select Quality")
        self.quality_menu = ctk.CTkOptionMenu(self, values=["Select Quality"], variable=self.quality_var, width=250)
        self.quality_menu.grid(row=4, column=0, padx=20, pady=10)
        self.quality_menu.configure(state="disabled")

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, width=450)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=5, column=0, padx=20, pady=(20, 5))

        # Progress Text
        self.progress_label = ctk.CTkLabel(self, text="0%")
        self.progress_label.grid(row=6, column=0, padx=20, pady=0)

        # Download Button
        self.download_btn = ctk.CTkButton(self, text="Download", command=self.start_download, width=200, state="disabled")
        self.download_btn.grid(row=7, column=0, padx=20, pady=20)

    def startup_tasks(self):
        """Runs auto-updates and provisions ffmpeg."""
        # 1. Update yt-dlp
        self.update_status("Checking for yt-dlp updates...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
        except Exception as e:
            print(f"Failed to update yt-dlp: {e}")

        # 2. Get ffmpeg path
        self.update_status("Provisioning FFmpeg...")
        try:
            self.ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            print(f"FFmpeg found at: {self.ffmpeg_path}")
        except Exception as e:
            print(f"Failed to get ffmpeg path: {e}")
            self.update_status("Error loading FFmpeg.", error=True)
            return

        self.update_status("Ready.", error=False, success=True)
        self.after(0, lambda: self.url_entry.configure(state="normal"))

    def update_status(self, message, error=False, success=False):
        color = "red" if error else ("green" if success else "gray")
        self.after(0, lambda: self.status_label.configure(text=message, text_color=color))

    # --- URL Tracing & Metadata Fetching ---
    def on_url_change(self, *args):
        url = self.url_var.get().strip()
        # Basic validation for youtube URL
        if "youtube.com" in url or "youtu.be" in url:
            self.update_status("Fetching available qualities...")
            self.quality_menu.configure(state="disabled")
            self.download_btn.configure(state="disabled")

            # Start fetch in background so UI doesn't freeze
            threading.Thread(target=self.fetch_metadata, args=(url,), daemon=True).start()
        else:
            self.update_status("Waiting for valid YouTube URL...", error=False)
            self.quality_menu.configure(state="disabled")
            self.download_btn.configure(state="disabled")

    def fetch_metadata(self, url):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                self.current_info_dict = info
                self.parse_and_populate_formats()
                self.update_status("Metadata fetched! Select format and quality.", success=True)
        except Exception as e:
            print(f"Error fetching metadata: {e}")
            self.update_status("Error fetching URL.", error=True)

    def parse_and_populate_formats(self):
        if not self.current_info_dict:
            return

        formats = self.current_info_dict.get('formats', [])

        self.video_qualities = set()
        self.audio_qualities = set()

        for f in formats:
            # Video formats (has video, usually best handled by combining later if has audio, but we just want the options)
            if f.get('vcodec') != 'none' and f.get('resolution') and f.get('resolution') != 'audio only':
                res = f.get('resolution')
                if 'x' in res:
                    res = res.split('x')[1] + 'p'
                self.video_qualities.add(res)

            # Audio formats
            if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                abr = f.get('abr')
                if abr:
                    self.audio_qualities.add(f"{int(abr)}kbps")

        # Sort and update UI
        self.video_qualities = sorted(list(self.video_qualities), key=lambda x: int(re.sub(r'[^0-9]', '', x)) if re.sub(r'[^0-9]', '', x).isdigit() else 0, reverse=True)
        self.audio_qualities = sorted(list(self.audio_qualities), key=lambda x: int(re.sub(r'[^0-9]', '', x)) if re.sub(r'[^0-9]', '', x).isdigit() else 0, reverse=True)

        self.after(0, self.update_quality_dropdown)

    def update_quality_dropdown(self):
        fmt = self.format_var.get()
        if fmt == "Video":
            options = self.video_qualities if self.video_qualities else ["best"]
        else:
            options = self.audio_qualities if self.audio_qualities else ["bestaudio"]

        if not options:
            options = ["Default Best"]

        self.quality_menu.configure(values=options, state="normal")
        self.quality_var.set(options[0])
        self.download_btn.configure(state="normal")

    def on_format_change(self, *args):
        if self.current_info_dict:
            self.update_quality_dropdown()

    def get_download_location(self):
        download_dir = ""
        # Check config
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    download_dir = config.get("download_dir", "")
            except Exception as e:
                print(f"Error reading config: {e}")

        if not download_dir or not os.path.isdir(download_dir):
            download_dir = filedialog.askdirectory(title="Select default download folder")
            if download_dir:
                try:
                    with open(CONFIG_FILE, "w") as f:
                        json.dump({"download_dir": download_dir}, f)
                except Exception as e:
                    print(f"Error writing config: {e}")

        return download_dir

    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            return

        download_dir = self.get_download_location()
        if not download_dir:
            self.update_status("Download cancelled. No directory selected.")
            return

        self.download_btn.configure(state="disabled")
        self.url_entry.configure(state="disabled")
        self.format_menu.configure(state="disabled")
        self.quality_menu.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")

        fmt = self.format_var.get()
        q = self.quality_var.get()

        threading.Thread(target=self.download_thread, args=(url, download_dir, fmt, q), daemon=True).start()

    def download_thread(self, url, download_dir, fmt, quality):
        ydl_opts = {
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self.yt_dlp_progress_hook],
            'ffmpeg_location': self.ffmpeg_path if self.ffmpeg_path else None
        }

        if fmt == "Video":
            if quality == "best" or quality == "Default Best":
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                # E.g. quality is "1080p", extract 1080
                height = re.sub(r'[^0-9]', '', quality)
                if height.isdigit():
                    ydl_opts['format'] = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                else:
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
        else:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            if quality != "bestaudio" and quality != "Default Best":
                bitrate = re.sub(r'[^0-9]', '', quality)
                if bitrate.isdigit():
                    ydl_opts['postprocessors'][0]['preferredquality'] = bitrate

        self.update_status("Downloading...")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.update_status("Download Complete!", success=True)
            self.after(0, lambda: self.progress_bar.set(1.0))
            self.after(0, lambda: self.progress_label.configure(text="100%"))
        except Exception as e:
            print(f"Download Error: {e}")
            self.update_status(f"Error during download.", error=True)
        finally:
            self.after(0, self.reset_ui_after_download)

    def yt_dlp_progress_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').strip()
            # Clean ANSI escape sequences that yt-dlp sometimes outputs
            p = re.sub(r'\x1b\[[0-9;]*m', '', p)
            try:
                percent_float = float(p.replace('%', ''))
                self.after(0, lambda: self.progress_bar.set(percent_float / 100.0))
                self.after(0, lambda: self.progress_label.configure(text=f"{percent_float}%"))
            except ValueError:
                pass
        elif d['status'] == 'finished':
            self.after(0, lambda: self.progress_bar.set(1.0))
            self.after(0, lambda: self.progress_label.configure(text="100% - Processing..."))
            self.update_status("Processing file (Merging/Converting)...")

    def reset_ui_after_download(self):
        self.download_btn.configure(state="normal")
        self.url_entry.configure(state="normal")
        self.format_menu.configure(state="normal")
        self.quality_menu.configure(state="normal")

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = YouTubeDownloaderApp()
    app.mainloop()
