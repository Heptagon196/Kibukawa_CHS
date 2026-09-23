param(
    [int]$Port = 9333,
    [int]$TimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"

function Invoke-Cdp {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [string]$Method,
        [hashtable]$Params = @{}
    )

    $script:cdpId += 1
    $id = $script:cdpId
    $payload = @{ id = $id; method = $Method; params = $Params } | ConvertTo-Json -Compress -Depth 12
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $segment = [System.ArraySegment[byte]]::new($bytes)
    $Socket.SendAsync(
        $segment,
        [System.Net.WebSockets.WebSocketMessageType]::Text,
        $true,
        [System.Threading.CancellationToken]::None
    ).GetAwaiter().GetResult()

    while ($true) {
        $stream = [System.IO.MemoryStream]::new()
        do {
            $buffer = [byte[]]::new(65536)
            $receiveSegment = [System.ArraySegment[byte]]::new($buffer)
            $result = $Socket.ReceiveAsync(
                $receiveSegment,
                [System.Threading.CancellationToken]::None
            ).GetAwaiter().GetResult()
            if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
                throw "DevTools WebSocket closed unexpectedly"
            }
            $stream.Write($buffer, 0, $result.Count)
        } while (-not $result.EndOfMessage)

        $message = [System.Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
        if ($message.id -eq $id) {
            if ($message.error) {
                throw "CDP $Method failed: $($message.error.message)"
            }
            return $message
        }
    }
}

$desktopRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stageRoot = Join-Path $desktopRoot "portable\Kibukawa-Web-Spinoffs-CHS-portable"
$exePath = Join-Path $stageRoot "Kibukawa-Web-Spinoffs-CHS.exe"
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "Portable executable not found: $exePath"
}

$processInfo = [System.Diagnostics.ProcessStartInfo]::new($exePath)
$processInfo.WorkingDirectory = $stageRoot
$processInfo.UseShellExecute = $false
$processInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$processInfo.Environment["WEBVIEW2_USER_DATA_FOLDER"] = Join-Path $desktopRoot "reports\birthday-smoke-profile"
$processInfo.Environment["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--remote-debugging-port=$Port"
$app = [System.Diagnostics.Process]::Start($processInfo)
$socket = $null

try {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $target = $null
    while ([DateTime]::UtcNow -lt $deadline -and $null -eq $target) {
        try {
            $targets = Invoke-RestMethod "http://127.0.0.1:$Port/json/list"
            $target = $targets | Where-Object { $_.type -eq "page" } | Select-Object -First 1
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if ($null -eq $target) { throw "Timed out waiting for WebView2 DevTools" }

    $socket = [System.Net.WebSockets.ClientWebSocket]::new()
    $socket.ConnectAsync(
        [Uri]$target.webSocketDebuggerUrl,
        [System.Threading.CancellationToken]::None
    ).GetAwaiter().GetResult() | Out-Null

    Start-Sleep -Seconds 2
    $response = Invoke-Cdp $socket "Runtime.evaluate" @{
        expression = [IO.File]::ReadAllText((Join-Path $desktopRoot 'scripts/birthday-portrait-repro.js'))
        awaitPromise = $true
        returnByValue = $true
    }
    if ($response.result.exceptionDetails) { throw ($response.result.exceptionDetails | ConvertTo-Json -Depth 8) }
    $state=$response.result.result.value
    Write-Host ($state | ConvertTo-Json -Compress -Depth 5)

    if (-not $state.ok) { throw 'Portrait layers lost alignment during camera animation' }
    $shot = Invoke-Cdp $socket "Page.captureScreenshot" @{ format = "png" }
    $reportRoot = Join-Path $desktopRoot "reports"
    New-Item -ItemType Directory -Force -Path $reportRoot | Out-Null
    [IO.File]::WriteAllBytes((Join-Path $reportRoot "birthday-portrait.png"), [Convert]::FromBase64String($shot.result.data))
} finally {
    if ($null -ne $socket) { $socket.Dispose() }
    if ($null -ne $app -and -not $app.HasExited) { $app.Kill() }
}
