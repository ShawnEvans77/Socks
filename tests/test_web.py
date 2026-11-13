import datetime as dt
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

# Imported first so the app's import-time tables never touch the real database.
from tests.support import SocksDatabase, ValidationError

from pypdf import PdfReader

from src.constants import filenames
from web import services
from web.app import create_app

TEMPLATE_PDF = Path(filenames.asset_folder) / filenames.pdf_input_folder / filenames.starting_pdf
# 04/05/2026 is a Sunday.
PERIOD_START = "04/05/2026"


def weekly(**days):
    order = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")
    return [days.get(day, []) for day in order]


class ServiceTests(unittest.TestCase):
    def test_browser_times_convert_to_socks_format(self):
        self.assertEqual(services.time_from_input("09:00"), "9AM")
        self.assertEqual(services.time_from_input("14:15"), "2:15PM")
        self.assertEqual(services.time_from_input("00:00"), "12AM")
        self.assertEqual(services.time_from_input("12:30"), "12:30PM")
        self.assertEqual(services.time_from_input("2:15 pm"), "2:15PM")
        with self.assertRaises(ValidationError):
            services.time_from_input("soon")

    def test_stored_times_round_trip_through_browser_format(self):
        for stored in ("9AM", "12PM", "2:15PM", "12AM", "11:59PM"):
            browser = services.time_to_input(stored)
            self.assertEqual(services.time_from_input(browser), stored)
        self.assertEqual(services.time_to_input("nonsense"), "")

    def test_browser_dates_convert_both_ways(self):
        self.assertEqual(services.date_from_input("2026-11-13"), "11/13/2026")
        self.assertEqual(services.date_from_input("11/13/2026"), "11/13/2026")
        self.assertEqual(services.date_to_input("11/13/2026"), "2026-11-13")
        self.assertEqual(services.date_to_input(""), "")
        for bad in ("", "2026-02-30", "tomorrow"):
            with self.assertRaises(ValidationError):
                services.date_from_input(bad)

    def test_intervals_validate_pairs_and_order(self):
        self.assertEqual(services.parse_intervals("", "", "", ""), ())
        self.assertEqual(
            services.parse_intervals("12:00", "14:00", "14:15", "15:15"),
            (("12PM", "2PM"), ("2:15PM", "3:15PM")),
        )
        for bad in (
            ("09:00", "", "", ""),
            ("", "", "09:00", "10:00"),
            ("10:00", "09:00", "", ""),
            ("09:00", "12:00", "11:00", "13:00"),
        ):
            with self.assertRaises(ValidationError):
                services.parse_intervals(*bad)

    def test_current_pay_period_includes_last_day(self):
        class Table:
            @staticmethod
            def get_pay_dict():
                return {19: (dt.datetime(2026, 11, 1), dt.datetime(2026, 11, 14))}

        self.assertEqual(services.current_pay_period(Table, dt.date(2026, 11, 14)), 19)
        self.assertEqual(services.current_pay_period(Table, dt.date(2026, 11, 1)), 19)
        self.assertIsNone(services.current_pay_period(Table, dt.date(2026, 11, 15)))

    def test_file_names_match_the_command_line_app(self):
        self.assertEqual(services.timesheet_file_name("Shawn Evans", 19), "Evans_Timesheet_19.pdf")
        self.assertEqual(services.timesheet_file_name("shawn o'neil", 2), "Oneil_Timesheet_2.pdf")
        self.assertEqual(services.split_name("Mary Ann Smith"), ("Mary Ann", "Smith"))


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="socks-web-tests-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.db_path = root / "socks.db"
        self.output = root / "timesheets"

        self.db = SocksDatabase(str(self.db_path))
        self.db.ensure_schema()
        self.db.create_pay_period("1", PERIOD_START, "04/20/2026", "04/30/2026")
        self.db.create_invalid_date("04/08/2026")  # Wednesday of week one
        self.db.create_employee(
            "Shawn Evans",
            weekly(
                mon=[("1PM", "4PM")],
                wed=[("12PM", "3PM")],
                thu=[("12PM", "2PM"), ("2:15PM", "3:15PM")],
            ),
            "90000001",
            54,
        )

        # Tests never read the real backup; each one builds its own when needed.
        self.backup_path = root / "starter.db"
        app = create_app(self.db_path, TEMPLATE_PDF, self.output, self.backup_path)
        app.testing = True
        self.client = app.test_client()

    def post_timesheet(self, **fields):
        data = {"employee": "Shawn Evans", "period": "1"}
        data.update(fields)
        return self.client.post("/timesheet", data=data)

    def pdf_text(self, name="Evans_Timesheet_1.pdf"):
        return PdfReader(BytesIO((self.output / name).read_bytes())).pages[0].extract_text()

    # ── Pages load ───────────────────────────────────────────────────────────

    def test_every_page_loads(self):
        for url in (
            "/", "/employees", "/employees/new", "/employees/edit?name=shawn%20evans",
            "/pay-periods", "/pay-periods/edit?period=1", "/days-off",
            "/days-off/edit?date=04/08/2026", "/timesheet?employee=Shawn+Evans&period=1",
            "/static/style.css",
        ):
            with self.subTest(url=url):
                with self.client.get(url) as response:
                    self.assertEqual(response.status_code, 200)

    def test_unknown_things_redirect_or_404(self):
        self.assertEqual(self.client.get("/nope").status_code, 404)
        self.assertEqual(self.client.get("/timesheet?employee=nobody").status_code, 302)
        self.assertEqual(self.client.get("/employees/edit?name=nobody").status_code, 302)
        self.assertEqual(self.client.get("/pay-periods/edit?period=9").status_code, 302)
        self.assertEqual(self.client.get("/days-off/edit?date=01/01/2026").status_code, 302)

    def test_timesheet_page_shows_schedule_and_holiday(self):
        page = self.client.get("/timesheet?employee=shawn evans&period=1").get_data(as_text=True)
        self.assertIn("1PM – 4PM", page)
        self.assertIn("Day off / holiday", page)
        self.assertIn("Missed 2:15PM – 3:15PM", page)
        self.assertIn("Make my timesheet", page)

    def test_unknown_pay_period_shows_picker_without_form(self):
        page = self.client.get("/timesheet?employee=Shawn+Evans&period=7").get_data(as_text=True)
        self.assertIn("hasn&#39;t been set up", page)
        self.assertNotIn("Make my timesheet", page)

    # ── Making timesheets ────────────────────────────────────────────────────

    def test_normal_schedule_makes_pdf_with_expected_hours(self):
        response = self.post_timesheet()
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("Evans_Timesheet_1.pdf", page)
        # Week 1: Mon 3 + Thu 3 (Wed is a holiday). Week 2: Mon 3 + Wed 3 + Thu 3.
        self.assertIn('<span class="stat-num">15</span>', page)
        self.assertIn('<span class="stat-num">6</span>', page)
        self.assertIn('<span class="stat-num">9</span>', page)
        self.assertIn("04/20/2026", page)
        self.assertIn("04/30/2026", page)

        text = self.pdf_text()
        self.assertIn("Evans", text)
        self.assertIn("90000001", text)
        self.assertIn("885-54", text)
        self.assertIn("15", text)

        with self.client.get("/timesheets/Evans_Timesheet_1.pdf") as served:
            self.assertEqual(served.status_code, 200)
            self.assertEqual(served.mimetype, "application/pdf")
            self.assertTrue(served.data.startswith(b"%PDF"))
        with self.client.get("/timesheets/Evans_Timesheet_1.pdf?download=1") as download:
            self.assertIn("attachment", download.headers["Content-Disposition"])

    def test_missed_day_split_miss_and_extra_day_change_hours(self):
        response = self.post_timesheet(
            mode_1="missed",                       # Mon 04/06: -3
            skip_4_1="1",                          # Thu 04/09: miss 2:15-3:15, -1
            mode_3="custom",                       # Wed 04/08 holiday: +2.5
            start1_3="09:00", end1_3="11:30",
            mode_6="custom",                       # Sat 04/11 split: +3
            start1_6="09:00", end1_6="10:00", start2_6="13:00", end2_6="15:00",
        )
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        # Week 1: Wed 2.5 + Thu 2 + Sat 3 = 7.5; week 2 unchanged at 9.
        self.assertIn('<span class="stat-num">16.5</span>', page)
        self.assertIn('<span class="stat-num">7.5</span>', page)
        self.assertIn("9AM – 11:30AM", page)
        self.assertIn("Missed", page)
        self.assertIn("16.5", self.pdf_text())

    def test_bad_custom_hours_show_error_and_keep_input(self):
        for fields, message in (
            ({"mode_2": "custom"}, "Enter the hours you worked"),
            ({"mode_2": "custom", "start1_2": "09:00"}, "both a start time and an end time"),
            ({"mode_2": "custom", "start1_2": "11:00", "end1_2": "09:00"}, "end must be later"),
        ):
            with self.subTest(fields=fields):
                response = self.post_timesheet(**fields)
                self.assertEqual(response.status_code, 422)
                page = response.get_data(as_text=True)
                self.assertIn(message, page)
                self.assertIn('name="mode_2" value="custom" checked', page)
                self.assertFalse(self.output.exists())

    def test_missing_emplid_is_required_then_saved(self):
        self.db.create_employee("Ada Lovelace", weekly(tue=[("9AM", "11AM")]), None, 54)

        page = self.client.get("/timesheet?employee=Ada+Lovelace&period=1").get_data(as_text=True)
        self.assertIn("EMPLID needed", page)

        for bad in ("", "abc", "90000001"):  # blank, non-digits, already taken
            with self.subTest(emplid=bad):
                response = self.client.post(
                    "/timesheet", data={"employee": "Ada Lovelace", "period": "1", "emplid": bad}
                )
                self.assertEqual(response.status_code, 422)

        response = self.client.post(
            "/timesheet", data={"employee": "Ada Lovelace", "period": "1", "emplid": "11112222"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("11112222", self.pdf_text("Lovelace_Timesheet_1.pdf"))
        saved = services.find_employee(self.db.list_employees(), "ada lovelace")
        self.assertEqual(saved.emplid, "11112222")

    def test_changes_toggle_defaults_and_hides_day_edits(self):
        page = self.client.get("/timesheet?employee=Shawn+Evans&period=1").get_data(as_text=True)
        self.assertIn('name="changes" value="none" checked', page)

        # Edits left behind a "normal schedule" answer are ignored.
        response = self.post_timesheet(changes="none", mode_1="missed", skip_4_1="1")
        self.assertIn('<span class="stat-num">15</span>', response.get_data(as_text=True))

        response = self.post_timesheet(changes="some", mode_1="missed")
        self.assertIn('<span class="stat-num">12</span>', response.get_data(as_text=True))

        # A failed submit reopens the day editor so the error is visible.
        page = self.post_timesheet(changes="some", mode_2="custom").get_data(as_text=True)
        self.assertIn('name="changes" value="some" checked', page)

    def test_requests_do_not_share_missed_days(self):
        self.post_timesheet(mode_1="missed")
        page = self.post_timesheet().get_data(as_text=True)
        self.assertIn('<span class="stat-num">15</span>', page)

    def test_stale_employee_or_period_redirects(self):
        self.assertEqual(
            self.client.post("/timesheet", data={"employee": "Nobody", "period": "1"}).status_code, 302
        )
        self.assertEqual(self.post_timesheet(period="12").status_code, 302)

    # ── Employees ────────────────────────────────────────────────────────────

    def test_create_employee_with_split_schedule(self):
        response = self.client.post("/employees/new", data={
            "first": "grace", "last": "hopper", "emplid": "55556666", "budget": "72",
            "d2_s1": "09:00", "d2_e1": "12:00", "d2_s2": "13:00", "d2_e2": "15:30",
        })
        self.assertEqual(response.status_code, 302)
        employee = services.find_employee(self.db.list_employees(), "Grace Hopper")
        self.assertEqual(employee.emplid, "55556666")
        self.assertEqual(employee.budget, 72)
        self.assertEqual(employee.schedule[2], (("9AM", "12PM"), ("1PM", "3:30PM")))
        self.assertEqual(employee.schedule[0], ())

    def test_create_employee_rejects_bad_input(self):
        good = {"first": "Grace", "last": "Hopper", "emplid": "55556666", "budget": "72"}
        for change, message in (
            ({"last": ""}, "Enter both a first and last name."),
            ({"first": "SHAWN", "last": "evans"}, "already exists"),
            ({"emplid": "12ab"}, "digits only"),
            ({"emplid": "90000001"}, "already assigned"),
            ({"budget": "x"}, "Budget must contain digits only."),
            ({"d1_s1": "09:00"}, "both a start time and an end time"),
            ({"d1_s1": "12:00", "d1_e1": "09:00"}, "end must be later"),
        ):
            with self.subTest(change=change):
                response = self.client.post("/employees/new", data={**good, **change})
                self.assertEqual(response.status_code, 422)
                self.assertIn(message, response.get_data(as_text=True))
        self.assertEqual(len(self.db.list_employees()), 1)

    def test_edit_employee_updates_schedule_budget_and_emplid(self):
        page = self.client.get("/employees/edit?name=Shawn+Evans").get_data(as_text=True)
        self.assertIn('name="d1_s1" value="13:00"', page)
        self.assertIn('name="d4_s2" value="14:15"', page)

        response = self.client.post("/employees/edit", data={
            "name": "Shawn Evans", "emplid": "99990000", "budget": "60",
            "d1_s1": "10:00", "d1_e1": "12:00",          # Monday changed
            "d5_s1": "09:00", "d5_e1": "10:30",          # Friday added
            # Wednesday and Thursday left blank: cleared
        })
        self.assertEqual(response.status_code, 302)
        employee = self.db.list_employees()[0]
        self.assertEqual((employee.emplid, employee.budget), ("99990000", 60))
        self.assertEqual(employee.schedule[1], (("10AM", "12PM"),))
        self.assertEqual(employee.schedule[5], (("9AM", "10:30AM"),))
        self.assertEqual(employee.schedule[3], ())
        self.assertEqual(employee.schedule[4], ())

    def test_edit_employee_rejects_bad_input_without_saving(self):
        response = self.client.post("/employees/edit", data={
            "name": "Shawn Evans", "emplid": "", "budget": "60",
            "d1_s1": "10:00", "d1_e1": "12:00",
        })
        self.assertEqual(response.status_code, 422)
        employee = self.db.list_employees()[0]
        self.assertEqual((employee.emplid, employee.budget), ("90000001", 54))
        self.assertEqual(employee.schedule[1], (("1PM", "4PM"),))

    # ── Pay periods ──────────────────────────────────────────────────────────

    def test_pay_period_add_edit_delete(self):
        response = self.client.post("/pay-periods/add", data={
            "period": "2", "start": "2026-04-19", "due": "2026-05-04", "pay": "2026-05-14",
        })
        self.assertEqual(response.status_code, 302)
        added = self.db.list_pay_periods()[1]
        self.assertEqual(
            (added.pay_period, added.start_date, added.end_date, added.due_date, added.pay_date),
            ("2", "04/19/2026", "05/02/2026", "05/04/2026", "05/14/2026"),
        )

        response = self.client.post("/pay-periods/edit", data={
            "period": "2", "start": "2026-04-20", "due": "2026-05-05", "pay": "2026-05-15",
        })
        self.assertEqual(response.status_code, 302)
        edited = self.db.list_pay_periods()[1]
        self.assertEqual((edited.start_date, edited.end_date), ("04/20/2026", "05/03/2026"))

        self.assertEqual(self.client.post("/pay-periods/delete", data={"period": "2"}).status_code, 302)
        self.assertEqual([p.pay_period for p in self.db.list_pay_periods()], ["1"])

    def test_pay_period_rejects_bad_input(self):
        good = {"period": "2", "start": "2026-04-19", "due": "2026-05-04", "pay": "2026-05-14"}
        for change, message in (
            ({"period": "1"}, "already exists"),
            ({"period": "27"}, "between 1 and 26"),
            ({"period": ""}, "between 1 and 26"),
            ({"start": ""}, "Start date is required."),
            ({"start": "2026-04-05"}, "Start date 04/05/2026 already exists."),
            ({"pay": "garbage"}, "Pay date"),
        ):
            with self.subTest(change=change):
                response = self.client.post("/pay-periods/add", data={**good, **change})
                self.assertEqual(response.status_code, 422)
                self.assertIn(message, response.get_data(as_text=True))
        self.assertEqual(len(self.db.list_pay_periods()), 1)

        response = self.client.post("/pay-periods/edit", data={"period": "1", "start": "", "due": "", "pay": ""})
        self.assertEqual(response.status_code, 422)

    def test_pay_period_delete_year(self):
        self.db.create_pay_period("26", "12/27/2026", "01/11/2027", "02/04/2027")  # spans two years
        page = self.client.get("/pay-periods").get_data(as_text=True)
        self.assertIn("<option>2026</option>", page)
        self.assertNotIn("<option>2027</option>", page)

        # Without the confirm box ticked, nothing is deleted.
        response = self.client.post("/pay-periods/delete-year", data={"year": "2026"}, follow_redirects=True)
        self.assertIn("Tick the box to confirm", response.get_data(as_text=True))
        self.assertEqual(len(self.db.list_pay_periods()), 2)

        confirmed = {"year": "2026", "confirm": "yes"}
        response = self.client.post("/pay-periods/delete-year", data=confirmed, follow_redirects=True)
        self.assertIn("Deleted 1 pay period(s) fully inside 2026.", response.get_data(as_text=True))
        self.assertEqual([p.pay_period for p in self.db.list_pay_periods()], ["26"])

        response = self.client.post("/pay-periods/delete-year", data=confirmed, follow_redirects=True)
        self.assertIn("No pay periods found fully inside 2026.", response.get_data(as_text=True))

    def make_backup(self, *periods):
        backup = SocksDatabase(str(self.backup_path))
        backup.ensure_schema()
        for row in periods:
            backup.create_pay_period(*row)
        return backup

    def test_restore_puts_back_only_missing_pay_periods(self):
        self.make_backup(
            ("1", "01/01/2026", "01/15/2026", "01/30/2026"),  # different from the live #1
            ("2", "04/19/2026", "05/04/2026", "05/28/2026"),
            ("3", "05/03/2026", "05/18/2026", "06/11/2026"),
        )
        page = self.client.get("/pay-periods").get_data(as_text=True)
        self.assertIn("Restore 2 missing pay periods", page)

        response = self.client.post("/pay-periods/restore", follow_redirects=True)
        self.assertIn("Restored 2 pay period(s) from the backup: #2, #3.", response.get_data(as_text=True))
        periods = {p.pay_period: p for p in self.db.list_pay_periods()}
        self.assertEqual(sorted(periods, key=int), ["1", "2", "3"])
        self.assertEqual(periods["1"].start_date, PERIOD_START)  # existing one untouched
        self.assertEqual(periods["3"].end_date, "05/16/2026")

        page = self.client.get("/pay-periods").get_data(as_text=True)
        self.assertIn("All 3 backed-up pay periods are here", page)
        response = self.client.post("/pay-periods/restore", follow_redirects=True)
        self.assertIn("Nothing to restore", response.get_data(as_text=True))

    def test_restore_after_deleting_a_whole_year(self):
        self.make_backup((("1", PERIOD_START, "04/20/2026", "04/30/2026")))
        self.client.post("/pay-periods/delete-year", data={"year": "2026", "confirm": "yes"})
        self.assertEqual(self.db.list_pay_periods(), [])
        self.client.post("/pay-periods/restore")
        self.assertEqual([p.pay_period for p in self.db.list_pay_periods()], ["1"])

    def test_restore_without_a_backup_file(self):
        page = self.client.get("/pay-periods").get_data(as_text=True)
        self.assertNotIn("Restore", page)
        response = self.client.post("/pay-periods/restore", follow_redirects=True)
        self.assertIn("no pay period backup", response.get_data(as_text=True))
        self.assertFalse(self.backup_path.exists())  # it is never created by reading

    # ── Days off ─────────────────────────────────────────────────────────────

    def test_day_off_add_change_delete(self):
        self.assertEqual(self.client.post("/days-off/add", data={"date": "2026-12-25"}).status_code, 302)
        self.assertIn("12/25/2026", self.db.list_invalid_dates())

        for bad, message in (("2026-12-25", "already exists"), ("", "Date is required.")):
            response = self.client.post("/days-off/add", data={"date": bad})
            self.assertEqual(response.status_code, 422)
            self.assertIn(message, response.get_data(as_text=True))

        response = self.client.post("/days-off/edit", data={"old": "12/25/2026", "date": "2026-12-24"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.db.list_invalid_dates(), ["04/08/2026", "12/24/2026"])

        response = self.client.post("/days-off/edit", data={"old": "12/24/2026", "date": "2026-04-08"})
        self.assertEqual(response.status_code, 422)

        self.assertEqual(self.client.post("/days-off/delete", data={"date": "12/24/2026"}).status_code, 302)
        self.assertEqual(self.db.list_invalid_dates(), ["04/08/2026"])

    def test_day_off_delete_year(self):
        self.db.create_invalid_date("01/01/2027")
        response = self.client.post("/days-off/delete-year", data={"year": "2026"}, follow_redirects=True)
        self.assertIn("Deleted 1 day(s) off from 2026.", response.get_data(as_text=True))
        self.assertEqual(self.db.list_invalid_dates(), ["01/01/2027"])

    # ── Safety ───────────────────────────────────────────────────────────────

    def test_other_sites_and_hosts_are_refused(self):
        response = self.client.post(
            "/days-off/delete", data={"date": "04/08/2026"}, headers={"Origin": "http://evil.example"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.db.list_invalid_dates(), ["04/08/2026"])

        response = self.client.get("/", headers={"Host": "evil.example"})
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            "/days-off/add", data={"date": "2026-12-25"}, headers={"Origin": "http://localhost"}
        )
        self.assertEqual(response.status_code, 302)

    def test_timesheet_files_cannot_escape_their_folder(self):
        self.post_timesheet()
        self.assertEqual(self.client.get("/timesheets/../socks.db").status_code, 404)

    def test_delete_saved_timesheet(self):
        self.post_timesheet()
        pdf = self.output / "Evans_Timesheet_1.pdf"
        self.assertTrue(pdf.exists())
        self.assertIn("Delete", self.client.get("/").get_data(as_text=True))

        response = self.client.post(
            "/timesheets/delete", data={"file_name": "Evans_Timesheet_1.pdf"}, follow_redirects=True
        )
        self.assertIn("Deleted Evans_Timesheet_1.pdf", response.get_data(as_text=True))
        self.assertFalse(pdf.exists())

    def test_delete_refuses_names_outside_the_list(self):
        self.post_timesheet()
        for bad in ("../socks.db", "missing.pdf", ""):
            with self.subTest(file_name=bad):
                response = self.client.post(
                    "/timesheets/delete", data={"file_name": bad}, follow_redirects=True
                )
                self.assertIn("doesn&#39;t exist anymore", response.get_data(as_text=True))
        self.assertTrue(Path(self.db_path).exists())
        self.assertTrue((self.output / "Evans_Timesheet_1.pdf").exists())


if __name__ == "__main__":
    unittest.main()
