import streamlit as st
import pandas as pd
import time
import io
import concurrent.futures 
from wilayah import get_provinces, get_regencies, get_districts
from scraper import scrape_google_maps

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Market Intelligence & Public Sector Scraper", 
    layout="wide", 
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# --- 2. CUSTOM CSS (TEMA BIRU & FONT PROPOSIONAL) ---
st.markdown("""
    <style>
    /* BACKGROUND UTAMA */
    .stApp {
        background: #2980b9;
        background: -webkit-linear-gradient(to right, #6dd5fa, #2980b9);
        background: linear-gradient(to right, #6dd5fa, #2980b9);
        color: white;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background-color: #34495e;
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    
    /* TEKS JADI PUTIH */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div[data-testid="stRadio"] label,
    h1, h2, h3, h4, h5, h6, p, label, div.stMarkdown {
        color: #ffffff !important;
    }

    /* HEADER SIDEBAR (Diperbesar dari sebelumnya tapi tidak terlalu tebal) */
    [data-testid="stSidebar"] h3 {
        font-weight: 600 !important;
        font-size: 1.3rem !important;
        letter-spacing: 0.5px;
    }

    /* KEYWORD HIGHLIGHT DI LOG */
    .highlight-text {
        color: #2980b9 !important; 
        font-weight: 600;
    }

    /* INPUT FIELD */
    .stTextInput > div > div > input {
        background-color: #ffffff;
        color: #333333 !important;
        border-radius: 8px;
        border: none;
        font-size: 1rem;
    }
    .stSelectbox > div > div > div {
        background-color: #ffffff;
        color: #333333 !important;
        border-radius: 8px;
        font-size: 1rem;
    }
    
    /* TOMBOL */
    .stButton > button {
        background-color: #ffffff;
        color: #2980b9;
        font-weight: 700;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        font-size: 1.1rem;
    }
    .stButton > button:hover {
        background-color: #ecf0f1;
        color: #1c5980;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }

    /* TABEL HASIL */
    .result-container {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 20px;
        border-radius: 10px;
        color: #333333 !important;
        margin-top: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .result-container h3, .result-container p, .result-container div, .result-container span {
        color: #333333 !important;
    }

    /* PROGRESS BAR */
    .stProgress > div > div > div > div {
        background-color: #ffffff;
    }
    
    /* FOOTER */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #2c3e50;
        color: #bdc3c7;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        font-weight: 400;
        z-index: 999;
        border-top: 1px solid rgba(255,255,255,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR MENU ---
with st.sidebar:
    st.markdown("### ⚙️ Mode Aplikasi")
    
    mode = st.radio("Pilih Tujuan:", [
        "🔍 Cari Per Wilayah (Massal)", 
        "📍 Satu Provinsi Full (Semua Kota/Kab)",
        "🎯 Cari Spesifik + Nearby",
        "🇮🇩 ID Nasional (Publik Sektor)"
    ], index=3)
    
    st.markdown("---")
    
    target_list_loop = []   
    selected_area_name = "" 
    selected_prov_name = "" 
    selected_reg_name = "" 
    selected_kec_specific = "" 
    input_keyword = ""
    enable_nearby = False
    
    @st.cache_data
    def load_provinces(): return get_provinces()
    prov_data = load_provinces()
    prov_map = {item['name']: item['id'] for item in prov_data}
    
    if mode == "🇮🇩 ID Nasional (Publik Sektor)":
        st.markdown("### 📍 Konfigurasi Nasional")
        st.info("Robot mencari data di **38 Provinsi** otomatis.")
        input_keyword = st.text_input("Nama Instansi / Dinas", value="BNPB")
        st.caption("Contoh: 'Dinas Kesehatan', 'Kantor Pajak', 'BPS'")
        target_list_loop = [p['name'] for p in prov_data]
        selected_area_name = "Seluruh_Indonesia"

    elif mode == "📍 Satu Provinsi Full (Semua Kota/Kab)":
        st.markdown("### 📍 Konfigurasi Provinsi")
        selected_prov_name = st.selectbox("Pilih Provinsi", list(prov_map.keys()))
        @st.cache_data
        def load_regencies(id_prov): return get_regencies(id_prov)
        reg_data = load_regencies(prov_map[selected_prov_name])
        target_list_loop = [item['name'] for item in reg_data]
        selected_area_name = selected_prov_name
        input_keyword = st.text_input("Kategori Bisnis", value="Distributor Pupuk")

    elif mode == "🔍 Cari Per Wilayah (Massal)":
        st.markdown("### 📍 Lokasi Spesifik")
        selected_prov_name = st.selectbox("Pilih Provinsi", list(prov_map.keys()))
        @st.cache_data
        def load_regencies_mass(id_prov): return get_regencies(id_prov)
        reg_data = load_regencies_mass(prov_map[selected_prov_name])
        reg_map = {item['name']: item['id'] for item in reg_data}
        selected_reg_name = st.selectbox("Pilih Kota/Kabupaten", list(reg_map.keys()))
        
        dist_names = []
        if selected_reg_name:
            dist_data = get_districts(reg_map[selected_reg_name])
            dist_names = [item['name'] for item in dist_data]
            
        opsi = ["--- PILIH SEMUA KECAMATAN ---"] + dist_names
        pilihan_kec = st.selectbox("Target Kecamatan", opsi)
        
        if pilihan_kec == "--- PILIH SEMUA KECAMATAN ---":
            target_list_loop = dist_names
        else:
            target_list_loop = [pilihan_kec]
            
        selected_area_name = selected_reg_name
        input_keyword = st.text_input("Kategori Bisnis", value="Klinik Kecantikan")

    else: 
        st.markdown("### 📍 Lokasi Target")
        selected_prov_name = st.selectbox("Pilih Provinsi", list(prov_map.keys()))
        reg_data = get_regencies(prov_map[selected_prov_name])
        reg_map = {item['name']: item['id'] for item in reg_data}
        selected_reg_name = st.selectbox("Pilih Kota/Kabupaten", list(reg_map.keys()))
        
        dist_names = []
        if selected_reg_name:
            dist_data = get_districts(reg_map[selected_reg_name])
            dist_names = [item['name'] for item in dist_data]
        
        selected_kec_specific = st.selectbox("Target Kecamatan", dist_names)
        selected_area_name = f"{selected_kec_specific}_{selected_reg_name}"
        input_keyword = st.text_input("Nama Perusahaan", value="Indomaret")
        st.markdown("---")
        enable_nearby = st.checkbox("📡 Aktifkan Nearby", value=True)

    st.markdown("---")
    max_workers = 1

# --- 4. TAMPILAN UTAMA (HEADER BARU) ---
# Ukuran dikembalikan besar (2.6rem) tapi font-weight semi-bold (600) agar tidak terlihat norak
st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 5px; margin-top: 10px;">
        <span style="font-size: 2.8rem; margin-right: 15px; color: white !important;">🏢</span>
        <div>
            <h1 style="margin: 0; padding: 0; font-size: 2.6rem; font-weight: 600 !important; letter-spacing: 0.5px;">Market Intelligence & Public Sector Scraper</h1>
        </div>
    </div>
""", unsafe_allow_html=True)

