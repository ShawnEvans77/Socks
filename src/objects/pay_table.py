import datetime as dt

from ..constants.schedule import DAYS_PER_PAY_PERIOD
from ..utils.database import DATE_FORMAT, SocksDatabase, parse_existing_date


class PayTable:
    """In-memory view of payroll periods and invalid dates."""

    def __init__(self, database: SocksDatabase | None = None, ensure_schema: bool = True):
        self.db = database or SocksDatabase()
        if ensure_schema:
            self.db.ensure_schema()

        periods = self.db.list_pay_periods()
        self.pay_dict = {
            int(period.pay_period): (
                self.str_to_datetime(period.start_date),
                self.str_to_datetime(period.end_date),
            )
            for period in periods
        }
        self.payment_dict = {
            int(period.pay_period): (period.due_date, period.pay_date)
            for period in periods
        }
        self.invalid_dates = [
            self.str_to_datetime(value) for value in self.db.list_invalid_dates()
        ]

    @staticmethod
    def str_to_datetime(date_str: str) -> dt.datetime:
        normalized = parse_existing_date(date_str)
        return dt.datetime.strptime(normalized, DATE_FORMAT)

    @staticmethod
    def date_str(date: dt.datetime) -> str:
        return date.strftime("%m/%d")

    def get_period_dates(self, pay_period: int) -> list[dt.datetime]:
        return [
            self.date_offset(pay_period, offset)
            for offset in range(DAYS_PER_PAY_PERIOD)
        ]

    def get_invalid_dates(self) -> list[dt.datetime]:
        return list(self.invalid_dates)

    def get_pay_dict(self) -> dict[int, tuple[dt.datetime, dt.datetime]]:
        return dict(self.pay_dict)

    def date_offset(self, pay_period: int, offset: int) -> dt.datetime:
        return self.pay_dict[int(pay_period)][0] + dt.timedelta(days=offset)

    def start_date_string(self, pay_period: int) -> str:
        return self.date_str(self.pay_dict[int(pay_period)][0])

    def end_date_string(self, pay_period: int) -> str:
        return self.date_str(self.pay_dict[int(pay_period)][1])

    def due_date_string(self, pay_period: int) -> str:
        return self.payment_dict[int(pay_period)][0]

    def pay_date_string(self, pay_period: int) -> str:
        return self.payment_dict[int(pay_period)][1]

    def date_offset_string(self, pay_period: int, offset: int) -> str:
        return self.date_str(self.date_offset(pay_period, offset))

    def has_pay_period(self, pay_period: str | int) -> bool:
        try:
            return int(pay_period) in self.pay_dict
        except (TypeError, ValueError):
            return False
