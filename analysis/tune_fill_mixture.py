"""Tune popularity/similarity mixtures on May, then evaluate frozen choices on June.

python3 -B analysis/tune_fill_mixture.py tune
python3 -B analysis/tune_fill_mixture.py evaluate

Only free slots change. The June stage never evaluates a lambda grid.
"""
import argparse
import csv
import hashlib
import json
import math
import platform
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import scipy
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from fill_experiment import ROOT, starter, text_tokens


OUTPUT = ROOT / 'outputs' / 'fill_mixture'
GRID = [0.0, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]
BASELINE = ROOT / 'outputs' / 'baseline_full_warm'
SOURCES = ('transactions.csv', 'asset_information.csv', 'customer_information.csv', 'close_prices.csv')


def hashes():
    return {name: hashlib.sha256((ROOT / 'FAR-Trans' / name).read_bytes()).hexdigest()
            for name in SOURCES}


def code_hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__).resolve(), ROOT / 'analysis' / 'fill_experiment.py',
                      ROOT / 'starter' / 'starter.py')}


def mix_fill(prefix, asset_ids, pop_normalized, similarity, weight):
    scores = pop_normalized + weight * similarity
    # asset_ids are sorted, so stable sorting breaks exact score ties by ISIN.
    order = np.argsort(-scores, kind='stable')
    used = set(prefix)
    fill = [asset_ids[j] for j in order if asset_ids[j] not in used][:10 - len(prefix)]
    return prefix + fill


