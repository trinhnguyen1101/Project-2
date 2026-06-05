File: num_clean.csv

quarter: Mã quý báo cáo (ví dụ 2015q1).
adsh: Accession number — mã duy nhất của submission/filing (xác định 1 báo cáo).
tag: Tên thẻ XBRL (khóa định danh thực thể số, ví dụ SalesRevenueNet).
version: Taxonomy / phiên bản tag (ví dụ us-gaap/2014).
ddate: Ngày liên quan tới giá trị (format YYYYMMDD) — ngày kỳ/vụ mà giá trị áp dụng.
qtrs: Số quý trong kỳ báo cáo (ví dụ 1, 3, 4 — số quý phủ bởi giá trị).
uom: Unit Of Measure — đơn vị đo (ví dụ USD).
value: Giá trị số (số thực).
File: pre_clean.csv

quarter: Mã quý báo cáo.
adsh: Accession number (như trên).
report: Mã/ID báo cáo trong filing (dùng để nhóm các dòng presentation).
line: Số dòng/sequence trong phần presentation (dùng để giữ thứ tự).
stmt: Statement type — loại báo cáo (ví dụ IS = Income Statement, BS = Balance Sheet, CF = Cash Flow, EQ, CI).
inpth: Indentation depth — mức thụt lề/hierarchy level trong cây presentation (số nguyên, 0 là top-level).
rfile: Mã file/role của presentation (mã phân loại phần/bản trình bày; giá trị ví dụ H xuất hiện trong dữ liệu).
tag: Thẻ XBRL liên quan nếu có (tên fact).
version: Taxonomy / phiên bản (như trên).
plabel: Presentation label — nhãn đọc được của dòng (chuỗi mô tả, ví dụ “Total Revenues”).
negating: Cờ/flag chỉ việc có cần đảo dấu/negate hay không (0/1; dùng để xử lý logic trình bày).
File: sub_clean.csv

quarter: Mã quý báo cáo.
adsh: Accession number (như trên).
cik: Company CIK — mã định danh công ty trên SEC.
name: Tên công ty (chuỗi).
sic: SIC code — mã ngành theo chuẩn SIC.
countryba: Country (business address) — quốc gia địa chỉ kinh doanh.
stprba: State/province (business address).
cityba: City (business address).
zipba: ZIP/postal (business address).
bas1: Business address line 1 (địa chỉ dòng 1).
countryma: Country (mailing address).
stprma: State/province (mailing).
cityma: City (mailing).
zipma: ZIP (mailing).
mas1: Mailing address line 1.
countryinc: Country of incorporation (nơi đăng ký thành lập).
stprinc: State/province of incorporation.
ein: Employer Identification Number (EIN / tax id).
afs: Mã/metadata từ submission (giá trị dạng chuỗi trong dữ liệu — giữ nguyên); (không có chú giải rõ ràng trong repo, là metadata liên quan tới filing).
wksi: WKSI flag — chỉ báo công ty là Well-Known Seasoned Issuer (0/1).
fye: Fiscal year end (thông tin FYE, có thể là tháng/ngày).
form: Form type (ví dụ 10-K, 10-Q).
period: Period end (thời điểm kết thúc kỳ, thường YYYYMMDD).
fy: Fiscal year (năm tài chính).
fp: Fiscal period code (ví dụ FY, Q1, Q2).
filed: Ngày filed (ngày nộp, đã chuẩn hoá).
accepted: Thời điểm accepted (datetime chuỗi).
prevrpt: Cờ báo cáo sửa đổi (1 = báo cáo sửa đổi, 0 = gốc).
nciks: Số CIKs liên quan trong submission (thường 1).