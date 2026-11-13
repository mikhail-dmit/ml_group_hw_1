# Nonzero manual nDCG@10 check

User: `D63DFAE7E53493A5ADD5`, position 56 in the saved demo cohort of 100.
Cutoff: `2021-06-01`; label window: `[2021-06-01, 2021-07-01)`.

## Truth and the meaning of new

The user's one retained eligible June Buy is transaction `9059812`,
`GRS015003007` (ALPHA SERVICES AND HOLDINGS S.A.), dated `2021-06-09`.
Source: `FAR-Trans/transactions.csv`, line 144647 including the header.
Thus `truth = {GRS015003007}`, with one binary-relevant asset.

There is no retained pre-cutoff Buy of that asset. However, line 144646 is a
reconstructed initial-position Buy dated `2018-01-02`, transaction ID `-13769`.
The starter excludes it because its ID is negative. Consequently, this is new
relative to the starter's retained purchase history, not proof of first-ever
ownership. An audit of all demo users found that this is the only such new hit
for each of the two methods; neither method hits a June asset absent even from
initial-position Buy records.

## Rankings

| Rank | Latest buy | Latest buy origin | Popularity |
|---:|---|---|---|
| 1 | GRS003003035 | History, last Buy 2021-05-24 | GRS003003035 |
| 2 | GRF000011004 | History, last Buy 2021-04-01 | **GRS015003007 (relevant)** |
| 3 | GRC4261213D5 | History, last Buy 2021-03-19 | GRS014003032 |
| 4 | GRS393503008 | History, last Buy 2021-03-19 | GRC4261213D5 |
| 5 | GRS470003013 | History, last Buy 2021-03-19 | GRS323003012 |
| 6 | GRS495003006 | History, last Buy 2021-03-19 | GRS434003000 |
| 7 | **GRS015003007 (relevant)** | First popularity-fill slot | GRS393503008 |
| 8 | GRS014003032 | Popularity fill | GRS419003009 |
| 9 | GRS323003012 | Popularity fill | GRS426003000 |
| 10 | GRS434003000 | Popularity fill | GRS191213008 |

The latest-buy prefix contains all six retained historical assets. Same-date
ties use ascending ISIN. Popularity fill skips IDs already in the prefix, so
`GRS003003035`, the first popular asset, is skipped and `GRS015003007` fills rank 7.

## Calculator arithmetic

With one-based ranks, `DCG@10 = sum(rel_r / log2(r + 1))`.
One relevant asset gives `IDCG@10 = 1 / log2(2) = 1`.

Latest buy relevance vector: `[0,0,0,0,0,0,1,0,0,0]`.

```text
DCG_latest = 1 / log2(7 + 1) = 1 / log2(8) = 1/3
nDCG_latest = (1/3) / 1 = 0.3333333333333333
```

Popularity relevance vector: `[0,1,0,0,0,0,0,0,0,0]`.

```text
DCG_popularity = 1 / log2(2 + 1) = 1 / log2(3)
               = 1 / 1.584962500721156
               = 0.6309297535714575
nDCG_popularity = 0.6309297535714575 / 1 = 0.6309297535714575
```

## Comparison with saved scores

`outputs/baseline_default/per_user.csv`, lines 222 and 224:

```csv
D63DFAE7E53493A5ADD5,popularity,1,0.6309297535714575
D63DFAE7E53493A5ADD5,latest_buy,1,0.3333333333333333
```

Both agree exactly with the independent calculator arithmetic. Neither is
divided by 10 or by the number of users; those are individual-user scores.

Raw-data reconstruction, source line numbers, and independent numeric checks are
in `evidence.json`, produced without calling the starter's metric or data loader:

```bash
python3 -B analysis/demo_ndcg_walkthrough.py \
  --user-id D63DFAE7E53493A5ADD5 \
  --output-dir outputs/demo_ndcg_nonzero
```

This document is an AI-prepared worked example. It is not evidence that the
student has already performed the personal calculation or raw-file inspection.
