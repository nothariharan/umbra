# Register S4-RC2..S4-RC28 (S4-U7 rerun successors for withdrawn S4-C2..C28).
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$full = @{
    'S4-C2'='refund requires idempotency key and amount body'; 'S4-C3'='refund receiver-only and unknown payment 404'
    'S4-C4'='refund target rules and refund-of-refund rejected'; 'S4-C5'='refund invalid amount validation_failed'
    'S4-C6'='cumulative refunds vs corrected payment refund_exceeds_payment'; 'S4-C7'='refund payment shape and non-refund refund_of null'
    'S4-C8'='refund idempotent replay returns original body'; 'S4-C9'='refund insufficient available funds 409'
    'S4-C10'='refund does not reopen request or authorization'; 'S4-C11'='capture and refund payments immutable under correction'
    'S4-C12'='correction below refunded total refund_exceeds_payment'; 'S4-C13'='correction batch auth matches settlements'
    'S4-C14'='batch body validation distinct payment_ids'; 'S4-C15'='batch item not found 404 and stale revision 409'
    'S4-C16'='batch scope immutable capture and refund targets'; 'S4-C17'='incomplete settlement batch rejected'
    'S4-C18'='settlement members share effective instant'; 'S4-C19'='single correction still available; unknown batch fields ignored'
    'S4-C20'='rejected batch leaves state unchanged'; 'S4-C21'='successful batch shape and recorded_at ordering'
    'S4-C22'='batch idempotent replay and snapshot rules'; 'S4-C23'='batch future effective time rejected'
    'S4-C24'='settlement member refund keeps membership'; 'S4-C25'='concurrent corrections same revision exclusive'
    'S4-C26'='import stage-3 export retains state on stage-4'; 'S4-C27'='stage-4 delivery artifacts and official isolated regression'
    'S4-C28'='stage 1-2 UI pytest regression on stage-4 build'
}
foreach ($n in 2..28) {
    $base = "S4-C$n"
    $cid = "S4-RC$n"
    $rid = "S4-R$n"
    & $py scripts/record.py check --seat verifier --id $cid --req $rid --text "S4-U7 rerun: $($full[$base])"
}
