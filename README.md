# 🎥 YouTube Video Downloader CLI

A simple and interactive command-line tool to download YouTube videos using [yt-dlp](https://github.com/Oluwatemmy/Youtube-Downloader).

[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/Oluwatemmy/Youtube-Downloader/graphs/commit-activity)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**⚠️ Educational Use Only**

Always comply with YouTube's Terms of Service and only download videos you have permission to download.

## 🛠️ Features

* **Select from multiple video resolutions:** 360p, 480p, 720p, 1080p, 1440p, 2160p
* **Detects and skips already-downloaded videos**
* **Displays download progress** with speed and ETA
* **Intelligent error handling** with retry logic
* **Clear and well-commented code**
* **Modular structure** for easy modification

## 📦 Requirements

* [Python 3.7+](https://www.python.org/downloads/)
* [yt-dlp](https://github.com/yt-dlp/yt-dlp#installation)
* [ffmpeg](https://ffmpeg.org/download.html) (required for merging audio and video)

## 📁 Installation

1.  **Clone the repository**

    ```bash
    git clone [https://github.com/Oluwatemmy/Youtube-Downloader.git](https://github.com/Oluwatemmy/Youtube-Downloader.git)
    cd Youtube-Downloader
    ```

2.  **Create a virtual environment (recommended)**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

## 🔧 Installing ffmpeg

This script requires `ffmpeg` to merge audio and video streams. Follow the instructions below for your operating system:

**Windows:**

1.  Download the latest stable build from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html).
2.  Extract the ZIP file to a location on your computer (e.g., `C:\ffmpeg`).
3.  Add the `bin\` folder inside the extracted directory to your system's `PATH` environment variable.
4.  Verify the installation by opening a new command prompt and running:

    ```bash
    ffmpeg -version
    ```

**macOS (with Homebrew):**

1.  If you don't have Homebrew installed, you can install it from [https://brew.sh/](https://brew.sh/).
2.  Open your terminal and run:

    ```bash
    brew install ffmpeg
    ```

**Ubuntu/Linux:**

1.  Open your terminal and run:

    ```bash
    sudo apt update
    sudo apt install ffmpeg
    ```

## 🚀 Usage

Run the script from the terminal:

```bash
python downloader.py
```

You'll be prompted to paste a YouTube video or playlist URL and select a resolution from the available options.

The downloaded file will be saved in the downloads/ folder inside the current directory.

## 🧠 How It Works
1. **User Input:** The script prompts the user for a YouTube video or playlist URL and a desired resolution.
2. **Video Information:** It uses `yt-dlp` to fetch video information, including available formats and the best resolution without downloading the actual content initially.
3. **List available Resolutions:** The script lists available resolutions and allows the user to select one.
5. **Resolution Selection:** The user selects their preferred resolution from the provided list.
6. **Duplicate Check:** The script checks if the video has already been downloaded by comparing the video ID with existing files in the `downloads/` directory.
7. **Download:** If the video hasn't been downloaded, it uses `yt-dlp` to download the video in the selected resolution and save it in the `downloads/` directory.
8. **Progress Display:** The script displays the download progress, including speed and estimated time of arrival (ETA).
9. **Error Handling:** If an error occurs during the download, the script retries the download up to 3 times before giving up.
10. **Completion Message:** Once the download is complete, the script informs the user and provides the path to the downloaded file.
11. **Exit:** The script exits after the download is complete.

## Output
Downloads are saved to:
```bash
<your-project-root>/downloads/
```
The filenames are cleaned to remove invalid characters, ensuring they are readable and compatible with most operating systems.

## ❗ Troubleshooting
### ffmpeg not found?
Make sure:
* `ffmpeg` is installed correctly to your system.
* The `bin` directory of `ffmpeg` is added to your system's `PATH` environment variable(for Windows).
* Restart your terminal or command prompt after making changes to the `PATH` variable.
* If you still encounter issues, try running `ffmpeg -version` in your terminal to verify the installation.
### yt-dlp not found?
Make sure:
* `yt-dlp` is installed correctly in your Python environment.
* You can check if `yt-dlp` is installed by running `yt-dlp --version` in your terminal.
* If you see an error, try reinstalling `yt-dlp` using `pip install -U yt-dlp`.
### Error during download?
The script includes basic error handling and will attempt retries automatically in some cases. 
Common issues include:
* `Network connectivity problems:` Check your internet connection and try again.
* `Invalid URL:` Ensure the URL you provided is correct and accessible.
* `Video unavailable:` The video may have been removed or set to private. Try a different URL.
* `Age-restricted content:` Some videos may be age-restricted. You may need to log in to your YouTube account to access them. You can do this by providing your cookies file using the `--cookies` option in `yt-dlp`.
*`Outdated yt-dlp version:` Ensure you have the latest version of `yt-dlp` installed. You can update it using:
```bash
pip install -U yt-dlp
```
If you encounter persistent errors, please check the yt-dlp documentation or issue tracker for potential solutions.

## 🤝 Contributing
Contributions are welcome! If you find a bug or have a feature request, please open an issue or submit a pull request.
Please ensure your code adheres to the existing style and includes appropriate tests.

## 📄 License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🛡️ Disclaimer
This tool is intended for educational purposes only. Downloading copyrighted material without permission is illegal and violates YouTube's Terms of Service. Please use this script responsibly and only download videos that you have the right to access and save. The developers are not responsible for any misuse of this tool.

## 👤 Author

**Oluwaseyi Ajayi** - [GitHub](https://github.com/Oluwatemmy) | [Twitter](https://twitter.com/Oluwatemmy15) | [LinkedIn](https://www.linkedin.com/in/aotem11/) | [Portfolio](https://oluwatemmy.netlify.app/)
