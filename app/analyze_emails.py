import pandas as pd
import matplotlib.pyplot as plt
import json
import re
import os
from datetime import datetime


LOG_FILE = 'app/email_logs.json'
OUTPUT_PNG = 'app/email_relevance_chart.png'
PORTFOLIO_CSV = 'app/resource/portfolio.csv'

# Load JSON lines into DataFrame
def load_email_logs(log_file):
    
    if not os.path.exists(log_file):
        print(f"Error: {log_file} not found. Run the app to generate emails first!")
        return pd.DataFrame()
    
    logs = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  
    
    df = pd.DataFrame(logs)
    if df.empty:
        print("No valid logs found. Generate some emails!")
        return df
    
    # Compute relevance %
    df['total_links'] = 2
    df['relevance_pct'] = (df['included_links_count'] / df['total_links']) * 100
    
    print(f"Loaded {len(df)} emails. Avg relevance: {df['relevance_pct'].mean():.1f}%")
    return df

# Generate bar chart: % emails by number of links included
def generate_chart(df, output_png):
    if df.empty:
        print("No data for chart.")
        return
    
    bins = [0, 1, 2, 3, float('inf')]
    labels = ['0 Links', '1 Link', '2 Links', '3+ Links']
    df['bin'] = pd.cut(df['included_links_count'], bins=bins, labels=range(len(labels)), right=False)
    chart_data = df['bin'].value_counts(normalize=True).sort_index() * 100
    chart_data = chart_data.reindex(range(len(labels)), fill_value=0)  
    
    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, chart_data, color=['#FF6384', '#FFCE56', '#36A2EB', '#4BC0C0'])
    plt.title(f'Link Inclusion (n={len(df)} Emails)')
    plt.ylabel('% of Emails')
    plt.ylim(0, 100)
    plt.xticks(rotation=45, ha='right')
    for bar, val in zip(bars, chart_data):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{val:.0f}%', ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart saved: {output_png}")
    
if __name__ == "__main__":
    df = load_email_logs(LOG_FILE)
    if not df.empty:
        generate_chart(df, OUTPUT_PNG)
        