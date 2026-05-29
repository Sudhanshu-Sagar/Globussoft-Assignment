# Amazon.in Laptop Scraper — Task 1

Scrapes laptop search results from **Amazon.in** using **Selenium + BeautifulSoup**
and saves all extracted data to a **timestamped CSV file**.

---

## Fields Extracted

| Field     | Description                               |
|-----------|-------------------------------------------|
| ASIN      | Amazon product ID                         |
| Title     | Product name                              |
| Price     | Listed price (₹)                          |
| Rating    | Star rating (e.g. `4.2`)                  |
| Image     | Direct URL to product thumbnail           |
| Ad_Type   | `Ad` (Sponsored) or `Organic`             |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> Chrome must be installed on your system.  
> ChromeDriver is managed automatically by `webdriver-manager` (optional) or  
> must match your Chrome version — download from https://chromedriver.chromium.org

### 2. Run the scraper

```bash
# Default — scrapes 3 pages of "laptop", headless mode
python amazon_scraper.py

# Custom query and page count
python amazon_scraper.py --query "gaming laptop" --pages 5

# Show browser window (non-headless, useful for debugging)
python amazon_scraper.py --no-headless
```

### 3. Output

Results are saved to the `output/` folder with a timestamp:

```
output/amazon_laptop_20260527_143022.csv
```

---

## Project Structure

```
task1/
├── amazon_scraper.py      ← Main script
├── requirements.txt       ← Dependencies
├── README.md              ← This file
└── output/
    └── amazon_laptop_<timestamp>.csv
```

---

## How It Works

1. **Launch Chrome** (headless by default) with anti-bot settings
2. **Search Amazon.in** for the given query
3. **For each page**: scroll to load lazy images → parse HTML with BeautifulSoup
4. **Extract** title, price, rating, image URL per product card
5. **Detect Sponsored vs Organic** by checking Amazon's sponsored badge labels
6. **Deduplicate** by ASIN across pages
7. **Export** to a UTF-8 timestamped CSV

---

## Notes

- Amazon's HTML layout changes frequently. If selectors break, update `SELECTORS`
  in `amazon_scraper.py` — all selectors are centralised in one dictionary.
- Random sleep intervals are used between page loads to mimic human behaviour.
- Use `--no-headless` to visually debug what the browser is doing.
