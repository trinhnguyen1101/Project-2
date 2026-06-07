# Data Dictionary: SEC Financial Statement Data Sets (Cleaned)

Đây là lược đồ (schema) chi tiết của bộ dữ liệu tài chính lấy từ SEC sau khi đã trải qua bước làm sạch (cleaning). Dữ liệu bao gồm 3 file CSV chính: `sub_clean.csv`, `num_clean.csv`, và `pre_clean.csv`.

---

## 1. File `sub_clean.csv` (Bảng Thông tin Báo cáo & Công ty)
Chứa thông tin siêu dữ liệu (metadata) về các bản nộp báo cáo (submissions) của công ty. Mỗi dòng tương ứng với một báo cáo tài chính được nộp cho SEC.

| Tên trường | Kiểu dữ liệu | Ý nghĩa chi tiết |
| :--- | :--- | :--- |
| **`quarter`** | `String` | Quý mà báo cáo được tải về từ hệ thống SEC (vd: `2015q1`). |
| **`adsh`** | `String` | **Khóa chính (Primary Key)**. Accession Number - Số định danh duy nhất dài 20 ký tự do SEC cấp cho mỗi bản nộp báo cáo. Dùng để nối (join) với bảng `num` và `pre`. |
| **`cik`** | `Integer` | Central Index Key - Số định danh duy nhất (10 chữ số) của công ty. |
| **`name`** | `String` | Tên công ty (đã được viết hoa và cắt bỏ khoảng trắng thừa). |
| **`sic`** | `Integer` | Standard Industrial Classification (Mã ngành nghề 4 chữ số). Dùng để phân loại ngành. |
| **`countryba`** | `String` | Quốc gia đặt trụ sở kinh doanh (Business Address). |
| **`stprba`** | `String` | Bang/Tỉnh đặt trụ sở kinh doanh. |
| **`cityba`** | `String` | Thành phố đặt trụ sở kinh doanh. |
| **`zipba`** | `String` | Mã bưu điện trụ sở kinh doanh. |
| **`bas1`** | `String` | Địa chỉ cụ thể (số nhà, đường) của trụ sở kinh doanh. |
| **`countryma`** | `String` | Quốc gia của địa chỉ nhận thư (Mailing Address). |
| **`stprma`** | `String` | Bang/Tỉnh của địa chỉ nhận thư. |
| **`cityma`** | `String` | Thành phố của địa chỉ nhận thư. |
| **`zipma`** | `String` | Mã bưu điện của địa chỉ nhận thư. |
| **`mas1`** | `String` | Địa chỉ cụ thể để nhận thư. |
| **`countryinc`**| `String` | Quốc gia nơi công ty đăng ký thành lập pháp nhân (Incorporation). |
| **`stprinc`** | `String` | Bang nơi đăng ký pháp nhân (thường là Delaware - DE ở Mỹ). |
| **`ein`** | `String` | Employer Identification Number - Mã số thuế của công ty. |
| **`afs`** | `String` | Tình trạng nộp báo cáo (vd: `1-LAF` = Large Accelerated Filer - Công ty có vốn hóa siêu lớn). |
| **`wksi`** | `Integer` | Well-Known Seasoned Issuer (1 = Có, 0 = Không). Thể hiện công ty phát hành uy tín. |
| **`fye`** | `String` | Fiscal Year End - Ngày kết thúc năm tài chính định dạng MMDD (vd: `1231` là 31/12). |
| **`form`** | `String` | Loại form báo cáo (vd: `10-K` là báo cáo năm, `10-Q` là báo cáo quý). |
| **`period`** | `Date` | **Ngày chốt sổ** báo cáo (Report period end date). Vd báo cáo quý 1 kết thúc vào ngày `2015-03-31`. |
| **`fy`** | `Integer` | Fiscal Year - Năm tài chính mà báo cáo đang đề cập. |
| **`fp`** | `String` | Fiscal Period - Kỳ tài chính (`Q1`, `Q2`, `Q3`, `Q4` hoặc `FY` cho cả năm). |
| **`filed`** | `Date` | Ngày công ty chính thức nộp báo cáo này lên hệ thống SEC. |
| **`accepted`**| `Datetime`| Thời điểm chính xác hệ thống EDGAR của SEC chấp nhận file. |
| **`prevrpt`** | `Integer` | Cờ báo hiệu báo cáo sửa đổi. *(Đã filter: Chỉ giữ lại giá trị `0` - báo cáo gốc)*. |
| **`nciks`** | `Integer` | Số lượng mã CIK đồng nộp chung trong báo cáo này (thường là 1). |

---

## 2. File `num_clean.csv` (Bảng Dữ liệu Số - Facts)
Chứa các giá trị tài chính thực tế. Đây là bảng Fact hạt mịn nhất. Cứ mỗi con số trên báo cáo tài chính sẽ tạo thành 1 dòng.

