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

    options.binary_location = "/usr/bin/chromium"

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Anti detect
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

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def scrape_google_maps(query):

    for attempt in range(3):
        driver = None

        try:
            print(f"\n🔎 SCRAPING: {query}")

            driver = setup_driver()

            time.sleep(random.uniform(2, 4))

            url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}?hl=id"
            driver.get(url)

            time.sleep(7)

            wait = WebDriverWait(driver, 25)

            # cek blok
            if "unusual traffic" in driver.page_source.lower():
                print("❌ TERBLOCK GOOGLE")
                return []

            # =========================
            # COBA AMBIL FEED
            # =========================
            try:
                scrollable_div = wait.until(
                    EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
                )

                # scroll
                for _ in range(10):
                    driver.execute_script(
                        "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div
                    )
                    time.sleep(2)

                items = driver.find_elements(By.CLASS_NAME, "hfpxzc")

                if len(items) == 0:
                    items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/place/']")

                print(f"📊 ITEM DITEMUKAN: {len(items)}")

                data = []

                for item in items[:10]:
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
                            if "Jl" in d.text:
                                alamat = d.text

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

            # =========================
            # 🔥 FALLBACK MODE
            # =========================
            except:
                print("❌ FEED TIDAK DITEMUKAN → FALLBACK")

                if "google.com/search" in driver.current_url:
                    print("⚠️ Redirect ke Google Search")

                items = driver.find_elements(By.CSS_SELECTOR, "a")

                data = []

                for a in items:
                    try:
                        href = a.get_attribute("href")
                        text = a.text

                        if href and "/maps/place/" in href and text.strip() != "":
                            data.append({
                                "Nama Perusahaan": text.strip(),
                                "Alamat": "N/A"
                            })
                    except:
                        pass

                print(f"📊 FALLBACK DATA: {len(data)}")

                driver.quit()

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
