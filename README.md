# CBETAfetch 2.0 (CBETA Sutra Downloader & Processor 2.0)

> 專為漢語大乘佛典數位人文研讀打造的高效能、高可用、多格式批次下載與自動化整理工作台。

---

## 🌟 CBETAfetch 2.0 重構亮點

### 1. 🚀 流暢向導式研讀流水線 (Fluent 4-Step Pipeline)
從「典籍挑選」到「排版研讀與匯出」的端到端向導式工作流：
- **步驟一：典籍挑選 (Corpus & Presets)**：
  - 內建 6 大傳世大乘經論預設庫（唯識根本部、般若波羅蜜多部、根本阿含部、法華楞嚴部、禪宗祖師要籍、嘉興續藏稀見論著），支援一鍵載入。
  - 支援單號、連續區間（`T1500-T1505`）與 9 大下載格式矩陣（TXT、TXT+校注、HTML、DOCX、ODT、PDF、EPUB、MOBI、DocuSky）。
  - 提供「🚀 一鍵執行完整流水線」按鈕，由下載至排版閱讀全自動完成。
- **步驟二：批次下載 (Batch Download)**：多線程並行串流下載，支援 DILA 官方節點與自訂鏡像源，即時進度追蹤。
- **步驟三：卷次合併 (Extract & Intelligent Combine)**：卷次自然排序升冪（`001` 到 `010`）、TOC 目錄檔案自動置尾、跨卷版權註解清洗去重、經論題名自動提取。
- **步驟四：排版研讀工作台 (Reading & Typography Workbench)**：
  - **左欄典籍管理庫**：即時檢索已產出之 Markdown 典籍，顯示經號、檔案大小、修改時間。
  - **右欄禪風閱讀器**：精緻宋體（Noto Serif TC）排版，H2 卷品地標題導航，支援「排版視圖」與「原始 Markdown」切換，一鍵複製全文與一鍵下載 `.md` 檔案。

### 2. 📚 智慧佛典卷次整理與 Markdown 排版 (Intelligent Processing)
- **卷次與目錄排序引擎**：自動過濾 macOS 隱藏檔案 (`._*`)，經文卷次自然升冪排列，並自動識別目錄檔案（`*-toc.txt`）精確置於經文末尾。
- **跨卷註解智慧保留**：僅保留首卷註解與藏經出版資訊，次卷起之冗餘版權註解自動清洗，合併為單一乾淨典籍。
- **典籍元數據自動提取**：自動辨析首卷題名與經名，自動過濾非法檔名字元，產出如 `T1585《成唯識論》.md` 標準格式檔名。
- **H2 卷品地層級排版與防撞去重 (卷首卷尾智能防重)**：
  - **嚴格卷首 H2 轉化**：佛典中「卷」往往在「卷首」與「卷尾」各出現一次（如首見《佛說長阿含經卷第一》，尾見《佛說長阿含經卷第一》或《佛說長阿含經卷第一終/畢/竟》）。系統採用智能卷次數字歸一化識別（`1`、`2`、`上/中/下`），**僅對每卷第一次出現（卷首）套用 `## ` H2**；卷尾之重複標題一律嚴格保留為內文，絕不二次加上 `##`。
  - **卷尾標記智能過濾**：自動識別古典佛典卷尾結尾標記（`終`、`畢`、`竟`、`完`、`結`、`訖`、`分`），防範變體卷尾標題被誤認為新章節。
  - 多卷經論自動對首現卷名加上 `## ` H2 標籤；單卷經論自動免除卷名標籤以防重複。
  - 自動識別 `品第一`、`第二品`、`歡喜地第一` 等品目與十地標題並標註 H2（同樣支援品尾/地尾去重）。
  - 智能排除假陽性佛學詞彙（如 `地獄`、`大地`、`邊地`、`勝地` 等）。
  - 自動轉換 `#` 為 `//` 註解，防止 Markdown H1 標題語義衝突。

### 3. 🌐 全藏雙版本批次下載 (Dual-Edition Full Canon Engine)
全藏下載全面支援兩種版本與模式：
1. **純文字壓縮包版 (TXT ZIP Pack)**：
   - 來源網址：`https://cbdata.dila.edu.tw/stable/download/cbeta-text.zip`
   - 功能：自動串流下載、解壓數千典籍資料夾、全量卷次自然排序合併、自動替換註解並套用 H2 標題排版匯出為 Markdown。
