"""Build the editable report template as an A4 PDF with output-backed numbers.

Run with an environment containing reportlab, pypdf and pymupdf:
    python3 -B analysis/build_session1_report.py
Edit report/dmitrenko_mikhail_session1_report.md to fill personal placeholders.
The template is never overwritten; rendered text and a numeric audit are saved.
"""
import csv
import hashlib
import html
import json
import re
from pathlib import Path

from reportlab import Version as REPORTLAB_VERSION
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted,
)
from pypdf import PdfReader
import pymupdf


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'report' / 'dmitrenko_mikhail_session1_report.md'
OUTPUT = ROOT / 'dmitrenko_mikhail_session1_report.pdf'
BUILD = ROOT / 'outputs' / 'report_build'
NAVY = colors.HexColor('#18364B')
TEAL = colors.HexColor('#176B80')
PALE = colors.HexColor('#F0F5F7')
GRAY = colors.HexColor('#52616B')
WIDTH, HEIGHT = A4
MARGIN = 16 * mm
CONTENT_WIDTH = WIDTH - 2 * MARGIN


def load(path):
    return json.loads((ROOT / path).read_text())


def source_values():
    evidence = {}
    values = {}

    def put(name, value, source, fmt=None):
        rendered = format(value, fmt) if fmt else str(value)
        values[name] = rendered
        evidence[name] = {'value': value, 'rendered': rendered, 'source': source}
        return rendered

    full_path = 'outputs/baseline_full_warm/metrics.json'
    full = load(full_path)
    proto = load('outputs/baseline_full_warm/protocol.json')
    repeat_path = 'outputs/repeat_analysis/summary.json'
    repeat = load(repeat_path)
    fill_path = 'outputs/fill_experiment/metrics.json'
    fill = load(fill_path)
    mix_path = 'outputs/fill_mixture/test_june/metrics.json'
    mix = load(mix_path)
    selection_path = 'outputs/fill_mixture/selection.json'
    selection = load(selection_path)
    audit_path = 'outputs/data_audit/audit.json'
    audit = load(audit_path)
    case_path = 'outputs/demo_ndcg_nonzero/evidence.json'
    case = load(case_path)
    model_path = 'outputs/report_build/model_plan.json'
    model = load(model_path)
    version_path = 'outputs/fill_experiment/protocol.json'
    versions = load(version_path)['versions']

    assert full['protocol_hash'] == repeat['protocol_hash'] == fill['base_protocol_hash']
    assert len(proto['users']) == mix['counts']['users'] == repeat['users']
    assert selection['selected']['cbf']['lambda'] == selection['selected']['tfidf']['lambda'] == model['primary_mixture_lambda']
    assert full['methods']['latest_buy']['ndcg_at_10'] == fill['methods']['popularity_fill']['ndcg_at_10']
    assert mix['methods']['popularity_fill']['ndcg_at_10'] == full['methods']['latest_buy']['ndcg_at_10']

    base = full['methods']['latest_buy']
    for name, val, src, fmt in [
        ('full_users', base['users'], full_path, ','),
        ('nonempty_users', base['nonempty_truth_users'], full_path, ','),
        ('empty_users', base['empty_truth_users'], full_path, ','),
        ('eligible_assets', repeat['eligible_assets'], repeat_path, ','),
        ('latest_all', base['ndcg_at_10'], full_path, '.4f'),
        ('mix_tfidf_all', mix['methods']['tfidf_mixture']['ndcg_at_10'], mix_path, '.4f'),
        ('oracle_all', fill['methods']['oracle_fill']['ndcg_at_10'], fill_path, '.4f'),
        ('repeat_pairs', repeat['future_distinct_user_asset_pairs']['repeat'], repeat_path, ','),
        ('new_pairs', repeat['future_distinct_user_asset_pairs']['new'], repeat_path, ','),
        ('repeat_pair_pct', repeat['percentages']['repeat_truth_pairs'], repeat_path, '.1f'),
        ('fill_users', fill['counts']['users_with_free_slots'], fill_path, ','),
        ('active_fill_users', fill['counts']['nonempty_users_with_free_slots'], fill_path, ','),
        ('fixed_repeat_hits', fill['methods']['popularity_fill']['relevant_pairs_retrieved']['repeat'], fill_path, ','),
        ('validation_users', selection['selected']['cbf']['validation_metrics']['users'], selection_path, ','),
        ('validation_nonempty', selection['selected']['cbf']['validation_metrics']['nonempty_truth_users'], selection_path, ','),
        ('chosen_lambda', model['primary_mixture_lambda'], model_path + ' and ' + selection_path, 'g'),
        ('random_std', fill['random_30_seed_summary']['ndcg_at_10']['sample_std'], fill_path, '.6f'),
        ('random_seeds', len([k for k in fill['methods'] if k.startswith('random_seed_')]), fill_path, None),
    ]:
        put(name, val, src, fmt)
    put('cutoff', proto['cutoff'], 'outputs/baseline_full_warm/protocol.json')
    put('end_exclusive', proto['end_exclusive'], 'outputs/baseline_full_warm/protocol.json')
    put('validation_cutoff', selection['validation_cutoff'], selection_path)
    put('validation_end', selection['validation_end_exclusive'], selection_path)
    for name in ('model_id', 'model_revision', 'embedding_dimension', 'timing_repeats'):
        key = 'revision' if name == 'model_revision' else name
        put(name, model[key], model_path)
    put('starter_commit', '51337032503c56e3a28ef646a24aa016782e1bd3',
        'Unmodified downloaded course-starter snapshot; session download verification')
    tx = audit['transaction']
    for target, key in [('record_customer', 'customerID'), ('record_isin', 'ISIN'),
                        ('record_id', 'transactionID'), ('record_type', 'transactionType'),
                        ('record_date', 'timestamp'), ('record_value', 'totalValue'),
                        ('record_units', 'units'), ('record_channel', 'channel'),
                        ('record_market', 'marketID')]:
        put(target, tx['record'][key], audit_path)
    put('record_line', tx['physical_line_including_header'], audit_path)
    june = audit['cutoff_audits']['2021-06-01']
    asset = june['asset_information']['sample_asset']
    profile = june['customer_information']['sample_profile']
    limit = june['limit_prices']['sample_limit_row']
    for name, value in {
        'asset_name': asset['assetName'], 'asset_date': asset['timestamp'],
        'asset_category': asset['assetCategory'], 'asset_subcategory': asset['assetSubCategory'],
        'asset_market': asset['marketID'], 'customer_type': profile['customerType'],
        'customer_risk': profile['riskLevel'], 'customer_capacity': profile['investmentCapacity'],
        'profile_date': profile['timestamp'], 'questionnaire_date': profile['lastQuestionnaireDate'],
        'pre_close': audit['sample_latest_pre_june_close_price']['closePrice'],
        'pre_close_date': audit['sample_latest_pre_june_close_price']['timestamp'],
        'event_close': audit['sample_transaction_date_close_price']['closePrice'],
        'limit_end': limit['maxDate'], 'limit_end_price': limit['priceMaxDate'],
        'limit_return': limit['profitability'],
    }.items():
        put(name, value, audit_path)
    put('future_profiles', june['customer_information']['selected_profiles_with_questionnaire_at_or_after_cutoff'], audit_path, ',')
    put('predicted_risk', june['customer_information']['field_status_counts']['riskLevel']['estimated'], audit_path, ',')
    put('predicted_capacity', june['customer_information']['field_status_counts']['investmentCapacity']['estimated'], audit_path, ',')
    put('future_asset_rows', june['asset_information']['raw_rows_at_or_after_cutoff'], audit_path)
    for method, short in [('latest_buy', 'latest'), ('popularity', 'pop')]:
        calculation = case['calculations'][method]
        assert len(calculation['hit_ranks']) == 1 and calculation['absolute_difference'] == 0
        rank = calculation['hit_ranks'][0]
        put('case_' + short + '_rank', rank, case_path)
        put('case_' + short + '_logarg', rank + 1, case_path + ' (rank + 1)')
        put('case_' + short + '_score', calculation['ndcg'], case_path, '.4f')
    put('case_idcg', case['calculations']['latest_buy']['idcg'], case_path, 'g')
    for name, value in versions.items():
        put(('sklearn' if name == 'scikit-learn' else name.replace('-', '_')) + '_version', value, version_path)

    rows = []
    for key, label in [('popularity', 'Popularity'), ('cbf', 'CBF'), ('latest_buy', 'Latest buy'),
                       ('latest_buy_or_sell', 'Latest buy or sell')]:
        row = full['methods'][key]
        metrics = [put(f'base_{key}_all', row['ndcg_at_10'], full_path, '.4f'),
                   put(f'base_{key}_nonempty', row['ndcg_at_10_nonempty'], full_path, '.4f')]
        rows.append(f"| {label} | {row['users']:,} | {row['nonempty_truth_users']:,} | {metrics[0]} | {metrics[1]} |")
    values['baseline_rows'] = '\n'.join(rows)
    rows = []
    configs = [('Popularity fill (= Latest buy)', fill['methods']['popularity_fill'], fill_path),
               ('CBF similarity only', fill['methods']['cbf_fill'], fill_path),
               ('TF-IDF similarity only', fill['methods']['tfidf_fill'], fill_path),
               ('Popularity + CBF, lambda = 1', mix['methods']['cbf_mixture'], mix_path),
               ('Popularity + TF-IDF, lambda = 1', mix['methods']['tfidf_mixture'], mix_path)]
    for idx, (label, row, path) in enumerate(configs):
        a = put(f'fill_{idx}_all', row['ndcg_at_10'], path, '.4f')
        b = put(f'fill_{idx}_nonempty', row['ndcg_at_10_nonempty'], path, '.4f')
        n = put(f'fill_{idx}_new', row['relevant_pairs_retrieved']['new'], path)
        rows.append(f'| {label} | {a} | {b} | {n} |')
    rand = fill['random_30_seed_summary']
    a = put('random_all', rand['ndcg_at_10']['mean'], fill_path, '.4f')
    b = put('random_nonempty', rand['ndcg_at_10_nonempty']['mean'], fill_path, '.4f')
    n = put('random_new', fill['random_mean_new_hits'], fill_path, '.1f')
    rows.append(f'| Random fill (seed mean) | {a} | {b} | {n} mean |')
    oracle = fill['methods']['oracle_fill']
    a = put('oracle_all', oracle['ndcg_at_10'], fill_path, '.4f')
    b = put('oracle_nonempty', oracle['ndcg_at_10_nonempty'], fill_path, '.4f')
    n = put('oracle_new', oracle['relevant_pairs_retrieved']['new'], fill_path)
    rows.append(f'| Perfect fill (oracle; diagnostic) | {a} | {b} | {n} |')
    values['fill_rows'] = '\n'.join(rows)
    return values, evidence


