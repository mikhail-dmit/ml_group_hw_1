# Related work for HuggyWuggy — Encoder / fixed-history fill study

Checked on **2026-11-13**. The five selected full-text articles were opened and their
methods, experimental protocols, results/ablations and conclusions read beyond
the abstract. Detailed section/table pointers and qualifications are in
`reading_notes.md`. These are AI-performed source checks, not a claim that the
student has already personally read or verified each paper.

**Revised selection after checking FLARKO:** replace Recformer in the compact
five-study review with FLARKO, which directly studies LLM recommendations on
FAR-Trans. Retain FAR-Trans, RepeatNet, UniSRec and Yuan et al. Recformer's reading
notes and BibTeX entry remain as supplementary material. The report source now
uses [4] for FLARKO in the table, closest-work/gap paragraphs and bibliography;
the former Recformer-dependent citations in the introduction and terminology
paragraph have been corrected.

## Comparison table

| Study (authors, year, venue) | Method | Data and evaluation | Limitation / connection to our question |
|---|---|---|---|
| **[1] Sanz-Cruzado, Droukas and McCreadie, 2024, Fin-RecSys workshop at IJCAI-24. FAR-Trans.** | Introduces the financial dataset and compares 11 random, popularity, collaborative, price-regression and hybrid recommenders. | Financial asset transactions and prices, 2018–2022; Table 1 reports 29,090 customers and 806 assets. Evaluates 61 time points with six-month windows; **nDCG@10 and ROI@10**. | The published ranking task **excludes previously bought assets** and retains customers active in both train and test. It is not our repeat-allowed 30-day, empty-truth-inclusive starter protocol. Establishes the data/domain and strong popularity effects, but does not test text embeddings or fixed-history fill slots. |
| **[2] Ren et al., 2019, AAAI. RepeatNet.** | GRU session encoder with a learned repeat/explore gate, an attention/copy-style decoder over historical items and a decoder over items outside the current session. | **YOOCHOOSE 1/4, DIGINETICA, LASTFM**; next-event prediction with **Recall@10/20 and MRR@10/20**; repeat/non-repeat and component ablations. | Repeat refers to the current session, not a customer's full investment history. The model learns both branches and their gate, whereas we freeze the history prefix. Authors find excessive repeat bias can hurt non-repeat sessions. Supports separating repeat and discovery effects and retaining repeat-aware baselines. |
| **[3] Hou et al., 2022, KDD. UniSRec.** | Uses precomputed BERT item-text features, parametric whitening and a mixture-of-experts adapter; contrastive multi-domain sequence pretraining. Tests text-only and text-plus-ID variants. | Pretrains on five Amazon categories; transfers to five other Amazon categories and **Online Retail**. Leave-one-out, full-item ranking; **Recall and nDCG @10/@50**; adapter ablations and long-tail-item analysis. | Frozen language features do **not** mean the entire recommender is training-free: adapters and sequential components are learned. Five-core filtering and next-item tests differ from our sparse financial cohort and purchase-set labels. Motivates reusable text representations and tests whether IDs add value, not an assumption that frozen cosine similarity alone is sufficient. |
| **[4] Spadea and Seneviratne, 2025, ICAIF. FLARKO.** | Generative Qwen3 models receive personal-transaction and historical-market knowledge graphs; KTO/LoRA finetuning targets purchases with positive returns. Centralized and simulated federated variants. | **FAR-Trans**; training data through Nov. 2021, test period Dec. 2021–Nov. 2022; **180-day** outcome windows. Reports **Hits@3 variants: Pref@3, Prof@3, Comb@3**, with context/model ablations. | Closest financial-domain LLM prior work. Does not report our nDCG@10 fixed-prefix, same-information frozen-embedding comparison. Its market-price inputs, finetuning objective, horizon and cohort conventions are not our protocol; repeat eligibility/empty-truth handling are not specified sufficiently to equate the tasks. |
| **[5] Yuan et al., 2023, SIGIR. Where to Go Next for Recommender Systems? ID- vs. Modality-based Recommender Models Revisited.** | Matched DSSM/SASRec backbones compare ID lookup embeddings with text/image encoders; contrasts frozen feature extraction plus trainable heads against end-to-end encoder training. | **MIND** news titles, **H&M** images, **Bili** video-cover images; leave-one-out, full-pool ranking; **HR@10 and nDCG@10**. Regular/warm-item, frozen-vs-trained, cost and cold/new-item analyses. | Frozen features often underperform ID and end-to-end alternatives; results depend on the backbone and domain. No financial assets, fixed recency prefix or free-slot-only intervention. This is the closest methodological precedent for isolating an encoder change and a direct reason to treat frozen-embedding gains as an empirical question. |

UniSRec and [5] study text/modality representations; FLARKO instead finetunes
generative Qwen3 models. It does not use the Qwen3-Embedding checkpoint planned
for our item vectors. Do not conflate cached frozen features, trained generative
recommendation and recommendation-specific sequence learning.

## Closest prior work and defensible gap

