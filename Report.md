# BigEye Pro — Test Report

**Date:** 2025-02-09 20:23 (UTC+07:00)
**Platform:** macOS — Python 3.12.4, pytest 9.0.2, PySide6 6.7.0
**Result:** **838 passed, 0 failed** in 32.72s

---

## Summary

| Side | Test Files | Tests | Passed | Failed |
|------|-----------|-------|--------|--------|
| Client (Frontend) | 17 | 580 | 580 | 0 |
| Server (Backend) | 15 | 258 | 258 | 0 |
| **Total** | **32** | **838** | **838** | **0** |

---

## Client Tests (580 tests)

| # | Test File | Tests | Status |
|---|-----------|-------|--------|
| 1 | `test_file_processing.py` | 66 | PASS |
| 2 | `test_keyword_dictionary.py` | 64 | PASS |
| 3 | `test_helpers.py` | 48 | PASS |
| 4 | `test_retry_logic.py` | 40 | PASS |
| 5 | `test_gemini_engine.py` | 39 | PASS |
| 6 | `test_keyword_processor.py` | 38 | PASS |
| 7 | `test_copyright_guard.py` | 35 | PASS |
| 8 | `test_csv_export_formats.py` | 31 | PASS |
| 9 | `test_config.py` | 29 | PASS |
| 10 | `test_security.py` | 29 | PASS |
| 11 | `test_api_client.py` | 28 | PASS |
| 12 | `test_api_mocked.py` | 28 | PASS |
| 13 | `test_csv_exporter.py` | 22 | PASS |
| 14 | `test_credit_calculation.py` | 18 | PASS |
| 15 | `test_signals.py` | 18 | PASS |
| 16 | `test_journal_manager.py` | 16 | PASS |
| 17 | `test_integration_workers.py` | 16 | PASS |
| 18 | `test_auth_manager.py` | 15 | PASS |

### Key Areas Covered (Client)

- **API Client** — Error mapping (401–503), token management, network errors, all API methods
- **Auth Manager** — Login/register session persistence, token validation, keyring operations
- **Gemini Engine** — Error classification, JSON parsing, model configuration, retry logic with exponential backoff
- **File Processing** — Image/video detection, folder scanning, file counting
- **Keyword Processing** — Cleaning, stemming, dedup, blacklist filtering, iStock/hybrid/single modes
- **Copyright Guard** — Blacklist matching, text scanning, keyword filtering, violation reporting
- **CSV Export** — iStock (photo/video split), Adobe, Shutterstock formats, special characters
- **Credit Calculation** — Platform rates, cost estimation, balance checks, charged calculation
- **Qt Signals** — QueueManager, FileWorker, JobManager signal emissions
- **Journal Manager** — Create/read/update/delete journals, crash recovery
- **Integration Workers (pytest-qt)** — AuthWorker login/register flows, StartupWorker balance/promos/rates loading, chained login-to-balance flow

---

## Server Tests (258 tests)

| # | Test File | Tests | Status |
|---|-----------|-------|--------|
| 1 | `test_models.py` | 35 | PASS |
| 2 | `test_api_job.py` | 33 | PASS |
| 3 | `test_promo_engine.py` | 26 | PASS |
| 4 | `test_api_auth.py` | 25 | PASS |
| 5 | `test_api_credit.py` | 23 | PASS |
| 6 | `test_security.py` | 21 | PASS |
| 7 | `test_api_system.py` | 20 | PASS |
| 8 | `test_routers_job.py` | 19 | PASS |
| 9 | `test_config.py` | 16 | PASS |
| 10 | `test_routers_system.py` | 11 | PASS |
| 11 | `test_integration_transaction.py` | 10 | PASS |
| 12 | `test_transaction_consistency.py` | 8 | PASS |
| 13 | `test_integration_auth.py` | 6 | PASS |
| 14 | `test_dependencies.py` | 5 | PASS |

### Key Areas Covered (Server)

