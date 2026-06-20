import csv
import os
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'results', 'query_benchmark.csv')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'results', 'fig11_query_performance.png')

rows = list(csv.DictReader(open(RESULTS)))

SCALE_ORDER  = ['S', 'M', 'L', 'XL']
ROW_COUNTS   = {'S': 4843, 'M': 227832, 'L': 450943, 'XL': 897547}
COMPLEXITY   = ['simple', 'rollup', 'pivot']
CLASS_LABELS = {'simple': 'Simple Aggregation', 'rollup': 'Roll-up', 'pivot': 'Pivot'}
COLORS       = {'simple': '#2196F3', 'rollup': '#4CAF50', 'pivot': '#F44336'}
MARKERS      = {'simple': 'o', 'rollup': 's', 'pivot': '^'}

# ── Aggregate avg median per class per scale ──────────────────────────────────
by_class = defaultdict(lambda: defaultdict(list))
for r in rows:
    by_class[r['complexity']][r['scale']].append(float(r['median_ms']))

avg_by_class = {
    c: [sum(by_class[c][s]) / len(by_class[c][s]) for s in SCALE_ORDER]
    for c in COMPLEXITY
}

x_rows = np.array([ROW_COUNTS[s] for s in SCALE_ORDER])
x_k    = x_rows / 1000

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('white')

for c in COMPLEXITY:
    y = np.array(avg_by_class[c])

    # Scatter points
    ax.scatter(x_rows, y, color=COLORS[c], marker=MARKERS[c],
               s=90, zorder=4, edgecolors='white', linewidths=0.8)

    # Regression line
    coef   = np.polyfit(x_k, y, 1)
    slope  = coef[0]
    r2     = 1 - np.sum((y - np.polyval(coef, x_k))**2) / np.sum((y - y.mean())**2)
    x_line = np.linspace(x_k.min(), x_k.max(), 300)
    y_line = np.polyval(coef, x_line)

    ax.plot(x_line * 1000, y_line, color=COLORS[c], linewidth=1.8,
            linestyle='--', alpha=0.7, zorder=3,
            label=f'{CLASS_LABELS[c]}  '
                  f'[slope = {slope:.4f} ms/1K rows,  R² = {r2:.4f}]')

# ── Threshold line ─────────────────────────────────────────────────────────────
ax.axhline(150, color='#BDBDBD', linewidth=0.8, linestyle=':', alpha=0.5,
           label='150 ms threshold')

# ── Labels ────────────────────────────────────────────────────────────────────
ax.set_xlabel('Total Fact Records (rows)', fontsize=12)
ax.set_ylabel('Median Response Time (ms)', fontsize=12)
ax.set_title('Query Response Time Across Warehouse Scales\n'
             'by Analytical Complexity Class', fontsize=13, fontweight='bold', pad=14)

ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{int(v):,}'))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f} ms'))
ax.set_xlim(left=0)
ax.set_ylim(bottom=0, top=160)
ax.grid(True, linestyle='--', alpha=0.35, color='#9E9E9E')
ax.set_axisbelow(True)
ax.legend(loc='upper left', fontsize=9.5, framealpha=0.92, edgecolor='#BDBDBD')

plt.tight_layout()
plt.savefig(OUT, dpi=180, bbox_inches='tight')
print(f'Saved → {OUT}')
plt.close()
