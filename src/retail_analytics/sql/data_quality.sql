-- How many raw lines each cleaning rule removes, in the order they are applied.
WITH flagged AS (
    SELECT
        CASE
            WHEN is_cancellation      THEN '1 cancellation line'
            WHEN NOT is_merchandise   THEN '2 non-merchandise code (postage, fees, adjustments)'
            WHEN quantity <= 0        THEN '3 non-positive quantity'
            WHEN price <= 0           THEN '4 non-positive price'
            ELSE                           '5 kept as a sale'
        END AS rule,
        line_value,
        customer_id IS NULL AS anonymous
    FROM lines
)
SELECT
    rule,
    count(*)                                      AS lines,
    round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct_of_lines,
    round(sum(line_value), 2)                     AS line_value,
    count(*) FILTER (WHERE anonymous)             AS anonymous_lines
FROM flagged
GROUP BY rule
ORDER BY rule;
