"""Independent raw-data evidence and calculator arithmetic for one demo user's nDCG.

Run: python3 -B analysis/demo_ndcg_walkthrough.py
Does not call the starter's ndcg10 or load_data functions.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'outputs' / 'baseline_default'


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        yield from csv.DictReader(stream)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user-id')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs' / 'demo_ndcg_walkthrough')
    args = parser.parse_args()
    protocol = json.loads((RUN / 'protocol.json').read_text())
    assert len(protocol['users']) == 100
    assert protocol['cutoff'] == '2021-06-01' and protocol['end_exclusive'] == '2021-07-01'
    assert not protocol['exclude_seen']
    for name, digest in protocol['source_sha256'].items():
        assert hashlib.sha256((ROOT / 'FAR-Trans' / name).read_bytes()).hexdigest() == digest
    eligible = set(protocol['eligible_assets'])
    demo_users = set(protocol['users'])
    demo_history, demo_future, raw_demo_history = defaultdict(set), defaultdict(set), defaultdict(set)
    for row in rows(ROOT / 'FAR-Trans' / 'transactions.csv'):
        if (row['customerID'] not in demo_users or row['ISIN'] not in eligible
                or row['transactionType'] != 'Buy'):
            continue
        if row['timestamp'] < protocol['cutoff']:
            raw_demo_history[row['customerID']].add(row['ISIN'])
        if int(row['transactionID']) < 0:
            continue
        if row['timestamp'] < protocol['cutoff']:
            demo_history[row['customerID']].add(row['ISIN'])
        elif row['timestamp'] < protocol['end_exclusive']:
            demo_future[row['customerID']].add(row['ISIN'])
    saved_scores = defaultdict(dict)
    for row in rows(RUN / 'per_user.csv'):
        saved_scores[row['user_id']][row['method']] = float(row['ndcg_at_10'])
    # Select an unambiguous new asset: no pre-cutoff Buy, even an initial-position row.
    candidates = [u for u in protocol['users'] if demo_future[u] - raw_demo_history[u]]
    assert candidates
    # Prefer nonzero, different scores, then multiple truth items for an informative example.
    user = args.user_id or min(candidates, key=lambda u: (
        not (saved_scores[u]['latest_buy'] > 0 and saved_scores[u]['popularity'] > 0),
        saved_scores[u]['latest_buy'] == saved_scores[u]['popularity'],
        -len(demo_future[u]), u))
    assert user in demo_users
    demo_novel_hits = {method: {'absent_from_retained_history': set(),
                                 'absent_even_from_initial_positions': set()}
                       for method in ('latest_buy', 'popularity')}
    for row in rows(RUN / 'predictions.csv'):
        u, i, method = row['user_id'], row['ISIN'], row['method']
        if method not in demo_novel_hits or i not in demo_future[u]:
            continue
        if i not in demo_history[u]:
            demo_novel_hits[method]['absent_from_retained_history'].add((u, i))
        if i not in raw_demo_history[u]:
            demo_novel_hits[method]['absent_even_from_initial_positions'].add((u, i))
    seen, history, latest, future, initial_positions = set(), Counter(), {}, [], []
    for line, row in enumerate(rows(ROOT / 'FAR-Trans' / 'transactions.csv'), start=2):
        if row['customerID'] != user:
            continue
        key = tuple(sorted(row.items()))
        if key in seen:
            continue
        seen.add(key)
        if int(row['transactionID']) < 0 and row['transactionType'] == 'Buy':
            initial_positions.append({'ISIN': row['ISIN'], 'transactionID': row['transactionID'],
                                      'timestamp': row['timestamp'], 'source_line': line})
        if (int(row['transactionID']) < 0 or row['transactionType'] != 'Buy'
                or row['ISIN'] not in eligible):
            continue
        isin, day = row['ISIN'], row['timestamp'][:10]
        if day < protocol['cutoff']:
            history[isin] += 1
            latest[isin] = max(latest.get(isin, ''), day)
        elif day < protocol['end_exclusive']:
            future.append({'transactionID': row['transactionID'], 'ISIN': isin,
                           'timestamp': day, 'source_line': line})
    truth = {r['ISIN'] for r in future}
    assert truth - set(history), 'Selected user must have a new June purchase'
    metadata = {}
    for row in rows(ROOT / 'FAR-Trans' / 'asset_information.csv'):
        if row['timestamp'] < protocol['cutoff']:
            old = metadata.get(row['ISIN'])
            if old is None or row['timestamp'] > old['timestamp']:
                metadata[row['ISIN']] = row
    for row in future:
        row.update(assetName=metadata[row['ISIN']]['assetName'],
                   repeat_or_new='repeat' if row['ISIN'] in history else 'new',
                   retained_pre_cutoff_buy_count=history[row['ISIN']],
                   last_pre_cutoff_buy=latest.get(row['ISIN']))
    predictions = {'latest_buy': [], 'popularity': []}
    for line, row in enumerate(rows(RUN / 'predictions.csv'), start=2):
        if row['user_id'] == user and row['method'] in predictions:
            predictions[row['method']].append(dict(row, source_line=line,
                                                   relevant=row['ISIN'] in truth))
    per_user = {}
    for line, row in enumerate(rows(RUN / 'per_user.csv'), start=2):
        if row['user_id'] == user and row['method'] in predictions:
            per_user[row['method']] = dict(row, source_line=line)
    # Explicit calculator terms for this example, independently of starter.ndcg10.
    idcg_terms = [1 / math.log2(r + 1) for r in range(1, min(10, len(truth)) + 1)]
    idcg = sum(idcg_terms)
    calculations = {}
    for method, ranking in predictions.items():
        assert [int(r['rank']) for r in ranking] == list(range(1, 11))
        hit_ranks = [int(r['rank']) for r in ranking if r['relevant']]
        terms = [1 / math.log2(r + 1) for r in hit_ranks]
        dcg = sum(terms)
        score = dcg / idcg
        saved = float(per_user[method]['ndcg_at_10'])
        assert int(per_user[method]['relevant_count']) == len(truth)
        assert math.isclose(score, saved, abs_tol=1e-15)
        calculations[method] = {'hit_ranks': hit_ranks, 'dcg_terms': terms,
                                'dcg': dcg, 'idcg': idcg, 'ndcg': score,
                                'saved_ndcg': saved, 'absolute_difference': abs(score - saved),
                                'per_user_csv_row': per_user[method]}
    prefix = sorted(latest, key=lambda i: (-int(latest[i].replace('-', '')), i))[:10]
    popularity_order = [r['ISIN'] for r in predictions['popularity']]
    # Popularity's global top ten suffice to fill any shorter prefix.
    reconstructed = (prefix + [i for i in popularity_order if i not in set(prefix)])[:10]
    assert reconstructed == [r['ISIN'] for r in predictions['latest_buy']]
    report = {'user_id': user, 'demo_position_one_based': protocol['users'].index(user) + 1,
              'protocol_hash': protocol['protocol_hash'], 'distinct_history_assets': len(history),
              'new_truth_assets': len(truth - set(history)),
              'new_truth_assets_even_including_initial_positions': len(truth - raw_demo_history[user]),
              'repeat_truth_assets': len(truth & set(history)),
              'future_buy_rows': sorted(future, key=lambda r: (r['timestamp'], r['ISIN'])),
              'truth': sorted(truth), 'idcg_terms': idcg_terms,
              'excluded_initial_positions_for_truth_assets': [r for r in initial_positions if r['ISIN'] in truth],
              'history_prefix': [{'ISIN': i, 'last_buy': latest[i], 'buy_count': history[i]} for i in prefix],
              'predictions': predictions, 'calculations': calculations,
              'all_demo_new_hit_pair_counts': {m: {k: len(v) for k, v in counts.items()}
                                               for m, counts in demo_novel_hits.items()},
              'verification': {'at_least_one_future_asset_has_no_retained_pre_cutoff_buys': True,
                               'at_least_one_future_asset_absent_even_from_initial_positions': bool(truth - raw_demo_history[user]),
                               'latest_buy_top10_reconstructed_from_history_and_popularity': True,
                               'independent_calculations_match_saved_per_user': True}}
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    (output / 'evidence.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: report[k] for k in (
        'user_id', 'demo_position_one_based', 'distinct_history_assets',
        'new_truth_assets', 'new_truth_assets_even_including_initial_positions',
        'future_buy_rows', 'truth', 'idcg_terms', 'calculations',
        'all_demo_new_hit_pair_counts', 'verification')},
        indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
