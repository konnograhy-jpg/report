# 標案自動化 C 專案 - 開發與變更日誌 (Development & Change Log)

此日誌檔專門記錄 **標案自動化 C 專案 (網頁版)** 的所有修改、調整與修復歷史，以便於人類與 AI 代理人（Pandora, CODEX 等）快速追溯系統現狀。

---

<details open>
<summary><h2>📅 2026 年</h2></summary>
<div style="padding-left: 20px; margin-top: 10px;">

<details open>
<summary><h3>📌 08 月</h3></summary>
<div style="padding-left: 20px; margin-top: 10px;">

| 日期 | 變更類型 | 變更內容描述 | 影響範圍 / 涉及檔案 | 執行人 / 代理人 |
| :--- | :--- | :--- | :--- | :--- |
| 2026/08/06 | 案件資料庫與 API 對接升級 | **補上「預算金額 (budget)」欄位對接**：應閣下指示對齊案件資料庫需求，於 C 專案轉發端點 `/api/submit-bid` 與 Modal 網頁產生器中新增 `budget` 欄位讀取與轉發機制。點擊【我要投標】時會自 DOM / 屬性抽取標案金額，經 `parseBudget` 解析為整數/數值並納入 HMAC-SHA256 簽章，安全轉發給毅築標案系統 (`/api/external-bid-import`)。 | 1. [test_screenshot_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/test_screenshot_c.py)<br>2. [submit-bid.js](file:///e:/01.AI/Antigravity/標案自動化C專案/api/submit-bid.js)<br>3. [test_bid_connection.html](file:///e:/01.AI/Antigravity/標案自動化C專案/boss/tenders/test_bid_connection.html) | 潘朵拉 (Pandora) |

</div>
</details>

<details open>
<summary><h3>📌 07 月</h3></summary>
<div style="padding-left: 20px; margin-top: 10px;">

| 日期 | 變更類型 | 變更內容描述 | 影響範圍 / 涉及檔案 | 執行人 / 代理人 |
| :--- | :--- | :--- | :--- | :--- |
| 2026/07/29 | 新功能與爬蟲開發 | 1. **新增標案「過去決標紀錄」Modal 按鈕**：於標案點擊 Modal 中加入亮藍色【過去決標紀錄】按鈕，自動抓取當前標案之機關名稱與標案名稱並帶入 URL 參數。<br>2. **重構 100% 真實採購網 114-115 年歷史決標爬蟲模組**：依閣下精準指導重構 [fetch_history_award.py](file:///e:/01.AI/Antigravity/標案自動化C專案/fetch_history_award.py)，限定查詢範圍為 114 年與 115 年，穿透檢視內頁精準抓取「總決標金額」與「得標廠商/履約廠商」真實資料。<br>3. **實作雙分頁與得標廠商動態 UI 報告**：於 [tender_analysis_prototype.html](file:///e:/01.AI/Antigravity/report/boss/tenders/tender_analysis_prototype.html) 實作第一區【得標廠商總覽統計（得標次數、總金額、案件清單）】與第二區【114年與115年自由動態切換 Tab 頁籤】。 | 1. [fetch_history_award.py](file:///e:/01.AI/Antigravity/標案自動化C專案/fetch_history_award.py)<br>2. [tenders_2026_7_29_20260729_0830.html](file:///e:/01.AI/Antigravity/report/boss/tenders/tenders_2026_7_29_20260729_0830.html)<br>3. [tender_analysis_prototype.html](file:///e:/01.AI/Antigravity/report/boss/tenders/tender_analysis_prototype.html) | 潘朵拉 (Pandora) |
| 2026/07/10 | 需求調整與優化 | 1. **全面開放標案超連結**：修改 HTML 表格與手機版卡片的超連結生成邏輯，由原先的「僅限學校運動類標案」放寬為「所有標案只要有超連結網址皆加入超連結」，提升檢索標案時的跳轉便利性。<br>2. **今天已上線的就不動了**：維持今日既有已上網頁不變，此修改將套用於之後生成的報告。 | 1. [test_screenshot_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/test_screenshot_c.py) | 潘朵拉 (Pandora) |
| 2026/07/09 | Bug 修復與功能優化 | 1. **修正 Google Sheets 8 欄擴充溢出崩潰**：擴充 Google Sheets 新增招標公告連結時的 API 寫入範圍（`cols=8`，並更新所有 `endColumnIndex`/`endIndex` 為 8），防止 gspread 在寫入 8 欄時因網格限制拋出 400 錯誤。<br>2. **修正下午比對無更新無法優雅退出 Bug**：由於推薦標案置頂，下午讀取 Sheet 時會因表頭解析在開頭即中斷（break）導致讀回 0 筆並誤判定為有 50+ 筆新增案件。重構解析邏輯，使其在有推薦標案時自動跳過置頂區並從主表表頭開始解析，順利在資料無異動時以 Exit Code 3 優雅退出。 | 1. [tender_scraper_api_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_scraper_api_c.py) | 潘朵拉 (Pandora) |
| 2026/07/06 | 設定調整與部署 | 1. **發布管道機制升級**：建立自定義的 GitHub Actions workflow 檔案 [deploy.yml](file:///e:/01.AI/Antigravity/report/.github/workflows/deploy.yml)，明確宣告 Pages 寫入與 ID-Token 權限，改用最新 `actions/deploy-pages@v4` API 取代舊有黑箱背景預設建置。<br>2. **解決 GitHub 官方部署異常**：排除今日 (7/6) 上午因官方部署伺服器當機導致 `tenders.html` 線上未更新的問題。推送空 Commit 並套用新 workflow 後，成功讓 GitHub Pages 發布正常，線上已恢復綠勾且可順利瀏覽今日 50 筆標案報告。 | 1. [deploy.yml](file:///e:/01.AI/Antigravity/report/.github/workflows/deploy.yml)<br>2. [tenders.html](file:///e:/01.AI/Antigravity/report/boss/tenders.html)<br>3. [tenders_2026_7_6_20260706_0830.html](file:///e:/01.AI/Antigravity/report/boss/tenders/tenders_2026_7_6_20260706_0830.html) | 潘朵拉 (Pandora) |
| 2026/07/01 | Bug 修復與優化 | 1. **修正下午異動解析標題列 Bug**：在 `tender_scraper_api_c.py` 讀取上午標案進行解析的迴圈中，以及 `test_screenshot_c.py` 讀取下午異動資料的解析迴圈中，新增對欄位標題列（如含有「機關名稱」或「項次」的列）之過濾與排除邏輯，解決在進行下午標案比對時，會將「標題列」誤判為「已刪除/撤案標案」並在 Google Sheets 與 HTML 報告中產生一筆以 `機關名稱` / `標案案號` 作為資料的無效刪除線記錄的錯誤。<br>2. **實作排程背景靜默執行**：為防止排程執行時彈出黑色 Console 視窗干擾打字或因誤觸 QuickEdit 導致任務卡死，新增 [run_hidden_c.vbs](file:///e:/01.AI/Antigravity/標案自動化C專案/run_hidden_c.vbs) 啟動包裝，並修改 [setup_tender_task_c.ps1](file:///e:/01.AI/Antigravity/標案自動化C專案/setup_tender_task_c.ps1) 重新註冊排程，使任務改由 `wscript.exe` 背景靜態隱藏執行。 | 1. [tender_scraper_api_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_scraper_api_c.py)<br>2. [test_screenshot_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/test_screenshot_c.py)<br>3. [run_hidden_c.vbs](file:///e:/01.AI/Antigravity/標案自動化C專案/run_hidden_c.vbs)<br>4. [setup_tender_task_c.ps1](file:///e:/01.AI/Antigravity/標案自動化C專案/setup_tender_task_c.ps1) | 潘朵拉 (Pandora) |

</div>
</details>

<details open>
<summary><h3>📌 06 月</h3></summary>
<div style="padding-left: 20px; margin-top: 10px;">

| 日期 | 變更類型 | 變更內容描述 | 影響範圍 / 涉及檔案 | 執行人 / 代理人 |
| :--- | :--- | :--- | :--- | :--- |
| 2026/06/29 | 系統優化 | 1. **推薦標案置頂**：修改 `tender_scraper_api_c.py` 與 `test_screenshot_c.py` 的排版與 HTML 生成邏輯，將「學校運動類推薦標案」調整至頁面最上方顯示。<br>2. **Git 目錄重構對接**：配合最新 Git 重構（`tenders.html` 與 `tenders/` 移至 `boss/`），更新常數路徑與 Telegram 通知預覽 URL。<br>3. **新增觀看計數與返回目錄**：依據交接 SOP 在報告頁中引入基於 `localStorage` 的訪問追蹤與 `⬅️ 返回標案列表`、`🌿 返回世界樹` 導覽連結。 | 1. [tender_scraper_api_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_scraper_api_c.py)<br>2. [test_screenshot_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/test_screenshot_c.py)<br>3. [tender_pipeline_master_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_pipeline_master_c.py)<br>4. [boss/tenders.html](file:///e:/01.AI/Antigravity/report/boss/tenders.html) | 潘朵拉 (Pandora) |
| 2026/06/22 | 設定調整 | 1. **排程優化**：更新 Windows 排程任務 `TenderAutomation_C`，將觸發天數由每日 (Daily) 改為每週週一至週五 (Weekly Mon-Fri)，以避免週末開機時的無效執行與 Telegram 額外推送。<br>2. **Git 重複更新清理**：從 Git 倉庫與歷史備份中徹底清除 2026/06/17 下午 13:44 的重複標案 HTML 網頁檔（其與 17:40 檔案內容重疊），並同步修改 [tenders.html](file:///e:/01.AI/Antigravity/report/tenders.html) 更新總更新數為 18 份並移除失效連結，最後 Push 至 GitHub Pages。 | 1. [setup_tender_task_c.ps1](file:///e:/01.AI/Antigravity/標案自動化C專案/setup_tender_task_c.ps1)<br>2. [tenders.html](file:///e:/01.AI/Antigravity/report/tenders.html)<br>3. [tenders_2026_6_17_下午_20260617_1344.html](file:///e:/01.AI/Antigravity/report/tenders/tenders_2026_6_17_下午_20260617_1344.html) (已刪除) | 潘朵拉 (Pandora) |
| 2026/06/17 | 功能重建 | 1. 根據閣下指示，重建單向 Telegram 通知推送功能（零背景空耗）。<br>2. 於 [tender_scraper_api_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_scraper_api_c.py) 的狀態寫入（`run_status.json`）中補全上午/下午統計欄位 (`summary`)。<br>3. 於 [tender_pipeline_master_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_pipeline_master_c.py) 實作符合閣下要求之格式化時間與內容：上午發送「標案總數、推薦標案數」；下午發送「刪除數、新增數」變更統計。 | 1. [tender_pipeline_master_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_pipeline_master_c.py)<br>2. [tender_scraper_api_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_scraper_api_c.py)<br>3. [.env](file:///e:/01.AI/Antigravity/標案自動化C專案/.env) | 潘朵拉 (Pandora) |
| 2026/07/30 | 架構升級 | 1. 正式升級 C 專案推薦篩選機制為雙重推薦架構：【🏃 操場跑道標案推薦】與【🏀 運動類標案推薦】。<br>2. 移除第一重「學校/教育機構」過濾限制，成功擴張捕捉工務局、鄉鎮市公所等非學校機關發包之高額運動場地標案。<br>3. 同步更新 `tender_scraper_api_c.py`（Google 試算表雙區塊寫入）與 `test_screenshot_c.py`（HTML 雙區塊渲染、純中文標題與轉跳彈窗保留）。 | 1. [tender_scraper_api_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_scraper_api_c.py)<br>2. [test_screenshot_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/test_screenshot_c.py)<br>3. [tender_recommendation_prototype.html](file:///e:/01.AI/Antigravity/report/boss/tenders/tender_recommendation_prototype.html) | 潘朵拉 (Pandora) |
| 2026/06/17 | 文件撰寫 | 撰寫 [incident_report.html](file:///e:/01.AI/Antigravity/標案自動化C專案/incident_report.html) 以分析從 Mac mini M4 任務之後 Telegram 斷線與 409 Conflict 衝突的根本原因與解決歷程。 | 1. [incident_report.html](file:///e:/01.AI/Antigravity/標案自動化C專案/incident_report.html) | 潘朵拉 (Pandora) |


| 2026/06/17 | 功能移除 | 1. 根據閣下指示，徹底清除 C 專案與 Telegram 的所有連線設定與通知整合。<br>2. 刪除 `Telegram` 資料夾與其設定紀錄，將 Excel 成果檔案移回根目錄。<br>3. 刪除所有相關的監聽守護進程與測試腳本 (`pandora_agent_daemon.py`, `telegram_watcher_daemon.py`, `telegram_bridge.py`, `test_telegram.py`, `run_pandora_daemon.bat`)。<br>4. 清除 `.env` 中的 Telegram Token，並修改 `tender_pipeline_master_c.py` 移除 Telegram 通知功能，恢復為純本機執行。 | 1. [tender_pipeline_master_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_pipeline_master_c.py)<br>2. [.env](file:///e:/01.AI/Antigravity/標案自動化C專案/.env)<br>3. 刪除 Telegram 資料夾與連線腳本 | 潘朵拉 (Pandora) |
| 2026/06/17 | Bug 修復 | 1. 解決 Telegram daemon 在處理個別訊息報錯時，因未更新 offset 導致的無限重試洗版問題。<br>2. 實作地端日誌功能，將活動軌跡完整記錄至 [pandora_daemon.log](file:///e:/01.AI/Antigravity/標案自動化C專案/pandora_daemon.log)。 | 1. [pandora_agent_daemon.py](file:///e:/01.AI/Antigravity/標案自動化C專案/pandora_agent_daemon.py)<br>2. [telegram_watcher_daemon.py](file:///e:/01.AI/Antigravity/標案自動化C專案/telegram_watcher_daemon.py) | 潘朵拉 (Pandora) |
| 2026/06/17 | 設定調整 | 1. 建立 `Telegram` 獨立收納資料夾，並將 `bot_offset.txt`、`telegram_inbox.json`、`pandora_daemon.log` 以及所有生成的 Excel 檔案收納至其中。<br>2. 修改 `pandora_agent_daemon.py`、`telegram_watcher_daemon.py` 與 `telegram_bridge.py` 中所有的路徑常量與輸出位置。 | 1. [pandora_agent_daemon.py](file:///e:/01.AI/Antigravity/標案自動化C專案/pandora_agent_daemon.py)<br>2. [telegram_watcher_daemon.py](file:///e:/01.AI/Antigravity/標案自動化C專案/telegram_watcher_daemon.py)<br>3. [telegram_bridge.py](file:///e:/01.AI/Antigravity/標案自動化C專案/telegram_bridge.py) | 潘朵拉 (Pandora) |
| 2026/06/17 | 功能新增 | 1. 實作 Telegram 與地端潘朵拉雙向連接（背景長輪詢，零 Token 空耗）。<br>2. 撰寫 [pandora_agent_daemon.py](file:///e:/01.AI/Antigravity/標案自動化C專案/pandora_agent_daemon.py) 負責 Bot 訊息解析、靜態指令地端就地處理，並對自訂任務使用 `gemini-3.5-flash` 進行工具調用與推理。<br>3. 針對 429 頻繁限制實作自動退避重試機制（Exponential Backoff）。<br>4. 實作 L0 安全防禦閘，自動拒絕與警報違規指令（涉及刪除、金鑰外洩與金融付款）。 | 1. [pandora_agent_daemon.py](file:///e:/01.AI/Antigravity/標案自動化C專案/pandora_agent_daemon.py)<br>2. [telegram_bridge.py](file:///e:/01.AI/Antigravity/標案自動化C專案/telegram_bridge.py) | 潘朵拉 (Pandora) |
| 2026/06/17 | 系統整合 | 1. 整合 Telegram Bot 通知推送功能，實現執行狀態自動推送。<br>2. 建立 [.env](file:///e:/01.AI/Antigravity/標案自動化C專案/.env) 儲存敏感密鑰與 Chat ID（符合 L0 安全規範）。<br>3. 修改 [tender_pipeline_master_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_pipeline_master_c.py) 以解析環境變數並在成功、跳過及報錯時推送通知。<br>4. 撰寫 [test_telegram.py](file:///e:/01.AI/Antigravity/標案自動化C專案/test_telegram.py) 用於日後連線檢驗。 | 1. [tender_pipeline_master_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_pipeline_master_c.py)<br>2. [.env](file:///e:/01.AI/Antigravity/標案自動化C專案/.env)<br>3. [test_telegram.py](file:///e:/01.AI/Antigravity/標案自動化C專案/test_telegram.py) | 潘朵拉 (Pandora) |
| 2026/06/17 | 設定調整 | 1. 爬蟲關鍵字與高亮清單追加「泳池」。<br>2. 調整學校運動推薦條件：第二組追加「泳池」，第三組追加「技術服務」（使屬性變更為：設計+監造+技術服務）。<br>3. 完成本機執行與爬取驗證（排除 Git 上傳以維持分支乾淨）。 | 1. [tender_scraper_api_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/tender_scraper_api_c.py)<br>2. [test_screenshot_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/test_screenshot_c.py) | 潘朵拉 (Pandora) |
| 2026/06/12 | Bug 修復 | 排程執行環境異常排查修復，並對齊 Git 倉庫衝突同步。 | 1. Git 同步與排程執行環境 | 潘朵拉 (Pandora) |
| 2026/06/08 | 部署移交 | 1. **完成 C 專案部署**：將專案部署至 `E:\01.AI\Antigravity\標案自動化C專案\`，對齊絕對路徑。<br>2. **完成 report 目錄部署**：解壓並部署 `report`（GitHub Pages）目錄至 `E:\01.AI\Antigravity\report\`。<br>3. **環境初始化**：成功建立 Python 3.14.5 `venv` 虛擬環境，並使用本地 wheel 庫離線安裝了所有依賴套件。<br>4. **修正 C 專案特徵分頁篩選**：修改 `test_screenshot_c.py` 的分頁選取邏輯，新增 `學校運動` 行內容檢查，解決誤選 B 專案無推薦分頁（`2026/6/8-2`）的 bug。 | 1. [test_screenshot_c.py](file:///e:/01.AI/Antigravity/標案自動化C專案/test_screenshot_c.py)<br>2. 專案部署路徑與 venv 環境 | 賽巴斯 (Sebastian) / 潘朵拉 (Pandora) |

</div>
</details>

</div>
</details>
