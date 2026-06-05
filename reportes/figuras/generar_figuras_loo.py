"""Genera las figuras de validación LOO blind para la tesis.

Lee `loo_resultados_n26.csv` (formato largo) y produce las 8 figuras finales
en PNG (300 dpi) y SVG en `reportes/figuras/`.

Uso:
    ./venv_311/Scripts/python.exe reportes/figuras/generar_figuras_loo.py
"""
import re
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

HERE = Path(__file__).resolve().parent
CSV_N26 = HERE / "loo_resultados_n26.csv"

sns.set_theme(style="whitegrid", context="paper", font_scale=1.15)
mpl.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.family": "DejaVu Sans", "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
})

COLOR_SIMBA = "#1f77b4"
COLOR_BSOID = "#d62728"
COLOR_ENSEMBLE = "#2ca02c"
COLOR_CONDITIONAL = "#9467bd"
COLOR_DYNAMIC = "#ff7f0e"
PALETA = {
    "SimBA RF": COLOR_SIMBA, "B-SOiD": COLOR_BSOID,
    "Ensemble OR": COLOR_ENSEMBLE, "Conditional": COLOR_CONDITIONAL,
    "Dynamic": COLOR_DYNAMIC,
}
MODEL_LABEL = {
    "simba": "SimBA RF", "bsoid": "B-SOiD", "ensemble": "Ensemble OR",
    "conditional": "Conditional", "dynamic": "Dynamic",
}


def save(fig, name):
    fig.savefig(HERE / f"{name}.png")
    fig.savefig(HERE / f"{name}.svg")
    print(f"  guardada {name}.png + {name}.svg")


def short_label(video):
    return video.split("_")[0]


def extract_frames_from_logs(videos):
    """Lee logs/loo_full_<video>.log y extrae 'GT: X frames'."""
    logs_dir = HERE.parent.parent / "logs"
    pat = re.compile(r"GT:\s*(\d+)\s*frames")
    out = {}
    for video in videos:
        log_file = logs_dir / f"loo_full_{video}.log"
        if not log_file.exists():
            continue
        content = log_file.read_text(encoding="utf-8", errors="replace")
        m = pat.search(content)
        if m:
            out[video] = int(m.group(1))
    return out


