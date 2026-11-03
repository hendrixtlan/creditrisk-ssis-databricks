-- Reference SQL translation of the legacy SSIS aggregation.
-- Must run after source tables contain your synthetic dataset.
DECLARE @as_of_date DATE = '2026-10-31';
WITH payments_by_loan AS (
    SELECT loan_id,
           SUM(CAST(payment_amount AS DECIMAL(28,2))) AS collected
    FROM dbo.Payments
    WHERE payment_date <= @as_of_date
    GROUP BY loan_id
), portfolio AS (
    SELECT c.region, c.risk_band, l.loan_id,
           l.principal_amount, l.outstanding_balance,
           CASE WHEN l.due_date < @as_of_date AND l.outstanding_balance > 0
                THEN l.outstanding_balance ELSE CAST(0 AS DECIMAL(18,2)) END AS past_due,
           COALESCE(p.collected, CAST(0 AS DECIMAL(28,2))) AS collected
    FROM dbo.Loans l
    JOIN dbo.Customers c ON c.customer_id = l.customer_id
    LEFT JOIN payments_by_loan p ON p.loan_id = l.loan_id
)
SELECT @as_of_date AS as_of_date, region, risk_band,
       COUNT(*) AS loan_count,
       SUM(principal_amount) AS total_principal,
       SUM(outstanding_balance) AS outstanding_exposure,
       SUM(past_due) AS past_due_exposure,
       SUM(collected) AS total_collected,
       CAST(CASE WHEN SUM(outstanding_balance) = 0 THEN 0
                 ELSE 100.0 * SUM(past_due) / SUM(outstanding_balance)
            END AS DECIMAL(12,4)) AS past_due_pct
FROM portfolio
GROUP BY region, risk_band
ORDER BY region, risk_band;
