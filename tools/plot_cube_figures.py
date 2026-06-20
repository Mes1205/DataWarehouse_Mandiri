import csv
import os
import numpy as np
import matplotlib.pyplot as plt

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'results', 'cube_benchmark.csv')
OUT_9  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'results', 'fig9_cube_buildtime.png')
OUT_10 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'results', 'fig10_cube_memory.png')

# ── Load data ────────────────────────────────────────────────────────────────
rows = list(csv.DictReader(open(RESULTS)))

SCALE_ORDER  = ['S', 'M', 'L', 'XL']
SCALE_LABELS = {'S': 'Scale S\n(4,843)', 'M': 'Scale M\n(227,832)',
                'L': 'Scale L\n(450,943)', 'XL': 'Scale XL\n(897,547)'}
COLORS       = {'S': '#2196F3', 'M': '#4CAF50', 'L': '#FF9800', 'XL': '#F44336'}

data = {r['scale']: r for r in rows}
x_rows  = np.array([int(data[s]['n_rows'])             for s in SCALE_ORDER])
y_build = np.array([float(data[s]['median_build_sec']) for s in SCALE_ORDER])
y_mem   = np.array([float(data[s]['median_memory_mb']) for s in SCALE_ORDER])

x_k = x_rows / 1000  # per 1K rows


def regression(x, y):
    c    = np.polyfit(x, y, 1)
    yp   = np.polyval(c, x)
    r2   = 1 - np.sum((y - yp) ** 2) / np.sum((y - y.mean()) ** 2)
    return c[0], c[1], r2


def smooth_line(x, coeffs):
    x_line = np.linspace(x.min(), x.max(), 300)
    return x_line, np.polyval(coeffs, x_line)


# ── Figure 9: Cube Build Time ─────────────────────────────────────────────────
slope_b, intercept_b, r2_b = regression(x_k, y_build * 1000)  # ms
coeffs_b = np.polyfit(x_k, y_build, 1)

fig, ax = plt.subplots(figsize=(9, 5.5))
fig.patch.set_facecolor('white')

for s in SCALE_ORDER:
    ax.scatter(int(data[s]['n_rows']), float(data[s]['median_build_sec']),
               color=COLORS[s], s=120, zorder=4, edgecolors='white',
               linewidths=0.8, label=SCALE_LABELS[s].replace('\n', '  '))

x_line, y_line = smooth_line(x_k, coeffs_b)
ax.plot(x_line * 1000, y_line, color='#212121', linewidth=1.8, linestyle='--',
        label='Regression line', zorder=3)

ax.text(0.97, 0.05,
        f'$R^2 = {r2_b:.4f}$\nSlope = {slope_b:.2f} ms / 1K rows',
        transform=ax.transAxes, ha='right', va='bottom', fontsize=10,
        bbox=dict(boxstyle='round,pad=0.4', facecolor='#F5F5F5',
                  edgecolor='#BDBDBD', linewidth=0.8))

ax.set_xlabel('Total Fact Records (rows)', fontsize=12)
ax.set_ylabel('Cube Build Time (seconds)', fontsize=12)
ax.set_title('Cube Construction Time Across Warehouse Scales\n'
             'with Linear Regression Trend', fontsize=13, fontweight='bold', pad=14)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{int(v):,}'))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}s'))
ax.set_xlim(left=0)
ax.set_ylim(bottom=0)
ax.grid(True, linestyle='--', alpha=0.35, color='#9E9E9E')
ax.set_axisbelow(True)
ax.legend(loc='upper left', fontsize=9, framealpha=0.9, edgecolor='#BDBDBD')

plt.tight_layout()
plt.savefig(OUT_9, dpi=180, bbox_inches='tight')
print(f'Saved → {OUT_9}')
plt.close()

# ── Figure 10: Memory Consumption ────────────────────────────────────────────
slope_m, intercept_m, r2_m = regression(x_k, y_mem)
coeffs_m = np.polyfit(x_k, y_mem, 1)

fig, ax = plt.subplots(figsize=(9, 5.5))
fig.patch.set_facecolor('white')

for s in SCALE_ORDER:
    ax.scatter(int(data[s]['n_rows']), float(data[s]['median_memory_mb']),
               color=COLORS[s], s=120, zorder=4, edgecolors='white',
               linewidths=0.8, label=SCALE_LABELS[s].replace('\n', '  '))

x_line, y_line = smooth_line(x_k, coeffs_m)
ax.plot(x_line * 1000, y_line, color='#212121', linewidth=1.8, linestyle='--',
        label='Regression line', zorder=3)

ax.text(0.97, 0.05,
        f'$R^2 = {r2_m:.4f}$\nSlope = {slope_m:.4f} MB / 1K rows',
        transform=ax.transAxes, ha='right', va='bottom', fontsize=10,
        bbox=dict(boxstyle='round,pad=0.4', facecolor='#F5F5F5',
                  edgecolor='#BDBDBD', linewidth=0.8))

ax.set_xlabel('Total Fact Records (rows)', fontsize=12)
ax.set_ylabel('Memory Consumption — RSS (MB)', fontsize=12)
ax.set_title('Memory Consumption During MOLAP Cube Construction\n'
             'Across Warehouse Scales', fontsize=13, fontweight='bold', pad=14)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{int(v):,}'))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f} MB'))
ax.set_xlim(left=0)
ax.set_ylim(bottom=0)
ax.grid(True, linestyle='--', alpha=0.35, color='#9E9E9E')
ax.set_axisbelow(True)
ax.legend(loc='upper left', fontsize=9, framealpha=0.9, edgecolor='#BDBDBD')

plt.tight_layout()
plt.savefig(OUT_10, dpi=180, bbox_inches='tight')
print(f'Saved → {OUT_10}')
plt.close()
