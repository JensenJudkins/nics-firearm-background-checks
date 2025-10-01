#!/usr/bin/env python
import datetime
import re
import sys
from operator import itemgetter

import pandas as pd
import pdfplumber
from pdfplumber.utils import extract_text

COLUMNS = [
    "month",
    "state",
    "permit",
    "permit_recheck",
    "handgun",
    "long_gun",
    "other",
    "multiple",
    "admin",
    "prepawn_handgun",
    "prepawn_long_gun",
    "prepawn_other",
    "redemption_handgun",
    "redemption_long_gun",
    "redemption_other",
    "returned_handgun",
    "returned_long_gun",
    "returned_other",
    "rentals_handgun",
    "rentals_long_gun",
    "private_sale_handgun",
    "private_sale_long_gun",
    "private_sale_other",
    "return_to_seller_handgun",
    "return_to_seller_long_gun",
    "return_to_seller_other",
    "totals",
]


def parse_month(month_str):
    normed = month_str.replace("-", " ")
    d = datetime.datetime.strptime(normed, "%B %Y")
    return d.strftime("%Y-%m")


def validate_data(checks):
    if not len(checks):
        raise Exception("No data found.")

    # Test vertical totals
    #
    # Here, [2:] because first two columns are month and state name
    for c in COLUMNS[2:]:
        v_total = checks[c].iloc[-1]
        v_colsum = checks[c].sum()
        if v_colsum != (v_total * 2):
            raise Exception("Vertical totals don't match on {0}.".format(c))

    # Test horizontal totals
    h_colsums = checks.sum(axis=1, numeric_only=True)
    h_totals = checks["totals"].fillna(0)
    zipped = zip(checks["state"], h_colsums, h_totals)
    for state, h_colsum, h_total in zipped:
        if h_colsum != (h_total * 2):
            raise Exception("Horizontal totals don't match on {0}.".format(state))


def parse_value(x):
    if pd.isnull(x) or x == "":
        return None
    return int(re.sub(r"[^\d]", "", x))


def parse_table_old(page):
    cropped = page.crop(
        (
            0,
            page.search("Alabama")[0]["top"],
            page.width,
            page.search("Totals")[-1]["bottom"] + 5,
        )
    )

    edge_xs = list(set(map(itemgetter("x0"), cropped.edges)))
    leftmost_char = min(map(itemgetter("x0"), cropped.chars))

    return cropped.extract_table(
        {
            "horizontal_strategy": "text",
            "vertical_strategy": "explicit",
            "explicit_vertical_lines": [leftmost_char] + edge_xs,
            "intersection_tolerance": 5,
            "text_y_tolerance": 0,
            "text_x_tolerance": 2,
        }
    )


def parse_table_new(page):
    cropped = page.crop(
        (
            0,
            page.search("Alabama")[0]["top"] - 5,
            page.width,
            page.height,
        )
    )

    return cropped.extract_table(
        {"horizontal_strategy": "lines_strict", "vertical_strategy": "lines_strict"}
    )


def detect_pdf_format(pdf):
    """Detect if this is a daily data PDF or state-by-state monthly PDF"""
    if len(pdf.pages) < 2:
        return "unknown"
    
    # Check the second page (first page is usually cover/intro)
    page = pdf.pages[1]
    text = page.extract_text()
    
    # Check for patterns that indicate daily data format
    if "Day/Month/Year" in text and re.search(r"Year \d{4}", text):
        return "daily"
    
    # Check for patterns that indicate state data format
    if any(state in text for state in ["Alabama", "Alaska", "Arizona"]):
        return "state"
    
    return "unknown"


def parse_page_state_format(page):
    """Parse a page in the state-by-state monthly format"""
    reds = [
        [1, 0, 0],
        (1, 0, 0),
    ]
    month_chars = [c for c in page.chars if c["non_stroking_color"] in reds]
    
    # If no red characters found, try to find month in text
    if not month_chars:
        text = page.extract_text()
        # Look for month patterns like "March 2024" or "February 2024"
        month_match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}", text)
        if month_match:
            month_text = month_match.group(0)
        else:
            raise Exception(f"Could not find month information on page {page.page_number}")
    else:
        month_text = extract_text(month_chars, x_tolerance=2)
    
    month = parse_month(month_text)
    sys.stderr.write("\r" + month)

    table_parser = parse_table_new if month > "2022" else parse_table_old
    _table = table_parser(page)
    page.flush_cache()

    table = pd.DataFrame([[month] + row for row in _table if any(row)])
    assert len(table)

    table.columns = COLUMNS
    table[table.columns[2:]] = table[table.columns[2:]].map(parse_value)

    validate_data(table)

    return table


def parse_pdf(pdf):
    pdf_format = detect_pdf_format(pdf)
    
    if pdf_format == "daily":
        # For daily format PDFs, we'll return an empty DataFrame
        # as this format doesn't contain state-by-state data
        sys.stderr.write("Detected daily data format - skipping (no state-by-state data available)\n")
        return pd.DataFrame(columns=COLUMNS)
    elif pdf_format == "state":
        # Parse state-by-state format
        checks_dfs = [parse_page_state_format(page) for page in pdf.pages if page.page_number > 1]
        if not checks_dfs:
            return pd.DataFrame(columns=COLUMNS)
        checks = pd.concat(checks_dfs)
        return checks[~checks["state"].str.contains("Total")]
    else:
        raise Exception(f"Unknown PDF format - cannot parse")


def parse_page(page):
    """Legacy function - redirects to state format parser"""
    return parse_page_state_format(page)


if __name__ == "__main__":
    with pdfplumber.open(sys.argv[1]) as pdf:
        checks = parse_pdf(pdf)

    checks.to_csv(sys.stdout, index=False, float_format="%.0f")

    sys.stderr.write("\r\n")
