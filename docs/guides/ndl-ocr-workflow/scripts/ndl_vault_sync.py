#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NDL Vault Sync - 国立国会図書館デジタルコレクション自動同期スクリプト
================================================
使い方:
    python ndl_vault_sync.py --pid 3048008
    python ndl_vault_sync.py --url https://dl.ndl.go.jp/pid/3048008
    python ndl_vault_sync.py --pid 3048008 --pages 1-10

フロー:
    1. NDL次世代デジタルライブラリーAPIでOCRテキスト存在確認
    2a. テキストあり → API経由で直接取得（高速ルート）
    2b. テキストなし → 画像DL後にNDLOCR-Liteで処理（OCRルート）
    3. AI校正（呼び出し元のAntigravityが担当）
    4. 設定された保存先へ保存
    5. Google Drive保存（OCRルートは確認後）
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
import io
import shutil

# WindowsコンソールでのUnicodeEncodeError回避
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ===== config.py の読み込み =====
# 同じディレクトリの config.py を参照
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import config
except ImportError:
    print("Error: config.py が見つかりません。")
    print("       scripts/ フォルダに config.py を配置し、設定を記入してください。")
    sys.exit(1)

# config から設定値を取得
PYTHON_BIN   = getattr(config, 'PYTHON_BIN', 'python')
NDLOCR_SRC   = str(getattr(config, 'NDLOCR_SRC', ''))
TEMP_DIR     = Path(getattr(config, 'TEMP_DIR', './_ndl_tmp'))

# 保存先
OBSIDIAN_NDL_PATH = getattr(config, 'OBSIDIAN_NDL_PATH', '')
GDRIVE_ENABLED    = getattr(config, 'GDRIVE_ENABLED', False)
GDRIVE_BASE_FOLDER = getattr(config, 'GDRIVE_BASE_FOLDER', 'NDL_Archives')
DROPBOX_ENABLED   = getattr(config, 'DROPBOX_ENABLED', False)
DROPBOX_PATH      = getattr(config, 'DROPBOX_PATH', '')
LOCAL_FALLBACK    = Path(getattr(config, 'LOCAL_FALLBACK_PATH', Path.home() / 'Documents' / 'NDL_Archives'))

# NDL API
NDL_API_BASE = getattr(config, 'NDL_API_BASE', 'https://lab.ndl.go.jp/dl')
NDL_BOOK_API = getattr(config, 'NDL_BOOK_API', NDL_API_BASE + '/api/book/{pid}')
NDL_FULL_API = getattr(config, 'NDL_FULL_API', NDL_API_BASE + '/api/book/fulltext/{pid}')
NDL_PAGE_API = getattr(config, 'NDL_PAGE_API', NDL_API_BASE + '/api/page/{pid}_{page}')
NDL_META_API = getattr(config, 'NDL_META_API', 'https://ndlsearch.ndl.go.jp/api/opensearch?pid={pid}')
NDL_IMG_URL  = getattr(config, 'NDL_IMG_URL', 'https://dl.ndl.go.jp/api/iiif/{pid}_{seq}/full/full/0/default.jpg')

# OCR補正辞書
AI_REPAIR_MAP = getattr(config, 'AI_REPAIR_MAP', {})

NDL_SUBFOLDER_PREFIX = "NDL_"


# ===== ユーティリティ =====
def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "i", "OK": "+", "WARN": "!", "ERR": "x", "ASK": "?"}.get(level, ".")
    print(f"[{ts}] [{prefix}] {msg}")

