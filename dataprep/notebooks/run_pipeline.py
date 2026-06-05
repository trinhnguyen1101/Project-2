"""
run_pipeline.py
================
Script tổng hợp:
  1. Lọc dữ liệu SEC (filter) — chỉ giữ 50 công ty mục tiêu
  2. Gộp (merge) tất cả quý thành 3 file CSV trong data/processed/
  3. Xóa file .zip gốc để giải phóng dung lượng

Cách dùng:
  python dataprep/notebooks/run_pipeline.py
"""

import os
import sys
import io
import json
import csv
import urllib.request
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
# Đường dẫn
# ============================================================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

# Các file cần lọc và gộp
DATA_FILES = ["sub.txt", "num.txt", "pre.txt"]

# File đánh dấu thư mục đã được lọc
FILTER_MARKER = ".filtered_done"


# ==============================================================
# PHẦN 1: FETCH TICKER -> CIK
# ==============================================================
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
        ticker_to_cik[entry["ticker"].upper()] = str(entry["cik_str"])

    print(f"[INFO] Đã tải {len(ticker_to_cik)} ticker.")
    return ticker_to_cik


def resolve_target_ciks(ticker_to_cik):
    """Chuyển danh sách Ticker -> set CIK (string)"""
    target_ciks = set()
    missing = []
    for ticker in TARGET_TICKERS:
        cik = ticker_to_cik.get(ticker.upper())
        if cik is not None:
            target_ciks.add(cik)
        else:
            missing.append(ticker)

    if missing:
        print(f"[WARNING] Không tìm thấy CIK cho: {missing}")
    print(f"[INFO] Số CIK mục tiêu: {len(target_ciks)}")
    return target_ciks


# ==============================================================
# PHẦN 2: FILTER — Lọc từng thư mục quý
# ==============================================================
def get_col_idx(header_line, col_name):
    """Lấy index cột trong dòng header (tab-delimited)"""
    cols = header_line.rstrip("\r\n").split("\t")
    try:
        return cols.index(col_name)
    except ValueError:
        return -1


def filter_sub(sub_path, target_ciks):
    """Lọc sub.txt theo CIK, trả về set adsh hợp lệ."""
    tmp = sub_path + ".tmp"
    valid_adshs = set()
    kept = total = 0

    with open(sub_path, "r", encoding="utf-8", errors="replace") as fin, \
         open(tmp, "w", encoding="utf-8") as fout:
        header = fin.readline()
        fout.write(header)
        cik_idx = get_col_idx(header, "cik")
        adsh_idx = get_col_idx(header, "adsh")
        if cik_idx < 0 or adsh_idx < 0:
            print(f"  [ERROR] Không tìm thấy cột cik/adsh trong sub.txt")
            os.remove(tmp)
            return set()

        for line in fin:
            total += 1
            parts = line.split("\t")
            if len(parts) > max(cik_idx, adsh_idx):
                if parts[cik_idx].strip() in target_ciks:
                    fout.write(line)
                    valid_adshs.add(parts[adsh_idx].strip())
                    kept += 1

    os.replace(tmp, sub_path)
    print(f"  sub.txt: {kept:,}/{total:,} dòng giữ lại ({len(valid_adshs)} submissions)")
    return valid_adshs


def filter_by_adsh(file_path, valid_adshs):
    """Lọc num.txt hoặc pre.txt theo adsh."""
    if not os.path.exists(file_path):
        print(f"  [SKIP] {os.path.basename(file_path)} không tồn tại.")
        return

    tmp = file_path + ".tmp"
    kept = total = 0

    with open(file_path, "r", encoding="utf-8", errors="replace") as fin, \
         open(tmp, "w", encoding="utf-8") as fout:
        header = fin.readline()
        fout.write(header)
        adsh_idx = get_col_idx(header, "adsh")
        if adsh_idx < 0:
            print(f"  [ERROR] Không tìm thấy cột adsh trong {os.path.basename(file_path)}")
            os.remove(tmp)
            return

        for line in fin:
            total += 1
            parts = line.split("\t")
            if len(parts) > adsh_idx and parts[adsh_idx].strip() in valid_adshs:
                fout.write(line)
                kept += 1

    os.replace(tmp, file_path)
    print(f"  {os.path.basename(file_path)}: {kept:,}/{total:,} dòng giữ lại")


def is_already_filtered(quarter_dir):
    """Kiểm tra thư mục đã lọc chưa (dựa vào marker file)"""
    return os.path.exists(os.path.join(quarter_dir, FILTER_MARKER))


def mark_filtered(quarter_dir):
    """Đánh dấu thư mục đã lọc xong"""
    with open(os.path.join(quarter_dir, FILTER_MARKER), "w") as f:
        f.write(f"filtered_at={time.strftime('%Y-%m-%d %H:%M:%S')}\n")


def filter_quarter(quarter_dir, target_ciks):
    """Lọc 1 thư mục quý."""
    name = os.path.basename(quarter_dir)

    if is_already_filtered(quarter_dir):
        print(f"\n[SKIP] {name} — đã lọc trước đó.")
        return True

    print(f"\n{'='*50}")
    print(f"[FILTER] {name}")
    print(f"{'='*50}")

    sub_path = os.path.join(quarter_dir, "sub.txt")
    if not os.path.exists(sub_path):
        print(f"  [SKIP] sub.txt không tồn tại.")
        return False

    valid_adshs = filter_sub(sub_path, target_ciks)
    if not valid_adshs:
        print(f"  [WARNING] Không tìm thấy submission nào cho công ty mục tiêu.")
        return False

    filter_by_adsh(os.path.join(quarter_dir, "num.txt"), valid_adshs)
    filter_by_adsh(os.path.join(quarter_dir, "pre.txt"), valid_adshs)

    mark_filtered(quarter_dir)
    print(f"[DONE] {name} — lọc xong.")
    return True