def verify_reruns():
    checks = []
    for cohort in ('baseline_default', 'baseline_full_warm'):
        for file in ('predictions.csv', 'metrics.json', 'protocol.json', 'per_user.csv', 'contexts.jsonl'):
            paths = [ROOT / 'outputs' / folder / file for folder in (cohort, cohort + '_repeat')]
            digests = []
            for path in paths:
                with path.open('rb') as stream:
                    digests.append(hashlib.file_digest(stream, 'sha256').hexdigest())
            assert digests[0] == digests[1], (cohort, file)
            checks.append({'first': str(paths[0].relative_to(ROOT)),
                           'repeat': str(paths[1].relative_to(ROOT)), 'identical': True,
                           'sha256': digests[0]})
    return checks


def register_fonts():
    for name, file in [('Arial', 'Arial.ttf'), ('ArialB', 'Arial Bold.ttf'),
                       ('ArialI', 'Arial Italic.ttf'), ('ArialBI', 'Arial Bold Italic.ttf')]:
        pdfmetrics.registerFont(TTFont(name, '/System/Library/Fonts/Supplemental/' + file))
    pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='ArialB', italic='ArialI', boldItalic='ArialBI')


def inline(text):
    tokens = []
    def code(match):
        tokens.append('<font name="Courier" size="8.2">' + html.escape(match.group(1)) + '</font>')
        return f'ZZCODETOKEN{len(tokens) - 1}ZZ'
    text = re.sub(r'`([^`]+)`', code, text)
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'https?://[^\s<>]+', lambda m: url_markup(m.group()), text)
    for i, value in enumerate(tokens):
        text = text.replace(f'ZZCODETOKEN{i}ZZ', value)
    return text


