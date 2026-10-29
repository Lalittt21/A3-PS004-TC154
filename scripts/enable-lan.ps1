param(
 [Parameter(Mandatory=$true)][System.Net.IPAddress]$LaptopAddress,
 [Parameter(Mandatory=$true)][System.Net.IPAddress]$WslAddress,
 [Parameter(Mandatory=$true)][System.Net.IPAddress]$BoardAddress,
 [System.Net.IPAddress]$PreviousLaptopAddress
)
$ErrorActionPreference = 'Stop'
# Run in an administrator PowerShell. Only the ESP32 may reach this lab rule.
if ($PreviousLaptopAddress) {
 netsh interface portproxy delete v4tov4 "listenaddress=$PreviousLaptopAddress" listenport=1853
}
netsh interface portproxy add v4tov4 "listenaddress=$LaptopAddress" listenport=1853 "connectaddress=$WslAddress" connectport=1853
if ($LASTEXITCODE -ne 0) { throw 'Port forwarding failed' }
if (Get-NetFirewallRule -Name TrustGate-TLS-Lab -ErrorAction SilentlyContinue) {
 Remove-NetFirewallRule -Name TrustGate-TLS-Lab
}
New-NetFirewallRule -Name TrustGate-TLS-Lab -DisplayName 'TrustGate TLS lab on local Wi-Fi' -Direction Inbound -Action Allow -Protocol TCP -LocalAddress $LaptopAddress.IPAddressToString -LocalPort 1853 -RemoteAddress $BoardAddress.IPAddressToString -Profile Any | Out-Null
netsh interface portproxy show v4tov4
