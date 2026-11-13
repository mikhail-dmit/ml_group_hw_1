# Data example and temporal provenance — report material

## One actual historical transaction

Source: public FAR-Trans release, University of Glasgow, 2024, DOI
[10.5525/gla.researchdata.1658](https://doi.org/10.5525/gla.researchdata.1658),
[`FAR-Trans.zip`](https://researchdata.gla.ac.uk/1658/1/FAR-Trans.zip),
`transactions.csv`, line 83760 including the header.

```text
record id: 7438853 (transactionID; disambiguated by source line and the fields below)
fields: customerID,ISIN,transactionID,transactionType,timestamp,totalValue,units,channel,marketID
values: U001,GRS003003035,7438853,Buy,2020-01-14,1152.0,400.0,Internet Banking,XATH
window: historical input, timestamp < 2021-06-01; also before the May validation cutoff
```

Only `customerID` is replaced with the report-local pseudonym `U001`; all other
values are verbatim. This is pseudonymization of an already de-identified public
record, not a claim that a public transaction cannot be linked back to its source.
No real-world customer identity is attached. The released event date is
**2020-01-14**. The FAR-Trans paper (§3.3.1) explains that `totalValue` is
**estimated/derived** as shares times the closing price, rather than an original
observed execution amount. The other fields are recorded transaction attributes,
but shares can be split-adjusted and transaction dates can be clipped to the
available price-series interval during release preprocessing. The assigned alias is not
a verbatim source value. `transactionID` is retained for provenance and the
nonnegative-ID exclusion check; `totalValue`, `units`, `channel`, and the
transaction's `marketID` are shown for completeness but do not enter our scorers.
The transaction is a retained historical Buy, not a reconstructed initial position.

## Field-level provenance for this example

“Observed” below describes the release's field type, not independent verification
of its historical publication date. Metadata dates are the release's recorded
row-update dates. Missing values remain missing; they are not inferred from later
rows. An empty string is shown explicitly as `""`.

| Source / fields | Verbatim value(s), except the customer alias | Status | Recorded timestamp / availability rule | Role |
|---|---|---|---|---|
| Transaction: `customerID` | `U001` (assigned alias) | Observed source identifier, pseudonymized | Event `2020-01-14` | User grouping |
| Transaction: `ISIN` | `GRS003003035` | Observed | Event `2020-01-14` | History item and asset join |
| Transaction: `transactionID` | `7438853` | Observed | Event `2020-01-14` | Provenance; negative-ID exclusion check |
| Transaction: `transactionType` | `Buy` | Observed | Event `2020-01-14` | Historical purchase inclusion |
| Transaction: `timestamp` | `2020-01-14` | Observed | Event date itself | Cutoff filtering and Latest buy recency |
| Transaction: `totalValue` | `1152.0` | Estimated/derived from shares × closing price | Released event date `2020-01-14`; release-computation time not supplied | Displayed only, not a scoring input |
| Transaction: `units` | `400.0` | Recorded quantity, potentially split-adjusted | Released event date `2020-01-14`; adjustment provenance not supplied per row | Displayed only, not a scoring input |
| Transaction: `channel`, `marketID` | `Internet Banking`, `XATH` | Observed recorded attributes | Released event date `2020-01-14` | Displayed only, not scoring inputs |
| Asset: `assetName` | `NATIONAL BANK OF GREECE` | Observed | Metadata row `2018-01-02` | TF-IDF name input; planned embedding input |
| Asset: `assetCategory`, `assetSubCategory`, `marketID` | `Stock`, `Large Cap`, `XATH` | Observed | Metadata row `2018-01-02` | CBF and text features |
| Asset: `sector`, `industry` | `""`, `""` | Missing | Metadata row `2018-01-02`; true values unavailable | Omitted from content tokens; no imputation |
| Customer: `customerType`, `riskLevel`, `investmentCapacity` | `Mass`, `Income`, `CAP_LT30K` | Observed, not `Predicted_*` | Profile row `2020-01-14` | Audit/context only, not scoring inputs |
| Customer: `lastQuestionnaireDate` | `2019-07-16` | Observed date | Questionnaire date `2019-07-16`, profile row `2020-01-14` | Temporal audit only |
| Close price: `closePrice` | `2.584` | Observed | `2021-05-31`, strictly before June cutoff | Confirms a positive historical price for eligibility; not a return forecast |

The user-history purchase counts, distinct-buyer popularity, recency ordering,
TF-IDF values, and cosine scores are **derived from observed pre-cutoff data**.
They are not additional raw fields or predicted investment outcomes.

Provenance correction from reading the full paper: §3.3.1 describes estimated
monetary amounts and adjusted transaction records. The example asset's released
close price on `2020-01-14` is `2.88`, consistent with `400.0 × 2.88 = 1152.0`.
Thus “all displayed transaction fields are unmodified raw observations” would be
incorrect. The paper also describes retrospectively adjusted price series (§3.1.1);
we use price positivity only for eligibility, not numerical returns as features.

## Leakage audit

### `customer_information.csv`

The starter chooses the latest profile row strictly before each cutoff. However,
row-date filtering is not sufficient to prove field-level temporal validity:
among the **10,404 June full-warm profiles**, **1,318** have a
`lastQuestionnaireDate` on or after **2021-06-01**, despite having a pre-cutoff
profile `timestamp`. One pseudonymized example is:

```text
customerID: U002
customerType: Premium
riskLevel: Income
investmentCapacity: CAP_80K_300K
lastQuestionnaireDate: 2021-11-03
timestamp: 2021-03-19
```

The future questionnaire date itself cannot be an input at the June cutoff. This
inconsistency also prevents us from certifying that its associated questionnaire
attributes were available then; it does not establish exactly which attributes
were retrospectively updated. The current fill methods do not score with any
customer profile attributes, and these fields should remain outside the planned
asset-text encoder inputs unless their historical provenance is resolved.

In the same selected cohort, `riskLevel` has **725 estimated** (`Predicted_*`),
**9,659 observed**, and **20 missing** values; `investmentCapacity` has
**738 estimated**, **9,646 observed**, and **20 missing** values. Algorithmically
predicted fields are estimates, not verified ground truth; the release does not
give their per-field estimation/training times. There are also **41** selected
profiles with `timestamp = 2000-01-01` and **726** with that questionnaire date;
such sentinel dates do not establish genuine historical availability. Cohort
membership follows the starter's recorded-date convention, with this limitation
documented. The specific `U001` profile has a pre-cutoff, non-sentinel questionnaire
date and no within-row future date.

The same audit was performed for May: **1,324 of 10,178** selected profiles have
questionnaire dates on or after the May cutoff. Profile attributes were not used
for May scoring either.

### `asset_information.csv`

Use only the latest asset row strictly before the prediction cutoff, and never
backfill a missing attribute from a later row. In June, the raw file contains
**47 rows dated on or after the cutoff**; none is selected for the **767 eligible
assets**. Their selected metadata dates range from **2018-01-01 to 2021-05-26**.
The example asset's row is dated **2018-01-02**, with missing sector and industry.

Across the 767 selected assets, **23** names, **253** subcategories, **366** sectors,
and **411** industries are missing under the release's missing-value conventions.
These are excluded from the respective token streams rather than filled with
future knowledge. The audit confirms compliance with recorded row dates; the
release does not supply per-field publication/version histories, so historical
availability of every name/attribute cannot be independently established.

### `limit_prices.csv`

The release README defines `minDate` and `maxDate` as the **first and last dates
of the price series**, not the dates of its minimum and maximum prices.
`priceMinDate` and `priceMaxDate` are the prices at those endpoints. For the
example asset, the verbatim row is:

```csv
ISIN,minDate,maxDate,priceMinDate,priceMaxDate,profitability
GRS003003035,2018-01-02,2022-11-29,3.24,3.76,0.1604938271604936
```

| Field | Status | Temporal interpretation at the June cutoff |
|---|---|---|
| `minDate`, `priceMinDate` | Observed retrospective summary; endpoint price observed on `2018-01-02` | Historical endpoint could be reconstructed from pre-cutoff close prices |
| `maxDate`, `priceMaxDate` | Observed retrospective summary; endpoint price observed on `2022-11-29` | Future endpoint and price; unavailable at `2021-06-01` |
| `profitability` | Derived realized outcome from observed endpoint prices, not a predicted return | Depends on the future endpoint; unavailable until at least `2022-11-29` |

The audit verified both prices against `close_prices.csv` and verified
`profitability = 3.76 / 3.24 - 1`. **553 of 767 eligible assets** have a
`limit_prices.maxDate` on or after the June cutoff. The current recommendation
pipelines exclude the entire `limit_prices.csv` file, including its profitability
field. Eligibility is computed from positive **pre-cutoff** rows of
`close_prices.csv`, not from full-series endpoints or realized returns.

## Reproducible evidence

The automated checks are implemented in `analysis/audit_data_provenance.py`;
their results, the pseudonymized record, both cutoff audits, and source-file
SHA-256 hashes are saved in `outputs/data_audit/audit.json`. They establish the
reported automated checks, not a claim that the student personally performed
them. Personal verification should be described separately when actually done.
