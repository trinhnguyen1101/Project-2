# Cong thuc tinh cac measure trong fact

File nay tong hop cac cong thuc tinh measure cho thiet ke DWH trong `sql/dwh/dwh_dim_fact_only.sql`.

## 1. `fact_financial_metrics`

| Measure | Cong thuc | Raw input chinh |
|---|---|---|
| `current_ratio` | `AssetsCurrent / LiabilitiesCurrent` | `AssetsCurrent`, `LiabilitiesCurrent` |
| `quick_ratio` | `(CashAndCashEquivalents + ReceivablesNetCurrent) / LiabilitiesCurrent` | `CashAndCashEquivalentsAtCarryingValue`, `AccountsReceivableNetCurrent`, `LiabilitiesCurrent` |
| `working_capital` | `AssetsCurrent - LiabilitiesCurrent` | `AssetsCurrent`, `LiabilitiesCurrent` |
| `gross_margin` | `(Revenues - CostOfRevenue) / Revenues` hoac `GrossProfit / Revenues` | `Revenues`, `CostOfRevenue`, `CostOfGoodsAndServicesSold`, `GrossProfit` |
| `operating_margin` | `OperatingIncomeLoss / Revenues` | `OperatingIncomeLoss`, `Revenues` |
| `net_margin` | `NetIncomeLoss / Revenues` | `NetIncomeLoss`, `Revenues` |
| `roa` | `NetIncomeLoss / AverageAssets` | `NetIncomeLoss`, `Assets` |
| `roe` | `NetIncomeLoss / AverageStockholdersEquity` | `NetIncomeLoss`, `StockholdersEquity` |
| `debt_to_equity` | `Liabilities / StockholdersEquity` | `Liabilities`, `StockholdersEquity` |
| `debt_to_assets` | `Liabilities / Assets` | `Liabilities`, `Assets` |
| `interest_coverage` | `EBIT / InterestExpense` | `OperatingIncomeLoss`, `IncomeBeforeTax`, `InterestExpense` |
| `revenue_growth_yoy` | `(Revenues_current - Revenues_same_period_last_year) / Revenues_same_period_last_year` | `Revenues` |
| `net_income_growth_yoy` | `(NetIncome_current - NetIncome_same_period_last_year) / NetIncome_same_period_last_year` | `NetIncomeLoss` |
| `asset_growth_yoy` | `(Assets_current - Assets_same_period_last_year) / Assets_same_period_last_year` | `Assets` |
| `retained_earnings_to_assets` | `RetainedEarningsAccumulatedDeficit / Assets` | `RetainedEarningsAccumulatedDeficit`, `Assets` |
| `ebit_to_assets` | `EBIT / Assets` | `OperatingIncomeLoss`, `IncomeBeforeTax`, `InterestExpense`, `Assets` |
| `sales_to_assets` | `Revenues / Assets` | `Revenues`, `Assets` |

Goi y tinh EBIT:

```text
EBIT = OperatingIncomeLoss
```

Hoac:

```text
EBIT = IncomeBeforeTax + InterestExpense
```

Voi `roa`, `roe`, neu can don gian hoa trong do an co the dung:

```text
ROA = NetIncomeLoss / Assets
ROE = NetIncomeLoss / StockholdersEquity
```

Neu can chuan hon, dung gia tri binh quan:

```text
AverageAssets = (Assets_current + Assets_previous_period) / 2
AverageStockholdersEquity = (Equity_current + Equity_previous_period) / 2
```

## 2. `fact_health_score`

