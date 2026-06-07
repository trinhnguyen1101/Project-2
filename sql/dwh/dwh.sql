-- ============================================================
-- DWH SNOWFLAKE SCHEMA - SEC FINANCIAL HEALTH AND RISK
-- Topic:
--   Analyze financial health and risk of US listed companies by SIC,
--   focusing on liquidity, profitability, and leverage trends from
--   2015 to 2025, and detect companies with financial distress signals.
--
-- Design rules for this project:
--   - Dimensions store descriptive attributes, SEC metadata, and raw inputs.
--   - Facts store calculated business metrics, scores, benchmarks, and signals.
--   - Validation results are stored in audit_* tables, not analytical facts.
--   - ML features and labels are stored in ml_* tables, not analytical facts.
-- DBMS: PostgreSQL
-- ============================================================

-- ============================================================
-- 0. DROP TABLES IF EXISTS
-- ============================================================
DROP TABLE IF EXISTS ml_risk_label CASCADE;
DROP TABLE IF EXISTS ml_risk_feature_snapshot CASCADE;
DROP TABLE IF EXISTS audit_data_quality_check CASCADE;
DROP TABLE IF EXISTS audit_etl_batch CASCADE;
DROP TABLE IF EXISTS fact_risk_signal CASCADE;
DROP TABLE IF EXISTS fact_industry_benchmark CASCADE;
DROP TABLE IF EXISTS fact_health_score CASCADE;
DROP TABLE IF EXISTS fact_financial_metrics CASCADE;
DROP TABLE IF EXISTS bridge_filing_presentation CASCADE;
DROP TABLE IF EXISTS dim_raw_financials CASCADE;
DROP TABLE IF EXISTS dim_concept CASCADE;
DROP TABLE IF EXISTS dim_filing CASCADE;
DROP TABLE IF EXISTS dim_fiscal_period CASCADE;
DROP TABLE IF EXISTS dim_company CASCADE;
DROP TABLE IF EXISTS dim_industry CASCADE;
DROP TABLE IF EXISTS dim_sic_major_group CASCADE;
DROP TABLE IF EXISTS dim_sic_division CASCADE;
DROP TABLE IF EXISTS dim_sector CASCADE;

-- ============================================================
-- 1. SNOWFLAKE DIMENSIONS
-- ============================================================

-- 1.1 Custom sector grouping used for dashboards and broad comparison.
CREATE TABLE dim_sector (
    sector_key      SERIAL PRIMARY KEY,
    sector_name     TEXT UNIQUE NOT NULL
);

-- 1.2 SIC division, e.g. Manufacturing, Retail Trade, Finance.
CREATE TABLE dim_sic_division (
    division_key    SERIAL PRIMARY KEY,
    division_code   VARCHAR(5) UNIQUE NOT NULL,
    division_name   TEXT NOT NULL
);

-- 1.3 SIC 2-digit major group.
CREATE TABLE dim_sic_major_group (
    major_group_key     SERIAL PRIMARY KEY,
    sic_2digit          INTEGER UNIQUE NOT NULL,
    major_group_name    TEXT,
    division_key        INTEGER REFERENCES dim_sic_division(division_key),

    CONSTRAINT ck_sic_2digit CHECK (sic_2digit BETWEEN 1 AND 99)
);

-- 1.4 SIC 4-digit industry.
CREATE TABLE dim_industry (
    industry_key        SERIAL PRIMARY KEY,
    sic_4digit          INTEGER UNIQUE NOT NULL,
    sic_3digit          INTEGER,
    industry_name       TEXT,
    major_group_key     INTEGER REFERENCES dim_sic_major_group(major_group_key),
    sector_key          INTEGER REFERENCES dim_sector(sector_key),

    CONSTRAINT ck_sic_4digit CHECK (sic_4digit BETWEEN 100 AND 9999),
    CONSTRAINT ck_sic_3digit CHECK (sic_3digit BETWEEN 10 AND 999 OR sic_3digit IS NULL)
);

