import time
import pandas as pd
import re 
import random 
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- DAFTAR IDENTITAS (USER-AGENTS) ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]

# --- KONFIGURASI DRIVER ---
def setup_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # USER AGENT
    random_agent = random.choice(USER_AGENTS)
    options.add_argument(f"user-agent={random_agent}")

    # ✅ PENTING: path chrome untuk streamlit cloud
    options.binary_location = "/usr/bin/chromium"

    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        return driver
    except Exception as e:
        print("❌ Gagal start driver:", e)
        raise
        
# --- HELPER: JEDA MANUSIA ---
def human_delay(min_seconds=1.0, max_seconds=2.0):
    time.sleep(random.uniform(min_seconds, max_seconds))

# --- HELPER: FILTER EMAIL & TEXT ---
def is_relevant_email(email, company_name):
    # Logika filter email tetap sama (sudah bagus)
    email = email.lower()
    official_words = ["admin", "info", "contact", "kantor", "sekretariat", "humas", "marketing", "sales", "cs", "sekolah", "kepsek", "tu.", "tatausaha", "lapor", "pengaduan", "layanan"]
    if any(word in email for word in official_words): return True
    
    generic_domains = ["gmail.com", "yahoo.com", "yahoo.co.id", "hotmail.com", "outlook.com", "ymail.com"]
    domain = email.split("@")[-1]
    if domain not in generic_domains: return True 
    
    # Cek kemiripan nama
    name_clean = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
    email_clean = re.sub(r'[^a-zA-Z0-9]', '', email.split("@")[0].lower())
    
    # Jika sebagian nama perusahaan ada di email -> OK
    if len(name_clean) > 3 and name_clean[:4] in email_clean: return True
    
    return False

def find_email_pattern(text_source, company_name):
    if not text_source: return "N/A"
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text_source)
    valid_emails = []
    if emails:
        unique_emails = list(set(emails))
        for e in unique_emails:
            if e.lower().endswith(('.png', '.jpg', '.gif', 'wix.com', 'sentry.io', 'google.com', 'facebook.com', 'twitter.com')): continue
            if is_relevant_email(e, company_name): valid_emails.append(e)
    if valid_emails: return ", ".join(valid_emails[:1]) 
    return "N/A"

def find_employee_count_pattern(text_source):
    if not text_source: return None
    pattern = r'([0-9,]+(?:\+|-[0-9,]+)?)\s+(?:employees|karyawan|pengikut)'
    match = re.search(pattern, text_source, re.IGNORECASE)
    if match: return match.group(1).replace(",", ".") 
    return None

def estimate_employee_by_entity(name):
    name_upper = name.upper()
    if "TBK" in name_upper or "(PERSERO)" in name_upper: return "> 500"
    elif "PT" in name_upper: return "20 - 100"
    elif "CV" in name_upper: return "5 - 20"
    elif "UD" in name_upper or "TOKO" in name_upper: return "1 - 10"
    elif "DINAS" in name_upper or "KEMENTERIAN" in name_upper: return "Instansi Pemerintah"
    else: return "N/A"

