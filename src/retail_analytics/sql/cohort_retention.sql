-- Monthly acquisition cohorts. A customer's cohort is the month of their first
-- identified sale; they are "active" in any later month in which they buy again.
WITH first_purchase AS (
    SELECT customer_id, min(order_month) AS cohort_month
    FROM customer_sales
    GROUP BY customer_id
),
activity AS (
    SELECT DISTINCT customer_id, order_month FROM customer_sales
),
last_month AS (
    SELECT max(order_month) AS m, max(invoice_date) AS ts FROM customer_sales
),
cells AS (
    SELECT
        f.cohort_month,
        date_diff('month', f.cohort_month, a.order_month) AS months_since,
        count(*)                                          AS active_customers
    FROM activity AS a
    JOIN first_purchase AS f USING (customer_id)
    GROUP BY ALL
),
sizes AS (
    SELECT cohort_month, count(*) AS cohort_size FROM first_purchase GROUP BY cohort_month
)
SELECT
    c.cohort_month,
    c.months_since,
    s.cohort_size,
    c.active_customers,
    round(c.active_customers / s.cohort_size, 4) AS retention,
    -- The final month only runs to 2011-12-09, so any cell landing there
    -- understates activity. Flag it rather than letting it read as churn.
    (c.cohort_month + to_months(c.months_since) = l.m
        AND l.ts < l.m + INTERVAL 1 MONTH - INTERVAL 1 DAY) AS is_partial_period
FROM cells AS c
JOIN sizes AS s USING (cohort_month)
CROSS JOIN last_month AS l
ORDER BY c.cohort_month, c.months_since;
