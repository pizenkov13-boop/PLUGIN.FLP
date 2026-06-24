# Deploy PLG Cloud API to Fly.io
# Usage:  scripts\deploy_cloud.ps1
# Prereq: flyctl auth login  (once)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Get-Fly {
    if (Get-Command flyctl -ErrorAction SilentlyContinue) { return "flyctl" }
    if (Get-Command fly -ErrorAction SilentlyContinue) { return "fly" }
    throw "flyctl not found. Run: winget install Fly-io.flyctl"
}

$Fly = Get-Fly

Write-Host "=== PLG Cloud deploy (Fly.io) ===" -ForegroundColor Cyan

& $Fly auth whoami 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Log in to Fly.io (browser will open)..." -ForegroundColor Yellow
    & $Fly auth login
}

$envFile = Join-Path $Root "cloud\.env"
if (-not (Test-Path $envFile)) {
    throw "Missing cloud\.env - copy cloud\.env.example and fill Supabase + GEMINI keys."
}

function Read-DotEnv([string]$path) {
    $map = @{}
    Get-Content $path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        if ($line -match "^([^=]+)=(.*)$") {
            $map[$Matches[1].Trim()] = $Matches[2].Trim()
        }
    }
    return $map
}

$env = Read-DotEnv $envFile
$app = "plg-api"

# Ensure Fly app exists
$apps = & $Fly apps list --json 2>$null | ConvertFrom-Json
$exists = $apps | Where-Object { $_.Name -eq $app }
if (-not $exists) {
    Write-Host "Creating Fly app '$app'..." -ForegroundColor Yellow
    & $Fly apps create $app --org personal 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $Fly launch --config cloud/fly.toml --no-deploy --yes
    }
}

# Build secrets list from cloud/.env
$secretKeys = @(
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_SECRET_KEY",
    "SUPABASE_JWKS_URL",
    "SUPABASE_JWT_SECRET",
    "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY",
    "YOOKASSA_SHOP_ID",
    "YOOKASSA_SECRET_KEY",
    "REDIS_URL",
    "UPSTASH_REDIS_URL",
    "SENTRY_DSN",
    "RESEND_API_KEY",
    "TURNSTILE_SITE_KEY",
    "TURNSTILE_SECRET_KEY",
    "PLG_ADMIN_SECRET"
)

$toSet = @{}
foreach ($key in $secretKeys) {
    if ($env.ContainsKey($key) -and $env[$key]) {
        $toSet[$key] = $env[$key]
    }
}

# Alias service key name
if (-not $toSet["SUPABASE_SERVICE_KEY"] -and $env["SUPABASE_SECRET_KEY"]) {
    $toSet["SUPABASE_SERVICE_KEY"] = $env["SUPABASE_SECRET_KEY"]
}

if (-not $toSet["SUPABASE_URL"]) {
    throw "SUPABASE_URL missing in cloud\.env"
}
if (-not $toSet["SUPABASE_SERVICE_KEY"]) {
    throw "SUPABASE_SERVICE_KEY (or SUPABASE_SECRET_KEY) missing in cloud\.env"
}
if (-not $toSet["GEMINI_API_KEY"]) {
    throw "GEMINI_API_KEY missing in cloud\.env"
}

# Production defaults
$toSet["PLG_ENV"] = "production"
$toSet["PLG_CAPTCHA_PROVIDER"] = if ($env["PLG_CAPTCHA_PROVIDER"]) { $env["PLG_CAPTCHA_PROVIDER"] } else { "none" }
$toSet["PLG_INVITE_ONLY"] = if ($env["PLG_INVITE_ONLY"]) { $env["PLG_INVITE_ONLY"] } else { "false" }
$toSet["PLG_REQUIRE_DEVICE_BINDING"] = "true"

if (-not $toSet["PLG_ADMIN_SECRET"]) {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $toSet["PLG_ADMIN_SECRET"] = [Convert]::ToBase64String($bytes)
    Write-Host "Generated PLG_ADMIN_SECRET (save it somewhere safe)" -ForegroundColor Yellow
}

Write-Host "Setting Fly secrets..." -ForegroundColor Cyan
$secretsFile = Join-Path $env:TEMP "plg-fly-secrets.env"
$lines = $toSet.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }
$lines | Set-Content -Path $secretsFile -Encoding utf8
Get-Content $secretsFile | & $Fly secrets import --app $app
Remove-Item $secretsFile -Force -ErrorAction SilentlyContinue

Write-Host "Deploying..." -ForegroundColor Cyan
& $Fly deploy --config cloud/fly.toml --app $app

$hostname = "$app.fly.dev"
Write-Host ""
Write-Host "=== Deployed ===" -ForegroundColor Green
Write-Host "Health:  https://$hostname/health"
Write-Host "Status:  https://$hostname/v1/status"
Write-Host ""
Write-Host "Next (manual):" -ForegroundColor Yellow
Write-Host "  1. Cloudflare: api.pluginflp.app CNAME -> $hostname"
Write-Host "  2. Update .env.release: PLG_CLOUD_URL=https://api.pluginflp.app"
Write-Host "  3. YooKassa webhook: https://api.pluginflp.app/v1/billing/webhooks/yookassa"
