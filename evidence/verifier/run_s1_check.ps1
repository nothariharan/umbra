# Run one verifier S1-C* check at pinned SUBMIT rev (boot + targeted pytest, or static delivery tests).
param(
    [Parameter(Mandatory = $true)]
    [string]$Check
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$rev = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { '1125eee49810' }

function Invoke-Boot {
    $boot = & $py scripts/lever.py boot --stage 1 --rev $rev 2>&1 | Out-String
    if ($boot -notmatch 'BASE_URL=(\S+)') { throw "no BASE_URL in boot output: $boot" }
    $env:BASE_URL = $Matches[1]
}

function Invoke-PytestNodes {
    param([string[]]$Nodes)
    & $py -m pytest -q -p no:cacheprovider @Nodes
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Check) {
    'S1-C1' {
        Invoke-PytestNodes @('verify/stage-1/test_s1_delivery.py::test_s1_c1_stage1_has_source_dockerfile_and_run_md')
    }
    'S1-C2' {
        Invoke-PytestNodes @('verify/stage-1/test_s1_delivery.py::test_s1_c2_run_md_documents_one_build_and_start_command')
    }
    'S1-C3' {
        Invoke-PytestNodes @('verify/stage-1/test_s1_delivery.py::test_s1_c3_dockerfile_and_sources_reference_port_binding')
    }
    'S1-C32' {
        & $py scripts/lever.py checks --suite official --stage 1 --rev $rev --isolated
        exit $LASTEXITCODE
    }
    'S1-C31' {
        & $PSScriptRoot/repro_s1_c31.ps1
        exit $LASTEXITCODE
    }
    'S1-C18' {
        & $PSScriptRoot/repro_s1_c18.ps1
        exit $LASTEXITCODE
    }
    default {
        Invoke-Boot
        try {
            switch ($Check) {
                'S1-C4' { Invoke-PytestNodes @('verify/stage-1/test_s1_runtime.py::test_s1_c4_health_returns_ok_json') }
                'S1-C5' {
                    Invoke-PytestNodes @(
                        'verify/stage-1/test_s1_runtime.py::test_s1_c5_reset_replaces_state_and_supports_repeat',
                        'verify/stage-1/test_s1_runtime.py::test_s1_c5_reset_requires_no_auth'
                    )
                }
                'S1-C6' {
                    Invoke-PytestNodes @(
                        'verify/stage-1/test_s1_runtime.py::test_s1_c6_unknown_body_fields_ignored',
                        'verify/stage-1/test_s1_runtime.py::test_s1_c6_unknown_query_params_ignored',
                        'verify/stage-1/test_s1_runtime.py::test_s1_c6_created_at_has_rfc3339_offset'
                    )
                }
                'S1-C9' { & $py -m pytest -q -p no:cacheprovider verify/stage-1/test_s1_auth.py -k 'test_s1_c9_' }
                'S1-C10' { Invoke-PytestNodes @('verify/stage-1/test_s1_auth.py::test_s1_c10_export_state_does_not_store_plaintext_password') }
                'S1-C11' { Invoke-PytestNodes @('verify/stage-1/test_s1_payments.py::test_s1_c11_me_shape') }
                'S1-C12' { & $py -m pytest -q -p no:cacheprovider verify/stage-1/test_s1_payments.py -k 'test_s1_c12_' }
                'S1-C13' { & $py -m pytest -q -p no:cacheprovider verify/stage-1/test_s1_requests.py -k 'test_s1_c13_' }
                'S1-C14' { & $py -m pytest -q -p no:cacheprovider verify/stage-1/test_s1_requests.py -k 'test_s1_c14_' }
                'S1-C15' { & $py -m pytest -q -p no:cacheprovider verify/stage-1/test_s1_requests.py -k 'test_s1_c15_' }
                'S1-C16' { & $py -m pytest -q -p no:cacheprovider verify/stage-1/test_s1_requests.py -k 'test_s1_c16_' }
                'S1-C17' { & $py -m pytest -q -p no:cacheprovider verify/stage-1/test_s1_splits_activity.py -k 'test_s1_c17_' }
                'S1-C20' { Invoke-PytestNodes @('verify/stage-1/test_s1_errors_load.py::test_s1_c20_error_envelope_shape') }
                'S1-C21' {
                    Invoke-PytestNodes @(
                        'verify/stage-1/test_s1_idempotency.py::test_s1_c21_idempotency_key_length',
                        'verify/stage-1/test_s1_idempotency.py::test_s1_c21_limit_offset_ranges'
                    )
                }
                'S1-C22' { & $py -m pytest -q -p no:cacheprovider verify/stage-1/test_s1_idempotency.py -k 'test_s1_c22_' }
                'S1-C23' { & $py -m pytest -q -p no:cacheprovider verify/stage-1/test_s1_export_import.py -k 'test_s1_c23_' }
                'S1-C24' { & $py -m pytest -q -p no:cacheprovider verify/stage-1/test_s1_settlements.py -k 'test_s1_c24_' }
                'S1-C25' { Invoke-PytestNodes @('verify/stage-1/test_s1_settlements.py::test_s1_c25_non_operator_forbidden') }
                'S1-C26' { & $py -m pytest -q -p no:cacheprovider verify/stage-1/test_s1_invariants.py -k 'test_s1_c26_' }
                'S1-C27' {
                    Invoke-PytestNodes @(
                        'verify/stage-1/test_s1_errors_load.py::test_s1_c27_burst_payments_no_5xx',
                        'verify/stage-1/test_s1_errors_load.py::test_s1_c27_many_parallel_reads_no_5xx'
                    )
                }
                'S1-C28' { Invoke-PytestNodes @('verify/stage-1/test_s1_splits_activity.py::test_s1_c28_scope_endpoints_exist') }
                'S1-C29' { Invoke-PytestNodes @('verify/stage-1/test_s1_invariants.py::test_s1_c29_currency_minor_units_from_fixture') }
                'S1-C30' { Invoke-PytestNodes @('verify/stage-1/test_s1_invariants.py::test_s1_c30_handle_immutable_after_signup') }
                'S1-C33' {
                    Invoke-PytestNodes @(
                        'verify/stage-1/test_s1_spec_edges.py::test_s1_c22_concurrent_identical_idempotency_one_201',
                        'verify/stage-1/test_s1_spec_edges.py::test_s1_c22_idempotency_scoped_per_user',
                        'verify/stage-1/test_s1_spec_edges.py::test_s1_c22_claimed_key_before_field_validation',
                        'verify/stage-1/test_s1_spec_edges.py::test_s1_c22_idempotent_paths_requests_splits_settlements'
                    )
                }
                'S1-C34' {
                    Invoke-PytestNodes @(
                        'verify/stage-1/test_s1_spec_edges.py::test_s1_c14_pay_body_empty_vs_public_are_distinct',
                        'verify/stage-1/test_s1_spec_edges.py::test_s1_c17_split_caller_only_and_zero_share_request',
                        'verify/stage-1/test_s1_spec_edges.py::test_s1_c24_settlement_collective_insufficient_funds_unchanged'
                    )
                }
                'S1-C35' {
                    Invoke-PytestNodes @(
                        'verify/stage-1/test_s1_spec_edges.py::test_s1_c9_multiple_login_tokens_both_valid',
                        'verify/stage-1/test_s1_spec_edges.py::test_s1_c25_operator_cannot_see_others_private_activity_or_requests',
                        'verify/stage-1/test_s1_spec_edges.py::test_s1_c12_note_longer_than_200_rejected',
                        'verify/stage-1/test_s1_spec_edges.py::test_s1_c16_unknown_direction_or_status_422',
                        'verify/stage-1/test_s1_spec_edges.py::test_s1_c23_import_preserves_idempotency_replay'
                    )
                }
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
