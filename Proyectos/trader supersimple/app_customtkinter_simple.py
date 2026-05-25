from __future__ import annotations

import json
import logging
import math
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable
from uuid import uuid4

import customtkinter as ctk


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


API_PREFIX = "/api/v1"
LOOP_INTERVAL_MS = 4000
LOOP_RETRY_MS = 1200
DEFAULT_MAX_LOOP_ERRORS = 3
DEFAULT_MAX_DRAWDOWN_STOP_PCT = 8.0
PAPER_HOST_HINT = "paper-api.alpaca.markets"


@dataclass
class RuntimeState:
    run_id: str = ""
    session_id: str = ""
    loop_running: bool = False
    current_ticker: str = ""
    last_request_id: str = ""
    loop_error_count: int = 0


class OnlineEquityMetrics:
    """Numerically stable online metrics from equity snapshots."""

    def __init__(self) -> None:
        self.initial_equity: float | None = None
        self.peak_equity: float | None = None
        self.last_equity: float | None = None
        self.max_drawdown: float = 0.0
        self.returns_count: int = 0
        self.returns_mean: float = 0.0
        self.returns_m2: float = 0.0

    def reset(self) -> None:
        self.__init__()

    def update(self, equity_value) -> None:
        try:
            equity = float(equity_value)
        except (TypeError, ValueError):
            return
        if not math.isfinite(equity) or equity <= 0:
            return

        if self.initial_equity is None:
            self.initial_equity = equity
            self.peak_equity = equity
            self.last_equity = equity
            return

        assert self.peak_equity is not None
        assert self.last_equity is not None

        if equity > self.peak_equity:
            self.peak_equity = equity
        drawdown = (self.peak_equity - equity) / self.peak_equity
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

        if self.last_equity > 0:
            step_return = math.log(equity / self.last_equity)
            self.returns_count += 1
            delta = step_return - self.returns_mean
            self.returns_mean += delta / self.returns_count
            delta2 = step_return - self.returns_mean
            self.returns_m2 += delta * delta2
        self.last_equity = equity

    def summary(self) -> dict[str, float]:
        cumulative = 0.0
        if self.initial_equity and self.last_equity:
            cumulative = (self.last_equity / self.initial_equity) - 1.0

        volatility = 0.0
        if self.returns_count > 1:
            volatility = math.sqrt(self.returns_m2 / (self.returns_count - 1))

        sharpe_like = 0.0
        if volatility > 1e-12:
            sharpe_like = self.returns_mean / volatility

        return {
            "cum_return": cumulative,
            "max_drawdown": self.max_drawdown,
            "step_volatility": volatility,
            "step_sharpe_like": sharpe_like,
        }


def load_env_value(key: str) -> str:
    value = os.getenv(key, "").strip()
    if value:
        return value

    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / "DT spec-driven" / ".env",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            for line in candidate.read_text(encoding="utf-8", errors="ignore").splitlines():
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                if k.strip() == key:
                    return v.strip().strip('"').strip("'")
        except OSError:
            continue
    return ""


def build_audit_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("dt_trade_app")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger

    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def looks_like_paper_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url.strip())
    host = parsed.netloc.lower()
    if not host:
        return False
    return PAPER_HOST_HINT in host


class BaseHttpClient:
    @staticmethod
    def _decode_json(data: bytes) -> dict:
        text = data.decode("utf-8", errors="replace")
        if not text.strip():
            return {}
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise RuntimeError("Respuesta API invalida.")
        return parsed


class ApiClient(BaseHttpClient):
    def __init__(self, base_url: str, api_token: str, admin_token: str, actor_id: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token.strip()
        self.admin_token = admin_token.strip()
        self.actor_id = actor_id.strip()

    def configure(self, base_url: str, api_token: str, admin_token: str, actor_id: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token.strip()
        self.admin_token = admin_token.strip()
        self.actor_id = actor_id.strip()

    def _headers(self, use_admin: bool = False) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["X-DT-Trade-Token"] = self.api_token
        if use_admin and self.admin_token:
            headers["X-DT-Trade-Admin-Token"] = self.admin_token
        if self.actor_id:
            headers["X-DT-Actor"] = self.actor_id
        return headers

    def _request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        use_admin: bool = False,
        timeout_sec: int = 20,
    ):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.base_url}{path}",
            method=method,
            data=data,
            headers=self._headers(use_admin),
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as res:
                return self._unwrap(self._decode_json(res.read()))
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                parsed = self._decode_json(raw)
            except Exception:
                text = raw.decode("utf-8", errors="replace")
                raise RuntimeError(f"HTTP {exc.code}: {text[:250]}") from exc
            raise RuntimeError(str(parsed.get("error") or parsed.get("message") or f"HTTP {exc.code}")) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"No se pudo conectar con la API: {exc}") from exc

    @staticmethod
    def _unwrap(payload: dict):
        if "ok" in payload and "data" in payload:
            if payload.get("ok") is False:
                raise RuntimeError(str(payload.get("error", "Error API")))
            return payload["data"]
        return payload

    def health(self):
        return self._request("GET", f"{API_PREFIX}/health")

    def train_sequence(self, ticker: str, profile: str, sample_periods: int):
        return self._request(
            "POST",
            f"{API_PREFIX}/train/sequence",
            {"ticker": ticker, "profile": profile, "sample_periods": sample_periods},
        )

    def promote_paper(self, run_id: str):
        return self._request(
            "POST",
            f"{API_PREFIX}/registry/promote",
            {"run_id": run_id, "target": "paper"},
        )

    def start_paper(self, run_id: str):
        return self._request("POST", f"{API_PREFIX}/runtime/start-paper", {"run_id": run_id})

    def alpaca_paper_status(self):
        return self._request("GET", f"{API_PREFIX}/runtime/alpaca-paper-status", use_admin=True)

    def alpaca_paper_step(self, run_id: str, session_id: str | None = None, request_id: str | None = None):
        payload: dict[str, str] = {"run_id": run_id}
        if session_id:
            payload["session_id"] = session_id
        if request_id:
            payload["request_id"] = request_id
        return self._request("POST", f"{API_PREFIX}/runtime/alpaca-paper-step", payload, use_admin=True)

    def runtime_summary(self, session_id: str):
        query = urllib.parse.urlencode({"session_id": session_id})
        return self._request("GET", f"{API_PREFIX}/runtime/summary?{query}")


