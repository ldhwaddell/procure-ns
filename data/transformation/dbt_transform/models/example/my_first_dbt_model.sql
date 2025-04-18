{{ config(materialized='table') }}

WITH awards AS (
  SELECT
    tm."procurementEntity",
    (award->>'awardAmount')::text::money AS award_amount
  FROM {{ ref('tender_metadata') }} tm
  CROSS JOIN LATERAL jsonb_array_elements(tm."tenderAwardData") AS award
  WHERE award->>'awardAmount' ~ '^\d+(\.\d+)?$'
)

SELECT
  "procurementEntity",
  SUM(award_amount) AS total_tender_value
FROM awards
GROUP BY "procurementEntity";