def url_markup(value):
    url = value.rstrip('.,;')
    suffix = value[len(url):]
    return f'<link href="{url}" color="#176B80">{url}</link>{suffix}'


def styles():
    base = dict(fontName='Arial', fontSize=10.0, leading=12.8,
                textColor=colors.HexColor('#202B34'), spaceAfter=5.0, splitLongWords=True)
    result = {'body': ParagraphStyle('Body', **base)}
    result['title'] = ParagraphStyle('Title', fontName='ArialB', fontSize=18.4,
                                    leading=21.4, textColor=NAVY, spaceAfter=10)
    result['h2'] = ParagraphStyle('H2', fontName='ArialB', fontSize=12.5, leading=16,
                                 textColor=NAVY, spaceBefore=8, spaceAfter=7, keepWithNext=True)
    result['h3'] = ParagraphStyle('H3', fontName='ArialB', fontSize=10.4, leading=13.2,
                                 textColor=TEAL, spaceBefore=6, spaceAfter=5, keepWithNext=True)
    result['cell'] = ParagraphStyle('Cell', fontName='Arial', fontSize=8.35, leading=10.5,
                                   textColor=colors.HexColor('#202B34'), spaceAfter=0, splitLongWords=True)
    result['th'] = ParagraphStyle('TH', fontName='ArialB', fontSize=8.4, leading=10.5,
                                 textColor=colors.white, spaceAfter=0, splitLongWords=True)
    result['quote'] = ParagraphStyle('Quote', fontName='Arial', fontSize=9.7,
                                    leading=12.5, textColor=NAVY, spaceAfter=0)
    result['reference'] = ParagraphStyle('Reference', fontName='Arial', fontSize=9.15,
                                        leading=12.1, textColor=colors.HexColor('#202B34'),
                                        spaceAfter=10, splitLongWords=True)
    return result


