from pypdf import PdfReader, PdfWriter # type: ignore

class SheetWriter:

    last_pos, first_pos = 6, 7 # SIX SEVEN!!! :3
    pay_pos = 5

    def __init__(self, writer, page):
        self.writer = writer
        self.page = page

    def write_last(self, last_name):
        self.writer.update_page_form_field_values(self.page,{f"topmostSubform[0].Page1[0].TextField1[{SheetWriter.last_pos}]": last_name})

    def write_first(self, first_name):
        self.writer.update_page_form_field_values(self.page,{f"topmostSubform[0].Page1[0].TextField1[{SheetWriter.first_pos}]": first_name})

    def write_pay_period(self, pay_period):
        self.writer.update_page_form_field_values(self.page, {f"topmostSubform[0].Page1[0].TextField1[{SheetWriter.pay_pos}]":  f"{pay_period} - {pay_dict[pay_period]}"})  
