-- Merchandise returned (cancelled) value as a share of gross merchandise sales,
-- for countries with at least 1,000 sale lines.
WITH gross AS (
    SELECT country, count(*) AS sale_lines, sum(line_value) AS gross_sales
    FROM sales GROUP BY country
),
returned AS (
    SELECT country, -sum(line_value) AS returned_value
    FROM merchandise_returns GROUP BY country
)
SELECT
    country,
    sale_lines,
    round(gross_sales, 2)                                          AS gross_sales,
    round(coalesce(returned_value, 0), 2)                          AS returned_value,
    round(100.0 * coalesce(returned_value, 0) / gross_sales, 2)    AS return_rate_pct
FROM gross LEFT JOIN returned USING (country)
WHERE sale_lines >= 1000
ORDER BY gross_sales DESC;
