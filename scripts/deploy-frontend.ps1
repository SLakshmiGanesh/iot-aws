[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^https://')]
  [string]$ApiUrl,
  [Parameter(Mandatory = $true)]
  [string]$BucketName,
  [Parameter(Mandatory = $true)]
  [string]$DistributionId,
  [string]$AwsProfile
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendPath = Join-Path $repoRoot "frontend"
Push-Location $frontendPath
try {
  $env:VITE_API_URL = $ApiUrl.TrimEnd("/")
  npm install
  if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
} finally {
  Remove-Item Env:VITE_API_URL -ErrorAction SilentlyContinue
  Pop-Location
}

$distPath = Join-Path $frontendPath "dist"
$profileArgs = @()
if ($AwsProfile) { $profileArgs = @("--profile", $AwsProfile) }

& aws s3 sync $distPath "s3://$BucketName/" --delete @profileArgs
if ($LASTEXITCODE -ne 0) { throw "S3 upload failed" }

& aws cloudfront create-invalidation --distribution-id $DistributionId --paths "/*" @profileArgs
if ($LASTEXITCODE -ne 0) { throw "CloudFront invalidation failed" }
Write-Host "Dashboard uploaded. CloudFront URL is available from terraform output dashboard_url."