-- 1.5 Company dimension with true SCD Type 2.
-- One CIK can have many versions over time when name, SIC, address, or flags change.
CREATE TABLE dim_company (
    company_key     BIGSERIAL PRIMARY KEY,
    cik             BIGINT NOT NULL,
    name            TEXT NOT NULL,
    ticker          TEXT,
    exchange_name   TEXT,
    industry_key    INTEGER REFERENCES dim_industry(industry_key),

    countryba       TEXT,
    stprba          TEXT,
    cityba          TEXT,
    countryinc      TEXT,
    stprinc         TEXT,
    ein             TEXT,
    wksi            BOOLEAN,

    valid_from      DATE NOT NULL,
    valid_to        DATE NOT NULL DEFAULT DATE '9999-12-31',
    is_current      BOOLEAN NOT NULL DEFAULT TRUE,
    scd_hash        TEXT,

    etl_batch_id    BIGINT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_dim_company_valid_date CHECK (valid_to >= valid_from),
    CONSTRAINT uq_dim_company_version UNIQUE (cik, valid_from)
);

CREATE UNIQUE INDEX uq_dim_company_current
    ON dim_company(cik)
    WHERE is_current;

-- 1.6 Fiscal period dimension.
-- period_end_date is SEC ddate / report period end date, not filing date.
CREATE TABLE dim_fiscal_period (
    period_key          BIGSERIAL PRIMARY KEY,
    period_end_date     DATE NOT NULL,
    fy                  INTEGER,
    fp                  VARCHAR(10),       -- Q1, Q2, Q3, Q4, FY
    fiscal_year         INTEGER,
    fiscal_quarter      SMALLINT,
    qtrs                SMALLINT,          -- 1 for quarter, 4 for annual
    period_type         VARCHAR(20),       -- quarterly, annual, ttm
    calendar_year       INTEGER,
    calendar_quarter    SMALLINT,

    CONSTRAINT ck_fiscal_quarter CHECK (
        fiscal_quarter BETWEEN 1 AND 4 OR fiscal_quarter IS NULL
    ),
    CONSTRAINT ck_calendar_quarter CHECK (
        calendar_quarter BETWEEN 1 AND 4 OR calendar_quarter IS NULL
    ),
    CONSTRAINT ck_period_type CHECK (
        period_type IN ('quarterly', 'annual', 'ttm') OR period_type IS NULL
    ),
    CONSTRAINT uq_dim_fiscal_period UNIQUE (period_end_date, fy, fp, qtrs)
);

