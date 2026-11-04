"""HTTP routes, one blueprint per area of the app."""

from flask import flash, redirect, request, url_for


def flash_validation(exc):
    """Show the errors of a ValidationError as flash messages."""
    for key, message in exc.errors.items():
        if key == "rows":
            continue
        flash(message, "error")


def back(default_endpoint, **values):
    """Redirect to a safe ``next`` URL from the form, or to a default page."""
    target = request.form.get("next") or request.args.get("next")
    if target and target.startswith("/") and not target.startswith("//"):
        return redirect(target)
    return redirect(url_for(default_endpoint, **values))
