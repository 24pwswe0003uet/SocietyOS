"""XLSX export service using XlsxWriter."""

import io
import logging

logger = logging.getLogger("societyos.documents.xlsx")


def generate_budget_xlsx(
    title: str,
    currency: str,
    categories: list[dict],
    contingency_percent: int = 10,
) -> bytes:
    """Generate a professional budget XLSX spreadsheet."""
    try:
        import xlsxwriter
    except ImportError:
        logger.error("XlsxWriter not installed")
        raise ImportError("XlsxWriter is required for XLSX export")

    buffer = io.BytesIO()
    wb = xlsxwriter.Workbook(buffer, {"in_memory": True})
    ws = wb.add_worksheet("Budget")

    # Formats
    title_fmt = wb.add_format({
        "bold": True, "font_size": 16, "font_color": "#4F46E5",
        "bottom": 2, "bottom_color": "#4F46E5",
    })
    header_fmt = wb.add_format({
        "bold": True, "bg_color": "#F1F5F9", "border": 1,
        "font_size": 10,
    })
    currency_fmt = wb.add_format({"num_format": f"{currency} #,##0", "border": 1})
    num_fmt = wb.add_format({"num_format": "#,##0", "border": 1})
    text_fmt = wb.add_format({"border": 1, "text_wrap": True})
    cat_fmt = wb.add_format({
        "bold": True, "bg_color": "#EEF2FF", "border": 1,
        "font_color": "#4F46E5",
    })
    total_fmt = wb.add_format({
        "bold": True, "num_format": f"{currency} #,##0", "border": 1,
        "bg_color": "#F1F5F9", "font_size": 11,
    })
    grand_fmt = wb.add_format({
        "bold": True, "num_format": f"{currency} #,##0", "border": 2,
        "bg_color": "#4F46E5", "font_color": "#FFFFFF", "font_size": 12,
    })

    # Set column widths
    ws.set_column("A:A", 35)
    ws.set_column("B:B", 10)
    ws.set_column("C:C", 18)
    ws.set_column("D:D", 18)

    # Title
    ws.write(0, 0, f"Budget: {title}", title_fmt)
    ws.write(1, 0, f"Currency: {currency}")

    # Headers
    row = 3
    for col, label in enumerate(["Description", "Qty", "Unit Cost", "Total"]):
        ws.write(row, col, label, header_fmt)
    row += 1

    grand_total = 0

    for cat in categories:
        # Category header
        ws.write(row, 0, cat["name"], cat_fmt)
        ws.write(row, 1, "", cat_fmt)
        ws.write(row, 2, "", cat_fmt)
        ws.write(row, 3, "", cat_fmt)
        row += 1

        cat_total = 0
        for item in cat.get("items", []):
            ws.write(row, 0, item.get("description", ""), text_fmt)
            ws.write(row, 1, item.get("quantity", 1), num_fmt)
            ws.write(row, 2, item.get("unit_cost", 0), currency_fmt)
            item_total = item.get("total", item.get("quantity", 1) * item.get("unit_cost", 0))
            ws.write(row, 3, item_total, currency_fmt)
            cat_total += item_total
            row += 1

        # Category subtotal
        ws.write(row, 0, f"Subtotal — {cat['name']}", total_fmt)
        ws.write(row, 3, cat_total, total_fmt)
        grand_total += cat_total
        row += 1

    # Contingency
    row += 1
    contingency = grand_total * (contingency_percent / 100)
    ws.write(row, 0, f"Subtotal before contingency", total_fmt)
    ws.write(row, 3, grand_total, total_fmt)
    row += 1
    ws.write(row, 0, f"Contingency ({contingency_percent}%)", total_fmt)
    ws.write(row, 3, contingency, total_fmt)
    row += 1
    ws.write(row, 0, "GRAND TOTAL", grand_fmt)
    ws.write(row, 3, grand_total + contingency, grand_fmt)

    wb.close()
    return buffer.getvalue()
