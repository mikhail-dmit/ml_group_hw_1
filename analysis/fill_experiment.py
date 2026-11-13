"""Compare free-slot fills with the Latest buy history prefix held fixed.

Run: python3 -B analysis/fill_experiment.py
All inputs follow outputs/baseline_full_warm/protocol.json. Only oracle_fill
uses future labels, solely to calculate a constrained diagnostic upper bound.
"""
import hashlib
import importlib.util
import json
import math
import platform
import random
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from time import perf_counter
import csv

import numpy as np
import scipy
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RUN = ROOT / 'outputs' / 'baseline_full_warm'
OUTPUT = ROOT / 'outputs' / 'fill_experiment'
RANDOM_SEEDS = list(range(30))
spec = importlib.util.spec_from_file_location('course_starter', ROOT / 'starter' / 'starter.py')
starter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(starter)


def text_tokens(asset):
    # Names use Unicode word unigrams (length >= 2). Metadata stays field-qualified.
    name = asset.get('assetName', '').strip()
    if name in ('Not_Available', 'nan'):
        name = ''
    return (['name=' + token for token in re.findall(r'(?u)\b\w\w+\b', name.casefold())]
            + starter.tokens(asset))


def complete(prefix, fill_order):
    used = set(prefix)
    return (prefix + [i for i in fill_order if i not in used])[:10]


def oracle_value(prefix, relevant, allowed):
    """Independent closed-form maximum for binary relevance and a frozen prefix."""
    if not relevant:
        return 0.0
    k = len(prefix)
    prefix_gain = sum(1 / math.log2(r + 2) for r, i in enumerate(prefix) if i in relevant)
    possible_hits = min(10 - k, len(relevant & set(allowed)))
    fill_gain = sum(1 / math.log2(r + 2) for r in range(k, k + possible_hits))
    ideal = sum(1 / math.log2(r + 2) for r in range(min(10, len(relevant))))
    return (prefix_gain + fill_gain) / ideal


