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

    Invoke-Cdp $socket "Runtime.enable" | Out-Null
    Invoke-Cdp $socket "Runtime.evaluate" @{
        expression = 'document.querySelector("[data-game=operation-check-2]").click(); true'
        returnByValue = $true
    } | Out-Null

    $lastState = $null
    $inputReleased = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 500
        $expression = @'
(() => {
  const frame = document.querySelector('#game-frame');
  if (!frame) return JSON.stringify({ stage: 'missing-frame' });
  try {
    const win = frame.contentWindow;
    const doc = frame.contentDocument;
    const bodyHeight = doc.body ? doc.body.scrollHeight : 0;
    return JSON.stringify({
      stage: 'frame',
      src: frame.getAttribute('src'),
      title: doc.title,
      innerHeight: win.innerHeight,
      scrollHeight: Math.max(doc.documentElement.scrollHeight, bodyHeight),
      hasScreen: Boolean(doc.querySelector('#pyxel-screen')),
      hasCanvas: Boolean(doc.querySelector('#canvas')),
      canStart: typeof win.pyxelContext?.resolveInput === 'function',
      initialized: Boolean(win.pyxelContext?.initialized),
      fatal: Boolean(win.pyxelContext?.hasFatalError)
    });
  } catch (error) {
    return JSON.stringify({ stage: 'frame-error', error: String(error) });
  }
})()
'@
        $response = Invoke-Cdp $socket "Runtime.evaluate" @{
            expression = $expression
            returnByValue = $true
        }
        $lastState = $response.result.result.value | ConvertFrom-Json

        if ($lastState.fatal) { throw "Pyxel reported a fatal error" }
        if ($lastState.canStart -and -not $inputReleased) {
            Invoke-Cdp $socket "Runtime.evaluate" @{
                expression = "document.querySelector('#game-frame').contentWindow.pyxelContext.resolveInput(); true"
                returnByValue = $true
            } | Out-Null
            $inputReleased = $true
        }
        if ($lastState.initialized -and $lastState.hasCanvas) {
            if ($lastState.scrollHeight -gt ($lastState.innerHeight + 1)) {
                throw "Operation page scrolls: $($lastState.scrollHeight) > $($lastState.innerHeight)"
            }
            Write-Host ($lastState | ConvertTo-Json -Compress)
            exit 0
        }
    }

    throw "Timed out waiting for Pyxel initialization. Last state: $($lastState | ConvertTo-Json -Compress)"
} finally {
    if ($null -ne $socket) { $socket.Dispose() }
    if ($null -ne $app -and -not $app.HasExited) { $app.Kill() }
}
