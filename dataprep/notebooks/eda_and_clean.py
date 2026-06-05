"""
eda_and_clean.py
================
EDA + Data Cleaning cho SEC Financial Statement Data Sets.

Script này thực hiện:
  1. EDA: Khảo sát dữ liệu (shape, dtypes, missing, duplicates, outliers)
  2. CLEAN: Làm sạch dữ liệu và xuất ra file sạch
  3. Xuất báo cáo EDA ra file HTML

Cách dùng:
  python dataprep/notebooks/eda_and_clean.py
"""

import os
import sys
import io
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# Fix encoding cho Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ============================================================
# Paths
# ============================================================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
REPORT_DIR = os.path.join(PROJECT_ROOT, "dataprep", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

SUB_FILE = os.path.join(PROCESSED_DIR, "sub_all.csv")
NUM_FILE = os.path.join(PROCESSED_DIR, "num_all.csv")
PRE_FILE = os.path.join(PROCESSED_DIR, "pre_all.csv")


# ==============================================================
# HELPER FUNCTIONS
# ==============================================================
def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_basic_info(df, name):
    """In thông tin cơ bản về DataFrame."""
    print(f"\n--- {name} ---")
    print(f"  Shape: {df.shape[0]:,} dòng x {df.shape[1]} cột")
    print(f"  Memory: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    print(f"  Columns: {df.columns.tolist()}")


def print_missing(df, name):
    """In chi tiết về missing values."""
    print(f"\n--- Missing Values: {name} ---")
    missing = df.isnull().sum()
    missing_pct = (df.isnull().sum() / len(df) * 100).round(2)
    missing_df = pd.DataFrame({
        "missing_count": missing,
        "missing_pct": missing_pct,
        "dtype": df.dtypes
    })
    # Chỉ hiện cột có missing > 0
    has_missing = missing_df[missing_df["missing_count"] > 0].sort_values("missing_pct", ascending=False)
    if has_missing.empty:
        print("  => Không có missing values!")
    else:
        print(has_missing.to_string())


def print_duplicates(df, name, key_cols):
    """Kiểm tra duplicates theo khóa."""
    dup_count = df.duplicated(subset=key_cols, keep=False).sum()
    print(f"\n--- Duplicates: {name} (key={key_cols}) ---")
    print(f"  Tổng dòng trùng: {dup_count:,} / {len(df):,} ({dup_count/len(df)*100:.2f}%)")
    return dup_count


def print_value_counts(df, col, name, top_n=10):
    """In phân bố giá trị top-N."""
    print(f"\n--- Value Counts: {name}.{col} (top {top_n}) ---")
    vc = df[col].value_counts().head(top_n)
    for val, cnt in vc.items():
        print(f"  {val:20s} : {cnt:>8,} ({cnt/len(df)*100:.1f}%)")


# ==============================================================
# EDA: SUB (Submissions)
# ==============================================================
def eda_sub(df):
    section("EDA: SUB (Submissions)")
    print_basic_info(df, "sub_all")

    # Dtypes
    print(f"\n--- Dtypes ---")
    print(df.dtypes.to_string())

    # Missing
    print_missing(df, "sub_all")

    # Duplicates
    print_duplicates(df, "sub_all", ["adsh"])

    # Phân bố form types
    print_value_counts(df, "form", "sub_all")

    # Phân bố theo quarter
    print_value_counts(df, "quarter", "sub_all", top_n=44)

    # Phân bố fiscal year (fy)
    print(f"\n--- Fiscal Year (fy) range ---")
    print(f"  Min: {df['fy'].min()}, Max: {df['fy'].max()}")
    print(f"  Value Counts:")
    fy_counts = df["fy"].value_counts().sort_index()
    for fy, cnt in fy_counts.items():
        print(f"    {int(fy):>6d} : {cnt:>5,}")

    # Kiểm tra number of CIKs (unique companies)
    print(f"\n--- Unique Companies ---")
    print(f"  Unique CIK: {df['cik'].nunique()}")
    print(f"  Unique Name: {df['name'].nunique()}")

    # Kiểm tra period format
    print(f"\n--- Period column ---")
    print(f"  Dtype: {df['period'].dtype}")
    print(f"  Sample: {df['period'].head(5).tolist()}")
    print(f"  Min: {df['period'].min()}, Max: {df['period'].max()}")


# ==============================================================
# EDA: NUM (Numbers)
# ==============================================================
def eda_num(df):
    section("EDA: NUM (Numbers)")
    print_basic_info(df, "num_all")

    # Dtypes
    print(f"\n--- Dtypes ---")
    print(df.dtypes.to_string())

    # Missing
    print_missing(df, "num_all")

    # Duplicates
    print_duplicates(df, "num_all", ["adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg"])

    # Value column stats
    print(f"\n--- Value column statistics ---")
    print(f"  Count:  {df['value'].count():>15,}")
    print(f"  Null:   {df['value'].isnull().sum():>15,}")
    print(f"  Mean:   {df['value'].mean():>20,.2f}")
    print(f"  Median: {df['value'].median():>20,.2f}")
    print(f"  Min:    {df['value'].min():>20,.2f}")
    print(f"  Max:    {df['value'].max():>20,.2f}")
    print(f"  Std:    {df['value'].std():>20,.2f}")

    # Outlier detection (IQR method) on value
    q1 = df["value"].quantile(0.25)
    q3 = df["value"].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = df[(df["value"] < lower) | (df["value"] > upper)]
    print(f"\n--- Outliers (IQR method) on 'value' ---")
    print(f"  Q1:          {q1:>20,.2f}")
    print(f"  Q3:          {q3:>20,.2f}")
    print(f"  IQR:         {iqr:>20,.2f}")
    print(f"  Lower bound: {lower:>20,.2f}")
    print(f"  Upper bound: {upper:>20,.2f}")
    print(f"  Outliers:    {len(outliers):>10,} / {len(df):,} ({len(outliers)/len(df)*100:.1f}%)")

    # UOM (Unit of Measure)
    print_value_counts(df, "uom", "num_all")

    # qtrs distribution
    print(f"\n--- qtrs (quarters) distribution ---")
    print(df["qtrs"].value_counts().sort_index().to_string())

    # Top tags by frequency
    print(f"\n--- Top 20 tags by frequency ---")
    tag_counts = df["tag"].value_counts().head(20)
    for i, (tag, cnt) in enumerate(tag_counts.items(), 1):
        print(f"  {i:>2}. {tag:50s} : {cnt:>8,}")

    # ddate (date) range
    print(f"\n--- ddate range ---")
    print(f"  Min: {df['ddate'].min()}, Max: {df['ddate'].max()}")

    # Negative values
    neg_count = (df["value"] < 0).sum()
    zero_count = (df["value"] == 0).sum()
    print(f"\n--- Negative & Zero values ---")
    print(f"  Negative: {neg_count:>10,} ({neg_count/len(df)*100:.1f}%)")
    print(f"  Zero:     {zero_count:>10,} ({zero_count/len(df)*100:.1f}%)")


# ==============================================================
# EDA: PRE (Presentation)
# ==============================================================
def eda_pre(df):
    section("EDA: PRE (Presentation)")
    print_basic_info(df, "pre_all")

    # Dtypes
    print(f"\n--- Dtypes ---")
    print(df.dtypes.to_string())

    # Missing
    print_missing(df, "pre_all")

    # Duplicates
    print_duplicates(df, "pre_all", ["adsh", "report", "line"])

    # Statement types (stmt)
    print_value_counts(df, "stmt", "pre_all")

    # rfile distribution
    print_value_counts(df, "rfile", "pre_all")


# ==============================================================
# CLEANING RECOMMENDATIONS
# ==============================================================
def analyze_cleaning_needs(sub, num, pre):
    section("DATA CLEANING — PHÂN TÍCH VÀ ĐỀ XUẤT")

    issues = []

    # --- SUB ---
    print("\n[SUB] Phân tích...")

    # 1. Missing values trong các cột quan trọng
    important_sub_cols = ["adsh", "cik", "name", "sic", "form", "period", "fy", "fp", "filed"]
    for col in important_sub_cols:
        m = sub[col].isnull().sum()
        if m > 0:
            issues.append(f"SUB.{col}: {m} missing values")
            print(f"  [!] {col}: {m} missing")

    # 2. Cột former/changed — metadata lịch sử, nhiều null là bình thường
    former_null = sub["former"].isnull().sum()
    print(f"  [i] former: {former_null} null ({former_null/len(sub)*100:.0f}%) — bình thường (cột metadata lịch sử)")

    # 3. Cột bas2, mas2 — dòng địa chỉ phụ, nhiều null là bình thường
    for col in ["bas2", "mas2"]:
        n = sub[col].isnull().sum()
        print(f"  [i] {col}: {n} null ({n/len(sub)*100:.0f}%) — bình thường (địa chỉ phụ)")

    # 4. Kiểm tra period format
    period_bad = sub[~sub["period"].astype(str).str.match(r"^\d{8}$")]
    if len(period_bad) > 0:
        issues.append(f"SUB.period: {len(period_bad)} dòng format không hợp lệ")
        print(f"  [!] period: {len(period_bad)} dòng format không phải YYYYMMDD")

    # 5. prevrpt (previous report) — nên loại bỏ các báo cáo sửa đổi
    prevrpt_count = (sub["prevrpt"] == 1).sum()
    print(f"  [?] prevrpt=1 (báo cáo sửa đổi): {prevrpt_count} dòng")
    if prevrpt_count > 0:
        issues.append(f"SUB.prevrpt: {prevrpt_count} báo cáo sửa đổi (nên xem xét loại)")

    # --- NUM ---
    print("\n[NUM] Phân tích...")

    # 1. Value null
    val_null = num["value"].isnull().sum()
    if val_null > 0:
        issues.append(f"NUM.value: {val_null} null values")
        print(f"  [!] value: {val_null} null ({val_null/len(num)*100:.2f}%)")

    # 2. Segments — phân mảnh, nhiều dòng có segments => dữ liệu segment-level
    seg_not_null = num["segments"].notna().sum()
    print(f"  [?] segments: {seg_not_null} dòng có segment ({seg_not_null/len(num)*100:.1f}%) — cân nhắc chỉ giữ consolidated")

    # 3. coreg — co-registrant, thường null
    coreg_not_null = num["coreg"].notna().sum()
    print(f"  [?] coreg: {coreg_not_null} dòng có co-registrant ({coreg_not_null/len(num)*100:.1f}%)")

    # 4. footnote — thường null
    fn_not_null = num["footnote"].notna().sum()
    print(f"  [i] footnote: {fn_not_null} dòng có footnote ({fn_not_null/len(num)*100:.1f}%)")

    # 5. Kiểm tra ddate format
    ddate_bad = num[~num["ddate"].astype(str).str.match(r"^\d{8}$")]
    if len(ddate_bad) > 0:
        issues.append(f"NUM.ddate: {len(ddate_bad)} format lỗi")
        print(f"  [!] ddate: {len(ddate_bad)} dòng format không hợp lệ")

    # --- PRE ---
    print("\n[PRE] Phân tích...")
    pre_missing = pre.isnull().sum()
    for col in pre.columns:
        m = pre[col].isnull().sum()
        if m > 0:
            print(f"  [?] {col}: {m} null ({m/len(pre)*100:.1f}%)")

    # --- TÓM TẮT ---
    section("TÓM TẮT VẤN ĐỀ CẦN XỬ LÝ")
    if not issues:
        print("  Không phát hiện vấn đề nghiêm trọng!")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")

    return issues


# ==============================================================
# CLEANING EXECUTION
# ==============================================================
def clean_sub(df):
    """Làm sạch bảng SUB."""
    print("\n[CLEAN] sub_all ...")
    original = len(df)

    # 1. Loại bỏ duplicates theo adsh (giữ dòng đầu tiên)
    df = df.drop_duplicates(subset=["adsh"], keep="first")
    print(f"  - Drop duplicate adsh: {original - len(df)} dòng")

    # 2. Loại bỏ báo cáo sửa đổi (prevrpt=1), chỉ giữ báo cáo gốc
    before = len(df)
    df = df[df["prevrpt"] == 0]
    print(f"  - Drop prevrpt=1 (báo cáo sửa đổi): {before - len(df)} dòng")

    # 3. Chuẩn hóa period -> datetime string (YYYY-MM-DD)
    df["period"] = pd.to_datetime(df["period"].astype(str), format="%Y%m%d", errors="coerce")
    bad_period = df["period"].isnull().sum()
    if bad_period > 0:
        print(f"  - Period parse errors: {bad_period} dòng (giữ lại, đánh dấu NaT)")

    # 4. Chuẩn hóa filed -> datetime
    df["filed"] = pd.to_datetime(df["filed"].astype(str), format="%Y%m%d", errors="coerce")

    # 5. Drop các cột ít giá trị phân tích
    drop_cols = ["bas2", "mas2", "baph", "former", "changed", "aciks", "instance", "detail"]
    existing_drop = [c for c in drop_cols if c in df.columns]
    df = df.drop(columns=existing_drop)
    print(f"  - Drop {len(existing_drop)} cột metadata thừa: {existing_drop}")

    # 6. Chuẩn hóa tên công ty (strip whitespace, upper)
    df["name"] = df["name"].str.strip().str.upper()

    print(f"  => Kết quả: {len(df):,} dòng, {df.shape[1]} cột")
    return df


def clean_num(df):
    """Làm sạch bảng NUM."""
    print("\n[CLEAN] num_all ...")
    original = len(df)

    # 1. Drop rows where value is null
    before = len(df)
    df = df.dropna(subset=["value"])
    print(f"  - Drop value=null: {before - len(df)} dòng")

    # 2. Drop duplicates
    key_cols = ["adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg"]
    before = len(df)
    df = df.drop_duplicates(subset=key_cols, keep="first")
    print(f"  - Drop duplicates: {before - len(df)} dòng")

    # 3. Chỉ giữ dữ liệu consolidated (segments = null) để phân tích ở cấp công ty
    before = len(df)
    df_consolidated = df[df["segments"].isna()].copy()
    print(f"  - Filter consolidated only (segments=null): loại {before - len(df_consolidated)} dòng segment-level")
    df = df_consolidated

    # 4. Drop cột coreg (hầu hết null) và footnote (ít giá trị)
    drop_cols = ["coreg", "footnote", "segments"]
    existing_drop = [c for c in drop_cols if c in df.columns]
    df = df.drop(columns=existing_drop)
    print(f"  - Drop cột: {existing_drop}")

    # 5. Chuẩn hóa ddate -> datetime
    df["ddate"] = pd.to_datetime(df["ddate"].astype(str), format="%Y%m%d", errors="coerce")

    print(f"  => Kết quả: {len(df):,} dòng, {df.shape[1]} cột")
    return df


def clean_pre(df):
    """Làm sạch bảng PRE."""
    print("\n[CLEAN] pre_all ...")
    original = len(df)

    # 1. Drop duplicates
    before = len(df)
    df = df.drop_duplicates(subset=["adsh", "report", "line"], keep="first")
    print(f"  - Drop duplicates: {before - len(df)} dòng")

    # 2. Chỉ giữ các statement chính: BS, IS, CF, EQ, CI
    valid_stmts = ["BS", "IS", "CF", "EQ", "CI"]
    before = len(df)
    df = df[df["stmt"].isin(valid_stmts)]
    print(f"  - Filter valid statements ({valid_stmts}): loại {before - len(df)} dòng")

    print(f"  => Kết quả: {len(df):,} dòng, {df.shape[1]} cột")
    return df


# ==============================================================
# MAIN
# ==============================================================
def main():
    section("SEC Financial Data — EDA & Cleaning")

    # --- Load data ---
    print("\n[LOAD] Đang đọc dữ liệu...")
    sub = pd.read_csv(SUB_FILE)
    num = pd.read_csv(NUM_FILE)
    pre = pd.read_csv(PRE_FILE)
    print(f"  sub: {sub.shape[0]:,} x {sub.shape[1]}")
    print(f"  num: {num.shape[0]:,} x {num.shape[1]}")
    print(f"  pre: {pre.shape[0]:,} x {pre.shape[1]}")

    # ========== PHASE 1: EDA ==========
    eda_sub(sub)
    eda_num(num)
    eda_pre(pre)

    # ========== PHASE 2: CLEANING ANALYSIS ==========
    issues = analyze_cleaning_needs(sub, num, pre)

    # ========== PHASE 3: CLEAN ==========
    section("CLEANING — THỰC HIỆN LÀM SẠCH")
    sub_clean = clean_sub(sub)
    num_clean = clean_num(num)
    pre_clean = clean_pre(pre)

    # ========== PHASE 4: SAVE ==========
    section("LƯU DỮ LIỆU SẠCH")
    sub_out = os.path.join(PROCESSED_DIR, "sub_clean.csv")
    num_out = os.path.join(PROCESSED_DIR, "num_clean.csv")
    pre_out = os.path.join(PROCESSED_DIR, "pre_clean.csv")

    sub_clean.to_csv(sub_out, index=False)
    num_clean.to_csv(num_out, index=False)
    pre_clean.to_csv(pre_out, index=False)

    print(f"\n  Đã lưu:")
    for name, path in [("sub_clean.csv", sub_out), ("num_clean.csv", num_out), ("pre_clean.csv", pre_out)]:
        size = os.path.getsize(path) / 1024 / 1024
        rows = sum(1 for _ in open(path, encoding="utf-8")) - 1
        print(f"    {name:16s} | {rows:>10,} dòng | {size:>8.2f} MB")

    # ========== SUMMARY ==========
    section("SO SÁNH TRƯỚC/SAU")
    print(f"  {'Dataset':<12} {'Trước':>12} {'Sau':>12} {'Giảm':>10}")
    print(f"  {'-'*46}")
    for name, before, after in [
        ("sub", len(sub), len(sub_clean)),
        ("num", len(num), len(num_clean)),
        ("pre", len(pre), len(pre_clean)),
    ]:
        pct = (1 - after/before) * 100 if before > 0 else 0
        print(f"  {name:<12} {before:>12,} {after:>12,} {pct:>8.1f}%")

    print("\n" + "="*60)
    print("  HOÀN TẤT!")
    print("="*60)


if __name__ == "__main__":
    main()
