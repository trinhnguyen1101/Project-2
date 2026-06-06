Chủ đề: Phân tích sức khỏe tài chính và rủi ro của các công ty niêm yết Mỹ theo ngành (theo SIC), tập trung vào xu hướng thanh khoản, lợi nhuận và đòn bẩy nợ trong giai đoạn 2015–2025, đồng thời phát hiện các công ty có dấu hiệu khó khăn tài chính

A. Phân tích xu hướng theo thời gian (Trend Analysis) 2015–2025
Theo từng công ty lớn + theo ngành (SIC).
Tập trung: Thanh khoản, Lợi nhuận, Đòn bẩy nợ.
B. So sánh ngang ngành (Peer & Industry Benchmarking)
Nhóm công ty theo SIC (ví dụ: Manufacturing, Technology, Retail, Finance...).
Xem ngành nào đang khỏe mạnh / gặp khó khăn.
C. Đánh giá sức khỏe tài chính tổng hợp
Sử dụng bộ chỉ số + Altman Z-Score (hoặc biến thể) để chấm điểm sức khỏe.
D. Phát hiện công ty có dấu hiệu khó khăn tài chính (Early Warning)
Dựa trên ngưỡng chỉ số + Z-Score + các dấu hiệu khác.


2. Các chỉ số cụ thể & Công thức tính (từ dữ liệu num + pre + sub)
Nhóm Thanh khoản (Liquidity)
Chỉ số
Công thức (Tags XBRL phổ biến)
Ý nghĩa & Ngưỡng cảnh báo
Current Ratio
AssetsCurrent / LiabilitiesCurrent
> 1.5 tốt, < 1.0 nguy hiểm
Quick Ratio
(CashAndCashEquivalents + ReceivablesNetCurrent) / LiabilitiesCurrent
> 1.0 tốt

Nhóm Lợi nhuận (Profitability)
Chỉ số
Công thức
Ý nghĩa & Ngưỡng cảnh báo
Gross Margin
(Revenues - CostOfRevenue/CostOfGoodsSold) / Revenues
Ngành-dependent, giảm mạnh = rủi ro
Operating Margin
OperatingIncomeLoss / Revenues
> 10% tốt (tùy ngành)
Net Profit Margin
NetIncomeLoss / Revenues
Âm liên tục = nguy hiểm
ROA
NetIncomeLoss / Assets
> 5-10% tùy ngành
ROE
NetIncomeLoss / StockholdersEquity
> 15% tốt

Nhóm Đòn bẩy nợ (Leverage / Solvency)
Chỉ số
Công thức
Ý nghĩa & Ngưỡng cảnh báo
Debt-to-Equity
Liabilities / StockholdersEquity
< 1.0–2.0 tùy ngành
Debt-to-Assets
Liabilities / Assets
< 0.5 tốt
Interest Coverage
EBIT / InterestExpense
< 1.5 = rủi ro cao

Chỉ số tổng hợp - Altman Z-Score (rất phù hợp cho Early Warning)
Z-Score = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5
X1: Working Capital / Total Assets = (AssetsCurrent - LiabilitiesCurrent) / Assets
X2: Retained Earnings / Total Assets (tag: RetainedEarningsAccumulatedDeficit)
X3: EBIT / Total Assets (EBIT ≈ OperatingIncomeLoss + Interest + Taxes)
X4: Market Value of Equity / Total Liabilities (cần thêm dữ liệu giá thị trường)
X5: Sales / Total Assets (Revenues / Assets)
3. Những vấn đề con cần phân tích chi tiết
Xu hướng theo quý/năm: Tính growth rate (YoY, QoQ) của các chỉ số trên.
Phân bố theo ngành (SIC): Trung bình, median, percentile của từng chỉ số theo SIC 2-digit hoặc 4-digit.
Tương quan giữa các nhóm chỉ số: Ví dụ, nợ cao có làm giảm ROE không?
Công ty outlier: Top/Bottom 10 theo ROE, Current Ratio, Z-Score.
Dấu hiệu khó khăn:
Thanh khoản giảm liên tục + nợ tăng.
Lợi nhuận âm nhiều quý.
Restatement (prevrpt=1).
Z-Score giảm mạnh.
4. Những gì cần KIỂM ĐỊNH (Validation) – Rất quan trọng
Để đảm bảo kết quả đáng tin cậy:
Kiểm định dữ liệu & Tính toán:
Balance check: Total Assets ≈ Total Liabilities + StockholdersEquity (kiểm tra accuracy của XBRL).
Consistency: So sánh giá trị cùng tag giữa quarterly (qtrs=1) và annual (qtrs=4).
Tag mapping: Kiểm tra xem tag có sẵn trong num_clean.csv (ví dụ: AssetsCurrent, NetIncomeLoss, Revenues...). Dùng plabel từ pre_clean.csv để tìm tag tương đương nếu tag chuẩn thiếu.
Handling negating: Dùng cột negating từ pre để đảo dấu khi cần.
Fiscal alignment: Dùng period, fy, fp, ddate để align đúng kỳ.
Kiểm định bên ngoài:
Chọn 5–10 công ty lớn (ví dụ: Apple, Amazon, Tesla – tìm CIK qua sub) → so sánh ratios tính được với Yahoo Finance, Macrotrends, hoặc báo cáo 10-K gốc trên EDGAR.
So sánh benchmark ngành với dữ liệu công khai (RMA, S&P, VCBS tương đương cho US).
Kiểm định thống kê:
Missing values rate cho từng tag quan trọng.
Outlier detection (ví dụ: value cực lớn do unit sai).
Phân tích robustness (thử tính với/without restatements).
1. Mục tiêu tổng quát của phần ML
Phát hiện sớm (Early Warning System) các công ty có nguy cơ khó khăn tài chính (distress, default, phá sản).
Dự báo xu hướng sức khỏe tài chính.
Hỗ trợ quyết định cho nhà đầu tư, ngân hàng, quỹ đầu tư (screening, risk monitoring).
Phân khúc rủi ro theo ngành (SIC).
2.Mô hình ML 
Dự đoán công ty có nguy cơ khó khăn tài chính trong 4 quý tiếp theo. 
Dùng XGBoost Classifier 
