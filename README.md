
# YouTube → MP3 Downloader (Streamlit Demo)

**No YouTube API key needed.** This demo uses `yt-dlp` to fetch the best audio stream and FFmpeg to extract MP3.

> ⚠️ **Legal note**: Downloading YouTube content may violate YouTube’s Terms of Service and/or copyright law depending on your use and jurisdiction. This demo is for educational purposes. Ensure you have rights/permission before downloading.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Install FFmpeg (see below), then:
streamlit run app.py
```

Then paste a YouTube URL, choose an MP3 bitrate, and click **Fetch & Convert**. The app uses `yt-dlp` post-processing with FFmpeg to output MP3.

## FFmpeg install

- **macOS** (Homebrew):
  ```bash
  brew install ffmpeg
  ```
- **Windows**:
  1. Download a static build from https://www.gyan.dev/ffmpeg/builds/ (or via `winget install Gyan.FFmpeg`).
  2. Extract, then add the `bin` folder (containing `ffmpeg.exe`) to your **PATH**.
- **Linux (Debian/Ubuntu)**:
  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```

Verify:
```bash
ffmpeg -version
```

If FFmpeg is not present, the app will still try to download but MP3 conversion will likely fail.

## Why `yt-dlp` over `pytube`?
`yt-dlp` is actively maintained and more resilient to YouTube changes. It also supports robust post-processing via FFmpeg.

## Troubleshooting
- **SSL / TLS errors on macOS**: ensure Python certificates are installed (`/Applications/Python*/Install Certificates.command`).
- **Firewall / corporate network blocks**: try a different network.
- **Unicode filenames**: the app sanitizes filenames for cross-OS safety.

## Educational Use Only
Please respect creators, platforms, and laws. This demo is intended to showcase Streamlit UI, progress hooks, and simple media post-processing without any API keys.
