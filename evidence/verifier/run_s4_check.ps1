# Run one verifier S4-C* check (boot stage-4 + targeted pytest, or static delivery).
param(
    [Parameter(Mandatory = $true)]
    [string]$Check
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$rev = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { '10d2be5fa9c6' }

function Invoke-Boot {
    $boot = & $py scripts/lever.py boot --stage 4 --rev $rev 2>&1 | Out-String
    if ($boot -notmatch 'BASE_URL=(\S+)') { throw "no BASE_URL in boot output: $boot" }
    $env:BASE_URL = $Matches[1]
}

function Invoke-PytestNodes {
    param([string[]]$Nodes)
    & $py -m pytest -q -p no:cacheprovider @Nodes
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Check) {
    'S4-C1' {
        Invoke-PytestNodes @('verify/stage-4/test_s4_delivery.py::test_s4_c1_prior_stages_and_ten_idempotent_writes')
    }
    'S4-C27' {
        Invoke-PytestNodes @('verify/stage-4/test_s4_delivery.py::test_s4_c27_stage4_delivery_artifacts')
        & $py scripts/lever.py checks --suite official --stage 4 --rev $rev --isolated
        exit $LASTEXITCODE
    }
    'S4-C28' {
        Invoke-Boot
        try {
            Invoke-PytestNodes @('verify/stage-4/test_s4_regression.py::test_s4_c28_stage123_ui_on_stage4_build')
        }
        finally {
            & $py scripts/lever.py stop | Out-Null
        }
    }
    'S4-OFFICIAL' {
        & $py scripts/lever.py checks --suite official --stage 4 --rev $rev --isolated
        exit $LASTEXITCODE
    }
    default {
        Invoke-Boot
        try {
            switch ($Check) {
                'S4-C2' { Invoke-PytestNodes @('verify/stage-4/test_s4_refunds.py::test_s4_c2_refund_requires_idempotency_and_amount') }
                'S4-C3' { Invoke-PytestNodes @('verify/stage-4/test_s4_refunds.py::test_s4_c3_refund_receiver_only_and_unknown_payment') }
                'S4-C4' { Invoke-PytestNodes @('verify/stage-4/test_s4_refunds.py::test_s4_c4_refund_target_rules_and_refund_of_refund') }
                'S4-C5' { Invoke-PytestNodes @('verify/stage-4/test_s4_refunds.py::test_s4_c5_refund_invalid_amount') }
                'S4-C6' { Invoke-PytestNodes @('verify/stage-4/test_s4_refunds.py::test_s4_c6_refund_exceeds_corrected_payment') }
                'S4-C7' { Invoke-PytestNodes @('verify/stage-4/test_s4_refunds.py::test_s4_c7_refund_payment_shape_and_non_refund_null_refund_of') }
                'S4-C8' { Invoke-PytestNodes @('verify/stage-4/test_s4_refunds.py::test_s4_c8_refund_idempotent_replay') }
                'S4-C9' { Invoke-PytestNodes @('verify/stage-4/test_s4_refunds.py::test_s4_c9_refund_insufficient_available_funds') }
                'S4-C10' { Invoke-PytestNodes @('verify/stage-4/test_s4_refunds.py::test_s4_c10_refund_does_not_reopen_request_or_hold') }
                'S4-C11' { Invoke-PytestNodes @('verify/stage-4/test_s4_corrections.py::test_s4_c11_capture_and_refund_payments_immutable') }
                'S4-C12' { Invoke-PytestNodes @('verify/stage-4/test_s4_corrections.py::test_s4_c12_correction_below_refunded_amount') }
                'S4-C13' {
                    Invoke-PytestNodes @(
                        'verify/stage-4/test_s4_batches.py::test_s4_c13_batch_auth_like_settlements',
                        'verify/stage-4/test_s4_spec_part2.py::test_s4_correction_batches_unauthenticated_401'
                    )
                }
                'S4-C14' { Invoke-PytestNodes @('verify/stage-4/test_s4_batches.py::test_s4_c14_batch_body_validation') }
                'S4-C15' { Invoke-PytestNodes @('verify/stage-4/test_s4_batches.py::test_s4_c15_batch_item_not_found_and_stale') }
                'S4-C16' { Invoke-PytestNodes @('verify/stage-4/test_s4_batches.py::test_s4_c16_batch_scope_immutable_targets') }
                'S4-C17' { Invoke-PytestNodes @('verify/stage-4/test_s4_batches.py::test_s4_c17_incomplete_settlement_batch') }
                'S4-C18' {
                    Invoke-PytestNodes @(
                        'verify/stage-4/test_s4_batches.py::test_s4_c18_settlement_effective_instant_mismatch',
                        'verify/stage-4/test_s4_spec_part2.py::test_s4_batch_settlement_same_instant_different_offset_spelling'
                    )
                }
                'S4-C19' { Invoke-PytestNodes @('verify/stage-4/test_s4_batches.py::test_s4_c19_single_correction_still_available_and_unknown_fields_ignored') }
                'S4-C20' {
                    Invoke-PytestNodes @(
                        'verify/stage-4/test_s4_batches.py::test_s4_c20_batch_rejected_leaves_state_unchanged',
                        'verify/stage-4/test_s4_spec_part2.py::test_s4_batch_precedence_item_404_before_incomplete_settlement'
                    )
                }
                'S4-C21' {
                    Invoke-PytestNodes @(
                        'verify/stage-4/test_s4_batches.py::test_s4_c21_batch_success_shape',
                        'verify/stage-4/test_s4_spec_part2.py::test_s4_batch_recorded_at_strictly_after_member_prior'
                    )
                }
                'S4-C22' {
                    Invoke-PytestNodes @(
                        'verify/stage-4/test_s4_batches.py::test_s4_c22_batch_idempotent_replay',
                        'verify/stage-4/test_s4_spec_part2.py::test_s4_batch_snapshot_frozen_and_statement_updates',
                        'verify/stage-4/test_s4_spec_part2.py::test_s4_batch_does_not_mutate_idempotent_payment_replay'
                    )
                }
                'S4-C23' { Invoke-PytestNodes @('verify/stage-4/test_s4_batches.py::test_s4_c23_batch_future_effective_rejected') }
                'S4-C24' { Invoke-PytestNodes @('verify/stage-4/test_s4_misc.py::test_s4_c24_settlement_member_refund_keeps_membership') }
                'S4-C25' { Invoke-PytestNodes @('verify/stage-4/test_s4_misc.py::test_s4_c25_concurrent_corrections_same_revision') }
                'S4-C26' { Invoke-PytestNodes @('verify/stage-4/test_s4_misc.py::test_s4_c26_import_stage3_export_retains_state') }
                default { throw "unknown check $Check" }
            }
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
        finally {
            & $py scripts/lever.py stop | Out-Null
        }
    }
}
exit 0
