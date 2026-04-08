#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NDL OCR Workflow — 設定ファイル (config.py)
==========================================
このファイルを自分の環境に合わせて1回だけ編集してください。
他のスクリプト（ndl_vault_sync.py, ndl_docx_generator.py）は
ここの値を参照して動作します。

【必須】のマークがついた項目は必ず変更してください。
【任意】のマークがついた項目はデフォルトのままでも動作します。
"""

from pathlib import Path
import os

# =====================================================================
# 【必須】基本設定
# =====================================================================

# Python実行ファイルのパス
# "python" でPATHが通っていればそのままでOK。
# 通っていない場合はフルパスを指定（例: r"C:\Users\YourName\AppData\Local\Programs\Python\Python312\python.exe"）
PYTHON_BIN = "python"

# NDLOCR-Liteのインストール先（setup.ps1 で自動配置される）
NDLOCR_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "ndlocr-lite"
NDLOCR_SRC = NDLOCR_DIR / "src" / "ocr.py"

# 一時ファイル保存先（OCRの中間ファイルが保存される。自動作成される）
TEMP_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "_ndl_tmp"

# =====================================================================
# 【必須】保存先設定 — 少なくとも1つを有効にしてください
# =====================================================================

# --- Obsidian保管庫 ---
# Obsidianを使っている場合、NDL_Archivesフォルダのパスを指定
# 使わない場合は空文字列 "" のままにしてください
OBSIDIAN_NDL_PATH = ""
# 例: r"C:\Users\YourName\iCloudDrive\iCloud~md~obsidian\YourVault\NDL_Archives"
# 例: r"C:\Users\YourName\Documents\ObsidianVault\NDL_Archives"

# --- Google Drive ---
# Google Driveデスクトップ版がインストールされている場合に有効化
GDRIVE_ENABLED = True
GDRIVE_BASE_FOLDER = "NDL_Archives"  # マイドライブ直下のフォルダ名（自動作成）
# ※ gws コマンドが必要です（setup.ps1でインストール案内あり）

# --- Dropbox ---
# Dropboxを使う場合に有効化
DROPBOX_ENABLED = False
DROPBOX_PATH = ""
# 例: r"C:\Users\YourName\Dropbox\NDL_Archives"

# --- ローカルフォルダ（フォールバック） ---
# 上記すべてが無効の場合のデフォルト保存先
LOCAL_FALLBACK_PATH = Path(os.path.expanduser("~")) / "Documents" / "NDL_Archives"

# =====================================================================
# 【任意】NDL API設定 — 通常は変更不要
# =====================================================================

NDL_API_BASE  = "https://lab.ndl.go.jp/dl"
NDL_BOOK_API  = NDL_API_BASE + "/api/book/{pid}"
NDL_FULL_API  = NDL_API_BASE + "/api/book/fulltext/{pid}"
NDL_PAGE_API  = NDL_API_BASE + "/api/page/{pid}_{page}"
NDL_META_API  = "https://ndlsearch.ndl.go.jp/api/opensearch?pid={pid}"
NDL_IMG_URL   = "https://dl.ndl.go.jp/api/iiif/{pid}_{seq}/full/full/0/default.jpg"

# =====================================================================
# 【任意】DOCX生成設定
# =====================================================================

DOCX_BODY_FONT = "MS Mincho"       # 本文フォント
DOCX_HEADING_FONT = "MS Gothic"    # 見出しフォント
DOCX_BODY_SIZE = 18                # 本文フォントサイズ (pt)
DOCX_HEADING_SIZE = 22             # 見出しフォントサイズ (pt)
DOCX_LINE_SPACING = 1.5            # 行間倍率
DOCX_HEADING_COLOR = (0x00, 0x00, 0x80)  # 見出し色（RGB: 濃紺）

# =====================================================================
# 【任意】OCR補正辞書
# =====================================================================
# 旧字体→新字体の自動変換マップ。
# 仏教文献を扱う場合のデフォルトセットが入っています。
# 不要な場合は空の辞書 {} にしてください。
# 独自のパターンを追加することもできます。

AI_REPAIR_MAP = {
    # 旧字体・異体字 → 常用漢字
    "國": "国", "眞": "真", "實": "実", "來": "来",
    "敎": "教", "辨": "弁", "吿": "告", "淨": "浄",
    "佛": "仏", "如來": "如来", "信樂": "信楽",
}
