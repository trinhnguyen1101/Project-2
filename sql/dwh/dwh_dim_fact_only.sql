-- ============================================================
-- DWH SNOWFLAKE SCHEMA - DIMENSIONS AND FACTS ONLY
-- Topic:
--   Analyze financial health and risk of US listed companies by SIC,
--   focusing on liquidity, profitability, and leverage trends from
--   2015 to 2025, and detect companies with financial distress signals.
--
-- Scope:
--   - This file contains only dim_* and fact_* tables.
--   - audit_*, ml_*, bridge_*, and other supporting tables are intentionally excluded.
-- DBMS: PostgreSQL
-- ============================================================

-- ============================================================
-- 0. DROP TABLES IF EXISTS
-- ============================================================
DROP TABLE IF EXISTS fact_risk_signal CASCADE;
DROP TABLE IF EXISTS fact_industry_benchmark CASCADE;
DROP TABLE IF EXISTS fact_health_score CASCADE;
DROP TABLE IF EXISTS fact_financial_metrics CASCADE;
DROP TABLE IF EXISTS dim_raw_financials CASCADE;
DROP TABLE IF EXISTS dim_concept CASCADE;
DROP TABLE IF EXISTS dim_filing CASCADE;
DROP TABLE IF EXISTS dim_quarter CASCADE;
DROP TABLE IF EXISTS dim_year CASCADE;
DROP TABLE IF EXISTS dim_company CASCADE;
DROP TABLE IF EXISTS dim_industry CASCADE;
DROP TABLE IF EXISTS dim_sic_major_group CASCADE;
DROP TABLE IF EXISTS dim_sic_division CASCADE;
DROP TABLE IF EXISTS dim_sector CASCADE;

-- ============================================================
-- 1. DIMENSION TABLES
-- ============================================================

CREATE TABLE dim_sector (
    sector_key      SERIAL PRIMARY KEY,
    sector_name     TEXT UNIQUE NOT NULL
);

CREATE TABLE dim_sic_division (
    division_key    SERIAL PRIMARY KEY,
    division_code   VARCHAR(5) UNIQUE NOT NULL,
    division_name   TEXT NOT NULL
);

CREATE TABLE dim_sic_major_group (
    major_group_key     SERIAL PRIMARY KEY,
    sic_2digit          INTEGER UNIQUE NOT NULL,
    major_group_name    TEXT,
    division_key        INTEGER REFERENCES dim_sic_division(division_key),

    CONSTRAINT ck_sic_2digit CHECK (sic_2digit BETWEEN 1 AND 99)
);

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

-- SCD Type 2 company dimension.
CREATE TABLE dim_company (
    company_key     BIGSERIAL PRIMARY KEY,
    cik             BIGINT NOT NULL,
    name            TEXT NOT NULL,
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

    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_dim_company_valid_date CHECK (valid_to >= valid_from),
    CONSTRAINT uq_dim_company_version UNIQUE (cik, valid_from)
);

CREATE UNIQUE INDEX uq_dim_company_current
    ON dim_company(cik)
    WHERE is_current;

-- Year dimension for fiscal/calendar year analysis.
CREATE TABLE dim_year (
    year_key        SERIAL PRIMARY KEY,
    fiscal_year     INTEGER NOT NULL UNIQUE,
    calendar_year   INTEGER,
    year_label      VARCHAR(20)
);

-- Quarter/reporting-period dimension based on SEC ddate/report period end.
-- Annual reports are stored as period_type = 'annual' and fiscal_quarter may be null.
CREATE TABLE dim_quarter (
    quarter_key         BIGSERIAL PRIMARY KEY,
    year_key            INTEGER NOT NULL REFERENCES dim_year(year_key),
    period_end_date     DATE NOT NULL,
    fp                  VARCHAR(10),
    fiscal_quarter      SMALLINT,
    qtrs                SMALLINT,
    period_type         VARCHAR(20),
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
    CONSTRAINT uq_dim_quarter UNIQUE (period_end_date, year_key, fp, qtrs)
);

