# Frozen Asset-Text Embeddings for Repeat-Preserving Financial Recommendation

**Mikhail Dmitrenko** · Team **HuggyWuggy**

midmitrenko@edu.hse.ru · **2026-11-13**

LLM4Rec, HSE University · Session 1: Research Question and Minimal Study Plan · **Encoder track**

## Abstract

Repeat purchases are important in financial recommendation, so replacing a strong history-based ranking can obscure the value of semantic item representations. This study proposes to retain Latest buy's historical prefix and replace only the free-slot TF-IDF representation with frozen Qwen3 asset-text embeddings, holding information and scoring rules fixed. Completed classical experiments on {{full_users}} warm users give nDCG@10 of {{mix_tfidf_all}} for popularity-plus-TF-IDF fill versus {{latest_all}} for original Latest buy, while the constrained oracle reaches {{oracle_all}}. The LLM comparison remains planned: the contribution is a controlled test of incremental representation value, not a claim of improved investment quality.

## 1. Introduction

FAR-Trans contains purchases, sales and asset information for financial recommendation [1], [6]. Under the course project's repeat-allowed task, a model should predict future purchases of either previously bought or new-to-user assets. This differs from the paper's new-asset-only evaluation. A semantic encoder may improve discovery, but it should be tested without changing a useful repeat-purchase mechanism.

> **Research question.** We test whether frozen LLM-derived asset-text embeddings improve mean nDCG@10 over popularity-plus-TF-IDF filling for FAR-Trans users in the course starter's full warm cohort, while keeping Latest buy's historical prefix unchanged.

| Element | Definition for this study |
|---|---|
| Intervention | Replace TF-IDF item vectors with frozen Qwen3-Embedding-0.6B vectors only. |
| Control | Popularity-plus-TF-IDF fill using the same pre-cutoff asset names and metadata. |
| Outcome | Mean nDCG@10 against future eligible purchases over all selected users, including empty truth. |
| Population | Current teaching cohort: {{full_users}} warm users; cutoff {{cutoff}}; June purchase window. |
| Track and state | **Encoder; partly run.** Classical diagnostics are complete; LLM inference and its main comparison are planned. |

**Research importance.** Repeat/explore modeling [2] and text-based item representations [3] are established, but frozen content features can underperform learned ID representations [5]. The new knowledge sought is whether a frozen semantic encoder adds ranking value specifically in free slots after a fixed recency prefix and a strong popularity term. A negative or null result would bound the usefulness of this low-training-cost design.

**Business value.** A recommendation product owner must decide whether to retain a cheap classical fill or pay the preparation, memory and maintenance costs of cached neural embeddings. A same-information comparison can support that decision even if the LLM does not improve ranking. Neither nDCG nor this offline study establishes profitability, suitability, causal business effects or user acceptance [1].

**Scope.** The team has agreed to use the course starter as its common working protocol [8]. Its dates, cohort and eligibility settings are teaching choices, not a declaration of the final instructor-defined project benchmark. The output remains one Top-10 list per evaluated user.

<!-- PAGEBREAK -->

## 2. Related Work

The following primary studies were opened in full text by the AI assistant; method, experimental and limitation sections were inspected. Author order and publication details were checked against DOI records or the workshop/university record. Student-side verification remains to be completed in Section 6.

