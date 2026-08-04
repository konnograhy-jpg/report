import os
import sys
import io
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# 強制 UTF-8 輸出，防止 Windows 本地 CP950 (Big5) 發生 UnicodeEncodeError
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 設定路徑與金鑰檔案尋找邏輯
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, 'credentials.json')
if not os.path.exists(CREDENTIALS_PATH):
    CREDENTIALS_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), 'MCP', 'credentials.json')
if not os.path.exists(CREDENTIALS_PATH):
    CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, 'MCP', 'credentials.json')

# ── C專案升級標籤：ENABLE_AWARD_HISTORY (True: 進階版 / False: 基礎版) ──
ENABLE_AWARD_HISTORY = os.getenv("ENABLE_AWARD_HISTORY", "True").lower() == "true"

try:
    from fetch_award_history import fetch_unit_award_history
    from analytics_engine import analyze_award_history
    from generate_report import generate_html_report
    AWARD_ENGINE_AVAILABLE = True
except Exception as e:
    print(f"[Award Engine Warning] {e}")
    AWARD_ENGINE_AVAILABLE = False

# 本地永久備份夾
LOCAL_BACKUP_DIR = r"E:\01.AI\Antigravity\標案網頁歷史備份"
os.makedirs(LOCAL_BACKUP_DIR, exist_ok=True)

# Git 同步資料夾中的 tenders 目錄
GIT_TENDERS_DIR = r"E:\01.AI\Antigravity\report\boss\tenders"
os.makedirs(GIT_TENDERS_DIR, exist_ok=True)

schoolKeywords = ["小學", "中學", "高級", "學校", "大學", "學院", "專科", "幼兒園", "高職", "高農"]
sportKeywords = ["體育", "運動", "操場", "跑道", "球場", "箭場", "冰場", "草地", "公園", "景觀", "水岸", "人行", "車道", "人本", "停車", "步道", "地坪", "休憩", "遊憩", "遊戲", "田徑場", "泳池"]
toiletKeywords = ["廁所", "公廁", "浴室", "辦公", "教室", "室內", "地板", "宿舍", "修繕", "變更使用", "裝修", "整修", "無障礙", "電梯", "復建", "中心", "活動中心"]
wallKeywords = ["防水", "隔熱", "外牆", "拉皮"]

highLightKeywords = [
    "設計", "監造", "規劃", "規畫", "工程", "修繕", "裝修", "整修", "技術服務",
    "可行性", "評估", "體育", "運動", "操場", "跑道", "球場", "箭場", "冰場",
    "地坪", "廁所", "公廁", "辦公室", "教室", "室內", "宿舍", "防水", "隔熱",
    "外牆", "拉皮", "公園", "休憩", "遊憩", "遊戲", "泳池"
]

def highlight_keywords(text):
    if not text:
        return ""
    # Sort keywords by length in descending order to avoid partial matches
    sorted_kws = sorted(highLightKeywords, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(kw) for kw in sorted_kws))
    return pattern.sub(lambda m: f'<span class="hl-red-bold">{m.group(0)}</span>', text)

def generate_section_html(data, section_type, title_text, header_class):
    if not data:
        return ""
    
    table_rows_html = ""
    mobile_cards_html = ""
    
    for row in data:
        while len(row) < 8:
            row.append("")
        idx_val, agency_val, name_val, trans_val, date_pub_val, date_end_val, budget_val, detail_url = row[:8]
        
        agency_cls = "school-red" if any(skw in agency_val for skw in schoolKeywords) else ""
        
        bg_cls = ""
        if any(spkw in name_val for spkw in sportKeywords):
            bg_cls = "bg-sport"
        elif any(tkw in name_val for tkw in toiletKeywords):
            bg_cls = "bg-toilet"
        elif any(wkw in name_val for wkw in wallKeywords):
            bg_cls = "bg-wall"
            
        strikethrough_style = "text-decoration: line-through; color: #64748b;" if section_type == "removed" else ""
        
        name_html = highlight_keywords(name_val).replace("\n", "<br>")
        
        trans_html = str(trans_val).replace("\n", "<br>")
        deadline_html = str(date_end_val)
        budget_html = str(budget_val)
        
        # 判斷是否為學校運動類標案以加入超連結，現改為所有案都要有連結
        data_url_attr = ""
        if detail_url.strip():
            data_url_attr = f' data-url="{detail_url.strip()}"'
        
        table_rows_html += f"""                    <tr style="{strikethrough_style}"{data_url_attr}>
                        <td class="col-idx">{idx_val}</td>
                        <td class="col-agency {agency_cls}">{agency_val}</td>
                        <td class="col-name {bg_cls}">{name_html}</td>
                        <td class="col-trans">{trans_html}</td>
                        <td class="col-date-pub">{date_pub_val}</td>
                        <td class="col-date-end">{deadline_html}</td>
                        <td class="col-budget">{budget_html}</td>
                    </tr>\n"""
        
        mobile_name = highlight_keywords(name_val).replace("\n", " ")
        mobile_cards_html += f"""            <div class="mobile-tender-row {bg_cls}" style="{strikethrough_style}"{data_url_attr}>
                <div class="mobile-row-meta">
                    <span class="mobile-row-idx">#{idx_val}</span>
                    <span class="mobile-row-agency {agency_cls}">{agency_val}</span>
                    <span class="mobile-row-budget">預算金額：{budget_html}</span>
                </div>
                <div class="mobile-row-name">{mobile_name}</div>
                <div class="mobile-row-dates">
                    📅 公告：{date_pub_val} | 截止：{deadline_html} | 傳：{trans_html.replace('<br>', '')}
                </div>
            </div>\n"""
            
    return f"""
        <div class="diff-section-container" style="margin-bottom: 40px; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; background: #ffffff; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);">
            <div class="diff-section-header {header_class}" style="padding: 14px 20px; font-weight: 700; color: #ffffff; background: {get_header_gradient(header_class)};">{title_text}</div>
            <div style="padding: 16px;">
                <!-- 電腦版 -->
                <div class="table-responsive" style="margin-bottom: 0; border: none; border-radius: 0;">
                    <table>
                        <thead>
                            <tr>
                                <th class="col-idx">項次</th>
                                <th class="col-agency">機關名稱</th>
                                <th class="col-name">標案案號 / 標案名稱</th>
                                <th class="col-trans">傳輸<br>次數</th>
                                <th class="col-date-pub">公告日期</th>
                                <th class="col-date-end">截止投標</th>
                                <th class="col-budget">預算金額</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows_html}
                        </tbody>
                    </table>
                </div>
                <!-- 手機版 -->
                <div class="mobile-tender-list" style="margin-bottom: 0;">
                    {mobile_cards_html}
                </div>
            </div>
        </div>
    """