CREATE TABLE dim_filing (
    filing_key          VARCHAR PRIMARY KEY,
    cik                 BIGINT NOT NULL,
    form                VARCHAR(20),
    filed_date          DATE,
    accepted_at         TIMESTAMP,
    report_period_end   DATE,
    fy                  INTEGER,
    fp                  VARCHAR(10),
    nciks               SMALLINT,
    is_latest_filing    BOOLEAN DEFAULT TRUE,
    load_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dim_concept (
    concept_key     BIGSERIAL PRIMARY KEY,
    tag             TEXT NOT NULL,
    version         TEXT NOT NULL,
    standard_tag    TEXT,
    preferred_label TEXT,
    statement_type  VARCHAR(10),
    normal_balance  VARCHAR(10),
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

-- Raw SEC numeric values kept as dim by project convention.
CREATE TABLE dim_raw_financials (
    raw_key         BIGSERIAL PRIMARY KEY,

    company_key     BIGINT NOT NULL REFERENCES dim_company(company_key),
    filing_key      VARCHAR NOT NULL REFERENCES dim_filing(filing_key),
    concept_key     BIGINT NOT NULL REFERENCES dim_concept(concept_key),
    quarter_key     BIGINT NOT NULL REFERENCES dim_quarter(quarter_key),

    value           NUMERIC,
    qtrs            SMALLINT,
    uom             TEXT NOT NULL,

    is_adjusted     BOOLEAN NOT NULL DEFAULT FALSE,
    load_date       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_dim_raw_financials_num_grain UNIQUE (
        filing_key, concept_key, quarter_key, qtrs, uom
    )
);

-- ============================================================
-- 2. FACT TABLES
-- ============================================================

CREATE TABLE fact_financial_metrics (
    company_key                 BIGINT NOT NULL REFERENCES dim_company(company_key),
    quarter_key                 BIGINT NOT NULL REFERENCES dim_quarter(quarter_key),
    filing_key                  VARCHAR NOT NULL REFERENCES dim_filing(filing_key),

    currency_uom                TEXT,

    current_ratio               NUMERIC,
    quick_ratio                 NUMERIC,
    working_capital             NUMERIC,

    gross_margin                NUMERIC,
    operating_margin            NUMERIC,
    net_margin                  NUMERIC,
    roa                         NUMERIC,
    roe                         NUMERIC,

    debt_to_equity              NUMERIC,
    debt_to_assets              NUMERIC,
    interest_coverage           NUMERIC,

    revenue_growth_yoy          NUMERIC,
    net_income_growth_yoy       NUMERIC,
    asset_growth_yoy            NUMERIC,

    retained_earnings_to_assets NUMERIC,
    ebit_to_assets              NUMERIC,
    sales_to_assets             NUMERIC,

    is_annual                   BOOLEAN,
    calculated_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (company_key, quarter_key, filing_key)
);

CREATE TABLE fact_health_score (
    company_key                    BIGINT NOT NULL REFERENCES dim_company(company_key),
    quarter_key                    BIGINT NOT NULL REFERENCES dim_quarter(quarter_key),
    filing_key                     VARCHAR NOT NULL REFERENCES dim_filing(filing_key),

    liquidity_score                NUMERIC,
    profitability_score            NUMERIC,
    leverage_score                 NUMERIC,
    efficiency_score               NUMERIC,

    altman_z_score                 NUMERIC,
    z_score_version                VARCHAR(30),
    financial_health_score         NUMERIC,
    health_level                   VARCHAR(20),

    x1_working_capital_ratio       NUMERIC,
    x2_retained_earnings_ratio     NUMERIC,
    x3_ebit_ratio                  NUMERIC,
    x4_equity_liabilities_ratio    NUMERIC,
    x5_sales_turnover              NUMERIC,

    book_value_equity              NUMERIC,
    calculated_at                  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (company_key, quarter_key, filing_key),

    CONSTRAINT ck_fact_health_level CHECK (
        health_level IN ('Safe', 'Grey', 'Distress') OR health_level IS NULL
    ),
    CONSTRAINT ck_fact_zscore_version CHECK (
        z_score_version IN ('book_value', 'private') OR z_score_version IS NULL
    )
);

CREATE TABLE fact_industry_benchmark (
    benchmark_key              BIGSERIAL PRIMARY KEY,
    quarter_key                BIGINT NOT NULL REFERENCES dim_quarter(quarter_key),

    benchmark_level            VARCHAR(20) NOT NULL,
    sector_key                 INTEGER REFERENCES dim_sector(sector_key),
    major_group_key            INTEGER REFERENCES dim_sic_major_group(major_group_key),
    industry_key               INTEGER REFERENCES dim_industry(industry_key),

    company_count              INTEGER,

    current_ratio_median       NUMERIC,

    roe_median                 NUMERIC,
    debt_to_assets_median      NUMERIC,
    altman_z_score_median      NUMERIC,
    distress_rate              NUMERIC,

    calculated_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_benchmark_level CHECK (
        benchmark_level IN ('sector', 'sic_2digit', 'sic_4digit')
    )
);

CREATE TABLE fact_risk_signal (
    company_key                     BIGINT NOT NULL REFERENCES dim_company(company_key),
    quarter_key                     BIGINT NOT NULL REFERENCES dim_quarter(quarter_key),
    filing_key                      VARCHAR NOT NULL REFERENCES dim_filing(filing_key),

    distress_flag                   BOOLEAN,
    risk_level                      VARCHAR(20),

    negative_earnings_streak        SMALLINT,
    current_ratio_decline_streak    SMALLINT,
    debt_increase_streak            SMALLINT,

    liquidity_trend                 VARCHAR(20),
    leverage_trend                  VARCHAR(20),
    zscore_trend                    VARCHAR(20),

    negative_equity_flag            BOOLEAN,
    zscore_drop_flag                BOOLEAN,

    calculated_at                   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (company_key, quarter_key, filing_key),

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
-- 3. INDEXES
-- ============================================================

CREATE INDEX idx_dim_sic_major_division ON dim_sic_major_group(division_key);
CREATE INDEX idx_dim_industry_major ON dim_industry(major_group_key);
CREATE INDEX idx_dim_industry_sector ON dim_industry(sector_key);
CREATE INDEX idx_dim_company_cik ON dim_company(cik);
CREATE INDEX idx_dim_company_industry ON dim_company(industry_key);
CREATE INDEX idx_dim_company_scd_dates ON dim_company(cik, valid_from, valid_to);
CREATE INDEX idx_dim_quarter_year_quarter ON dim_quarter(year_key, fiscal_quarter);
CREATE INDEX idx_dim_quarter_end_date ON dim_quarter(period_end_date);
CREATE INDEX idx_dim_filing_cik_period ON dim_filing(cik, report_period_end);
CREATE INDEX idx_dim_filing_form ON dim_filing(form);
CREATE INDEX idx_dim_concept_tag ON dim_concept(tag);
CREATE INDEX idx_dim_concept_standard_tag ON dim_concept(standard_tag);

CREATE INDEX idx_dim_raw_company_quarter ON dim_raw_financials(company_key, quarter_key);
CREATE INDEX idx_dim_raw_filing ON dim_raw_financials(filing_key);
CREATE INDEX idx_dim_raw_concept ON dim_raw_financials(concept_key);
CREATE INDEX idx_dim_raw_quarter_concept ON dim_raw_financials(quarter_key, concept_key);

CREATE INDEX idx_fact_metrics_company_quarter ON fact_financial_metrics(company_key, quarter_key);
CREATE INDEX idx_fact_metrics_quarter ON fact_financial_metrics(quarter_key);
CREATE INDEX idx_fact_health_company_quarter ON fact_health_score(company_key, quarter_key);
CREATE INDEX idx_fact_health_level ON fact_health_score(health_level);
CREATE INDEX idx_fact_health_zscore ON fact_health_score(altman_z_score);
CREATE INDEX idx_fact_benchmark_quarter_level ON fact_industry_benchmark(quarter_key, benchmark_level);
CREATE INDEX idx_fact_risk_company_quarter ON fact_risk_signal(company_key, quarter_key);
CREATE INDEX idx_fact_risk_distress ON fact_risk_signal(distress_flag);
CREATE INDEX idx_fact_risk_level ON fact_risk_signal(risk_level);

