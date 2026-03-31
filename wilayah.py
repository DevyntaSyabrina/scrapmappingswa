import requests

# URL sumber data wilayah Indonesia (Open Source by emsifa)
BASE_URL = "https://emsifa.github.io/api-wilayah-indonesia/api"

def get_provinces():
    """Mengambil daftar semua provinsi"""
    try:
        response = requests.get(f"{BASE_URL}/provinces.json")
        if response.status_code == 200:
            return response.json() # List of dict: [{'id': '11', 'name': 'ACEH'}, ...]
    except:
        return []
    return []

def get_regencies(province_id):
    """Mengambil daftar kota/kabupaten berdasarkan ID Provinsi"""
    try:
        response = requests.get(f"{BASE_URL}/regencies/{province_id}.json")
        if response.status_code == 200:
            return response.json()
    except:
        return []
    return []

def get_districts(regency_id):
    """Mengambil daftar kecamatan berdasarkan ID Kota/Kabupaten"""
    try:
        response = requests.get(f"{BASE_URL}/districts/{regency_id}.json")
        if response.status_code == 200:
            return response.json()
    except:
        return []
    return []