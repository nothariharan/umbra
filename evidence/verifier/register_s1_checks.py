"""Register verifier checks for Pocketful Stage 1. Run from repo root."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

CHECKS = [
    ("S1-C1", "S1-R1", "stage-1/ contains service source, Dockerfile, and RUN.md"),
    ("S1-C2", "S1-R2", "RUN.md documents one fenced docker build-and-run command"),
    ("S1-C3", "S1-R3,S1-R44", "Dockerfile PORT and sources bind 0.0.0.0:PORT"),
    ("S1-C4", "S1-R4", "GET /health returns 200 {\"status\":\"ok\"} within harness boot window"),
    ("S1-C5", "S1-R5,S1-R17", "POST /_test/reset 204, repeat supported, negative balance 422 unchanged"),
    ("S1-C6", "S1-R6,S1-R7", "JSON conventions, RFC3339 offsets, unknown fields ignored, ids <=64"),
    ("S1-C9", "S1-R25,S1-R26,S1-R28,S1-R15", "signup/login/auth paths and handle derivation"),
    ("S1-C10", "S1-R27", "export snapshot does not contain plaintext fixture passwords"),
    ("S1-C11", "S1-R30", "GET /me profile fields and balances"),
    ("S1-C12", "S1-R31,S1-R32,S1-R46", "POST /payments defaults, notes, integral amount forms"),
    ("S1-C13", "S1-R33,S1-R19", "POST /requests without payer balance check"),
    ("S1-C14", "S1-R34", "POST /requests/{id}/pay idempotent payer-only payment"),
    ("S1-C15", "S1-R35", "decline/cancel idempotent with forbidden and not_pending cases"),
    ("S1-C16", "S1-R36,S1-R23", "GET /requests filters, pagination, bad integer queries"),
    ("S1-C17", "S1-R37,S1-R38", "POST /splits shares and rounding table"),
    ("S1-C18", "S1-R20,S1-R21,S1-R39", "GET /activity visibility and pagination"),
    ("S1-C20", "S1-R22", "4xx/5xx error envelope code and message"),
    ("S1-C21", "S1-R23,S1-R29", "Idempotency-Key length and limit/offset ranges"),
    ("S1-C22", "S1-R29", "idempotency replay, reuse, post-4xx reuse on POST /payments"),
    ("S1-C23", "S1-R40,S1-R41,S1-R16", "export/import shape and round-trip preserves payments"),
    ("S1-C24", "S1-R42", "POST /settlements operator atomic batch"),
    ("S1-C25", "S1-R43", "non-operator forbidden on settlements"),
    ("S1-C26", "S1-R9,S1-R10,S1-R11", "conservation, non-negative, request pay-once"),
    ("S1-C27", "S1-R24,S1-R45", "no 5xx under concurrent payments and parallel reads"),
    ("S1-C28", "S1-R8", "scope endpoints respond for pay/request/split/activity"),
    ("S1-C29", "S1-R12,S1-R13", "amount bounds and fixture currency minor_units"),
    ("S1-C30", "S1-R14", "handle immutable after account creation"),
    ("S1-C31", "S1-R9,S1-R10,S1-R12", "150-step payment differential vs reference_model"),
    ("S1-C32", "S1-R1,S1-R2,S1-R3,S1-R4,S1-R5,S1-R6,S1-R7,S1-R8,S1-R9,S1-R10,S1-R11,S1-R12,S1-R13,S1-R14,S1-R15,S1-R16,S1-R17,S1-R18,S1-R19,S1-R20,S1-R21,S1-R22,S1-R23,S1-R24,S1-R25,S1-R26,S1-R27,S1-R28,S1-R29,S1-R30,S1-R31,S1-R32,S1-R33,S1-R34,S1-R35,S1-R36,S1-R37,S1-R38,S1-R39,S1-R40,S1-R41,S1-R42,S1-R43,S1-R44,S1-R45,S1-R46", "official harness via lever on SUBMIT"),
    ("S1-C33", "S1-R29", "concurrent idempotency, per-user scope, pre-validation key claim, all five paths"),
    ("S1-C34", "S1-R34,S1-R37,S1-R38,S1-R42", "pay visibility body distinctness, split-only caller, zero-share, settlement batch"),
    ("S1-C35", "S1-R28,S1-R43,S1-R32,S1-R36,S1-R41", "multi-token sessions, operator privacy, note length, import replay"),
]


def main():
    for cid, req, text in CHECKS:
        subprocess.check_call(
            [PY, "scripts/record.py", "check", "--seat", "verifier", "--id", cid, "--req", req, "--text", text],
            cwd=ROOT,
        )
    print("registered", len(CHECKS), "checks")


if __name__ == "__main__":
    main()