st.markdown('<p style="font-size: 1.1rem; opacity: 0.9; margin-bottom: 30px; font-weight: 400;">Aplikasi scraping data bisnis, analisis lingkungan (Nearby), dan <b>Data Sektor Publik Nasional</b>.</p>', unsafe_allow_html=True)

def process_single_area(area_name, keyword, mode_type, parent_area, prov_name):
    try:
        if mode_type == "🇮🇩 ID Nasional (Publik Sektor)":
            query = f"{keyword} di {area_name}"
        elif mode_type == "📍 Satu Provinsi Full (Semua Kota/Kab)":
            query = f"{keyword} di {area_name}, {prov_name}"
        else:
            query = f"{keyword} di Kecamatan {area_name}, {parent_area}"

        st.write(f"🔎 Query: {query}")

        hasil = scrape_google_maps(query, lokasi_target=area_name)

        st.write(f"📊 Hasil ditemukan: {len(hasil)}")

        if hasil:
            df = pd.DataFrame(hasil)
            df['Lokasi/Wilayah'] = area_name
            return df

    except Exception as e:
        st.error(f"❌ Error process area: {e}")

    return pd.DataFrame()

# --- 5. LOG DISPLAY ---
# Menghilangkan background putih dan mengubah teks keyword menjadi Kuning Terang agar kontras
if mode == "🇮🇩 ID Nasional (Publik Sektor)":
    log_title = f"Log: Scraping Nasional <span style='color: #ffeb3b !important; font-weight: 700;'>{input_keyword}</span> (38 Provinsi)"
elif mode == "📍 Satu Provinsi Full (Semua Kota/Kab)":
    log_title = f"Log: Scraping Provinsi <span style='color: #ffeb3b !important; font-weight: 700;'>{selected_prov_name}</span>"
else:
    log_title = f"Log: Memproses <span style='color: #ffeb3b !important; font-weight: 700;'>{input_keyword}</span>"

st.markdown(f'<h2 style="font-size: 1.6rem; font-weight: 500 !important; margin-bottom: 20px;">{log_title}</h2>', unsafe_allow_html=True)

status_container = st.empty()
progress_bar = st.progress(0)
detail_text = st.empty()

