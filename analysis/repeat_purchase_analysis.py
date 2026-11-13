"""Audit repeat purchases and encoder headroom under the saved full-warm protocol.

Run from any directory: python3 -B analysis/repeat_purchase_analysis.py
Repeat means bought before the prediction cutoff, not earlier in the label window.
Uses the starter's retained-row and eligible-asset rules without modifying it.
"""
import csv
import hashlib
import importlib.util
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'outputs' / 'baseline_full_warm'
spec = importlib.util.spec_from_file_location('course_starter', ROOT / 'starter' / 'starter.py')
starter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(starter)


def main():
    protocol = json.loads((RUN / 'protocol.json').read_text())
    data = ROOT / 'FAR-Trans'
    for name, expected in protocol['source_sha256'].items():
        assert hashlib.sha256((data / name).read_bytes()).hexdigest() == expected, name
    assets, profiles, history, truth, end, excluded = starter.load_data(
        data, protocol['cutoff'], 30)
    users = protocol['users']
    selected = set(users)
    assert users == starter.select_users(profiles, history, 'warm', 0, None)
    assert end == protocol['end_exclusive'] and not protocol['exclude_seen']
    assert set(assets) == set(protocol['eligible_assets'])
    predictions = defaultdict(dict)
    for row in starter.rows(RUN / 'predictions.csv'):
        predictions[row['user_id']].setdefault(row['method'], []).append(row['ISIN'])

    repeats = {u: truth[u] & set(history[u]) for u in users}
    new = {u: truth[u] - set(history[u]) for u in users}
    user_group = {u: ('mixed' if repeats[u] and new[u] else 'repeat_only' if repeats[u]
                     else 'new_only' if new[u] else 'empty') for u in users}
    last_buy = defaultdict(dict)
    transactions = Counter()
    seen = set()
    for row in starter.rows(data / 'transactions.csv'):
        key = tuple(sorted(row.items()))
        if key in seen:
            continue
        seen.add(key)
        u, isin, day = row['customerID'], row['ISIN'], row['timestamp'][:10]
        if (int(row['transactionID']) < 0 or row['transactionType'] != 'Buy'
                or u not in selected or isin not in assets):
            continue
        if day < protocol['cutoff']:
            last_buy[u][isin] = max(last_buy[u].get(isin, ''), day)
        elif day < end:
            transactions['repeat' if isin in history[u] else 'new'] += 1

    features = {i: tuple(starter.tokens(a)) for i, a in assets.items()}
    feature_groups = defaultdict(list)
    for i, f in features.items():
        feature_groups[f].append(i)
    pop = starter.popularity_scores(history, assets)
    pop_order = starter.order(pop)
    composition = Counter()
    method_stats = {}
    buckets = defaultdict(list)
    examples = []
    for u in users:
        n = len(history[u])
        bucket = '1' if n == 1 else '2-5' if n <= 5 else '6-10' if n <= 10 else '11+'
        buckets[bucket].append(u)
        prefix = sorted(last_buy[u], key=lambda i: (-int(last_buy[u][i].replace('-', '')), i))[:10]
        expected = (prefix + [i for i in pop_order if i not in set(prefix)])[:10]
        assert expected == predictions[u]['latest_buy'], u
        composition['history_slots'] += len(prefix)
        composition['popularity_fill_slots'] += 10 - len(prefix)
        composition['users_needing_fill'] += n < 10
        composition['users_with_one_history_asset'] += n == 1
        composition['users_with_one_feature_type'] += len({features[i] for i in history[u]}) == 1
        if truth[u]:
            composition['active_history_slots'] += len(prefix)
            composition['active_popularity_fill_slots'] += 10 - len(prefix)
            composition['active_users_needing_fill'] += n < 10
            composition['active_users_with_one_history_asset'] += n == 1
            composition['active_users_with_one_feature_type'] += len({features[i] for i in history[u]}) == 1
        if user_group[u] == 'mixed' and 2 <= n <= 5 and len(examples) < 1:
            examples.append({'user_id': u,
                             'past_assets_by_recency': [{'id': i, 'name': assets[i]['assetName'],
                                                        'last_buy': last_buy[u][i],
                                                        'buy_count': history[u][i]} for i in prefix],
                             'latest_buy_top10': expected,
                             'repeat_truth': sorted(repeats[u]), 'new_truth': sorted(new[u])})

    for method in predictions[users[0]]:
        stats = Counter()
        group_scores = defaultdict(list)
        for u in users:
            ranking = predictions[u][method]
            score = starter.ndcg10(ranking, truth[u])
            group_scores[user_group[u]].append(score)
            stats['repeat_hits'] += len(set(ranking) & repeats[u])
            stats['new_hits'] += len(set(ranking) & new[u])
            if truth[u]:
                ideal = sum(1 / math.log2(r + 2) for r in range(min(10, len(truth[u]))))
                for rank, i in enumerate(ranking):
                    if i in truth[u]:
                        kind = 'repeat' if i in repeats[u] else 'new'
                        stats[kind + '_ndcg_sum'] += 1 / math.log2(rank + 2) / ideal
        method_stats[method] = dict(stats, group_mean_ndcg={
            g: sum(v) / len(v) for g, v in group_scores.items()})
    saved_metrics = json.loads((RUN / 'metrics.json').read_text())
    for method, stats in method_stats.items():
        reconstructed = (stats['repeat_ndcg_sum'] + stats['new_ndcg_sum']) / len(users)
        assert math.isclose(reconstructed, saved_metrics['methods'][method]['ndcg_at_10'],
                            rel_tol=1e-12)

    candidate_hits = Counter()
    for context in starter.rows(RUN / 'per_user.csv'):
        assert int(context['relevant_count']) == len(truth[context['user_id']])
    with (RUN / 'contexts.jsonl').open() as stream:
        for line in stream:
            context = json.loads(line)
            u = context['user_id']
            candidates = {a['id'] for a in context['candidate_assets']}
            candidate_hits['repeat_in_cbf_top50'] += len(candidates & repeats[u])
            candidate_hits['new_in_cbf_top50'] += len(candidates & new[u])

    bucket_stats = {}
    for bucket, cohort in buckets.items():
        active = [u for u in cohort if truth[u]]
        bucket_stats[bucket] = {
            'users': len(cohort), 'active_users': len(active),
            'repeat_truth_pairs': sum(len(repeats[u]) for u in cohort),
            'new_truth_pairs': sum(len(new[u]) for u in cohort),
            'nonempty_mean_ndcg': {m: sum(starter.ndcg10(predictions[u][m], truth[u])
                                        for u in active) / len(active) if active else None
                                   for m in method_stats}}

    report = {
        'protocol_hash': protocol['protocol_hash'], 'cutoff': protocol['cutoff'],
        'end_exclusive': end, 'users': len(users), 'eligible_assets': len(assets),
        'repeat_definition': 'Retained eligible Buy before cutoff; not within-window repetition',
        'future_buy_transaction_rows': dict(transactions),
        'future_distinct_user_asset_pairs': {
            'repeat': sum(map(len, repeats.values())), 'new': sum(map(len, new.values()))},
        'percentages': {
            'repeat_transactions': 100 * transactions['repeat'] / sum(transactions.values()),
            'repeat_truth_pairs': 100 * sum(map(len, repeats.values())) / sum(len(truth[u]) for u in users),
            'latest_buy_repeat_recall': 100 * method_stats['latest_buy']['repeat_hits'] / sum(map(len, repeats.values())),
            'latest_buy_new_recall': 100 * method_stats['latest_buy']['new_hits'] / sum(map(len, new.values())),
            'latest_buy_ndcg_credit_from_repeats': 100 * method_stats['latest_buy']['repeat_ndcg_sum'] / (
                method_stats['latest_buy']['repeat_ndcg_sum'] + method_stats['latest_buy']['new_ndcg_sum']),
            'cbf_top50_repeat_coverage': 100 * candidate_hits['repeat_in_cbf_top50'] / sum(map(len, repeats.values())),
            'cbf_top50_new_coverage': 100 * candidate_hits['new_in_cbf_top50'] / sum(map(len, new.values()))},
        'user_groups': dict(Counter(user_group.values())),
        'latest_buy_composition': dict(composition),
        'history_size_buckets': bucket_stats, 'methods': method_stats,
        'cbf_candidate_coverage': dict(candidate_hits),
        'feature_resolution': {
            'distinct_feature_vectors': len(feature_groups),
            'assets_in_nonunique_feature_groups': sum(len(v) for v in feature_groups.values() if len(v) > 1),
            'largest_group_size': max(map(len, feature_groups.values())),
            'largest_groups': [{'assets': len(v), 'features': list(f)}
                               for f, v in sorted(feature_groups.items(), key=lambda p: -len(p[1]))[:5]]},
        'example': examples,
        'verification': {'source_hashes_match_saved_protocol': True,
                         'all_latest_buy_lists_independently_reconstructed': True,
                         'all_saved_relevant_counts_match_reconstructed_truth': True,
                         'repeat_plus_new_ndcg_contributions_match_saved_metrics': True},
        'excluded_rows': excluded}
    output = ROOT / 'outputs' / 'repeat_analysis'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'summary.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
