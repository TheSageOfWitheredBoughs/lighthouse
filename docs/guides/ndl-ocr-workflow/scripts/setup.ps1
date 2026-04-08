# ============================================================
#  NDL OCR Workflow — セットアップスクリプト (Windows PowerShell)
# ============================================================
#  使い方:
#    PowerShellを開いて以下を実行:
#      Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
#      cd path\to\scripts
#      .\setup.ps1
#
#  このスクリプトが行うこと:
#    1. Python環境の確認
#    2. NDLOCR-Lite リポジトリのクローン
#    3. Python依存パッケージのインストール
#    4. 動作確認テスト
# ============================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  NDL OCR Workflow - Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Python確認 ---
Write-Host "[1/4] Python..." -ForegroundColor Yellow -NoNewline
try {
    $pyVer = python --version 2>&1
    Write-Host " OK ($pyVer)" -ForegroundColor Green
} catch {
    Write-Host " NOT FOUND" -ForegroundColor Red
    Write-Host ""
    Write-Host "Python 3.10+ required." -ForegroundColor Red
    Write-Host "Download: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# --- Step 2: Git確認 ---
Write-Host "[2/4] Git..." -ForegroundColor Yellow -NoNewline
try {
    $gitVer = git --version 2>&1
    Write-Host " OK ($gitVer)" -ForegroundColor Green
} catch {
    Write-Host " NOT FOUND" -ForegroundColor Red
    Write-Host "Git required: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

# --- Step 3: NDLOCR-Lite クローン ---
$ndlocrDir = Join-Path $ScriptDir "ndlocr-lite"
Write-Host "[3/4] NDLOCR-Lite..." -ForegroundColor Yellow -NoNewline

if (Test-Path $ndlocrDir) {
    Write-Host " Already exists (skipping clone)" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "       Cloning ndl-lab/ndlocr-lite..." -ForegroundColor Gray
    git clone https://github.com/ndl-lab/ndlocr-lite.git $ndlocrDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Clone failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "       Clone complete." -ForegroundColor Green
}

# --- Step 4: Dependencies ---
Write-Host "[4/4] Installing dependencies..." -ForegroundColor Yellow

# Workflow dependencies
Write-Host "       [a] Workflow requirements..." -ForegroundColor Gray
pip install -r (Join-Path $ScriptDir "requirements.txt") --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "  pip install failed for requirements.txt" -ForegroundColor Red
    exit 1
}

# NDLOCR-Lite dependencies
$ndlReq = Join-Path $ndlocrDir "requirements.txt"
if (Test-Path $ndlReq) {
    Write-Host "       [b] NDLOCR-Lite requirements..." -ForegroundColor Gray
    pip install -r $ndlReq --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  pip install failed for ndlocr-lite" -ForegroundColor Red
        exit 1
    }
}

Write-Host "       Dependencies installed." -ForegroundColor Green

# --- Complete ---
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit config.py (set your paths)" -ForegroundColor White
Write-Host "  2. Test: python ndl_vault_sync.py --pid 3048008 --pages 24" -ForegroundColor White
Write-Host "  3. Copy workflows/ndl.md to .agents/workflows/ (Antigravity)" -ForegroundColor White
Write-Host ""
