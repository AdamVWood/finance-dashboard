"""Personal Budget & Investment Dashboard - Flask application factory."""

import logging
import os
import secrets
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for

from . import db
from .utils import PERIODS, cents_to_input, format_money, today

BASE_DIR = Path(__file__).resolve().parent.parent


def _secret_key(instance_path):
    """Use SECRET_KEY from the environment, else a random key saved on first run."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    key_file = Path(instance_path) / "secret_key"
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32), encoding="utf-8")
    return key_file.read_text(encoding="utf-8").strip()


def create_app(test_config=None):
    app = Flask(__name__, instance_path=str(BASE_DIR / "instance"), instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.update(
        DATABASE=os.environ.get("FINANCE_DB", str(Path(app.instance_path) / "finance.db")),
        BACKUP_DIR=str(Path(app.instance_path) / "backups"),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,  # uploads (CSV / backups) up to 20 MB
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = _secret_key(app.instance_path)

    _configure_logging(app)
    db.init_app(app)
    _register_security(app)
    _register_template_helpers(app)
    _register_blueprints(app)
    _register_errors(app)

    from .cli import register_cli
    register_cli(app)
    return app


def _configure_logging(app):
    if app.testing:
        return
    handler = RotatingFileHandler(Path(app.instance_path) / "app.log", maxBytes=1_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.setLevel(logging.WARNING)
    app.logger.addHandler(handler)


def _register_security(app):
    @app.before_request
    def csrf_protect():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_urlsafe(32)
        if request.method == "POST" and not app.config.get("CSRF_DISABLED"):
            token = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
            if not token or not secrets.compare_digest(token, session["_csrf"]):
                abort(400, description="Your session expired or the form was submitted twice. Please try again.")

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'",
        )
        return response


def _register_template_helpers(app):
    from .services import settings as settings_svc

    @app.before_request
    def load_settings():
        g.settings = settings_svc.get_all()

    @app.template_filter("money")
    def money_filter(cents, sign=False, decimals=True):
        symbol = g.get("settings", {}).get("currency_symbol", "$")
        return format_money(cents, symbol, show_sign=sign, decimals=decimals)

    @app.template_filter("input_money")
    def input_money(cents):
        return cents_to_input(cents)

    @app.template_filter("pct")
    def pct_filter(value, decimals=0, sign=False):
        if value is None:
            return "—"
        text = f"{abs(value):.{decimals}f}%"
        if value < 0:
            return "−" + text
        return ("+" + text) if sign and value > 0 else text

    @app.template_filter("nicedate")
    def nicedate(value, fmt="%d %b %Y"):
        if not value:
            return "—"
        from .utils import parse_date
        try:
            return parse_date(str(value)[:10]).strftime(fmt).lstrip("0")
        except ValueError:
            return value

    @app.template_filter("qty")
    def qty(value):
        return f"{value:,.8f}".rstrip("0").rstrip(".") if value is not None else "—"

    @app.context_processor
    def inject_globals():
        def url_with(**changes):
            args = request.args.to_dict()
            args.update({k: v for k, v in changes.items()})
            args = {k: v for k, v in args.items() if v not in (None, "")}
            return url_for(request.endpoint, **(request.view_args or {}), **args)

        return {
            "csrf_token": session.get("_csrf", ""),
            "today_iso": today().isoformat(),
            "settings": g.get("settings", {}),
            "PERIODS": PERIODS,
            "url_with": url_with,
        }


def _register_blueprints(app):
    from .views import (accounts, budgets, categories, dashboard, goals, investments, recurring, reports,
                        settings, transactions)

    for module in (dashboard, transactions, accounts, categories, budgets, goals, investments, recurring,
                   reports, settings):
        app.register_blueprint(module.bp)


def _register_errors(app):
    @app.errorhandler(400)
    def bad_request(err):
        if request.method == "POST" and "session expired" in str(err.description):
            flash(err.description, "error")
            return redirect(request.referrer or url_for("dashboard.index"))
        return render_template("error.html", code=400, message=err.description), 400

    @app.errorhandler(404)
    def not_found(_err):
        return render_template("error.html", code=404, message="That page or record doesn't exist."), 404

    @app.errorhandler(413)
    def too_large(_err):
        flash("That file is too large (maximum 20 MB).", "error")
        return redirect(request.referrer or url_for("dashboard.index"))

    @app.errorhandler(500)
    def server_error(err):
        app.logger.exception("Unhandled error: %s", err)
        return render_template("error.html", code=500,
                               message="Something went wrong. The error has been logged."), 500
