import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'results', 'fig12_bottleneck.png')

# ── Data final dari benchmark ─────────────────────────────────────────────────
DATA = [
    ('Cube Build\nBuild Time',    25.77,  0.982, '#E53935'),
    ('ETL Pipeline\nExec Time',   10.51,  0.065, '#FB8C00'),
    ('Query Pivot\nResponse',     0.1301, 0.997, '#1E88E5'),
    ('Query Simple\nResponse',    0.0716, 0.995, '#1E88E5'),
    ('Query Roll-up\nResponse',   0.0527, 0.999, '#1E88E5'),
]

labels  = [d[0] for d in DATA]
slopes  = [d[1] for d in DATA]
r2s     = [d[2] for d in DATA]
colors  = [d[3] for d in DATA]
x       = np.arange(len(labels))
width   = 0.62

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
fig.patch.set_facecolor('white')
fig.suptitle('Comparative Scalability Characteristics Across\n'
             'ETL, Cube Construction, and Query Layers',
             fontsize=13, fontweight='bold', y=0.98)

# ── Top: Growth Rate ──────────────────────────────────────────────────────────
bars1 = ax1.bar(x, slopes, width=width, color=colors,
                edgecolor='white', linewidth=0.8, zorder=3)

# Value labels on top of each bar
DISP_SLOPE = ['25.77', '10.51', '0.1301', '0.0716', '0.0527']
for bar, val, lbl in zip(bars1, slopes, DISP_SLOPE):
    ax1.text(bar.get_x() + bar.get_width() / 2,
             bar.get_height() + 0.4,
             lbl, ha='center', va='bottom',
             fontsize=9, color='#212121', fontweight='bold')


ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontsize=9.5)
ax1.set_ylabel('Growth Rate (ms per 1,000 rows)', fontsize=10.5)
ax1.set_title('(a) Growth Rate by Layer', fontsize=11,
              fontweight='bold', pad=8)
ax1.set_ylim(0, max(slopes) * 1.20)
ax1.yaxis.set_minor_locator(ticker.AutoMinorLocator())
ax1.grid(True, axis='y', linestyle='--', alpha=0.35, color='#9E9E9E', zorder=0)
ax1.set_axisbelow(True)
ax1.spines[['top', 'right']].set_visible(False)

# ── Bottom: R² ───────────────────────────────────────────────────────────────
bars2 = ax2.bar(x, r2s, width=width, color=colors,
                edgecolor='white', linewidth=0.8, zorder=3)

DISP_R2 = ['0.982', '0.065', '0.997', '0.995', '0.999']
for bar, val, lbl in zip(bars2, r2s, DISP_R2):
    if val < 0.15:
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() - 0.04,
                 lbl, ha='center', va='top',
                 fontsize=9, color='#212121', fontweight='bold')
    elif val > 0.98:
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() - 0.04,
                 lbl, ha='center', va='top',
                 fontsize=9, color='white', fontweight='bold')
    else:
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 0.01,
                 lbl, ha='center', va='bottom',
                 fontsize=9, color='#212121', fontweight='bold')


# R²=0.9 reference line
ax2.axhline(0.9, color='#9E9E9E', linewidth=0.9, linestyle=':',
            alpha=0.7, zorder=2, label='R² = 0.90 reference')

ax2.set_xticks(x)
ax2.set_xticklabels(labels, fontsize=9.5)
ax2.set_ylabel('Coefficient of Determination (R²)', fontsize=10.5)
ax2.set_title('(b) Linearity of Growth (R²)', fontsize=11,
              fontweight='bold', pad=8)
ax2.set_ylim(0, 1.15)
ax2.yaxis.set_minor_locator(ticker.AutoMinorLocator())
ax2.grid(True, axis='y', linestyle='--', alpha=0.35, color='#9E9E9E', zorder=0)
ax2.set_axisbelow(True)
ax2.spines[['top', 'right']].set_visible(False)
ax2.legend(loc='upper right', fontsize=8.5, framealpha=0.9,
           edgecolor='#BDBDBD')

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(OUT, dpi=180, bbox_inches='tight')
print(f'Saved → {OUT}')
plt.close()
