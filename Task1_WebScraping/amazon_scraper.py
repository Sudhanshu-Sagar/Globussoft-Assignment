"""
Amazon.in Laptop Scraper
========================
Scrapes laptop listings from Amazon.in and saves to a timestamped CSV.

Fields extracted per product:
  - Image URL
  - Title
  - Rating
  - Price
  - Ad / Organic

Usage:
    python amazon_scraper.py                       # default: 3 pages, headless
    python amazon_scraper.py --pages 5             # scrape 5 pages
    python amazon_scraper.py --no-headless         # show browser window
    python amazon_scraper.py --query "gaming laptop"
"""

import argparse
import csv
import os
import random
import time
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager

# ──────────────────────────────────────────────
# Constants / Config
# ──────────────────────────────────────────────

BASE_URL   = "https://www.amazon.in"
OUTPUT_DIR = "output"

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
]

# All CSS selectors centralised here — update this dict if Amazon changes layout
SELECTORS = {
    "product_card": [
        "div[data-component-type='s-search-result']",
        "div.s-result-item[data-asin]",
    ],
    "title": [
    "h2 a span",
    "h2 span",
    "[data-cy='title-recipe'] h2 a span",
    "[data-cy='title-recipe'] span",

    ],
    "price": [
        "span.a-price > span.a-offscreen",
        "span.a-price-whole",
        ".a-price .a-offscreen",
        "span[data-a-color='price'] span.a-offscreen",
    ],
    "rating": [
        "span.a-icon-alt",
        "i.a-icon-star-small span.a-icon-alt",
        "i[class*='a-star'] span.a-icon-alt",
    ],
    "image": [
        "img.s-image",
        "img[data-image-latency='s-product-image']",
        ".s-product-image-container img",
    ],
    "sponsored_text": [
        "span.s-label-popover-default",
        "span[data-component-type='s-status-badge-component']",
        ".puis-sponsored-label-text",
        "span.aok-inline-block.s-label-popover-default",
    ],
    "next_page": [
        "a.s-pagination-next",
        "li.a-last a",
        "a[aria-label='Go to next page']",
    ],
}


# ──────────────────────────────────────────────
# Driver Setup
# ──────────────────────────────────────────────