- **Auth API** — Register (validation, duplicates, case-insensitive), Login (password, device mismatch, banned), JWT validation
- **Credit API** — Balance (with promos), history, top-up (with promo codes, validation)
- **Job API** — Reserve (rates, insufficient credits, anti-cheat), Finalize (refund calc, idempotency, overclaim), full reserve-refund cycle
- **System API** — Health check, update check, maintenance mode, expired job cleanup, promo expiration, prompt management
- **Security** — Password hashing (bcrypt), JWT create/decode/expiry, AES encrypt/decrypt
- **Models** — Pydantic validation for all request/response schemas
- **Promo Engine** — Exchange rates, promo eligibility, tier matching, redemption counting
- **Integration: Transaction Consistency** — Reserve-refund protocol, AI failure full refund, partial refund, double finalize idempotency, anti-cheat overclaim rejection, sequential job balance integrity
- **Integration: Auth Flow** — Register → login → balance check, wrong password retry, device mismatch blocking, duplicate registration

---

## Test Infrastructure

- **Mocking:** Firestore (server), httpx/api_client (client), keyring (client)
- **Qt Testing:** pytest-qt with real QThread — no GUI launched
- **Fixtures:** Shared conftest adds `server/` and `client/` to `sys.path`
- **All tests are fully isolated** — no real network calls, no real database, no real keychain access

---

## Issues Found During Manual Testing (2025-02-09)

6 issues were identified during manual testing of the desktop client and fixed in commit `623e9dc`.

### #1 — START button slow (5-10s) on first use
- **Root cause:** Server reads `system_config/app_settings` **twice** during `/job/reserve` — once for credit rates, again for prompts/blacklist/dictionary. Each Firestore read adds 1-3s on cold start.
- **Fix:** Refactored `server/app/routers/job.py` to load `system_config/app_settings` **once** and pass the pre-loaded dict to `_get_credit_rates()`. Eliminates ~2-4s.

### #2 — Adobe/Shutterstock mode crashes during credit check
- **Root cause:** Client HTTP timeout was 30s. On slow networks or cold Firestore connections, the reserve call can exceed this, causing an unhandled timeout → crash.
- **Fix:** Increased `client/core/api_client.py` timeout from **30s → 60s**.

### #3 — No step-by-step progress during preparation
- **Root cause:** UI showed only "Preparing... Reserving credits" for all 9 internal steps (reserve → decrypt → blacklist → engine setup → cache → journal → start).
- **Fix:** Added `status_update` Signal to `JobManager`. UI now shows: "Verifying credits..." → "Preparing configuration..." → "Setting up processing engine..." → "Optimizing for large batch..." → "Starting processing..."
- **Files:** `client/core/job_manager.py`, `client/ui/main_window.py`

### #4 — SSL:WRONG_VERSION_NUMBER on video processing (Single Words mode)
- **Root cause:** gRPC SSL connection pool corruption after processing multiple modes. The `_upload_video()` call to Gemini File API fails with SSL handshake error.
- **Fix:**
  1. Classified SSL errors as **retryable** in `classify_error()` (`gemini_engine.py`)
  2. Added **3-retry loop with exponential backoff** specifically for `_upload_video()` to handle transient SSL failures

### #5 — Video processing is very slow
- **Root cause:** Expected behavior — Gemini requires upload → server-side processing (30-120s/file) → generation. Cannot be sped up.
- **Mitigation:** Added `status_update.emit("Uploading video: filename")` so users see which video is being processed instead of no feedback.

### #6 — Inspector missing character count for Title/Description
- **Root cause:** Keywords showed count `Keywords (45)` but Title/Description did not.
- **Fix:** Changed static "Title" / "Description" labels to dynamic `Title (N)` / `Description (N)` in `client/ui/components/inspector.py`, updating on each file selection.

### Summary of Changes

| File | Changes |
|:--|:--|
| `server/app/routers/job.py` | Read `system_config` once; pass to `_get_credit_rates()` |
| `client/core/api_client.py` | Timeout 30s → 60s |
| `client/core/job_manager.py` | Add `status_update` Signal; emit at each step + video upload |
| `client/ui/main_window.py` | Connect `status_update` → progress text + status bar |
| `client/core/engines/gemini_engine.py` | SSL error classification + video upload retry (3x) |
| `client/ui/components/inspector.py` | Title/Description character count labels |

---

## Conclusion

All **838 tests pass** with zero failures across both frontend and backend. The test suite covers unit tests, API endpoint tests, signal/slot tests, and integration tests for critical flows (authentication, credit transactions, worker thread handshakes).

6 additional issues found during manual testing have been addressed in a follow-up commit.
