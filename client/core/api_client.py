"""
BigEye Pro — API Client (Task B-03)
Centralized HTTP client for all backend API calls.
Uses httpx.Client with base_url and 30s timeout.
"""
import logging
import httpx
from core.config import API_BASE_URL

logger = logging.getLogger("bigeye")


# ═══════════════════════════════════════
# Custom Exceptions (all extend APIError)
# ═══════════════════════════════════════

class APIError(Exception):
    """Base API error."""
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class NetworkError(APIError):
    """Cannot connect to server."""
    def __init__(self, message: str = "Cannot connect to server. Please check your internet."):
        super().__init__(message, 0)


class AuthenticationError(APIError):
    """401 — Invalid credentials."""
    pass


class InsufficientCreditsError(APIError):
    """402 — Not enough credits."""
    def __init__(self, message: str, required: int = 0, available: int = 0, shortfall: int = 0):
        super().__init__(message, 402)
        self.required = required
        self.available = available
        self.shortfall = shortfall


class ForbiddenError(APIError):
    """403 — Device mismatch or forbidden."""
    pass


class ConflictError(APIError):
    """409 — Already exists (e.g. duplicate email)."""
    pass


class UpdateRequiredError(APIError):
    """426 — Client must update."""
    def __init__(self, message: str, version: str = "", download_url: str = "", force: bool = False):
        super().__init__(message, 426)
        self.version = version
        self.download_url = download_url
        self.force = force


class RateLimitError(APIError):
    """429 — Too many requests."""
    pass


class MaintenanceError(APIError):
    """503 — Server maintenance."""
    pass


# ═══════════════════════════════════════
# API Client
# ═══════════════════════════════════════

