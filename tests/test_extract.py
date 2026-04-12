"""Unit tests for PDF extraction — deterministic, no LLM needed."""

from pathlib import Path

from app.services.extract import (
    Row,
    _cell_text,
    _col_index,
    _find_header_row,
    _is_annexure_table,
    _is_total_row,
    _parse_invoice_total,
    _parse_row,
    extract,
)

INVOICE_PDF = Path(__file__).parent / "fixtures" / "test_invoice.pdf"


# --- Helper function tests ---


def test_find_header_row_found():
    table = [
        ["Metadata", "stuff"],
        ["UPC", "Item Description", "MRP", "Qty", "Total"],
        ["123", "Chicken", "100", "1", "100"],
    ]
    assert _find_header_row(table) == 1


def test_find_header_row_not_found():
    table = [["No", "header", "here"]]
    assert _find_header_row(table) is None


def test_find_header_row_case_insensitive():
    table = [["upc", "ITEM DESCRIPTION", "mrp", "qty", "TOTAL"]]
    assert _find_header_row(table) == 0


def test_is_annexure_table_true():
    table = [["Nature of charge", "Amount", "Tax"]]
    assert _is_annexure_table(table) is True


def test_is_annexure_table_false():
    table = [["UPC", "Item Description", "Total"]]
    assert _is_annexure_table(table) is False


def test_col_index_found():
    header = ["UPC", "Item Description", "MRP", "Qty", "Total"]
    assert _col_index(header, "item description") == 1
    assert _col_index(header, "total") == 4
    assert _col_index(header, "upc", "hsn code") == 0


def test_col_index_not_found():
    header = ["UPC", "Description", "Total"]
    assert _col_index(header, "mrp") is None


def test_col_index_none_cells():
    header = [None, "Item Description", None, "Total"]
    assert _col_index(header, "item description") == 1


def test_is_total_row():
    assert _is_total_row(["Total", "", "", "", "1048"]) is True
    assert _is_total_row(["total", "", "", "", "1048"]) is True
    assert _is_total_row(["Chicken", "", "", "", "100"]) is False
    assert _is_total_row([]) is False


def test_cell_text():
    row = ["hello", "world\nwrap", None, "  spaced  "]
    assert _cell_text(row, 0) == "hello"
    assert _cell_text(row, 1) == "world wrap"  # newline replaced
    assert _cell_text(row, 2) == ""  # None → empty
    assert _cell_text(row, 3) == "spaced"  # trimmed
    assert _cell_text(row, None) == ""  # no column
    assert _cell_text(row, 99) == ""  # out of bounds


def test_parse_row_product():
    raw = ["8901262150989", "Amul Gold Milk(Tetra Pak) (HSN-04012000)", "83", "1", "83"]
    row = _parse_row(raw, 0, 1, 2, 3, 4)
    assert isinstance(row, Row)
    assert row.upc == "8901262150989"
    assert row.description == "Amul Gold Milk(Tetra Pak)"
    assert row.hsn == "04012000"
    assert row.mrp == 83.0
    assert row.qty == 1
    assert row.total == 83.0


def test_parse_row_fee():
    raw = ["-", "Delivery and other charges", "-", "-", "1.13"]
    row = _parse_row(raw, 0, 1, 2, 3, 4)
    assert row.upc == "-"
    assert row.description == "Delivery and other charges"
    assert row.hsn is None
    assert row.mrp is None
    assert row.qty is None
    assert row.total == 1.13


def test_parse_row_hsn_with_space():
    raw = ["5512458010000", "Onion(Pack) (HSN- 07081000)", "26", "1", "26"]
    row = _parse_row(raw, 0, 1, 2, 3, 4)
    assert row.hsn == "07081000"
    assert row.description == "Onion(Pack)"


def test_parse_row_no_hsn():
    raw = ["998549", "Handling charge", "9.36", "1", "9.36"]
    row = _parse_row(raw, 0, 1, 2, 3, 4)
    assert row.hsn is None
    assert row.description == "Handling charge"


def test_parse_invoice_total():
    assert _parse_invoice_total("1048") == 1048.0
    assert _parse_invoice_total("") is None
    assert _parse_invoice_total("-") is None
    assert _parse_invoice_total("\u2013") is None  # en dash
    assert _parse_invoice_total("\u2014") is None  # em dash
    assert _parse_invoice_total(None) is None


# --- Full PDF extraction test ---


def test_extract_real_pdf():
    """Extract from the real test PDF and verify structure + values."""
    result = extract(str(INVOICE_PDF))

    assert "invoices" in result
    invoices = result["invoices"]
    assert len(invoices) == 3  # 3 invoice tables in this PDF

    # Count all items across invoices
    all_items = [item for inv in invoices for item in inv["items"]]
    assert len(all_items) == 16  # 13 items + 3 fees

    # Check first item
    first = all_items[0]
    assert first["upc"] == "5511290002500"
    assert "Lady Finger" in first["description"]
    assert first["hsn"] == "07081000"
    assert first["mrp"] == 16.5
    assert first["qty"] == 2
    assert first["total"] == 33.0

    # Check a fee row
    fees = [i for i in all_items if i["mrp"] is None and i["upc"] == "-"]
    assert len(fees) == 2  # Two "Delivery and other charges"

    # Invoice totals
    for inv in invoices:
        assert inv["invoice_total"] is not None
        assert inv["page"] >= 1