def make_table(lines, st):
    raw = [[x.strip() for x in line.strip().strip('|').split('|')] for line in lines]
    raw = [row for row in raw if not all(re.fullmatch(r':?-+:?', cell) for cell in row)]
    n = len(raw[0])
    assert all(len(row) == n for row in raw)
    header = raw[0]
    if n == 2:
        ratios = [0.23, 0.77]
    elif n == 3:
        ratios = [0.38, 0.37, 0.25]
    elif header[0] == 'Study':
        ratios = [0.19, 0.23, 0.23, 0.35]
    elif n == 4:
        ratios = [0.49, 0.17, 0.21, 0.13]
    else:
        ratios = [0.35, 0.12, 0.13, 0.17, 0.23]
    cells = [[Paragraph(inline(cell), st['th' if idx == 0 else 'cell']) for cell in row]
             for idx, row in enumerate(raw)]
    table = Table(cells, colWidths=[CONTENT_WIDTH * r for r in ratios], repeatRows=1, hAlign='LEFT')
    commands = [('BACKGROUND', (0, 0), (-1, 0), NAVY),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 3.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, NAVY),
                ('LINEBELOW', (0, 1), (-1, -1), 0.3, colors.HexColor('#D7E0E5'))]
    for i in range(1, len(raw)):
        if i % 2:
            commands.append(('BACKGROUND', (0, i), (-1, i), PALE))
    table.setStyle(TableStyle(commands))
    return [table, Spacer(1, 7)]


