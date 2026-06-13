# MELD Graph Viewer

Generate a self-contained HTML file to view MRI volumes and FreeSurfer surfaces in your browser — no server, no installation beyond Python itself.

The output is a single `.html` file with all data embedded. Open it by double-clicking, share it with a colleague, or archive it alongside your results.

---

## Requirements

| Requirement | Details |
|-------------|---------|
| **Python** | 3.9 or later (uses `X \| Y` type hints) |
| **Packages** | None — standard library only |
| **Internet** | One-time download of the NiiVue viewer bundle (~1.5 MB, cached) |
| **OS** | macOS, Linux, Windows |

No `pip install` is needed.

---

## Installation

```bash
git clone <this-repo>
cd meld_graph_viewer
```

That's it. The script is `open_freebrowse.py`.

---

## Usage

```bash
python open_freebrowse.py \
  --t1w        path/to/T1w.nii.gz \
  --flair      path/to/FLAIR.nii.gz \
  --pial-lh    path/to/lh.pial \
  --white-lh   path/to/lh.white \
  --pial-rh    path/to/rh.pial \
  --white-rh   path/to/rh.white \
  --lesion     path/to/lesion_mask.nii.gz \
  --output     viewer.html
```

All arguments are optional — pass only what you have. At least one file must be provided.

| Argument | Description |
|----------|-------------|
| `--t1w` | T1-weighted volume (`.nii.gz` or `.mgz`) |
| `--flair` | FLAIR volume (`.nii.gz` or `.mgz`) |
| `--pial-lh` | Left hemisphere pial surface |
| `--white-lh` | Left hemisphere white matter surface |
| `--pial-rh` | Right hemisphere pial surface |
| `--white-rh` | Right hemisphere white matter surface |
| `--lesion` | Lesion mask overlay (`.nii.gz` or `.mgz`) |
| `--output` | Output HTML file (default: `viewer.html`) |

The script opens the generated file in your default browser automatically.

### Minimal example (volumes only)

```bash
python open_freebrowse.py --t1w T1w.nii.gz --flair FLAIR.nii.gz
```

### Surfaces only

```bash
python open_freebrowse.py --pial-lh lh.pial --white-lh lh.white
```

---

## Output

The script produces a single `.html` file. It can be:

- **Opened** directly by double-clicking (no server needed)
- **Shared** by copying or emailing the file
- **Archived** alongside subject data

File size is roughly **1.3× the sum of your input files** due to base64 encoding.

---

## Display

| Layer | Color |
|-------|-------|
| T1w | Grayscale, opacity 1.0 |
| FLAIR | Grayscale, opacity 0.7 |
| Lesion mask | Random colormap, opacity 0.8 |
| Pial surfaces (LH + RH) | Yellow |
| White matter surfaces (LH + RH) | Orange |

Surfaces are shown in crosscut mode on 2D slices.

---

## Privacy

All MRI data stays on your computer. The only outbound network request is a one-time download of the [NiiVue](https://github.com/niivue/niivue) JavaScript bundle (~1.5 MB) from jsDelivr, which is then cached locally. After the first run, the script works fully offline.

---

## Troubleshooting

**`python` not found** — try `python3 open_freebrowse.py ...`

**Requires Python 3.9+** — check your version with `python --version`. On older systems, replace `Path | None` type hints with `Optional[Path]` or upgrade Python.

**Browser does not open automatically** — open the output HTML file manually from your file manager.

**NiiVue bundle download fails** — check your internet connection. The cached file is stored in your system temp directory (`/tmp/freebrowse_html_cache/` on macOS/Linux, `%TEMP%\freebrowse_html_cache\` on Windows).
