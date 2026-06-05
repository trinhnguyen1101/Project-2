"""
filter_sec_data.py
==================
Lọc dữ liệu SEC Financial Statement Data Sets, chỉ giữ lại 50 công ty mục tiêu.

Logic:
1. Tải mapping Ticker -> CIK từ SEC.gov
2. Lọc sub.txt theo CIK -> thu được danh sách adsh hợp lệ
3. Lọc num.txt và pre.txt theo adsh
4. Ghi đè file gốc bằng file đã lọc
5. Xóa các file .zip để giải phóng dung lượng
"""

import os
import sys
import io
import json
import urllib.request
import shutil
import glob
import time

# Fix encoding cho Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ============================================================
# Danh sách 50 Ticker mục tiêu
# ============================================================
TARGET_TICKERS = [
    # Technology (10)
    "AAPL", "MSFT", "NVDA", "INTC", "AMD", "CSCO", "ORCL", "IBM", "CRM", "ADBE",
    # Financial Services (10)
    "JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "BLK", "SCHW", "USB",
    # Healthcare (10)
    "JNJ", "PFE", "MRK", "ABBV", "BMY", "AMGN", "GILD", "MDT", "CVS", "UNH",
    # Consumer / Retail (10)
    "WMT", "COST", "HD", "LOW", "MCD", "KO", "PEP", "SBUX", "TGT", "NKE",
    # Energy & Industrials (10)
    "XOM", "CVX", "COP", "SLB", "EOG", "CAT", "DE", "GE", "HON", "UPS",
]

# ============================================================
# Đường dẫn gốc
# ============================================================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")


def fetch_ticker_to_cik():
    """Tải mapping Ticker -> CIK từ SEC.gov"""
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {"User-Agent": "ProjectSEC DataAnalysis (contact@example.com)"}
    req = urllib.request.Request(url, headers=headers)

    print("[INFO] Đang tải Ticker-CIK mapping từ SEC.gov ...")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    ticker_to_cik = {}
    for entry in data.values():
        ticker_to_cik[entry["ticker"].upper()] = entry["cik_str"]

    print(f"[INFO] Đã tải {len(ticker_to_cik)} ticker.")
    return ticker_to_cik


def resolve_target_ciks(ticker_to_cik):
    """Chuyển danh sách Ticker mục tiêu thành set CIK (dạng string)"""
    target_ciks = set()
    missing = []
    for ticker in TARGET_TICKERS:
        cik = ticker_to_cik.get(ticker.upper())
        if cik is not None:
            target_ciks.add(str(cik))
        else:
            missing.append(ticker)

    if missing:
        print(f"[WARNING] Không tìm thấy CIK cho: {missing}")

    print(f"[INFO] Số CIK mục tiêu: {len(target_ciks)}")
    return target_ciks


def get_column_index(header_line, col_name):
    """Lấy index của một cột trong dòng header (tab-delimited)"""
    cols = header_line.rstrip("\n").rstrip("\r").split("\t")
    try:
        return cols.index(col_name)
    except ValueError:
        return -1


def filter_sub_file(sub_path, target_ciks):
    """
    Lọc sub.txt: giữ lại dòng có CIK thuộc danh sách mục tiêu.
    Trả về set các adsh hợp lệ.
    """
    tmp_path = sub_path + ".filtered"
    valid_adshs = set()
    kept = 0
    total = 0

    with open(sub_path, "r", encoding="utf-8", errors="replace") as fin, \
         open(tmp_path, "w", encoding="utf-8") as fout:

        header = fin.readline()
        fout.write(header)

        cik_idx = get_column_index(header, "cik")
        adsh_idx = get_column_index(header, "adsh")

        if cik_idx < 0 or adsh_idx < 0:
            print(f"  [ERROR] Không tìm thấy cột cik/adsh trong {sub_path}")
            os.remove(tmp_path)
            return set()

        for line in fin:
            total += 1
            parts = line.split("\t")
            if len(parts) > max(cik_idx, adsh_idx):
                cik_val = parts[cik_idx].strip()
                if cik_val in target_ciks:
                    fout.write(line)
                    valid_adshs.add(parts[adsh_idx].strip())
                    kept += 1

    # Ghi đè file gốc
    os.replace(tmp_path, sub_path)
    print(f"  sub.txt: {kept}/{total} dòng giữ lại ({len(valid_adshs)} submissions)")
    return valid_adshs