class APIClient:
    """Centralized HTTP client for BigEye Pro backend."""

    def __init__(self, base_url: str = API_BASE_URL):
        self._client = httpx.Client(
            base_url=base_url,
            timeout=60.0,
            headers={"Content-Type": "application/json"},
        )
        self._token = ""

    def set_token(self, jwt: str):
        """Set JWT token and add Authorization header."""
        self._token = jwt
        self._client.headers["Authorization"] = f"Bearer {jwt}"

    def clear_token(self):
        """Clear JWT token and remove Authorization header."""
        self._token = ""
        self._client.headers.pop("Authorization", None)

    @property
    def is_authenticated(self) -> bool:
        return bool(self._token)

    # ── Auth ──

    def register(self, email: str, password: str, name: str,
                 phone: str, hardware_id: str) -> dict:
        """POST /auth/register — auto set_token on success."""
        data = self._post("/auth/register", {
            "email": email, "password": password, "full_name": name,
            "phone": phone, "hardware_id": hardware_id,
        })
        if "token" in data:
            self.set_token(data["token"])
        return data

    def login(self, email: str, password: str, hardware_id: str) -> dict:
        """POST /auth/login — auto set_token on success."""
        data = self._post("/auth/login", {
            "email": email, "password": password, "hardware_id": hardware_id,
        })
        if "token" in data:
            self.set_token(data["token"])
        return data

    # ── Credits ──

    def get_balance(self) -> int:
        """GET /credit/balance — returns credit balance as int."""
        data = self._get("/credit/balance")
        return data.get("credits", 0)

    def get_balance_with_promos(self) -> dict:
        """GET /credit/balance — returns full response with credits + active_promos + credit_rates + bank_info."""
        data = self._get("/credit/balance")
        return {
            "credits": data.get("credits", 0),
            "exchange_rate": data.get("exchange_rate", 4),
            "credit_rates": data.get("credit_rates", {}),
            "active_promos": data.get("active_promos", []),
            "bank_info": data.get("bank_info", {}),
        }

    def get_history(self, limit: int = 50) -> list:
        """GET /credit/history — returns list of transactions."""
        data = self._get("/credit/history", params={"limit": limit})
        return data.get("transactions", [])

    def topup(self, qr_data: str, promo_code: str = "") -> dict:
        """POST /credit/topup — submit slip QR code data for verification."""
        payload = {"slip": qr_data}
        if promo_code:
            payload["promo_code"] = promo_code
        return self._post("/credit/topup", payload)

    # ── Jobs ──

    def reserve_job(self, file_count: int, mode: str, keyword_style: str,
                    model: str, version: str,
                    photo_count: int = 0, video_count: int = 0) -> dict:
        """POST /job/reserve — returns job_token + encrypted config + rates."""
        return self._post("/job/reserve", {
            "file_count": file_count,
            "photo_count": photo_count,
            "video_count": video_count,
            "mode": mode,
            "keyword_style": keyword_style, "model": model,
            "version": version,
        })

    def finalize_job(self, job_token: str, success: int, failed: int,
                     photos: int, videos: int) -> dict:
        """POST /job/finalize — returns refund info."""
        return self._post("/job/finalize", {
            "job_token": job_token, "success": success, "failed": failed,
            "photos": photos, "videos": videos,
        })

    # ── System ──

    def check_update(self, version: str, hardware_id: str) -> dict:
        """POST /system/check-update — returns update info."""
        return self._post("/system/check-update", {
            "version": version, "hardware_id": hardware_id,
        })

    # ── Internal HTTP helpers ──

    def _get(self, path: str, params: dict | None = None) -> dict:
        """Execute GET request with network error handling."""
        try:
            resp = self._client.get(path, params=params)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error(f"Network error GET {path}: {e}")
            raise NetworkError() from e
        return self._handle_errors(resp)

    def _post(self, path: str, json_body: dict) -> dict:
        """Execute POST request with network error handling."""
        try:
            resp = self._client.post(path, json=json_body)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error(f"Network error POST {path}: {e}")
            raise NetworkError() from e
        return self._handle_errors(resp)

    def _handle_errors(self, resp: httpx.Response) -> dict:
        """Map HTTP status codes to custom exceptions."""
        if resp.status_code == 200:
            return resp.json()

        try:
            body = resp.json()
        except Exception:
            body = {}

        # User-friendly fallback messages by status code
        _friendly = {
            400: "ข้อมูลที่ส่งไม่ถูกต้อง กรุณาลองใหม่",
            401: "กรุณาเข้าสู่ระบบใหม่",
            402: "เครดิตไม่เพียงพอ",
            403: "ไม่มีสิทธิ์เข้าถึง",
            404: "ไม่พบข้อมูลที่ร้องขอ",
            409: "ข้อมูลซ้ำ กรุณาตรวจสอบ",
            422: "ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบ",
            429: "คำขอถี่เกินไป กรุณารอสักครู่",
            500: "เซิร์ฟเวอร์ขัดข้อง กรุณาลองใหม่ภายหลัง",
            502: "เซิร์ฟเวอร์ไม่ตอบสนอง กรุณาลองใหม่",
            503: "ระบบปิดปรับปรุงชั่วคราว",
        }
        fallback = _friendly.get(resp.status_code, f"เกิดข้อผิดพลาด (รหัส {resp.status_code})")
        msg = body.get("detail", body.get("message", fallback))
        logger.warning(f"API error {resp.status_code}: {msg}")

        if resp.status_code == 401:
            raise AuthenticationError(msg, 401)
        elif resp.status_code == 402:
            raise InsufficientCreditsError(
                msg,
                required=body.get("required", 0),
                available=body.get("available", 0),
                shortfall=body.get("shortfall", 0),
            )
        elif resp.status_code == 403:
            raise ForbiddenError(msg, 403)
        elif resp.status_code == 409:
            raise ConflictError(msg, 409)
        elif resp.status_code == 426:
            raise UpdateRequiredError(
                msg,
                version=body.get("version", ""),
                download_url=body.get("download_url", ""),
                force=body.get("force", False),
            )
        elif resp.status_code == 429:
            raise RateLimitError(msg, 429)
        elif resp.status_code == 503:
            raise MaintenanceError(msg, 503)
        else:
            raise APIError(msg, resp.status_code)


# Singleton
api = APIClient()