# --- HELPER: SOSMED ---
def get_social_media_and_employees(driver, company_name, city):
    result = {"LinkedIn": "N/A", "Instagram": "N/A", "Range Karyawan": "N/A"}
    try:
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        
        query = f"{company_name} {city} LinkedIn Instagram official"
        driver.get(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        human_delay(1.0, 2.0)
        
        links = driver.find_elements(By.CSS_SELECTOR, "div.yuRUbf a")
        for res in links:
            href = res.get_attribute("href")
            if not href: continue
            
            if "linkedin.com/" in href and result["LinkedIn"] == "N/A":
                blacklist = ["/in/", "/jobs/", "/dir/", "/pulse/", "/people/", "/learning/", "/login", "/search"]
                if not any(bad_word in href for bad_word in blacklist):
                    result["LinkedIn"] = href
            
            elif "instagram.com/" in href and result["Instagram"] == "N/A":
                if not any(x in href for x in ["/p/", "/reels/", "/explore/", "google.com"]):
                    result["Instagram"] = href

        body_text = driver.find_element(By.TAG_NAME, "body").text
        found_emp = find_employee_count_pattern(body_text)
        
        if found_emp: result["Range Karyawan"] = found_emp
        else: result["Range Karyawan"] = estimate_employee_by_entity(company_name)
        
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
    except:
        result["Range Karyawan"] = estimate_employee_by_entity(company_name)
        if len(driver.window_handles) > 1: driver.switch_to.window(driver.window_handles[0])  
    return result

def extract_email_from_website(driver, url, company_name):
    email_found = "N/A"
    try:
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        try:
            driver.get(url)
            human_delay(1.5, 2.5)
            page_source = driver.page_source
            email_found = find_email_pattern(page_source, company_name)
        except: pass
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
    except:
        if len(driver.window_handles) > 1: driver.switch_to.window(driver.window_handles[0])
    return email_found

def find_email_via_google_search(driver, company_name, city):
    email_found = "N/A"
    try:
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        search_query = f'{company_name} {city} email contact "@gmail.com" OR "@yahoo.com"'
        driver.get(f"https://www.google.com/search?q={search_query.replace(' ', '+')}")
        human_delay(1.0, 2.0)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        email_found = find_email_pattern(body_text, company_name)
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
    except:
        if len(driver.window_handles) > 1: driver.switch_to.window(driver.window_handles[0])
    return email_found

# === MAIN SCRAPER (VERSI DEEP SCROLL - NO LIMIT) ===
def scrape_google_maps(query, lokasi_target=None):
    driver = setup_driver()
    data = []
    
    try:
        print(f"🔎 Query: {query}")
        driver.get(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
        wait = WebDriverWait(driver, 20)
        
        # Cek apakah sidebar hasil pencarian muncul
        try:
            scrollable_div = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]')))
        except: 
            print("❌ Sidebar tidak ditemukan (mungkin hasil kosong)")
            return []

        # === UPDATE 1: SCROLL SAMPAI MENTOK (DEEP SCROLL) ===
        last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
        max_scroll_attempts = 20 # Maksimal 20 kali scroll (bisa dapat 100+ data)
        
        for _ in range(max_scroll_attempts):
            driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div)
            human_delay(1.5, 3.0) # Wajib jeda biar loading
            
            # Cek apakah sudah mentok bawah
            new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
            if new_height == last_height:
                # Coba scroll sekali lagi buat memastikan
                human_delay(2.0, 3.0)
                new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
                if new_height == last_height:
                    break # Sudah mentok beneran
            last_height = new_height

        # === UPDATE 2: AMBIL SEMUA DATA (NO LIMIT) ===
        items = driver.find_elements(By.CLASS_NAME, "hfpxzc")
        print(f"📍 Ditemukan {len(items)} entitas di Google Maps. Mulai ekstrak...")
        
        # Loop semua items (TIDAK ADA [:15] LAGI)
        for idx, item in enumerate(items): 
            try:
                # Scroll ke elemen biar kelihatan (kadang error kalau elemen di luar layar)
                driver.execute_script("arguments[0].scrollIntoView();", item)
                
                link_maps = item.get_attribute("href")
                
                # Klik elemen untuk memunculkan detail di panel kanan
                driver.execute_script("arguments[0].click();", item)
                human_delay(0.5, 1.5) 

                row = {
                    "Nama Perusahaan": "N/A", "Alamat": "N/A", "Range Karyawan": "N/A",
                    "Telepon": "N/A", "Website": "N/A", "Email": "N/A",
                    "LinkedIn": "N/A", "Instagram": "N/A", "Link Maps": link_maps
                }

                try: row["Nama Perusahaan"] = driver.find_element(By.CSS_SELECTOR, "h1.DUwDvf").text
                except: pass

                # Ambil detail (Alamat, Telp, Web)
                details = driver.find_elements(By.CLASS_NAME, "Io6YTe")
                for d in details:
                    txt = d.text
                    if not txt: continue
                    if any(x in txt for x in ["Jl.", "Jalan", "Kec.", "Kab.", "Kota", "Blok", "Ruko"]):
                        row["Alamat"] = txt
                    elif txt.replace(" ", "").replace("-", "").isdigit() or txt.startswith("+62"):
                        row["Telepon"] = txt
                    elif "." in txt and " " not in txt and "maps" not in txt and "Jl." not in txt and ":" not in txt:
                        row["Website"] = txt

                # === UPDATE 3: FILTER LOKASI DILONGGARKAN ===
                # Dulu: Kalau tidak ada kata "Gubeng" -> Skip.
                # Sekarang: Kita ambil saja semuanya. Biarkan user memfilter manual di Excel.
                # Kenapa? Karena Google sering nulis alamat cuma "Surabaya" padahal aslinya di Gubeng.
                # Kita percayakan pada hasil search query Google.
                
                if row["Nama Perusahaan"] != "N/A":
                    kota_simple = lokasi_target if lokasi_target else "Indonesia"
                    
                    # Ekstrak Info Tambahan
                    extra_info = get_social_media_and_employees(driver, row["Nama Perusahaan"], kota_simple)
                    row.update(extra_info)
                    
                    if row["Website"] != "N/A":
                        url_web = row["Website"] if row["Website"].startswith("http") else "http://" + row["Website"]
                        row["Email"] = extract_email_from_website(driver, url_web, row["Nama Perusahaan"])
                    
                    if row["Email"] == "N/A":
                        row["Email"] = find_email_via_google_search(driver, row["Nama Perusahaan"], kota_simple)

                    print(f"✅ ({idx+1}/{len(items)}) {row['Nama Perusahaan']} | 📧 {row['Email']}")
                    data.append(row)

            except Exception as e: 
                # print(f"Error item: {e}")
                continue

    finally:
        driver.quit()
    
    return data