def filter_by_adsh(file_path, valid_adshs):
    """
    Lọc num.txt hoặc pre.txt: giữ lại dòng có adsh trong tập hợp hợp lệ.
    """
    if not os.path.exists(file_path):
        print(f"  [SKIP] {os.path.basename(file_path)} không tồn tại.")
        return

    tmp_path = file_path + ".filtered"
    kept = 0
    total = 0

    with open(file_path, "r", encoding="utf-8", errors="replace") as fin, \
         open(tmp_path, "w", encoding="utf-8") as fout:

        header = fin.readline()
        fout.write(header)

        adsh_idx = get_column_index(header, "adsh")
        if adsh_idx < 0:
            print(f"  [ERROR] Không tìm thấy cột adsh trong {file_path}")
            os.remove(tmp_path)
            return

        for line in fin:
            total += 1
            parts = line.split("\t")
            if len(parts) > adsh_idx:
                if parts[adsh_idx].strip() in valid_adshs:
                    fout.write(line)
                    kept += 1

    os.replace(tmp_path, file_path)
    basename = os.path.basename(file_path)
    print(f"  {basename}: {kept}/{total} dòng giữ lại")


def filter_quarter(quarter_dir, target_ciks):
    """Lọc toàn bộ 1 thư mục quý (sub, num, pre)."""
    dir_name = os.path.basename(quarter_dir)
    print(f"\n{'='*50}")
    print(f"[PROCESSING] {dir_name}")
    print(f"{'='*50}")

    sub_path = os.path.join(quarter_dir, "sub.txt")
    num_path = os.path.join(quarter_dir, "num.txt")
    pre_path = os.path.join(quarter_dir, "pre.txt")

    if not os.path.exists(sub_path):
        print(f"  [SKIP] sub.txt không tồn tại trong {dir_name}")
        return

    # Bước 1: Lọc sub.txt -> lấy danh sách adsh hợp lệ
    valid_adshs = filter_sub_file(sub_path, target_ciks)

    if not valid_adshs:
        print(f"  [WARNING] Không tìm thấy submission nào cho công ty mục tiêu trong {dir_name}")
        return

    # Bước 2: Lọc num.txt và pre.txt theo adsh
    filter_by_adsh(num_path, valid_adshs)
    filter_by_adsh(pre_path, valid_adshs)

    print(f"[DONE] {dir_name} đã lọc xong.")


def delete_zip_files():
    """Xóa tất cả file .zip trong data/raw/ để giải phóng dung lượng."""
    zip_files = glob.glob(os.path.join(RAW_DIR, "*.zip"))
    if not zip_files:
        print("\n[INFO] Không tìm thấy file .zip nào để xóa.")
        return

    total_size = 0
    for zf in zip_files:
        size = os.path.getsize(zf)
        total_size += size
        os.remove(zf)
        print(f"  [DELETED] {os.path.basename(zf)} ({size / 1024 / 1024:.1f} MB)")

    print(f"[INFO] Đã xóa {len(zip_files)} file .zip, giải phóng {total_size / 1024 / 1024:.1f} MB")


def main():
    print("=" * 60)
    print("  SEC Data Filter - Lọc 50 công ty mục tiêu")
    print("=" * 60)
    print(f"[INFO] Thư mục raw: {RAW_DIR}")

    # 1. Lấy mapping Ticker -> CIK
    ticker_to_cik = fetch_ticker_to_cik()
    target_ciks = resolve_target_ciks(ticker_to_cik)

    # In ra mapping để kiểm tra
    print("\n[INFO] Mapping Ticker -> CIK:")
    for ticker in sorted(TARGET_TICKERS):
        cik = ticker_to_cik.get(ticker, "N/A")
        print(f"  {ticker:6s} -> {cik}")

    # 2. Tìm tất cả thư mục quý
    quarter_dirs = sorted([
        os.path.join(RAW_DIR, d)
        for d in os.listdir(RAW_DIR)
        if os.path.isdir(os.path.join(RAW_DIR, d)) and d not in (".git",)
    ])

    if not quarter_dirs:
        print("[ERROR] Không tìm thấy thư mục dữ liệu quý nào trong data/raw/")
        sys.exit(1)

    print(f"\n[INFO] Tìm thấy {len(quarter_dirs)} thư mục quý: {[os.path.basename(d) for d in quarter_dirs]}")

    # 3. Lọc từng quý
    start = time.time()
    for qdir in quarter_dirs:
        filter_quarter(qdir, target_ciks)

    elapsed = time.time() - start
    print(f"\n[INFO] Tổng thời gian lọc: {elapsed:.1f} giây")

    # 4. Xóa file .zip
    print("\n[INFO] Xóa các file .zip gốc ...")
    delete_zip_files()

    print("\n" + "=" * 60)
    print("  HOÀN TẤT!")
    print("=" * 60)


if __name__ == "__main__":
    main()
