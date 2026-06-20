import csv
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'results', 'etl_benchmark.csv')
OUT     = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'results', 'fig_etl_scatter.png')

# ── Load data ────────────────────────────────────────────────────────────────
rows = []
with open(RESULTS, newline='') as f:
    rows = list(csv.DictReader(f))

SCALE_CFG = {
    'S' : {'color': '#2196F3', 'label': 'Scale S  (4,843 rows)',    'marker': 'o', 'z': 4},
    'M' : {'color': '#4CAF50', 'label': 'Scale M  (227,832 rows)',  'marker': 's', 'z': 3},
    'L' : {'color': '#FF9800', 'label': 'Scale L  (450,943 rows)',  'marker': '^', 'z': 2},
    'XL': {'color': '#F44336', 'label': 'Scale XL (897,547 rows)',  'marker': 'D', 'z': 1},
}

x_all, y_all = [], []
by_scale = {s: {'x': [], 'y': []} for s in SCALE_CFG}

for r in rows:
    x = int(r['rows_total_in_db'])
    y = float(r['etl_time_sec'])
    scale = r['scale']
    x_all.append(x); y_all.append(y)
    by_scale[scale]['x'].append(x)
    by_scale[scale]['y'].append(y)

x_arr = np.array(x_all)
y_arr = np.array(y_all)

# ── Regression ───────────────────────────────────────────────────────────────
coeffs     = np.polyfit(x_arr, y_arr, 1)
slope, intercept = coeffs
x_line = np.linspace(x_arr.min(), x_arr.max(), 300)
y_line = np.polyval(coeffs, x_line)

y_pred = np.polyval(coeffs, x_arr)
ss_res = np.sum((y_arr - y_pred) ** 2)
ss_tot = np.sum((y_arr - y_arr.mean()) ** 2)
r2     = 1 - ss_res / ss_tot

# ── Plot ─────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('white')

for scale, cfg in SCALE_CFG.items():
    ax.scatter(by_scale[scale]['x'], by_scale[scale]['y'],
               color=cfg['color'], marker=cfg['marker'],
               s=55, alpha=0.80, edgecolors='white', linewidths=0.5,
               zorder=cfg['z'], label=cfg['label'])

ax.plot(x_line, y_line,
        color='#212121', linewidth=1.8, linestyle='--',
        label=f'Regression line  y = {slope*1000:.4f}·(x/1000) + {intercept:.2f}  '
              f'[Growth Rate = {slope*1_000_000:.2f} ms / 1K rows]',
        zorder=5)

# ── Annotations ──────────────────────────────────────────────────────────────
ax.text(0.97, 0.97,
        f'$R^2 = {r2:.4f}$\nSlope = {slope*1_000_000:.2f} ms / 1K rows',
        transform=ax.transAxes, ha='right', va='top', fontsize=10,
        bbox=dict(boxstyle='round,pad=0.4', facecolor='#F5F5F5',
                  edgecolor='#BDBDBD', linewidth=0.8))

# ── Labels ───────────────────────────────────────────────────────────────────
ax.set_xlabel('Total Fact Records (rows)', fontsize=12)
ax.set_ylabel('ETL Execution Time (seconds)', fontsize=12)
ax.set_title('Figure X. ETL Execution Time vs. Warehouse Size\n'
             'Incremental Loading Performance Across 101 Benchmark Runs',
             fontsize=13, fontweight='bold', pad=14)

ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{int(v):,}'))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}s'))

ax.set_xlim(left=0)
ax.set_ylim(bottom=0)
ax.grid(True, linestyle='--', alpha=0.35, color='#9E9E9E')
ax.set_axisbelow(True)

ax.legend(loc='upper left', fontsize=9.5, framealpha=0.9,
          edgecolor='#BDBDBD', frameon=True)

plt.tight_layout()
plt.savefig(OUT, dpi=180, bbox_inches='tight')
print(f'Saved → {OUT}')
plt.show()
