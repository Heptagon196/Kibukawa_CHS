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
        expression = @'
(async () => {
 for(let i=0;i<100&&!document.querySelector('[data-game=birthday]');i++) await new Promise(r=>setTimeout(r,100));
 document.querySelector('[data-game=birthday]').click();
 const f = document.querySelector('#game-frame');
 for(let i=0;i<100;i++) { await new Promise(r=>setTimeout(r,100)); if(f.contentWindow.TYRANO?.kag?.menu) break; }
 const w=f.contentWindow, k=w.TYRANO.kag;
 k.config.userFace='webfont_1';
 k.variable.tf.system.backlog=['他们一定会为我准备的巧妙惊喜，感动得热泪盈眶。','（伊纲）……来了，请进。','（伊纲）……哦，什么嘛。'];
 k.menu.displayLog();
 for(let i=0;i<50;i++){await new Promise(r=>setTimeout(r,100)); if(f.contentDocument.querySelector('.log_body')) break;}
 const log=f.contentDocument.querySelector('.log_body');
 await w.document.fonts.ready;
 const font=w.getComputedStyle(log).fontFamily;
 const files=await Promise.all(['scene1.ks','scene2.ks'].map(x=>w.fetch('data/scenario/'+x).then(r=>r.text())));
 const labels=files.map(s=>s.match(/text=%text\|([^ \]]+)/)[1]);
 return {font,labels,text:log.textContent,ok:!font.startsWith('webfont_1')&&labels.every(x=>x==='交谈')};
})()
'@
        awaitPromise = $true
        returnByValue = $true
    }
    if ($response.result.exceptionDetails) { throw ($response.result.exceptionDetails | ConvertTo-Json -Depth 8) }
    $state=$response.result.result.value
    Write-Host ($state | ConvertTo-Json -Compress -Depth 5)
    if (-not $state.ok) { throw 'Birthday backlog font / choice label regression' }
    $shot = Invoke-Cdp $socket "Page.captureScreenshot" @{ format = "png" }
    $reportRoot = Join-Path $desktopRoot "reports"
    New-Item -ItemType Directory -Force -Path $reportRoot | Out-Null
    [IO.File]::WriteAllBytes((Join-Path $reportRoot "birthday-backlog.png"), [Convert]::FromBase64String($shot.result.data))
} finally {
    if ($null -ne $socket) { $socket.Dispose() }
    if ($null -ne $app -and -not $app.HasExited) { $app.Kill() }
}
