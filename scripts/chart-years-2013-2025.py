#!/usr/bin/env python
import sys
import os
import pdfplumber
import re

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sb
from matplotlib.ticker import StrMethodFormatter

sb.set()

def extract_monthly_totals_from_pdf():
    """Extract monthly totals from the daily PDF for smoother chart"""
    pdf_path = "pdfs/nics-checks-archive.pdf"
    monthly_data = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num == 0:  # Skip first page (cover)
                continue
                
            text = page.extract_text()
            
            # Look for year patterns
            year_match = re.search(r'Year (\d{4})', text)
            if year_match:
                year = int(year_match.group(1))
                
                # Find lines with daily data and aggregate by month
                lines = text.split('\n')
                monthly_totals = [0] * 12  # Initialize 12 months
                
                for line in lines:
                    if re.match(r'^\d{1,2}\s+[\d,\s]+$', line.strip()):
                        numbers = re.findall(r'[\d,]+', line)
                        try:
                            day_numbers = [int(num.replace(',', '')) for num in numbers[1:]]  # Skip day number
                            # Add daily values to monthly totals
                            for month_idx in range(min(12, len(day_numbers))):
                                monthly_totals[month_idx] += day_numbers[month_idx]
                        except ValueError:
                            continue
                
                # Create monthly records
                month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                
                for month_idx, month_total in enumerate(monthly_totals):
                    if month_total > 0:  # Only include months with data
                        month_date = f"{year}-{month_idx+1:02d}"
                        monthly_data.append({
                            'year': year, 
                            'month': month_idx + 1,
                            'date': month_date,
                            'total': month_total
                        })
    
    return pd.DataFrame(monthly_data).sort_values(['year', 'month'])

# Extract monthly data from PDF for smoother chart
monthly_df = extract_monthly_totals_from_pdf()

# Filter for years 2013-2025
year_filtered = monthly_df.loc[
    (monthly_df["year"] >= 2013) & (monthly_df["year"] <= 2025)
].copy()

# Convert date string to datetime for smooth plotting
year_filtered['date_dt'] = pd.to_datetime(year_filtered['date'])

# Create the plot
ax = year_filtered.plot(x="date_dt", y="total", kind="area", figsize=(14, 8), color="#1f77b4", alpha=0.7, legend=False)

ax.figure.set_facecolor("#FFFFFF")
ax.set_title("NICS Background Check Totals — Monthly Data 2013-2025", fontsize=24)

plt.setp(ax.get_yticklabels(), fontsize=12)
ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))

ax.set_xlabel("Year", fontsize=14)
ax.set_ylabel("Monthly Background Checks", fontsize=14)

# Set x-axis to show years nicely
import matplotlib.dates as mdates
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax.xaxis.set_minor_locator(mdates.MonthLocator((1, 7)))  # Show ticks at Jan and July

plt.tight_layout()
plt.savefig(sys.stdout.buffer)