def main():
    if not CSV_N26.exists():
        raise SystemExit(f"No existe {CSV_N26}")

    df = pd.read_csv(CSV_N26)
    df["video_short"] = df["video"].map(short_label)
    df["metodo"] = df["model"].map(MODEL_LABEL)
    n_videos = df["video"].nunique()
    print(f"Cargados {len(df)} registros, {n_videos} videos")

    g = df[df["behavior"] == "Grooming"].copy()
    t = df[df["behavior"] == "Thigmotaxis"].copy()

    sin_gt_groom = set(short_label(v) for v in g[g["model"] == "simba"]
                       .query("tp + fn == 0")["video"])
    sin_gt_thigmo = set(short_label(v) for v in t[t["model"] == "simba"]
                        .query("tp + fn == 0")["video"])
    print(f"Sin GT Grooming: {sorted(sin_gt_groom)}")
    print(f"Sin GT Thigmotaxis: {sorted(sin_gt_thigmo)}")

    def mark_no_gt(ax, sin_gt_set, marker="*"):
        new_labels = []
        for tl in ax.get_xticklabels():
            txt = tl.get_text()
            if txt in sin_gt_set:
                new_labels.append(f"{txt}{marker}")
                tl.set_color("#c0392b")
                tl.set_fontweight("bold")
            else:
                new_labels.append(txt)
        ax.set_xticklabels(new_labels)

    orden_videos = sorted(df["video_short"].unique())

    # ---- Fig 1: Barras F1 Grooming por video × 3 métodos ----
    metodos_3 = ["SimBA RF", "B-SOiD", "Ensemble OR"]
    df_g3 = g[g["metodo"].isin(metodos_3)].copy()
    fig, ax = plt.subplots(figsize=(13, 4.8))
    sns.barplot(data=df_g3, x="video_short", y="f1", hue="metodo",
                order=orden_videos, hue_order=metodos_3,
                palette=PALETA, ax=ax, edgecolor="white")
    ax.axhline(0.85, color="gray", linestyle="--", linewidth=1,
               label="F1 mínimo deseable (0.85)")
    ax.set_title(f"F1 de Grooming por video — Validación LOO ciega (n={n_videos})")
    ax.set_xlabel("Video (animal excluido del entrenamiento)")
    ax.set_ylabel("F1 (validación ciega)")
    ax.set_ylim(0, 1.05)
    ax.tick_params(axis="x", rotation=45)
    for tl in ax.get_xticklabels():
        tl.set_horizontalalignment("right")
    mark_no_gt(ax, sin_gt_groom, "*")
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    fig.text(0.5, -0.02,
             "* Videos sin Grooming positivo etiquetado en GT (F1=0 por definición).",
             ha="center", fontsize=8.5, style="italic", color="#c0392b")
    save(fig, "fig1_f1_grooming_barras")
    plt.close(fig)

    # ---- Fig 2: Boxplot F1 Grooming por método (5) ----
    orden_5 = ["SimBA RF", "B-SOiD", "Ensemble OR", "Conditional", "Dynamic"]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    sns.boxplot(data=g, x="metodo", y="f1", order=orden_5, hue="metodo",
                palette=PALETA, ax=ax, width=0.55, fliersize=0,
                linewidth=1.2, legend=False)
    sns.stripplot(data=g, x="metodo", y="f1", order=orden_5,
                  color="black", alpha=0.55, size=4.5, jitter=0.12, ax=ax)
    means = g.groupby("metodo")["f1"].mean()
    for i, met in enumerate(orden_5):
        ax.annotate(f"μ={means[met]:.2f}", (i, means[met]), xytext=(10, 0),
                    textcoords="offset points", va="center",
                    fontsize=9.5, fontweight="bold")
    ax.set_title(f"Distribución del F1 de Grooming por método (n={n_videos})")
    ax.set_xlabel("")
    ax.set_ylabel("F1 (validación ciega)")
    ax.set_ylim(-0.05, 1.05)
    ax.tick_params(axis="x", rotation=15)
    save(fig, "fig2_distribucion_f1_metodos")
    plt.close(fig)

    # ---- Fig 3: Grooming vs Thigmotaxis SimBA por video ----
    simba_only = df[df["model"] == "simba"].copy()
    fig, ax = plt.subplots(figsize=(13, 4.4))
    sns.barplot(data=simba_only, x="video_short", y="f1", hue="behavior",
                order=orden_videos,
                palette={"Grooming": "#e377c2", "Thigmotaxis": "#17becf"},
                ax=ax, edgecolor="white")
    for cond, c in [("Grooming", "#e377c2"), ("Thigmotaxis", "#17becf")]:
        m = simba_only[simba_only["behavior"] == cond]["f1"].mean()
        ax.axhline(m, color=c, linestyle=":", linewidth=1.4, alpha=0.8,
                   label=f"Promedio {cond}: {m:.2f}")
    ax.set_title(f"F1 SimBA — Grooming vs Thigmotaxis (n={n_videos}, LOO ciega)")
    ax.set_xlabel("Video (animal excluido del entrenamiento)")
    ax.set_ylabel("F1 (validación ciega)")
    ax.set_ylim(0, 1.05)
    ax.tick_params(axis="x", rotation=45)
    for tl in ax.get_xticklabels():
        tl.set_horizontalalignment("right")
    sin_gt_cualquier = sin_gt_groom | sin_gt_thigmo
    mark_no_gt(ax, sin_gt_cualquier, "*")
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    fig.text(0.5, -0.02,
             f"* Videos sin GT positivo — sin Grooming: {sorted(sin_gt_groom)}; "
             f"sin Thigmotaxis: {sorted(sin_gt_thigmo)}",
             ha="center", fontsize=8.5, style="italic", color="#c0392b")
    save(fig, "fig3_grooming_vs_thigmotaxis")
    plt.close(fig)

    # ---- Fig 4: Precisión vs Recall ----
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharex=True, sharey=True)
    gs = simba_only[simba_only["behavior"] == "Grooming"]
    axes[0].scatter(gs["recall"], gs["precision"], s=80, c=COLOR_SIMBA,
                    edgecolors="black", linewidth=0.6, zorder=3, alpha=0.85)
    for _, r in gs.iterrows():
        if r["precision"] > 0 or r["recall"] > 0:
            axes[0].annotate(short_label(r["video"]),
                             (r["recall"], r["precision"]),
                             xytext=(5, 4), textcoords="offset points",
                             fontsize=7.5, alpha=0.75)
    axes[0].set_title("Grooming")
    axes[0].set_xlabel("Exhaustividad (Recall)")
    axes[0].set_ylabel("Precisión")

    ts = simba_only[simba_only["behavior"] == "Thigmotaxis"]
    ts_valid = ts[(ts["tp"] + ts["fn"]) > 0]
    axes[1].scatter(ts_valid["recall"], ts_valid["precision"], s=80, c="#17becf",
                    edgecolors="black", linewidth=0.6, zorder=3, alpha=0.85)
    for _, r in ts_valid.iterrows():
        axes[1].annotate(short_label(r["video"]),
                         (r["recall"], r["precision"]),
                         xytext=(5, 4), textcoords="offset points",
                         fontsize=7.5, alpha=0.75)
    axes[1].set_title("Thigmotaxis")
    axes[1].set_xlabel("Exhaustividad (Recall)")

    for ax in axes:
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 1.05)
        for f1_iso in [0.2, 0.4, 0.6, 0.8]:
            x = np.linspace(0.01, 1.0, 200)
            y = (f1_iso * x) / (2 * x - f1_iso)
            m = (y > 0) & (y <= 1)
            ax.plot(x[m], y[m], color="gray", linestyle=":", linewidth=0.8, alpha=0.5)
            ax.text(1.0, f1_iso / (2 - f1_iso), f"F1={f1_iso}",
                    color="gray", fontsize=8, va="bottom", ha="right")
    fig.suptitle(f"Precisión vs Exhaustividad (SimBA RF, n={n_videos})",
                 fontweight="bold")
    fig.tight_layout()
    save(fig, "fig4_precision_vs_recall")
    plt.close(fig)

    # ---- Fig 5: Desbalance de clases ----
    frames_por_video = extract_frames_from_logs(df["video"].unique())
    rows = []
    for video in df["video"].unique():
        total = frames_por_video.get(video)
        if total is None:
            continue
        g_row = df[(df["video"] == video) & (df["behavior"] == "Grooming")
                   & (df["model"] == "simba")].iloc[0]
        t_row = df[(df["video"] == video) & (df["behavior"] == "Thigmotaxis")
                   & (df["model"] == "simba")].iloc[0]
        rows.append({
            "video": short_label(video),
            "Grooming": (g_row["tp"] + g_row["fn"]) / total * 100,
            "Thigmotaxis": (t_row["tp"] + t_row["fn"]) / total * 100,
        })
    df_pct = pd.DataFrame(rows).melt(id_vars="video", var_name="conducta",
                                     value_name="pct")
    fig, ax = plt.subplots(figsize=(13, 4.4))
    sns.barplot(data=df_pct, x="video", y="pct", hue="conducta",
                order=sorted(df_pct["video"].unique()),
                palette={"Grooming": "#e377c2", "Thigmotaxis": "#17becf"},
                ax=ax, edgecolor="white")
    media_g = df_pct[df_pct["conducta"] == "Grooming"]["pct"].mean()
    media_t = df_pct[df_pct["conducta"] == "Thigmotaxis"]["pct"].mean()
    ax.axhline(media_g, color="#e377c2", linestyle="--", linewidth=1.0,
               alpha=0.7, label=f"Grooming promedio ({media_g:.1f}%)")
    ax.axhline(media_t, color="#17becf", linestyle="--", linewidth=1.0,
               alpha=0.7, label=f"Thigmotaxis promedio ({media_t:.1f}%)")
    ax.set_title(f"Desbalance de clases — % de frames con conducta positiva (n={n_videos})")
    ax.set_xlabel("Video")
    ax.set_ylabel("% frames con conducta")
    ax.tick_params(axis="x", rotation=45)
    for tl in ax.get_xticklabels():
        tl.set_horizontalalignment("right")
    ax.legend(loc="upper right", frameon=True, fontsize=8)
    save(fig, "fig5_desbalance_clases")
    plt.close(fig)

    # ---- Fig 6: Trampa de la Exactitud ----
    total_frames = sum(frames_por_video.values())
    groom_pos = int(simba_only[simba_only["behavior"] == "Grooming"].apply(
        lambda r: r["tp"] + r["fn"], axis=1).sum())
    groom_neg = total_frames - groom_pos
    thigmo_pos = int(simba_only[simba_only["behavior"] == "Thigmotaxis"].apply(
        lambda r: r["tp"] + r["fn"], axis=1).sum())
    thigmo_neg = total_frames - thigmo_pos
    f1_simba_g = g[g["model"] == "simba"]["f1"].mean()
    f1_ens_g = g[g["model"] == "ensemble"]["f1"].mean()
    modelos = ["Modelo trivial\n(predice 0)", "SimBA RF\nLOO ciega",
               "Ensemble OR\nLOO ciega"]
    accuracy_groom = [groom_neg / total_frames, 0.91, 0.92]
    f1_groom = [0.0, f1_simba_g, f1_ens_g]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6),
                             gridspec_kw={"width_ratios": [1.3, 1, 1]})
    x = np.arange(len(modelos))
    w = 0.36
    axes[0].bar(x - w/2, accuracy_groom, w, color="#bcbd22",
                label="Exactitud", edgecolor="white")
    axes[0].bar(x + w/2, f1_groom, w, color=COLOR_SIMBA,
                label="F1", edgecolor="white")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(modelos, fontsize=9)
    axes[0].set_ylabel("Valor de la métrica")
    axes[0].set_ylim(0, 1.05)
    axes[0].set_title("Grooming: Exactitud vs F1")
    axes[0].legend(loc="upper left", frameon=True)
    for i, (a, f) in enumerate(zip(accuracy_groom, f1_groom)):
        axes[0].text(i - w/2, a + 0.015, f"{a:.2f}", ha="center", fontsize=9)
        axes[0].text(i + w/2, f + 0.015, f"{f:.2f}", ha="center", fontsize=9)
    pct_g = groom_pos / total_frames * 100
    axes[1].pie([groom_pos, groom_neg],
                labels=[f"Grooming\npositivo\n({pct_g:.1f}%)",
                        f"No-Grooming\n({100-pct_g:.1f}%)"],
                colors=["#e377c2", "#dddddd"],
                autopct="%1.1f%%", startangle=90,
                wedgeprops={"edgecolor": "white", "linewidth": 2},
                textprops={"fontsize": 9})
    axes[1].set_title(f"Composición Grooming\n(n={total_frames:,} frames)",
                      fontsize=10)
    pct_t = thigmo_pos / total_frames * 100
    axes[2].pie([thigmo_pos, thigmo_neg],
                labels=[f"Thigmotaxis\npositivo\n({pct_t:.1f}%)",
                        f"No-Thigmotaxis\n({100-pct_t:.1f}%)"],
                colors=["#17becf", "#dddddd"],
                autopct="%1.1f%%", startangle=90,
                wedgeprops={"edgecolor": "white", "linewidth": 2},
                textprops={"fontsize": 9})
    axes[2].set_title(f"Composición Thigmotaxis\n(n={total_frames:,} frames)",
                      fontsize=10)
    fig.suptitle('La "Trampa de la Exactitud" — por qué el F1 es la métrica correcta',
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    save(fig, "fig6_trampa_exactitud")
    plt.close(fig)

    # ---- Fig 7: Conditional vs alternativas (todos los 26) ----
    orden_cond = ["SimBA RF", "B-SOiD", "Ensemble OR", "Conditional", "Dynamic"]
    fig, ax = plt.subplots(figsize=(13, 4.8))
    sns.barplot(data=g, x="video_short", y="f1", hue="metodo",
                order=orden_videos, hue_order=orden_cond,
                palette=PALETA, ax=ax, edgecolor="white")
    ax.set_title(f"Ensemble Condicional y estrategias dinámicas — Grooming (n={n_videos})")
    ax.set_xlabel("Video")
    ax.set_ylabel("F1 Grooming (validación ciega)")
    ax.set_ylim(0, 1.05)
    ax.tick_params(axis="x", rotation=45)
    for tl in ax.get_xticklabels():
        tl.set_horizontalalignment("right")
    mark_no_gt(ax, sin_gt_groom, "*")
    ax.legend(loc="upper right", frameon=True, fontsize=8, ncol=2)
    fig.text(0.5, -0.02,
             "* Videos sin Grooming positivo etiquetado en GT (F1=0 por definición).",
             ha="center", fontsize=8.5, style="italic", color="#c0392b")
    save(fig, "fig7_ensemble_condicional_M1")
    plt.close(fig)

    # ---- Fig 8: YOLO vs Clasificador ----
    f1_simba_t = t[t["model"] == "simba"]["f1"].mean()
    f1_cond_g = g[g["model"] == "conditional"]["f1"].mean()
    etapas = [
        ("YOLO Pose v4\n(tracking de\nkeypoints)", 0.995, "#2ca02c", "mAP50"),
        ("SimBA RF\n(Thigmotaxis,\nclasificación)", f1_simba_t, "#17becf", "F1"),
        ("SimBA Conditional\n(Grooming,\nclasificación)", f1_cond_g, "#9467bd", "F1"),
        ("SimBA RF\n(Grooming solo,\nclasificación)", f1_simba_g, "#1f77b4", "F1"),
    ]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    xs = np.arange(len(etapas))
    values = [e[1] for e in etapas]
    colors = [e[2] for e in etapas]
    bars = ax.bar(xs, values, color=colors, edgecolor="white", width=0.65)
    ax.set_xticks(xs)
    ax.set_xticklabels([e[0] for e in etapas], fontsize=9.5)
    ax.set_ylabel("Métrica (0-1)")
    ax.set_ylim(0, 1.08)
    ax.set_title("Pipeline en dos etapas — el tracking de pose es preciso;\n"
                 "la clasificación conductual es el bottleneck", fontsize=11.5)
    for bar, (_, val, _, metric_name) in zip(bars, etapas):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.015,
                f"{metric_name} = {val:.3f}",
                ha="center", fontsize=10, fontweight="bold")
    ax.axvline(0.5, color="gray", linestyle="--", linewidth=1.2, alpha=0.6)
    ax.text(0.0, 1.05, "Etapa 1: Pose", ha="center", fontsize=9,
            style="italic", color="#2ca02c")
    ax.text(2.0, 1.05, "Etapa 2: Conducta (LOO ciega, n=26)", ha="center",
            fontsize=9, style="italic", color="gray")
    save(fig, "fig8_yolo_vs_clasificador")
    plt.close(fig)

    # ---- Tabla resumen ----
    def resumen(df_sub, label_prefix, sin_gt):
        full = df_sub.groupby("metodo")["f1"].agg(["mean", "std", "count"]).round(3)
        full.columns = ["F1 promedio (n=26)", "Desv.Est", "n videos"]
        df_valid = df_sub[~df_sub["video_short"].isin(sin_gt)]
        fair = df_valid.groupby("metodo")["f1"].agg(["mean", "count"]).round(3)
        fair.columns = ["F1 promedio justo", "n efectivo"]
        merged = full.join(fair)
        merged = merged.reindex([m for m in orden_5 if m in merged.index])
        merged.index = [f"{label_prefix} " + i for i in merged.index]
        return merged
    tabla = pd.concat([resumen(g, "Grooming", sin_gt_groom),
                       resumen(t, "Thigmotaxis", sin_gt_thigmo)])
    tabla.to_csv(HERE / "tabla_resumen_loo.csv")
    print("\nTabla resumen N=26:")
    print(tabla.to_string())


if __name__ == "__main__":
    main()