def parse_markdown(text):
    st = styles()
    lines = text.splitlines()
    story = []
    i = 0
    references = False
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line == '<!-- PAGEBREAK -->':
            story.append(PageBreak())
            i += 1
            continue
        if line.startswith('```'):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i])
                i += 1
            pre = Preformatted('\n'.join(code), ParagraphStyle('Code', fontName='Courier',
                               fontSize=7.7, leading=10, spaceAfter=0))
            box = Table([[pre]], colWidths=[CONTENT_WIDTH])
            box.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), PALE),
                                     ('BOX', (0, 0), (-1, -1), .4, colors.HexColor('#CAD9E0')),
                                     ('LEFTPADDING', (0, 0), (-1, -1), 7),
                                     ('TOPPADDING', (0, 0), (-1, -1), 7),
                                     ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
            story.extend([box, Spacer(1, 6)])
            i += 1
            continue
        if line.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            story.extend(make_table(table_lines, st))
            continue
        if line.startswith('>'):
            quotes = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quotes.append(lines[i].strip()[1:].strip())
                i += 1
            p = Paragraph('<br/>'.join(inline(q) for q in quotes), st['quote'])
            box = Table([[p]], colWidths=[CONTENT_WIDTH])
            box.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), PALE),
                                     ('LINEBEFORE', (0, 0), (0, -1), 2.2, TEAL),
                                     ('LEFTPADDING', (0, 0), (-1, -1), 9),
                                     ('RIGHTPADDING', (0, 0), (-1, -1), 9),
                                     ('TOPPADDING', (0, 0), (-1, -1), 7),
                                     ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
            story.extend([box, Spacer(1, 7)])
            continue
        if line.startswith('#'):
            heading = re.match(r'^(#+)\s+(.+)$', line)
            level, title = len(heading[1]), heading[2]
            if title == 'References':
                references = True
            style = st['title' if level == 1 else 'h2' if level == 2 else 'h3']
            story.append(Paragraph(inline(title), style))
            i += 1
            continue
        paragraph = []
        while i < len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(('#', '|', '>', '```', '<!--')):
            paragraph.append(lines[i].strip())
            i += 1
        story.append(Paragraph(inline(' '.join(paragraph)), st['reference' if references else 'body']))
    return story