def get_header_gradient(cls):
    if cls == "added":
        return "linear-gradient(135deg, #10b981, #059669)"
    elif cls == "modified":
        return "linear-gradient(135deg, #3b82f6, #1d4ed8)"
    elif cls == "removed":
        return "linear-gradient(135deg, #ef4444, #b91c1c)"
    elif cls == "rec":
        return "linear-gradient(135deg, #8b5cf6, #6d28d9)"
    return "#64748b"

def main():
    print("==================================================")
    print("[啟動] C專案 Google 試算表讀取與 HTML 網頁生成服務")
    print("==================================================")
    
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"[錯誤] 找不到金鑰檔案 {CREDENTIALS_PATH}")
        return
        
    print("[驗證] 正在進行 Google Cloud 身分驗證...")
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scope)
    gc = gspread.authorize(creds)

    spreadsheet_id = '1xPTrVcnw_79bXUGIY8qZcRdgFJI5nuJPa9No5TpiDSg'
    try:
        sh = gc.open_by_key(spreadsheet_id)
        print(f"[成功] 成功開啟試算表：{sh.title}")
    except Exception as e:
        print(f"[錯誤] 開啟試算表失敗: {e}")
        return

    print("[尋找] 正在檢索今日最新分頁...")
    worksheets = sh.worksheets()
    today_prefix = datetime.now().strftime('%Y/') + str(int(datetime.now().strftime('%m'))) + "/" + str(int(datetime.now().strftime('%d')))
    
    target_sheet = None
    first_today_match = None
    # 優先從最後面往前找符合今天日期的分頁，且必須包含「學校運動」以確保為 C 專案分頁
    for w in reversed(worksheets):
        if w.title.startswith(today_prefix):
            if not first_today_match:
                first_today_match = w
            try:
                temp_vals = w.get_all_values()
                if w.title.endswith("-下午") or any(any("學校運動" in str(cell) for cell in row) for row in temp_vals):
                    target_sheet = w
                    break
            except Exception as e:
                print(f"[警告] 檢查分頁 {w.title} 時發生錯誤: {e}")
                
    if not target_sheet and first_today_match:
        target_sheet = first_today_match
            
    if target_sheet:
        print(f"[成功] 找到今日分頁：{target_sheet.title}")
    else:
        target_sheet = worksheets[-1]
        print(f"[警告] 未找到以今日日期 {today_prefix} 開頭的分頁，退回使用最後一個分頁：{target_sheet.title}")

    print("[讀取] 正在讀取所有分頁資料...")
    try:
        all_values = target_sheet.get_all_values()
        print(f"[成功] 成功讀取 {len(all_values)} 列原始資料。")
    except Exception as e:
        print(f"[錯誤] 讀取試算表資料失敗: {e}")
        return

    if not all_values or len(all_values) <= 1:
        print("[錯誤] 試算表內無有效資料。")
        return

    # 5. 解析資料：區分主表與推薦區塊，支援下午異動
    is_afternoon_sheet = "-下午" in target_sheet.title
    
    added_data = []
    modified_data = []
    removed_data = []
    rec_diff_data = []
    
    main_data = []
    rec_items = []
    no_rec_msg = ""
    
    if is_afternoon_sheet:
        print("[解析] 偵測為下午異動分頁，執行區塊解析...")
        current_section = None
        for r in all_values:
            if not any(cell.strip() for cell in r):
                continue
            if "下午新增案件" in str(r):
                current_section = "added"
                continue
            elif "下午修改案件" in str(r):
                current_section = "modified"
                continue
            elif "下午減少案件" in str(r):
                current_section = "removed"
                continue
            elif "學校運動類推薦異動" in str(r):
                current_section = "recommended"
                continue
            elif any("項" in str(cell) for cell in r) and any("機關名稱" in str(cell) for cell in r):
                continue
            elif len(r) > 1 and r[1].strip() == "機關名稱":
                continue
                
            while len(r) < 8:
                r.append("")
                
            if current_section == "added":
                added_data.append(r)
            elif current_section == "modified":
                modified_data.append(r)
            elif current_section == "removed":
                removed_data.append(r)
            elif current_section == "recommended":
                rec_diff_data.append(r)
        print(f"[解析] 下午異動解析完成：新增 {len(added_data)} 筆，修改 {len(modified_data)} 筆，減少 {len(removed_data)} 筆，推薦異動 {len(rec_diff_data)} 筆。")
    else:
        # 上午全量解析 (雙重推薦區塊：操場跑道 + 運動類)
        main_rows = []
        track_field_items = []
        sports_items = []
        rec_items = []
        
        # 尋找全體資料中的主要表格內容
        header_indices = []
        for idx, r in enumerate(all_values):
            if any("項" in str(cell) for cell in r) and any("機關名稱" in str(cell) for cell in r):
                header_indices.append(idx)
                
        # 主表通常位在最後一個表頭區塊之後
        if header_indices:
            main_start_idx = header_indices[-1] + 1
            for idx in range(main_start_idx, len(all_values)):
                r = all_values[idx]
                if any(cell.strip() for cell in r) and r[0].strip().isdigit():
                    main_rows.append(r)
            main_data = main_rows
        else:
            # 備用保險機制
            main_data = [r for r in all_values if len(r) > 2 and r[0].strip().isdigit()]

        # 計算操場跑道與運動類推薦項目
        track_field_kws = ["操場", "跑道", "田徑場"]
        sports_kws = ["體育", "運動", "球場", "箭場", "冰場", "泳池"]
        design_kws = ["設計", "監造", "技術服務"]

        for item in main_data:
            while len(item) < 8:
                item.append("")
            agency_val = item[1].strip()
            name_val = item[2].strip()
            combined = f"{agency_val} {name_val}"
            has_design = any(kw in combined for kw in design_kws)
            has_track = any(kw in combined for kw in track_field_kws)
            has_sports = any(kw in combined for kw in sports_kws)
            
            if has_design and has_track:
                track_field_items.append(item)
            elif has_design and has_sports:
                sports_items.append(item)
                
        rec_items = track_field_items + sports_items
        print(f"[解析] 主表資料 {len(main_data)} 筆，操場跑道推薦 {len(track_field_items)} 筆，運動類推薦 {len(sports_items)} 筆。")

    # 6. 滾動清理：刪除 30 天前的舊 Git 網頁檔案
    print("[清理] 正在執行 30 天滾動清理篩選...")
    now_date = datetime.now()
    deleted_count = 0
    for f_name in os.listdir(GIT_TENDERS_DIR):
        if f_name.startswith("tenders_") and f_name.endswith(".html"):
            base = f_name[:-5]
            parts = base.split('_')
            if len(parts) >= 2:
                date_str = parts[-2]
                try:
                    file_date = datetime.strptime(date_str, "%Y%m%d")
                    delta = now_date - file_date
                    if delta.days > 30:
                        git_file_path = os.path.join(GIT_TENDERS_DIR, f_name)
                        os.remove(git_file_path)
                        deleted_count += 1
                except Exception as ex:
                    print(f"⚠️ 無法解析檔案日期 {f_name}: {ex}")
    if deleted_count > 0:
        print(f"       ✅ 成功清除 {deleted_count} 個超過 30 天的舊 Git 網頁！")

    # 7. 生成 HTML
    now_time_str = datetime.now().strftime('%Y/%m/%d %H:%M')
    file_time_suffix = datetime.now().strftime('%Y%m%d_%H%M')
    sheet_title_clean = target_sheet.title.replace('/', '_').replace('-', '_')
    filename = f"tenders_{sheet_title_clean}_{file_time_suffix}.html"

    # Meta Tags
    if is_afternoon_sheet:
        meta_tags = f"""    <meta name="is-afternoon" content="true">
    <meta name="total-added" content="{len(added_data)}">
    <meta name="total-modified" content="{len(modified_data)}">
    <meta name="total-removed" content="{len(removed_data)}">
    <meta name="total-rec" content="{len(rec_diff_data)}">
    <meta name="sheet-title" content="{target_sheet.title}">"""
        title_str = f"政府標案下午異動整理 - {now_time_str}"
    else:
        meta_tags = f"""    <meta name="total-tenders" content="{len(main_data)}">
    <meta name="rec-tenders" content="{len(rec_items)}">
    <meta name="sheet-title" content="{target_sheet.title}">"""
        title_str = f"政府標案公告整理 - {now_time_str}"

    html_content = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_str}</title>
{meta_tags}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: #f8fafc;
            color: #1e293b;
            font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif;
            padding: 24px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #ffffff;
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
        }}
        header {{
            margin-bottom: 24px;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 16px;
        }}
        h1 {{
            font-size: 24px;
            font-weight: 900;
            color: #0f172a;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .update-time {{
            font-size: 13px;
            color: #64748b;
            margin-top: 4px;
        }}
        .back-btn-portal:hover {{
            background: #cbd5e1 !important;
            color: #0f172a !important;
        }}
        
        /* 表格樣式 (電腦版) */
        .table-responsive {{
            overflow-x: auto;
            margin-bottom: 40px;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }}
        th, td {{
            padding: 12px 14px;
            border-bottom: 1px solid #e2e8f0;
            vertical-align: middle;
            word-break: break-all;
        }}
        th {{
            background-color: #f1f5f9;
            font-weight: 700;
            color: #334155;
            text-align: center;
        }}
        
        .col-idx {{ width: 5%; text-align: center; }}
        .col-agency {{ width: 18%; }}
        .col-name {{ width: 43%; }}
        .col-trans {{ width: 6%; text-align: center; }}
        .col-date-pub {{ width: 9%; text-align: center; }}
        .col-date-end {{ width: 9%; text-align: center; }}
        .col-budget {{ width: 10%; text-align: right; }}

        .school-red {{
            color: #dc2626 !important;
            font-weight: 700;
        }}
        .bg-sport {{ background-color: #e2f0d9 !important; }}
        .bg-toilet {{ background-color: #ddebf7 !important; }}
        .bg-wall {{ background-color: #fce4d6 !important; }}
        .hl-red-bold {{
            color: #dc2626;
            font-weight: 700;
        }}
        
        /* 推薦標案卡片樣式 */
        .rec-section {{
            margin-top: 40px;
        }}
        .rec-title {{
            font-size: 18px;
            font-weight: 900;
            color: #1e3a8a;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-left: 5px solid #1e3a8a;
            padding-left: 10px;
        }}
        .rec-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 16px;
        }}
        .rec-card {{
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-left: 6px solid #10b981;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .rec-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        }}
        .rec-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .rec-badge-agency {{
            font-size: 12px;
            font-weight: 700;
            color: #dc2626;
            background: #fee2e2;
            padding: 4px 10px;
            border-radius: 20px;
        }}
        .rec-budget {{
            font-size: 13px;
            font-weight: 500;
            color: #475569;
        }}
        .rec-tender-name {{
            font-size: 16px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 12px;
            line-height: 1.4;
        }}
        .rec-details {{
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            font-size: 12px;
            color: #64748b;
            background: #f8fafc;
            padding: 8px 12px;
            border-radius: 8px;
        }}
        .rec-detail-item strong {{
            color: #475569;
        }}
        .no-rec-message {{
            color: #64748b;
            font-style: italic;
            background: #f1f5f9;
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }}

        /* 手機版凝聚卡片列表 */
        .mobile-tender-list {{
            display: none;
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 12px;
            }}
            .container {{
                padding: 16px;
                border-radius: 12px;
            }}
            .table-responsive {{
                display: none;
            }}
            .mobile-tender-list {{
                display: flex;
                flex-direction: column;
                gap: 10px;
                margin-bottom: 30px;
            }}
            .mobile-tender-row {{
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
            }}
            .mobile-row-meta {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 6px;
                font-size: 12px;
            }}
            .mobile-row-idx {{
                background: rgba(0, 0, 0, 0.05);
                color: #475569;
                font-weight: 700;
                padding: 1px 5px;
                border-radius: 4px;
                font-size: 11px;
            }}
            .mobile-row-agency {{
                font-weight: 700;
                margin-left: 6px;
                margin-right: auto;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 170px;
            }}
            .mobile-row-budget {{
                font-weight: 700;
                color: #0f172a;
                white-space: nowrap;
            }}
            .mobile-row-name {{
                font-weight: 500;
                color: #1e293b;
                margin-bottom: 6px;
                line-height: 1.4;
                word-break: break-all;
            }}
            .mobile-row-dates {{
                font-size: 11px;
                color: #64748b;
                border-top: 1px dashed rgba(0,0,0,0.08);
                padding-top: 6px;
                margin-top: 4px;
            }}
        }}

        /* 懸停手型指針與效果 */
        [data-url] {{
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        tr[data-url]:hover {{
            background-color: #f1f5f9 !important;
        }}

        /* 彈窗 Modal 樣式 */
        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(15, 23, 42, 0.4);
            backdrop-filter: blur(8px);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }}
        .modal-overlay.active {{
            opacity: 1;
            pointer-events: auto;
        }}
        .modal-card {{
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            width: 90%;
            max-width: 480px;
            padding: 24px;
            transform: scale(0.9);
            transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }}
        .modal-overlay.active .modal-card {{
            transform: scale(1);
        }}
        .modal-title {{
            font-size: 18px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .modal-body {{
            font-size: 14px;
            color: #475569;
            margin-bottom: 20px;
            line-height: 1.6;
        }}
        .modal-tender-info {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px;
            font-weight: 700;
            color: #1e293b;
            margin-top: 8px;
            word-break: break-all;
        }}
        .modal-actions {{
            display: flex;
            justify-content: flex-end;
            gap: 12px;
        }}
        .modal-btn {{
            padding: 10px 18px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            border: none;
            transition: background 0.2s, transform 0.1s;
        }}
        .modal-btn-cancel {{
            background: #f1f5f9;
            color: #475569;
        }}
        .modal-btn-cancel:hover {{
            background: #e2e8f0;
        }}
        .modal-btn-award {{
            background: #7c3aed;
            color: #ffffff;
        }}
        .modal-btn-award:hover {{
            background: #6d28d9;
        }}
        .modal-btn-confirm {{
            background: #1e3a8a;
            color: #ffffff;
        }}
        .modal-btn-confirm:hover {{
            background: #1d4ed8;
        }}
        .modal-btn-bid {{
            background: #059669;
            color: #ffffff;
        }}
        .modal-btn-bid:hover {{
            background: #047857;
        }}
        .bid-select-panel {{
            margin-top: 12px;
            padding: 12px;
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 8px;
            text-align: left;
        }}
        .bid-select-label {{
            font-weight: 700;
            font-size: 13px;
            color: #166534;
            margin-bottom: 6px;
            display: block;
        }}
        .bid-select-control {{
            width: 100%;
            padding: 8px 12px;
            font-size: 14px;
            border: 1px solid #86efac;
            border-radius: 6px;
            background: #ffffff;
            color: #0f172a;
            outline: none;
            font-weight: 600;
        }}
        .bid-status-toast {{
            margin-top: 10px;
            padding: 10px;
            background: #dcfce7;
            border: 1px solid #86efac;
            border-radius: 6px;
            color: #15803d;
            font-size: 13px;
            font-weight: 700;
            text-align: left;
        }}
        .modal-btn:active {{
            transform: scale(0.97);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 12px; border-bottom: 1px dashed rgba(0,0,0,0.06); padding-bottom: 8px;">
                <div style="display: flex; gap: 8px; margin-bottom: 6px;">
                    <a href="../tenders.html" class="back-btn-portal" style="display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: #475569; text-decoration: none; font-weight: 700; background: #e2e8f0; padding: 4px 10px; border-radius: 6px; transition: background 0.2s;">⬅️ 返回標案列表</a>
                    <a href="../../database_portal.html" class="back-btn-portal" style="display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: #475569; text-decoration: none; font-weight: 700; background: #e2e8f0; padding: 4px 10px; border-radius: 6px; transition: background 0.2s;">🌿 返回世界樹資料庫</a>
                </div>
                <div style="font-size: 12px; color: #64748b; font-weight: 700; display: flex; align-items: center; gap: 4px;">
                    👁️ 點閱次數：<span id="visit-count-val" style="color: #1e3a8a; font-weight: 800;">0</span> 次
                </div>
            </div>
            <h1>💼 {title_str.split(' - ')[0]}</h1>
            <div class="update-time">🕒 更新時間：{now_time_str} ({target_sheet.title} 分頁)</div>
        </header>
"""

    if is_afternoon_sheet:
        # 下午異動版渲染 - 推薦異動置頂
        html_content += generate_section_html(rec_diff_data, "rec", "🏫 學校運動類推薦異動", "rec")
        html_content += generate_section_html(added_data, "added", f"➕ 下午新增案件 (共 {len(added_data)} 筆)", "added")
        html_content += generate_section_html(modified_data, "modified", f"📝 下午修改案件 (共 {len(modified_data)} 筆)", "modified")
        html_content += generate_section_html(removed_data, "removed", f"❌ 下午減少案件/撤案 (共 {len(removed_data)} 筆)", "removed")
        
        # 若皆空
        if not added_data and not modified_data and not removed_data:
            html_content += """        <div style="text-align: center; padding: 40px; color: #64748b; font-style: italic;">本日下午無任何標案異動。</div>"""
    else:
        # 上午全量版渲染
        
        # 1. 操場跑道標案推薦區塊
        html_content += """
        <!-- 操場跑道標案推薦區塊 -->
        <div class="rec-section" style="margin-top: 0; margin-bottom: 30px;">
            <div class="rec-title">🏃 操場跑道標案推薦</div>
"""
        if track_field_items:
            html_content += '            <div class="rec-grid">\n'
            for r_idx, r_item in enumerate(track_field_items, 1):
                while len(r_item) < 8:
                    r_item.append("")
                idx_val, agency_val, name_val, trans_val, date_pub_val, date_end_val, budget_val, detail_url = r_item[:8]

                highlighted_name = highlight_keywords(name_val.replace("\n", " ").strip())
                data_agency_attr = f' data-agency="{agency_val.strip()}"'
                data_url_attr = f' data-url="{detail_url.strip()}"{data_agency_attr}' if detail_url.strip() else ""

                html_content += f"""                <div class="rec-card"{data_url_attr}>
                    <div class="rec-card-header">
                        <span class="rec-badge-agency">{agency_val}</span>
                        <span class="rec-budget">預算金額：<strong>{budget_val}</strong></span>
                    </div>
                    <div class="rec-tender-name">{highlighted_name}</div>
                    <div class="rec-details">
                        <span class="rec-detail-item"><strong>項次：</strong>{r_idx}</span>
                        <span class="rec-detail-item"><strong>公告日期：</strong>{date_pub_val}</span>
                        <span class="rec-detail-item"><strong>截止投標：</strong>{date_end_val}</span>
                        <span class="rec-detail-item"><strong>傳輸次數：</strong>{trans_val.strip()}</span>
                    </div>
                </div>\n"""
            html_content += '            </div>\n'
        else:
            html_content += '            <div class="no-rec-message">今日無符合條件之操場跑道推薦標案。</div>\n'
            
        html_content += """        </div>"""

        # 2. 運動類標案推薦區塊
        html_content += """
        <!-- 運動類標案推薦區塊 -->
        <div class="rec-section" style="margin-bottom: 30px;">
            <div class="rec-title" style="color: #b45309; border-left-color: #f59e0b;">🏀 運動類標案推薦</div>
"""
        if sports_items:
            html_content += '            <div class="rec-grid">\n'
            for r_idx, r_item in enumerate(sports_items, 1):
                while len(r_item) < 8:
                    r_item.append("")
                idx_val, agency_val, name_val, trans_val, date_pub_val, date_end_val, budget_val, detail_url = r_item[:8]

                highlighted_name = highlight_keywords(name_val.replace("\n", " ").strip())
                data_agency_attr = f' data-agency="{agency_val.strip()}"'
                data_url_attr = f' data-url="{detail_url.strip()}"{data_agency_attr}' if detail_url.strip() else ""
                
                is_non_school = not any(sk in agency_val for sk in ["學校", "國小", "國中", "中學", "高中", "大學"])
                agency_display = f"{agency_val} (非學校機關亮點)" if is_non_school else agency_val

                html_content += f"""                <div class="rec-card" style="border-left-color: #f59e0b;"{data_url_attr}>
                    <div class="rec-card-header">
                        <span class="rec-badge-agency" style="{'background: #e0f2fe; color: #0369a1;' if is_non_school else ''}">{agency_display}</span>
                        <span class="rec-budget">預算金額：<strong>{budget_val}</strong></span>
                    </div>
                    <div class="rec-tender-name">{highlighted_name}</div>
                    <div class="rec-details">
                        <span class="rec-detail-item"><strong>項次：</strong>{r_idx}</span>
                        <span class="rec-detail-item"><strong>公告日期：</strong>{date_pub_val}</span>
                        <span class="rec-detail-item"><strong>截止投標：</strong>{date_end_val}</span>
                        <span class="rec-detail-item"><strong>傳輸次數：</strong>{trans_val.strip()}</span>
                    </div>
                </div>\n"""
            html_content += '            </div>\n'
        else:
            html_content += '            <div class="no-rec-message">今日無符合條件之運動類推薦標案。</div>\n'
            
        html_content += """        </div>"""

        # 3. 電腦版表格 (一般搜尋標案)
        html_content += """
        <div class="rec-title" style="color: #0f172a; border-left-color: #0f172a; margin-top: 35px;">📋 本日查詢到的所有詳細標案資訊</div>
"""

        # 2. 電腦版表格 (一般搜尋標案)
        html_content += """
        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th class="col-idx">項次</th>
                        <th class="col-agency">機關名稱</th>
                        <th class="col-name">標案案號 / 標案名稱</th>
                        <th class="col-trans">傳輸<br>次數</th>
                        <th class="col-date-pub">公告日期</th>
                        <th class="col-date-end">截止投標</th>
                        <th class="col-budget">預算金額</th>
                    </tr>
                </thead>
                <tbody>
"""
        for row in main_data:
            while len(row) < 8:
                row.append("")
            idx_val, agency_val, name_val, trans_val, date_pub_val, date_end_val, budget_val, detail_url = row[:8]

            agency_cls = "school-red" if any(skw in agency_val for skw in schoolKeywords) else ""
            bg_cls = ""
            if any(spkw in name_val for spkw in sportKeywords):
                bg_cls = "bg-sport"
            elif any(tkw in name_val for tkw in toiletKeywords):
                bg_cls = "bg-toilet"
            elif any(wkw in name_val for wkw in wallKeywords):
                bg_cls = "bg-wall"

            name_html = highlight_keywords(name_val).replace("\n", "<br>")
            trans_html = str(trans_val).replace('\n', '<br>')

            # 判斷是否為學校運動類標案以加入超連結，現改為所有案都要有連結
            data_agency_attr = f' data-agency="{agency_val.strip()}"'
            data_url_attr = f' data-url="{detail_url.strip()}"{data_agency_attr}' if detail_url.strip() else ""

            html_content += f"""                    <tr{data_url_attr}>
                        <td class="col-idx">{idx_val}</td>
                        <td class="col-agency {agency_cls}">{agency_val}</td>
                        <td class="col-name {bg_cls}">{name_html}</td>
                        <td class="col-trans">{trans_html}</td>
                        <td class="col-date-pub">{date_pub_val}</td>
                        <td class="col-date-end">{date_end_val}</td>
                        <td class="col-budget">{budget_val}</td>
                    </tr>\n"""

        html_content += """                </tbody>
            </table>
        </div>

        <!-- 3. 手機版凝聚型卡片列表 -->
        <div class="mobile-tender-list">
"""
        for row in main_data:
            while len(row) < 8:
                row.append("")
            idx_val, agency_val, name_val, trans_val, date_pub_val, date_end_val, budget_val, detail_url = row[:8]

            agency_cls = "school-red" if any(skw in agency_val for skw in schoolKeywords) else ""
            bg_cls = ""
            if any(spkw in name_val for spkw in sportKeywords):
                bg_cls = "bg-sport"
            elif any(tkw in name_val for tkw in toiletKeywords):
                bg_cls = "bg-toilet"
            elif any(wkw in name_val for wkw in wallKeywords):
                bg_cls = "bg-wall"

            name_html = highlight_keywords(name_val).replace("\n", " ")
            clean_trans = trans_val.strip().replace('\n', '')

            # 判斷是否為學校運動類標案以加入超連結，現改為所有案都要有連結
            data_agency_attr = f' data-agency="{agency_val.strip()}"'
            data_url_attr = f' data-url="{detail_url.strip()}"{data_agency_attr}' if detail_url.strip() else ""

            html_content += f"""            <div class="mobile-tender-row {bg_cls}"{data_url_attr}>
                <div class="mobile-row-meta">
                    <span class="mobile-row-idx">#{idx_val}</span>
                    <span class="mobile-row-agency {agency_cls}">{agency_val}</span>
                    <span class="mobile-row-budget">預算金額：{budget_val}</span>
                </div>
                <div class="mobile-row-name">{name_html}</div>
                <div class="mobile-row-dates">
                    📅 公告：{date_pub_val} | 截止：{date_end_val} | 傳：{clean_trans}
                </div>
            </div>\n"""

        html_content += """        </div>"""

    html_content += """
    </div>
    
    <!-- ── 訪問追蹤與統計腳本 ── -->
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const pagePath = window.location.pathname;
            const filename = pagePath.substring(pagePath.lastIndexOf('/') + 1) || 'default_tender';
            const pageKey = "tender_page_" + filename.replace(/\\./g, '_');
            
            // 1. 紀錄目前頁面點閱
            let visitCounts = JSON.parse(localStorage.getItem('yggdrasil_visit_counts') || '{}');
            visitCounts[pageKey] = (visitCounts[pageKey] || 0) + 1;
            localStorage.setItem('yggdrasil_visit_counts', JSON.stringify(visitCounts));
            
            // 2. 更新畫面顯示
            document.getElementById('visit-count-val').innerText = visitCounts[pageKey];
        });

        // ── 彈窗確認模組邏輯 ──
        document.addEventListener('DOMContentLoaded', () => {
            // 建立 Modal DOM 節點並加入 body
            const modalHtml = `
                <div id="tender-modal" class="modal-overlay">
                    <div class="modal-card">
                        <div class="modal-title">🔗 標案詳細操作與投標管理</div>
                        <div class="modal-body">
                            您可選擇登記【我要投標】、檢索機關 5 年決標履歷，或前往電子採購網查看當前公告：
                            <div id="modal-tender-name" class="modal-tender-info"></div>
                            
                            <!-- 投標選擇面板 -->
                            <div id="modal-bid-panel" class="bid-select-panel" style="display: none;">
                                <label class="bid-select-label">🎯 請選擇負責之設計師：</label>
                                <select id="designer-select" class="bid-select-control">
                                    <option value="吳設計師">吳設計師</option>
                                    <option value="江設計師">江設計師</option>
                                    <option value="林設計師">林設計師</option>
                                </select>
                                <button id="modal-bid-submit" class="modal-btn modal-btn-bid" style="width: 100%; margin-top: 10px;">正式登記投標意向</button>
                            </div>
                            <div id="bid-status-message" class="bid-status-toast" style="display: none;"></div>
                        </div>
                        <div class="modal-actions">
                            <button id="modal-cancel-btn" class="modal-btn modal-btn-cancel">取消</button>
                            <button id="modal-bid-btn" class="modal-btn modal-btn-bid">🎯 我要投標</button>
                            <button id="modal-award-btn" class="modal-btn modal-btn-award">🏛️ 機關歷史履歷</button>
                            <button id="modal-confirm-btn" class="modal-btn modal-btn-confirm">🌐 前往採購網</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);

            const modal = document.getElementById('tender-modal');
            const modalTenderName = document.getElementById('modal-tender-name');
            const cancelBtn = document.getElementById('modal-cancel-btn');
            const bidBtn = document.getElementById('modal-bid-btn');
            const awardBtn = document.getElementById('modal-award-btn');
            const confirmBtn = document.getElementById('modal-confirm-btn');
            const bidPanel = document.getElementById('modal-bid-panel');
            const bidSubmitBtn = document.getElementById('modal-bid-submit');
            const designerSelect = document.getElementById('designer-select');
            const statusMsg = document.getElementById('bid-status-message');

            let targetUrl = '';
            let targetAgency = '';
            let currentExtraData = {};

            // 內部對應表：前端顯示稱號 ➔ 後端連線資料庫實名
            const designerRealNameMap = {
                "吳設計師": "吳誌軒",
                "江設計師": "江明鴻",
                "林設計師": "林宏明"
            };

            const showModal = (tenderName, url, agency, extraData = {}) => {
                if (!url) return;
                targetUrl = url;
                targetAgency = agency || '';
                currentExtraData = extraData;
                modalTenderName.innerText = tenderName;
                bidPanel.style.display = 'none';
                statusMsg.style.display = 'none';
                modal.classList.add('active');
            };

            const hideModal = () => {
                modal.classList.remove('active');
                targetUrl = '';
                targetAgency = '';
                currentExtraData = {};
                bidPanel.style.display = 'none';
                statusMsg.style.display = 'none';
            };

            // 監聽有設定 data-url 的元素點擊事件
            document.addEventListener('click', (e) => {
                const clickable = e.target.closest('[data-url]');
                if (clickable) {
                    const url = clickable.getAttribute('data-url');
                    const agency = clickable.getAttribute('data-agency') || '';
                    let tenderName = '';
                    
                    if (clickable.classList.contains('rec-card')) {
                        tenderName = clickable.querySelector('.rec-tender-name').innerText;
                    } else if (clickable.tagName === 'TR') {
                        const nameTd = clickable.querySelector('.col-name');
                        const agencyTd = clickable.querySelector('.col-agency');
                        tenderName = `${agencyTd ? agencyTd.innerText.trim() : ''} - ${nameTd ? nameTd.innerText.replace(/<<\\s*/, '').trim() : ''}`;
                    } else if (clickable.classList.contains('mobile-tender-row')) {
                        const nameDiv = clickable.querySelector('.mobile-row-name');
                        const agencySpan = clickable.querySelector('.mobile-row-agency');
                        tenderName = `${agencySpan ? agencySpan.innerText.trim() : ''} - ${nameDiv ? nameDiv.innerText.trim() : ''}`;
                    } else {
                        tenderName = clickable.innerText || '未命名標案';
                    }
                    
                    showModal(tenderName, url, agency);
                }
            });

            cancelBtn.addEventListener('click', hideModal);
            
            if (bidBtn) {
                bidBtn.addEventListener('click', () => {
                    bidPanel.style.display = bidPanel.style.display === 'none' ? 'block' : 'none';
                    statusMsg.style.display = 'none';
                });
            }

            if (bidSubmitBtn) {
                bidSubmitBtn.addEventListener('click', async () => {
                    const selectedDesignerTitle = designerSelect.value;
                    const realName = designerRealNameMap[selectedDesignerTitle] || selectedDesignerTitle;
                    const fullTenderTitle = modalTenderName.innerText;
                    
                    // 嘗試從標案名稱抽離案號
                    let tenderId = "";
                    const idMatch = fullTenderTitle.match(/\[([A-Za-z0-9\-_]+)\]/);
                    if (idMatch) {
                        tenderId = idMatch[1];
                    } else {
                        tenderId = "TENDER-" + Math.floor(Date.now() / 1000);
                    }

                    const cleanPayload = {
                        tender_id: tenderId,
                        tender_name: fullTenderTitle,
                        agency_name: targetAgency || "全省標案機關",
                        designer_name: realName
                    };

                    console.log("[正式登記投標 Payload (測試用)]", cleanPayload);
                    bidSubmitBtn.disabled = true;
                    bidSubmitBtn.innerText = "⏳ 正在傳送 (測試用)...";
                    statusMsg.style.display = 'block';
                    statusMsg.innerHTML = `⏳ 正在連線 Serverless API 轉發中... <span style="font-size:10px; color:#d97706; background:#fef3c7; padding:1px 4px; border-radius:3px;">[測試用 API]</span>`;

                    try {
                        const response = await fetch('/api/submit-bid', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(cleanPayload)
                        });

                        const resData = await response.json().catch(() => ({}));

                        if (response.status === 201) {
                            statusMsg.innerHTML = `
                                ✅ <strong>投標意向登記成功！</strong><br>
                                <strong>機關：</strong>${cleanPayload.agency_name}<br>
                                <strong>標案：</strong>${cleanPayload.tender_name}<br>
                                <strong>責任設計師：</strong>${selectedDesignerTitle} (${realName})<br>
                                <span style="font-size:11px; color:#15803d;">(已成功連線建立於毅築案件管理系統)</span>
                            `;
                        } else if (response.status === 409 || resData.error === 'duplicate_tender_id') {
                            statusMsg.innerHTML = `
                                ⚠️ <strong>此標案已建立過！</strong><br>
                                <span style="font-size:12px; color:#b45309;">案號 (${tenderId}) 已登記於系統，請至毅築標案管理操作。</span>
                            `;
                        } else if (response.status === 503) {
                            statusMsg.innerHTML = `
                                ⚙️ <strong>連線金鑰設定中</strong><br>
                                <span style="font-size:11px; color:#6b7280;">訊息：${resData.message || resData.error || 'Server not configured'}</span>
                            `;
                        } else if (response.status === 404) {
                            statusMsg.innerHTML = `
                                ⚠️ <strong>連線提示 (404)</strong><br>
                                <span style="font-size:11px; color:#dc2626;">GitHub Pages 為純靜態託管。請於 Vercel 正式網址開啟即可連線！</span>
                            `;
                        } else {
                            statusMsg.innerHTML = `
                                ⚠️ <strong>登記投標失敗 (${response.status})</strong><br>
                                <span style="font-size:11px; color:#dc2626;">${resData.message || resData.error || '無法完成連線'}</span>
                            `;
                        }
                    } catch (err) {
                        statusMsg.innerHTML = `
                            ⚠️ <strong>連線異常</strong><br>
                            <span style="font-size:11px; color:#dc2626;">${err.message || '請確認是否於 Vercel 環境執行'}</span>
                        `;
                    } finally {
                        bidSubmitBtn.disabled = false;
                        bidSubmitBtn.innerText = "正式登記投標意向";
                        bidPanel.style.display = 'none';
                    }
                });
            }

            if (awardBtn) {
                awardBtn.addEventListener('click', () => {
                    if (targetAgency) {
                        const awardUrl = `awards/award_analytics_${encodeURIComponent(targetAgency)}.html`;
                        window.open(awardUrl, '_blank');
                    }
                    hideModal();
                });
            }

            confirmBtn.addEventListener('click', () => {
                if (targetUrl) {
                    window.open(targetUrl, '_blank');
                }
                hideModal();
            });

            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    hideModal();
                }
            });
        });
    </script>
</body>
</html>
"""

    # ── C專案進階版：自動掃描並產出當日機關之 5 年歷史決標履歷 ──
    if ENABLE_AWARD_HISTORY and AWARD_ENGINE_AVAILABLE:
        print("\n🚀 [C專案進階版] 正在掃描當日標案機關並生成 5 年歷史決標履歷...")
        awards_dir = os.path.join(GIT_TENDERS_DIR, "awards")
        os.makedirs(awards_dir, exist_ok=True)
        
        all_agencies = set()
        for row in main_data:
            if len(row) > 1 and row[1].strip():
                all_agencies.add(row[1].strip())
                
        print(f"[進階版] 發現當日共 {len(all_agencies)} 個獨立機關，開始檢索歷史履歷...")
        for a_idx, agency in enumerate(all_agencies, 1):
            try:
                records = fetch_unit_award_history(agency)
                if records:
                    analytics = analyze_award_history(records, agency)
                    out_html_path = os.path.join(awards_dir, f"award_analytics_{agency}.html")
                    generate_html_report(analytics, out_html_path)
            except Exception as ex:
                print(f"   ⚠️ 檢索 [{agency}] 履歷時發生警告: {ex}")

    local_path = os.path.join(LOCAL_BACKUP_DIR, filename)
    git_path = os.path.join(GIT_TENDERS_DIR, filename)

    try:
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"[成功] 已成功產出本地歷史備份網頁：{local_path}")
    except Exception as ex:
        print(f"[錯誤] 寫入本地歷史備份網頁失敗: {ex}")

    try:
        with open(git_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"[成功] 已成功產出 Git 待同步網頁：{git_path}")
    except Exception as ex:
        print(f"[錯誤] 寫入 Git 待同步網頁失敗: {ex}")

    # 8. 重新動態編譯首頁 tenders.html
    print("[更新] 正在重新編譯首頁 tenders.html...")
    index_path = r"E:\01.AI\Antigravity\report\boss\tenders.html"
    if os.path.exists(index_path):
        tender_files = []
        for f_name in os.listdir(GIT_TENDERS_DIR):
            if f_name.startswith("tenders_") and f_name.endswith(".html"):
                f_path = os.path.join(GIT_TENDERS_DIR, f_name)
                
                is_afternoon = False
                total_tenders = 0
                rec_tenders = 0
                added_cnt = 0
                mod_cnt = 0
                rem_cnt = 0
                sheet_title = ""
                file_time_str = ""
                
                base = f_name[:-5]
                parts = base.split('_')
                timestamp_key = ""
                if len(parts) >= 2:
                    timestamp_key = f"{parts[-2]}_{parts[-1]}"
                    date_part = parts[-2]
                    time_part = parts[-1]
                    file_time_str = f"{date_part[:4]}/{date_part[4:6]}/{date_part[6:8]} {time_part[:2]}:{time_part[2:]}"
                
                try:
                    with open(f_path, 'r', encoding='utf-8') as tf:
                        content_slice = tf.read(5000)
                        
                        m_aft = re.search(r'<meta name="is-afternoon" content="true">', content_slice)
                        m_total = re.search(r'<meta name="total-tenders" content="(\d+)">', content_slice)
                        m_rec = re.search(r'<meta name="rec-tenders" content="(\d+)">', content_slice)
                        
                        m_added = re.search(r'<meta name="total-added" content="(\d+)">', content_slice)
                        m_modified = re.search(r'<meta name="total-modified" content="(\d+)">', content_slice)
                        m_removed = re.search(r'<meta name="total-removed" content="(\d+)">', content_slice)
                        m_rec_diff = re.search(r'<meta name="total-rec" content="(\d+)">', content_slice)
                        
                        m_sheet = re.search(r'<meta name="sheet-title" content="([^"]+)">', content_slice)
                        
                        if m_aft:
                            is_afternoon = True
                            added_cnt = int(m_added.group(1)) if m_added else 0
                            mod_cnt = int(m_modified.group(1)) if m_modified else 0
                            rem_cnt = int(m_removed.group(1)) if m_removed else 0
                            rec_tenders = int(m_rec_diff.group(1)) if m_rec_diff else 0
                        else:
                            if m_total: total_tenders = int(m_total.group(1))
                            if m_rec: rec_tenders = int(m_rec.group(1))
                            
                        if m_sheet: sheet_title = m_sheet.group(1)
                except Exception as ex:
                    print(f"⚠️ 讀取檔案 {f_name} 的 Meta 標記失敗: {ex}")
                
                tender_files.append({
                    'filename': f_name,
                    'key': timestamp_key,
                    'time_str': file_time_str,
                    'is_afternoon': is_afternoon,
                    'total': total_tenders,
                    'rec': rec_tenders,
                    'added': added_cnt,
                    'modified': mod_cnt,
                    'removed': rem_cnt,
                    'sheet': sheet_title
                })
        
        tender_files.sort(key=lambda x: x['key'], reverse=True)
        
        dynamic_html = "        <!-- DYNAMIC_TENDERS_START -->\n"
        for item in tender_files:
            relative_url = f"tenders/{item['filename']}"
            if item['is_afternoon']:
                card_icon = "⚡"
                card_title = f"{item['time_str']} 標案下午更新 ({item['sheet']})"
                card_desc = f"下午異動 · 新增 {item['added']} 筆 · 修改 {item['modified']} 筆 · 減少 {item['removed']} 筆"
                border_style = "border-left: 4px solid #3b82f6;"
                icon_bg = "background: linear-gradient(135deg, #3b82f6, #1d4ed8); box-shadow: 0 4px 12px rgba(59,130,246,0.2);"
            else:
                card_icon = "📅"
                card_title = f"{item['time_str']} 標案公告整理 ({item['sheet']})"
                card_desc = f"已篩選核心地區 · {item['total']} 筆標案 · {item['rec']} 筆學校運動推薦"
                border_style = "border-left: 4px solid var(--accent);"
                icon_bg = "background: linear-gradient(135deg, #d97706, var(--accent)); box-shadow: 0 4px 12px rgba(245,158,11,0.2);"
                
            dynamic_html += f"""        <a href="{relative_url}" class="report-card fade-up" style="{border_style} margin-bottom: 12px;">
            <div class="card-inner" style="padding: 16px 24px;">
                <div class="card-icon-wrap" style="width: 42px; height: 42px; font-size: 20px; {icon_bg}">{card_icon}</div>
                <div class="card-content">
                    <div class="card-name" style="font-size: 16px;">{card_title}</div>
                    <div class="card-desc" style="font-size: 12px;">{card_desc}</div>
                </div>
                <div class="card-arrow-btn" style="width: 36px; height: 36px; font-size: 14px;">→</div>
            </div>
        </a>\n"""
        dynamic_html += "        <!-- DYNAMIC_TENDERS_END -->"
        
        try:
            with open(index_path, 'r', encoding='utf-8') as inf:
                index_content = inf.read()
            
            pattern = r"<!-- DYNAMIC_TENDERS_START -->.*?<!-- DYNAMIC_TENDERS_END -->"
            new_index_content = re.sub(pattern, dynamic_html, index_content, flags=re.DOTALL)
            
            count_text = f"共 {len(tender_files)} 份更新"
            new_index_content = re.sub(r'<div class="topbar-count">.*?</div>', f'<div class="topbar-count">{count_text}</div>', new_index_content)
            
            with open(index_path, 'w', encoding='utf-8') as outf:
                outf.write(new_index_content)
            print(f"       ✅ 成功更新首頁 tenders.html！目前有 {len(tender_files)} 份歷史網頁。")
        except Exception as ex:
            print(f"[錯誤] 更新 tenders.html 失敗: {ex}")
    else:
        print(f"[警告] 找不到首頁檔案: {index_path}，無法進行首頁更新。")

    print("==================================================")
    print("[成功] 網頁產出與編譯處理完畢！")
    print("==================================================")

if __name__ == '__main__':
    main()
