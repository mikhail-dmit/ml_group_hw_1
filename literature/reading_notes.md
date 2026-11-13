# Full-text reading notes and checks

Date: 2026-11-13. Reading/checking below was performed by the AI assistant.
The full article bodies were consulted, not only abstracts or search snippets.
Scope: five selected primary studies, plus retained supplementary Recformer
notes; not a systematic/exhaustive review. After verifying FLARKO, it replaces
Recformer as [4] in the revised compact review and report source; existing
Recformer-dependent citations were corrected during report integration.

## [1] FAR-Trans — Sanz-Cruzado, Droukas, McCreadie

**Read:** §§1–6, with particular attention to dataset construction (§§3.1–3.4),
task definition (§5.1), temporal post-processing (§5.2.1), metrics (§5.2.2),
algorithms (§5.2.3), Table 2 and conclusions.

**Verified publication:** IJCAI-24 Workshop on Recommender Systems in Finance
(Fin-RecSys), Jeju, 4 August 2024. University of Glasgow's record says published
and refereed; the workshop program lists it as an accepted paper. This is a
workshop paper, not an IJCAI main-track proceedings article. The dataset DOI is
not a separate DOI for the paper.

**Method / data:** financial transactions, asset/customer metadata and adjusted
price time series spanning January 2018–November 2022. Paper Table 1 reports
806 assets, 29,090 customers and approximately 388k transactions; these are paper
statistics, not our June-as-of cohort sizes. Compares 11 methods: random; three
price regressors; popularity; LightGCN, MF, user-kNN and association rules; two
LightGBM-based hybrids.
Its popularity description counts purchase occurrences, unlike the starter's
distinct historical buying users; do not assume the implementations coincide.

**Evaluation:** 61 prediction dates spaced two weeks apart, starting August 2019;
six-month label windows. Previously purchased assets are excluded from the
ranking; training/test purchase overlap is removed from test. Users need at least
one training and one test interaction. Reports nDCG@10 and monthly ROI@10 for a
six-month holding interval. Hyperparameters are chosen by six-month ROI on three
specified dates, not by our primary purchase-ranking metric.

**Concrete result check:** Table 2 gives LightGCN nDCG@10 **0.3404** and popularity
**0.2710**. These cannot be compared numerically with our starter scores because
the task, horizon, selected users and empty-truth policy differ. The paper finds
transaction models stronger for predicting investments and price models stronger
for its profitability objective; the two objectives are not interchangeable.

**Important preprocessing detail, relevant to our data section:** §3.3.1 says
shares are adjusted for stock splits, synthetic initial buys are reconstructed
using excess sales over the full period, transaction dates outside price-series
coverage are moved to the nearest covered date, and total monetary values are
estimated from shares times closing price. Thus a nonnegative retained row is
not necessarily an untouched original observation in every field. In our sample,
400 shares × released close price 2.88 = totalValue 1152.0. The saved data section
has been corrected to mark `totalValue` estimated/derived. These monetary values
are not used by our current scorers.

**Connection:** source and protocol contrast for the study; evidence that
popularity is substantial. It does not evaluate a frozen text encoder or
repeat-preserving fill intervention.

## [2] RepeatNet — Ren et al.

**Read:** §§1–6, especially the repeat/explore mixture (Eq. 2 and §§3.3–3.5),
data/metrics (§4.1), main results (Table 3), repeat/non-repeat ablations
(Tables 4–5), attention analysis and joint-learning results (Tables 6–8).

**Verified authors:** Pengjie Ren; Zhumin Chen; Jing Li; Zhaochun Ren; Jun Ma;
Maarten de Rijke. AAAI 2019, vol. 33(1), pp. 4806–4813. The preprint date is
December 2018; use **2019** when citing the conference publication.

**Method:** a GRU encodes the current session. A learned gate produces repeat and
explore mode probabilities. The repeat decoder concentrates probability on
previously clicked session items, aggregating repeated occurrences. The explore
decoder masks items already present in the session. Recommendation probabilities
combine both branches. Model/item embeddings are trained, not frozen LM features.

