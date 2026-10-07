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
from PIL import Image
import requests
from io import BytesIO

# --- Settings ---
CONFIG_FILE = "config.json"
HISTORY_FILE = "history.json"
APP_TITLE = "Pro Downloader v2.4"
APP_GEOMETRY = "1000x700"

# Set Theme (Based on screenshot dark mode)
ctk.set_appearance_mode("Dark")  # Or light based on switch later
ctk.set_default_color_theme("blue")

class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(APP_GEOMETRY)
        self.minsize(800, 600)

        # State variables
        self.ffmpeg_path = ""
        self.current_tab = None
        self.download_dir = self.load_download_dir()

        self.build_ui()

        # Start startup tasks in background
        threading.Thread(target=self.startup_tasks, daemon=True).start()

    def load_download_dir(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    return config.get("download_dir", "")
            except:
                pass
        return ""

    def save_download_dir(self, path):
        self.download_dir = path
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"download_dir": path}, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def build_ui(self):
        # Configure grid layout (1 row, 2 columns)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1) # Spacer

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Downloader\nPro Dashboard v2.4", font=ctk.CTkFont(size=18, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Sidebar Buttons
        self.btn_youtube = ctk.CTkButton(self.sidebar_frame, text="YouTube Download", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=self.show_youtube_tab)
        self.btn_youtube.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.btn_instagram = ctk.CTkButton(self.sidebar_frame, text="Instagram Download", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=self.show_instagram_tab)
        self.btn_instagram.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.btn_history = ctk.CTkButton(self.sidebar_frame, text="Download History", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=self.show_history_tab)
        self.btn_history.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text="Settings", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=self.show_settings_tab)
        self.btn_settings.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        # --- Main Content Area ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Tab Frames
        self.youtube_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.instagram_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.history_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.settings_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")

        # Build initial tabs
        self.build_youtube_tab()
        self.build_instagram_tab()
        self.build_history_tab()
        self.build_settings_tab()

        # Show default tab
        self.show_youtube_tab()

    def build_youtube_tab(self):
        title = ctk.CTkLabel(self.youtube_frame, text="YouTube Video & Playlist Downloader", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=20, padx=20, anchor="w")

        # Search Box Area
        search_frame = ctk.CTkFrame(self.youtube_frame, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=5)

        self.yt_url_var = ctk.StringVar()
        self.yt_url_entry = ctk.CTkEntry(search_frame, placeholder_text="Paste YouTube URL here...", textvariable=self.yt_url_var, height=40)
        self.yt_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.yt_fetch_btn = ctk.CTkButton(search_frame, text="Fetch Media", command=self.yt_fetch_metadata, width=120, height=40)
        self.yt_fetch_btn.pack(side="right")

        self.yt_status_label = ctk.CTkLabel(self.youtube_frame, text="", text_color="gray")
        self.yt_status_label.pack(pady=5, padx=20, anchor="w")

        # Container for dynamic content (Preview & Settings)
        self.yt_content_frame = ctk.CTkFrame(self.youtube_frame, fg_color="transparent")
        self.yt_content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # State
        self.yt_current_info = None

    def yt_fetch_metadata(self):
        url = self.yt_url_var.get().strip()
        if not url:
            return

        self.yt_fetch_btn.configure(state="disabled")
        self.yt_status_label.configure(text="Fetching metadata...", text_color="gray")

        # Clear previous content
        for widget in self.yt_content_frame.winfo_children():
            widget.destroy()

        threading.Thread(target=self._yt_fetch_thread, args=(url,), daemon=True).start()

    def _yt_fetch_thread(self, url):
        ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': 'in_playlist'}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                self.yt_current_info = info
                self.after(0, self.yt_display_preview)
        except Exception as e:
            self.after(0, lambda: self.yt_status_label.configure(text=f"Error: {e}", text_color="red"))
            self.after(0, lambda: self.yt_fetch_btn.configure(state="normal"))

    def yt_display_preview(self):
        self.yt_status_label.configure(text="Metadata loaded.", text_color="green")
        self.yt_fetch_btn.configure(state="normal")

        info = self.yt_current_info
        if not info:
            return

        is_playlist = 'entries' in info

        # Top area: Thumbnail & Title
        header_frame = ctk.CTkFrame(self.yt_content_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=10)

        # Image logic
        thumb_url = info.get('thumbnails', [{'url': ''}])[-1]['url'] if info.get('thumbnails') else None

        self.yt_thumb_label = ctk.CTkLabel(header_frame, text="Loading Image...", width=160, height=90, fg_color="gray20")
        self.yt_thumb_label.pack(side="left", padx=(0, 15))

        if thumb_url:
            threading.Thread(target=self._load_image, args=(thumb_url, self.yt_thumb_label), daemon=True).start()

        title_text = info.get('title', 'Unknown Title')
        title_label = ctk.CTkLabel(header_frame, text=title_text, font=ctk.CTkFont(size=16, weight="bold"), wraplength=400, justify="left")
        title_label.pack(side="left", fill="x", expand=True)

        if is_playlist:
            # Playlist UI
            entries = info.get('entries', [])
            count_label = ctk.CTkLabel(self.yt_content_frame, text=f"Playlist items ({len(entries)}):")
            count_label.pack(anchor="w", pady=(10, 5))

            self.yt_playlist_vars = []
            scroll_frame = ctk.CTkScrollableFrame(self.yt_content_frame, height=200)
            scroll_frame.pack(fill="both", expand=True, pady=5)

            for i, entry in enumerate(entries):
                if not entry: continue
                var = ctk.BooleanVar(value=True)
                self.yt_playlist_vars.append((entry, var))
                chk = ctk.CTkCheckBox(scroll_frame, text=entry.get('title', f"Video {i+1}"), variable=var)
                chk.pack(anchor="w", pady=2)

            download_btn = ctk.CTkButton(self.yt_content_frame, text="Download Selected", command=self.yt_start_playlist_download)
            download_btn.pack(pady=15)

        else:
            # Single Video UI
            options_frame = ctk.CTkFrame(self.yt_content_frame, fg_color="transparent")
            options_frame.pack(fill="x", pady=10)

            # Format
            ctk.CTkLabel(options_frame, text="Format:").pack(side="left", padx=(0, 5))
            self.yt_format_var = ctk.StringVar(value="Video")
            format_menu = ctk.CTkOptionMenu(options_frame, values=["Video", "Audio"], variable=self.yt_format_var, command=self.yt_on_format_change)
            format_menu.pack(side="left", padx=(0, 20))

            # Quality
            ctk.CTkLabel(options_frame, text="Quality:").pack(side="left", padx=(0, 5))
            self.yt_quality_var = ctk.StringVar(value="Default Best")
            self.yt_quality_menu = ctk.CTkOptionMenu(options_frame, values=["Default Best"], variable=self.yt_quality_var)
            self.yt_quality_menu.pack(side="left", padx=(0, 20))

            self._yt_parse_single_formats()

            self.yt_progress_bar = ctk.CTkProgressBar(self.yt_content_frame)
            self.yt_progress_bar.set(0)
            self.yt_progress_bar.pack(fill="x", pady=(20, 5))

            self.yt_progress_lbl = ctk.CTkLabel(self.yt_content_frame, text="0%")
            self.yt_progress_lbl.pack()

            download_btn = ctk.CTkButton(self.yt_content_frame, text="Download", command=self.yt_start_single_download)
            download_btn.pack(pady=15)

    def _load_image(self, url, label_widget):
        try:
            response = requests.get(url)
            img_data = response.content
            img = Image.open(BytesIO(img_data))
            # Resize
            img = img.resize((160, 90), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 90))
            self.after(0, lambda: label_widget.configure(image=ctk_img, text=""))
        except Exception as e:
            print(f"Failed to load image: {e}")

    def _yt_parse_single_formats(self):
        info = self.yt_current_info
        formats = info.get('formats', [])

        video_sizes = {}
        audio_sizes = {}

        # Find best audio size for estimating video-only formats
        best_audio_size_mb = 0
        for f in formats:
            if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                fs = f.get('filesize') or f.get('filesize_approx') or 0
                mb = fs / (1024 * 1024)
                if mb > best_audio_size_mb:
                    best_audio_size_mb = mb

        for f in formats:
            fs = f.get('filesize') or f.get('filesize_approx') or 0
            size_mb = fs / (1024 * 1024)

            # Video
            if f.get('vcodec') != 'none' and f.get('resolution') and f.get('resolution') != 'audio only':
                res = f.get('resolution')
                if res and 'x' in res:
                    res = res.split('x')[1] + 'p'

                if f.get('acodec') == 'none':
                    size_mb += best_audio_size_mb

                if res not in video_sizes or size_mb > video_sizes[res]:
                    video_sizes[res] = size_mb

            # Audio
            if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                abr = f.get('abr')
                if abr:
                    kbps_str = f"{int(abr)}kbps"
                    if kbps_str not in audio_sizes or size_mb > audio_sizes[kbps_str]:
                        audio_sizes[kbps_str] = size_mb

        def sort_key(k):
            digits = re.sub(r'[^0-9]', '', k)
            return int(digits) if digits.isdigit() else 0

        self.yt_v_quals = []
        for res in sorted(video_sizes.keys(), key=sort_key, reverse=True):
            size_str = f" (~{video_sizes[res]:.1f} MB)" if video_sizes[res] > 0 else ""
            self.yt_v_quals.append(f"{res}{size_str}")

        self.yt_a_quals = []
        for kbps in sorted(audio_sizes.keys(), key=sort_key, reverse=True):
            size_str = f" (~{audio_sizes[kbps]:.1f} MB)" if audio_sizes[kbps] > 0 else ""
            self.yt_a_quals.append(f"{kbps}{size_str}")

        if not self.yt_v_quals: self.yt_v_quals = ["best"]
        if not self.yt_a_quals: self.yt_a_quals = ["bestaudio"]

        self.yt_on_format_change()

    def yt_on_format_change(self, *args):
        fmt = self.yt_format_var.get()
        if fmt == "Video":
            self.yt_quality_menu.configure(values=self.yt_v_quals)
            self.yt_quality_var.set(self.yt_v_quals[0])
        else:
            self.yt_quality_menu.configure(values=self.yt_a_quals)
            self.yt_quality_var.set(self.yt_a_quals[0])

    def _record_history(self, title, platform, filepath):
        try:
            history = []
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r") as f:
                    history = json.load(f)

            import datetime
            entry = {
                "title": title,
                "platform": platform,
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "path": filepath
            }
            history.insert(0, entry) # Add to top

            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=4)
        except Exception as e:
            print(f"Failed to record history: {e}")

    def yt_start_single_download(self):
        if not self.download_dir:
            messagebox.showerror("Error", "Please set a download location in Settings first.")
            return

        url = self.yt_current_info.get('webpage_url') or self.yt_url_var.get()
        fmt = self.yt_format_var.get()
        q = self.yt_quality_var.get()

        self.yt_progress_bar.set(0)
        self.yt_progress_lbl.configure(text="Starting...")

        threading.Thread(target=self._yt_download_thread, args=(url, self.download_dir, fmt, q, self.yt_current_info.get('title')), daemon=True).start()

    def _yt_download_thread(self, url, dl_dir, fmt, quality, title):
        ydl_opts = {
            'outtmpl': os.path.join(dl_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self._yt_hook],
            'ffmpeg_location': self.ffmpeg_path if self.ffmpeg_path else None
        }

        if fmt == "Video":
            if quality == "best":
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                height = re.sub(r'[^0-9]', '', quality)
                if height.isdigit():
                    ydl_opts['format'] = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                else:
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
        else:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['writethumbnail'] = True
            ydl_opts['postprocessors'] = [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'EmbedThumbnail', 'already_have_thumbnail': False}
            ]
            if quality != "bestaudio":
                bitrate = re.sub(r'[^0-9]', '', quality)
                if bitrate.isdigit():
                    ydl_opts['postprocessors'][0]['preferredquality'] = bitrate

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if fmt == "Audio":
                    filename = os.path.splitext(filename)[0] + ".mp3"
                self._record_history(title, "YouTube", filename)

            self.after(0, lambda: self.yt_progress_lbl.configure(text="Complete!"))
            self.after(0, self.refresh_history_tab)
        except Exception as e:
            self.after(0, lambda: self.yt_progress_lbl.configure(text=f"Error: {e}"))

    def _yt_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').strip()
            p = re.sub(r'\x1b\[[0-9;]*m', '', p)
            try:
                pf = float(p.replace('%', ''))
                self.after(0, lambda: self.yt_progress_bar.set(pf / 100.0))
                self.after(0, lambda: self.yt_progress_lbl.configure(text=f"{pf}%"))
            except: pass
        elif d['status'] == 'finished':
            self.after(0, lambda: self.yt_progress_bar.set(1.0))
            self.after(0, lambda: self.yt_progress_lbl.configure(text="Processing..."))

    def yt_start_playlist_download(self):
        if not self.download_dir:
            messagebox.showerror("Error", "Please set a download location in Settings first.")
            return

        selected_urls = []
        for entry, var in self.yt_playlist_vars:
            if var.get():
                selected_urls.append(entry['url'])

        if not selected_urls:
            return

        # For simplicity, playlist downloads use default Best settings
        threading.Thread(target=self._yt_playlist_download_thread, args=(selected_urls,), daemon=True).start()

    def _yt_playlist_download_thread(self, urls):
        ydl_opts = {
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'ffmpeg_location': self.ffmpeg_path if self.ffmpeg_path else None,
            'ignoreerrors': True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for url in urls:
                    info = ydl.extract_info(url, download=True)
                    if info:
                        filename = ydl.prepare_filename(info)
                        self._record_history(info.get('title', 'Unknown'), "YouTube Playlist", filename)
            self.after(0, self.refresh_history_tab)
            self.after(0, lambda: messagebox.showinfo("Success", "Playlist download complete!"))
        except Exception as e:
            print(f"Playlist download error: {e}")

    def refresh_history_tab(self):
        # We will build this in the history tab step
        pass

    def build_instagram_tab(self):
        title = ctk.CTkLabel(self.instagram_frame, text="Reels, Stories & Post Saver", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=20, padx=20, anchor="w")

        desc = ctk.CTkLabel(self.instagram_frame, text="Paste any Instagram post, Reel, or Carousel link to download securely.", text_color="gray")
        desc.pack(padx=20, anchor="w")

        # Search Box Area
        search_frame = ctk.CTkFrame(self.instagram_frame, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=15)

        self.ig_url_var = ctk.StringVar()
        self.ig_url_entry = ctk.CTkEntry(search_frame, placeholder_text="https://www.instagram.com/reel/...", textvariable=self.ig_url_var, height=40)
        self.ig_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.ig_format_var = ctk.StringVar(value="Video")
        ig_format_menu = ctk.CTkOptionMenu(search_frame, values=["Video", "Audio"], variable=self.ig_format_var, width=100, height=40)
        ig_format_menu.pack(side="left", padx=(0, 10))

        self.ig_fetch_btn = ctk.CTkButton(search_frame, text="Fetch Media", command=self.ig_fetch_and_download, width=120, height=40, fg_color="#c13584", hover_color="#833ab4")
        self.ig_fetch_btn.pack(side="right")

        self.ig_status_label = ctk.CTkLabel(self.instagram_frame, text="", text_color="gray")
        self.ig_status_label.pack(pady=5, padx=20, anchor="w")

        self.ig_progress_bar = ctk.CTkProgressBar(self.instagram_frame)
        self.ig_progress_bar.set(0)
        self.ig_progress_bar.pack(fill="x", padx=20, pady=(20, 5))

        self.ig_progress_lbl = ctk.CTkLabel(self.instagram_frame, text="Ready")
        self.ig_progress_lbl.pack()

        # Info Cards Area
        cards_frame = ctk.CTkFrame(self.instagram_frame, fg_color="transparent")
        cards_frame.pack(fill="both", expand=True, padx=20, pady=20)
        cards_frame.grid_columnconfigure((0,1,2), weight=1)

        c1 = ctk.CTkFrame(cards_frame, height=100)
        c1.grid(row=0, column=0, padx=5, sticky="nsew")
        ctk.CTkLabel(c1, text="Reels & Videos", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        ctk.CTkLabel(c1, text="Save viral Instagram reels directly.", text_color="gray", wraplength=180).pack()

        c2 = ctk.CTkFrame(cards_frame, height=100)
        c2.grid(row=0, column=1, padx=5, sticky="nsew")
        ctk.CTkLabel(c2, text="High-Res Photos", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        ctk.CTkLabel(c2, text="Download carousels automatically.", text_color="gray", wraplength=180).pack()

        c3 = ctk.CTkFrame(cards_frame, height=100)
        c3.grid(row=0, column=2, padx=5, sticky="nsew")
        ctk.CTkLabel(c3, text="No Login Required", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        ctk.CTkLabel(c3, text="Safe. Public accounts only.", text_color="gray", wraplength=180).pack()

    def ig_fetch_and_download(self):
        url = self.ig_url_var.get().strip()
        if not url:
            return

        if not self.download_dir:
            messagebox.showerror("Error", "Please set a download location in Settings first.")
            return

        self.ig_fetch_btn.configure(state="disabled")
        self.ig_status_label.configure(text="Extracting and downloading (Carousel items will download automatically)...", text_color="gray")
        self.ig_progress_bar.set(0)
        self.ig_progress_lbl.configure(text="Starting...")

        fmt = self.ig_format_var.get()
        threading.Thread(target=self._ig_download_thread, args=(url, self.download_dir, fmt), daemon=True).start()

    def _ig_download_thread(self, url, dl_dir, fmt):
        ydl_opts = {
            'outtmpl': os.path.join(dl_dir, '%(uploader)s_%(id)s.%(ext)s'),
            'progress_hooks': [self._ig_hook],
            'ffmpeg_location': self.ffmpeg_path if self.ffmpeg_path else None,
            'extract_flat': False, # Force deep extraction to get all carousel items
        }

        if fmt == "Video":
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
        else:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                # Record history. If it's a playlist/carousel, info has 'entries'
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            filename = ydl.prepare_filename(entry)
                            if fmt == "Audio": filename = os.path.splitext(filename)[0] + ".mp3"
                            self._record_history(entry.get('title') or entry.get('id', 'IG Post'), "Instagram", filename)
                else:
                    filename = ydl.prepare_filename(info)
                    if fmt == "Audio": filename = os.path.splitext(filename)[0] + ".mp3"
                    self._record_history(info.get('title') or info.get('id', 'IG Post'), "Instagram", filename)

            self.after(0, lambda: self.ig_progress_lbl.configure(text="Complete!"))
            self.after(0, lambda: self.ig_status_label.configure(text="Download finished.", text_color="green"))
            self.after(0, self.refresh_history_tab)
        except Exception as e:
            self.after(0, lambda: self.ig_progress_lbl.configure(text="Error occurred."))
            self.after(0, lambda: self.ig_status_label.configure(text=f"Error: {e}", text_color="red"))
        finally:
            self.after(0, lambda: self.ig_fetch_btn.configure(state="normal"))

    def _ig_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').strip()
            p = re.sub(r'\x1b\[[0-9;]*m', '', p)
            try:
                pf = float(p.replace('%', ''))
                self.after(0, lambda: self.ig_progress_bar.set(pf / 100.0))
                self.after(0, lambda: self.ig_progress_lbl.configure(text=f"{pf}%"))
            except: pass
        elif d['status'] == 'finished':
            self.after(0, lambda: self.ig_progress_bar.set(1.0))
            self.after(0, lambda: self.ig_progress_lbl.configure(text="Processing/Moving to next item..."))

    def build_history_tab(self):
        title = ctk.CTkLabel(self.history_frame, text="Download History", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=20, padx=20, anchor="w")

        self.history_scroll_frame = ctk.CTkScrollableFrame(self.history_frame)
        self.history_scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        btn_frame = ctk.CTkFrame(self.history_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        clear_btn = ctk.CTkButton(btn_frame, text="Clear History", command=self.clear_history, fg_color="#a83232", hover_color="#752222")
        clear_btn.pack(side="right")
        refresh_btn = ctk.CTkButton(btn_frame, text="Refresh", command=self.refresh_history_tab)
        refresh_btn.pack(side="right", padx=10)

        self.refresh_history_tab()

    def refresh_history_tab(self):
        for widget in self.history_scroll_frame.winfo_children():
            widget.destroy()

        if not os.path.exists(HISTORY_FILE):
            ctk.CTkLabel(self.history_scroll_frame, text="No download history yet.", text_color="gray").pack(pady=20)
            return

        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)

            if not history:
                ctk.CTkLabel(self.history_scroll_frame, text="No download history yet.", text_color="gray").pack(pady=20)
                return

            for item in history:
                frame = ctk.CTkFrame(self.history_scroll_frame, corner_radius=5)
                frame.pack(fill="x", pady=5)

                info_text = f"[{item.get('date', '')}] {item.get('platform', '')}\n{item.get('title', 'Unknown')}"
                ctk.CTkLabel(frame, text=info_text, justify="left", anchor="w").pack(side="left", padx=10, pady=5, fill="x", expand=True)

                path = item.get('path', '')
                if path and os.path.exists(path):
                    open_btn = ctk.CTkButton(frame, text="Open Folder", width=100, command=lambda p=path: self._open_folder(p))
                    open_btn.pack(side="right", padx=10, pady=5)
                else:
                    ctk.CTkLabel(frame, text="File moved/deleted", text_color="gray").pack(side="right", padx=10)

        except Exception as e:
            ctk.CTkLabel(self.history_scroll_frame, text=f"Error loading history: {e}", text_color="red").pack(pady=20)

    def _open_folder(self, filepath):
        folder = os.path.dirname(filepath)
        if os.name == 'nt':
            os.startfile(folder)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', folder])
        else:
            subprocess.Popen(['xdg-open', folder])

    def clear_history(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear your download history?"):
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            self.refresh_history_tab()

    def build_settings_tab(self):
        title = ctk.CTkLabel(self.settings_frame, text="Settings", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=20, padx=20, anchor="w")

        path_label = ctk.CTkLabel(self.settings_frame, text="Default Download Location:")
        path_label.pack(pady=(10, 0), padx=20, anchor="w")

        self.path_var = ctk.StringVar(value=self.download_dir if self.download_dir else "Not Set")
        path_entry = ctk.CTkEntry(self.settings_frame, textvariable=self.path_var, width=400, state="disabled")
        path_entry.pack(pady=5, padx=20, anchor="w")

        btn = ctk.CTkButton(self.settings_frame, text="Browse...", command=self.change_download_dir)
        btn.pack(pady=10, padx=20, anchor="w")

    def change_download_dir(self):
        dir = filedialog.askdirectory(title="Select Download Location")
        if dir:
            self.save_download_dir(dir)
            self.path_var.set(dir)

    def select_sidebar_button(self, button):
        # Reset all buttons
        buttons = [self.btn_youtube, self.btn_instagram, self.btn_history, self.btn_settings]
        for btn in buttons:
            btn.configure(fg_color="transparent")
        # Highlight selected
        button.configure(fg_color=("gray75", "gray25"))

    def show_youtube_tab(self):
        self.hide_all_tabs()
        self.youtube_frame.grid(row=0, column=0, sticky="nsew")
        self.select_sidebar_button(self.btn_youtube)

    def show_instagram_tab(self):
        self.hide_all_tabs()
        self.instagram_frame.grid(row=0, column=0, sticky="nsew")
        self.select_sidebar_button(self.btn_instagram)

    def show_history_tab(self):
        self.hide_all_tabs()
        self.history_frame.grid(row=0, column=0, sticky="nsew")
        self.select_sidebar_button(self.btn_history)

    def show_settings_tab(self):
        self.hide_all_tabs()
        self.settings_frame.grid(row=0, column=0, sticky="nsew")
        self.select_sidebar_button(self.btn_settings)

    def hide_all_tabs(self):
        self.youtube_frame.grid_forget()
        self.instagram_frame.grid_forget()
        self.history_frame.grid_forget()
        self.settings_frame.grid_forget()

    def startup_tasks(self):
        # Auto-update yt-dlp in the background
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
            print("yt-dlp auto-updated successfully.")
        except Exception as e:
            print(f"Failed to auto-update yt-dlp: {e}")

        try:
            self.ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        except:
            pass

        # If no download dir is set, we need to prompt the user (on main thread)
        if not self.download_dir:
            self.after(500, self.prompt_initial_download_dir)

    def prompt_initial_download_dir(self):
        messagebox.showinfo("First Time Setup", "Please select a default folder for your downloads.")
        self.change_download_dir()

if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()
