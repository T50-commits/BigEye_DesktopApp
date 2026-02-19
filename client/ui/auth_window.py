"""
BigEye Pro — Auth Window (Task B-04)
Login / Register QDialog with Deep Navy theme. ALL TEXT IN ENGLISH.
Uses QThread for async API calls via AuthManager.
"""
import re
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QStackedWidget, QWidget, QGraphicsDropShadowEffect,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize, QThread, QObject, Slot, QByteArray
from PySide6.QtGui import (
    QLinearGradient, QColor, QPainter, QBrush, QPen,
    QFont, QRadialGradient, QIcon, QPixmap
)
from PySide6.QtSvg import QSvgRenderer

from core.config import AUTH_WINDOW_WIDTH
from core.auth_manager import AuthManager
from core.api_client import (
    APIError, NetworkError, AuthenticationError, ForbiddenError,
    ConflictError, RateLimitError, MaintenanceError,
)

logger = logging.getLogger("bigeye")


# ═══════════════════════════════════════
# Auth Worker (QThread)
# ═══════════════════════════════════════

class AuthWorker(QObject):
    """Runs login/register on a background thread."""
    finished = Signal(dict)   # success result
    error = Signal(str)       # error message for UI

    def __init__(self, auth_manager: AuthManager):
        super().__init__()
        self._auth = auth_manager
        self._action = ""
        self._args = {}

    def set_login(self, email: str, password: str):
        self._action = "login"
        self._args = {"email": email, "password": password}

    def set_register(self, email: str, password: str, name: str):
        self._action = "register"
        self._args = {"email": email, "password": password, "name": name}

    @Slot()
    def run(self):
        try:
            if self._action == "login":
                result = self._auth.login(**self._args)
            else:
                result = self._auth.register(**self._args)
            self.finished.emit(result)
        except AuthenticationError:
            self.error.emit("Incorrect email or password")
        except ForbiddenError:
            self.error.emit("Device mismatch — this account is bound to another device.\nPlease contact admin.")
        except ConflictError:
            self.error.emit("This email is already registered")
        except RateLimitError:
            self.error.emit("Too many attempts, please wait")
        except MaintenanceError:
            self.error.emit("Server is under maintenance. Please try again later.")
        except NetworkError:
            self.error.emit("Cannot connect to server. Please check your internet.")
        except APIError as e:
            self.error.emit(f"Server error: {e}")
        except Exception as e:
            logger.error(f"Auth error: {e}")
            self.error.emit("An unexpected error occurred. Please try again.")


class GradientText(QLabel):
    """Label with gradient text effect for the logo."""

    def __init__(self, text: str, font_size: int = 30, parent=None):
        super().__init__(text, parent)
        self._font_size = font_size
        font = QFont("Helvetica Neue", font_size)
        font.setWeight(QFont.Weight.Black)
        self.setFont(font)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0.0, QColor("#FF00CC"))
        gradient.setColorAt(1.0, QColor("#7B2FFF"))

        pen = QPen(QBrush(gradient), 1)
        painter.setPen(pen)
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()


class AmbientGlow(QWidget):
    """Decorative ambient glow circles behind the form."""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Magenta glow
        grad1 = QRadialGradient(self.width() * 0.3, self.height() * 0.3, 150)
        grad1.setColorAt(0.0, QColor(255, 0, 204, 25))
        grad1.setColorAt(1.0, QColor(255, 0, 204, 0))
        painter.setBrush(QBrush(grad1))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            int(self.width() * 0.1), int(self.height() * 0.1), 300, 300
        )

        # Purple glow
        grad2 = QRadialGradient(self.width() * 0.7, self.height() * 0.7, 150)
        grad2.setColorAt(0.0, QColor(123, 47, 255, 25))
        grad2.setColorAt(1.0, QColor(123, 47, 255, 0))
        painter.setBrush(QBrush(grad2))
        painter.drawEllipse(
            int(self.width() * 0.5), int(self.height() * 0.4), 300, 300
        )

        painter.end()


