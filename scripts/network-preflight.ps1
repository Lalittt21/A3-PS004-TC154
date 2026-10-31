param([string]$Adapter='Wi-Fi')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$ips=@(Get-NetIPAddress -InterfaceAlias $Adapter -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '169.254.*'})
if ($ips.Count -ne 1) { throw 'Select an adapter with exactly one LAN IPv4 address.' }
$text=Get-Content -Raw (Join-Path $root 'client/esp32/include/config.h')
$match=[regex]::Match($text,'#define TG_GATEWAY_IP "([^"]+)"')
if (-not $match.Success) { throw 'Missing gateway IP in local firmware configuration' }
$wslAddress=(wsl -d Ubuntu -- hostname -I).Trim()
if ($LASTEXITCODE -ne 0) { throw 'WSL is unavailable' }
Write-Output "Laptop IPv4: $($ips[0].IPAddress)"
Write-Output "Firmware source gateway IPv4: $($match.Groups[1].Value)"
Write-Output "WSL IPv4: $wslAddress"
if ($ips[0].IPAddress -ne $match.Groups[1].Value) {
 Write-Warning 'Gateway IP changed. Update configuration and rebuild/reflash before testing.'
}
Get-NetFirewallRule -Name TrustGate-TLS-Lab -ErrorAction SilentlyContinue | Get-NetFirewallAddressFilter | Select-Object LocalAddress,RemoteAddress
netsh interface portproxy show v4tov4
Write-Output 'Compare the firewall RemoteAddress with the latest ESP32 serial WIFI connected IP. This checks source configuration, not firmware already flashed on the board.'
