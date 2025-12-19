# CBETA Sutra Downloader & Processor

[English](#english) | [繁體中文](#繁體中文)

---

<<<<<<< HEAD
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
=======
## English
>>>>>>> d9ed738 (feat: Major UI/UX improvements and new features)

### Overview

A web-based application for downloading and processing Buddhist texts from CBETA (Chinese Buddhist Electronic Text Association). This tool provides a user-friendly interface to download texts in multiple formats and process them for easier reading.

### Features

- **Multi-format Download**: Support for TXT, HTML, PDF, EPUB, and Mobi formats
- **Batch Download**: Download multiple texts at once with ID list or range support (e.g., T1500-T1505)
- **Complete Text Pack**: Download and process the entire CBETA text collection
- **Text Processing**: Automatically combine and convert downloaded texts
- **Markdown Conversion**: Convert processed texts to Markdown format
- **Multi-language Interface**: Support for English and Traditional Chinese
- **Custom URL Settings**: Configure custom download URLs for different formats

### Installation

#### Prerequisites

- Python 3.7+
- Flask library
- Internet connection

#### Setup

<<<<<<< HEAD
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
=======
1. **Install dependencies:**
   ```bash
   pip install flask
   ```

2. **Run the application:**
   ```bash
   python3 app.py
   ```

3. **Access the web interface:**
   The application will automatically open in your default browser at `http://127.0.0.1:10066`

### Usage
>>>>>>> d9ed738 (feat: Major UI/UX improvements and new features)

#### Download Tab

1. **Enter IDs**: Input the text IDs you want to download (one per line)
   - Single ID: `T1585`
   - Range: `T1500-T1505`
   
2. **Select Formats**: Choose which formats to download (TXT, HTML, PDF, EPUB, Mobi)

3. **Click "Start Download"**: The download process will begin and progress will be shown in the log area

#### Process Tab

1. **Set Project Directory**: Specify the directory containing downloaded zip files (default: `./downloads/`)

2. **Options**:
   - **Remove Zip files after extraction**: Automatically delete zip files after processing
   
3. **Actions**:
   - **Combine txt files**: Extract and combine text files from downloaded archives
   - **Convert to MD**: Convert processed `.txt` files to `.md` format (replaces `#` with `//`)

#### Full Download Tab

Process the complete CBETA text collection:

1. **Set Complete Text Pack URL**: URL to the complete CBETA archive (default provided)
2. **Enable "Convert to MD"**: Automatically convert to Markdown after processing
3. **Click "Complete Text Pack Process"**: Start the complete download and processing workflow

#### Settings Tab

Configure custom download URLs and paths:

- **Download Destination**: Where files will be saved
- **Format URLs**: Custom base URLs for each format (TXT, HTML, PDF, EPUB, MOBI)

### File Structure

```
cbget/
├── app.py                 # Flask application
├── downloader.py          # Download logic
├── process.py             # Text processing logic
├── templates/
│   └── index.html        # Web interface
├── static/
│   └── lang/             # Language files
│       ├── en.json       # English translations
│       └── zh-TW.json    # Traditional Chinese translations
├── downloads/            # Downloaded files (created at runtime)
└── complete/             # Processed output files (created at runtime)
```

### Output

- **Raw downloads**: Saved to `./downloads/` directory
- **Processed texts**: Saved to `./complete/` directory
- **File naming**: `{ID}_《{Name}》.txt` or `.md`

### API Endpoints

- `POST /download`: Start download process
- `POST /process`: Start text processing
- `POST /convert_md`: Convert texts to Markdown
- `POST /complete_process`: Process complete text pack
- `GET /logs`: Stream real-time logs (Server-Sent Events)

### Troubleshooting

**SSL Certificate Errors**:
The application automatically handles SSL certificate verification issues common on macOS.

**Port Already in Use**:
If port 10066 is occupied, modify the port number in `app.py`:
```python
app.run(port=YOUR_PORT, debug=True, use_reloader=False)
```

### License

This project is for educational and research purposes. Please respect CBETA's terms of use when downloading and using their texts.

---

## 繁體中文

### 概述

CBETA 經文下載與處理器是一個基於網頁的應用程式，用於從 CBETA（中華電子佛典協會）下載和處理佛教文獻。此工具提供友善的使用者介面，可下載多種格式的文本並處理以便於閱讀。

### 功能特色

- **多格式下載**：支援 TXT、HTML、PDF、EPUB 和 Mobi 格式
- **批次下載**：支援 ID 清單或範圍下載（例如：T1500-T1505）
- **完整文本包**：下載並處理完整的 CBETA 文本集合
- **文本處理**：自動合併和轉換下載的文本
- **Markdown 轉換**：將處理過的文本轉換為 Markdown 格式
- **多語言介面**：支援英文和繁體中文
- **自訂 URL 設定**：為不同格式配置自訂下載 URL

### 安裝

#### 系統需求

- Python 3.7+
- Flask 函式庫
- 網際網路連線

#### 設定步驟

1. **安裝相依套件：**
   ```bash
   pip install flask
   ```

2. **執行應用程式：**
   ```bash
   python3 app.py
   ```

3. **存取網頁介面：**
   應用程式會自動在預設瀏覽器開啟 `http://127.0.0.1:10066`

### 使用說明

#### 下載分頁

1. **輸入 ID**：輸入要下載的文本 ID（每行一個）
   - 單一 ID：`T1585`
   - 範圍：`T1500-T1505`
   
2. **選擇格式**：勾選要下載的格式（TXT、HTML、PDF、EPUB、Mobi）

3. **點擊「開始下載」**：下載程序將開始，進度會顯示在日誌區域

#### 處理分頁

1. **設定專案目錄**：指定包含已下載 zip 檔案的目錄（預設：`./downloads/`）

2. **選項**：
   - **解壓後移除 Zip 檔案**：處理後自動刪除 zip 檔案
   
3. **動作**：
   - **合併 txt 檔案**：從下載的壓縮檔中解壓並合併文本檔案
   - **轉換為 MD**：將處理過的 `.txt` 檔案轉換為 `.md` 格式（將 `#` 替換為 `//`）

#### 完整下載分頁

處理完整的 CBETA 文本集合：

1. **設定完整文本包 URL**：完整 CBETA 壓縮檔的 URL（已提供預設值）
2. **啟用「轉換為 MD」**：處理後自動轉換為 Markdown
3. **點擊「完整文本包處理」**：開始完整的下載和處理工作流程

#### 設定分頁

配置自訂下載 URL 和路徑：

- **下載目的地**：檔案儲存位置
- **格式 URL**：各格式的自訂基礎 URL（TXT、HTML、PDF、EPUB、MOBI）

### 檔案結構

```
cbget/
├── app.py                 # Flask 應用程式
├── downloader.py          # 下載邏輯
├── process.py             # 文本處理邏輯
├── templates/
│   └── index.html        # 網頁介面
├── static/
│   └── lang/             # 語言檔案
│       ├── en.json       # 英文翻譯
│       └── zh-TW.json    # 繁體中文翻譯
├── downloads/            # 下載檔案（執行時建立）
└── complete/             # 處理後的輸出檔案（執行時建立）
```

### 輸出

- **原始下載**：儲存至 `./downloads/` 目錄
- **處理後的文本**：儲存至 `./complete/` 目錄
- **檔案命名**：`{ID}_《{名稱}》.txt` 或 `.md`

### API 端點

- `POST /download`：開始下載程序
- `POST /process`：開始文本處理
- `POST /convert_md`：轉換文本為 Markdown
- `POST /complete_process`：處理完整文本包
- `GET /logs`：即時日誌串流（Server-Sent Events）

### 疑難排解

**SSL 憑證錯誤**：
應用程式會自動處理 macOS 上常見的 SSL 憑證驗證問題。

**連接埠已被佔用**：
如果連接埠 10066 被佔用，請修改 `app.py` 中的連接埠號碼：
```python
app.run(port=您的連接埠, debug=True, use_reloader=False)
```

### 授權

本專案僅供教育和研究用途。下載和使用 CBETA 文本時，請遵守 CBETA 的使用條款。

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- CBETA (Chinese Buddhist Electronic Text Association) for providing the Buddhist texts
- All contributors to this project

---

**Version**: 2.0  
**Last Updated**: December 2025