class AuthWindow(QDialog):
    """Authentication window with Sign In / Register tabs."""

    login_success = Signal(str, str)  # jwt_token, user_display_name

    def __init__(self, auth_manager: AuthManager | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BigEye Pro — Sign In")
        self.setFixedWidth(AUTH_WINDOW_WIDTH)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos = None
        self._auth = auth_manager or AuthManager()
        self._thread = None
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        # Main container
        self.container = QWidget()
        self.container.setObjectName("authContainer")
        self.container.setStyleSheet("""
            QWidget#authContainer {
                background: #1A1A2E;
                border: 1px solid #1A3A6B;
                border-radius: 20px;
            }
        """)

        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.addWidget(self.container)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(8)

        # Ambient glow background
        self.glow = AmbientGlow(self.container)
        self.glow.setGeometry(0, 0, AUTH_WINDOW_WIDTH, 600)
        self.glow.lower()

        # Logo
        logo = GradientText("BIGEYE PRO", font_size=42)
        logo.setMinimumHeight(60)
        layout.addWidget(logo)

        # Subtitle
        subtitle = QLabel("STOCK METADATA GENERATOR")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #4A5568; font-size: 13px; letter-spacing: 3px;")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Tab selector
        tab_layout = QHBoxLayout()
        tab_layout.setSpacing(0)

        self.tab_signin = QPushButton("SIGN IN")
        self.tab_signin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_signin.clicked.connect(lambda: self._switch_tab(0))

        self.tab_register = QPushButton("REGISTER")
        self.tab_register.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_register.clicked.connect(lambda: self._switch_tab(1))

        tab_layout.addWidget(self.tab_signin)
        tab_layout.addWidget(self.tab_register)
        layout.addLayout(tab_layout)

        # Apply initial tab styles
        self._apply_tab_styles(0)

        layout.addSpacing(16)

        # Stacked widget for forms
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_signin_form())
        self.stack.addWidget(self._create_register_form())
        layout.addWidget(self.stack)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet(
            "color: #FF4560; font-size: 12px; padding: 4px;"
        )
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        layout.addStretch()

    def _create_signin_form(self) -> QWidget:
        widget = QWidget()
        form = QVBoxLayout(widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(12)

        self.signin_email = QLineEdit()
        self.signin_email.setPlaceholderText("Email")
        self.signin_email.setMinimumHeight(42)
        form.addWidget(self.signin_email)

        self.signin_password, signin_pw_row = self._create_password_field("Password")
        form.addWidget(signin_pw_row)

        form.addSpacing(8)

        self.btn_signin = QPushButton("Sign In")
        self.btn_signin.setObjectName("signInButton")
        self.btn_signin.setMinimumHeight(44)
        self.btn_signin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_signin.clicked.connect(self._on_signin)
        form.addWidget(self.btn_signin)

        return widget

    def _create_register_form(self) -> QWidget:
        widget = QWidget()
        form = QVBoxLayout(widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(12)

        self.reg_name = QLineEdit()
        self.reg_name.setPlaceholderText("Full Name")
        self.reg_name.setMinimumHeight(42)
        form.addWidget(self.reg_name)

        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Email")
        self.reg_email.setMinimumHeight(42)
        form.addWidget(self.reg_email)

        self.reg_password, reg_pw_row = self._create_password_field("Password")
        form.addWidget(reg_pw_row)

        self.reg_confirm, reg_cf_row = self._create_password_field("Confirm Password")
        form.addWidget(reg_cf_row)

        form.addSpacing(8)

        self.btn_register = QPushButton("Create Account")
        self.btn_register.setObjectName("registerButton")
        self.btn_register.setMinimumHeight(44)
        self.btn_register.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_register.clicked.connect(self._on_register)
        form.addWidget(self.btn_register)

        return widget

    def _create_password_field(self, placeholder: str) -> tuple:
        """Create a password QLineEdit with a show/hide toggle button.
        Returns (line_edit, container_widget)."""
        container = QWidget()
        container.setMinimumHeight(42)
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        line_edit.setMinimumHeight(42)
        # Remove right border radius so toggle button sits flush
        line_edit.setStyleSheet(
            line_edit.styleSheet() +
            "QLineEdit { border-top-right-radius: 0px; border-bottom-right-radius: 0px; }"
        )
        row.addWidget(line_edit)

        toggle_btn = QPushButton()
        toggle_btn.setFixedSize(42, 42)
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setStyleSheet("""
            QPushButton {
                background: #16213E;
                border: 1px solid #1A3A6B;
                border-left: none;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            QPushButton:hover {
                background: #1A3A6B;
            }
        """)

        # Minimal SVG eye icons (outline style)
        _SVG_EYE_OPEN = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#8892A8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>"""
        _SVG_EYE_CLOSED = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#8892A8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
          <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
          <line x1="1" y1="1" x2="23" y2="23"/>
        </svg>"""

        def _svg_icon(svg_bytes: bytes) -> QIcon:
            renderer = QSvgRenderer(QByteArray(svg_bytes))
            pixmap = QPixmap(20, 20)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            return QIcon(pixmap)

        toggle_btn.setIcon(_svg_icon(_SVG_EYE_OPEN))
        toggle_btn.setIconSize(QSize(20, 20))

        def _toggle():
            if line_edit.echoMode() == QLineEdit.EchoMode.Password:
                line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
                toggle_btn.setIcon(_svg_icon(_SVG_EYE_CLOSED))
            else:
                line_edit.setEchoMode(QLineEdit.EchoMode.Password)
                toggle_btn.setIcon(_svg_icon(_SVG_EYE_OPEN))

        toggle_btn.clicked.connect(_toggle)
        row.addWidget(toggle_btn)

        return line_edit, container

    _TAB_ACTIVE_STYLE = """
        QPushButton {
            background: #7B2FFF25;
            color: #FF00CC;
            border: 1px solid #7B2FFF55;
            border-radius: 10px;
            padding: 8px 20px;
            font-weight: 700;
            font-size: 13px;
        }
        QPushButton:hover {
            background: #7B2FFF35;
            color: #FF00CC;
            border-color: #7B2FFF55;
        }
    """
    _TAB_INACTIVE_STYLE = """
        QPushButton {
            background: transparent;
            color: #4A5568;
            border: 1px solid #1A3A6B;
            border-radius: 10px;
            padding: 8px 20px;
            font-weight: 500;
            font-size: 13px;
        }
        QPushButton:hover {
            background: #16213E;
            color: #8892A8;
            border-color: #1A3A6B;
        }
    """

    def _apply_tab_styles(self, active_index: int):
        if active_index == 0:
            self.tab_signin.setStyleSheet(self._TAB_ACTIVE_STYLE)
            self.tab_register.setStyleSheet(self._TAB_INACTIVE_STYLE)
        else:
            self.tab_signin.setStyleSheet(self._TAB_INACTIVE_STYLE)
            self.tab_register.setStyleSheet(self._TAB_ACTIVE_STYLE)

    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        self.error_label.hide()
        self._apply_tab_styles(index)

    def _show_error(self, msg: str):
        self.error_label.setText(msg)
        self.error_label.show()

    def _validate_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _on_signin(self):
        email = self.signin_email.text().strip()
        password = self.signin_password.text()

        if not email or not password:
            self._show_error("Please fill in all fields")
            return
        if not self._validate_email(email):
            self._show_error("Please enter a valid email address")
            return

        self.error_label.hide()
        self._set_loading(True)

        self._worker = AuthWorker(self._auth)
        self._worker.set_login(email, password)
        self._start_worker()

    def _on_register(self):
        name = self.reg_name.text().strip()
        email = self.reg_email.text().strip()
        password = self.reg_password.text()
        confirm = self.reg_confirm.text()

        if not all([name, email, password, confirm]):
            self._show_error("Please fill in all fields")
            return
        if len(name) < 2 or len(name) > 100:
            self._show_error("Name must be 2-100 characters")
            return
        if not self._validate_email(email):
            self._show_error("Please enter a valid email address")
            return
        if len(password) < 8:
            self._show_error("Password must be at least 8 characters")
            return
        if password != confirm:
            self._show_error("Passwords do not match")
            return

        self.error_label.hide()
        self._set_loading(True)

        self._worker = AuthWorker(self._auth)
        self._worker.set_register(email, password, name)
        self._start_worker()

    # ── QThread management ──

    def _start_worker(self):
        """Start the auth worker on a background thread."""
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_auth_success)
        self._worker.error.connect(self._on_auth_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _on_auth_success(self, result: dict):
        """Handle successful login/register."""
        self._set_loading(False)
        token = result.get("token", "")
        name = self._auth.user_name or result.get("full_name", result.get("name", "User"))
        logger.info(f"Auth success: {name}")
        self.login_success.emit(token, name)
        self.accept()

    def _on_auth_error(self, message: str):
        """Handle auth error — show message in UI."""
        self._set_loading(False)
        self._show_error(message)
        logger.warning(f"Auth failed: {message}")

    def _cleanup_thread(self):
        """Clean up thread and worker references."""
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        if self._thread:
            self._thread.deleteLater()
            self._thread = None

    def _set_loading(self, loading: bool):
        """Disable/enable form controls during API call."""
        self.btn_signin.setEnabled(not loading)
        self.btn_register.setEnabled(not loading)
        self.tab_signin.setEnabled(not loading)
        self.tab_register.setEnabled(not loading)
        self.signin_email.setEnabled(not loading)
        self.signin_password.setEnabled(not loading)
        self.reg_name.setEnabled(not loading)
        self.reg_email.setEnabled(not loading)
        self.reg_password.setEnabled(not loading)
        self.reg_confirm.setEnabled(not loading)
        if loading:
            current_btn = self.btn_signin if self.stack.currentIndex() == 0 else self.btn_register
            current_btn.setText("Please wait...")
        else:
            self.btn_signin.setText("Sign In")
            self.btn_register.setText("Create Account")

    # ── Frameless window dragging ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
