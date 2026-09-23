-- Monthly revenue KPIs. A month is flagged partial when the data does not cover
-- it end to end (the extract starts 2009-12-01 and stops 2011-12-09).
WITH bounds AS (
    SELECT min(invoice_date) AS first_ts, max(invoice_date) AS last_ts FROM lines
)
SELECT
    order_month,
    round(sum(line_value), 2)                          AS revenue,
    count(DISTINCT invoice)                            AS orders,
    count(DISTINCT customer_id)                        AS identified_customers,
    round(sum(line_value) / count(DISTINCT invoice), 2) AS avg_order_value,
    round(100.0 * sum(line_value) FILTER (WHERE customer_id IS NULL) / sum(line_value), 2)
                                                       AS anonymous_revenue_pct,
    -- partial at the start if data begins after the 1st; at the end if it
    -- stops before the last day of the month
    (any_value(b.first_ts)::DATE > order_month
        OR any_value(b.last_ts)::DATE < last_day(order_month))
                                                       AS is_partial_month
FROM sales, bounds AS b
GROUP BY order_month
ORDER BY order_month;
