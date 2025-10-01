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

def extract_fall_months_from_pdf():
    """Extract September, October, November totals from the daily PDF"""
    pdf_path = "pdfs/nics-checks-archive.pdf"
    fall_data = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num == 0:  # Skip first page (cover)
                continue
                
            text = page.extract_text()
            
            # Look for year patterns
            year_match = re.search(r'Year (\d{4})', text)
            if year_match:
                year = int(year_match.group(1))
                
                # Find daily data lines and extract fall months (columns 9, 10, 11)
                lines = text.split('\n')
                monthly_totals = [0] * 12  # Initialize 12 months
                
                for line in lines:
                    if re.match(r'^\d{1,2}\s+[\d,\s]+$', line.strip()):
                        numbers = re.findall(r'[\d,]+', line)
                        try:
                            day_numbers = [int(num.replace(',', '')) for num in numbers[1:]]  # Skip day number
                            if len(day_numbers) >= 12:  # Make sure we have all 12 months
                                for i in range(12):
                                    if i < len(day_numbers):
                                        monthly_totals[i] += day_numbers[i]
                        except (ValueError, IndexError):
                            continue
                
                # Extract Sep (index 8), Oct (index 9), Nov (index 10)
                if len(monthly_totals) >= 11:
                    fall_data.append({'year': year, 'month': 9, 'month_name': 'Sep', 'total': monthly_totals[8]})
                    fall_data.append({'year': year, 'month': 10, 'month_name': 'Oct', 'total': monthly_totals[9]})
                    fall_data.append({'year': year, 'month': 11, 'month_name': 'Nov', 'total': monthly_totals[10]})
    
    return pd.DataFrame(fall_data)

# Extract fall months data from PDF
fall_df = extract_fall_months_from_pdf()

if fall_df.empty:
    print("No fall months data found")
    sys.exit(1)

# Filter for years 1988-2024 (limited by available data)
fall_filtered = fall_df.loc[
    (fall_df["year"] >= 1999) & (fall_df["year"] <= 2024)  # PDF data starts from 1999
]

# Create year-month labels for plotting
fall_filtered['year_month'] = fall_filtered['year'].astype(str) + '-' + fall_filtered['month_name']
fall_filtered = fall_filtered.sort_values(['year', 'month'])

# Create the plot
fig, ax = plt.subplots(figsize=(16, 8))

# Create bar positions
years = sorted(fall_filtered['year'].unique())
x_pos = []
labels = []
colors = []
values = []

color_map = {'Sep': '#d62728', 'Oct': '#ff7f0e', 'Nov': '#2ca02c'}

pos = 0
for year in years:
    year_data = fall_filtered[fall_filtered['year'] == year]
    for _, row in year_data.iterrows():
        x_pos.append(pos)
        labels.append(f"{row['month_name']}\n{year}")
        colors.append(color_map[row['month_name']])
        values.append(row['total'])
        pos += 1
    pos += 0.5  # Add space between years

bars = ax.bar(x_pos, values, color=colors, alpha=0.8)

ax.set_facecolor("#FFFFFF")
fig.patch.set_facecolor("#FFFFFF")
ax.set_title("NICS Background Check Totals — Fall Months (Sep, Oct, Nov) 1999-2024", fontsize=20)

ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
ax.set_ylabel("Total Background Checks", fontsize=12)

# Set x-axis labels (every 3rd label to avoid crowding)
ax.set_xticks(x_pos[::3])
ax.set_xticklabels([labels[i] for i in range(0, len(labels), 3)], rotation=45, ha='right')

# Add legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#d62728', alpha=0.8, label='September'),
    Patch(facecolor='#ff7f0e', alpha=0.8, label='October'), 
    Patch(facecolor='#2ca02c', alpha=0.8, label='November')
]
ax.legend(handles=legend_elements, loc='upper left')

plt.tight_layout()
plt.savefig(sys.stdout.buffer)