class AlpacaDirectClient(BaseHttpClient):
    def __init__(self, api_key: str, secret_key: str, base_url: str) -> None:
        self.api_key = api_key.strip()
        self.secret_key = secret_key.strip()
        self.base_url = base_url.strip().rstrip("/")

    def configure(self, api_key: str, secret_key: str, base_url: str) -> None:
        self.api_key = api_key.strip()
        self.secret_key = secret_key.strip()
        self.base_url = base_url.strip().rstrip("/")

    def account(self) -> dict:
        if not self.api_key or not self.secret_key:
            raise RuntimeError("Faltan credenciales de Alpaca.")
        if not self.base_url:
            raise RuntimeError("Falta ALPACA_BASE_URL.")
        req = urllib.request.Request(
            url=f"{self.base_url}/v2/account",
            method="GET",
            headers={
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.secret_key,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                return self._decode_json(res.read())
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Alpaca HTTP {exc.code}: {text[:250]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"No se pudo conectar con Alpaca: {exc}") from exc


class SimpleTradeApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DT Trade - HiperSimple")
        self.geometry("980x760")
        self.minsize(900, 700)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.runtime_state = RuntimeState()
        self.metrics = OnlineEquityMetrics()
        self._job_lock = threading.Lock()
        self._loop_token = 0
        self.audit_logger = build_audit_logger(Path.cwd() / "logs" / "trader_app.log")
        self.api_client = ApiClient("http://127.0.0.1:8080", "", "", "")
        self.alpaca_client = AlpacaDirectClient("", "", "")

        self._build_ui()
        self._refresh_overview()
        self.set_status("Listo", "Esperando accion.")
        self.log("Aplicacion lista.")
        self.log(f"Auditoria activa: {(Path.cwd() / 'logs' / 'trader_app.log')}")

    # ---------- runtime state ----------
    def _set_runtime_run(self, run_id: str, ticker: str) -> None:
        self.runtime_state.run_id = run_id
        self.runtime_state.current_ticker = ticker
        self.runtime_state.session_id = ""

    def _set_runtime_session(self, session_id: str) -> None:
        self.runtime_state.session_id = session_id.strip()

    def _clear_runtime_session(self) -> None:
        self.runtime_state.session_id = ""

    def _log_ctx(self, level: str, func_name: str, message: str) -> None:
        self.log(f"{level} [{func_name}] {message}")

    # ---------- UI ----------
    def _build_ui(self) -> None:
        root = ctk.CTkFrame(self, corner_radius=16)
        root.pack(fill="both", expand=True, padx=14, pady=14)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(5, weight=0)
        root.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(root, text="DT Trade HiperSimple", font=ctk.CTkFont(size=28, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 8)
        )
        ctk.CTkLabel(
            root,
            text="Flujo corto y robusto: conectar, entrenar, paper, Alpaca real.",
            font=ctk.CTkFont(size=14),
            text_color=("#3A3A3A", "#D0D0D0"),
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))

        stats = ctk.CTkFrame(root, corner_radius=14)
        stats.grid(row=2, column=0, sticky="ew", padx=12, pady=8)
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.next_step_var = ctk.StringVar(value="Entrenar")
        self.train_var = ctk.StringVar(value="Vacio")
        self.bot_var = ctk.StringVar(value="Parado")
        self.rt_var = ctk.StringVar(value="Sin sesion")
        self._stat(stats, 0, "Que toca", self.next_step_var)
        self._stat(stats, 1, "Entrenamiento", self.train_var)
        self._stat(stats, 2, "Bot", self.bot_var)
        self._stat(stats, 3, "Runtime", self.rt_var)

        math_bar = ctk.CTkFrame(root, corner_radius=14)
        math_bar.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        math_bar.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.metric_return_var = ctk.StringVar(value="0.00%")
        self.metric_dd_var = ctk.StringVar(value="0.00%")
        self.metric_vol_var = ctk.StringVar(value="0.000000")
        self.metric_sharpe_var = ctk.StringVar(value="0.0000")
        self._stat(math_bar, 0, "Retorno acum", self.metric_return_var)
        self._stat(math_bar, 1, "Max drawdown", self.metric_dd_var)
        self._stat(math_bar, 2, "Volatilidad paso", self.metric_vol_var)
        self._stat(math_bar, 3, "Sharpe paso", self.metric_sharpe_var)

        ultra = ctk.CTkFrame(root, corner_radius=14)
        ultra.grid(row=4, column=0, sticky="ew", padx=12, pady=8)
        ultra.grid_columnconfigure(5, weight=1)
        ctk.CTkLabel(ultra, text="Modo Ultra Simple", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, padx=(12, 8), pady=10, sticky="w"
        )
        ctk.CTkLabel(ultra, text="Ticker").grid(row=0, column=1, padx=(6, 4), pady=10, sticky="e")
        self.ultra_ticker_var = ctk.StringVar(value="NVDA")
        ctk.CTkEntry(ultra, textvariable=self.ultra_ticker_var, width=120).grid(
            row=0, column=2, padx=(0, 8), pady=10, sticky="w"
        )
        ctk.CTkButton(ultra, text="Conectar", width=110, command=self.on_ultra_connect).grid(
            row=0, column=3, padx=4, pady=10
        )
        ctk.CTkButton(ultra, text="Empezar", width=110, command=self.on_ultra_start).grid(
            row=0, column=4, padx=4, pady=10
        )
        ctk.CTkButton(
            ultra,
            text="Parar",
            width=110,
            command=self.on_ultra_stop,
            fg_color="#8f2f2f",
            hover_color="#7a2525",
        ).grid(row=0, column=5, padx=(4, 12), pady=10, sticky="e")

        top = ctk.CTkFrame(root, corner_radius=14)
        top.grid(row=5, column=0, sticky="nsew", padx=12, pady=8)
        top.grid_columnconfigure((0, 1), weight=1)
        top.grid_rowconfigure(0, weight=1)

        self._build_left_config(top)
        self._build_right_ops(top)

        self._build_bottom_log(root)

    def _build_left_config(self, parent) -> None:
        card = ctk.CTkFrame(parent, corner_radius=12)
        card.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card, text="Conexion", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 8)
        )

        self.base_url_var = ctk.StringVar(value="http://127.0.0.1:8080")
        self.api_token_var = ctk.StringVar(value="")
        self.admin_token_var = ctk.StringVar(value="")
        self.actor_var = ctk.StringVar(value="")
        self.alpaca_key_var = ctk.StringVar(value=load_env_value("ALPACA_API_KEY"))
        self.alpaca_secret_var = ctk.StringVar(value=load_env_value("ALPACA_SECRET_KEY"))
        self.alpaca_base_var = ctk.StringVar(
            value=load_env_value("ALPACA_BASE_URL") or "https://paper-api.alpaca.markets"
        )
        self.allow_live_var = ctk.BooleanVar(
            value=load_env_value("DT_ALLOW_LIVE_TRADING").strip().lower() in {"1", "true", "yes", "on"}
        )
        self.max_drawdown_stop_var = ctk.StringVar(
            value=load_env_value("DT_MAX_DRAWDOWN_STOP_PCT") or f"{DEFAULT_MAX_DRAWDOWN_STOP_PCT}"
        )
        self.max_loop_errors_var = ctk.StringVar(
            value=load_env_value("DT_MAX_LOOP_ERRORS") or f"{DEFAULT_MAX_LOOP_ERRORS}"
        )
        self.live_confirm_var = ctk.StringVar(value=load_env_value("DT_LIVE_CONFIRM"))

        self._entry(card, 1, "Base URL", self.base_url_var)
        self._entry(card, 2, "API Token", self.api_token_var, show="*")
        self._entry(card, 3, "Admin Token", self.admin_token_var, show="*")
        self._entry(card, 4, "Actor ID", self.actor_var)
        self._entry(card, 5, "Alpaca API Key", self.alpaca_key_var, show="*")
        self._entry(card, 6, "Alpaca Secret", self.alpaca_secret_var, show="*")
        self._entry(card, 7, "Alpaca Base URL", self.alpaca_base_var)
        self._entry(card, 8, "Max drawdown stop (%)", self.max_drawdown_stop_var)
        self._entry(card, 9, "Max errores seguidos", self.max_loop_errors_var)
        self._entry(card, 10, "Confirm LIVE (YES_LIVE)", self.live_confirm_var, show="*")

        ctk.CTkSwitch(
            card,
            text="Permitir LIVE (riesgo alto)",
            variable=self.allow_live_var,
            onvalue=True,
            offvalue=False,
        ).grid(row=11, column=0, columnspan=2, sticky="w", padx=12, pady=(2, 4))

        ctk.CTkButton(card, text="Probar conexion API", command=self.on_health).grid(
            row=12, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 6)
        )
        ctk.CTkButton(card, text="Probar Alpaca directo", command=self.on_alpaca_direct).grid(
            row=13, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12)
        )

    def _build_right_ops(self, parent) -> None:
        col = ctk.CTkFrame(parent, corner_radius=0, fg_color="transparent")
        col.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        col.grid_rowconfigure(1, weight=1)
        col.grid_columnconfigure(0, weight=1)

        rt_card = ctk.CTkFrame(col, corner_radius=12)
        rt_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        rt_card.grid_columnconfigure(0, weight=1)
        rt_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(rt_card, text="Log en tiempo real", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )
        self.realtime_box = ctk.CTkTextbox(
            rt_card,
            height=130,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=("#F5FAFF", "#0E1624"),
            border_width=1,
            border_color=("#C9D7EB", "#2B3A54"),
        )
        self.realtime_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.realtime_box.configure(state="disabled")

        ops = ctk.CTkFrame(col, corner_radius=12)
        ops.grid(row=1, column=0, sticky="nsew")
        ops.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ops, text="Operacion simple", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 8)
        )
        self.ticker_var = ctk.StringVar(value="NVDA")
        self.profile_var = ctk.StringVar(value="standard")
        self.periods_var = ctk.StringVar(value="48")
        self._entry(ops, 1, "Ticker", self.ticker_var)
        ctk.CTkLabel(ops, text="Perfil").grid(row=2, column=0, sticky="w", padx=12, pady=6)
        ctk.CTkOptionMenu(ops, variable=self.profile_var, values=["fast", "standard", "deep"]).grid(
            row=2, column=1, sticky="ew", padx=12, pady=6
        )
        self._entry(ops, 3, "Periodos", self.periods_var)

        btns = ctk.CTkFrame(ops, fg_color="transparent")
        btns.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=8)
        btns.grid_columnconfigure((0, 1), weight=1)
        self.quick_btn = ctk.CTkButton(btns, text="Hacerlo todo", command=self.on_quick_start)
        self.quick_btn.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        self.step_btn = ctk.CTkButton(btns, text="Paso manual", command=self.on_single_step)
        self.step_btn.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        loop = ctk.CTkFrame(ops, fg_color="transparent")
        loop.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=4)
        loop.grid_columnconfigure((0, 1), weight=1)
        self.loop_start_btn = ctk.CTkButton(loop, text="Iniciar loop", command=self.on_start_loop)
        self.loop_start_btn.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        self.loop_stop_btn = ctk.CTkButton(
            loop,
            text="Parar loop",
            command=self.on_stop_loop,
            fg_color="#8f2f2f",
            hover_color="#7a2525",
        )
        self.loop_stop_btn.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        ctk.CTkButton(ops, text="Abrir consola web", command=self.on_open_web).grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=12, pady=(6, 12)
        )

    def _build_bottom_log(self, parent) -> None:
        card = ctk.CTkFrame(parent, corner_radius=12)
        card.grid(row=6, column=0, sticky="nsew", padx=20, pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(card, text="Estado y mensajes", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 8)
        )

        self.status_box = ctk.CTkFrame(card, corner_radius=10)
        self.status_box.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.status_box.grid_columnconfigure(0, weight=1)
        self.status_title_var = ctk.StringVar(value="[IDLE] Listo")
        self.status_detail_var = ctk.StringVar(value="Esperando accion.")
        self.status_title_lbl = ctk.CTkLabel(
            self.status_box,
            textvariable=self.status_title_var,
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.status_title_lbl.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        self.status_detail_lbl = ctk.CTkLabel(
            self.status_box,
            textvariable=self.status_detail_var,
            font=ctk.CTkFont(size=12),
            text_color=("#4a4a4a", "#cdcdcd"),
        )
        self.status_detail_lbl.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))
        self.status_progress = ctk.CTkProgressBar(self.status_box, mode="indeterminate")
        self.status_progress.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.status_progress.grid_remove()
        self._apply_status_theme("idle")

        self.log_box = ctk.CTkTextbox(
            card,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color=("#F7FAFF", "#121A27"),
            border_width=1,
            border_color=("#CBD5E1", "#2A3953"),
        )
        self.log_box.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.log_box.configure(state="disabled")

        self.live_line_var = ctk.StringVar(value="Log en vivo: esperando eventos...")
        ctk.CTkLabel(
            card,
            textvariable=self.live_line_var,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=("#1F3A5F", "#9EC5FF"),
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))

    @staticmethod
    def _stat(parent, col: int, title: str, var: ctk.StringVar) -> None:
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.grid(row=0, column=col, sticky="nsew", padx=6, pady=8)
        ctk.CTkLabel(card, text=title, text_color=("#4d4d4d", "#cfcfcf")).pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkLabel(card, textvariable=var, font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w",
            padx=10,
            pady=(0, 8),
        )

    @staticmethod
    def _entry(parent, row: int, label: str, var: ctk.StringVar, show: str | None = None) -> None:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=6)
        ctk.CTkEntry(parent, textvariable=var, show=show if show else "").grid(
            row=row,
            column=1,
            sticky="ew",
            padx=12,
            pady=6,
        )

    # ---------- infra ----------
    def _on_ui(self, fn: Callable[[], None]) -> None:
        if threading.current_thread() is threading.main_thread():
            fn()
        else:
            self.after(0, fn)

    def _redact_text(self, text: str) -> str:
        redacted = text
        secrets = [
            self.api_token_var.get().strip(),
            self.admin_token_var.get().strip(),
            self.alpaca_key_var.get().strip(),
            self.alpaca_secret_var.get().strip(),
        ]
        for secret in secrets:
            if secret and len(secret) >= 6:
                redacted = redacted.replace(secret, f"{secret[:3]}***{secret[-2:]}")
        return redacted

    def _parse_risk_limits(self) -> tuple[float, int]:
        try:
            max_drawdown_stop_pct = float(self.max_drawdown_stop_var.get().strip())
        except ValueError as exc:
            raise RuntimeError("Max drawdown stop (%) debe ser numerico.") from exc
        if max_drawdown_stop_pct <= 0 or max_drawdown_stop_pct >= 100:
            raise RuntimeError("Max drawdown stop (%) debe estar entre 0 y 100.")

        try:
            max_loop_errors = int(self.max_loop_errors_var.get().strip())
        except ValueError as exc:
            raise RuntimeError("Max errores seguidos debe ser entero.") from exc
        if max_loop_errors <= 0:
            raise RuntimeError("Max errores seguidos debe ser mayor que 0.")
        return (max_drawdown_stop_pct / 100.0, max_loop_errors)

    @staticmethod
    def _normalize_drawdown_fraction(raw_drawdown) -> float:
        try:
            value = float(raw_drawdown)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(value) or value < 0:
            return 0.0
        # Tolerate both conventions from backend: fraction (0.05) or percent (5.0).
        if value > 1.0 and value <= 100.0:
            value = value / 100.0
        return min(value, 1.0)

    def _safe_max_loop_errors(self) -> int:
        try:
            _, max_loop_errors = self._parse_risk_limits()
            return max_loop_errors
        except Exception as exc:  # noqa: BLE001
            self.log(f"WARN [safety] Limite de errores invalido. Usando fallback={DEFAULT_MAX_LOOP_ERRORS}. Detalle: {exc}")
            return DEFAULT_MAX_LOOP_ERRORS

    def _validate_trading_safety(self) -> None:
        alpaca_url = self.alpaca_base_var.get().strip()
        if not alpaca_url:
            raise RuntimeError("Falta ALPACA_BASE_URL.")
        parsed = urllib.parse.urlparse(alpaca_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise RuntimeError("Alpaca Base URL invalida. Debe usar formato https://host")

        is_paper = looks_like_paper_url(alpaca_url)
        allow_live = bool(self.allow_live_var.get())
        if not is_paper and not allow_live:
            raise RuntimeError(
                "Base URL de Alpaca parece LIVE y LIVE esta bloqueado. "
                "Activa 'Permitir LIVE (riesgo alto)' solo si quieres operar real."
            )
        if not is_paper and allow_live:
            if self.live_confirm_var.get().strip() != "YES_LIVE":
                raise RuntimeError(
                    "LIVE requiere confirmacion textual. "
                    "Escribe YES_LIVE en 'Confirm LIVE (YES_LIVE)'."
                )
            self.log("WARN [safety] Modo LIVE habilitado manualmente.")

    def _sync_clients(self) -> None:
        parsed = urllib.parse.urlparse(self.base_url_var.get().strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError("Base URL invalida. Usa formato http://host:puerto")
        self._validate_trading_safety()
        self._parse_risk_limits()

        self.api_client.configure(
            base_url=self.base_url_var.get(),
            api_token=self.api_token_var.get(),
            admin_token=self.admin_token_var.get(),
            actor_id=self.actor_var.get(),
        )
        self.alpaca_client.configure(
            api_key=self.alpaca_key_var.get(),
            secret_key=self.alpaca_secret_var.get(),
            base_url=self.alpaca_base_var.get(),
        )

    def _set_controls_busy(self, busy: bool) -> None:
        def apply() -> None:
            state = "disabled" if busy else "normal"
            for widget in (self.quick_btn, self.step_btn, self.loop_start_btn):
                widget.configure(state=state)
            self.quick_btn.configure(text="Trabajando..." if busy else "Hacerlo todo")

        self._on_ui(apply)

    def _status_level(self, title: str, busy: bool) -> str:
        t = title.lower()
        if "error" in t:
            return "error"
        if busy or "entren" in t or "ejecut" in t or "comprob" in t:
            return "work"
        if "detenido" in t or "esperando" in t:
            return "warn"
        if "ok" in t or "listo" in t or "complet" in t or "activ" in t:
            return "ok"
        return "idle"

    def _apply_status_theme(self, level: str) -> None:
        theme = {
            "idle": {"panel": ("#E8ECF3", "#2A3040"), "title": ("#1E2A3B", "#F1F4FA"), "detail": ("#4A5568", "#C6CFDF"), "bar": ("#4A79FF", "#5D86FF")},
            "work": {"panel": ("#DCEBFF", "#1F314D"), "title": ("#143D73", "#E7F1FF"), "detail": ("#245287", "#C7DCFF"), "bar": ("#1E74FF", "#3E8BFF")},
            "ok": {"panel": ("#DDF5E8", "#1E3A2F"), "title": ("#1D6A42", "#D9FBE9"), "detail": ("#2C6A4B", "#BFECD5"), "bar": ("#20A364", "#2DBA74")},
            "warn": {"panel": ("#FFF0D9", "#4A3824"), "title": ("#915C00", "#FFE5B8"), "detail": ("#8A5B1A", "#FFD79A"), "bar": ("#D99300", "#E3A82D")},
            "error": {"panel": ("#FFE1E1", "#4A2525"), "title": ("#9F2F2F", "#FFD7D7"), "detail": ("#8E3A3A", "#FFBDBD"), "bar": ("#D73A3A", "#EA5757")},
        }[level]
        self.status_box.configure(fg_color=theme["panel"])
        self.status_title_lbl.configure(text_color=theme["title"])
        self.status_detail_lbl.configure(text_color=theme["detail"])
        self.status_progress.configure(progress_color=theme["bar"])

    def set_status(self, title: str, detail: str, busy: bool = False) -> None:
        def apply() -> None:
            level = self._status_level(title, busy)
            badge = {"ok": "[OK]", "work": "[RUN]", "warn": "[WARN]", "error": "[ERR]", "idle": "[IDLE]"}[level]
            self.status_title_var.set(f"{badge} {title}")
            self.status_detail_var.set(detail)
            self._apply_status_theme(level)
            if busy:
                self.status_progress.grid()
                self.status_progress.start()
            else:
                self.status_progress.stop()
                self.status_progress.grid_remove()

        self._on_ui(apply)

    def log(self, text: str) -> None:
        safe_text = self._redact_text(text)

        def append(box: ctk.CTkTextbox, line: str, max_lines: int, keep_lines: int) -> None:
            box.configure(state="normal")
            box.insert("end", line)
            try:
                total = int(float(box.index("end-1c").split(".")[0]))
                if total > max_lines:
                    box.delete("1.0", f"{total - keep_lines}.0")
            except ValueError:
                pass
            box.see("end")
            box.configure(state="disabled")

        def write() -> None:
            now = time.strftime("%H:%M:%S")
            line = f"[{now}] {safe_text}\n"
            self.live_line_var.set(line.strip())
            append(self.realtime_box, line, max_lines=45, keep_lines=30)
            append(self.log_box, line, max_lines=450, keep_lines=320)
            self.audit_logger.info(safe_text)

        self._on_ui(write)

    def _run_job(self, job_name: str, detail: str, fn: Callable[[], None], busy_controls: bool = False) -> bool:
        try:
            self._sync_clients()
        except Exception as exc:  # noqa: BLE001
            self.set_status("Error", str(exc), busy=False)
            self.log(f"ERROR: {exc}")
            return False

        if not self._job_lock.acquire(blocking=False):
            self.log("Operacion ignorada: ya hay una tarea en curso.")
            return False
        if busy_controls:
            self._set_controls_busy(True)

        def worker() -> None:
            try:
                self.set_status(job_name, detail, busy=True)
                fn()
            except Exception as exc:  # noqa: BLE001
                self.set_status("Error", str(exc), busy=False)
                self.log(f"ERROR: {exc}")
                self.audit_logger.exception("Job failed: %s", self._redact_text(job_name))
            finally:
                self._on_ui(self._refresh_overview)
                if busy_controls:
                    self._set_controls_busy(False)
                self._job_lock.release()

        threading.Thread(target=worker, daemon=True).start()
        return True

    # ---------- business ----------
    def _selected_ticker(self) -> str:
        return self.ticker_var.get().strip().upper()

    def _ensure_model_for_current_ticker(self) -> None:
        ticker = self._selected_ticker()
        if not ticker:
            raise RuntimeError("Ticker vacio.")
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", ticker):
            raise RuntimeError("Ticker invalido. Ejemplo valido: NVDA")
        if self.runtime_state.run_id and self.runtime_state.current_ticker == ticker:
            return
        if self.runtime_state.run_id and self.runtime_state.current_ticker != ticker:
            self.log(
                f"Cambio de ticker detectado ({self.runtime_state.current_ticker} -> {ticker}). "
                "Reentrenando."
            )
        self._set_runtime_run("", "")
        self.metrics.reset()
        self._update_metrics_ui()
        self._train()

    def _refresh_overview(self) -> None:
        if not self.runtime_state.run_id:
            self.next_step_var.set("Entrenar")
            self.train_var.set("Vacio")
            self.bot_var.set("Parado")
            self.rt_var.set("Sin sesion")
            return
        if self.runtime_state.run_id and not self.runtime_state.session_id:
            self.next_step_var.set("Arrancar bot")
            self.train_var.set("Listo")
            self.bot_var.set("Esperando")
            self.rt_var.set("Sin sesion")
            return
        self.next_step_var.set("Vigilar")
        self.train_var.set("Listo")
        self.bot_var.set("Activo" if self.runtime_state.loop_running else "En pausa")
        self.rt_var.set(self.runtime_state.session_id[:12])

    def _train(self) -> None:
        ticker = self._selected_ticker()
        if not ticker:
            raise RuntimeError("Ticker vacio.")
        try:
            periods = int(self.periods_var.get().strip())
        except ValueError as exc:
            raise RuntimeError("Periodos debe ser entero.") from exc
        if periods <= 0:
            raise RuntimeError("Periodos debe ser mayor que 0.")
        profile = self.profile_var.get().strip()
        if profile not in {"fast", "standard", "deep"}:
            raise RuntimeError("Perfil invalido. Usa fast, standard o deep.")
        self.log(f"Entrenando {ticker} ({profile}, {periods})...")
        result = self.api_client.train_sequence(ticker, profile, periods)
        run_id = str(result.get("run_id", "")).strip()
        if not run_id:
            raise RuntimeError("No se recibio run_id en entrenamiento.")
        self._set_runtime_run(run_id, ticker)
        self.metrics.reset()
        self._update_metrics_ui()
        self.set_status("Entrenado", f"run_id={run_id}", busy=False)
        self.log(f"Entrenamiento terminado. run_id={run_id}")

    def _validate_run_ready(self, caller: str) -> None:
        if not self.runtime_state.run_id:
            raise RuntimeError(
                f"No hay run entrenado. Ejecuta entrenamiento antes de {caller}. "
                "Ticker actual sin modelo asociado."
            )

    def _try_reuse_existing_session(self) -> bool:
        if not self.runtime_state.session_id:
            return False
        sid = self.runtime_state.session_id
        try:
            self.api_client.runtime_summary(sid)
            self._log_ctx("INFO", "_ensure_session", f"Reutilizando session_id existente: {sid}")
            return True
        except Exception as exc:  # noqa: BLE001
            self._log_ctx(
                "WARN",
                "_ensure_session",
                f"Session previa invalida ({sid}). Se iniciara una nueva. Detalle: {exc}",
            )
            self._clear_runtime_session()
            return False

    def _start_paper_session(self) -> str:
        run_id = self.runtime_state.run_id
        self._log_ctx("INFO", "_ensure_session", f"Promoviendo run={run_id} a paper.")
        self.api_client.promote_paper(run_id)
        started = self.api_client.start_paper(run_id)
        sid = str(started.get("session_id", "")).strip()
        if sid:
            return sid
        self._log_ctx(
            "WARN",
            "_ensure_session",
            f"start-paper sin session_id para run={run_id}. Reintentando 1 vez.",
        )
        started_retry = self.api_client.start_paper(run_id)
        sid_retry = str(started_retry.get("session_id", "")).strip()
        if sid_retry:
            return sid_retry
        raise RuntimeError(
            "No se pudo crear session_id tras iniciar paper. "
            f"run_id={run_id}. Revisa backend/runtime y tokens."
        )

    def _ensure_session(self) -> None:
        self._validate_run_ready("arrancar sesion paper")
        if self._try_reuse_existing_session():
            return
        sid = self._start_paper_session()
        self._set_runtime_session(sid)
        self._log_ctx("INFO", "_ensure_session", f"Bot paper iniciado. session_id={sid}")

    def _load_and_validate_alpaca_status(self) -> dict:
        status = self.api_client.alpaca_paper_status()
        if "configured" not in status or "connected" not in status:
            raise RuntimeError(
                "Respuesta incompleta de /alpaca-paper-status: faltan campos "
                "'configured' y/o 'connected'."
            )
        if not status.get("configured"):
            raise RuntimeError("Alpaca no esta configurado en backend.")
        if not status.get("connected"):
            raise RuntimeError(
                "Alpaca sin conexion en backend. "
                f"Detalle: {status.get('error', 'desconocido')}. "
                "Verifica credenciales y conectividad."
            )
        return status

    def _trigger_emergency_stop(self, reason: str) -> None:
        self.runtime_state.loop_running = False
        self._loop_token += 1
        self.set_status("Loop detenido por seguridad", reason, busy=False)
        self.log(f"WARN [safety] {reason}")
        self._on_ui(self._refresh_overview)

    def _alpaca_step(self) -> None:
        self._validate_run_ready("ejecutar alpaca step")
        status = self._load_and_validate_alpaca_status()
        request_id = f"step-{uuid4().hex[:12]}"
        self.runtime_state.last_request_id = request_id
        result = self.api_client.alpaca_paper_step(
            self.runtime_state.run_id,
            self.runtime_state.session_id or None,
            request_id=request_id,
        )
        sid = str(result.get("session_id", "")).strip() or self.runtime_state.session_id
        if not sid:
            raise RuntimeError(
                "No se recibio session_id tras alpaca step y no habia sesion previa. "
                f"run_id={self.runtime_state.run_id}"
            )
        self._set_runtime_session(sid)

        decision = result.get("decision", {})
        broker = result.get("broker", {})
        self._log_ctx(
            "INFO",
            "_alpaca_step",
            "Alpaca step -> "
            f"market_price={result.get('market_price', '-')} "
            f"model_action={decision.get('action', 'hold')} "
            f"confidence={decision.get('confidence', '-')} "
            f"broker_action={broker.get('action', 'hold')} "
            f"qty={broker.get('qty', 0)} "
            f"executed={broker.get('executed', False)} "
            f"configured={status.get('configured')} connected={status.get('connected')}"
        )
        summary = self.api_client.runtime_summary(sid)
        equity = summary.get("equity", "-")
        drawdown = summary.get("drawdown_pct", 0)
        self.metrics.update(equity)
        self._update_metrics_ui()
        max_drawdown_stop, _ = self._parse_risk_limits()
        drawdown_float = self._normalize_drawdown_fraction(drawdown)
        if drawdown_float >= max_drawdown_stop:
            self._trigger_emergency_stop(
                f"Drawdown {drawdown_float * 100:.2f}% >= limite {max_drawdown_stop * 100:.2f}%."
            )
            return
        self.set_status("Paso completado", f"equity={equity} drawdown={drawdown}", busy=False)
        self._log_ctx("INFO", "_alpaca_step", f"Runtime -> equity={equity} drawdown_pct={drawdown}")

    # ---------- actions ----------
    def on_health(self) -> None:
        def work() -> None:
            health = self.api_client.health()
            self.log(f"API OK: {health.get('status', 'ok')}")
            broker = self.api_client.alpaca_paper_status()
            self.log(
                "Broker Alpaca -> "
                f"configured={broker.get('configured')} "
                f"connected={broker.get('connected')} "
                f"mode={broker.get('mode')}"
            )
            self.set_status("Conexion OK", "API y broker verificados.", busy=False)

        self._run_job("Comprobando", "Verificando API y broker...", work)

    def on_alpaca_direct(self) -> None:
        def work() -> None:
            account = self.alpaca_client.account()
            self.log(
                "Alpaca directo -> "
                f"status={account.get('status', '-')} "
                f"equity={account.get('equity', '-')} "
                f"buying_power={account.get('buying_power', '-')}"
            )
            self.set_status("Alpaca OK", "Conexion directa validada.", busy=False)

        self._run_job("Comprobando Alpaca", "Llamando /v2/account...", work)

    def on_quick_start(self) -> None:
        def work() -> None:
            self._ensure_model_for_current_ticker()
            self._ensure_session()
            self._alpaca_step()
            self.set_status("Listo", "Flujo completo terminado.", busy=False)
            self.log("Flujo completo terminado.")

        self._run_job("Flujo completo", "Entrenar -> Paper -> Alpaca step", work, busy_controls=True)

    def on_single_step(self) -> None:
        def work() -> None:
            self._ensure_session()
            self._alpaca_step()

        self._run_job("Paso manual", "Ejecutando 1 paso real...", work)

    def _loop_tick(self) -> None:
        if not self.runtime_state.loop_running:
            return
        expected_token = self._loop_token

        def schedule_next(delay_ms: int = LOOP_INTERVAL_MS) -> None:
            if self.runtime_state.loop_running and expected_token == self._loop_token:
                self.after(delay_ms, self._loop_tick)

        def work() -> None:
            if expected_token != self._loop_token:
                return
            try:
                self._ensure_session()
                self._alpaca_step()
                self.runtime_state.loop_error_count = 0
                schedule_next(LOOP_INTERVAL_MS)
            except Exception as exc:  # noqa: BLE001
                self.runtime_state.loop_error_count += 1
                max_loop_errors = self._safe_max_loop_errors()
                self._log_ctx(
                    "ERROR",
                    "_loop_tick",
                    (
                        f"Fallo paso de loop ({self.runtime_state.loop_error_count}/{max_loop_errors}). "
                        f"Reintento en {LOOP_RETRY_MS}ms: {exc}"
                    ),
                )
                if self.runtime_state.loop_error_count >= max_loop_errors:
                    self._trigger_emergency_stop(
                        f"Errores consecutivos en loop: {self.runtime_state.loop_error_count}."
                    )
                    return
                schedule_next(LOOP_RETRY_MS)
                raise

        started = self._run_job("Loop activo", "Ejecutando pasos cada 4 segundos...", work)
        if not started:
            schedule_next(LOOP_RETRY_MS)

    def on_start_loop(self) -> None:
        try:
            self._sync_clients()
        except Exception as exc:  # noqa: BLE001
            self.set_status("Error", str(exc), busy=False)
            self.log(f"ERROR: {exc}")
            return
        if self.runtime_state.loop_running:
            self.log("El loop ya esta activo.")
            return
        self.runtime_state.loop_running = True
        self.runtime_state.loop_error_count = 0
        self._loop_token += 1
        self.set_status("Loop activo", "Ejecutando pasos cada 4 segundos...", busy=True)
        self.log("Loop iniciado.")
        self._refresh_overview()
        self._loop_tick()

    def on_stop_loop(self) -> None:
        self.runtime_state.loop_running = False
        self._loop_token += 1
        self.set_status("Loop detenido", "No se estan ejecutando pasos.", busy=False)
        self.log("Loop detenido.")
        self._refresh_overview()

    def on_open_web(self) -> None:
        url = self.base_url_var.get().strip() or "http://127.0.0.1:8080"
        webbrowser.open(url)
        self.log(f"Abriendo consola web: {url}")

    # ---------- ultra simple ----------
    def on_ultra_connect(self) -> None:
        self.on_health()

    def on_ultra_start(self) -> None:
        ticker = self.ultra_ticker_var.get().strip().upper()
        if ticker:
            self.ticker_var.set(ticker)

        def work() -> None:
            self._ensure_model_for_current_ticker()
            self._ensure_session()
            self._alpaca_step()
            if not self.runtime_state.loop_running:
                self.runtime_state.loop_running = True
                self.runtime_state.loop_error_count = 0
                self._loop_token += 1
                self._on_ui(lambda: self.after(LOOP_INTERVAL_MS, self._loop_tick))
            self.set_status("Loop activo", "Modo ultra simple ejecutando.", busy=True)
            self.log("Ultra simple: bot arrancado y loop activo.")

        self._run_job("Ultra simple", "Conectar, entrenar y arrancar loop...", work, busy_controls=True)

    def on_ultra_stop(self) -> None:
        self.on_stop_loop()

    def on_close(self) -> None:
        self.runtime_state.loop_running = False
        self._loop_token += 1
        self.log("Cerrando aplicacion.")
        self.destroy()

    def _update_metrics_ui(self) -> None:
        values = self.metrics.summary()

        def apply() -> None:
            self.metric_return_var.set(f"{values['cum_return'] * 100:.2f}%")
            self.metric_dd_var.set(f"{values['max_drawdown'] * 100:.2f}%")
            self.metric_vol_var.set(f"{values['step_volatility']:.6f}")
            self.metric_sharpe_var.set(f"{values['step_sharpe_like']:.4f}")

        self._on_ui(apply)


def main() -> None:
    app = SimpleTradeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