| Tên trường | Kiểu dữ liệu | Ý nghĩa chi tiết |
| :--- | :--- | :--- |
| **`quarter`** | `String` | Quý báo cáo (dùng để truy xuất file nguồn). |
| **`adsh`** | `String` | **Khóa ngoại (Foreign Key)** trỏ tới `sub_clean`. Định danh báo cáo. |
| **`tag`** | `String` | Tên chỉ tiêu chuẩn hóa theo thư viện XBRL (vd: `Revenues`, `NetIncomeLoss`, `Assets`). |
| **`version`** | `String` | Phiên bản từ điển XBRL (vd: `us-gaap/2021` hoặc mã nội bộ của công ty). `adsh + tag + version` định danh 1 khái niệm duy nhất. |
| **`ddate`** | `Date` | **Data Date**. Ngày kết thúc của kỳ tính toán cho con số này. Phải trùng hoặc gần với `period` trong bảng `sub`. |
| **`qtrs`** | `Integer` | **Đặc tính thời gian quan trọng:**<br>- `0`: Point-in-time (Số chốt sổ tại 1 ngày, dùng cho Bảng cân đối kế toán - Tài sản, Nợ).<br>- `1`: Duration 1 Quý (Dùng cho KQKD quý, Dòng tiền quý).<br>- `4`: Duration 1 Năm (Dùng cho KQKD năm, Dòng tiền năm). |
| **`uom`** | `String` | Đơn vị tính (Unit of Measure). Thường là `USD` hoặc `shares` (số lượng cổ phiếu), `pure` (tỷ lệ %). |
| **`value`** | `Float` | **Con số thực tế**. (Đã xóa các dòng value rỗng). |

*(Ghi chú: Các cột `segments`, `coreg`, `footnote` đã bị loại bỏ ở khâu làm sạch để đảm bảo dữ liệu chỉ ở cấp độ tổng hợp toàn công ty).*

---

## 3. File `pre_clean.csv` (Bảng Trình bày - Presentation)
Chứa thông tin về việc một chỉ tiêu (Tag) được sắp xếp hiển thị như thế nào trong tờ báo cáo tài chính (nằm ở Bảng nào, Dòng thứ mấy, Tên hiển thị là gì).

| Tên trường | Kiểu dữ liệu | Ý nghĩa chi tiết |
| :--- | :--- | :--- |
| **`quarter`** | `String` | Quý báo cáo. |
| **`adsh`** | `String` | **Khóa ngoại** trỏ tới `sub_clean`. |
| **`report`**| `Integer` | Số thứ tự của bảng báo cáo trong toàn bộ hồ sơ (ví dụ bảng KQKD có thể là report số 2, Bảng cân đối là report số 3). |
| **`line`** | `Integer` | Số thứ tự dòng của chỉ tiêu đó trong bảng báo cáo. |
| **`stmt`** | `String` | **Statement Type - Loại báo cáo tài chính:**<br>- `BS`: Balance Sheet (Cân đối kế toán)<br>- `IS`: Income Statement (Kết quả kinh doanh)<br>- `CF`: Cash Flow (Lưu chuyển tiền tệ)<br>- `EQ`: Equity (Vốn chủ sở hữu)<br>- `CI`: Comprehensive Income (Thu nhập toàn diện) |
| **`inpth`** | `Integer` | Độ lùi lề (Indentation depth). Dùng để vẽ cây phân cấp (Cấp cha = 0, Cấp con = 1, Cấp cháu = 2). |
| **`rfile`** | `String` | Định dạng file báo cáo gốc (Thường là `H` - HTML). |
| **`tag`** | `String` | Tên chỉ tiêu XBRL (Khóa ngoại trỏ đến `num_clean` để nối số liệu). |
| **`version`** | `String` | Phiên bản từ điển XBRL. |
| **`plabel`** | `String` | **Tên hiển thị thực tế** mà công ty dùng trên báo cáo PDF/HTML (vd: Tag là `Revenues` nhưng plabel công ty hiển thị là "Net Sales"). |
| **`negating`**| `Integer` | `1` nếu con số này khi hiển thị phải đổi dấu (từ âm sang dương hoặc ngược lại), `0` nếu giữ nguyên. Thường dùng khi hiển thị Chi phí. |

---

### Mối quan hệ giữa các bảng (Entity Relationship)
1. **Một Báo cáo (1 `adsh` trong `SUB`)** có chứa **Nhiều Con số (N dòng trong `NUM`)**. Nối nhau qua cột `adsh`.
2. **Một Con số (`adsh`, `tag`, `version` trong `NUM`)** được hiển thị lên BCTC theo định dạng quy định tại **1 Dòng (`adsh`, `tag`, `version` trong `PRE`)**.
   * *Nối NUM và PRE bằng cặp khóa: `adsh`, `tag`, `version`.*
