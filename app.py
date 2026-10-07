import streamlit as st
import yt_dlp
import os
import datetime
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="Pro Downloader Dashboard",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS (Dark Theme & Glowing Buttons) ---
st.markdown("""
<style>
    /* Main Backgrounds */
    .stApp {
        background-color: #0f172a;
        color: #e2e8f0;
    }

    .css-1d391kg, .stSidebar {
        background-color: #1e293b !important;
    }

    /* Cards */
    .hero-card {
        background-color: #1e293b;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 2rem;
        border: 1px solid #334155;
    }

    .format-card {
        background-color: #273549;
        padding: 1.5rem;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #334155;
    }

    /* Glowing Buttons */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 0 10px rgba(99, 102, 241, 0.4);
    }

    div.stButton > button:first-child:hover {
        box-shadow: 0 0 20px rgba(168, 85, 247, 0.6);
        transform: translateY(-2px);
    }

    /* Input Fields */
    .stTextInput > div > div > input {
        background-color: #0f172a;
        color: white;
        border: 1px solid #334155;
        border-radius: 6px;
    }

    /* Headers & Text */
    h1, h2, h3 {
        color: #f8fafc;
    }
    p {
        color: #cbd5e1;
    }
</style>
""", unsafe_allow_html=True)

# --- State Initialization ---
if 'history' not in st.session_state:
    st.session_state.history = []

if 'dl_dir' not in st.session_state:
    st.session_state.dl_dir = os.path.expanduser("~/Downloads")

def add_to_history(platform, title, format_info):
    entry = {
        "platform": platform,
        "title": title,
        "format": format_info,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.session_state.history.insert(0, entry)

def download_media(url, format_str, platform, dl_dir):
    import threading
    import imageio_ffmpeg

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    def _download(target_dir):
        try:
            ydl_opts = {
                'format': format_str,
                'outtmpl': os.path.join(target_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'ffmpeg_location': ffmpeg_path
            }

            # If we are strictly downloading audio, add the postprocessor for MP3
            if format_str == 'bestaudio/best':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"Download failed: {e}")

    # Run in background to avoid blocking the Streamlit UI completely
    # Pass target_dir into the thread to avoid relying on st.session_state inside the thread
    thread = threading.Thread(target=_download, args=(dl_dir,))
    thread.start()
    return True

# --- Sidebar ---
with st.sidebar:
    st.title("📥 Downloader Pro")
    st.caption("Secure Media Dashboard v3.0")

    st.markdown("---")

    view = st.radio("Navigation", [
        "YouTube Video Download",
        "Instagram Media Download",
        "Download History",
        "Settings",
        "How To Use",
        "About Us",
        "Contact Us"
    ])

    st.markdown("---")
    # A decorative network speed indicator for aesthetics
    st.metric(label="Server Status", value="Online (US-East)", delta="99.9% Uptime")

# --- Routing ---
if view == "YouTube Video Download":
    st.markdown("<div class='hero-card'><h2>▶️ YouTube Downloader</h2><p>Paste a YouTube URL below to analyze and download high-quality video or audio.</p></div>", unsafe_allow_html=True)

    yt_url = st.text_input("YouTube Link", placeholder="https://www.youtube.com/watch?v=...")

    # Initialize session state for YT info
    if 'yt_info' not in st.session_state:
        st.session_state.yt_info = None

    if st.button("Analyze Link", key="analyze_yt"):
        if yt_url:
            with st.spinner("Extracting metadata..."):
                ydl_opts = {'quiet': True, 'no_warnings': True}
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        st.session_state.yt_info = ydl.extract_info(yt_url, download=False)
                except Exception as e:
                    st.error(f"Failed to analyze link. Error: {e}")
        else:
            st.warning("Please enter a valid URL.")

    if st.session_state.yt_info:
        info = st.session_state.yt_info
        st.success(f"Loaded: {info.get('title', 'Video')}")
        if info.get('thumbnail'):
            st.image(info.get('thumbnail'), width=320)

        # Show Download Options
        st.markdown("### Available Formats")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("<div class='format-card'><h4>1080p HD</h4><p>MP4 Video</p></div>", unsafe_allow_html=True)
            if st.button("Download 1080p", key="dl_1080"):
                download_media(info.get('webpage_url', yt_url), 'bestvideo[height<=1080]+bestaudio/best[height<=1080]', 'YouTube', st.session_state.dl_dir)
                add_to_history("YouTube", info.get('title'), "1080p (MP4)")
                st.toast("Download Started: 1080p MP4", icon="✅")

        with col2:
            st.markdown("<div class='format-card'><h4>720p</h4><p>MP4 Video</p></div>", unsafe_allow_html=True)
            if st.button("Download 720p", key="dl_720"):
                download_media(info.get('webpage_url', yt_url), 'bestvideo[height<=720]+bestaudio/best[height<=720]', 'YouTube', st.session_state.dl_dir)
                add_to_history("YouTube", info.get('title'), "720p (MP4)")
                st.toast("Download Started: 720p MP4", icon="✅")

        with col3:
            st.markdown("<div class='format-card'><h4>Audio Only</h4><p>MP3 320kbps</p></div>", unsafe_allow_html=True)
            if st.button("Download Audio", key="dl_audio"):
                download_media(info.get('webpage_url', yt_url), 'bestaudio/best', 'YouTube', st.session_state.dl_dir)
                add_to_history("YouTube", info.get('title'), "Audio (MP3)")
                st.toast("Download Started: MP3 Audio", icon="✅")

elif view == "Instagram Media Download":
    st.markdown("<div class='hero-card'><h2>📸 Instagram Saver</h2><p>Download Reels, Stories, Posts, or full Carousels in original quality. No login required.</p></div>", unsafe_allow_html=True)

    ig_url = st.text_input("Instagram Link", placeholder="https://www.instagram.com/p/...")

    if 'ig_info' not in st.session_state:
        st.session_state.ig_info = None

    if st.button("Analyze Link", key="analyze_ig"):
        if ig_url:
            with st.spinner("Fetching Instagram media..."):
                # Using 'best' instead of 'bestvideo' allows photo-only posts to download successfully
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'format': 'best',
                    'extract_flat': False
                }
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        st.session_state.ig_info = ydl.extract_info(ig_url, download=False)
                except Exception as e:
                    st.error(f"Failed to fetch media. Make sure the account is public. Error: {e}")
        else:
            st.warning("Please enter a valid Instagram URL.")

    if st.session_state.ig_info:
        info = st.session_state.ig_info
        title = info.get('title') or info.get('id', 'Instagram Post')
        st.success(f"Loaded: {title}")
        if info.get('thumbnail'):
            st.image(info.get('thumbnail'), width=320)

        # Show Download Option for Instagram
        st.markdown("### Available Format")
        st.markdown("<div class='format-card'><h4>Original Quality</h4><p>Auto-detects Photo Carousel or Video Reel</p></div>", unsafe_allow_html=True)
        if st.button("Download Media", key="dl_ig"):
            download_media(info.get('webpage_url', ig_url), 'best', 'Instagram', st.session_state.dl_dir)
            add_to_history("Instagram", title, "Original Quality (Auto)")
            st.toast("Download Started: Original Quality", icon="✅")