**Data / metrics:** YOOCHOOSE 1/4 (e-commerce), DIGINETICA (e-commerce), LASTFM
(artist listening). Filters short sessions/rare items; LASTFM keeps the most
popular 40,000 artists. Reports Recall@10/20 and MRR@10/20 for a single next
event, not nDCG against a month-long set of purchases.

**Do not overstate the abstract:** Table 3's DIGINETICA Recall@20 is **47.79%**
for RepeatNet versus **49.70%** for NARM. It does not win every metric on every
dataset. §5.2 explicitly states the learned gate can favor repeat recommendations
too much and hurt non-repeat sessions. Table 5 reports LASTFM non-repeat
Recall@20 **16.79%** with the repeat mechanism versus **20.10%** without it.

**Connection:** separation of repeats and exploration is an established idea.
Our deterministic preserved-history prefix is a much simpler controlled design,
not a new repeat/explore architecture. Keeping it fixed isolates changes in the
discovery/fill branch and avoids attributing gains from repeat behavior to text.

## [3] UniSRec — Hou et al.

**Read:** §§1–5; BERT feature extraction (§2.2.1), whitening/MoE (§§2.2.2–2.2.3),
contrastive objectives (§2.3), inductive/transductive adaptation (§2.4), full
experimental setup (§3.1), Table 3, component/long-tail analyses (§3.3).

**Verified authors:** Yupeng Hou; Shanlei Mu; Wayne Xin Zhao; Yaliang Li;
Bolin Ding; Ji-Rong Wen. KDD 2022, pp. 585–593.

**Method:** encodes concatenated item title/category/brand text with BERT's CLS
representation. BERT text features are precomputed; learned parametric whitening
and an eight-expert adapter transform them. A Transformer sequence encoder is
pretrained using sequence–item and sequence–sequence contrastive objectives.
Adaptation freezes the main pretrained architecture and tunes lightweight
adapters; the transductive variant additionally learns item-ID embeddings.
Therefore “frozen BERT” must not be paraphrased as “no recommendation training.”

**Data:** pretraining on Amazon Grocery/Food, Home/Kitchen, CDs/Vinyl, Kindle and
Movies/TV; target categories Scientific, Pantry, Instruments, Arts and Office;
also transfers to UK Online Retail without shared users/items. Five-core
filtering; Amazon text contains title/categories/brand, Retail uses Description;
up to 512 text tokens. These texts are richer than many FAR-Trans asset names.

**Evaluation:** each user's last event is test, penultimate is validation. Ranks
the target among the full item universe. Recall@10/50 and nDCG@10/50; early
stopping by validation nDCG@10. Main Table 3 tests text-only UniSRec_t and
text-plus-ID UniSRec_t+ID. §3.3.3 groups by training item popularity, providing
long-tail evidence rather than a uniform proof for every globally unseen item.

**Concrete result check:** Scientific nDCG@10 is **0.0641** for text-only and
**0.0634** with IDs. On Office, text-only nDCG@10 **0.0619** is below SASRec
**0.0710** and FDSA **0.0868**. Text-only or added-ID superiority is not universal.

**Connection:** useful precedent for reusable item-text features, optional ID
signals and adaptation. Our proposed cached frozen features plus a fixed
count-weighted user profile do not reproduce its learned sequential architecture.

## [4] FLARKO — Spadea and Seneviratne

**Read:** complete main text §§1–9, including PKG/MKG construction (§3), prompt
format (§3.2), KTO label construction (§4), federated setup (§5), full evaluation
protocol (§6), context/model ablations and baseline comparisons (§7), conclusion
and resource statement (§§8–9). Verification details are in `flarko_review.md`.

