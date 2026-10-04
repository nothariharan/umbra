Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$checks = @(
  @{ id='S3-C1'; req='S3-R1'; text='prior stage requirements continue on stage-3 build' },
  @{ id='S3-C2'; req='S3-R2'; text='created_at with offset on payment-returning endpoints' },
  @{ id='S3-C3'; req='S3-R3'; text='activity ordered by created_at' },
  @{ id='S3-C4'; req='S3-R4'; text='future seeded created_at rejected on reset' },
  @{ id='S3-C5'; req='S3-R5'; text='seeded payments preserve fixture balances' },
  @{ id='S3-C6'; req='S3-R6'; text='GET /me as_of validation' },
  @{ id='S3-C7'; req='S3-R7'; text='as_of balance edges and inclusion' },
  @{ id='S3-C8'; req='S3-R8'; text='as_of echo' },
  @{ id='S3-C9'; req='S3-R9'; text='statement params and defaults' },
  @{ id='S3-C10'; req='S3-R10'; text='statement entry shape and ordering' },
  @{ id='S3-C11'; req='S3-R11'; text='opening/closing reconcile with deltas' },
  @{ id='S3-C12'; req='S3-R12'; text='statement pagination preserves balances' },
  @{ id='S3-C13'; req='S3-R13'; text='statement party visibility' },
  @{ id='S3-C14'; req='S3-R14'; text='revision 1 effective/recorded times' },
  @{ id='S3-C15'; req='S3-R15'; text='opening balances unchanged by corrections' },
  @{ id='S3-C16'; req='S3-R16'; text='correction auth validation and errors' },
  @{ id='S3-C17'; req='S3-R17'; text='correction wallet delta failures' },
  @{ id='S3-C18'; req='S3-R18'; text='correction idempotency and stale revision' },
  @{ id='S3-C19'; req='S3-R19'; text='activity original amount; revisions read ACL' },
  @{ id='S3-C20'; req='S3-R20'; text='known_at selection and echo' },
  @{ id='S3-C21'; req='S3-R21'; text='corrected statement ordering and zero revisions' },
  @{ id='S3-C22'; req='S3-R22'; text='statement snapshot token paging rules' },
  @{ id='S3-C23'; req='S3-R23'; text='snapshot stability under concurrent writes' },
  @{ id='S3-C24'; req='S3-R24'; text='settlement member immutable' },
  @{ id='S3-C25'; req='S3-R25'; text='capture correction immutable' },
  @{ id='S3-C26'; req='S3-R26'; text='historical me hold fields' },
  @{ id='S3-C27'; req='S3-R27'; text='authorization closed_at exposure' },
  @{ id='S3-C28'; req='S3-R28'; text='statement lists payments only' },
  @{ id='S3-C29'; req='S3-R29'; text='stage-3 delivery artifacts' },
  @{ id='S3-C30'; req='S3-R30'; text='stage 1-2 UI regression on stage 3' }
)
foreach ($c in $checks) {
  & $py scripts/record.py check --seat verifier --id $c.id --req $c.req --text $c.text
}
