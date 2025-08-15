#!/usr/bin/env python3
# app.py
# Streamlit YouTube → MP3 demo (no YouTube API key required)
#
# Uses yt-dlp to fetch the video's best audio and FFmpeg to transcode to MP3.
# Educational/demo use only. Respect YouTube's Terms of Service and local laws.

import io
import os
import re
import sys
import time
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

import streamlit as st

# We lazily import yt_dlp so the app can show a friendly error if not installed
try:
    import yt_dlp as ydl
except Exception as e:
    ydl = None

APP_TITLE = "YouTube ➜ MP3 Downloader (Demo, no API key)"

def sanitize_filename(name: str) -> str:
    # Remove characters not allowed in filenames across OSes
    return re.sub(r'[\\/*?:"<>|]+', "", name).strip()

def ensure_deps_ok() -> Optional[str]:
    """
    Quick checks for optional but recommended dependencies.
    Returns a warning string if something looks missing; otherwise None.
    """
    ffmpeg_in_path = any(
        os.access(os.path.join(p, "ffmpeg"), os.X_OK) or os.access(os.path.join(p, "ffmpeg.exe"), os.X_OK)
        for p in os.environ.get("PATH", "").split(os.pathsep)
    )
    if not ffmpeg_in_path:
        return "FFmpeg not found in PATH. We'll still try to download, but MP3 conversion may fail. See README for install steps."
    return None

def build_ydl_opts(tmpdir: Path, mp3_bitrate_k: int, progress_cb):
    # yt_dlp postprocessor uses FFmpeg to extract audio to mp3
    return {
        "outtmpl": str(tmpdir / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,  # Enable output for debugging
        "no_warnings": False,  # Show warnings for debugging
        "format": "bestaudio/best",
        "progress_hooks": [progress_cb],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(mp3_bitrate_k),
            }
        ],
        # Ensure sponsor/chapters etc. aren't altering the file unless desired
        "postprocessor_args": [
            "-vn"  # no video
        ],
        # Add more verbose logging and error handling
        "verbose": True,
        "extract_flat": False,
        "writethumbnail": False,
        "writeinfojson": False,
    }

def human_size(num: float) -> str:
    for unit in ["B","KB","MB","GB","TB"]:
        if num < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"

def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🎵", layout="centered")
    st.title(APP_TITLE)
    st.caption("For demo/educational use. Please respect platform ToS and copyright laws in your jurisdiction.")
    
    if ydl is None:
        st.error("`yt-dlp` is not installed. Install with: `pip install yt-dlp`")
        st.stop()

    dep_warn = ensure_deps_ok()
    if dep_warn:
        st.warning(dep_warn)

    url = st.text_input("Paste a YouTube URL:", placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/...")
    col1, col2 = st.columns(2)
    with col1:
        bitrate = st.select_slider("MP3 quality (kbps)", options=[64, 96, 128, 160, 192, 256, 320], value=192)
    with col2:
        normalize = st.toggle("Normalize audio (EBU R128)", value=False, help="Require FFmpeg. Keeps volume consistent between tracks.")

    go = st.button("Fetch & Convert", type="primary", disabled=not bool(url.strip()))

    if not go:
        st.stop()

    # Basic URL validation
    if not re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)/", url.strip(), flags=re.I):
        st.error("Please enter a valid YouTube URL.")
        st.stop()

    # Progress & status
    p = st.progress(0, text="Preparing...")
    status = st.empty()

    downloaded_bytes = 0
    total_bytes = None
    last_update = time.time()

    def hook(d: Dict[str, Any]):
        nonlocal downloaded_bytes, total_bytes, last_update
        if d.get("status") == "downloading":
            downloaded_bytes = d.get("downloaded_bytes") or downloaded_bytes
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or total_bytes
            # Throttle UI updates
            now = time.time()
            if now - last_update > 0.05:
                if total_bytes:
                    frac = min(1.0, downloaded_bytes / total_bytes)
                    p.progress(frac, text=f"Downloading... {human_size(downloaded_bytes)} / {human_size(total_bytes)}")
                else:
                    p.progress(0, text=f"Downloading... {human_size(downloaded_bytes)}")
                last_update = now
        elif d.get("status") == "finished":
            p.progress(1.0, text="Download complete. Converting to MP3...")

    # Download & convert in a temp dir
    with tempfile.TemporaryDirectory(prefix="ytmp3_") as tdir:
        tdir = Path(tdir)

        # Append normalization if requested
        postprocessor_args = ["-vn"]
        if normalize:
            # EBU R128 loudness normalization (targets -23 LUFS by default; adjust if desired)
            postprocessor_args += ["-af", "loudnorm"]
        opts = build_ydl_opts(tdir, bitrate, hook)
        opts["postprocessor_args"] = postprocessor_args

        try:
            with ydl.YoutubeDL(opts) as y:
                info = y.extract_info(url, download=True)
        except Exception as e:
            st.error(f"Download failed: {e}")
            st.stop()

        # Find the resulting MP3 file
        title = sanitize_filename(info.get("title") or "youtube_audio")
        # yt-dlp replaces slashes etc; we sanitize further just in case
        mp3_path = None
        
        # Debug: List all files in the temp directory
        all_files = list(tdir.glob("*"))
        print(f"Debug: Files in temp directory: {[f.name for f in all_files]}")
        
        # Look for MP3 files
        mp3_files = list(tdir.glob("*.mp3"))
        print(f"Debug: MP3 files found: {[f.name for f in mp3_files]}")
        
        if mp3_files:
            mp3_path = mp3_files[0]  # Use the first MP3 file found
        else:
            # If no MP3 files, check for other audio files that might need manual conversion
            audio_files = []
            for ext in ["*.m4a", "*.webm", "*.opus", "*.ogg", "*.wav", "*.aac"]:
                audio_files.extend(tdir.glob(ext))
            
            print(f"Debug: Other audio files found: {[f.name for f in audio_files]}")
            
            if audio_files:
                st.error(f"Audio download succeeded but MP3 conversion failed. Found: {[f.name for f in audio_files]}. This suggests an FFmpeg configuration issue.")
            else:
                st.error("No audio files found in output directory. The download may have failed.")
            st.stop()

        if mp3_path is None or not mp3_path.exists():
            st.error("Could not locate the MP3 output. FFmpeg may be missing. See README for install instructions.")
            st.stop()

        # Offer download
        b = mp3_path.read_bytes()
        p.progress(1.0, text="Ready!")
        status.success(f"✅ Converted: {title}.mp3  •  Size: {human_size(len(b))}  •  Bitrate: {bitrate} kbps")

        st.download_button(
            "Download MP3",
            data=b,
            file_name=f"{title}.mp3",
            mime="audio/mpeg",
            type="primary",
        )

        with st.expander("Video metadata"):
            st.json({
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "duration_sec": info.get("duration"),
                "webpage_url": info.get("webpage_url"),
                "upload_date": info.get("upload_date"),
                "channel": info.get("channel"),
                "id": info.get("id"),
            })

        st.info("Tip: If conversion fails, install FFmpeg and restart the app. See README for platform-specific steps.")

if __name__ == "__main__":
    main()
