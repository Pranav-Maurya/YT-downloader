# YouTube Downloader

A modern desktop application to easily download YouTube videos and audio. It features a clean UI built with CustomTkinter, automatically stays up-to-date, and handles FFmpeg dependencies so you don't have to.

## Features

- **Modern GUI:** Built with `customtkinter` for a dark/light mode friendly interface.
- **Auto-fetching:** Just paste a YouTube link and it automatically fetches available qualities.
- **Audio & Video Support:** Choose between downloading just the audio or the full video.
- **Auto-updating:** Checks and updates `yt-dlp` automatically on startup so it doesn't break when YouTube changes.
- **Built-in FFmpeg:** Automatically provisions FFmpeg via `imageio-ffmpeg`—no manual installation or PATH configuration required!
- **Remember Download Location:** Asks where to save on your first download and remembers it for next time.

## Requirements

- Python 3.8+

## Setup & Running

1. Clone or download this repository.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## Usage

1. **Launch the App:** Wait a moment for it to check for updates.
2. **Paste a Link:** Paste your YouTube URL into the input field. The app will automatically fetch available options.
3. **Select Format & Quality:** Choose Video or Audio, and select your desired quality.
4. **Download:** Click Download. If it's your first time, you'll be asked where to save it. You can see the progress in the progress bar.