-- 1.7 Filing dimension from SEC sub data.
CREATE TABLE dim_filing (
    filing_key          VARCHAR PRIMARY KEY,      -- adsh
    cik                 BIGINT NOT NULL,
    form                VARCHAR(20),              -- 10-K, 10-Q, 10-K/A, 10-Q/A
    filed_date          DATE,
    accepted_at         TIMESTAMP,
    report_period_end   DATE,
    fy                  INTEGER,
    fp                  VARCHAR(10),
    prevrpt             BOOLEAN,                  -- SEC previous report flag
    amendment_flag      BOOLEAN DEFAULT FALSE,
    nciks               SMALLINT,
    is_latest_filing    BOOLEAN DEFAULT TRUE,

    etl_batch_id        BIGINT,
    load_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 1.8 XBRL concept/tag metadata.
CREATE TABLE dim_concept (
    concept_key     BIGSERIAL PRIMARY KEY,
    tag             TEXT NOT NULL,
    version         TEXT NOT NULL,
    standard_tag    TEXT,
    preferred_label TEXT,
    statement_type  VARCHAR(10),          -- BS, IS, CF, EQ
    normal_balance  VARCHAR(10),          -- debit, credit
    data_type       TEXT,
    default_uom     TEXT,
    description     TEXT,

    CONSTRAINT uq_dim_concept_tag_version UNIQUE (tag, version),
    CONSTRAINT ck_concept_statement CHECK (
        statement_type IN ('BS', 'IS', 'CF', 'EQ') OR statement_type IS NULL
    ),
    CONSTRAINT ck_concept_normal_balance CHECK (
        normal_balance IN ('debit', 'credit') OR normal_balance IS NULL
    )
);

-- ============================================================
-- 2. RAW SEC INPUT TABLES
-- ============================================================
-- Kept under dim_* by project convention because raw SEC inputs are used as
-- dimensional input for calculated ratios. Grain follows SEC num:
-- one row per filing, concept, fiscal period, qtrs, uom, and coreg.

CREATE TABLE dim_raw_financials (
    raw_key         BIGSERIAL PRIMARY KEY,

    company_key     BIGINT NOT NULL REFERENCES dim_company(company_key),
    filing_key      VARCHAR NOT NULL REFERENCES dim_filing(filing_key),
    concept_key     BIGINT NOT NULL REFERENCES dim_concept(concept_key),
    period_key      BIGINT NOT NULL REFERENCES dim_fiscal_period(period_key),

    value           NUMERIC,
    qtrs            SMALLINT,
    uom             TEXT NOT NULL,
    coreg           TEXT NOT NULL DEFAULT '',
    decimals        INTEGER,

    is_adjusted     BOOLEAN NOT NULL DEFAULT FALSE,
    etl_batch_id    BIGINT,
    load_date       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_dim_raw_financials_num_grain UNIQUE (
        filing_key, concept_key, period_key, qtrs, uom, coreg
    )
);

-- Presentation metadata from SEC pre data. This is separated from raw values
-- to avoid duplicating numeric rows when a concept appears in multiple reports.
CREATE TABLE bridge_filing_presentation (
    presentation_key    BIGSERIAL PRIMARY KEY,
    filing_key          VARCHAR NOT NULL REFERENCES dim_filing(filing_key),
    concept_key         BIGINT NOT NULL REFERENCES dim_concept(concept_key),

    report              INTEGER,
    line                INTEGER,
    statement_type      VARCHAR(10),
    preferred_label     TEXT,
    negating            BOOLEAN,
    inpth               SMALLINT,

    CONSTRAINT uq_bridge_filing_presentation UNIQUE (
        filing_key, concept_key, report, line
    )
);

-- ============================================================
-- 3. ANALYTICAL FACT TABLES
-- ============================================================

-- 3.1 Company-period calculated financial metrics.
CREATE TABLE fact_financial_metrics (
    company_key                BIGINT NOT NULL REFERENCES dim_company(company_key),
    period_key                 BIGINT NOT NULL REFERENCES dim_fiscal_period(period_key),
    filing_key                 VARCHAR NOT NULL REFERENCES dim_filing(filing_key),

    currency_uom               TEXT DEFAULT 'USD',

    -- Liquidity
    current_ratio              NUMERIC,
    quick_ratio                NUMERIC,
    cash_ratio                 NUMERIC,
    working_capital            NUMERIC,

    -- Profitability
    gross_margin               NUMERIC,
    operating_margin           NUMERIC,
    net_margin                 NUMERIC,
    roa                        NUMERIC,
    roe                        NUMERIC,

    -- Leverage / solvency
    debt_to_equity             NUMERIC,
    debt_to_assets             NUMERIC,
    liabilities_to_assets      NUMERIC,
    interest_coverage          NUMERIC,

    -- Growth and efficiency
    revenue_growth_yoy         NUMERIC,
    revenue_growth_qoq         NUMERIC,
    net_income_growth_yoy      NUMERIC,
    asset_growth_yoy           NUMERIC,
    asset_turnover             NUMERIC,
    inventory_turnover         NUMERIC,

    -- Altman component inputs also useful for analysis.
    retained_earnings_to_assets NUMERIC,
    ebit_to_assets             NUMERIC,
    sales_to_assets            NUMERIC,

    is_annual                  BOOLEAN,
    calculation_batch_id       BIGINT,
    calculated_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (company_key, period_key, filing_key)
);

-- 3.2 Company-period health score.
CREATE TABLE fact_health_score (
    company_key                    BIGINT NOT NULL REFERENCES dim_company(company_key),
    period_key                     BIGINT NOT NULL REFERENCES dim_fiscal_period(period_key),
    filing_key                     VARCHAR NOT NULL REFERENCES dim_filing(filing_key),

    liquidity_score                NUMERIC,
    profitability_score            NUMERIC,
    leverage_score                 NUMERIC,
    efficiency_score               NUMERIC,

    altman_z_score                 NUMERIC,
    z_score_version                VARCHAR(30),       -- original, book_value, private
    financial_health_score         NUMERIC,
    health_level                   VARCHAR(20),       -- Safe, Grey, Distress

    x1_working_capital_ratio       NUMERIC,
    x2_retained_earnings_ratio     NUMERIC,
    x3_ebit_ratio                  NUMERIC,
    x4_equity_liabilities_ratio    NUMERIC,
    x5_sales_turnover              NUMERIC,

    market_value_equity            NUMERIC,
    book_value_equity              NUMERIC,
    calculation_batch_id           BIGINT,
    calculated_at                  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (company_key, period_key, filing_key),

    CONSTRAINT ck_fact_health_level CHECK (
        health_level IN ('Safe', 'Grey', 'Distress') OR health_level IS NULL
    ),
    CONSTRAINT ck_fact_zscore_version CHECK (
        z_score_version IN ('original', 'book_value', 'private') OR z_score_version IS NULL
    )
);

-- 3.3 Industry/peer benchmarking by sector, SIC 2-digit, or SIC 4-digit.
CREATE TABLE fact_industry_benchmark (
    benchmark_key              BIGSERIAL PRIMARY KEY,
    period_key                 BIGINT NOT NULL REFERENCES dim_fiscal_period(period_key),

    benchmark_level            VARCHAR(20) NOT NULL,  -- sector, sic_2digit, sic_4digit
    sector_key                 INTEGER REFERENCES dim_sector(sector_key),
    major_group_key            INTEGER REFERENCES dim_sic_major_group(major_group_key),
    industry_key               INTEGER REFERENCES dim_industry(industry_key),

    company_count              INTEGER,

    current_ratio_avg          NUMERIC,
    current_ratio_median       NUMERIC,
    current_ratio_p25          NUMERIC,
    current_ratio_p75          NUMERIC,

    roe_avg                    NUMERIC,
    roe_median                 NUMERIC,
    debt_to_assets_avg         NUMERIC,
    debt_to_assets_median      NUMERIC,
    altman_z_score_median      NUMERIC,
    distress_rate              NUMERIC,

    calculation_batch_id       BIGINT,
    calculated_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_benchmark_level CHECK (
        benchmark_level IN ('sector', 'sic_2digit', 'sic_4digit')
    )
);

-- 3.4 Business early-warning signals. ML-specific lag/label columns are not here.
CREATE TABLE fact_risk_signal (
    company_key                     BIGINT NOT NULL REFERENCES dim_company(company_key),
    period_key                      BIGINT NOT NULL REFERENCES dim_fiscal_period(period_key),
    filing_key                      VARCHAR NOT NULL REFERENCES dim_filing(filing_key),

    distress_flag                   BOOLEAN,
    risk_level                      VARCHAR(20),      -- Low, Medium, High, Critical

    negative_earnings_streak        SMALLINT,
    current_ratio_decline_streak    SMALLINT,
    debt_increase_streak            SMALLINT,

    liquidity_trend                 VARCHAR(20),
    leverage_trend                  VARCHAR(20),
    zscore_trend                    VARCHAR(20),

    restatement_flag                BOOLEAN,
    negative_equity_flag            BOOLEAN,
    zscore_drop_flag                BOOLEAN,

    calculation_batch_id            BIGINT,
    calculated_at                   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (company_key, period_key, filing_key),

    CONSTRAINT ck_fact_risk_level CHECK (
        risk_level IN ('Low', 'Medium', 'High', 'Critical') OR risk_level IS NULL
    ),
    CONSTRAINT ck_fact_risk_liquidity_trend CHECK (
        liquidity_trend IN ('Increasing', 'Decreasing', 'Stable') OR liquidity_trend IS NULL
    ),
    CONSTRAINT ck_fact_risk_leverage_trend CHECK (
        leverage_trend IN ('Increasing', 'Decreasing', 'Stable') OR leverage_trend IS NULL
    ),
    CONSTRAINT ck_fact_risk_zscore_trend CHECK (
        zscore_trend IN ('Increasing', 'Decreasing', 'Stable') OR zscore_trend IS NULL
    )
);

-- ============================================================
-- 4. AUDIT AND VALIDATION TABLES
-- ============================================================
-- Validation results are operational audit data, not analytical facts.

CREATE TABLE audit_etl_batch (
    etl_batch_id    BIGSERIAL PRIMARY KEY,
    batch_name      TEXT,
    source_name     TEXT,
    source_files    TEXT,
    started_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at        TIMESTAMP,
    status          VARCHAR(20) NOT NULL DEFAULT 'running',
    row_count       BIGINT,
    error_message   TEXT,

    CONSTRAINT ck_audit_batch_status CHECK (
        status IN ('running', 'success', 'failed', 'partial')
    )
);

CREATE TABLE audit_data_quality_check (
    check_key       BIGSERIAL PRIMARY KEY,
    etl_batch_id    BIGINT REFERENCES audit_etl_batch(etl_batch_id),
    company_key     BIGINT REFERENCES dim_company(company_key),
    filing_key      VARCHAR REFERENCES dim_filing(filing_key),
    period_key      BIGINT REFERENCES dim_fiscal_period(period_key),

    check_type      VARCHAR(60) NOT NULL,    -- balance, missing_rate, outlier, tag_mapping
    check_name      TEXT NOT NULL,
    check_status    VARCHAR(20) NOT NULL,    -- pass, warning, fail
    expected_value  NUMERIC,
    actual_value    NUMERIC,
    difference      NUMERIC,
    severity        VARCHAR(20),
    details         TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_quality_status CHECK (
        check_status IN ('pass', 'warning', 'fail')
    ),
    CONSTRAINT ck_quality_severity CHECK (
        severity IN ('low', 'medium', 'high', 'critical') OR severity IS NULL
    )
);

-- ============================================================
-- 5. ML FEATURE AND LABEL TABLES
-- ============================================================
-- These tables support XGBoost training and scoring. They are intentionally
-- outside analytical facts to keep the warehouse model explainable.

CREATE TABLE ml_risk_feature_snapshot (
    snapshot_key                    BIGSERIAL PRIMARY KEY,
    company_key                     BIGINT NOT NULL REFERENCES dim_company(company_key),
    period_key                      BIGINT NOT NULL REFERENCES dim_fiscal_period(period_key),
    filing_key                      VARCHAR NOT NULL REFERENCES dim_filing(filing_key),

    prediction_horizon_quarters     SMALLINT NOT NULL DEFAULT 4,
    feature_window_quarters         SMALLINT NOT NULL DEFAULT 8,

    roa_volatility_8q               NUMERIC,
    roe_volatility_8q               NUMERIC,
    debt_volatility_8q              NUMERIC,

    current_ratio_ind_percentile    NUMERIC,
    roe_ind_percentile              NUMERIC,
    z_score_ind_percentile          NUMERIC,

    current_ratio_lag1              NUMERIC,
    current_ratio_lag4              NUMERIC,
    roe_lag1                        NUMERIC,
    roe_lag4                        NUMERIC,
    debt_to_equity_change_yoy       NUMERIC,
    z_score_change_yoy              NUMERIC,

    feature_batch_id                BIGINT,
    created_at                      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_ml_risk_feature_snapshot UNIQUE (
        company_key, period_key, filing_key, prediction_horizon_quarters
    )
);

CREATE TABLE ml_risk_label (
    label_key                   BIGSERIAL PRIMARY KEY,
    snapshot_key                BIGINT NOT NULL REFERENCES ml_risk_feature_snapshot(snapshot_key),
    label_window_start_period_key BIGINT REFERENCES dim_fiscal_period(period_key),
    label_window_end_period_key   BIGINT REFERENCES dim_fiscal_period(period_key),

    distress_label              BOOLEAN NOT NULL,
    z_score_next                NUMERIC,
    label_definition            TEXT NOT NULL,
    label_source                VARCHAR(50),       -- rule_based, bankruptcy, delisting, hybrid
    created_at                  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_ml_label_source CHECK (
        label_source IN ('rule_based', 'bankruptcy', 'delisting', 'hybrid') OR label_source IS NULL
    )
);

-- ============================================================
-- 6. INDEXES
-- ============================================================

-- Snowflake dimensions
CREATE INDEX idx_dim_sic_major_division ON dim_sic_major_group(division_key);
CREATE INDEX idx_dim_industry_major ON dim_industry(major_group_key);
CREATE INDEX idx_dim_industry_sector ON dim_industry(sector_key);
CREATE INDEX idx_dim_company_cik ON dim_company(cik);
CREATE INDEX idx_dim_company_industry ON dim_company(industry_key);
CREATE INDEX idx_dim_company_scd_dates ON dim_company(cik, valid_from, valid_to);
CREATE INDEX idx_dim_period_year_quarter ON dim_fiscal_period(fiscal_year, fiscal_quarter);
CREATE INDEX idx_dim_period_end_date ON dim_fiscal_period(period_end_date);
CREATE INDEX idx_dim_filing_cik_period ON dim_filing(cik, report_period_end);
CREATE INDEX idx_dim_filing_form ON dim_filing(form);
CREATE INDEX idx_dim_concept_tag ON dim_concept(tag);
CREATE INDEX idx_dim_concept_standard_tag ON dim_concept(standard_tag);

-- Raw inputs
CREATE INDEX idx_dim_raw_company_period ON dim_raw_financials(company_key, period_key);
CREATE INDEX idx_dim_raw_filing ON dim_raw_financials(filing_key);
CREATE INDEX idx_dim_raw_concept ON dim_raw_financials(concept_key);
CREATE INDEX idx_dim_raw_period_concept ON dim_raw_financials(period_key, concept_key);
CREATE INDEX idx_bridge_presentation_filing ON bridge_filing_presentation(filing_key);
CREATE INDEX idx_bridge_presentation_concept ON bridge_filing_presentation(concept_key);

-- Analytical facts
CREATE INDEX idx_fact_metrics_company_period ON fact_financial_metrics(company_key, period_key);
CREATE INDEX idx_fact_metrics_period ON fact_financial_metrics(period_key);
CREATE INDEX idx_fact_health_company_period ON fact_health_score(company_key, period_key);
CREATE INDEX idx_fact_health_level ON fact_health_score(health_level);
CREATE INDEX idx_fact_health_zscore ON fact_health_score(altman_z_score);
CREATE INDEX idx_fact_benchmark_period_level ON fact_industry_benchmark(period_key, benchmark_level);
CREATE INDEX idx_fact_risk_company_period ON fact_risk_signal(company_key, period_key);
CREATE INDEX idx_fact_risk_distress ON fact_risk_signal(distress_flag);
CREATE INDEX idx_fact_risk_level ON fact_risk_signal(risk_level);

-- Audit and ML
CREATE INDEX idx_audit_quality_batch ON audit_data_quality_check(etl_batch_id);
CREATE INDEX idx_audit_quality_company_period ON audit_data_quality_check(company_key, period_key);
CREATE INDEX idx_ml_snapshot_company_period ON ml_risk_feature_snapshot(company_key, period_key);
CREATE INDEX idx_ml_label_snapshot ON ml_risk_label(snapshot_key);

-- ============================================================
-- 7. TABLE COMMENTS
-- ============================================================

COMMENT ON TABLE dim_company IS 'SCD Type 2 company dimension. CIK is the business key; company_key is the surrogate version key.';
COMMENT ON TABLE dim_fiscal_period IS 'Fiscal reporting period dimension based on SEC ddate/report period end, fy, fp, and qtrs.';
COMMENT ON TABLE dim_filing IS 'SEC filing dimension from sub data. Filing key is adsh.';
COMMENT ON TABLE dim_concept IS 'XBRL concept metadata and standard tag mapping.';
COMMENT ON TABLE dim_raw_financials IS 'Raw SEC numeric values from num data at filing-concept-period-qtrs-uom-coreg grain.';
COMMENT ON TABLE bridge_filing_presentation IS 'SEC pre presentation metadata separated from raw numeric values.';
COMMENT ON TABLE fact_financial_metrics IS 'Calculated company-period financial ratios for trend analysis.';
COMMENT ON TABLE fact_health_score IS 'Calculated health score and Altman Z-Score components.';
COMMENT ON TABLE fact_industry_benchmark IS 'Calculated sector/SIC peer benchmarks by period.';
COMMENT ON TABLE fact_risk_signal IS 'Business early-warning risk signals, excluding ML labels.';
COMMENT ON TABLE audit_data_quality_check IS 'ETL and calculation validation results, separate from analytical facts.';
COMMENT ON TABLE ml_risk_feature_snapshot IS 'Feature snapshots for 4-quarter distress prediction models such as XGBoost.';
COMMENT ON TABLE ml_risk_label IS 'Training labels linked to ML feature snapshots.';

-- ============================================================
-- END OF FILE
-- ============================================================