# --- 6. EKSEKUSI ---
if st.button("🚀 MULAI SCRAPING", use_container_width=True):
    
    all_results_df = pd.DataFrame()
    
    if mode in ["🇮🇩 ID Nasional (Publik Sektor)", "📍 Satu Provinsi Full (Semua Kota/Kab)", "🔍 Cari Per Wilayah (Massal)"]:
        total_items = len(target_list_loop)
        completed_count = 0
        status_container.info(f"🚀 Memulai {max_workers} robot worker...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_area = {executor.submit(process_single_area, area, input_keyword, mode, selected_area_name, selected_prov_name): area for area in target_list_loop}
            
            for future in concurrent.futures.as_completed(future_to_area):
                area = future_to_area[future]
                detail_text.markdown(f"<span style='font-size: 1rem; opacity: 0.9;'>ID Memproses Wilayah: {area} ({completed_count + 1}/{total_items})...</span>", unsafe_allow_html=True)
                try:
                    df_result = future.result()
                    if not df_result.empty:
                        all_results_df = pd.concat([all_results_df, df_result], ignore_index=True)
                except Exception: pass
                
                completed_count += 1
                persen = int((completed_count / total_items) * 100)
                progress_bar.progress(persen)

    else:
        progress_bar.progress(20)
        detail_text.markdown(f"<span style='font-size: 1rem; opacity: 0.9;'>🎯 Mencari Target: {input_keyword}...</span>", unsafe_allow_html=True)
        query_main = f"{input_keyword} di Kecamatan {selected_kec_specific}, {selected_reg_name}"
        try:
            hasil_main = scrape_google_maps(query_main, lokasi_target=selected_kec_specific)
            if hasil_main:
                df_main = pd.DataFrame(hasil_main)
                df_main['Lokasi/Wilayah'] = selected_kec_specific
                df_main['Status'] = "TARGET UTAMA"
                all_results_df = pd.concat([all_results_df, df_main], ignore_index=True)
        except: pass

        if enable_nearby and not all_results_df.empty:
            progress_bar.progress(50)
            keywords_radar = ["PT", "CV", "Bank", "Pabrik", "Logistik", "Kantor Dinas"]
            detail_text.markdown("<span style='font-size: 1rem; opacity: 0.9;'>📡 Menjalankan Analisis Lingkungan Sekitar...</span>", unsafe_allow_html=True)
            def process_radar(kw):
                q = f"{kw} di sekitar {input_keyword} Kecamatan {selected_kec_specific}, {selected_reg_name}"
                res = scrape_google_maps(q, lokasi_target=None)
                if res:
                    dfr = pd.DataFrame(res)
                    dfr = dfr[~dfr['Nama Perusahaan'].str.lower().str.contains(input_keyword.lower())]
                    if not dfr.empty:
                        dfr['Lokasi/Wilayah'] = "Radius Sekitar"
                        dfr['Status'] = f"NEARBY ({kw})"
                        return dfr
                return pd.DataFrame()

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(process_radar, kw) for kw in keywords_radar]
                for future in concurrent.futures.as_completed(futures):
                    res_df = future.result()
                    if not res_df.empty:
                        all_results_df = pd.concat([all_results_df, res_df], ignore_index=True)

    progress_bar.progress(100)
    detail_text.markdown("<span style='font-size: 1rem; font-weight: 500;'>✅ Proses Selesai!</span>", unsafe_allow_html=True)
    status_container.success("✅ Ekstraksi Data Berhasil Diselesaikan!")
    
    st.write("DEBUG TOTAL DATA:", len(all_results_df))
    if not all_results_df.empty:
        all_results_df = all_results_df.drop_duplicates(subset=['Nama Perusahaan', 'Alamat'])
        st.markdown('<div class="result-container">', unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 📊 Hasil Data Scraper")
            st.markdown(f"**Total Data Ditemukan:** {len(all_results_df)} Entitas")
        
        st.dataframe(df, width="stretch")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            all_results_df.to_excel(writer, index=False, sheet_name='Data Scraper')
        buffer.seek(0)
        label_file = input_keyword.replace(" ", "_")
        if mode == "🇮🇩 ID Nasional (Publik Sektor)": final_area = "NASIONAL_RI"
        elif mode == "📍 Satu Provinsi Full (Semua Kota/Kab)": final_area = f"PROVINSI_{selected_prov_name}"
        else: final_area = selected_area_name
        
        with col2:
            st.download_button(label="⬇️ Download Excel", data=buffer, file_name=f"Report_{label_file}_{final_area}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ Data tidak ditemukan.")

# --- FOOTER BARU ---
st.markdown("""
    <div class="footer">
        © 2025 Copyright by <b>duo gen-Z ITS</b> | All Rights Reserved
    </div>
    """, unsafe_allow_html=True)