| Study | Method | Data and evaluation | Limitation and connection |
|---|---|---|---|
| **[1] Sanz-Cruzado, Droukas and McCreadie (2024), Fin-RecSys / IJCAI workshop** | FAR-Trans release; transaction, price-regression and hybrid recommenders. | Financial transactions and prices; rolling temporal evaluation; nDCG@10 and ROI@10. | Excludes past purchases and requires active test users. Supplies our domain, but does not evaluate repeat-allowed fixed-prefix fills or text embeddings. |
| **[2] Ren et al. (2019), AAAI: RepeatNet** | GRU encoder, learned repeat/explore gate and separate decoders. | YOOCHOOSE, DIGINETICA, LASTFM; Recall and MRR at ranking cutoffs. | Session-level repeats differ from investment history. Learned repeat bias can harm exploration; motivates separating repeat and new-item effects. |
| **[3] Hou et al. (2022), KDD: UniSRec** | Precomputed BERT features, whitening/MoE adapter and contrastive sequence learning; text-only and text-plus-ID variants. | Amazon categories and Online Retail; full-item leave-one-out; Recall and nDCG. | Adapters and sequence components are trained. Transfer and long-tail evidence does not prove frozen cosine features help our fill-only setting. |
| **[4] Spadea and Seneviratne (2025), ICAIF: FLARKO** | Generative Qwen3 models, personal/market knowledge graphs and KTO/LoRA finetuning; centralized/federated variants. | FAR-Trans; 180-day outcomes; Hits@3 variants: Pref@3, Prof@3 and Comb@3. | Closest financial-domain LLM prior. Different inputs, training and objective; no frozen asset-vector swap, fixed recency prefix or nDCG@10 fill comparison. |
| **[5] Yuan et al. (2023), SIGIR: ID vs. modality representations** | Matched recommendation backbones compare IDs, frozen content features and end-to-end encoders. | MIND, H&M and Bili; full-pool HR@10 and nDCG@10; warm/cold-item and cost analyses. | Frozen features can be weaker than IDs or trained encoders; conclusions depend on domain/backbone. Closest controlled-encoder precedent, without financial fixed-prefix fills. |

**Nearest prior work.** FLARKO [4] is the closest financial-domain LLM study: it already evaluates KG-grounded, KTO-finetuned recommendations on FAR-Trans using purchase/profitability hit metrics. Yuan et al. [5] remain the closest methodological precedent for matched encoder comparisons and frozen versus end-to-end learning. UniSRec [3] provides modular text features with learned adaptation; RepeatNet [2] motivates repeat/explore separation.

**Gap.** FLARKO already studies KTO-finetuned LLM recommendations on FAR-Trans using knowledge-graph context and 180-day Hits@3 objectives [4]. Among the studies reviewed, we did not find a same-information comparison of frozen language-model asset-text embeddings against popularity-plus-TF-IDF filling that holds a recency-based historical prefix fixed and evaluates 30-day, repeat-allowed purchases with all-user mean nDCG@10. This is a bounded literature finding, not a global novelty claim.

**Terminology.** An asset new to one user's retained history can still be popular across other users. This is not the same as an item absent from all training interactions, the stronger cold/new-item condition considered in [5]. Moreover, reconstructed initial positions are excluded by the starter, so “new-to-user” here does not establish first-ever ownership. The present warm-user cohort is not a warm-item-only benchmark.

**Evidence for these summaries.** Section and table pointers, qualifications, checked links and complete author lists are retained in `literature/reading_notes.md`, `literature/link_checks.json` and `literature/references.bib`. The reviewed representation models should not all be described as prompted generative LLMs.

<!-- PAGEBREAK -->

## 3. Method

### 3.1. Data, protocol and one actual record

At cutoff **{{cutoff}}**, the starter selects the latest asset/customer rows strictly before prediction time, and assets with at least one positive pre-cutoff close price [8]. The full warm cohort contains **{{full_users}} users and {{eligible_assets}} eligible assets**, including stocks, funds and bonds under the data-driven rules. Users have retained historical Buy activity and an as-of profile. The label window is **[{{cutoff}}, {{end_exclusive}})**. Repeat purchases remain eligible; negative-ID initial positions and exact duplicate rows are excluded. The demo sample uses deterministic ID hashing; this report's main experiments use the full warm cohort.

The following is one real record from the public release [6]; only the customer identifier is replaced by a report-local alias. All other values are verbatim. Its ID is nonnegative and its event precedes both validation and test cutoffs.

```text
source: FAR-Trans.zip / transactions.csv; source line {{record_line}}
record id: {{record_id}}
fields: customerID, ISIN, transactionID, transactionType, timestamp,
        totalValue, units, channel, marketID
values: {{record_customer}}, {{record_isin}}, {{record_id}}, {{record_type}}, {{record_date}},
        {{record_value}}, {{record_units}}, {{record_channel}}, {{record_market}}
window: history before {{cutoff}}
```

