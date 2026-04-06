import time
import random

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_driver():
    options = Options()

    # WAJIB STREAMLIT
    options.binary_location = "/usr/bin/chromium"

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # 🔥 ANTI DETECT
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=Service("/usr/bin/chromedriver"),
        options=options
    )

    # 🔥 HILANGKAN DETEKSI SELENIUM
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def scrape_google_maps(query, lokasi_target=None):

    for attempt in range(3):  # retry 3x
        driver = None

        try:
            print(f"\n🔎 SCRAPING: {query}")

            driver = setup_driver()

            url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
            driver.get(url)

            time.sleep(7)  # WAJIB

            wait = WebDriverWait(driver, 25)

            # 🔥 CEK BLOCK GOOGLE
            if "unusual traffic" in driver.page_source.lower():
                print("❌ TERBLOCK GOOGLE")
                return []

            # =========================
            # SCROLL AREA
            # =========================
            try:
                scrollable_div = wait.until(
                    EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
                )
            except:
                print("❌ FEED TIDAK DITEMUKAN")
                print(driver.page_source[:1000])  # DEBUG
                return []

            # SCROLL DALAM
            for _ in range(10):
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div
                )
                time.sleep(2)

            # =========================
            # AMBIL LIST ITEM (FALLBACK)
            # =========================
            items = driver.find_elements(By.CLASS_NAME, "hfpxzc")

            # 🔥 FALLBACK kalau kosong
            if len(items) == 0:
                print("⚠️ hfpxzc kosong → pakai fallback")
                items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/place/']")

            print(f"📊 ITEM DITEMUKAN: {len(items)}")

            data = []

            for i, item in enumerate(items[:10]):  # limit biar stabil
                try:
                    driver.execute_script("arguments[0].click();", item)
                    time.sleep(3)

                    nama = "N/A"
                    alamat = "N/A"

                    try:
                        nama = driver.find_element(By.CSS_SELECTOR, "h1.DUwDvf").text
                    except:
                        pass

                    detail = driver.find_elements(By.CLASS_NAME, "Io6YTe")

                    for d in detail:
                        txt = d.text
                        if "Jl" in txt:
                            alamat = txt

                    if nama != "N/A":
                        data.append({
                            "Nama Perusahaan": nama,
                            "Alamat": alamat
                        })

                        print(f"✅ {nama}")

                except Exception as e:
                    print("⚠️ ERROR ITEM:", e)

            driver.quit()

            if len(data) > 0:
                return data

        except Exception as e:
            print(f"❌ ERROR ATTEMPT {attempt+1}:", e)

            try:
                if driver:
                    driver.quit()
            except:
                pass

            time.sleep(5)

    print("❌ GAGAL TOTAL")
    return []