**Closest financial-domain LLM prior work: FLARKO [4].** It already evaluates
LLM recommendations on FAR-Trans using behavioral and market graphs, KTO
finetuning and purchase/profitability hit metrics at a longer horizon. Therefore,
our contribution cannot be framed as introducing LLM recommendation to FAR-Trans.

**Closest methodological prior work: [5].** It asks whether replacing ID item
representations by modality encoders helps under matched recommendation
backbones, and explicitly studies frozen versus end-to-end learning. It finds
that frozen features are not automatically suitable for preference prediction.
**[3] is the closest modular text-feature architecture**, but adds learned
adaptation and sequence pretraining. **[2] motivates separating repeat and
explore behavior**, while [1] supplies the financial setting.

Suggested gap wording:

> FLARKO already studies KTO-finetuned LLM recommendations on FAR-Trans using
> knowledge-graph context and 180-day Hits@3 objectives [4]. Among the studies
> reviewed, we did not find a same-information comparison of frozen language-model
> asset-text embeddings against popularity-plus-TF-IDF filling that holds a recency-based
> historical prefix fixed and evaluates 30-day, repeat-allowed purchases with
> all-user mean nDCG@10.

This is a bounded statement about the reviewed literature, not an exhaustive
global novelty claim. Text representations, frozen encoders and repeat/explore
models are already established; the proposed contribution is a controlled test
of their incremental usefulness under this particular constraint.

## Terminology to keep separate

- **New to the user:** absent from that user's retained pre-cutoff Buy history;
  an item can still be globally popular. Excluded reconstructed initial
  positions mean this is not proof of first-ever ownership.
- **Globally cold/new item:** absent from *all users'* training interactions.
  This is the stronger setting explicitly examined in [5] and in supplementary
  Recformer reading.
- **Long-tail item:** has few training interactions, with the threshold defined
  before evaluation. It is not necessarily unseen.
- **Warm user:** has historical purchases. A warm user may buy either cold or
  popular items. Our full warm-user cohort is not a warm-item-only benchmark.

Consequently, do not describe every new-to-user fill success as solving item
cold start. Keep common all-user nDCG@10 primary; cold-item and repeat/new
breakdowns can be clearly labeled secondary diagnostics.

## Verified IEEE-style references

[1] J. Sanz-Cruzado, N. Droukas, and R. McCreadie, “FAR-Trans: An Investment
Dataset for Financial Asset Recommendation,” in *IJCAI-24 Workshop on Recommender
Systems in Finance (Fin-RecSys)*, Jeju, Republic of Korea, 2024. [Online].
Available: https://arxiv.org/html/2407.08692. [Accessed: Nov. 13, 2026].

[2] P. Ren, Z. Chen, J. Li, Z. Ren, J. Ma, and M. de Rijke, “RepeatNet: A Repeat
Aware Neural Recommendation Machine for Session-Based Recommendation,” in
*Proceedings of the AAAI Conference on Artificial Intelligence*, vol. 33, no. 1,
pp. 4806–4813, 2019, doi: 10.1609/aaai.v33i01.33014806. [Online]. Available:
https://arxiv.org/html/1812.02646v1. [Accessed: Nov. 13, 2026].

[3] Y. Hou, S. Mu, W. X. Zhao, Y. Li, B. Ding, and J.-R. Wen, “Towards Universal
Sequence Representation Learning for Recommender Systems,” in *Proceedings of
the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining*,
pp. 585–593, 2022, doi: 10.1145/3534678.3539381. [Online]. Available:
https://arxiv.org/html/2206.05941v1. [Accessed: Nov. 13, 2026].

[4] F. Spadea and O. Seneviratne, “Aligning Language Models with Investor and
Market Behavior for Financial Recommendations,” in *Proceedings of the 6th ACM
International Conference on AI in Finance (ICAIF '25)*, pp. 509–517, 2025,
doi: 10.1145/3768292.3770399. [Online]. Available:
https://arxiv.org/html/2510.15993. [Accessed: Nov. 13, 2026].

[5] Z. Yuan, F. Yuan, Y. Song, Y. Li, J. Fu, F. Yang, Y. Pan, and Y. Ni, “Where to
Go Next for Recommender Systems? ID- vs. Modality-based Recommender Models
Revisited,” in *Proceedings of the 46th International ACM SIGIR Conference on
Research and Development in Information Retrieval*, pp. 2639–2649, 2023,
doi: 10.1145/3539618.3591932. [Online]. Available:
https://arxiv.org/html/2303.13835. [Accessed: Nov. 13, 2026].

## Source-verification notes

All five linked HTML full texts opened successfully. The four proceedings DOIs
resolved to matching bibliographic metadata, and Crossref records independently
confirmed author order, title, venue, year and pages. For [1], the University of
Glasgow publication record and the workshop program confirmed the workshop
publication; it must not be cited as an IJCAI main-conference paper. RepeatNet's
arXiv preprint is dated 2018, but the verified AAAI publication is **2019**.
Successful checks and access limitations are recorded in `link_checks.json`.