| Fields / example values | Status and recorded time | Use |
|---|---|---|
| Transaction IDs, ISIN, Buy and date, as above | Observed released attributes at {{record_date}}; customer alias assigned for display | Grouping, eligibility/exclusion checks and history/recency |
| `assetName`: {{asset_name}} | Observed metadata; row {{asset_date}} | TF-IDF and planned embedding input |
| Category / subcategory / market: {{asset_category}} / {{asset_subcategory}} / {{asset_market}} | Observed metadata; row {{asset_date}} | Both content representations |
| `sector`, `industry`: empty strings | **Missing** at metadata row {{asset_date}} | Omitted; no future imputation |
| Customer: {{customer_type}}, {{customer_risk}}, {{customer_capacity}} | Observed labels; row {{profile_date}}; questionnaire {{questionnaire_date}} | Audit/context only; not scoring inputs |
| `totalValue` {{record_value}}; `units` {{record_units}} | Value estimated/derived; quantity can be split-adjusted; released date {{record_date}} | Displayed only; not scorer inputs |
| Close price {{pre_close}} | Observed released price, {{pre_close_date}} | Positive-price eligibility, not return prediction |

“Observed” refers to the released attribute, not proof of an unmodified raw observation. The paper documents adjusted units/dates, retrospective price processing and value estimation [1, Sec. 3]. For the example, {{record_units}} × {{event_close}} = {{record_value}}. Original per-field publication/adjustment times are not supplied. Counts, popularity, vectors and similarities are derived only from retained pre-cutoff inputs.

### 3.2. Leakage checks and field restrictions

**Customer information:** {{future_profiles}} selected pre-cutoff profiles contain a questionnaire date at or after the June cutoff; row timestamps alone cannot certify field availability. `Predicted_*` means estimated, not observed ground truth; there are {{predicted_risk}} such risk labels and {{predicted_capacity}} capacity labels in this cohort. Profile attributes are excluded from both encoders. Cohort membership follows the starter's convention, with placeholder-date uncertainty documented.

**Asset information:** no selected asset metadata row is dated at/after the cutoff; {{future_asset_rows}} future-dated raw rows are not used. Missing names/fields are not backfilled from later records. Recorded dates pass the as-of check, but field-level historical versioning remains a limitation.

**Limit prices:** the example's `maxDate` is {{limit_end}}, its endpoint price is {{limit_end_price}}, and its realized profitability is {{limit_return}}. These are future-derived at the prediction cutoff; min/max refer to series endpoints, not price extrema. The entire file is excluded. Eligibility uses pre-cutoff `close_prices.csv` instead. Source: `outputs/data_audit/audit.json`.

<!-- PAGEBREAK -->

### 3.3. Controlled encoder comparison — planned

Freeze Latest buy's prefix: up to ten historical assets ordered by last Buy date (ties by ISIN). Fill candidates are all eligible assets outside it. Both encoders receive identical as-of names, category, subcategory, sector, industry and market, omitting missing fields. Profiles, future transactions and returns are excluded.

**Control:** TF-IDF name unigrams and field-qualified tokens. **Intervention:** frozen **{{model_id}}** [7], revision `{{model_revision}}`; {{embedding_dimension}}-dimensional normalized vectors, last-token pooling, no instructions or finetuning. Both use the same normalized purchase-count-weighted history sum and free-slot score:

> **s(u,i) = distinct_buyers(i) / max_j distinct_buyers(j) + lambda × cosine(v_u, v_i)**

**Lambda = {{chosen_lambda}} for both** in the primary swap; no June tuning. **Ablations:** TF-IDF substitutes the representation using the same information; lambda = 0 removes similarity and recovers original Latest buy. All supplied baselines are retained; the diagnostic oracle never supplies inputs.

**Metric:** binary nDCG@10 uses eligible June purchases. DCG sums `rel_r / log2(r+1)`; IDCG places up to ten relevant assets first. Empty truth scores zero. Report all-user and nonempty means/counts, plus repeat/new hits. Ground truth is purchases, not an LLM judge.

