# CBETAfetch

**CBETAfetch** is a powerful tool for downloading and processing Sutra texts from the [CBETA API](https://cbdata.dila.edu.tw/). It provides a modern web interface to easily manage downloads, support multiple formats (TXT, HTML, PDF, EPUB, MOBI), and process texts into clean, readable Markdown files.

## Features

-   **Multi-Language Support**:
    -   English and Traditional Chinese (繁體中文) interface
    -   Automatic browser language detection
    -   Easy language switching with persistent preferences
-   **Web Interface**: A user-friendly Flask-based web UI with four main tabs.
-   **Flexible Downloads**:
    -   Input IDs directly (e.g., `T2017`) or use ranges (e.g., `T1500-T1510`).
    -   Support for multiple formats: TXT, HTML, PDF, EPUB, MOBI.
    -   Customizable base URLs for each format.
-   **Automated Processing**:
    -   Extracts downloaded ZIP files.
    -   Combines segmented text files into a single volume.
    -   Cleans up comments and headers.
-   **Complete Text Pack Processing**:
    -   Download the entire CBETA text collection in one operation
    -   Automatically unzips, processes thousands of folders, and combines text files
    -   Optional automatic conversion to Markdown
    -   Progress tracking for large-scale processing
-   **Markdown Conversion**:
    -   Converts processed text files to Markdown (`.md`).
    -   Automatically sanitizes content (e.g., replacing `#` with `//` to avoid header conflicts).
-   **Cross-Platform Compatibility**:
    -   Works on macOS, Linux, and Windows
    -   Automatic browser opening on application start
    -   UTF-8 encoding support for all platforms

## Prerequisites

-   **Python 3.6+**

## Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/chicman/CBETAfetch.git
    cd CBETAfetch
    ```

2.  **Install Dependencies**:
    
    The project requires Python 3.6+ and Flask.
    
    ```bash
    pip install flask
    ```

## Usage

### Web Interface

1.  **Start the Application**:
    ```bash
    python app.py
    ```
    The application will start and automatically open your default browser to `http://127.0.0.1:10066`.

2.  **Language Selection**:
    -   Choose your preferred language (English or 繁體中文) from the language selector in the top-right corner.
    -   The application automatically detects your browser's language on first visit.
    -   Your language preference is saved locally for future sessions.

3.  **Configure Settings**:
    -   Go to the **Settings** tab.
    -   Set your **Download Destination** (absolute path like `./downloads/` or a full path).
    -   (Optional) Configure custom URLs for specific formats if the defaults don't work.

4.  **Download Individual Texts**:
    -   Go to the **Download** tab.
    -   Enter Sutra IDs in the **ID List** box (one per line).
        -   Single ID: `T2017`
        -   Range: `T1500-T1505`
    -   Select desired formats (TXT, HTML, PDF, EPUB, MOBI).
    -   Click **Start Download**.

5.  **Process Downloaded Texts**:
    -   Go to the **Process** tab.
    -   Ensure the **Project Directory** matches your download folder.
    -   Click **Combine txt files** to extract and combine text files.
    -   Processed files will be saved in a `complete` folder (sibling to your download folder).
    -   Click **Convert to MD** to convert the processed `.txt` files to Markdown format.

6.  **Complete Text Pack Processing** (NEW):
    -   Go to the **Full Download** tab.
    -   The **Complete Text Pack URL** is pre-configured with the CBETA complete text collection.
    -   Check **Convert to MD** if you want automatic Markdown conversion (recommended).
    -   Click **Complete Text Pack Process** to:
        -   Download the entire CBETA text collection (~hundreds of MB)
        -   Automatically unzip and process thousands of text folders
        -   Combine all text files into organized volumes
        -   Optionally convert to Markdown format
        -   Output all processed files to the `./complete/` directory
    -   **Note**: This process handles large amounts of data and may take significant time depending on your system.

### Command Line Processing

Run `python process.py --help` to see command-line options for processing downloaded files.

## License

[MIT](LICENSE)
