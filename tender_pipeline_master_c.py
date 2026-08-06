# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import io
import datetime
import requests
import json
import re

# 強制 UTF-8 輸出，防止 Windows 本地 CP950 編碼衝突
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 定義 Python 解譯器路徑（優先使用專案 local 的 venv，否則使用預設）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 尋找 python.exe，支持地端 venv 與分享包 local 結構
PYTHON_EXE = os.path.join(SCRIPT_DIR, 'venv', 'Scripts', 'python.exe')
if not os.path.exists(PYTHON_EXE):
    # 地端預設路徑 (MCP下的 venv)
    PYTHON_EXE = r"E:\01.AI\Antigravity\MCP\venv\Scripts\python.exe"
if not os.path.exists(PYTHON_EXE):
    # 若依然找不到，退回系統全域 python.exe
    PYTHON_EXE = "python.exe"

SCRAPER_SCRIPT = os.path.join(SCRIPT_DIR, "tender_scraper_api_c.py")
SCREENSHOT_SCRIPT = os.path.join(SCRIPT_DIR, "test_screenshot_c.py")

EXIT_NO_DATA = 2
EXIT_NO_CHANGES = 3
EXIT_FAILURE = 1

def send_telegram_notification(message):
    """
    從專案目錄的 .env 讀取 TELEGRAM_BOT_TOKEN 與 TELEGRAM_CHAT_ID，並發送 HTML 格式通知。
    """
    try:
        env_path = os.path.join(SCRIPT_DIR, '.env')
        if not os.path.exists(env_path):
            print(f"[Telegram] 找不到 .env 檔案：{env_path}")
            return False
        
        bot_token = None
        chat_id = None
        
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    parts = line.split('=', 1)
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if key == 'TELEGRAM_BOT_TOKEN':
                        bot_token = val
                    elif key == 'TELEGRAM_CHAT_ID':
                        chat_id = val
        
        if not bot_token or not chat_id:
            print("[Telegram] 未在 .env 中設定 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("[Telegram] 通知發送成功！")
            return True
        else:
            print(f"[Telegram] 通知發送失敗，狀態碼: {response.status_code}, 回應: {response.text}")
            return False
    except Exception as e:
        print(f"[Telegram] 發送通知時發生異常: {e}")
        return False

def get_chinese_datetime():
    now = datetime.datetime.now()
    ampm = "上午" if now.hour < 12 else "下午"
    return f"{now.year}年{now.month}月{now.day}日 {ampm}{now.hour}:{now.minute:02d}"

def send_formatted_telegram_report(is_success=True, error_msg=""):
    """
    讀取 run_status.json 中的資料，根據上午/下午以及執行狀態，組合出符合格式的訊息並發送。
    """
    dt_str = get_chinese_datetime()
    
    # 預設值
    mode = "morning" if datetime.datetime.now().hour < 12 else "afternoon"
    total = 0
    recommended = 0
    added = 0
    removed = 0
    modified = 0
    
    # 試圖讀取狀態檔
    status_path = os.path.join(SCRIPT_DIR, 'run_status.json')
    if os.path.exists(status_path):
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                mode = data.get("mode", mode)
                sum_data = data.get("summary", {})
                
                total = sum_data.get("total", 0)
                recommended = sum_data.get("recommended", 0)
                added = sum_data.get("added", 0)
                removed = sum_data.get("removed", 0)
                modified = sum_data.get("modified", 0)
                
                # 如果是 morning 且總數為 0，從文字解析
                if mode == "morning" and total == 0:
                    msg = data.get("message", "")
                    m = re.search(r'共\s*(\d+)\s*筆標案', msg)
                    if m:
                        total = int(m.group(1))
        except Exception as e:
            print(f"[Telegram] 讀取狀態檔失敗: {e}")

    if not is_success:
        # 錯誤通知
        msg_text = f"❌ <b>[標案自動化助手 - 錯誤告警]</b>\n執行時間：{dt_str}\n執行中斷！原因：{error_msg}"
        send_telegram_notification(msg_text)
        return

    # 組合成功通知 (遵照最新指定格式與 Vercel 網址)
    if mode == "morning":
        msg_text = (
            f"今日工程標案已更新\n"
            f"標案總數{total}個 學校運動標案{recommended}個\n"
            f"{dt_str} 發布完成\n"
            f"🔗 <a href='https://report-alpha-two.vercel.app/boss/tenders.html'>點此查看標案列表</a>"
        )
    else:
        msg_text = (
            f"今日工程標案已更新\n"
            f"標案異動 刪除{removed}個 新增{added}個 (總數{total}個 學校運動{recommended}個)\n"
            f"{dt_str} 發布完成\n"
            f"🔗 <a href='https://report-alpha-two.vercel.app/boss/tenders.html'>點此查看標案列表</a>"
        )

    send_telegram_notification(msg_text)

def run_step(name, script_path, cwd):
    """
    執行子步驟，即時輸出 stdout。
    """
    print("\n" + "="*60)
    print(f"[步驟啟動] {name}")
    print(f"指令: {PYTHON_EXE} -X utf8 {script_path}")
    print("="*60)

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    process = subprocess.Popen(
        [PYTHON_EXE, "-X", "utf8", script_path],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        bufsize=1
    )

    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            print(f" | {line.strip()}")

    rc = process.poll()
    if rc == 0:
        print(f"\n✅ {name} 執行成功！")
        return True, rc
    else:
        print(f"\n❌ {name} 執行失敗，退出碼: {rc}")
        return False, rc

def run_git_push(repo_dir):
    """
    執行 Git add, commit, push 操作。
    """
    print("\n" + "="*60)
    print(f"[步驟啟動] 3. Git 同步與發布至 GitHub Pages")
    print(f"Git 倉庫目錄: {repo_dir}")
    print("="*60)

    try:
        # 1. git add .
        print("[Git] git add .")
        subprocess.run(["git", "-C", repo_dir, "add", "."], check=True)

        # 2. 檢查是否有變更需要 commit
        res = subprocess.run(
            ["git", "-C", repo_dir, "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        if not res.stdout.strip():
            print("[Git] 偵測無任何變更，跳過 Commit 與 Push。")
            return True

        # 3. git commit
        commit_msg = f"Auto-update daily tenders: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        print(f"[Git] git commit -m \"{commit_msg}\"")
        subprocess.run(["git", "-C", repo_dir, "commit", "-m", commit_msg], check=True)

        # 3.5. git pull --rebase origin main (防止與遠端其他提交衝突導致 non-fast-forward 失敗)
        print("[Git] git pull --rebase origin main")
        subprocess.run(["git", "-C", repo_dir, "pull", "--rebase", "origin", "main"], check=True)

        # 4. git push origin main
        print("[Git] git push origin main")
        subprocess.run(["git", "-C", repo_dir, "push", "origin", "main"], check=True)

        print("\n✅ Git 同步成功！網頁已上傳發布至 GitHub Pages。")
        return True
    except Exception as e:
        print(f"\n❌ Git 同步失敗: {e}")
        return False

def main():
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print("==================================================")
    print(f"🚀 啟動 標案自動化收尋C專案 全流程管道 (Pipeline Master)")
    print(f"   執行時間：{now_str}")
    print(f"   使用解譯器：{PYTHON_EXE}")
    print("==================================================")

    # 1. 步驟 1：PCC 爬網與寫入 Google Sheets
    ok, rc = run_step("1. PCC 標案爬網與寫入 Google Sheets",
                      SCRAPER_SCRIPT,
                      SCRIPT_DIR)
    if not ok:
        if rc == EXIT_NO_DATA:
            print("\n[跳過] 今日查無符合條件之標案（或無新增標案），管道優雅退出。")
            send_formatted_telegram_report(is_success=True)
            sys.exit(0)
        elif rc == EXIT_NO_CHANGES:
            print("\n[跳過] 下午比對偵測無 any 案件異動，管道以 Exit Code 3 優雅退出。")
            send_formatted_telegram_report(is_success=True)
            sys.exit(EXIT_NO_CHANGES)
        else:
            print("\n[中斷] 步驟 1 發生錯誤，終止管道運作。")
            send_formatted_telegram_report(is_success=False, error_msg=f"步驟「1. PCC 爬網」失敗，退出碼：{rc}")
            sys.exit(EXIT_FAILURE)

    # 2. 步驟 2：讀取 Google Sheets → 產生網頁檔案
    ok, rc = run_step("2. Google 試算表讀取與 HTML 網頁生成",
                      SCREENSHOT_SCRIPT,
                      SCRIPT_DIR)
    if not ok:
        print("\n[中斷] 步驟 2 失敗，終止管道運作。")
        send_formatted_telegram_report(is_success=False, error_msg=f"步驟「2. 網頁生成與截圖」失敗，退出碼：{rc}")
        sys.exit(EXIT_FAILURE)

    # 3. 步驟 3：Git 同步與發布
    GIT_REPO_DIR = r"E:\01.AI\Antigravity\report"
    ok = run_git_push(GIT_REPO_DIR)
    if not ok:
        print("\n[中斷] 步驟 3 Git 同步失敗，終止管道運作。")
        send_formatted_telegram_report(is_success=False, error_msg="步驟「3. Git 同步與發布」失敗。")
        sys.exit(EXIT_FAILURE)

    print("\n" + "==================================================")
    print("🎉 標案自動化收尋C專案 全流程管道運作完畢！")
    print("==================================================")

    # 成功發布通知
    send_formatted_telegram_report(is_success=True)
if __name__ == '__main__':
    main()
