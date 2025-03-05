# Web Scraper for Container Ship Data (Classdirect registry)

A Python-based web scraper using **Selenium** and **Beautiful Soup** to collect cargo, maintenance, and engine data on over 10,000 container ships. This scraper gathers vessel data from the online Classdirect registry.

## Features
- Collects data on cargo, maintenance, and engine specifics of container ships
- Outputs structured data for streamlined analysis

## Setup Instructions

### Prerequisites
- **Python 3.x**
- **Selenium**
- **Beautiful Soup**
- **Pandas**

### Running the Scraper

1. Create a `.xlsx` file containg the ID of ships under the header `links`
2. Edit the file path of the excel file in `scraper.py`
3. Run the following command:

   ```bash
   python scraper.py
