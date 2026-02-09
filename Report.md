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

## Conclusion

All **838 tests pass** with zero failures across both frontend and backend. The test suite covers unit tests, API endpoint tests, signal/slot tests, and integration tests for critical flows (authentication, credit transactions, worker thread handshakes).
