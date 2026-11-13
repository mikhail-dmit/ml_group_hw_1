# FLARKO — full-text verification and literature-selection decision

Checked by the AI assistant on **2026-11-13**. This update concerns literature
notes and gap wording. At the user's subsequent request, the verified replacement
was integrated into the report's literature and citation cross-references.

## Verified reference and accessible sources

Fernando Spadea and Oshani Seneviratne, **“Aligning Language Models with Investor
and Market Behavior for Financial Recommendations.”** *Proceedings of the 6th
ACM International Conference on AI in Finance* (**ICAIF 2025**), pp. **509–517**.
DOI: **10.1145/3768292.3770399**.

- Full text opened: https://arxiv.org/html/2510.15993
- Abstract/author/version record opened: https://arxiv.org/abs/2510.15993
- Publisher DOI resolved: https://doi.org/10.1145/3768292.3770399
- Independent publication metadata opened:
  https://api.crossref.org/works/10.1145/3768292.3770399

All four requests succeeded and returned the expected article or bibliographic
record. The full-text version read was **2510.15993v1**. Author names/order and
publication title, year, proceedings venue and page range agree with Crossref.

## What was read and what the paper actually tests

The full main text (§§1–9) was read, including data construction, prompts, training,
evaluation, ablations, baseline discussion and conclusion. Search snippets or the
abstract alone were not used as evidence for the protocol.

| Element | Verified full-text finding |
|---|---|
| Dataset | FAR-Trans: customer transaction histories, historical asset prices, metadata and investor attributes. |
| Personal graph (PKG), §3.1 | Pre-recommendation Buy/Sell transactions, ISINs, transaction values and dates. |
| Market graph (MKG), §3.1 | Historical price summaries over ten-week intervals, plus asset category/sector/industry; periods must end before the recommendation date. |
| Model/training, §§4–6.5 | Generative Qwen3 variants, 0.6B/1.7B/4B/8B; KTO finetuning with LoRA and quantization; centralized and simulated federated variants. The 8B model is excluded from federated training. |
| Training-data coverage, §6.1 | 2018-01-02 through 2021-11-30. |
| Training-prompt dates | Every four weeks, 2019-08-01 through 2021-06-01, as reported by the authors. |
| Test-data coverage | 2021-12-01 through 2022-11-29. |
| Test-prompt dates | Every two weeks, 2021-12-01 through 2022-06-02. Outcomes extend after the final prompt date. |
| Outcome horizon | **180 days** after each recommendation date, for both purchases and returns. |
| Training desirability label, §4 | An asset must be purchased by the user and have a positive return during that same future window. |
| Recommendation output, §3.2 | Prompt requests **three asset ISINs**. |
| Metrics, §6.3 | **Hits@3** variants: **Pref@3** for purchase hits; **Prof@3** for profitable-asset hits; **Comb@3** for the intersection. No nDCG@10 result is reported. |
| Baselines, §6.2 | Random Forest, Linear Regression, LightGBM; Popularity, LightGCN, ARM, MF, user-kNN; Random. No named Latest buy or Latest buy or sell baseline. |
| Context ablation, §7.1/Table 2 | Combined PKG+MKG, PKG only, MKG only, and no explicit context; combined context does not uniformly dominate. |

**Do not infer missing protocol details:** the article does not clearly establish
our full warm cohort, common eligible set, initial-position exclusion, empty-truth
zero policy or exact handling of already-bought candidates. The dataset being
FAR-Trans does not imply those conventions are identical. Its metric descriptions
also do not provide a detailed aggregation formula, so Pref@3 should not be
silently reinterpreted as our nDCG, recall or precision.

The paper's Qwen3 generative models are **not** the frozen Qwen3-Embedding model
planned for our study. It combines a different input set, finetuning, generation
and a purchase-plus-return objective; its results do not isolate an asset-text
representation swap.

## Decision: replace Recformer in the compact review

Keep the five central studies as:

1. FAR-Trans — dataset and original protocol.
2. RepeatNet — repeat/explore behavior.
3. UniSRec — cached textual features and adaptation.
4. **FLARKO** — LLM recommendation on the same financial dataset.
5. Yuan et al. — matched ID/modality comparisons and frozen-feature limitations.

FLARKO is closer to our **domain and use of an LLM on FAR-Trans** than Recformer.
UniSRec and Yuan et al. retain coverage of textual representations and cold-item
conditions. Recformer is preserved as supplementary reading, not deleted from the
source library. Adding a sixth table row is unnecessary under the assignment's
compact five-study target.

## Revised closest-work statement and gap

**FLARKO is the closest financial-domain LLM prior work; Yuan et al. remains the
closest methodological precedent for the controlled encoder comparison.**

Proposed gap text:

> FLARKO already studies KTO-finetuned LLM recommendations on FAR-Trans using
> knowledge-graph context and 180-day Hits@3 objectives. Among the studies
> reviewed, we did not find a same-information comparison of frozen language-model
> asset-text embeddings against popularity-plus-TF-IDF filling that holds a recency-based
> historical prefix fixed and evaluates 30-day, repeat-allowed purchases with
> all-user mean nDCG@10.

This preserves a narrow, condition-specific question. It does not claim that no
LLM financial recommendation research exists or that this search is exhaustive.

## Report integration status

The literature notes and report source number FLARKO as [4]. The report's related-
work row, closest-work/gap paragraphs and reference entry were updated together;
the introduction's item-representation claim now cites UniSRec [3], and the strict
cold-item terminology cites Yuan et al. [5]. Recformer remains supplementary
reading only. No experiments, RQ, method, discussion or disclosure content was
changed for this integration; the requested placeholders remain intact.