# ==============================================================
# PHẦN 3: MERGE — Gộp tất cả quý thành CSV
# ==============================================================
def merge_all_quarters(quarter_dirs):
    """
    Gộp sub.txt, num.txt, pre.txt từ tất cả quý
    thành 3 file CSV (comma-separated) trong data/processed/
    Thêm cột 'quarter' ở đầu mỗi dòng.
    """
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    output_map = {
        "sub.txt": os.path.join(PROCESSED_DIR, "sub_all.csv"),
        "num.txt": os.path.join(PROCESSED_DIR, "num_all.csv"),
        "pre.txt": os.path.join(PROCESSED_DIR, "pre_all.csv"),
    }

    for data_file, out_path in output_map.items():
        print(f"\n[MERGE] Gộp {data_file} -> {os.path.basename(out_path)}")
        total_rows = 0
        header_written = False

        with open(out_path, "w", encoding="utf-8", newline="") as fout:
            writer = None

            for qdir in quarter_dirs:
                quarter_name = os.path.basename(qdir)  # e.g. "2025q1"
                src = os.path.join(qdir, data_file)
                if not os.path.exists(src):
                    print(f"  [SKIP] {quarter_name}/{data_file} — không tồn tại")
                    continue

                with open(src, "r", encoding="utf-8", errors="replace") as fin:
                    header_line = fin.readline().rstrip("\r\n")
                    cols = header_line.split("\t")

                    if not header_written:
                        # Ghi header: thêm cột "quarter" ở đầu
                        writer = csv.writer(fout)
                        writer.writerow(["quarter"] + cols)
                        header_written = True

                    for line in fin:
                        row = line.rstrip("\r\n").split("\t")
                        writer.writerow([quarter_name] + row)
                        total_rows += 1

                print(f"  + {quarter_name}: xong")

        print(f"  => Tổng: {total_rows:,} dòng -> {os.path.basename(out_path)}")
        size_mb = os.path.getsize(out_path) / 1024 / 1024
        print(f"  => Dung lượng: {size_mb:.2f} MB")


# ==============================================================
# PHẦN 4: XÓA ZIP
# ==============================================================
def delete_zip_files():
    """Xóa tất cả file .zip trong data/raw/"""
    zip_files = glob.glob(os.path.join(RAW_DIR, "*.zip"))
    if not zip_files:
        print("\n[INFO] Không có file .zip nào để xóa.")
        return
    total_size = 0
    for zf in zip_files:
        size = os.path.getsize(zf)
        total_size += size
        os.remove(zf)
        print(f"  [DELETED] {os.path.basename(zf)} ({size / 1024 / 1024:.1f} MB)")
    print(f"[INFO] Đã xóa {len(zip_files)} file .zip, giải phóng {total_size / 1024 / 1024:.1f} MB")


# ==============================================================
# MAIN
# ==============================================================
def main():
    print("=" * 60)
    print("  SEC Data Pipeline: Filter + Merge")
    print("=" * 60)
    print(f"[INFO] Raw dir : {RAW_DIR}")
    print(f"[INFO] Output  : {PROCESSED_DIR}")

    # --- Bước 1: Lấy CIK ---
    ticker_to_cik = fetch_ticker_to_cik()
    target_ciks = resolve_target_ciks(ticker_to_cik)

    # --- Bước 2: Tìm thư mục quý ---
    quarter_dirs = sorted([
        os.path.join(RAW_DIR, d)
        for d in os.listdir(RAW_DIR)
        if os.path.isdir(os.path.join(RAW_DIR, d)) and d not in (".git",)
    ])

    if not quarter_dirs:
        print("[ERROR] Không tìm thấy thư mục dữ liệu quý nào.")
        sys.exit(1)

    names = [os.path.basename(d) for d in quarter_dirs]
    print(f"[INFO] Tìm thấy {len(quarter_dirs)} thư mục quý: {names}")

    # --- Bước 3: Lọc từng quý ---
    start = time.time()
    for qdir in quarter_dirs:
        filter_quarter(qdir, target_ciks)
    filter_time = time.time() - start
    print(f"\n[INFO] Thời gian lọc: {filter_time:.1f} giây")

    # --- Bước 4: Gộp thành CSV ---
    print("\n" + "=" * 60)
    print("  MERGE: Gộp dữ liệu các quý")
    print("=" * 60)
    merge_all_quarters(quarter_dirs)

    # --- Bước 5: Xóa .zip ---
    print("\n[INFO] Kiểm tra và xóa file .zip ...")
    delete_zip_files()

    # --- Tóm tắt ---
    print("\n" + "=" * 60)
    print("  KẾT QUẢ")
    print("=" * 60)
    for fname in ["sub_all.csv", "num_all.csv", "pre_all.csv"]:
        fpath = os.path.join(PROCESSED_DIR, fname)
        if os.path.exists(fpath):
            size = os.path.getsize(fpath) / 1024 / 1024
            # Đếm số dòng (trừ header)
            with open(fpath, "r", encoding="utf-8") as f:
                lines = sum(1 for _ in f) - 1
            print(f"  {fname:16s} | {lines:>10,} dòng | {size:>8.2f} MB")

    print(f"\n  Tổng thời gian: {time.time() - start:.1f} giây")
    print("=" * 60)
    print("  HOÀN TẤT!")
    print("=" * 60)


if __name__ == "__main__":
    main()
