import tempfile
from pathlib import Path

from flask import Blueprint, after_this_request, flash, redirect, render_template, request, send_file, url_for

from ..services import settings as settings_svc
from ..utils import ValidationError
from . import flash_validation

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            settings_svc.save(request.form)
            flash("Settings saved.", "success")
            return redirect(url_for(".index"))
        except ValidationError as exc:
            flash_validation(exc)
    return render_template(
        "settings/index.html",
        current=settings_svc.get_all(),
        currencies=settings_svc.CURRENCIES,
        has_data=settings_svc.has_any_data(),
        safety_backups=settings_svc.list_safety_backups(),
    )


@bp.route("/backup")
def backup():
    path = Path(settings_svc.make_backup_file())

    @after_this_request
    def cleanup(response):
        try:
            path.unlink(missing_ok=True)
            path.parent.rmdir()
        except OSError:
            pass
        return response

    return send_file(path, as_attachment=True, download_name=path.name, mimetype="application/octet-stream")


@bp.route("/restore", methods=["POST"])
def restore():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        flash("Choose a backup file to restore.", "error")
        return redirect(url_for(".index"))
    if request.form.get("confirm") != "RESTORE":
        flash("Type RESTORE to confirm - restoring replaces all current data.", "error")
        return redirect(url_for(".index"))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "upload.db"
        upload.save(path)
        try:
            settings_svc.restore_from(str(path))
        except ValidationError as exc:
            flash_validation(exc)
            return redirect(url_for(".index"))
    flash("Backup restored. A copy of your previous data was saved in instance/backups.", "success")
    return redirect(url_for("dashboard.index"))


@bp.route("/demo", methods=["POST"])
def load_demo():
    from ..demo import seed_demo
    if settings_svc.has_any_data():
        flash("Sample data can only be loaded into an empty database.", "error")
        return redirect(url_for(".index"))
    seed_demo()
    flash("Sample data loaded. Use Settings → Erase all data when you're ready to start for real.", "success")
    return redirect(url_for("dashboard.index"))


@bp.route("/reset", methods=["POST"])
def reset():
    if request.form.get("confirm") != "DELETE":
        flash("Type DELETE to confirm erasing all data.", "error")
        return redirect(url_for(".index"))
    settings_svc.reset_all()
    flash("All data erased. A safety backup was saved in instance/backups.", "success")
    return redirect(url_for("dashboard.index"))
