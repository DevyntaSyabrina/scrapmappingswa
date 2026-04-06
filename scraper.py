import time
import pandas as pd
import re 
import random 
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- USER AGENTS ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko Firefox/121.0"
]

# =========================================================
# ✅ FIX DRIVER (WAJIB UNTUK STREAMLIT CLOUD)
# =========================================================
def setup_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # random user agent
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")

    # ✅ path wajib untuk streamlit cloud
    options.binary_location = "/usr/bin/chromium"

    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        return driver
    except Exception as e:
        print("❌ ERROR DRIVER:", e)
        raise


# --- DELAY ---
def human_delay(a=1.0, b=2.0):
    time.sleep(random.uniform(a, b))


# =========================================================
# 🔍 EMAIL FILTER
# =========================================================
def find_email_pattern(text, company):
    if not text:
        return "N/A"
    
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, text)

    if emails:
        return list(set(emails))[0]

    return "N/A"


# =========================================================
# 🌐 SCRAPER DENGAN RETRY + DEBUG
# =========================================================
def scrape_google_maps(query, lokasi_target=None):

    for attempt in range(2):  # ✅ retry 2x
        driver = None

        try:
            print(f"\n🔎 START SCRAPING: {query}")
            driver = setup_driver()

            driver.get(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
            wait = WebDriverWait(driver, 20)

            # tunggu sidebar
            scrollable_div = wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
            )

            # ============================
            # 🔽 SCROLL
            # ============================
            last_height = driver.execute_script(
                "return arguments[0].scrollHeight", scrollable_div
            )

            for _ in range(10):
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div
                )
                human_delay(1.5, 2.5)

                new_height = driver.execute_script(
                    "return arguments[0].scrollHeight", scrollable_div
                )

                if new_height == last_height:
                    break

                last_height = new_height

            # ============================
            # 📊 AMBIL DATA
            # ============================
            items = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            print(f"📍 Total ditemukan: {len(items)}")

            data = []

            for i, item in enumerate(items[:20]):  # batasi 20 dulu biar stabil
                try:
                    driver.execute_script("arguments[0].scrollIntoView();", item)
                    driver.execute_script("arguments[0].click();", item)

                    human_delay(1, 2)

                    row = {
                        "Nama Perusahaan": "N/A",
                        "Alamat": "N/A",
                        "Telepon": "N/A",
                        "Website": "N/A",
                        "Email": "N/A",
                    }

                    try:
                        row["Nama Perusahaan"] = driver.find_element(
                            By.CSS_SELECTOR, "h1.DUwDvf"
                        ).text
                    except:
                        pass

                    details = driver.find_elements(By.CLASS_NAME, "Io6YTe")

                    for d in details:
                        txt = d.text

                        if "Jl" in txt:
                            row["Alamat"] = txt
                        elif txt.startswith("+62"):
                            row["Telepon"] = txt
                        elif "." in txt and " " not in txt:
                            row["Website"] = txt

                    # email dari halaman
                    body = driver.page_source
                    row["Email"] = find_email_pattern(body, row["Nama Perusahaan"])

                    print(f"✅ {row['Nama Perusahaan']}")
                    data.append(row)

                except Exception as e:
                    print("⚠️ ERROR ITEM:", e)
                    continue

            driver.quit()
            return data

        except Exception as e:
            print(f"❌ ERROR SCRAPING ATTEMPT {attempt+1}:", e)

            try:
                if driver:
                    driver.quit()
            except:
                pass

            time.sleep(3)

    print("❌ GAGAL TOTAL SCRAPING")
    return []
