"""Command-line tools: ``flask --app run <command>``."""

from pathlib import Path

import click

from .db import get_db, init_schema


def register_cli(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Create the database tables (safe to run more than once)."""
        init_schema(get_db())
        click.echo(f"Database ready at {app.config['DATABASE']}")

    @app.cli.command("seed-demo")
    @click.option("--force", is_flag=True, help="Add sample data even if the database already has data.")
    def seed_demo_command(force):
        """Fill the database with 12 months of realistic sample data."""
        from .demo import seed_demo
        from .services.settings import has_any_data
        if has_any_data() and not force:
            raise click.ClickException("The database already has data. Use --force to add sample data anyway.")
        seed_demo()
        click.echo("Sample data added.")

    @app.cli.command("backup")
    @click.argument("destination", required=False)
    def backup_command(destination):
        """Write a backup copy of the database (default: instance/backups/)."""
        from .services.settings import backup_filename, backup_to
        dest = Path(destination) if destination else Path(app.config["BACKUP_DIR"]) / backup_filename()
        dest.parent.mkdir(parents=True, exist_ok=True)
        backup_to(dest)
        click.echo(f"Backup written to {dest}")

    @app.cli.command("import-legacy")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False))
    def import_legacy_command(path):
        """Import data from the original version's database/finance.db."""
        from .legacy import import_legacy
        counts = import_legacy(path)
        click.echo(", ".join(f"{v} {k}" for k, v in counts.items()) + " imported.")
