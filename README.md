# Project 2: Financial Data Analysis (2015-2025)

## Giới thiệu
Dự án phân tích dữ liệu tài chính từ **SEC.gov | Financial Statement Data Sets**. 
Mục tiêu: Phân tích 50 công ty lớn thuộc 5 ngành khác nhau (mỗi ngành 10 công ty) trong giai đoạn từ năm 2015 đến hết 2025.
Các chỉ số phân tích sẽ được tham khảo từ **Vietcombank Securities (VCBS)**.

## Công cụ (Tech Stack)
- **Data Source**: SEC.gov Financial Statement Data Sets
- **Database**: PostgreSQL (lưu trữ data model)
- **ETL**: duckle-ETL (trích xuất, transform và load dữ liệu)
- **Data Preparation**: dataprep (làm sạch và chuẩn bị dữ liệu)
- **BI / Visualization**: PowerBI (xây dựng dashboard báo cáo)

## Cấu trúc thư mục

```text
Project-2/
├── data/
│   ├── raw/             # Lưu trữ dữ liệu thô tải từ SEC.gov
│   └── processed/       # Dữ liệu sau khi qua dataprep, sẵn sàng cho DB
├── etl/
│   ├── duckle/          # Các pipeline script của duckle-ETL
│   └── sql/             # Script SQL (DDL, DML) tạo bảng và nạp dữ liệu cho Postgres
├── dataprep/
│   └── notebooks/       # Các script / Jupyter notebooks sử dụng dataprep để làm sạch dữ liệu
├── docs/
│   ├── companies/       # Chứa danh sách 50 công ty và phân loại ngành
│   └── metrics/         # Tài liệu tham khảo các chỉ số từ Vietcombank Securities
├── powerbi/             # File dashboard (.pbix) và các file config liên quan
└── README.md            # Tài liệu dự án
```
