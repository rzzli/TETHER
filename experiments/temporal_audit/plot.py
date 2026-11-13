"""Plot the released descriptive audit from replay CSVs, without source-row access.

Usage:
    python experiments/temporal_audit/plot.py --input replay-output --output figures

Requires optional matplotlib (qualified with 3.6.2); installs nothing. The output
directory must be new. CSV counts are checked before plotting. These figures are
descriptive product/selection accounting, not clinical prediction or effect tests.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import io
import json
import math
import os
from pathlib import Path


ARCHIVE_COLUMNS = (
    'source', 'archive', 'cutoff', 'field', 'archive_pairs', 'modern_pairs',
    'shared', 'archive_only', 'modern_only', 'union', 'jaccard',
)
ARCHIVE_EXTRA_COLUMNS = (
    'archive_retention', 'selected_modern_unmatched', 'archive_rows', 'modern_rows',
    'at_or_after', 'crossing', 'empty', 'entirely_before', 'malformed',
    'missing_column', 'null', 'unsupported',
)
FLOW_IDS = (
    'sizing', 'development', 'reserve', 'selected_trails', 'withheld_trails',
    'linked_trails', 'requested_ids', 'row_trial_links',
)
SOURCES = (
    ('gene_burden', 'Gene burden'),
    ('uniprot_literature', 'UniProt literature'),
    ('expression_atlas', 'Expression Atlas'),
)
CLOCKS = {'22.11': '2022-11-25', '24.09': '2024-09-19'}
COLORS = {'22.11': '#2166AC', '24.09': '#B35806'}


def _rows(payload: bytes, columns: tuple[str, ...], name: str,
          extra_columns: tuple[str, ...] = ()) -> list[dict]:
    reader = csv.DictReader(io.StringIO(payload.decode('utf-8-sig'), newline=''))
    if reader.fieldnames not in (list(columns), list(columns + extra_columns)):
        raise ValueError(f'{name}: unexpected or reordered CSV columns')
    rows = list(reader)
    if any(set(row) != set(reader.fieldnames) or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f'{name}: missing or extra CSV fields')
    # Replay also exports denominator/date diagnostics. Their exact known
    # headers are accepted; this figure uses only the declared pair columns.
    return [{key: row[key] for key in columns} for row in rows]


def _count(text: str) -> int:
    if not text or not text.isascii() or not text.isdecimal():
        raise ValueError('Counts must be nonnegative decimal integers')
    return int(text)


def load_tables(archive_bytes: bytes, flow_bytes: bytes) -> tuple[list[dict], dict, str]:
    """Check only the released aggregate contract; never infer source correctness."""
    rows = _rows(archive_bytes, ARCHIVE_COLUMNS, 'archive.csv', ARCHIVE_EXTRA_COLUMNS)
    indexed = {}
    count_columns = ARCHIVE_COLUMNS[4:-1]
    for row in rows:
        if (row['source'] not in dict(SOURCES) or row['archive'] not in CLOCKS
                or row['field'] not in ('evidenceDate', 'publicationDate')):
            raise ValueError('Unsupported source, release or date field')
        if row['cutoff'] != CLOCKS[row['archive']]:
            raise ValueError('Release and exclusive calendar cutoff differ from the released protocol')
        date.fromisoformat(row['cutoff'])
        key = (row['source'], row['archive'], row['field'])
        if key in indexed:
            raise ValueError('Duplicate source/release/field cell')
        item = dict(row)
        item.update({name: _count(row[name]) for name in count_columns})
        a, m, shared = item['archive_pairs'], item['modern_pairs'], item['shared']
        union = item['union']
        if (a != shared + item['archive_only'] or m != shared + item['modern_only']
                or union != shared + item['archive_only'] + item['modern_only']):
            raise ValueError('Pair-set counts do not conserve membership')
        if union == 0:
            if row['jaccard'] != '':
                raise ValueError('An empty union must have an empty, undefined Jaccard')
            item['jaccard'] = None
        else:
            supplied = float(row['jaccard'])
            if not math.isfinite(supplied) or not math.isclose(
                    supplied, shared / union, rel_tol=0, abs_tol=1e-10):
                raise ValueError('Jaccard differs from shared/union')
            item['jaccard'] = shared / union
        indexed[key] = item
    expected = {(source, archive, 'evidenceDate') for source, _ in SOURCES for archive in CLOCKS}
    if not expected.issubset(indexed):
        raise ValueError('All six primary source/release cells are required')
    sensitivity = {key for key in indexed if key[2] == 'publicationDate'}
    if sensitivity and sensitivity != {(source, archive, 'publicationDate')
                                       for source, _ in SOURCES for archive in CLOCKS}:
        raise ValueError('A supplied publicationDate sensitivity must contain all six paired cells')
    same_sensitivity = bool(sensitivity) and all(
        all(indexed[(source, archive, 'evidenceDate')][name] ==
            indexed[(source, archive, 'publicationDate')][name] for name in count_columns)
        for source, _ in SOURCES for archive in CLOCKS)
    sensitivity_note = (
        'publicationDate sensitivity: identical counts in all six paired cells; not independent replication.'
        if same_sensitivity else
        'publicationDate sensitivity is retained in archive.csv; this panel shows evidenceDate only.'
        if sensitivity else 'No publicationDate sensitivity was supplied in this CSV.')
    flow = {}
    for row in _rows(flow_bytes, ('id', 'count'), 'flow.csv'):
        if row['id'] not in FLOW_IDS or row['id'] in flow:
            raise ValueError('Unknown or duplicate flow unit')
        flow[row['id']] = _count(row['count'])
    if set(flow) != set(FLOW_IDS):
        raise ValueError('Incomplete flow accounting')
    if (flow['development'] + flow['reserve'] != flow['sizing']
            or flow['withheld_trails'] + flow['linked_trails'] != flow['selected_trails']
            or flow['selected_trails'] > flow['development']
            or flow['row_trial_links'] < flow['requested_ids']):
        raise ValueError('Flow partitions or units do not conserve counts')
    primary = [indexed[(source, archive, 'evidenceDate')]
               for source, _ in SOURCES for archive in CLOCKS]
    return primary, flow, sensitivity_note


def _archive_figure(plt, cells, sensitivity_note):
    fig, ax = plt.subplots(figsize=(11.2, 6.8))
    fig.subplots_adjust(left=0.30, right=0.72, top=0.79, bottom=0.22)
    fig.text(0.055, 0.95, 'Archived and date-filtered modern pair membership',
             fontsize=16, weight='bold', va='top')
    fig.text(0.055, 0.895,
             'Open Targets 25.09 · complete reported evidenceDate interval before the exclusive cutoff',
             fontsize=10, va='top', color='#444444')
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.6, len(cells) - 0.4)
    labels = []
    for index, cell in enumerate(cells):
        y = len(cells) - index - 1
        labels.append(f"{dict(SOURCES)[cell['source']]} · {cell['archive']}\ncutoff {cell['cutoff']}")
        value = cell['jaccard']
        color = COLORS[cell['archive']]
        if value is not None:
            ax.hlines(y, 0, value, color=color, linewidth=2, alpha=0.45)
            ax.scatter([value], [y], s=72, color=color, edgecolor='white', linewidth=0.8, zorder=3,
                       marker='o' if cell['archive'] == '22.11' else 's')
            text = f"{cell['shared']:,} / {cell['union']:,}   (J = {value:.4f})"
        else:
            text = '0 / 0   (J undefined)'
        ax.text(1.035, y, text, transform=ax.get_yaxis_transform(), va='center',
                fontsize=10, clip_on=False)
    ax.set_yticks(list(reversed(range(len(cells)))))
    ax.set_yticklabels(labels, fontsize=10)
    ax.tick_params(axis='y', length=0, pad=12)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1])
    ax.set_xlabel('Jaccard = shared literal target–disease pairs / union', fontsize=10, labelpad=10)
    ax.grid(axis='x', color='#E3E6E8', linewidth=0.7)
    ax.set_axisbelow(True)
    for side in ('top', 'left', 'right'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color('#A3A9AF')
    ax.text(1.035, 1.075, 'Cell n: shared / union', transform=ax.transAxes,
            fontsize=10, weight='bold', clip_on=False)
    fig.text(0.055, 0.12, 'Descriptive census of the selected products; no sampling confidence intervals.',
             fontsize=9, color='#444444')
    fig.text(0.055, 0.083, sensitivity_note, fontsize=9, color='#444444')
    fig.text(0.055, 0.046,
             'Literal differences can reflect mapping, curation and date coverage; they do not establish historical availability.',
             fontsize=9, color='#444444')
    return fig


def _flow_figure(plt, flow):
    from matplotlib.patches import FancyBboxPatch
    fig, ax = plt.subplots(figsize=(11.2, 8.1))
    fig.subplots_adjust(left=0.04, right=0.97, top=0.88, bottom=0.08)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    fig.text(0.055, 0.955, 'Study accounting: preserve the unit at each stage',
             fontsize=16, weight='bold', va='top')
    fig.text(0.055, 0.91, 'Contemporary reconstruction of 2016–2019 entry declarations; development audit only',
             fontsize=10, color='#444444', va='top')

    def box(x, y, width, height, number, label, color='#EAF1F8'):
        ax.add_patch(FancyBboxPatch((x, y), width, height, boxstyle='round,pad=0.012,rounding_size=0.012',
                                   edgecolor='#A3AFBB', facecolor=color, linewidth=1))
        ax.text(x + width / 2, y + height * 0.66, f'{number:,}',
                ha='center', va='center', fontsize=20, weight='bold', color='#17324D')
        ax.text(x + width / 2, y + height * 0.27, label,
                ha='center', va='center', fontsize=10, linespacing=1.4)

    def arrow(start, end):
        ax.annotate('', xy=end, xytext=start,
                    arrowprops={'arrowstyle': '-|>', 'color': '#64717E', 'lw': 1.1,
                                'shrinkA': 2, 'shrinkB': 2})

    ax.text(0.015, 0.985, '1  Pair designation', fontsize=11, weight='bold', va='top')
    box(0.02, 0.76, 0.27, 0.16, flow['sizing'], 'source-observed entry pairs')
    box(0.40, 0.79, 0.25, 0.13, flow['development'], 'development pairs')
    box(0.71, 0.79, 0.25, 0.13, flow['reserve'], 'exploratory reserve pairs', '#FFF3E5')
    arrow((0.30, 0.86), (0.385, 0.86))
    ax.plot([0.34, 0.34, 0.835], [0.86, 0.955, 0.955], color='#64717E', linewidth=1.1)
    arrow((0.835, 0.955), (0.835, 0.932))
    ax.text(0.40, 0.745, 'Disjoint designation; reserve exposure and independence remain unqualified.',
            fontsize=9, color='#444444', va='top')
    ax.plot([0.01, 0.98], [0.68, 0.68], color='#D8DDE2', linewidth=0.8)

    ax.text(0.015, 0.65, '2  Selected development audit', fontsize=11, weight='bold', va='top')
    box(0.02, 0.435, 0.27, 0.16, flow['selected_trails'], 'selected development trails')
    box(0.40, 0.465, 0.25, 0.13, flow['linked_trails'], 'registry-linked trails')
    box(0.71, 0.465, 0.25, 0.13, flow['withheld_trails'], 'trails withheld by bridge rule', '#FFF3E5')
    arrow((0.30, 0.535), (0.385, 0.535))
    ax.plot([0.34, 0.34, 0.835], [0.535, 0.625, 0.625], color='#64717E', linewidth=1.1)
    arrow((0.835, 0.625), (0.835, 0.607))
    ax.text(0.40, 0.415, 'Selected trails are a development subset, not a random population sample.',
            fontsize=9, color='#444444', va='top')
    ax.plot([0.01, 0.98], [0.35, 0.35], color='#D8DDE2', linewidth=0.8)

    ax.text(0.015, 0.32, '3  Registry lookup units', fontsize=11, weight='bold', va='top')
    box(0.12, 0.095, 0.33, 0.15, flow['requested_ids'], 'distinct requested trial IDs')
    box(0.56, 0.095, 0.33, 0.15, flow['row_trial_links'], 'original-row-to-trial links')
    ax.text(0.50, 0.04, 'Two descriptions of the linked trails; repeated trial links create dependence. Do not add these counts.',
            ha='center', fontsize=9, color='#444444')
    fig.text(0.055, 0.025, 'Box sizes are schematic. Neither registry lookup nor name agreement establishes a clinical training label.',
             fontsize=9, color='#444444')
    return fig


def plot(input_dir: Path, output: Path, dpi: int = 200) -> dict:
    if type(dpi) is not int or not 72 <= dpi <= 600:
        raise ValueError('DPI must be an integer between 72 and 600')
    input_dir, output = Path(input_dir), Path(output)
    if os.path.lexists(output):
        raise ValueError('Figure output directory must be new')
    blobs = {name: (input_dir / name).read_bytes() for name in ('archive.csv', 'flow.csv')}
    cells, flow, note = load_tables(blobs['archive.csv'], blobs['flow.csv'])
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError('Plotting requires optional matplotlib; no dependency was installed') from error
    output.mkdir(parents=True, exist_ok=False)
    figures = []
    try:
        with plt.rc_context({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none',
                             'svg.hashsalt': 'tether-temporal-audit-v1', 'axes.unicode_minus': False}):
            figures = [('archive-jaccard', _archive_figure(plt, cells, note)),
                       ('cohort-flow', _flow_figure(plt, flow))]
            for name, figure in figures:
                figure.savefig(output / (name + '.svg'), metadata={'Date': None}, facecolor='white')
                figure.savefig(output / (name + '.png'), dpi=dpi, facecolor='white')
        report = {'status': 'descriptive_figures_written', 'matplotlib_version': matplotlib.__version__,
            'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'inputs': {name: hashlib.sha256(blob).hexdigest() for name, blob in blobs.items()},
            'outputs': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in sorted(output.iterdir())},
            'primary_cells': len(cells), 'interpretation': 'descriptive_product_and_selection_accounting',
            'scientific_validation': 'not_established', 'source_rows_read': 0}
        (output / 'plot-manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        return report
    except BaseException as error:
        (output / 'failure.json').write_text(json.dumps({'status': 'plotting_failed',
            'error_class': type(error).__name__, 'outputs_may_be_partial': True}, indent=2) + '\n', encoding='utf-8')
        raise
    finally:
        for _, figure in figures:
            plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, dest='input_dir')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dpi', type=int, default=200)
    args = parser.parse_args()
    result = plot(args.input_dir, args.output, args.dpi)
    print(json.dumps({'status': result['status'], 'output': str(args.output),
                      'primary_cells': result['primary_cells']}))


if __name__ == '__main__':
    main()
