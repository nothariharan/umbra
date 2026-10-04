# Run one verifier S2-C* check at pinned SUBMIT rev (boot + targeted pytest, or static delivery / lever).
param(
    [Parameter(Mandatory = $true)]
    [string]$Check
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$rev = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { 'b013f5e17143' }

function Invoke-Boot {
    $boot = & $py scripts/lever.py boot --stage 2 --rev $rev 2>&1 | Out-String
    if ($boot -notmatch 'BASE_URL=(\S+)') { throw "no BASE_URL in boot output: $boot" }
    $env:BASE_URL = $Matches[1]
}

function Invoke-PytestNodes {
    param([string[]]$Nodes)
    & $py -m pytest -q -p no:cacheprovider @Nodes
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Check) {
    'S2-C1' {
        Invoke-PytestNodes @('verify/stage-2/test_s2_delivery.py')
    }
    'S2-C4' {
        & $PSScriptRoot/repro_s2_verifier_suite.ps1
        exit $LASTEXITCODE
    }
    'S2-C5' {
        & $PSScriptRoot/repro_s2_c5.ps1
        exit $LASTEXITCODE
    }
    'S2-C6' {
        & $PSScriptRoot/repro_s2_c6.ps1
        exit $LASTEXITCODE
    }
    'S2-C19' {
        & $PSScriptRoot/repro_s2_submit_r22_r23_r28.ps1
        exit $LASTEXITCODE
    }
    'S2-C25' {
        & $PSScriptRoot/repro_s2_c25.ps1
        exit $LASTEXITCODE
    }
    'S2-C32' {
        & $py scripts/lever.py checks --suite official --stage 2 --rev $rev --isolated
        exit $LASTEXITCODE
    }
    default {
        Invoke-Boot
        try {
            switch ($Check) {
                'S2-C2' { Invoke-PytestNodes @('verify/stage-2/test_s2_routes_negotiation.py::test_s2_c2_required_routes_respond') }
                'S2-C3' { Invoke-PytestNodes @('verify/stage-2/test_s2_routes_negotiation.py::test_s2_c3_requests_html_vs_json', 'verify/stage-2/test_s2_routes_negotiation.py::test_s2_c3_authorizations_html_vs_json') }
                'S2-C7' { Invoke-PytestNodes @('verify/stage-2/test_s2_ui_testids.py::test_s2_c4_home_wallet_and_pay_testids') }
                'S2-C8' { Invoke-PytestNodes @('verify/stage-2/test_s2_ui_testids.py::test_s2_c4_home_wallet_and_pay_testids') }
                'S2-C9' { Invoke-PytestNodes @('verify/stage-2/test_s2_ui_testids.py::test_s2_c4_home_wallet_and_pay_testids') }
                'S2-C10' { Invoke-PytestNodes @('verify/stage-2/test_s2_ui_testids.py::test_s2_c4_home_wallet_and_pay_testids') }
                'S2-C11' { Invoke-PytestNodes @('verify/stage-2/test_s2_ui_flows.py::test_s2_c11_balance_feed_refresh_after_pay') }
                'S2-C12' { Invoke-PytestNodes @('verify/stage-2/test_s2_ui_flows.py::test_s2_c12_wallet_refresh_latest_wins') }
                'S2-C13' {
                    & $PSScriptRoot/repro_s2_c6.ps1
                    exit $LASTEXITCODE
                }
                'S2-C14' { Invoke-PytestNodes @('verify/stage-2/test_s2_ui_flows.py::test_s2_c14_stage1_export_import_session_survives') }
                'S2-C15' { Invoke-PytestNodes @('verify/stage-2/test_s2_differential.py::test_s2_c28_differential_payments_and_holds') }
                'S2-C16' { Invoke-PytestNodes @('verify/stage-2/test_s2_wallet_authorizations.py::test_s2_c16_me_balance_total_available') }
                'S2-C17' { & $py -m pytest -q -p no:cacheprovider verify/stage-2/test_s2_authorization_spec.py -k 'test_s2_c17_' }
                'S2-C18' { & $py -m pytest -q -p no:cacheprovider verify/stage-2/test_s2_wallet_authorizations.py verify/stage-2/test_s2_authorization_spec.py -k 'test_s2_c18_' }
                'S2-C20' { & $py -m pytest -q -p no:cacheprovider verify/stage-2/test_s2_authorization_spec.py verify/stage-2/test_s2_wallet_authorizations.py -k 'test_s2_c20_' }
                'S2-C21' { Invoke-PytestNodes @('verify/stage-2/test_s2_wallet_authorizations.py::test_s2_c21_list_filters_direction') }
                'S2-C22' { & $py -m pytest -q -p no:cacheprovider verify/stage-2/test_s2_authorization_spec.py -k 'test_s2_c22_' }
                'S2-C23' { Invoke-PytestNodes @('verify/stage-2/test_s2_authorization_spec.py::test_s2_c23_expired_seed_releases_available_on_read') }
                'S2-C24' { Invoke-PytestNodes @('verify/stage-2/test_s2_ui_testids.py::test_s2_c25_authorizations_screen_testids') }
                'S2-C26' { & $py -m pytest -q -p no:cacheprovider verify/stage-2/test_s2_regression_stage1.py -k 'test_s2_c26_' }
                'S2-C27' { Invoke-PytestNodes @('verify/stage-2/test_s2_concurrent_auth.py::test_s2_c27_concurrent_authorize_same_key') }
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
