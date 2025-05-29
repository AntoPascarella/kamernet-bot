from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json
import os
import requests

BOT_TOKEN = '8044501305:AAFbrgEeH7QAq3YejRGO8lHW_P2_lE99pZc' 
CHAT_ID = '-4973676986'         

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=data)
    if not response.ok:
        print("❌ Failed to send message:", response.text)


SEEN_FILE = "seen.json"

def load_seen_urls():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r") as f:
        return set(json.load(f))

def save_seen_urls(urls):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(urls), f, indent=2)

LISTINGS_URL = "https://kamernet.nl/en/for-rent/room-amsterdam?listingTypes=1&searchview=1&maxRent=800&minSize=2&radius=5&pageNo=1&sort=1"

def fetch_listings():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    print("Loading page...")
    driver.get(LISTINGS_URL)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[class*='MuiLink-root'][href*='/room-']"))
        )
    except Exception as e:
        print("⚠️ Timeout or page error:", e)
        driver.quit()
        return []

    listings = []
    elements = driver.find_elements(By.CSS_SELECTOR, "a[class*='MuiLink-root'][href*='/room-']")

    for item in elements:
        try:
            url = item.get_attribute("href").strip()
            if "/room-" not in url or url == "https://kamernet.nl/en/for-rent/room-amsterdam":
                continue  # skip generic or non-listing URLs


            lines = item.text.strip().split("\n")
            lines = [line.strip() for line in lines if line.strip()]

            price_line = next((l for l in lines if "€" in l), "€?")

            # Fix for split title/address
            title_line = ""
            for i, line in enumerate(lines):
                if "," in line and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line and next_line[0].isupper():
                        title_line = f"{line} {next_line}"
                        break
            if not title_line:
                title_line = next((l for l in lines if "," in l), lines[0])

            listings.append({
                "title": title_line,
                "price": price_line,
                "url": url
            })
        except Exception as e:
            print("⚠️ Error parsing listing:", e)




    driver.quit()
    return listings


if __name__ == "__main__":
    data = fetch_listings()

    # Compare current data with seen listings
    seen_urls = load_seen_urls()
    new_listings = [l for l in data if l["url"] not in seen_urls]

    # Print and save
    print(f"\n✅ Found {len(new_listings)} new listings:\n")
    for listing in new_listings:
        print(f"{listing['title']} - {listing['price']}")
        print(listing['url'], "\n")
        message = f"*{listing['title']}* - {listing['price']}\n{listing['url']}"
        send_telegram_message(message)

    # Save updated seen list
    all_urls = seen_urls.union({l["url"] for l in new_listings})
    save_seen_urls(all_urls)

    