2. **官方 TEI P5 XML 完整代碼庫 (Git Repository)**：
   - 來源倉庫：`https://github.com/cbeta-org/xml-p5`
   - 預設下載路徑：`./downloads-xml`
   - 功能：透過 Git Clone / Pull 完整取得 CBETA 官方 XML 經文原始標註，支援淺層 Clone (`--depth 1`，大幅省時與節省硬碟空間)、即時 Commit 與 Branch 狀態檢視、斷點同步與即時終端日誌。
   - **Obsidian 專用 Markdown 轉換引擎**：內建一鍵「轉換 XML 為 Obsidian 版本 MD」功能，批次解析 TEI P5 XML，自動產生符合 Obsidian 規格的 YAML Frontmatter、Callout 資訊框、偈頌引用排版、校注異文註解（`[^1]: ...`）與缺字 Unicode 映射。

### 4. 🧪 完整的全系統自我功能診斷與健康檢驗 (Self-Diagnostic System)
CBETAfetch 2.0 內建端到端自我診斷機制：
- **終端檢驗工具 (`verify.py`)**：一鍵檢驗 13 大核心項目（運行環境、目錄寫入權限、經號解析、雙字母藏號、多格式網址建構、H2 標題格式化、去重防撞、註解轉換、TOC 排序、典籍名稱提取、Job 狀態機、Git 版本控制工具、DILA API 連線）。
- **完整 Pytest 測試套件**：內建 **124 項全覆蓋自動化測試單元**（專案整體測試覆蓋率達 **91%**），全面覆蓋核心模組、進度條引擎、XML 倉庫同步、XML 轉 Obsidian 轉換器、遠端更新檢測、4 步研讀流水線、預設庫 CRUD、標題去重與 REST API 路由。
- **Web UI 線上自檢中心**：在 Web 介面一鍵觸發全系統自檢，即時觀看各子系統耗時、通過/警示狀態卡片與診斷日誌。

### 5. 🎨 現代化 Vue 3 + Tailwind CSS 數位人文 Web 架構
- **Vue 3 (Composition API) 響應式狀態機**：採用現代化主流前端架構，徹底淘汰傳統手動 DOM 拼接，具備響應式表單驗證、非同步任務排程與狀態同步。
- **Tailwind CSS 禪意美學設計**：內建 3 大主題（🌙 禪意深空 Zen Dark、☀️ 明朗素雅 Scholastic Light、🍂 貝葉古風 Gruvbox），自適應深淺色調與排版字體（Noto Serif TC + JetBrains Mono）。
- **即時串流控制台**：SSE 零延遲傳輸、即時篩選（全部/資訊/成功/錯誤）、自動滾動鎖定、一鍵複製剪貼簿、清空與任務中斷按鈕。
- **中英雙語 i18n 即時切換**：繁體中文與 English 介面隨時切換，並自動持久化使用者語言喜好至 localStorage。

---

## 🚀 快速啟動

### 1. 一鍵啟動 (推薦)

```bash
cd /Users/jm/SyncDev/A1-antigravity/CBETAfetch2
./start.sh
```

`start.sh` 將自動配置虛擬環境、執行全系統功能檢驗並啟動服務。

### 2. 手動啟動

```bash
cd /Users/jm/SyncDev/A1-antigravity/CBETAfetch2
./.venv/bin/python run.py
```