| Measure | Cong thuc / cach tinh |
|---|---|
| `liquidity_score` | Diem chuan hoa tu `current_ratio`, `quick_ratio`, `working_capital` |
| `profitability_score` | Diem chuan hoa tu `gross_margin`, `operating_margin`, `net_margin`, `roa`, `roe` |
| `leverage_score` | Diem chuan hoa tu `debt_to_equity`, `debt_to_assets`, `interest_coverage` |
| `efficiency_score` | Diem chuan hoa tu `sales_to_assets` hoac nhom chi so hieu qua lien quan |
| `x1_working_capital_ratio` | `(AssetsCurrent - LiabilitiesCurrent) / Assets` |
| `x2_retained_earnings_ratio` | `RetainedEarningsAccumulatedDeficit / Assets` |
| `x3_ebit_ratio` | `EBIT / Assets` |
| `x4_equity_liabilities_ratio` | `BookValueEquity / Liabilities` |
| `x5_sales_turnover` | `Revenues / Assets` |
| `altman_z_score` | `1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5` |
| `financial_health_score` | Diem tong hop tu cac component score va `altman_z_score` |
| `health_level` | Phan loai tu `altman_z_score` hoac `financial_health_score` |
| `book_value_equity` | `StockholdersEquity` |

Do DWH hien tai khong dung du lieu gia thi truong, Altman Z-Score nen dung bien the book-value:

```text
z_score_version = 'book_value'
```

Nguong Altman tham khao:

```text
Safe:      Z > 2.99
Grey:      1.81 <= Z <= 2.99
Distress:  Z < 1.81
```

## 3. `fact_industry_benchmark`

Bang nay tong hop benchmark theo nganh trong cung ky bao cao.

Group theo:

```text
quarter_key + benchmark_level
```

Trong do `benchmark_level` co the la:

```text
sector
sic_2digit
sic_4digit
```

| Measure | Cong thuc |
|---|---|
| `company_count` | `COUNT(DISTINCT company_key)` |
| `current_ratio_median` | `MEDIAN(current_ratio)` trong nganh/ky |
| `roe_median` | `MEDIAN(roe)` trong nganh/ky |
| `debt_to_assets_median` | `MEDIAN(debt_to_assets)` trong nganh/ky |
| `altman_z_score_median` | `MEDIAN(altman_z_score)` trong nganh/ky |
| `distress_rate` | `COUNT(company co distress_flag = true) / COUNT(company)` |

Nguon tinh chinh:

```text
fact_financial_metrics
fact_health_score
fact_risk_signal
dim_company
dim_industry
dim_sic_major_group
dim_sector
```

## 4. `fact_risk_signal`

| Measure / signal | Cong thuc / rule |
|---|---|
| `distress_flag` | `true` neu cong ty thoa mot hoac nhieu rule rui ro |
| `risk_level` | `Low`, `Medium`, `High`, `Critical` dua tren so luong va muc do rule bi vi pham |
| `negative_earnings_streak` | So ky lien tiep `NetIncomeLoss < 0` |
| `current_ratio_decline_streak` | So ky lien tiep `current_ratio` giam |
| `debt_increase_streak` | So ky lien tiep `debt_to_assets` hoac `debt_to_equity` tang |
| `liquidity_trend` | `Increasing`, `Decreasing`, `Stable` dua tren xu huong `current_ratio`/`quick_ratio` |
| `leverage_trend` | `Increasing`, `Decreasing`, `Stable` dua tren xu huong `debt_to_assets`/`debt_to_equity` |
| `zscore_trend` | `Increasing`, `Decreasing`, `Stable` dua tren xu huong `altman_z_score` |
| `restatement_flag` | `dim_filing.prevrpt = true OR dim_filing.amendment_flag = true` |
| `negative_equity_flag` | `StockholdersEquity < 0` |
| `zscore_drop_flag` | `altman_z_score_current < altman_z_score_same_period_last_year` hoac giam vuot nguong dinh truoc |

Rule goi y cho `distress_flag`:

```text
distress_flag = true neu:
- altman_z_score < 1.81
OR current_ratio < 1.0
OR negative_earnings_streak >= 4
OR negative_equity_flag = true
OR interest_coverage < 1.5
```

Rule goi y cho `risk_level`:

```text
Low:      khong co hoac chi co tin hieu nhe
Medium:   co 1-2 tin hieu canh bao
High:     co >= 3 tin hieu canh bao hoac Z-Score < 1.81
Critical: Z-Score < 1.81 va loi nhuan am lien tuc hoac von chu am
```
