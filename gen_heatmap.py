"""Regenerate failure heatmap — no title, no colorbar, compact."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

RESULTS_DIR = Path("pilot/results")
FIGURES_DIR = Path("figures")

FAILURE_TYPES = ["PI", "GD", "UA", "HT", "RF", "OF", "PL", "SH"]
VERSIONS = ["Control", "Treated"]

data = np.array([
    [2, 0, 1, 0, 0, 0, 1, 0],
    [0, 0, 1, 0, 0, 0, 0, 0],
])

fig, ax = plt.subplots(figsize=(10, 3.5))

im = ax.imshow(data, cmap='YlOrRd', aspect='equal', vmin=0, vmax=2)

ax.set_xticks(range(len(FAILURE_TYPES)))
ax.set_xticklabels(FAILURE_TYPES, fontsize=13, fontweight='bold')
ax.set_yticks(range(len(VERSIONS)))
ax.set_yticklabels(VERSIONS, fontsize=13, fontweight='bold')

for i in range(len(VERSIONS)):
    for j in range(len(FAILURE_TYPES)):
        val = data[i, j]
        ax.text(j, i, str(int(val)), ha='center', va='center',
                fontsize=16, fontweight='bold',
                color='white' if val > 1 else 'black')

# No title, no colorbar
plt.tight_layout()

for path in [RESULTS_DIR / "failure_heatmap.png", FIGURES_DIR / "failure_heatmap.png"]:
    plt.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
print("Saved compact heatmap (no title, no colorbar).")
plt.close()
