from pypdf import PdfReader, PdfWriter # type: ignore

reader = PdfReader("timesheet.pdf")
writer = PdfWriter()

page = reader.pages[0]
fields = reader.get_fields()

writer.append(reader)

writer.update_page_form_field_values(
    writer.pages[0],
    {"topmostSubform[0].Page1[0].TextField1[10]": "dogs"},
    auto_regenerate=False,
)

writer.write("out-filled-form.pdf")