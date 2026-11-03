# 周天 / Celestial Wheel —— 本机启动脚本
# 用法：双击 start.cmd，或在本目录执行  powershell -ExecutionPolicy Bypass -File .\start.ps1
# 参数：-Port 8788（端口被占用会自动往后找）  -NoBrowser（不自动开浏览器）
[CmdletBinding()]
param(
  [int]$Port = 8788,
  [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Find-FreePort([int]$start) {
  for ($p = $start; $p -lt $start + 40; $p++) {
    $busy = $false
    try { $busy = [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) } catch { }
    if (-not $busy) { return $p }
  }
  throw "找不到空闲端口（试过 $start 起 40 个）"
}

$Port = Find-FreePort $Port
$url = "http://127.0.0.1:$Port/"

$python = Get-Command python, python3 -ErrorAction SilentlyContinue | Select-Object -First 1
$node = Get-Command node -ErrorAction SilentlyContinue | Select-Object -First 1
# 带 /api 的那套要 tianzhi-core 的 venv；有它就用 uvicorn，没有就退成纯静态站。
$venv = 'D:\Dev\tianzhi\.venv\Scripts\python.exe'

if (Test-Path $venv) {
  $exe = $venv
  $serverArgs = @('-m', 'uvicorn', 'server.app:app', '--host', '127.0.0.1', '--port', "$Port")
  $mode = 'full'
} elseif ($python) {
  $exe = $python.Source
  $serverArgs = @('-m', 'http.server', "$Port", '--bind', '127.0.0.1')
  $mode = 'static'
} elseif ($node) {
  $exe = $node.Source
  $serverArgs = @('vendor/serve.mjs', "$Port", '.')
  $mode = 'static'
} else {
  Write-Host '需要 Python 3 或 Node.js 之一来当静态服务器。' -ForegroundColor Red
  Write-Host '装一个，或者用 VS Code 的 Live Server 插件打开 index.html 也行。'
  Read-Host '按回车退出'
  exit 1
}

Write-Host ''
Write-Host '  周天 · Celestial Wheel' -ForegroundColor Yellow
Write-Host "  $url" -ForegroundColor Cyan
if ($mode -eq 'full') {
  Write-Host '  含 /api：屏幕右下角的「问璇玑」可用。' -ForegroundColor DarkGray
} else {
  Write-Host '  纯静态：右下角的璇玑面板取不到读数（要 D:\Dev\tianzhi\.venv 才有 /api）。' -ForegroundColor DarkGray
}
Write-Host '  必须走 http，双击 index.html（file://）会被浏览器的模块与 fetch 拦住。' -ForegroundColor DarkGray
Write-Host '  Ctrl+C 或关掉这个窗口即可停止。' -ForegroundColor DarkGray
Write-Host ''

if (-not $NoBrowser) {
  Start-Job -ScriptBlock { param($u) Start-Sleep -Milliseconds 900; Start-Process $u } -ArgumentList $url | Out-Null
}

& $exe @serverArgs