**Runtime/cost:** time cold generation (loading, representation preparation, scoring/Top-10), excluding evaluation; separate preparation and cached generation. Use {{timing_repeats}} repeats on identical hardware, report median/range, dependencies, precision, batch size and peak memory. Local inference needs no paid API; log compute hours and actual rental charges. **Next sessions:** implement/cache embeddings and controls, then ablate, analyse failures and integrate under the final protocol. Frozen inference avoids sampling; diagnostic random fills use saved seeds.

## 4. Experiments — completed classical work

**All supplied baselines, full warm cohort.** All-user means include {{empty_users}} empty-truth users; the nonempty column uses {{nonempty_users}} users. Values are shown to four decimals.

| Method | Users | Nonempty | nDCG: all | nDCG: nonempty |
|---|---:|---:|---:|---:|
{{baseline_rows}}

Source: `outputs/baseline_full_warm/metrics.json`. Both cohort reruns were byte-identical across saved predictions, protocol, metrics and contexts; hashes are saved with this build.

**Fixed-prefix fills, same June users.** May validation: [{{validation_cutoff}}, {{validation_end}}), {{validation_users}} warm / {{validation_nonempty}} nonempty users. Both selected lambda = {{chosen_lambda}} from the saved grid, then each was evaluated once on June.

| Fill / fixed-history method | nDCG: all | nDCG: nonempty | New hits |
|---|---:|---:|---:|
{{fill_rows}}

Sources: `outputs/fill_experiment/metrics.json` and `outputs/fill_mixture/`. Random: {{random_seeds}}-seed mean, all-user SD {{random_std}}; all fills retain {{fixed_repeat_hits}} repeat hits. **LLM inference/timing: not run.**

<!-- PAGEBREAK -->

## 5. Discussion

**Position and interpretation.** I adopt fixed-prefix filling to isolate an Encoder change while protecting repeat recommendations. The data contain {{repeat_pairs}} repeat and {{new_pairs}} new future user–asset pairs ({{repeat_pair_pct}}% repeats). There are {{fill_users}} users with free slots, {{active_fill_users}} with future purchases. Pure similarity fill loses to popularity; mixtures improve slightly. The oracle ceiling is {{oracle_all}}, not a promised neural gain. Positive findings would support cached semantic features for this branch; negative/null findings would support classical fills.

**Threats and failure mechanisms.** June informed exploratory design and is not a pristine holdout; freeze settings before the LLM comparison and assess generalization under the final protocol. Empty truth dominates, full prefixes prevent intervention for some users, and short/multilingual names may provide weak semantics. The checkpoint postdates prediction time, leaving pretraining-contamination risk. Keep pseudonymized customer data local and treat text as data, not instructions. Ranking accuracy does not establish suitability or profit.

**Automated metric check, not yet personal verification.** One demo user's single relevant asset is at popularity rank {{case_pop_rank}} and Latest buy's first fill rank {{case_latest_rank}}. IDCG = {{case_idcg}}; rounded scores `1/log2({{case_latest_logarg}})` → {{case_latest_score}} and `1/log2({{case_pop_logarg}})` → {{case_pop_score}} match `per_user.csv`. Its excluded initial position means novelty is relative to retained history. Evidence: `outputs/demo_ndcg_nonzero/evidence.json`.

### Team Discussion — pending

No team discussion meeting has taken place yet. The previously agreed team name, Encoder role and use of the course starter are the current shared context.

> **[TO COMPLETE AFTER THE TEAM MEETING]**
> Options considered: questions, methods, baselines, data slices and rejected options.
> Agreement and unresolved differences: record the actual discussion.
> My contribution versus joint work: identify proposals/checks and shared ideas.
> My position and reasons: complete in my own words after the meeting.

## 6. AI Usage Disclosure

**Tools and scope.** OpenCode with OpenAI **gpt-6.1-sol** (`openai/gpt-6.1-sol`); harness version unrecorded. AI retrieved/synthesized sources, inspected the starter, generated/executed analyses, checked outputs, and drafted/rendered this report. Recorded analysis versions: Python {{python_version}}, NumPy {{numpy_version}}, SciPy {{scipy_version}}, scikit-learn {{sklearn_version}}. Qwen inference remains planned.

