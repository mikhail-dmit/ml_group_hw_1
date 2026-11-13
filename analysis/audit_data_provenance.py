"""Audit raw field provenance at the May and June cutoffs; export a pseudonymized record.

Run: python3 -B analysis/audit_data_provenance.py
No raw customer identifier is written to the output.
"""
import hashlib
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'FAR-Trans'
spec = importlib.util.spec_from_file_location('course_starter', ROOT / 'starter' / 'starter.py')
starter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(starter)
MISSING = ('', 'Not_Available', 'nan')


def status(value):
    if value in MISSING:
        return 'missing'
    return 'estimated' if value.startswith('Predicted_') else 'observed'


def redact(row):
    return dict(row, customerID='U001') if 'customerID' in row else dict(row)


def main():
    customer_rows = list(starter.rows(DATA / 'customer_information.csv'))
    asset_rows = list(starter.rows(DATA / 'asset_information.csv'))
    limit_rows = list(starter.rows(DATA / 'limit_prices.csv'))
    chosen = []
    for line, row in enumerate(starter.rows(DATA / 'transactions.csv'), start=2):
        if (row['transactionID'] == '7438853' and row['ISIN'] == 'GRS003003035'
                and row['timestamp'] == '2020-01-14' and row['transactionType'] == 'Buy'):
            chosen.append((line, row))
    assert len(chosen) == 1
    line, transaction = chosen[0]
    customer = transaction['customerID']
    isin = transaction['ISIN']
    audits = {}
    for cutoff in ('2021-05-01', '2021-06-01'):
        assets, profiles, history, truth, end, excluded = starter.load_data(DATA, cutoff, 30)
        users = starter.select_users(profiles, history, 'warm', 0, None)
        assert customer in users and isin in assets and int(transaction['transactionID']) >= 0
        assert transaction['timestamp'] < cutoff and history[customer][isin] >= 1
        selected_profiles = [profiles[u] for u in users]
        future_questionnaires = [r for r in selected_profiles
                                 if r['lastQuestionnaireDate'] not in MISSING
                                 and r['lastQuestionnaireDate'][:10] >= cutoff]
        chronological_inconsistencies = [r for r in selected_profiles
                                        if r['lastQuestionnaireDate'] not in MISSING
                                        and r['lastQuestionnaireDate'][:10] != '2000-01-01'
                                        and r['lastQuestionnaireDate'][:10] > r['timestamp'][:10]]
        # Keep evidence of an inconsistent row without exposing a second customer ID.
        anomaly = None
        if future_questionnaires:
            anomaly = {k: v for k, v in future_questionnaires[0].items() if k != 'customerID'}
            anomaly['customerID'] = 'U002'
        linked_limit = [r for r in limit_rows if r['ISIN'] == isin]
        assert len(linked_limit) == 1
        selected_asset_rows = list(assets.values())
        audits[cutoff] = {
            'users': len(users), 'nonempty_truth_users': sum(bool(truth[u]) for u in users),
            'end_exclusive': end,
            'customer_information': {
                'raw_rows': len(customer_rows),
                'raw_rows_at_or_after_cutoff': sum(r['timestamp'][:10] >= cutoff for r in customer_rows),
                'selected_profiles': len(selected_profiles),
                'selected_profile_timestamp_range': [min(r['timestamp'][:10] for r in selected_profiles),
                                                     max(r['timestamp'][:10] for r in selected_profiles)],
                'selected_profiles_with_placeholder_timestamp': sum(r['timestamp'][:10] == '2000-01-01' for r in selected_profiles),
                'selected_profiles_with_placeholder_questionnaire_date': sum(r['lastQuestionnaireDate'][:10] == '2000-01-01' for r in selected_profiles),
                'selected_profiles_with_questionnaire_at_or_after_cutoff': len(future_questionnaires),
                'selected_profiles_with_questionnaire_after_row_timestamp': len(chronological_inconsistencies),
                'field_status_counts': {f: dict(Counter(status(r[f]) for r in selected_profiles))
                                        for f in ('customerType', 'riskLevel', 'investmentCapacity')},
                'sample_profile': redact(profiles[customer]),
                'future_questionnaire_example': anomaly},
            'asset_information': {
                'raw_rows': len(asset_rows),
                'raw_unique_assets': len({r['ISIN'] for r in asset_rows}),
                'raw_rows_at_or_after_cutoff': sum(r['timestamp'][:10] >= cutoff for r in asset_rows),
                'eligible_asof_assets': len(assets),
                'selected_metadata_timestamp_range': [min(r['timestamp'][:10] for r in selected_asset_rows),
                                                       max(r['timestamp'][:10] for r in selected_asset_rows)],
                'selected_rows_at_or_after_cutoff': sum(r['timestamp'][:10] >= cutoff for r in selected_asset_rows),
                'missing_fields_in_eligible_assets': {f: sum(status(r[f]) == 'missing' for r in selected_asset_rows)
                                                     for f in ('assetName', 'assetCategory', 'assetSubCategory',
                                                               'marketID', 'sector', 'industry')},
                'sample_asset': assets[isin]},
            'limit_prices': {
                'raw_rows': len(limit_rows),
                'rows_with_maxDate_at_or_after_cutoff': sum(r['maxDate'][:10] >= cutoff for r in limit_rows),
                'eligible_assets_with_future_endpoint': sum(r['ISIN'] in assets and r['maxDate'][:10] >= cutoff for r in limit_rows),
                'sample_limit_row': linked_limit[0],
                'used_by_current_scorers_or_eligibility': False},
            'excluded_rows': excluded}
    june_protocol = json.loads((ROOT / 'outputs' / 'baseline_full_warm' / 'protocol.json').read_text())
    for name, digest in june_protocol['source_sha256'].items():
        assert hashlib.sha256((DATA / name).read_bytes()).hexdigest() == digest
    limit = audits['2021-06-01']['limit_prices']['sample_limit_row']
    assert math.isclose(float(limit['priceMaxDate']) / float(limit['priceMinDate']) - 1,
                        float(limit['profitability']), rel_tol=1e-12)
    endpoint_matches = {'first': False, 'last': False}
    latest_pre_cutoff_price = None
    transaction_date_price = None
    for row in starter.rows(DATA / 'close_prices.csv'):
        if row['ISIN'] != isin:
            continue
        if row['timestamp'] == limit['minDate']:
            endpoint_matches['first'] = math.isclose(float(row['closePrice']), float(limit['priceMinDate']))
        if row['timestamp'] == limit['maxDate']:
            endpoint_matches['last'] = math.isclose(float(row['closePrice']), float(limit['priceMaxDate']))
        if row['timestamp'] == transaction['timestamp']:
            transaction_date_price = row
        if row['timestamp'] < '2021-06-01' and (latest_pre_cutoff_price is None or row['timestamp'] > latest_pre_cutoff_price['timestamp']):
            latest_pre_cutoff_price = row
    assert all(endpoint_matches.values())
    assert transaction_date_price is not None
    assert math.isclose(float(transaction['units']) * float(transaction_date_price['closePrice']),
                        float(transaction['totalValue']), rel_tol=1e-12)
    field_statuses = {f: status(v) for f, v in transaction.items()}
    # FAR-Trans paper, section 3.3.1: released monetary values are estimates
    # computed from the share count and the asset's closing price on that date.
    field_statuses['totalValue'] = 'estimated'
    report = {
        'source': 'https://researchdata.gla.ac.uk/1658/1/FAR-Trans.zip',
        'source_doi': '10.5525/gla.researchdata.1658',
        'transaction': {'file': 'transactions.csv', 'physical_line_including_header': line,
                        'record_id': transaction['transactionID'], 'record': redact(transaction),
                        'field_statuses': field_statuses,
                        'field_provenance_notes': {
                            'totalValue': 'Estimated/derived using units times closing price; FAR-Trans section 3.3.1',
                            'units': 'Released share counts can be adjusted for stock splits; not guaranteed original raw units',
                            'timestamp': 'Released transaction dates can be clipped to available price-series dates; original dates are not separately supplied'},
                        'event_timestamp': transaction['timestamp'], 'window': 'History before 2021-06-01',
                        'redaction': 'Only customerID replaced with U001; all other field values are verbatim'},
        'cutoff_audits': audits,
        'sample_latest_pre_june_close_price': latest_pre_cutoff_price,
        'sample_transaction_date_close_price': transaction_date_price,
        'verification': {'source_hashes_match_saved_june_protocol': True,
                         'sample_is_retained_history_for_both_cutoffs': True,
                         'limit_price_endpoints_match_close_prices': endpoint_matches,
                         'sample_totalValue_matches_units_times_released_close_price': True,
                         'limit_profitability_matches_realized_endpoint_return': True},
        'source_sha256': {name: hashlib.sha256((DATA / name).read_bytes()).hexdigest()
                          for name in ('transactions.csv', 'customer_information.csv',
                                       'asset_information.csv', 'limit_prices.csv', 'README.txt')}}
    output = ROOT / 'outputs' / 'data_audit'
    output.mkdir(parents=True, exist_ok=True)
    starter.json_file(output / 'audit.json', report)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