def build_driver(headless: bool = True) -> webdriver.Chrome:
    """Initialise Chrome with anti-detection settings and auto-managed driver."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # webdriver-manager downloads the correct ChromeDriver automatically —
    # no manual driver setup needed on any machine.
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )

    # Patch navigator.webdriver to avoid bot fingerprinting
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def random_sleep(min_s: float = 1.5, max_s: float = 3.5) -> None:
    """Mimic human browsing pauses."""
    time.sleep(random.uniform(min_s, max_s))


def first_match(soup_el, selectors: list) -> str:
    """Try each CSS selector in order; return stripped text of first hit."""
    for sel in selectors:
        tag = soup_el.select_one(sel)
        if tag:
            text = tag.get_text(strip=True)
            if text:
                return text
    return "N/A"


def extract_image(card) -> str:
    """
    Resolve product image URL handling Amazon's lazy-loading patterns.

    Priority order:
      1. src      – already loaded standard image
      2. data-src – deferred/lazy load
      3. srcset   – responsive image set; we pick the first URL
    """
    for sel in SELECTORS["image"]:
        tag = card.select_one(sel)
        if not tag:
            continue
        url = (
            tag.get("src")
            or tag.get("data-src")
            or (tag.get("srcset", "").split()[0] if tag.get("srcset") else None)
        )
        if url and url.startswith("http"):
            return url.strip()
    return "N/A"


def is_sponsored(card) -> str:
    """
    Detect whether a product card is Sponsored (Ad) or Organic.

    Strategy:
      1. Check known Amazon sponsored-badge selectors
      2. Fall back to scanning first 200 chars of card text
    """
    for sel in SELECTORS["sponsored_text"]:
        badge = card.select_one(sel)
        if badge:
            text = badge.get_text(strip=True).lower()
            if text in ("sponsored", "ad", "advertisement"):
                return "Ad"

    # Fallback: check intro text of card (avoids false positives deeper in reviews)
    intro = card.get_text(separator=" ", strip=True).lower()[:200]
    if "sponsored" in intro:
        return "Ad"

    return "Organic"


def is_captcha_page(page_source: str) -> bool:
    """Return True if Amazon is showing a CAPTCHA / robot-check page."""
    lower = page_source.lower()
    return (
        "captcha" in lower
        or "robot check" in lower
        or "api-services-support@amazon" in lower
        or 'id="captchacharacters"' in lower
    )


# ──────────────────────────────────────────────
# Core Scraping Logic
# ──────────────────────────────────────────────

def parse_page(page_source: str) -> list:
    """Parse one search-results page; return a list of product dicts."""
    soup = BeautifulSoup(page_source, "html.parser")
    products = []

    # Try each card selector until we get results
    cards = []
    for sel in SELECTORS["product_card"]:
        cards = soup.select(sel)
        if cards:
            break

    print(f"    Found {len(cards)} product cards on this page.")

    for card in cards:
        asin = card.get("data-asin", "").strip()

        # Skip filler/banner cards
        if not asin:
            continue

        # Extract title directly from product heading
        title_tag = card.select_one("h2 a span")

        if title_tag:
            title = title_tag.get_text(strip=True)
        else:
            title = first_match(card, SELECTORS["title"])

        # Skip invalid titles caused by sponsored labels
        if title.lower() in [
            "sponsored",
            "sponsoredsponsored",
            "ad",
            "advertisement",
        ]:
            continue

        price = first_match(card, SELECTORS["price"])
        rating = first_match(card, SELECTORS["rating"])
        image = extract_image(card)
        ad_type = is_sponsored(card)

        # Keep only numeric part of rating
        if rating != "N/A":
            parts = rating.split()
            rating = parts[0] if parts else rating

        products.append({
            "ASIN": asin,
            "Title": title,
            "Price": price,
            "Rating": rating,
            "Image": image,
            "Ad_Type": ad_type,
        })

    return products


def scrape_amazon(
    query:    str  = "laptop",
    pages:    int  = 3,
    headless: bool = True,
) -> pd.DataFrame:
    """
    Orchestrates the full scrape: open Amazon → search → page loop → DataFrame.

    Args:
        query:    Search term
        pages:    Number of result pages to scrape
        headless: Run Chrome without a visible window

    Returns:
        pandas DataFrame with all extracted products
    """
    all_products = []
    driver = build_driver(headless=headless)

    try:
        print(f"\n{'='*55}")
        print(f"  Amazon.in Laptop Scraper")
        print(f"  Query : {query!r}  |  Pages : {pages}")
        print(f"{'='*55}\n")

        # ── 1. Open Amazon.in ───────────────────────────────
        print("[1/4] Opening Amazon.in …")
        driver.get(BASE_URL)
        random_sleep(2, 4)

        # ── 2. Search ───────────────────────────────────────
        print(f"[2/4] Searching for '{query}' …")
        try:
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "twotabsearchtextbox"))
            )
            search_box.clear()
            search_box.send_keys(query)
            random_sleep(0.5, 1.2)
            search_box.send_keys(Keys.RETURN)
            random_sleep(2, 4)
        except TimeoutException:
            print("  ✗ Search box not found. Amazon may have changed its layout.")
            return pd.DataFrame()

        # ── 3. Page loop ────────────────────────────────────
        print("[3/4] Scraping pages …\n")

        for page_num in range(1, pages + 1):
            print(f"  ► Page {page_num}/{pages}  [{driver.current_url[:70]}…]")

            # CAPTCHA guard — check before attempting to parse
            if is_captcha_page(driver.page_source):
                print(
                    f"  ⚠ CAPTCHA detected on page {page_num}. Stopping scrape.\n"
                    "    Tip: re-run with --no-headless to solve it manually."
                )
                break

            # Scroll in two steps to trigger lazy-loaded images
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            random_sleep(1, 2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            random_sleep(1, 2)

            products = parse_page(driver.page_source)
            all_products.extend(products)
            print(f"    Running total: {len(all_products)} products\n")

            # Navigate to next page
            if page_num < pages:
                navigated = False
                for sel in SELECTORS["next_page"]:
                    try:
                        next_btn = driver.find_element(By.CSS_SELECTOR, sel)
                        driver.execute_script("arguments[0].click();", next_btn)
                        random_sleep(2.5, 4.5)
                        navigated = True
                        break
                    except NoSuchElementException:
                        continue

                if not navigated:
                    print("  ✗ No 'Next' button found. Stopping early.")
                    break

                # Guard newly loaded page for CAPTCHA too
                random_sleep(0.5, 1.0)
                if is_captcha_page(driver.page_source):
                    print("  ⚠ CAPTCHA detected after navigation. Stopping.")
                    break

    except WebDriverException as exc:
        print(f"\n  ✗ WebDriver error: {exc}")
    finally:
        driver.quit()

    # ── 4. Build DataFrame ──────────────────────────────────
    print("[4/4] Building DataFrame …")
    df = pd.DataFrame(all_products)
    if df.empty:
        print("  ✗ No products scraped. Check selectors or your network.")
        return df

    before = len(df)
    df.drop_duplicates(subset=["ASIN"], keep="first", inplace=True)
    print(f"  Removed {before - len(df)} duplicate ASINs.")
    print(f"  Final product count: {len(df)}\n")

    return df


# ──────────────────────────────────────────────
# Save to CSV
# ──────────────────────────────────────────────

def save_to_csv(df: pd.DataFrame, query: str) -> str:
    """Save DataFrame to a timestamped CSV; return the file path."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = query.replace(" ", "_").lower()
    filename   = f"amazon_{safe_query}_{timestamp}.csv"
    filepath   = os.path.join(OUTPUT_DIR, filename)

    df.to_csv(filepath, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
    print(f"  ✓ CSV saved → {filepath}")
    return filepath


# ──────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Amazon.in laptop listings and save to a timestamped CSV."
    )
    parser.add_argument(
        "--query", type=str, default="laptop",
        help="Search term (default: 'laptop')"
    )
    parser.add_argument(
        "--pages", type=int, default=3,
        help="Number of result pages to scrape (default: 3)"
    )
    parser.add_argument(
        "--no-headless", dest="headless", action="store_false", default=True,
        help="Show the browser window (default: headless mode)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    df = scrape_amazon(
        query    = args.query,
        pages    = args.pages,
        headless = args.headless,
    )

    if not df.empty:
        path = save_to_csv(df, args.query)

        has_ratings = any(df["Rating"] != "N/A")
        avg_rating  = (
            df.loc[df["Rating"] != "N/A", "Rating"].astype(float).mean()
            if has_ratings else None
        )

        print("\n" + "─" * 45)
        print("  SCRAPING SUMMARY")
        print("─" * 45)
        print(f"  Total products : {len(df)}")
        print(f"  Sponsored (Ad) : {(df['Ad_Type'] == 'Ad').sum()}")
        print(f"  Organic        : {(df['Ad_Type'] == 'Organic').sum()}")
        print(f"  Avg Rating     : {avg_rating:.2f}" if avg_rating else "  Avg Rating     : N/A")
        print(f"  Output file    : {path}")
        print("─" * 45 + "\n")
    else:
        print("\n  No data to save.")
