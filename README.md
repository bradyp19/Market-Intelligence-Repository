![Market Intelligence Logo](assets/logo.png)

# Market Intelligence Agent

A Python-based tool that automatically collects, analyzes, and summarizes product announcements from major tech and data companies.

## Features

- Scrapes product announcements and press releases from company websites
- Extracts key features and strategic positioning
- Groups features by themes (Product Features, Integrations, Performance, etc.)
- Generates formatted summary posts with headlines, introductions, and bullet points
- Saves summaries as markdown files

## Supported Companies

- Snowflake
- Databricks
- Domo
- Tableau
- PowerBI
- Denodo
- Starburst

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the agent:
   ```bash
   python main.py
   ```

## Output

Summaries are saved in the `summaries` directory as markdown files. Each summary includes:
- Headline
- Company name and date
- Brief introduction
- Themed feature lists
- Source link

## Configuration

You can modify the following in `config.py`:
- Company sources and URLs
- Product announcement keywords
- Maximum articles per company
- Output directory

## Requirements

- Python 3.7+
- See `requirements.txt` for package dependencies 