開啟瀏覽器前往：
- **Web UI 介面**: [http://127.0.0.1:10067](http://127.0.0.1:10067)
- **API Swagger 文檔**: [http://127.0.0.1:10067/docs](http://127.0.0.1:10067/docs)

*(可透過 `--port` 或環境變數 `CBETA_PORT` 自訂埠號，預設 10067 避免與舊版 10066 衝突)*

---

## 🧪 執行自我功能檢測與自動化測試

### 1. 終端快速自檢
```bash
./.venv/bin/python verify.py
```

### 2. 執行完整 Pytest 測試套件 (63 項測試)
```bash
./.venv/bin/python verify.py --pytest
```
或直接執行：
```bash
./.venv/bin/pytest tests -v
```

### 3. Web UI 線上自檢
啟動服務後，前往上方導覽列「系統自檢」分頁，點擊「執行全系統功能健康檢測」即可。

---

## 📂 專案目錄結構

```
CBETAfetch2/
├── run.py                     # CBETAfetch 2.0 啟動入口 (預設 Port: 10067)
├── start.sh                   # 一鍵環境建置、自檢並啟動指令碼
├── verify.py                  # 系統自我功能檢測驗證程式 (支援 --pytest)
├── requirements.txt           # Python 套件相依性宣告
├── core/                      # 核心商業邏輯模組
│   ├── id_parser.py           # 經號解析器 (單一編號、範圍展開、藏號提取、驗證)
│   ├── downloader.py          # 多格式下載引擎 (TXT/HTML/EPUB/MOBI/PDF/全藏包)
│   ├── processor.py           # 壓縮檔解壓、TOC 置尾排序、卷次合併與批次處理
│   ├── headings.py            # 智能 H2 標題格式化器 (卷/品/地、去重、防撞)
│   ├── converter.py           # 純文字轉 Markdown 轉換器 (註解替換 # -> //)
│   ├── job_engine.py          # 非同步工作排程引擎 (狀態生命週期、協同中斷、日誌廣播)
│   ├── xml_repo.py            # TEI P5 XML Git 倉庫克隆、同步與狀態探測
│   ├── xml_to_obsidian.py     # TEI P5 XML 轉 Obsidian Markdown 轉換引擎
│   ├── progress.py            # 標準化視覺進度條、傳輸速率與 ETA 計算
│   └── diagnostics.py         # 全系統自我診斷健康檢查引擎
├── server/                    # FastAPI 後端服務
│   ├── app.py                 # 應用程式工廠、CORS 與靜態資源掛載
│   └── routes.py              # RESTful API 與 SSE 事件流路由 (相容舊版端點)
├── templates/                 # 網頁視圖範本
│   └── index.html             # 現代化單頁 SPA 介面 (即時日誌、狀態機、自檢中心)
├── static/                    # 靜態資源
│   └── lang/                  # 多國語言資源包
│       ├── zh-TW.json         # 繁體中文
│       └── en.json            # English
├── tests/                     # 完整自動化測試單元 (124 項測試全部通過，覆蓋率 91%)
│   ├── conftest.py            # Pytest 測試環境與隔離 fixtures
│   ├── test_api.py            # REST API、相容路由與錯誤邊界測試
│   ├── test_cli.py            # run.py 啟動參數與命令列測試
│   ├── test_converter.py      # 純文字轉 Markdown 邊界測試
│   ├── test_coverage_boost.py # 深入分支與錯誤處理邊界測試
│   ├── test_diagnostics.py    # 13 項全系統自我診斷測試
│   ├── test_downloader.py     # 多格式下載、重試與中斷測試
│   ├── test_headings.py       # 智能標題排版、卷首卷尾去重防撞測試
│   ├── test_id_parser.py      # 藏號與範圍解析測試
│   ├── test_job_engine.py     # 工作生命週期與協同中斷測試
│   ├── test_preset_manager.py # 預設庫 CRUD 與磁碟持久化測試
│   ├── test_processor.py      # 解壓、TOC 置尾、損毀壓縮檔與合併測試
│   ├── test_progress.py       # 終端進度條、傳輸速率與 ETA 計算測試
│   ├── test_update_checker.py # 遠端壓縮包與 Git 最新更新檢查測試
│   ├── test_xml_repo.py       # TEI P5 XML Git 倉庫克隆、同步與中斷測試
│   └── test_xml_to_obsidian.py# XML 轉 Obsidian 規格與批次轉換測試
├── downloads/                 # 預設下載暫存目錄
└── complete/                  # 預設合併完成與 Markdown 輸出目錄
```

---

## 📡 API 端點參考

| 方法 | 路徑 | 說明 |
| :--- | :--- | :--- |
| `GET` | `/` | 存取 Web UI 介面 |
| `GET` | `/api/status` | 取得系統狀態與目前進行中之工作 |
| `GET` | `/api/config` | 取得當前目錄設定與預設路徑 |
| `GET` | `/api/jobs` | 列出歷史任務列表 |
| `GET` | `/api/jobs/{id}` | 查詢特定任務詳細進度與日誌 |
| `POST` | `/api/jobs/{id}/cancel` | 請求中斷執行中之任務 |
| `GET` | `/logs` 或 `/api/logs/stream` | Server-Sent Events (SSE) 即時日誌串流 |
| `POST` | `/api/download` (或 `/download`) | 發起經文批次下載任務 |
| `POST` | `/api/process` (或 `/process`) | 發起 Zip 解壓與卷次合併任務 |
| `POST` | `/api/convert_md` (或 `/convert_md`) | 發起 Markdown 轉換與 H2 排版任務 |
| `POST` | `/api/format_headings` (或 `/format_headings`) | 批次套用 H2 標題排版 |
| `POST` | `/api/complete_process` (或 `/complete_process`) | 發起全藏完整包下載與處理任務 |
| `GET` | `/api/system/self-test` | 執行全系統功能健康檢測並回傳診斷報告 |
