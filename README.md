# CBETAfetch

**CBETAfetch** is a powerful tool for downloading and processing Sutra texts from the [CBETA API](https://cbdata.dila.edu.tw/). It provides a modern web interface to easily manage downloads, support multiple formats (TXT, HTML, PDF, EPUB, MOBI), and process texts into clean, readable Markdown files.

## Features

-   **Web Interface**: A user-friendly Flask-based web UI.
-   **Flexible Downloads**:
    -   Input IDs directly (e.g., `T2017`) or use ranges (e.g., `T1500-T1510`).
    -   Support for multiple formats: TXT, HTML, PDF, EPUB, MOBI.
    -   Customizable base URLs for each format.
-   **Automated Processing**:
    -   Extracts downloaded ZIP files.
    -   Combines segmented text files into a single volume.
    -   Cleans up comments and headers.
-   **Markdown Conversion**:
    -   Converts processed text files to Markdown (`.md`).
    -   Automatically sanitizes content (e.g., replacing `#` with `//` to avoid header conflicts).

## Prerequisites

-   **Python 3.6+**

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/chicman/CBETAfetch.git
cd CBETAfetch
```

### 2. Set Up a Virtual Environment (Recommended)

**MacOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

### 3. Install Dependencies

The project primarily requires `Flask`.

```bash
pip install flask
```

*Note: If you plan to use the legacy desktop GUI (`gui.py`), you will need `tkinter`. This is usually included with Python on Windows and macOS. On Linux (e.g., Ubuntu), you may need to install it:*
```bash
sudo apt-get install python3-tk
```

## Usage

### Web Interface (Recommended)

1.  **Start the Application**:
    ```bash
    python app.py
    ```
    The application will start and automatically open your default browser to `http://127.0.0.1:10066`.

2.  **Configure Settings**:
    -   Go to the **Settings** tab.
    -   Set your **Download Destination** (absolute path).
    -   (Optional) Configure custom URLs for specific formats if the defaults don't work.

3.  **Download Texts**:
    -   Go to the **Download** tab.
    -   Enter Sutra IDs in the **ID List** box (one per line).
        -   Single ID: `T2017`
        -   Range: `T1500-T1505`
    -   Select desired formats (TXT, HTML, etc.).
    -   Click **Start Download**.

4.  **Process Texts**:
    -   Go to the **Process** tab.
    -   Ensure the **Project Directory** matches your download folder.
    -   Click **Start Processing** to extract and combine text files.
    -   Processed files will be saved in a `complete` folder next to your download folder.

5.  **Convert to Markdown**:
    -   In the **Process** tab, click **Convert to MD**.
    -   This will convert the processed `.txt` files in the `complete` folder to `.md` format.

### Command Line / Legacy GUI

-   **Legacy GUI**: Run `python gui.py` for a Tkinter-based desktop interface (Note: May not have all the latest features of the web UI).
-   **CLI Processing**: Run `python process.py --help` to see command-line options for processing files.

## License

[MIT](LICENSE)
