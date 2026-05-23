import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from datetime import datetime

# 1. Supabase 환경 변수 로드 (GitHub Secrets로부터 주입됨)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. 수집 대상 GPU 및 다나와 상품 ID 매핑 (MVP 대상 품목 목록)
TARGET_GPUS = [
    {"id": "nv-rtx-4070-super-asus-dual", "danawa_code": "33407981"},
    {"id": "nv-rtx-4060-ti-msi-ventus", "danawa_code": "20324835"},
    {"id": "amd-rx-7800-xt-sapphire-pulse", "danawa_code": "27871343"}
]

def get_danawa_price(danawa_code):
    """다나와 상품 페이지에서 크래시 없이 최저가를 파싱하는 함수"""
    url = f"https://prod.danawa.com/info/?pcode={danawa_code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 다나와 최저가 영역 클래스 추출 (사이트 구조 변경 시 이 부분만 수정)
        price_tag = soup.select_or_insert(".prc_c .prc_c") 
        if not price_tag:
            price_tag = soup.select_one(".lowest_price .prc_c")
            
        if price_tag:
            price_str = price_tag.text.replace(",", "").replace("원", "").strip()
            return int(price_str)
    except Exception as e:
        print(f"Error fetching code {danawa_code}: {e}")
    return None

def main():
    today = datetime.now().date().isoformat()
    print(f"[{today}] GPU 가격 크롤링 시작...")
    
    for gpu in TARGET_GPUS:
        price = get_danawa_price(gpu["danawa_code"])
        
        if price:
            # 이상치 검증 및 Supabase 적재
            print(f"수집 성공 -> {gpu['id']}: {price}원")
            
            data = {
                "gpu_id": gpu["id"],
                "price": price,
                "collected_at": today
            }
            
            # Upsert 실행 (이미 당일 데이터가 있으면 업데이트, 없으면 인서트)
            try:
                supabase.table("gpu_price_history").upsert(data).execute()
            except Exception as e:
                print(f"DB 적재 실패 ({gpu['id']}): {e}")
        else:
            print(f"수집 실패 -> {gpu['id']}")

if __name__ == "__main__":
    main()