def page_decoration(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#D4DFE5'))
    canvas.setLineWidth(.5)
    canvas.line(MARGIN, HEIGHT - 13.6 * mm, WIDTH - MARGIN, HEIGHT - 13.6 * mm)
    canvas.setFillColor(GRAY)
    canvas.setFont('Arial', 7.8)
    canvas.drawString(MARGIN, HEIGHT - 11 * mm, 'LLM4Rec | Session 1 | Encoder')
    canvas.drawRightString(WIDTH - MARGIN, HEIGHT - 11 * mm, 'Mikhail Dmitrenko | HuggyWuggy')
    canvas.line(MARGIN, 13 * mm, WIDTH - MARGIN, 13 * mm)
    canvas.drawString(MARGIN, 9 * mm, 'References (excluded from content limit)' if doc.page >= 6 else 'Research question and minimal study plan')
    canvas.drawRightString(WIDTH - MARGIN, 9 * mm, str(doc.page))
    canvas.restoreState()


def validate_and_render(rendered, evidence, rerun_checks):
    reader = PdfReader(OUTPUT)
    texts = [p.extract_text() for p in reader.pages]
    reference_pages = [i + 1 for i, text in enumerate(texts) if re.search(r'\nReferences\s*\n', text)]
    assert reference_pages and reference_pages[0] == 6, f'References start on {reference_pages}; pages={len(texts)}'
    for page in reader.pages:
        assert abs(float(page.mediabox.width) - WIDTH) < .1
        assert abs(float(page.mediabox.height) - HEIGHT) < .1
    combined = '\n'.join(texts)
    for required in ('Mikhail Dmitrenko', 'HuggyWuggy', 'midmitrenko@edu.hse.ru', '2026-11-13',
                     'What I personally verified', 'Trusted without verification',
                     'TO COMPLETE AFTER THE TEAM MEETING', 'TO BE COMPLETED BY MIKHAIL'):
        assert required in combined, required
    assert not re.search(r'\{\{\w+\}\}', combined)
    assert '\ufffd' not in combined and '\u25a0' not in combined
    document = pymupdf.open(OUTPUT)
    text_bounds = []
    for idx, page in enumerate(document):
        spans = [span for block in page.get_text('dict')['blocks'] if 'lines' in block
                 for line in block['lines'] for span in line['spans'] if span['text'].strip()]
        overflow = [s for s in spans if s['bbox'][0] < MARGIN - 2 or s['bbox'][2] > WIDTH - MARGIN + 2]
        assert not overflow, f'Horizontal overflow on page {idx + 1}: {overflow[:2]}'
        page.get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4), alpha=False).save(BUILD / f'page_{idx + 1}.png')
        text_bounds.append({'page': idx + 1, 'text_spans': len(spans), 'horizontal_overflow': False})
    (BUILD / 'report_extracted.txt').write_text('\n\n'.join(f'PAGE {i + 1}\n{t}' for i, t in enumerate(texts)))
    # A compact contact sheet supports visual inspection without changing the PDF.
    from PIL import Image, ImageOps, ImageDraw
    thumbs = []
    for idx in range(len(texts)):
        image = Image.open(BUILD / f'page_{idx + 1}.png').convert('RGB')
        image.thumbnail((420, 595))
        thumb = Image.new('RGB', (440, 625), '#dbe2e7')
        thumb.paste(image, ((440 - image.width) // 2, 5))
        ImageDraw.Draw(thumb).text((12, 604), f'Page {idx + 1}', fill='black')
        thumbs.append(thumb)
    sheet = Image.new('RGB', (3 * 440, ((len(thumbs) + 2) // 3) * 625), 'white')
    for idx, image in enumerate(thumbs):
        sheet.paste(image, ((idx % 3) * 440, (idx // 3) * 625))
    sheet.save(BUILD / 'contact_sheet.png')
    checks = {'pdf': str(OUTPUT.relative_to(ROOT)), 'total_pages': len(texts),
              'content_pages': reference_pages[0] - 1, 'references_start_page': reference_pages[0],
              'page_size': 'A4', 'all_required_placeholders_present': True,
              'numbers': evidence, 'rerun_file_checks': rerun_checks, 'layout': text_bounds,
              'reportlab_version': REPORTLAB_VERSION,
              'pdf_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}
    (BUILD / 'validation.json').write_text(json.dumps(checks, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: checks[k] for k in ('pdf', 'total_pages', 'content_pages',
                                           'references_start_page', 'page_size',
                                           'all_required_placeholders_present', 'pdf_sha256')}, indent=2))


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    values, evidence = source_values()
    template = TEMPLATE.read_text()
    def expand(match):
        key = match[1]
        assert key in values, f'Missing report variable: {key}'
        return values[key]
    rendered = re.sub(r'\{\{(\w+)\}\}', expand, template)
    assert len(re.findall(r'\S+', rendered.split('## Abstract\n')[1].split('\n## 1.')[0])) in range(50, 151)
    (BUILD / 'report_rendered.md').write_text(rendered)
    reruns = verify_reruns()
    register_fonts()
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=18 * mm, bottomMargin=16 * mm,
                            title='Frozen Asset-Text Embeddings for Repeat-Preserving Financial Recommendation',
                            author='Mikhail Dmitrenko', subject='LLM4Rec Session 1 individual report',
                            pageCompression=1)
    doc.build(parse_markdown(rendered), onFirstPage=page_decoration, onLaterPages=page_decoration)
    validate_and_render(rendered, evidence, reruns)


if __name__ == '__main__':
    main()