**Verified authors/venue:** Fernando Spadea and Oshani Seneviratne, Rensselaer
Polytechnic Institute. *Proceedings of the 6th ACM International Conference on AI
in Finance* (ICAIF '25), pp. 509–517, 2025. DOI 10.1145/3768292.3770399. The DOI
resolver and Crossref returned matching title, author order, venue, year and pages.
Open full text: https://arxiv.org/html/2510.15993, version 2510.15993v1.

**Method/data:** uses FAR-Trans, not a different financial dataset. A personal
knowledge graph serializes pre-recommendation Buy/Sell history, ISINs, values
and dates. A market graph serializes historical price summaries and asset
category/sector/industry; only summary periods ending before the recommendation
date are included. Qwen3 generative models are KTO-finetuned using LoRA and
quantization. Desirable labels require both a future purchase and a positive
return over the same horizon. CenFLARKO is centralized; FedFLARKO simulates
federated clients. This is not frozen asset-vector cosine retrieval.

**Exact timeline in §6.1:** training data January 2, 2018–November 30, 2021;
training prompts sampled every four weeks from August 1, 2019–June 1, 2021.
Test dataset December 1, 2021–November 29, 2022; test prompt dates every two weeks
from December 1, 2021–June 2, 2022. The label/return horizon is **180 days**;
the later dataset endpoint allows outcomes after the last prompt to be observed.
Do not conflate prompt dates with the full test-data coverage interval.

**Metrics in §6.3:** the authors call them Hits@3, with **Pref@3** against purchased
assets, **Prof@3** against profitable assets, and **Comb@3** against their
intersection. Prompts request three ISIN recommendations. No nDCG@10 result is
reported. The section describes the hit metrics but does not give a full
mathematical aggregation definition; do not silently relabel them as precision,
recall or discounted ranking scores.

**Limitations relative to our comparison:** longer horizon; different prediction
dates, information and objective; trained generative model rather than a frozen
embedding checkpoint. §6.2 lists price regressors, popularity, LightGCN, ARM, MF,
user-kNN and random baselines, but not Latest buy or Latest buy or sell. The
article does not establish our cohort/eligibility/empty-truth/repeat policies, so
they should be marked unspecified rather than inferred from its dataset citation.
There is no fixed-history fill experiment or same-information TF-IDF control.

**Read beyond broad claims:** Table 2 and §7.1 report that combining both graphs
can hurt smaller models compared with a single graph. The conclusion's broad
claim that combined context is strongest is not a result holding across all
configurations. We need no FLARKO performance number to motivate our gap, and we
do not import its profitability claims into our purchase-ranking task.

**Selection decision:** use FLARKO instead of Recformer in the five-study table.
FAR-Trans supplies the dataset, RepeatNet the repeat/explore distinction, UniSRec
cached text-feature architecture, Yuan et al. frozen-versus-ID evidence, and
FLARKO direct LLM-on-FAR-Trans prior work. Recformer remains useful background,
but its trained text/sequence evidence overlaps other retained studies and is
less direct for the specific financial frozen-fill question.

## Supplementary reading, not in the revised five-study table: Recformer — Li et al.

**Read:** §§1–5, including model input and embedding layers (§2.2), cosine
retrieval (§2.2.4), language/recommendation pretraining (§2.3.1), two-stage
finetuning (§2.3.2 and Algorithm 1), full setup (§3.1), low-resource analysis
(§3.3), unseen-item evaluation (§3.4.1/Table 3), ablations (§3.4.2/Table 4).

**Verified authors:** Jiacheng Li; Ming Wang; Jin Li; Jinmiao Fu; Xin Shen;
Jingbo Shang; Julian McAuley. KDD 2023, pp. 1258–1267. Jiacheng Li and Jin Li are
different authors; do not collapse them because their IEEE initials coincide.

**Method:** flattens text key–value attributes (title/categories/brand) into item
sentences and encodes reversed recent-first sequences with a Longformer-style
network. Adds token-type and item-position embeddings. Item and user-sequence
representations share the encoder; cosine similarity scores all items. Initializes
from Longformer and pretrains with masked language modeling plus contrastive
next-item learning, then performs two-stage target finetuning. Freezing an item
feature matrix in stage 2 is not the same as leaving an off-the-shelf LM untrained.

**Data / protocol:** seven Amazon categories for pretraining, CDs/Vinyl for
pretraining validation; Scientific, Instruments, Arts, Office, Games and Pet as
six target categories. Five-core inputs; removes items without titles. Last-event
test / penultimate validation; full-item ranking. Reports nDCG@10, Recall@10 and
MRR. Additional zero-shot transfer, 1–100% training-data and cold-item studies.

**Cold-item definition:** §3.4.1 sends test items never seen in target training to
the cold-start partition. For SASRec, single-occurrence training items help form
a shared cold-token prior; this fallback is not equivalent to a text encoder.

**Concrete result check:** Table 3, Scientific cold-item nDCG@10: SASRec **0.0213**,
UniSRec **0.0441**, Recformer **0.0520**. This supports text's utility for unseen
items in that experiment. Table 2 also shows Recformer does not beat UniSRec on
Instruments Recall@10 (**0.1052** versus **0.1119**), despite its nDCG gain.

**Connection / limitation:** supports serialization and ID-free item representations,
but its gains combine substantial pretraining, sequence architecture and target
training, rather than isolating our frozen item encoder in free slots. Our
user-new assets need not be globally unseen, unlike its strict cold partition.

## [5] IDRec versus MoRec — Yuan et al.

**Read:** §§1–9 plus Appendix A.1. Particularly matched encoder replacement
(§§2–3), regular/warm comparisons (§4), encoder sizes and pretraining (§5),
frozen versus end-to-end (§6/Table 5), costs/fusion (§7/Tables 6–8), limitations
(§9), cold/new-item definitions (Appendix A.1/Table 9).

**Verified authors:** Zheng Yuan; Fajie Yuan; Yu Song; Youhua Li; Junchen Fu;
Fei Yang; Yunzhu Pan; Yongxin Ni. SIGIR 2023, pp. 2639–2649. Do not confuse
first author Zheng Yuan with co-first/corresponding author Fajie Yuan.

**Method / fairness:** compare ID lookup item embeddings against modality item
encoders under matched DSSM and SASRec backbones, losses and sampling. Text
encoders include BERT/RoBERTa and an OPT comparison; visual encoders include
ResNet/Swin. Two-stage (TS) extracts fixed features then trains a recommendation
head; TS-DNN adds learned dense adaptation; E2E trains the item encoder too.

**Data / metrics:** MIND news titles (~630k users/80k items), H&M garment images
(500k/87k), Bili cover images with comment interactions (400k/128k), after the
paper's sampling/preprocessing. Leave-one-out; full-pool ranking; HR@10 and
nDCG@10. Filters users with fewer than five interactions; not a cold-user study.

**Key result for our hypothesis:** Table 5 reports MIND SASRec HR@10 (%):
IDRec **17.71**, frozen BERT TS **13.93**, best TS-DNN column **16.66**, E2E BERT
**18.23**. Frozen semantic features are not automatically good preference
representations, even with a learned recommendation head. A newer encoder or
our popularity mixture could behave differently, but that must be measured.

**Additional qualifications:** Table 3 shows near parity or a small ID advantage
in some very warm settings. Simple ID/content fusion fails to improve the best
single source in their Table 7; this is not a theorem that blending cannot work.
Costs can be very large for E2E visual recommenders. Authors limit conclusions to
three datasets, single modalities and relatively basic fusion. Appendix A.1
defines cold as fewer than ten training interactions and new as absent from
training, with a separately collected evaluation extension for that analysis.

**Connection:** closest controlled-encoder precedent and strongest caution
against assuming frozen LM embeddings beat a classical control. Our fixed
recency prefix, popularity term and financial purchase-set task remain untested
conditions in this paper.

## Synthesis for the research question

The literature supports separating repeat/explore behavior and representing
items with text. It also shows that recommendation-specific adaptation can be
important and that ID signals can remain strong. Thus a valid question is the
incremental value of a frozen text encoder over same-information classical
controls under our fixed-prefix protocol, not whether “LLMs understand finance”
or whether text embeddings are universally superior.

Keep runtime/caching and representation preparation cost visible. For a fair
comparison, provide the same pre-cutoff asset names/fields to TF-IDF and the LM,
keep user pooling/popularity/prefix construction fixed, and use the same earlier
validation procedure for any mixture hyperparameters. Maintain all four supplied
baselines in the eventual results table.
