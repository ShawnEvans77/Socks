"""Flask front end for Socks. Local use only: it listens on 127.0.0.1."""

from __future__ import annotations

import datetime as dt
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlsplit

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from src.constants import filenames, guide
from src.constants.schedule import WEEKDAYS
from src.objects.pay_table import PayTable
from src.objects.schedule_table import ScheduleTable
from src.utils.database import (
    DATE_FORMAT,
    DatabaseError,
    SocksDatabase,
    ValidationError,
    parse_budget,
    parse_emplid,
    parse_pay_period,
    parse_year,
)

from . import services

ROOT = Path(__file__).resolve().parent.parent
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
_FIRST_PERIOD = guide.PeriodLength.first_period.value
_LAST_PERIOD = guide.PeriodLength.last_period.value
_DEFAULT_BUDGET = guide.LearningCenter.default_budget.value
_DEPT_PREFIX = guide.LearningCenter.lc_dept_prefix.value


def create_app(
    database_path: str | Path | None = None,
    template_pdf: str | Path | None = None,
    output_dir: str | Path | None = None,
    backup_path: str | Path | None = None,
) -> Flask:
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    app.config["DB_PATH"] = str(
        database_path
        or ROOT / filenames.asset_folder / filenames.database_folder / filenames.database_name
    )
    app.config["TEMPLATE_PDF"] = Path(
        template_pdf
        or ROOT / filenames.asset_folder / filenames.pdf_input_folder / filenames.starting_pdf
    )
    app.config["OUTPUT_DIR"] = Path(output_dir or ROOT / filenames.output_folder)
    app.config["BACKUP_DB_PATH"] = Path(
        backup_path
        or ROOT / filenames.asset_folder / filenames.database_folder
        / filenames.pay_period_backup_name
    )

    SocksDatabase(app.config["DB_PATH"]).ensure_schema()

    def get_db() -> SocksDatabase:
        return SocksDatabase(app.config["DB_PATH"])

    def load_pay_table(db: SocksDatabase) -> PayTable:
        return PayTable(db, ensure_schema=False)

    # ── Safety: this app is for this computer only ───────────────────────────

    @app.before_request
    def local_requests_only():
        if urlsplit(f"//{request.host}").hostname not in _LOCAL_HOSTS:
            abort(403)
        if request.method == "POST":
            origin = request.headers.get("Origin")
            if origin and urlsplit(origin).netloc != request.host:
                abort(403)

    @app.after_request
    def no_caching(response):
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template(
            "message.html", title="Not allowed",
            message="Socks only answers requests from this computer.",
        ), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            "message.html", title="Page not found",
            message="That page doesn't exist. Head back home and try again.",
        ), 404

    @app.errorhandler(DatabaseError)
    def database_problem(error):
        return render_template(
            "message.html", title="Something went wrong", message=str(error),
        ), 400

    @app.context_processor
    def shared_values():
        return {
            "weekdays": WEEKDAYS,
            "dept_prefix": _DEPT_PREFIX,
            "first_period": _FIRST_PERIOD,
            "last_period": _LAST_PERIOD,
        }

    app.jinja_env.filters["shifts"] = services.format_shifts
    app.jinja_env.filters["date_input"] = services.date_to_input

    # ── Home ─────────────────────────────────────────────────────────────────

    def saved_timesheets() -> list[dict]:
        folder = app.config["OUTPUT_DIR"]
        if not folder.is_dir():
            return []
        files = sorted(
            (path for path in folder.glob("*.pdf") if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return [
            {
                "name": path.name,
                "saved": dt.datetime.fromtimestamp(path.stat().st_mtime).strftime(
                    "%m/%d/%Y %I:%M %p"
                ),
                "version": int(path.stat().st_mtime),
            }
            for path in files
        ]

    @app.get("/")
    def home():
        db = get_db()
        pay_table = load_pay_table(db)
        current = services.current_pay_period(pay_table)
        return render_template(
            "home.html",
            employees=db.list_employees(),
            has_periods=bool(pay_table.get_pay_dict()),
            current=current,
            current_range=_period_range(pay_table, current) if current else "",
            timesheets=saved_timesheets(),
        )

    # ── Timesheet ────────────────────────────────────────────────────────────

    def _period_range(pay_table: PayTable, pay_period: int) -> str:
        start, end = pay_table.get_pay_dict()[int(pay_period)]
        return f"{start.strftime(DATE_FORMAT)} → {end.strftime(DATE_FORMAT)}"

    def _period_options(pay_table: PayTable) -> list[tuple[int, str]]:
        return [
            (number, _period_range(pay_table, number))
            for number in sorted(pay_table.get_pay_dict())
        ]

    def _valid_period(pay_table: PayTable, raw: str | None) -> int | None:
        raw = (raw or "").strip()
        if raw.isascii() and raw.isdigit() and pay_table.has_pay_period(raw):
            return int(raw)
        return None

    def _render_timesheet(employee, pay_table, pay_period, days, status=200, **extra):
        current = services.current_pay_period(pay_table)
        return render_template(
            "timesheet.html",
            employee=employee,
            period=pay_period,
            period_range=_period_range(pay_table, pay_period) if pay_period else "",
            period_options=_period_options(pay_table),
            current=current,
            days=days,
            weeks=[days[:7], days[7:]] if days else [],
            **extra,
        ), status

    @app.get("/timesheet")
    def timesheet():
        db = get_db()
        employee = services.find_employee(db.list_employees(), request.args.get("employee", ""))
        if employee is None:
            flash("Pick an employee to start a timesheet.", "error")
            return redirect(url_for("home"))

        pay_table = load_pay_table(db)
        raw_period = request.args.get("period")
        if raw_period:
            pay_period = _valid_period(pay_table, raw_period)
            if pay_period is None:
                flash(f"Pay period {raw_period} hasn't been set up yet.", "error")
        else:
            pay_period = services.current_pay_period(pay_table)

        days = (
            services.build_days(pay_table, employee.schedule, pay_period)
            if pay_period is not None else []
        )
        return _render_timesheet(employee, pay_table, pay_period, days)

    @app.post("/timesheet")
    def make_timesheet():
        db = get_db()
        employee = services.find_employee(db.list_employees(), request.form.get("employee", ""))
        if employee is None:
            flash("That employee no longer exists.", "error")
            return redirect(url_for("home"))

        pay_table = load_pay_table(db)
        pay_period = _valid_period(pay_table, request.form.get("period"))
        if pay_period is None:
            flash("That pay period hasn't been set up yet.", "error")
            return redirect(url_for("timesheet", employee=employee.name))

        schedule_table = ScheduleTable(db, ensure_schema=False)
        emplid_error = ""
        emplid_value = request.form.get("emplid", "").strip()
        if not employee.emplid:
            try:
                schedule_table.set_emplid(employee.name, emplid_value)
            except DatabaseError as exc:
                emplid_error = str(exc)
            else:
                employee = services.find_employee(db.list_employees(), employee.name)

        days = services.build_days(pay_table, employee.schedule, pay_period)
        changes, ok = services.apply_form(days, request.form)
        if emplid_error or not ok:
            return _render_timesheet(
                employee, pay_table, pay_period, days, status=422,
                emplid_error=emplid_error, emplid_value=emplid_value,
                problem="Fix the highlighted problem, then try again.",
            )

        file_name = services.timesheet_file_name(employee.name, pay_period)
        try:
            pdf = services.generate_timesheet(
                app.config["TEMPLATE_PDF"], employee, pay_period,
                pay_table, schedule_table, changes,
            )
        except (ValueError, DatabaseError, OSError) as exc:
            return _render_timesheet(
                employee, pay_table, pay_period, days, status=500,
                problem=f"The timesheet could not be made: {exc}",
            )

        try:
            app.config["OUTPUT_DIR"].mkdir(parents=True, exist_ok=True)
            (app.config["OUTPUT_DIR"] / file_name).write_bytes(pdf)
        except OSError:
            return _render_timesheet(
                employee, pay_table, pay_period, days, status=500,
                problem=(
                    f"Couldn't save {file_name}. If it's open in another program, "
                    "close it and try again."
                ),
            )

        return render_template(
            "result.html",
            employee=employee,
            period=pay_period,
            period_range=_period_range(pay_table, pay_period),
            weeks=[days[:7], days[7:]],
            summary=services.summarize(days, changes),
            file_name=file_name,
            version=int(time.time()),
            due_date=pay_table.due_date_string(pay_period),
            pay_date=pay_table.pay_date_string(pay_period),
        )

    @app.get("/timesheets/<path:file_name>")
    def timesheet_file(file_name: str):
        return send_from_directory(
            app.config["OUTPUT_DIR"], file_name,
            as_attachment=request.args.get("download") == "1", max_age=0,
        )

    @app.post("/timesheets/delete")
    def delete_timesheet():
        file_name = request.form.get("file_name", "")
        # Only delete a PDF that is listed directly in the output folder, so a
        # crafted name can never reach anything outside it.
        saved = {sheet["name"] for sheet in saved_timesheets()}
        if file_name not in saved:
            flash("That timesheet doesn't exist anymore.", "error")
            return redirect(url_for("home"))
        try:
            (app.config["OUTPUT_DIR"] / file_name).unlink()
        except OSError:
            flash(
                f"Couldn't delete {file_name}. If it's open in another program, "
                "close it and try again.",
                "error",
            )
        else:
            flash(f"Deleted {file_name}.", "success")
        return redirect(url_for("home"))

    # ── Employees ────────────────────────────────────────────────────────────

    def _rows_from_form(form) -> list[list[str]]:
        return [
            [(form.get(f"d{weekday}_{key}") or "").strip() for key in ("s1", "e1", "s2", "e2")]
            for weekday in range(len(WEEKDAYS))
        ]

    def _rows_from_schedule(schedule) -> list[list[str]]:
        rows = []
        for segments in schedule:
            times = [services.time_to_input(value) for segment in segments for value in segment]
            rows.append((times + ["", "", "", ""])[:4])
        return rows

    def _parse_schedule(rows) -> tuple[list, dict[int, str]]:
        schedule, errors = [], {}
        for weekday, row in enumerate(rows):
            try:
                schedule.append(services.parse_intervals(*row))
            except ValidationError as exc:
                schedule.append(())
                errors[weekday] = str(exc)
        return schedule, errors

    @app.get("/employees")
    def employees():
        return render_template("employees.html", employees=get_db().list_employees())

    def _render_employee_form(status=200, **context):
        context.setdefault("errors", {})
        context.setdefault("day_errors", {})
        return render_template("employee_form.html", **context), status

    @app.get("/employees/new")
    def new_employee():
        return _render_employee_form(
            employee=None,
            values={"first": "", "last": "", "emplid": "", "budget": str(_DEFAULT_BUDGET)},
            rows=_rows_from_schedule([()] * len(WEEKDAYS)),
        )

    @app.post("/employees/new")
    def create_employee():
        db = get_db()
        existing = db.list_employees()
        values = {
            key: " ".join(request.form.get(key, "").split())
            for key in ("first", "last", "emplid", "budget")
        }
        rows = _rows_from_form(request.form)
        errors = {}

        name = f"{values['first']} {values['last']}".strip()
        if not values["first"] or not values["last"]:
            errors["name"] = "Enter both a first and last name."
        elif services.find_employee(existing, name):
            errors["name"] = f"An employee named {name} already exists."

        emplid = None
        try:
            emplid = parse_emplid(values["emplid"])
            if any(employee.emplid == emplid for employee in existing):
                errors["emplid"] = f"EMPLID {emplid} is already assigned to another employee."
        except ValidationError as exc:
            errors["emplid"] = str(exc)

        budget = None
        try:
            budget = parse_budget(values["budget"])
        except ValidationError as exc:
            errors["budget"] = str(exc)

        schedule, day_errors = _parse_schedule(rows)

        if not errors and not day_errors:
            try:
                employee = db.create_employee(name, schedule, emplid, budget)
            except DatabaseError as exc:
                errors["name"] = str(exc)
            else:
                flash(f"{employee.name} was added.", "success")
                return redirect(url_for("employees"))

        return _render_employee_form(
            status=422, employee=None, values=values, rows=rows,
            errors=errors, day_errors=day_errors,
        )

    @app.get("/employees/edit")
    def edit_employee():
        employee = services.find_employee(
            get_db().list_employees(), request.args.get("name", "")
        )
        if employee is None:
            flash("That employee doesn't exist.", "error")
            return redirect(url_for("employees"))
        return _render_employee_form(
            employee=employee,
            values={"emplid": employee.emplid or "", "budget": str(employee.budget)},
            rows=_rows_from_schedule(employee.schedule),
        )

    @app.post("/employees/edit")
    def update_employee():
        db = get_db()
        everyone = db.list_employees()
        employee = services.find_employee(everyone, request.form.get("name", ""))
        if employee is None:
            flash("That employee doesn't exist.", "error")
            return redirect(url_for("employees"))

        values = {
            key: request.form.get(key, "").strip() for key in ("emplid", "budget")
        }
        rows = _rows_from_form(request.form)
        errors = {}

        emplid = employee.emplid
        if values["emplid"] or employee.emplid:
            try:
                emplid = parse_emplid(values["emplid"])
                if any(
                    other.emplid == emplid for other in everyone if other is not employee
                ):
                    errors["emplid"] = (
                        f"EMPLID {emplid} is already assigned to another employee."
                    )
            except ValidationError as exc:
                errors["emplid"] = str(exc)

        budget = employee.budget
        try:
            budget = parse_budget(values["budget"])
        except ValidationError as exc:
            errors["budget"] = str(exc)

        schedule, day_errors = _parse_schedule(rows)

        if not errors and not day_errors:
            try:
                if emplid != employee.emplid:
                    db.set_employee_emplid(employee.name, emplid)
                if budget != employee.budget:
                    db.set_employee_budget(employee.name, budget)
                for weekday, segments in enumerate(schedule):
                    if tuple(segments) != tuple(employee.schedule[weekday]):
                        db.set_employee_schedule(employee.name, weekday, segments)
            except DatabaseError as exc:
                errors["emplid"] = str(exc)
            else:
                flash(f"{employee.name} was updated.", "success")
                return redirect(url_for("employees"))

        return _render_employee_form(
            status=422, employee=employee, values=values, rows=rows,
            errors=errors, day_errors=day_errors,
        )

    # ── Pay periods ──────────────────────────────────────────────────────────

    def _pay_period_years(db: SocksDatabase, periods) -> list[str]:
        years = sorted({p.start_date[-4:] for p in periods} | {p.end_date[-4:] for p in periods})
        return [year for year in years if db.count_pay_periods_in_year(year) > 0]

    def backup_pay_periods() -> list:
        """The saved standard pay periods. The app only ever reads this file."""
        path = app.config["BACKUP_DB_PATH"]
        if not path.is_file():  # never let sqlite create an empty one
            return []
        try:
            return SocksDatabase(str(path)).list_pay_periods()
        except sqlite3.Error:
            return []

    def _render_pay_periods(db, values=None, error="", status=200):
        periods = db.list_pay_periods()
        backup = backup_pay_periods()
        # Same rule as SocksDatabase.restore_pay_periods: number and start both free.
        numbers = {p.pay_period for p in periods}
        starts = {p.start_date for p in periods}
        missing = [
            p for p in backup if p.pay_period not in numbers and p.start_date not in starts
        ]
        used = {int(period.pay_period) for period in periods}
        next_free = next(
            (n for n in range(_FIRST_PERIOD, _LAST_PERIOD + 1) if n not in used), ""
        )
        return render_template(
            "pay_periods.html",
            periods=periods,
            current=services.current_pay_period(load_pay_table(db)),
            years=_pay_period_years(db, periods),
            backup=backup,
            backup_missing=missing,
            values=values or {"period": str(next_free), "start": "", "due": "", "pay": ""},
            error=error,
        ), status

    def _pay_period_fields(form) -> tuple[str, str, str]:
        return (
            services.date_from_input(form.get("start"), "Start date"),
            services.date_from_input(form.get("due"), "Timesheet due date"),
            services.date_from_input(form.get("pay"), "Pay date"),
        )

    @app.get("/pay-periods")
    def pay_periods():
        return _render_pay_periods(get_db())

    @app.post("/pay-periods/add")
    def add_pay_period():
        db = get_db()
        values = {key: request.form.get(key, "").strip() for key in ("period", "start", "due", "pay")}
        try:
            period = parse_pay_period(values["period"])
            created = db.create_pay_period(period, *_pay_period_fields(request.form))
        except DatabaseError as exc:
            return _render_pay_periods(db, values=values, error=str(exc), status=422)
        flash(
            f"Pay period {created.pay_period} added: "
            f"{created.start_date} → {created.end_date}.", "success",
        )
        return redirect(url_for("pay_periods"))

    def _find_pay_period(db, raw):
        raw = (raw or "").strip()
        return next((p for p in db.list_pay_periods() if p.pay_period == raw), None)

    @app.get("/pay-periods/edit")
    def edit_pay_period():
        period = _find_pay_period(get_db(), request.args.get("period"))
        if period is None:
            flash("That pay period doesn't exist.", "error")
            return redirect(url_for("pay_periods"))
        return render_template(
            "pay_period_form.html", period=period, error="",
            values={
                "start": services.date_to_input(period.start_date),
                "due": services.date_to_input(period.due_date),
                "pay": services.date_to_input(period.pay_date),
            },
        )

    @app.post("/pay-periods/edit")
    def update_pay_period():
        db = get_db()
        period = _find_pay_period(db, request.form.get("period"))
        if period is None:
            flash("That pay period doesn't exist.", "error")
            return redirect(url_for("pay_periods"))
        values = {key: request.form.get(key, "").strip() for key in ("start", "due", "pay")}
        try:
            updated = db.update_pay_period(period.pay_period, *_pay_period_fields(request.form))
        except DatabaseError as exc:
            return render_template(
                "pay_period_form.html", period=period, values=values, error=str(exc)
            ), 422
        flash(
            f"Pay period {updated.pay_period} updated: "
            f"{updated.start_date} → {updated.end_date}.", "success",
        )
        return redirect(url_for("pay_periods"))

    @app.post("/pay-periods/delete")
    def delete_pay_period():
        db = get_db()
        period = request.form.get("period", "").strip()
        try:
            db.delete_pay_period(period)
        except DatabaseError as exc:
            flash(str(exc), "error")
        else:
            flash(f"Pay period {period} deleted.", "success")
        return redirect(url_for("pay_periods"))

    @app.post("/pay-periods/restore")
    def restore_pay_periods():
        backup = backup_pay_periods()
        if not backup:
            flash("There's no pay period backup to restore from.", "error")
            return redirect(url_for("pay_periods"))
        restored = get_db().restore_pay_periods(backup)
        if restored:
            numbers = ", ".join(f"#{p.pay_period}" for p in restored)
            flash(f"Restored {len(restored)} pay period(s) from the backup: {numbers}.", "success")
        else:
            flash("Nothing to restore. Every backed-up pay period is already here.", "success")
        return redirect(url_for("pay_periods"))

    @app.post("/pay-periods/delete-year")
    def delete_pay_period_year():
        db = get_db()
        if request.form.get("confirm") != "yes":
            flash("Tick the box to confirm before deleting a whole year.", "error")
            return redirect(url_for("pay_periods"))
        try:
            year = parse_year(request.form.get("year", ""))
            count = db.delete_pay_periods_in_year(year)
        except DatabaseError as exc:
            flash(str(exc), "error")
        else:
            if count:
                flash(f"Deleted {count} pay period(s) fully inside {year}.", "success")
            else:
                flash(f"No pay periods found fully inside {year}.", "error")
        return redirect(url_for("pay_periods"))

    # ── Days off (invalid dates) ─────────────────────────────────────────────

    def _render_days_off(db, value="", error="", status=200):
        dates = db.list_invalid_dates()
        entries = [
            {
                "date": date,
                "weekday": dt.datetime.strptime(date, DATE_FORMAT).strftime("%A"),
            }
            for date in dates
        ]
        years = sorted({date[-4:] for date in dates})
        return render_template(
            "days_off.html", entries=entries, years=years, value=value, error=error,
        ), status

    @app.get("/days-off")
    def days_off():
        return _render_days_off(get_db())

    @app.post("/days-off/add")
    def add_day_off():
        db = get_db()
        raw = request.form.get("date", "").strip()
        try:
            added = db.create_invalid_date(services.date_from_input(raw))
        except DatabaseError as exc:
            return _render_days_off(db, value=raw, error=str(exc), status=422)
        flash(f"{added} added as a day off.", "success")
        return redirect(url_for("days_off"))

    @app.get("/days-off/edit")
    def edit_day_off():
        date = request.args.get("date", "").strip()
        if date not in get_db().list_invalid_dates():
            flash("That day off doesn't exist.", "error")
            return redirect(url_for("days_off"))
        return render_template(
            "day_off_form.html", date=date, value=services.date_to_input(date), error="",
        )

    @app.post("/days-off/edit")
    def update_day_off():
        db = get_db()
        old = request.form.get("old", "").strip()
        raw = request.form.get("date", "").strip()
        if old not in db.list_invalid_dates():
            flash("That day off doesn't exist.", "error")
            return redirect(url_for("days_off"))
        try:
            new = services.date_from_input(raw, "New date")
            if new != old:
                db.update_invalid_date(old, new)
        except DatabaseError as exc:
            return render_template(
                "day_off_form.html", date=old, value=raw, error=str(exc)
            ), 422
        flash(f"Day off changed: {old} → {new}.", "success")
        return redirect(url_for("days_off"))

    @app.post("/days-off/delete")
    def delete_day_off():
        db = get_db()
        date = request.form.get("date", "").strip()
        try:
            db.delete_invalid_date(date)
        except DatabaseError as exc:
            flash(str(exc), "error")
        else:
            flash(f"Day off {date} deleted.", "success")
        return redirect(url_for("days_off"))

    @app.post("/days-off/delete-year")
    def delete_day_off_year():
        db = get_db()
        try:
            year = parse_year(request.form.get("year", ""))
            count = db.delete_invalid_dates_in_year(year)
        except DatabaseError as exc:
            flash(str(exc), "error")
        else:
            if count:
                flash(f"Deleted {count} day(s) off from {year}.", "success")
            else:
                flash(f"No days off found for {year}.", "error")
        return redirect(url_for("days_off"))

    return app
