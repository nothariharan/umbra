# Run one verifier S3-C* check at pinned SUBMIT rev (boot + targeted pytest, or static delivery / lever).
param(
    [Parameter(Mandatory = $true)]
    [string]$Check
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$rev = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { '475ca690ab88' }

function Invoke-Boot {
    $boot = & $py scripts/lever.py boot --stage 3 --rev $rev 2>&1 | Out-String
    if ($boot -notmatch 'BASE_URL=(\S+)') { throw "no BASE_URL in boot output: $boot" }
    $env:BASE_URL = $Matches[1]
}

function Invoke-PytestNodes {
    param([string[]]$Nodes)
    & $py -m pytest -q -p no:cacheprovider @Nodes
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Check) {
    'S3-C1' {
        Invoke-PytestNodes @('verify/stage-3/test_s3_delivery.py::test_s3_c1_prior_stages_continue')
    }
    'S3-C29' {
        Invoke-PytestNodes @('verify/stage-3/test_s3_delivery.py::test_s3_c29_stage3_delivery_artifacts')
    }
    'S3-C30' {
        Invoke-Boot
        try {
            Invoke-PytestNodes @('verify/stage-3/test_s3_regression.py::test_s3_c30_stage12_ui_checks_on_stage3_build')
        }
        finally {
            & $py scripts/lever.py stop | Out-Null
        }
    }
    'S3-OFFICIAL' {
        & $py scripts/lever.py checks --suite official --stage 3 --rev $rev --isolated
        exit $LASTEXITCODE
    }
    default {
        Invoke-Boot
        try {
            switch ($Check) {
                'S3-C2' { Invoke-PytestNodes @('verify/stage-3/test_s3_timestamps.py::test_s3_c2_created_at_on_payment_endpoints') }
                'S3-C3' { Invoke-PytestNodes @('verify/stage-3/test_s3_timestamps.py::test_s3_c3_activity_ordered_by_created_at') }
                'S3-C4' { Invoke-PytestNodes @('verify/stage-3/test_s3_timestamps.py::test_s3_c4_future_seeded_created_at_rejected') }
                'S3-C5' { Invoke-PytestNodes @('verify/stage-3/test_s3_timestamps.py::test_s3_c5_seeded_payments_preserve_balances') }
                'S3-C6' { Invoke-PytestNodes @('verify/stage-3/test_s3_me_statement.py::test_s3_c6_invalid_as_of_validation_failed') }
                'S3-C7' { Invoke-PytestNodes @('verify/stage-3/test_s3_me_statement.py::test_s3_c7_as_of_balance_edges') }
                'S3-C8' { Invoke-PytestNodes @('verify/stage-3/test_s3_me_statement.py::test_s3_c8_as_of_echo') }
                'S3-C9' { Invoke-PytestNodes @('verify/stage-3/test_s3_me_statement.py::test_s3_c9_statement_defaults_and_window') }
                'S3-C10' { Invoke-PytestNodes @('verify/stage-3/test_s3_me_statement.py::test_s3_c10_statement_entry_shape') }
                'S3-C11' { Invoke-PytestNodes @('verify/stage-3/test_s3_me_statement.py::test_s3_c11_statement_balances_reconcile') }
                'S3-C12' { Invoke-PytestNodes @('verify/stage-3/test_s3_me_statement.py::test_s3_c12_pagination_preserves_balances') }
                'S3-C13' { Invoke-PytestNodes @('verify/stage-3/test_s3_me_statement.py::test_s3_c13_statement_party_visibility_not_activity') }
                'S3-C14' { Invoke-PytestNodes @('verify/stage-3/test_s3_corrections.py::test_s3_c14_revision_one_fields') }
                'S3-C15' { Invoke-PytestNodes @('verify/stage-3/test_s3_corrections.py::test_s3_c15_opening_balance_unchanged_after_correction') }
                'S3-C16' { Invoke-PytestNodes @('verify/stage-3/test_s3_corrections.py::test_s3_c16_correction_validation_and_forbidden') }
                'S3-C17' {
                    Invoke-PytestNodes @(
                        'verify/stage-3/test_s3_corrections.py::test_s3_c17_insufficient_funds_on_increase',
                        'verify/stage-3/test_s3_spec_part2.py::test_s3_c17_historical_overdraft_precedence',
                        'verify/stage-3/test_s3_differential.py::test_s3_differential_payments_and_corrections'
                    )
                }
                'S3-C18' { Invoke-PytestNodes @('verify/stage-3/test_s3_corrections.py::test_s3_c18_idempotency_and_stale_revision') }
                'S3-C19' {
                    Invoke-PytestNodes @(
                        'verify/stage-3/test_s3_corrections.py::test_s3_c19_activity_original_only_revisions_party_read',
                        'verify/stage-3/test_s3_spec_part2.py::test_s3_c19_revisions_shape_auth_and_public_third_party',
                        'verify/stage-3/test_s3_spec_part2.py::test_s3_c19_idempotent_payment_response_unchanged_after_correction'
                    )
                }
                'S3-C20' {
                    Invoke-PytestNodes @(
                        'verify/stage-3/test_s3_spec_part2.py::test_s3_c20_known_at_invalid_and_future',
                        'verify/stage-3/test_s3_spec_part2.py::test_s3_c20_payment_omitted_when_not_yet_known',
                        'verify/stage-3/test_s3_known_at_snapshots.py::test_s3_c20_known_at_echo_and_selection'
                    )
                }
                'S3-C21' {
                    Invoke-PytestNodes @(
                        'verify/stage-3/test_s3_spec_part2.py::test_s3_c21_statement_entry_includes_revision_times',
                        'verify/stage-3/test_s3_known_at_snapshots.py::test_s3_c21_corrected_statement_order'
                    )
                }
                'S3-C22' {
                    Invoke-PytestNodes @(
                        'verify/stage-3/test_s3_spec_part2.py::test_s3_c22_snapshot_has_more_and_unknown_token',
                        'verify/stage-3/test_s3_known_at_snapshots.py::test_s3_c22_snapshot_token_paging'
                    )
                }
                'S3-C23' {
                    Invoke-PytestNodes @(
                        'verify/stage-3/test_s3_spec_part2.py::test_s3_c23_concurrent_corrections_same_expected_revision',
                        'verify/stage-3/test_s3_known_at_snapshots.py::test_s3_c23_snapshot_stable_under_writes'
                    )
                }
                'S3-C24' { Invoke-PytestNodes @('verify/stage-3/test_s3_settlement_holds.py::test_s3_c24_settlement_member_immutable') }
                'S3-C25' { Invoke-PytestNodes @('verify/stage-3/test_s3_settlement_holds.py::test_s3_c25_capture_linked_payment_immutable') }
                'S3-C26' { Invoke-PytestNodes @('verify/stage-3/test_s3_settlement_holds.py::test_s3_c26_historical_me_hold_fields') }
                'S3-C27' {
                    Invoke-PytestNodes @(
                        'verify/stage-3/test_s3_settlement_holds.py::test_s3_c27_closed_at_on_authorization',
                        'verify/stage-3/test_s3_spec_part2.py::test_s3_c27_closed_at_set_after_void'
                    )
                }
                'S3-C28' { Invoke-PytestNodes @('verify/stage-3/test_s3_settlement_holds.py::test_s3_c28_statement_payments_only_no_auth_rows') }
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