**Direction and attribution.** I selected fixed-prefix Encoder work and requested reproducibility, repeat/new, classical-fill, earlier-window, provenance and literature checks. The assistant implemented and ran the analyses; these are not claimed as my personal verification.

### What I personally verified

> **[TO BE COMPLETED BY MIKHAIL]**
> Exact output/source, independent procedure or calculation, and outcome.

### Trusted without verification

> **[TO BE COMPLETED BY MIKHAIL]**
> AI-generated claims, code or summaries accepted without independent checking.

**Session export to attach:** `dmitrenko_mikhail_session1_session.json` (native JSONL accepted). Attachment is pending; reconcile this disclosure with the actual native log before submission.

<!-- PAGEBREAK -->

## References

[1] J. Sanz-Cruzado, N. Droukas, and R. McCreadie, “FAR-Trans: An Investment Dataset for Financial Asset Recommendation,” in *IJCAI-24 Workshop on Recommender Systems in Finance (Fin-RecSys)*, Jeju, Republic of Korea, 2024. [Online]. Available: https://arxiv.org/html/2407.08692. Publication verified at https://eprints.gla.ac.uk/328250/. Accessed: Nov. 13, 2026.

[2] P. Ren, Z. Chen, J. Li, Z. Ren, J. Ma, and M. de Rijke, “RepeatNet: A Repeat Aware Neural Recommendation Machine for Session-Based Recommendation,” *Proceedings of the AAAI Conference on Artificial Intelligence*, vol. 33, no. 1, pp. 4806–4813, 2019, doi: 10.1609/aaai.v33i01.33014806. [Online]. Available: https://arxiv.org/html/1812.02646v1. Accessed: Nov. 13, 2026.

[3] Y. Hou, S. Mu, W. X. Zhao, Y. Li, B. Ding, and J.-R. Wen, “Towards Universal Sequence Representation Learning for Recommender Systems,” in *Proceedings of the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining*, pp. 585–593, 2022, doi: 10.1145/3534678.3539381. [Online]. Available: https://arxiv.org/html/2206.05941v1. Accessed: Nov. 13, 2026.

[4] F. Spadea and O. Seneviratne, “Aligning Language Models with Investor and Market Behavior for Financial Recommendations,” in *Proceedings of the 6th ACM International Conference on AI in Finance (ICAIF '25)*, pp. 509–517, 2025, doi: 10.1145/3768292.3770399. [Online]. Available: https://arxiv.org/html/2510.15993. Accessed: Nov. 13, 2026.

[5] Z. Yuan, F. Yuan, Y. Song, Y. Li, J. Fu, F. Yang, Y. Pan, and Y. Ni, “Where to Go Next for Recommender Systems? ID- vs. Modality-based Recommender Models Revisited,” in *Proceedings of the 46th International ACM SIGIR Conference on Research and Development in Information Retrieval*, pp. 2639–2649, 2023, doi: 10.1145/3539618.3591932. [Online]. Available: https://arxiv.org/html/2303.13835. Accessed: Nov. 13, 2026.

[6] University of Glasgow, “FAR-Trans: An Investment Dataset for Financial Asset Recommendation,” public data collection, 2024, doi: 10.5525/gla.researchdata.1658. [Online]. Available: https://researchdata.gla.ac.uk/1658/. Data definitions: https://researchdata.gla.ac.uk/1658/2/README.txt. Accessed: Nov. 13, 2026.

[7] Qwen, “Qwen3-Embedding-0.6B,” model card and open weights, Apache-2.0; revision {{model_revision}}. [Online]. Available: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B. Model/version metadata: https://huggingface.co/api/models/Qwen/Qwen3-Embedding-0.6B. Accessed: Nov. 13, 2026.

[8] S. Jin (dryjins), “FAR-Trans student starter and Homework 2 instructions,” *RecSys-LLMs* course repository, commit {{starter_commit}}. [Online]. Available: https://github.com/dryjins/RecSys-LLMs/tree/{{starter_commit}}/project/far-trans. Accessed: Nov. 13, 2026.
