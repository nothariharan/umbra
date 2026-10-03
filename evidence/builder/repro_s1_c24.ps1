$env:UMBRA_SEAT = 'verifier'
$env:SUBMIT_REV = '1125eee49810'
powershell -NoProfile -File evidence/verifier/run_s1_check.ps1 -Check S1-C24