def main():
    started = perf_counter()
    protocol = json.loads((SOURCE_RUN / 'protocol.json').read_text())
    data = ROOT / 'FAR-Trans'
    for name, digest in protocol['source_sha256'].items():
        assert hashlib.sha256((data / name).read_bytes()).hexdigest() == digest, name
    assets, profiles, history, truth, end, excluded = starter.load_data(data, protocol['cutoff'], 30)
    users = protocol['users']
    assert starter.select_users(profiles, history, 'warm', 0, None) == users
    assert not protocol['exclude_seen'] and end == protocol['end_exclusive']
    assert sorted(assets) == protocol['eligible_assets']
    saved_latest = defaultdict(list)
    for row in starter.rows(SOURCE_RUN / 'predictions.csv'):
        if row['method'] == 'latest_buy':
            saved_latest[row['user_id']].append(row['ISIN'])
    events = starter.scan_recent_events(data, protocol['cutoff'], assets)
    features = {i: starter.tokens(a) for i, a in assets.items()}
    pop = starter.popularity_scores(history, assets)
    pop_order = starter.order(pop)
    asset_ids = sorted(assets)
    asset_index = {i: j for j, i in enumerate(asset_ids)}
    vectorizer = TfidfVectorizer(analyzer=text_tokens, norm='l2', use_idf=True,
                                 smooth_idf=True, sublinear_tf=False, dtype=np.float64)
    vectors = vectorizer.fit_transform([assets[i] for i in asset_ids])

    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = defaultdict(list)
    hit_counts = defaultdict(Counter)
    counts = Counter()
    random_expected_sum = 0.0
    example = None
    with ((OUTPUT / 'predictions.csv').open('w', newline='') as prediction_stream,
          (OUTPUT / 'per_user.csv').open('w', newline='') as user_stream):
        prediction_writer = csv.writer(prediction_stream)
        prediction_writer.writerow(['method', 'user_id', 'rank', 'ISIN'])
        user_writer = csv.writer(user_stream)
        user_writer.writerow(['method', 'user_id', 'relevant_count', 'prefix_length',
                              'ndcg_at_10', 'repeat_hits', 'new_hits'])
        for u in users:
            latest = {}
            for day, i, kind in events.get(u, []):
                if kind == 'Buy':
                    latest[i] = max(day, latest.get(i, ''))
            prefix = sorted(latest, key=lambda i: (-int(latest[i].replace('-', '')), i))[:10]
            allowed = [i for i in asset_ids if i not in set(prefix)]
            free = 10 - len(prefix)
            relevant = truth[u]
            upper = oracle_value(prefix, relevant, allowed)
            rankings = {'popularity_fill': complete(prefix, pop_order)}
            assert rankings['popularity_fill'] == saved_latest[u], u
            if free:
                cbf_scores = starter.content_scores(history[u], features)
                if not any(cbf_scores.values()):
                    cbf_scores = pop
                rankings['cbf_fill'] = complete(prefix, starter.order(cbf_scores))
                indices = [asset_index[i] for i in history[u]]
                weights = np.array([history[u][i] for i in history[u]], dtype=np.float64)
                # Same count-weighted history pooling and cosine scorer as CBF.
                profile = normalize(scipy.sparse.csr_matrix(weights.reshape(1, -1)) @ vectors[indices])
                scores = (profile @ vectors.T).toarray().ravel()
                tfidf_scores = dict(zip(asset_ids, map(float, scores)))
                if not any(tfidf_scores.values()):
                    tfidf_scores = pop
                rankings['tfidf_fill'] = complete(prefix, starter.order(tfidf_scores))
            else:
                rankings['cbf_fill'] = prefix[:]
                rankings['tfidf_fill'] = prefix[:]
            oracle_order = sorted(allowed, key=lambda i: (i not in relevant, -pop[i], i))
            rankings['oracle_fill'] = prefix + oracle_order[:free]
            for seed in RANDOM_SEEDS:
                digest = hashlib.sha256(f'{seed}:{u}'.encode()).digest()
                rng = random.Random(int.from_bytes(digest, 'big'))
                rankings[f'random_seed_{seed}'] = prefix + rng.sample(allowed, free)
            counts['users'] += 1
            counts['nonempty_truth_users'] += bool(relevant)
            counts['users_with_free_slots'] += bool(free)
            counts['nonempty_users_with_free_slots'] += bool(free and relevant)
            counts['free_slots'] += free
            counts['new_truth_pairs'] += len(relevant - set(history[u]))
            counts['new_truth_pairs_for_users_with_free_slots'] += len(relevant - set(history[u])) if free else 0
            counts['oracle_new_hits'] += len(set(rankings['oracle_fill']) & (relevant - set(history[u])))
            if relevant:
                ideal = sum(1 / math.log2(r + 2) for r in range(min(10, len(relevant))))
                prefix_gain = sum(1 / math.log2(r + 2) for r, i in enumerate(prefix) if i in relevant)
                expected_fill_gain = (len(set(allowed) & relevant) / len(allowed)
                                      * sum(1 / math.log2(r + 2) for r in range(len(prefix), 10)))
                random_expected_sum += (prefix_gain + expected_fill_gain) / ideal
            for method, ranking in rankings.items():
                starter.validate_ranking(ranking, asset_ids)
                assert ranking[:len(prefix)] == prefix
                score = starter.ndcg10(ranking, relevant)
                assert score <= upper + 1e-12, (u, method)
                if method == 'oracle_fill':
                    assert math.isclose(score, upper, abs_tol=1e-12)
                repeat_hits = len(set(ranking) & relevant & set(history[u]))
                new_hits = len((set(ranking) & relevant) - set(history[u]))
                hit_counts[method]['repeat'] += repeat_hits
                hit_counts[method]['new'] += new_hits
                records[method].append({'user_id': u, 'relevant_count': len(relevant), 'ndcg_at_10': score})
                user_writer.writerow([method, u, len(relevant), len(prefix), score, repeat_hits, new_hits])
                if not method.startswith('random_seed_') or method == 'random_seed_0':
                    prediction_writer.writerows((method, u, r, i) for r, i in enumerate(ranking, 1))
            if example is None and free and (relevant & set(allowed)):
                example = {'user_id': u, 'prefix': prefix, 'truth': sorted(relevant),
                           'free_slots': free, 'oracle_ranking': rankings['oracle_fill'],
                           'oracle_ndcg': upper}

    metrics = {m: dict(starter.aggregate(rows), relevant_pairs_retrieved=dict(hit_counts[m]))
               for m, rows in records.items()}
    saved_metrics = json.loads((SOURCE_RUN / 'metrics.json').read_text())
    assert metrics['popularity_fill']['ndcg_at_10'] == saved_metrics['methods']['latest_buy']['ndcg_at_10']
    assert metrics['popularity_fill']['ndcg_at_10_nonempty'] == saved_metrics['methods']['latest_buy']['ndcg_at_10_nonempty']
    assert len({m['relevant_pairs_retrieved']['repeat'] for m in metrics.values()}) == 1
    random_summary = {}
    for key in ('ndcg_at_10', 'ndcg_at_10_nonempty'):
        values = [metrics[f'random_seed_{seed}'][key] for seed in RANDOM_SEEDS]
        random_summary[key] = {'mean': statistics.mean(values), 'sample_std': statistics.stdev(values),
                               'min': min(values), 'max': max(values),
                               'exact_uniform_expectation': random_expected_sum / (
                                   counts['users'] if key == 'ndcg_at_10' else counts['nonempty_truth_users'])}
    report = {'base_protocol_hash': protocol['protocol_hash'], 'counts': dict(counts),
              'methods': metrics, 'random_30_seed_summary': random_summary,
              'random_mean_new_hits': statistics.mean(hit_counts[f'random_seed_{s}']['new'] for s in RANDOM_SEEDS),
              'verification': {'popularity_fill_all_predictions_equal_saved_latest_buy': True,
                               'popularity_fill_metrics_exactly_equal_saved_latest_buy': True,
                               'every_prefix_unchanged': True,
                               'every_ranking_valid_and_no_better_than_oracle': True,
                               'oracle_matches_independent_closed_form_for_every_user': True,
                               'repeat_hit_count_identical_for_every_method_and_seed': True},
              'oracle_example': example, 'elapsed_seconds_whole_analysis': perf_counter() - started}
    experiment = {'base_protocol': protocol, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'fixed_prefix': 'Distinct eligible assets by descending last pre-cutoff Buy date, then ISIN; first 10',
                  'fill_universe': 'All eligible assets minus fixed prefix; no CBF Top-50 restriction',
                  'cbf': 'Unmodified starter content_scores with buy counts; popularity fallback on all-zero scores',
                  'tfidf': {'name_tokens': 'Casefolded Unicode word unigrams of length >=2; name= prefix',
                            'metadata_tokens': 'Exact starter field=value tokens for the five CBF fields',
                            'idf_corpus': 'All 767 as-of eligible assets; no future transactions',
                            'idf': 'log((1 + number_of_assets) / (1 + document_frequency)) + 1',
                            'tf': 'Raw token counts', 'normalization': 'L2 asset vectors and count-weighted L2 user profile',
                            'score': 'Cosine similarity', 'ties': 'Ascending ISIN',
                            'vocabulary_size': len(vectorizer.vocabulary_)},
                  'random': {'seeds': RANDOM_SEEDS, 'sampling': 'Uniform without replacement from sorted fill universe',
                             'per_user_rng_seed': 'Integer from SHA256(str(seed) + colon + user_id)',
                             'predictions_saved_for': 'Seed 0; all 30 seeds have per-user metrics'},
                  'oracle': 'Future-relevant fill assets first; tied relevance by popularity then ISIN. Diagnostic only.',
                  'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                               'scipy': scipy.__version__, 'scikit-learn': sklearn.__version__},
                  'excluded_rows': excluded}
    starter.json_file(OUTPUT / 'protocol.json', experiment)
    starter.json_file(OUTPUT / 'metrics.json', report)
    print('method,users,nonempty,ndcg_all,ndcg_nonempty,new_pairs_retrieved')
    for method in ('popularity_fill', 'cbf_fill', 'tfidf_fill', 'oracle_fill'):
        row = metrics[method]
        print(f"{method},{row['users']},{row['nonempty_truth_users']},{row['ndcg_at_10']:.8f},"
              f"{row['ndcg_at_10_nonempty']:.8f},{row['relevant_pairs_retrieved']['new']}")
    print('random_30_seed_summary', json.dumps(random_summary))
    print('counts', json.dumps(dict(counts)))
    print('verification', json.dumps(report['verification']))
    print('whole_analysis_seconds', report['elapsed_seconds_whole_analysis'])


if __name__ == '__main__':
    main()
