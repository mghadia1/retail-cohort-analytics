-- What share of identified-customer revenue comes from the top X% of customers.
WITH ranked AS (
    SELECT
        customer_id,
        sum(line_value) AS revenue,
        row_number() OVER (ORDER BY sum(line_value) DESC) AS position,
        count(*) OVER () AS customers
    FROM customer_sales
    GROUP BY customer_id
),
cuts(top_pct) AS (VALUES (1), (5), (10), (20), (50))
SELECT
    top_pct,
    count(*)                                                        AS customers,
    round(100.0 * sum(revenue) / (SELECT sum(revenue) FROM ranked), 2) AS revenue_share_pct
FROM cuts
JOIN ranked ON ranked.position <= ceil(ranked.customers * top_pct / 100.0)
GROUP BY top_pct
ORDER BY top_pct;
