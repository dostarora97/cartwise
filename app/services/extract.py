"""
Invoice PDF Extractor

Deterministic extraction of line items from grocery invoice PDFs.
No classification, no heuristics — just reads the table structure.

This module is sync (pdfplumber is sync). Call via asyncio.to_thread()
from async code.
"""

import dataclasses
import re

import pdfplumber


@dataclasses.dataclass
class Row:
    upc: str
    description: str
    hsn: str | None
    mrp: float | None
    qty: int | None
    total: float


_HSN_RE = re.compile(r"\(HSN[-\s]*(\d+)\)", re.IGNORECASE)


def _find_header_row(table: list[list[str]]) -> int | None:
    for i, row in enumerate(table):
        cells = [(c or "").lower() for c in row]
        joined = " ".join(cells)
        if "item description" in joined and "total" in joined:
            return i
    return None


def _is_annexure_table(table: list[list[str]]) -> bool:
    for row in table:
        joined = " ".join((c or "").lower() for c in row)
        if "nature of charge" in joined:
            return True
    return False


def _col_index(header: list[str], *names: str) -> int | None:
    for i, cell in enumerate(header):
        if not cell:
            continue
        cell_lower = cell.strip().lower()
        for name in names:
            if name in cell_lower:
                return i
    return None


def _is_total_row(row: list[str]) -> bool:
    first = (row[0] or "").strip().lower() if row else ""
    return first == "total"


def _cell_text(row: list[str], col: int | None) -> str:
    if col is not None and col < len(row):
        return (row[col] or "").replace("\n", " ").strip()
    return ""


def _parse_row(
    raw: list[str],
    upc_col: int | None,
    item_col: int | None,
    mrp_col: int | None,
    qty_col: int | None,
    total_col: int | None,
) -> Row:
    raw_upc = _cell_text(raw, upc_col).replace(" ", "")

    raw_desc = _cell_text(raw, item_col)
    hsn_match = _HSN_RE.search(raw_desc)
    hsn = hsn_match.group(1) if hsn_match else None
    description = _HSN_RE.sub("", raw_desc).strip()

    raw_mrp = _cell_text(raw, mrp_col)
    mrp = None if raw_mrp in ("", "-", "\u2013", "\u2014") else float(raw_mrp)

    raw_qty = _cell_text(raw, qty_col)
    qty = None if raw_qty in ("", "-", "\u2013", "\u2014") else int(raw_qty)

    total = float(_cell_text(raw, total_col))

    return Row(upc=raw_upc, description=description, hsn=hsn, mrp=mrp, qty=qty, total=total)


def _parse_invoice_total(raw: str | None) -> float | None:
    if raw is None or raw in ("", "-", "\u2013", "\u2014"):
        return None
    return float(raw)


def extract(pdf_path: str) -> dict:
    """Extract all invoice line items from a grocery invoice PDF.

    This is a sync function. In async context, call via:
        result = await asyncio.to_thread(extract, pdf_path)

    Args:
        pdf_path: Path to the invoice PDF.

    Returns:
        Dict with "invoices" key containing extracted data.
    """
    invoices = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            for table in page.extract_tables():
                if not table or len(table) < 2:
                    continue
                if _is_annexure_table(table):
                    continue

                header_idx = _find_header_row(table)
                if header_idx is None:
                    continue

                header = table[header_idx]
                upc_col = _col_index(header, "upc", "hsn code")
                item_col = _col_index(header, "item description")
                mrp_col = _col_index(header, "mrp")
                qty_col = _col_index(header, "qty")
                total_col = _col_index(header, "total")

                rows = []
                invoice_total = None

                for raw_row in table[header_idx + 1 :]:
                    if _is_total_row(raw_row):
                        invoice_total = _parse_invoice_total(_cell_text(raw_row, total_col))
                        break

                    rows.append(
                        dataclasses.asdict(
                            _parse_row(raw_row, upc_col, item_col, mrp_col, qty_col, total_col)
                        )
                    )

                invoices.append(
                    {
                        "page": page_num,
                        "items": rows,
                        "invoice_total": invoice_total,
                    }
                )

    return {"invoices": invoices}
