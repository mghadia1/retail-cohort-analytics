-- Recency / frequency / monetary scores, 1 (worst) to 5 (best).
--
-- Scores come from percent_rank rather than NTILE: NTILE splits tied values
-- across buckets arbitrarily, so two customers with one order each could land
-- in different frequency scores. percent_rank gives ties the same score.
WITH snapshot AS (
    SELECT max(invoice_date)::DATE + 1 AS as_of FROM customer_sales
),
per_customer AS (
    SELECT
        customer_id,
        date_diff('day', max(invoice_date)::DATE, any_value(s.as_of)) AS recency_days,
        count(DISTINCT invoice)                                       AS frequency,
        round(sum(line_value), 2)                                     AS monetary
    FROM customer_sales, snapshot AS s
    GROUP BY customer_id
),
scored AS (
    SELECT
        *,
        least(5, 1 + floor(5 * percent_rank() OVER (ORDER BY recency_days DESC)))::INT AS r_score,
        least(5, 1 + floor(5 * percent_rank() OVER (ORDER BY frequency)))::INT         AS f_score,
        least(5, 1 + floor(5 * percent_rank() OVER (ORDER BY monetary)))::INT          AS m_score
    FROM per_customer
)
SELECT
    *,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
        WHEN r_score <= 2 AND f_score >= 4 THEN 'At risk'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'Recent, low frequency'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'Hibernating'
        ELSE 'Needs attention'
    END AS segment
FROM scored
ORDER BY customer_id;