def fetch_json(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NDLVaultSync/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            content_type = r.headers.get("Content-Type", "")
            raw = r.read()
            if "json" in content_type:
                return json.loads(raw.decode("utf-8"))
            return {"_raw": raw.decode("utf-8", errors="ignore")}
    except Exception as e:
        log(f"API error: {url} -> {e}", "WARN")
        return None

def fetch_text_raw(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NDLVaultSync/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        log(f"Fetch error: {url} -> {e}", "WARN")
        return ""

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()

def extract_text_from_page_response(raw: str) -> str:
    try:
        data = json.loads(raw)
        t = data.get("contents") or data.get("text") or data.get("fulltext") or ""
        if str(t).strip():
            return str(t).strip()
        coordjson = data.get("coordjson") or data.get("coord") or ""
        if coordjson:
            if isinstance(coordjson, str):
                coords = json.loads(coordjson)
            else:
                coords = coordjson
            texts = [c.get("contenttext", "") for c in coords if c.get("contenttext")]
            return " ".join(texts).strip()
    except (json.JSONDecodeError, Exception):
        pass
    return ""

def ai_repair_text(text: str) -> str:
    for old, new in AI_REPAIR_MAP.items():
        text = text.replace(old, new)
    text = text.replace("\u3002 ", "\u3002")
    return text


# ===== NDL PID抽出 =====
def extract_pid(url_or_pid: str) -> str:
    m = re.search(r'pid/(\d+)', url_or_pid)
    if m:
        return m.group(1)
    if re.fullmatch(r'\d+', url_or_pid.strip()):
        return url_or_pid.strip()
    raise ValueError(f"PID extraction failed: {url_or_pid}")


# ===== Step 1: 書誌情報取得 =====
def get_biblio_info(pid: str) -> dict:
    log(f"Fetching bibliography (PID: {pid})")
    url = NDL_META_API.format(pid=pid)
    raw = fetch_text_raw(url)
    title = f"NDL_{pid}"
    if raw:
        item_match = re.search(r'<item[^>]*>.*?<title>(.+?)</title>', raw, re.DOTALL)
        if item_match:
            title = item_match.group(1).strip()
        else:
            all_titles = re.findall(r'<title>(.+?)</title>', raw)
            if len(all_titles) >= 2:
                title = all_titles[1].strip()
    if title and title != f"NDL_{pid}":
        log(f"Title: {title}", "OK")
    else:
        book_raw = fetch_text_raw(NDL_BOOK_API.format(pid=pid))
        if book_raw:
            try:
                bdata = json.loads(book_raw)
                title = bdata.get("title", f"NDL_{pid}")
                vol = bdata.get("volume", "")
                if vol:
                    title = f"{title} {vol}"
                log(f"Title (Book API): {title}", "OK")
            except Exception:
                pass
    return {"pid": pid, "title": title, "data": {}}


# ===== Step 2: OCRテキスト存在確認 =====
def check_ndl_text_available(pid: str, page: int = 1) -> bool:
    log("Checking NDL Digital Library for existing OCR text...")

    book_url = NDL_BOOK_API.format(pid=pid)
    log(f"  Book API: {book_url}")
    book_raw = fetch_text_raw(book_url)
    if book_raw:
        try:
            bdata = json.loads(book_raw)
            pages_data = bdata.get("page", [])
            has_text = bdata.get("hasOCR") or bdata.get("ocrAvailable") or (isinstance(pages_data, list) and len(pages_data) > 0)
            if has_text:
                log("Book API: page data found. Checking Page API...", "OK")
        except json.JSONDecodeError:
            pass

    page_id = str(page)
    page_url = NDL_PAGE_API.format(pid=pid, page=page_id)
    log(f"  Page API: {page_url}")
    page_raw = fetch_text_raw(page_url)
    if page_raw:
        extracted = extract_text_from_page_response(page_raw)
        if extracted:
            log("Page API: OCR text found (API route available)", "OK")
            return True
        else:
            log(f"  Page API response (head): {page_raw[:200]}", "WARN")

    log("No OCR text found on NDL. Switching to OCR route.", "WARN")
    return False


# ===== Step 2a: APIルート =====
def fetch_text_via_api(pid: str, pages: list) -> str:
    full_url = NDL_FULL_API.format(pid=pid)
    log(f"  Trying fulltext API: {full_url}")
    try:
        req = urllib.request.Request(full_url, headers={"User-Agent": "NDLVaultSync/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw_bytes = r.read()
            import gzip, zipfile
            try:
                full_text = gzip.decompress(raw_bytes).decode("utf-8", errors="ignore")
            except Exception:
                try:
                    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                        full_text = "\n".join(
                            zf.read(name).decode("utf-8", errors="ignore")
                            for name in zf.namelist()
                        )
                except Exception:
                    full_text = raw_bytes.decode("utf-8", errors="ignore")
            if len(full_text) > 100:
                log(f"Fulltext API: {len(full_text)} chars retrieved", "OK")
                return full_text
    except Exception as e:
        log(f"Fulltext API error: {e}", "WARN")

    log(f"Fetching page by page ({len(pages)} pages)...")
    texts = []
    for page in pages:
        page_id = str(page)
        url = NDL_PAGE_API.format(pid=pid, page=page_id)
        raw = fetch_text_raw(url)
        if not raw:
            continue
        t = extract_text_from_page_response(raw)
        if t:
            texts.append(f"--- p.{page} ---\n{t}")
        else:
            log(f"  p.{page}: no text retrieved", "WARN")
    result = "\n\n".join(texts)
    log(f"API text retrieval complete: {len(result)} chars", "OK")
    return result


# ===== Step 2b: OCRルート =====
def fetch_text_via_ocr(pid: str, pages: list) -> str:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    img_dir = TEMP_DIR / f"{pid}_imgs"
    ocr_dir = TEMP_DIR / f"{pid}_ocr"
    img_dir.mkdir(exist_ok=True)
    ocr_dir.mkdir(exist_ok=True)

    log(f"OCR route: downloading {len(pages)} page images...")
    downloaded = []
    for i, page in enumerate(pages, 1):
        page_str = str(page).zfill(7)
        img_url = NDL_IMG_URL.format(pid=pid, seq=page_str)
        img_path = img_dir / f"page_{page:04d}.jpg"
        try:
            urllib.request.urlretrieve(img_url, img_path)
            downloaded.append(img_path)
            log(f"  Downloaded: p.{page} ({i}/{len(pages)})")
        except Exception as e:
            log(f"  Download failed: p.{page} -> {e}", "WARN")

    if not downloaded:
        log("No images downloaded", "ERR")
        return ""

    log("Running NDLOCR-Lite...")
    try:
        result = subprocess.run(
            [PYTHON_BIN, NDLOCR_SRC,
             "--sourcedir", str(img_dir),
             "--output", str(ocr_dir)],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode != 0:
            log(f"NDLOCR-Lite error: {result.stderr[:300]}", "ERR")
            return ""
    except subprocess.TimeoutExpired:
        log("NDLOCR-Lite timeout (10 min)", "ERR")
        return ""

    texts = []
    for txt_file in sorted(ocr_dir.rglob("*.txt")):
        content = txt_file.read_text(encoding="utf-8", errors="ignore")
        if content.strip():
            texts.append(content.strip())
    result_text = "\n\n".join(texts)
    log(f"OCR complete: {len(result_text)} chars", "OK")
    return result_text


# ===== Step 3: 保存（Obsidian / Dropbox / ローカル） =====
def save_to_storage(pid: str, title: str, text: str, route: str, pages: list) -> Path:
    safe_title = sanitize_filename(title)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}_{safe_title}.md"
    page_range = f"{pages[0]}-{pages[-1]}" if pages else "all"

    frontmatter = f"""---
title: "{title}"
pid: "{pid}"
source: "NDL Digital Collection"
url: "https://dl.ndl.go.jp/pid/{pid}"
pages: "{page_range}"
route: "{route}"
date: "{date_str}"
tags:
  - NDL
---

"""
    content = frontmatter + text
    saved_path = None

    # Obsidian
    if OBSIDIAN_NDL_PATH:
        obs_dir = Path(OBSIDIAN_NDL_PATH)
        obs_dir.mkdir(parents=True, exist_ok=True)
        obs_path = obs_dir / filename
        obs_path.write_text(content, encoding="utf-8")
        log(f"Saved to Obsidian: {obs_path.name}", "OK")
        saved_path = obs_path

    # Dropbox
    if DROPBOX_ENABLED and DROPBOX_PATH:
        db_dir = Path(DROPBOX_PATH)
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / filename
        db_path.write_text(content, encoding="utf-8")
        log(f"Saved to Dropbox: {db_path.name}", "OK")
        saved_path = saved_path or db_path

    # ローカルフォールバック
    if not saved_path:
        LOCAL_FALLBACK.mkdir(parents=True, exist_ok=True)
        local_path = LOCAL_FALLBACK / filename
        local_path.write_text(content, encoding="utf-8")
        log(f"Saved to local: {local_path.name}", "OK")
        saved_path = local_path

    return saved_path


# ===== Step 4: Google Drive保存 =====
def save_to_gdrive(title: str, text: str, route: str) -> bool:
    if not GDRIVE_ENABLED:
        return False

    safe_title = sanitize_filename(title)
    subfolder = f"{NDL_SUBFOLDER_PREFIX}{safe_title}"
    gdrive_path = f"{GDRIVE_BASE_FOLDER}/{subfolder}"

    if route == "OCR":
        print(f"\n{'='*60}")
        print(f"[?] Google Drive save confirmation")
        print(f"    Destination: My Drive / {gdrive_path}")
        print(f"    Create new subfolder '{subfolder}'?")
        print(f"    (yes/no): ", end="", flush=True)
        answer = "yes"  # Antigravity controls this
        print(answer)
        if answer.lower() not in ("yes", "y"):
            log("Google Drive save skipped", "WARN")
            return False

    # Check if gws is available
    if not shutil.which("gws"):
        log("gws command not found. Skipping Google Drive upload.", "WARN")
        log("Install: pip install gws", "WARN")
        return False

    try:
        tmp_txt = TEMP_DIR / f"{safe_title}.txt"
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        tmp_txt.write_text(text, encoding="utf-8")

        q_str = f"name='{GDRIVE_BASE_FOLDER}' and mimeType='application/vnd.google-apps.folder'"
        params_json = json.dumps({"q": q_str})
        result = subprocess.run(
            ["gws", "drive", "files", "list", "--format", "json", "--params", params_json],
            capture_output=True, text=True, encoding="utf-8", timeout=30
        )
        if result.returncode != 0:
            log(f"Google Drive: folder search failed: {result.stderr}", "WARN")
            return False

        folders = json.loads(result.stdout)
        if not folders.get("files"):
            log(f"Google Drive: base folder '{GDRIVE_BASE_FOLDER}' not found", "WARN")
            return False

        parent_id = folders["files"][0]["id"]
        create_metadata = json.dumps({
            "name": subfolder, "parents": [parent_id],
            "mimeType": "application/vnd.google-apps.folder"
        })
        create_result = subprocess.run(
            ["gws", "drive", "files", "create", "--format", "json", "--json", create_metadata],
            capture_output=True, text=True, encoding="utf-8", timeout=30
        )
        if create_result.returncode == 0:
            sub_data = json.loads(create_result.stdout)
            sub_id = sub_data.get("id", "")
            upload_metadata = json.dumps({"name": tmp_txt.name, "parents": [sub_id]})
            subprocess.run(
                ["gws", "drive", "files", "create", "--json", upload_metadata, "--upload", str(tmp_txt)],
                timeout=60
            )
            log(f"Google Drive saved: {gdrive_path}/{tmp_txt.name}", "OK")
            return True
        else:
            log(f"Google Drive: subfolder creation failed: {create_result.stderr}", "WARN")
    except Exception as e:
        log(f"Google Drive error: {e}", "WARN")
    return False


# ===== メイン =====
def main():
    parser = argparse.ArgumentParser(description="NDL Vault Sync")
    parser.add_argument("--pid", help="NDL PID number")
    parser.add_argument("--url", help="NDL Digital Collection URL")
    parser.add_argument("--pages", help="Page range (e.g. 1-10 or 1,2,5)", default="1")
    parser.add_argument("--no-gdrive", action="store_true", help="Skip Google Drive save")
    parser.add_argument("--force-ocr", action="store_true", help="Force OCR even if API text exists")
    args = parser.parse_args()

    if not args.pid and not args.url:
        parser.error("--pid or --url is required")

    source = args.url or args.pid
    pid = extract_pid(source)

    pages = []
    if "-" in args.pages:
        s, e = args.pages.split("-")
        pages = list(range(int(s), int(e) + 1))
    elif "," in args.pages:
        pages = [int(p) for p in args.pages.split(",")]
    else:
        pages = [int(args.pages)]

    print(f"\n{'='*60}")
    print(f"  NDL Vault Sync")
    print(f"  PID: {pid} / Pages: {args.pages}")
    print(f"{'='*60}\n")

    # Step 1: Bibliography
    biblio = get_biblio_info(pid)
    title = biblio["title"]

    # Step 2: Check for existing OCR text
    if not args.force_ocr and check_ndl_text_available(pid, pages[0]):
        route = "API"
        raw_text = fetch_text_via_api(pid, pages)
    else:
        route = "OCR"
        log("Processing via OCR route (NDLOCR-Lite)")
        raw_text = fetch_text_via_ocr(pid, pages)

    if not raw_text.strip():
        log("Text retrieval failed. Aborting.", "ERR")
        sys.exit(1)

    # Apply OCR repair
    corrected_text = ai_repair_text(raw_text)

    print(f"\n--- Retrieved text (first 500 chars) ---")
    print(corrected_text[:500])
    print("---\n")

    # Step 3: Save to storage
    saved_path = save_to_storage(pid, title, corrected_text, route, pages)

    # Step 4: Google Drive
    if not args.no_gdrive:
        save_to_gdrive(title, corrected_text, route)
    else:
        log("Google Drive save skipped (--no-gdrive)", "WARN")

    print(f"\n{'='*60}")
    print(f"  Complete!")
    print(f"  Route   : {route}")
    print(f"  Saved to: {saved_path}")
    print(f"{'='*60}\n")

    # JSON output for Antigravity
    result = {
        "pid": pid, "title": title, "route": route,
        "pages": pages, "text_length": len(corrected_text),
        "saved_path": str(saved_path), "raw_text": corrected_text
    }
    print("[RESULT_JSON]")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
