"""Render launch media from recorded results and `npm run demo` output.

Optional media dependencies: matplotlib, Pillow. They are not runtime dependencies.
Run from the repository root: python3 demo/render_assets.py
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'assets'
OUT.mkdir(parents=True, exist_ok=True)
BG, PANEL, TEXT, MUTED, GREEN, ORANGE = '#0c1522', '#152438', '#f2f6fb', '#adbed1', '#5ce0b0', '#f8b66c'
rows = [json.loads(p.read_text()) for p in (ROOT / 'results/general-v3-aggressive-r1').glob('*/result.json')]
assert len(rows) == 24 and not any(row.get('error') for row in rows)
arms = ['baseline', 'laya', 'von']
totals = {arm: {key: sum(row[key] for row in rows if row['arm'] == arm)
                for key in ['inputTotal', 'inputUncached', 'inputCached', 'cacheWrite']} for arm in arms}
assert all(value['cacheWrite'] == 0 for value in totals.values())
passes = {arm: sum(row['evaluation']['success'] for row in rows if row['arm'] == arm) for arm in arms}
saving = 100 * (1 - totals['laya']['inputTotal'] / totals['baseline']['inputTotal'])
plt.rcParams.update({'font.family': 'DejaVu Sans', 'text.color': TEXT,
                     'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': TEXT})
fig = plt.figure(figsize=(14, 9), facecolor=BG)
fig.text(.07, .94, 'PI CONTEXT GC  /  EXPLORATORY BENCHMARK', color=GREEN, fontsize=12, weight='bold')
fig.text(.07, .84, f'{saving:.1f}% fewer input tokens.', fontsize=37, weight='bold')
fig.text(.07, .785, '8 synthetic Python tasks · 1 repetition per arm · cached input included', fontsize=15, color=MUTED)
ax = fig.add_axes([.17, .33, .65, .35], facecolor=BG)
for index, arm in enumerate(arms):
    y = 2 - index
    value = totals[arm]
    ax.barh(y, value['inputUncached'], height=.42, color=ORANGE, label='Uncached input' if index == 0 else None)
    ax.barh(y, value['inputCached'], left=value['inputUncached'], height=.42, color=GREEN,
            label='Cached input' if index == 0 else None)
    ax.text(value['inputTotal'] + 8500, y, f"{value['inputTotal']:,}", va='center', fontsize=14, weight='bold')
    ax.text(1.075, y, f'{passes[arm]}/8', transform=ax.get_yaxis_transform(),
            va='center', fontsize=19, weight='bold')
ax.set_yticks([2, 1, 0], ['Baseline', 'Laya-guided', 'Von-guided'], fontsize=13)
ax.set_ylim(-.6, 2.65)
ax.set_xlim(0, 590000)
ax.set_xticks([0, 100000, 200000, 300000, 400000, 500000])
ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f'{value / 1000:.0f}k'))
ax.set_xlabel('Total input tokens across all requests', fontsize=12, labelpad=12)
ax.tick_params(axis='both', length=0, pad=12)
for spine in ax.spines.values(): spine.set_visible(False)
ax.set_axisbelow(True)
ax.grid(axis='x', color='#26364a', linewidth=.6)
fig.text(.865, .704, 'TASKS\nPASSED', color=MUTED, fontsize=10)
legend = ax.legend(loc='upper left', bbox_to_anchor=(0, 1.25), ncol=2, frameon=False, fontsize=12)
for text in legend.get_texts(): text.set_color(TEXT)
fig.text(.07, .21, 'Uncached input rose 6.4% with Laya. No demonstrated cost or quota saving.', color=ORANGE, fontsize=14, weight='bold')
fig.text(.07, .163, 'Laya savings interval: 17.4–53.9%. Earlier safe policy: 7.6% pooled savings.', color=MUTED, fontsize=12)
fig.text(.07, .12, 'Laya matched baseline task passes; Von lost one. Learned-judge advantage is unproven.', color=MUTED, fontsize=12)
fig.text(.07, .055, 'github.com/Lausi-h2ai/pi-context-gc', color=GREEN, fontsize=13, weight='bold')
fig.text(.93, .055, 'Source: v3 · 24 completed trials', ha='right', color=MUTED, fontsize=11)
fig.savefig(OUT / 'v3-results.png', dpi=140, facecolor=BG)
fig.savefig(OUT / 'v3-results.svg', facecolor=BG)
svg = OUT / 'v3-results.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
plt.close(fig)

demo = json.loads((ROOT / '.runtime/demo/replay.json').read_text())
assert demo['identical'] and demo['originalSha256'] == demo['recoveredSha256']
font_root = Path(matplotlib.get_data_path()) / 'fonts/ttf'
def font(size, bold=False, mono=False):
    family = 'DejaVuSansMono' if mono else 'DejaVuSans'
    return ImageFont.truetype(str(font_root / f'{family}{"-Bold" if bold else ""}.ttf'), size)

def frame(number, title, subtitle, lines, badge):
    im = Image.new('RGB', (1200, 720), BG)
    draw = ImageDraw.Draw(im)
    draw.text((60, 36), 'PI CONTEXT GC   /   KEEP THE EVIDENCE', font=font(19, True), fill=GREEN)
    draw.text((60, 94), title, font=font(43, True), fill=TEXT)
    draw.text((60, 157), subtitle, font=font(22), fill=MUTED)
    draw.rounded_rectangle((60, 213, 1140, 533), radius=18, fill=PANEL)
    for index, (text, color) in enumerate(lines):
        draw.text((88, 243 + index * 46), text, font=font(22, mono=True), fill=color)
    draw.text((60, 565), badge, font=font(25, True), fill=GREEN)
    draw.text((60, 624), 'Visual replay of real policy execution · synthetic log · deterministic judge', font=font(18), fill=MUTED)
    draw.text((60, 656), 'No model requests. This demonstrates recovery, not benchmark savings.', font=font(18), fill=MUTED)
    draw.text((1090, 565), f'{number}/4', font=font(20), fill=MUTED)
    return im

frames = [
    frame(1, 'Read it once. Carry it again?', 'Old tool output can stay in every later request.', [
        ('diagnostic.log', MUTED),
        ('PASS fixture-001: expected value matches actual value', TEXT),
        ('PASS fixture-002: expected value matches actual value', TEXT),
        ('... 158 more routine PASS lines ...', MUTED),
        (demo['recoveredFailure'], ORANGE),
    ], f"Original tool result: {demo['originalCharacters']:,} characters"),
    frame(2, 'Archive the bulk.', 'The real context policy writes the original output to disk.', [
        ('Later request: replace the old result with a reference', MUTED),
        ('[Earlier read output archived at', TEXT),
        (f" .runtime/demo/artifacts/{demo['originalSha256'][:12]}....txt]", GREEN),
        ('Read it if exact details are needed.', TEXT),
        ('Path shortened here for display.', MUTED),
    ], f"Context now carries a {demo['replacementCharacters']}-character reference."),
    frame(3, 'Need the detail? Read it back.', 'The demo reads the saved file and checks exact recovery.', [
        (demo['recoveredFailure'], ORANGE),
        ('', TEXT),
        ('Original SHA-256:  ' + demo['originalSha256'][:22] + '...', MUTED),
        ('Recovered SHA-256: ' + demo['recoveredSha256'][:22] + '...', MUTED),
        ('Exact byte comparison: PASS', GREEN),
    ], 'Every byte in this demo was recovered.'),
    frame(4, 'Try the mechanism locally.', 'After cloning the repository:', [
        ('$ npm ci', TEXT),
        ('$ npm run demo', GREEN),
        ('', TEXT),
        ('No GPU or model login needed for this demo.', MUTED),
        ('github.com/Lausi-h2ai/pi-context-gc', TEXT),
    ], 'Source, benchmark traces, and limitations are public.'),
]
frames[0].save(OUT / 'archive-demo.gif', save_all=True, append_images=frames[1:],
               duration=[3500, 4000, 4000, 3500], loop=0, optimize=True)
frames[2].save(OUT / 'archive-recovery.png')
print('Rendered:', ', '.join(p.name for p in OUT.iterdir()))