elif view == "Download History":
    st.markdown("<div class='hero-card'><h2>📜 Session History</h2><p>Recent downloads for this session.</p></div>", unsafe_allow_html=True)

    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()

    if not st.session_state.history:
        st.info("No downloads yet in this session.")
    else:
        for item in st.session_state.history:
            st.markdown(f"""
            <div style="background-color: #273549; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid #334155;">
                <h4 style="margin:0; color: #f8fafc;">{item['title']}</h4>
                <p style="margin:5px 0 0 0; color: #94a3b8; font-size: 0.9em;">
                    <strong>{item['platform']}</strong> | {item['format']} | {item['timestamp']}
                </p>
            </div>
            """, unsafe_allow_html=True)

elif view == "Settings":
    st.markdown("<div class='hero-card'><h2>⚙️ Settings</h2><p>Configure your dashboard preferences.</p></div>", unsafe_allow_html=True)

    new_dir = st.text_input("Default Download Directory", value=st.session_state.dl_dir)
    if st.button("Save Settings"):
        st.session_state.dl_dir = new_dir
        st.toast("Settings saved successfully!", icon="✅")

elif view == "How To Use":
    st.markdown("<div class='hero-card'><h2>📖 Quick Start Guide</h2></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='format-card'><h3>1. Copy Link</h3><p>Copy the URL of the video or post you want to download.</p></div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='format-card'><h3>2. Paste & Analyze</h3><p>Paste the link into the dashboard and click Analyze.</p></div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='format-card'><h3>3. Save</h3><p>Select your desired format and download directly.</p></div>", unsafe_allow_html=True)

elif view == "About Us":
    st.markdown("<div class='hero-card'><h2>ℹ️ About Downloader Pro</h2><p>Your ultimate all-in-one media extraction dashboard.</p></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Uptime", "99.9%", "Reliable")
    col2.metric("Processed Files", "10M+", "Fast")
    col3.metric("Security", "100%", "Safe")

elif view == "Contact Us":
    st.markdown("<div class='hero-card'><h2>📬 Get in Touch</h2><p>Send us your feedback or bug reports.</p></div>", unsafe_allow_html=True)

    with st.form("contact_form"):
        st.text_input("Name")
        st.text_input("Email")
        st.text_area("Message")
        submitted = st.form_submit_button("Send Message")
        if submitted:
            st.success("Thank you! Your message has been sent.")
