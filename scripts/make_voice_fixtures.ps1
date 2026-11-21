# Generate an original synthetic English WAV for voice-input verification.
# Requires Windows and an installed SAPI English voice. No network or API key.
$ErrorActionPreference = 'Stop'
$taskProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$taskAudioDirectory = Join-Path $taskProjectRoot 'evaluation\audio'
New-Item -ItemType Directory -Force -Path $taskAudioDirectory | Out-Null
$taskWavPath = Join-Path $taskAudioDirectory 'synthetic_english_deposit.wav'
$taskMetadataPath = Join-Path $taskAudioDirectory 'synthetic_english_deposit.metadata.json'
$taskSentence = 'My landlord has not returned my deposit of twelve thousand rupees. I have the receipt.'
$taskSpeaker = New-Object -ComObject SAPI.SpVoice
$taskVoiceTokens = $taskSpeaker.GetVoices()
$taskSelectedVoice = $null
for ($taskVoiceIndex = 0; $taskVoiceIndex -lt $taskVoiceTokens.Count; $taskVoiceIndex++) {
    $taskVoiceToken = $taskVoiceTokens.Item($taskVoiceIndex)
    if ($taskVoiceToken.GetDescription() -like '*David*') {
        $taskSelectedVoice = $taskVoiceToken
        break
    }
}
if ($null -eq $taskSelectedVoice) {
    for ($taskVoiceIndex = 0; $taskVoiceIndex -lt $taskVoiceTokens.Count; $taskVoiceIndex++) {
        $taskVoiceToken = $taskVoiceTokens.Item($taskVoiceIndex)
        if ($taskVoiceToken.GetDescription() -like '*English*') {
            $taskSelectedVoice = $taskVoiceToken
            break
        }
    }
}
if ($null -eq $taskSelectedVoice) {
    throw 'No installed English SAPI voice is available. No fixture was generated.'
}
$taskSpeaker.Voice = $taskSelectedVoice
$taskSpeaker.Rate = 0
$taskFileStream = New-Object -ComObject SAPI.SpFileStream
# SAPI SpeechAudioFormatType 18 = 16 kHz, 16-bit, mono PCM.
$taskFileStream.Format.Type = 18
try {
    $taskFileStream.Open($taskWavPath, 3, $false)
    $taskSpeaker.AudioOutputStream = $taskFileStream
    [void]$taskSpeaker.Speak($taskSentence, 0)
} finally {
    $taskFileStream.Close()
}
$taskMetadata = [ordered]@{
    synthetic = $true
    language = 'English'
    expected_text = $taskSentence
    generator = 'Windows SAPI speech synthesis'
    voice = $taskSelectedVoice.GetDescription()
    audio_format = 'PCM WAV, 16 kHz, 16-bit, mono'
    provenance = 'Original test sentence, synthesized locally; no human recording or user case data.'
    rights_note = 'The installed voice is a Microsoft Windows component; no voice software is bundled.'
}
$taskMetadata | ConvertTo-Json | Set-Content -LiteralPath $taskMetadataPath -Encoding utf8
Write-Output ('Generated synthetic fixture: ' + $taskWavPath)
