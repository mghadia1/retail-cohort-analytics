-- Cleaning rules, expressed once as views so every analysis shares them.
-- Input: a relation named raw_lines with the columns written by data.prepare.

CREATE OR REPLACE VIEW lines AS
SELECT
    *,
    quantity * price                                  AS line_value,
    starts_with(invoice, 'C')                         AS is_cancellation,
    -- Merchandise has a five-digit stock code, optionally followed by letters
    -- (85123A, 15056bl). POST, DOT, M, BANK CHARGES, AMAZONFEE, gift vouchers
    -- and the DCGS gift-shop codes are fees, adjustments or a separate channel.
    regexp_full_match(stock_code, '[0-9]{5}[A-Za-z]*') AS is_merchandise,
    date_trunc('month', invoice_date)::DATE           AS order_month
FROM raw_lines;

-- A sale: merchandise, not a cancellation, positive quantity and price.
CREATE OR REPLACE VIEW sales AS
SELECT * FROM lines
WHERE is_merchandise
  AND NOT is_cancellation
  AND quantity > 0
  AND price > 0;

-- Customer-level analyses need an identified customer. Anonymous sales still
-- count toward revenue KPIs, just not toward cohorts or RFM.
CREATE OR REPLACE VIEW customer_sales AS
SELECT * FROM sales WHERE customer_id IS NOT NULL;

-- Merchandise cancellations, used for the return-rate figure.
CREATE OR REPLACE VIEW merchandise_returns AS
SELECT * FROM lines WHERE is_merchandise AND is_cancellation;