def run(cutoff, choices, destination, source_hashes, save_predictions):
    assets, profiles, history, truth, end, excluded = starter.load_data(ROOT / 'FAR-Trans', cutoff, 30)
    users = starter.select_users(profiles, history, 'warm', 0, None)
    asset_ids = sorted(assets)
    index = {i: j for j, i in enumerate(asset_ids)}
    pop = starter.popularity_scores(history, assets)
    max_pop = max(pop.values())
    assert max_pop > 0
    pop_normalized = np.array([pop[i] / max_pop for i in asset_ids], dtype=np.float64)
    features = {i: starter.tokens(assets[i]) for i in asset_ids}
    vectorizer = TfidfVectorizer(analyzer=text_tokens, norm='l2', use_idf=True,
                                 smooth_idf=True, sublinear_tf=False, dtype=np.float64)
    vectors = vectorizer.fit_transform([assets[i] for i in asset_ids])
    events = starter.scan_recent_events(ROOT / 'FAR-Trans', cutoff, assets)
    original = {}
    original_metrics = None
    if save_predictions:
        saved_protocol = json.loads((BASELINE / 'protocol.json').read_text())
        assert saved_protocol['cutoff'] == cutoff and saved_protocol['end_exclusive'] == end
        assert users == saved_protocol['users'] and asset_ids == saved_protocol['eligible_assets']
        assert source_hashes == saved_protocol['source_sha256']
        original_metrics = json.loads((BASELINE / 'metrics.json').read_text())
        for row in starter.rows(BASELINE / 'predictions.csv'):
            if row['method'] == 'latest_buy':
                original.setdefault(row['user_id'], []).append(row['ISIN'])

    destination.mkdir(parents=True, exist_ok=False)
    protocol = {
        'cutoff': cutoff, 'end_exclusive': end, 'horizon_days': 30,
        'users': users, 'cohort_selection': 'warm', 'max_users': 0,
        'eligible_assets': asset_ids, 'exclude_seen': False, 'source_sha256': source_hashes,
        'fixed_prefix': 'Latest pre-cutoff Buy date per asset; descending date, ascending ISIN; first 10',
        'fill_universe': 'All eligible assets except fixed prefix',
        'formula': 'distinct_historical_buyers / maximum_buyers_across_eligible_assets + lambda * cosine_similarity',
        'maximum_popularity': max_pop, 'choices': choices,
        'ties': 'Ascending ISIN', 'empty_truth': 'Zero in all-user mean; nonempty mean also reported',
        'similarity': 'Unchanged starter CBF; TF-IDF settings identical to analysis/fill_experiment.py',
        'tfidf_vocabulary_size': len(vectorizer.vocabulary_), 'excluded_rows': excluded,
        'code_sha256': code_hashes(),
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                     'scipy': scipy.__version__, 'scikit-learn': sklearn.__version__}}
    starter.json_file(destination / 'protocol.json', protocol)
    records = defaultdict(list)
    hits = defaultdict(Counter)
    counts = Counter()
    with ((destination / 'per_user.csv').open('w', newline='') as user_stream,
          (destination / 'predictions.csv').open('w', newline='') as prediction_stream):
        user_writer = csv.writer(user_stream)
        user_writer.writerow(['method', 'user_id', 'relevant_count', 'prefix_length',
                              'ndcg_at_10', 'repeat_hits', 'new_hits'])
        prediction_writer = csv.writer(prediction_stream)
        prediction_writer.writerow(['method', 'user_id', 'rank', 'ISIN'])
        for u in users:
            latest = {}
            for day, i, kind in events.get(u, []):
                if kind == 'Buy':
                    latest[i] = max(day, latest.get(i, ''))
            prefix = sorted(latest, key=lambda i: (-date.fromisoformat(latest[i]).toordinal(), i))[:10]
            counts['users'] += 1
            counts['nonempty_truth_users'] += bool(truth[u])
            counts['users_with_free_slots'] += len(prefix) < 10
            similarities = {}
            if len(prefix) < 10:
                cbf = starter.content_scores(history[u], features)
                similarities['cbf'] = np.array([cbf[i] for i in asset_ids])
                indices = [index[i] for i in history[u]]
                weights = np.array([history[u][i] for i in history[u]], dtype=np.float64)
                profile = normalize(scipy.sparse.csr_matrix(weights.reshape(1, -1)) @ vectors[indices])
                similarities['tfidf'] = (profile @ vectors.T).toarray().ravel()
                for values in similarities.values():
                    assert np.all(np.isfinite(values)) and np.all(values >= -1e-12) and np.all(values <= 1 + 1e-12)
            baseline = mix_fill(prefix, asset_ids, pop_normalized, np.zeros(len(asset_ids)), 0.0)
            if original:
                assert baseline == original[u], u
            rankings = {'popularity_fill': baseline}
            for method, config in choices.items():
                rankings[method] = (mix_fill(prefix, asset_ids, pop_normalized,
                                             similarities[config['similarity']], config['lambda'])
                                    if len(prefix) < 10 else prefix[:])
                if config['lambda'] == 0:
                    assert rankings[method] == baseline
            expected_repeat_hits = len(set(prefix) & truth[u])
            for method, ranking in rankings.items():
                starter.validate_ranking(ranking, asset_ids)
                assert ranking[:len(prefix)] == prefix
                repeat_hits = len(set(ranking) & truth[u] & set(history[u]))
                assert repeat_hits == expected_repeat_hits
                new_hits = len((set(ranking) & truth[u]) - set(history[u]))
                score = starter.ndcg10(ranking, truth[u])
                records[method].append({'relevant_count': len(truth[u]), 'ndcg_at_10': score})
                hits[method]['repeat'] += repeat_hits
                hits[method]['new'] += new_hits
                user_writer.writerow([method, u, len(truth[u]), len(prefix), score, repeat_hits, new_hits])
                if save_predictions:
                    prediction_writer.writerows((method, u, r, i) for r, i in enumerate(ranking, 1))
    metrics = {m: dict(starter.aggregate(rows), relevant_pairs_retrieved=dict(hits[m]))
               for m, rows in records.items()}
    if original_metrics:
        for key in ('ndcg_at_10', 'ndcg_at_10_nonempty'):
            assert metrics['popularity_fill'][key] == original_metrics['methods']['latest_buy'][key]
    report = {'counts': dict(counts), 'methods': metrics,
              'verification': {'all_prefixes_frozen': True, 'all_rankings_valid': True,
                               'all_repeat_hits_unchanged': True,
                               'popularity_reproduces_saved_june_latest_buy': bool(original)}}
    starter.json_file(destination / 'metrics.json', report)
    return report, protocol


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('tune', 'evaluate'))
    args = parser.parse_args()
    source_hashes = hashes()
    if args.command == 'tune':
        choices = {f'{kind}_lambda_{weight:g}': {'similarity': kind, 'lambda': weight}
                   for kind in ('cbf', 'tfidf') for weight in GRID}
        report, protocol = run('2021-05-01', choices, OUTPUT / 'validation_may', source_hashes, False)
        selected = {}
        for kind in ('cbf', 'tfidf'):
            names = [m for m, c in choices.items() if c['similarity'] == kind]
            best = min(names, key=lambda m: (-report['methods'][m]['ndcg_at_10'], choices[m]['lambda']))
            selected[kind] = {'lambda': choices[best]['lambda'], 'validation_method': best,
                              'validation_metrics': report['methods'][best]}
        selection = {'validation_cutoff': protocol['cutoff'], 'validation_end_exclusive': protocol['end_exclusive'],
                     'test_cutoff': '2021-06-01', 'grid': GRID, 'selected': selected,
                     'selection_metric': 'All-user mean nDCG@10', 'ties': 'Smallest lambda',
                     'normalization': 'Popularity divided by maximum over all as-of eligible assets',
                     'source_sha256': source_hashes, 'code_sha256': code_hashes(),
                     'validation_metrics_sha256': hashlib.sha256((OUTPUT / 'validation_may' / 'metrics.json').read_bytes()).hexdigest()}
        starter.json_file(OUTPUT / 'selection.json', selection)
        print('May validation: method,lambda,ndcg_all,ndcg_nonempty')
        for method, config in choices.items():
            row = report['methods'][method]
            print(f"{config['similarity']},{config['lambda']:g},{row['ndcg_at_10']:.8f},{row['ndcg_at_10_nonempty']:.8f}")
        print('counts', json.dumps(report['counts']))
        print('FROZEN_SELECTION', json.dumps(selected))
    else:
        selection_path = OUTPUT / 'selection.json'
        selection = json.loads(selection_path.read_text())
        assert selection['source_sha256'] == source_hashes and selection['code_sha256'] == code_hashes()
        assert selection['validation_end_exclusive'] <= selection['test_cutoff']
        assert selection['validation_metrics_sha256'] == hashlib.sha256((OUTPUT / 'validation_may' / 'metrics.json').read_bytes()).hexdigest()
        choices = {f'{kind}_mixture': {'similarity': kind, 'lambda': config['lambda']}
                   for kind, config in selection['selected'].items()}
        report, protocol = run(selection['test_cutoff'], choices, OUTPUT / 'test_june', source_hashes, True)
        protocol['selection_file_sha256'] = hashlib.sha256(selection_path.read_bytes()).hexdigest()
        starter.json_file(OUTPUT / 'test_june' / 'protocol.json', protocol)
        print('June test: method,ndcg_all,ndcg_nonempty,new_pairs_retrieved')
        for method, row in report['methods'].items():
            print(f"{method},{row['ndcg_at_10']:.8f},{row['ndcg_at_10_nonempty']:.8f},{row['relevant_pairs_retrieved']['new']}")
        print('counts', json.dumps(report['counts']))
        print('verification', json.dumps(report['verification']))


if __name__ == '__main__':
    main()
