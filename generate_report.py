"""
generate_report.py
------------------
PsySafe Weakness Report 생성 스크립트
실험 결과를 바탕으로 시각화 포함 HTML 리포트를 생성합니다.

Usage:
    python generate_report.py
    python generate_report.py --output results/report.html
"""

import argparse
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import base64
from io import BytesIO

# ── 공통 스타일 ────────────────────────────────────────────────────────────────
COLORS = {
    "condA_full":          "#D62728",
    "condB_prefix_only":   "#FF7F0E",
    "condC_icl_only":      "#BCBD22",
    "condD_baseline":      "#17BECF",
    "condE_traits_only":   "#9467BD",
}
COND_LABELS = {
    "condA_full":          "A: Full PsySafe\n(dark+prefix+ICL)",
    "condB_prefix_only":   "B: Prefix+ICL\n(no dark traits)",
    "condC_icl_only":      "C: ICL only\n(no dark traits)",
    "condD_baseline":      "D: Baseline\n(all OFF)",
    "condE_traits_only":   "E: Traits only\n(no prefix/ICL)",
}
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})


def fig_to_b64(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


# ── 그래프 1: 조건별 Dangerous Rate ────────────────────────────────────────────
def plot_conditions(df) -> str:
    orig = df[df["stripped"] == False]
    conditions = ["condA_full", "condB_prefix_only", "condC_icl_only",
                  "condD_baseline", "condE_traits_only"]
    agents = ["AI_planner", "Coder"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    fig.suptitle("Figure 1. Dangerous Rate by Condition (Original)", fontweight="bold", fontsize=13)

    for ax, agent in zip(axes, agents):
        col = f"{agent}_dangerous"
        rates = []
        for c in conditions:
            sub = orig[(orig["condition"] == c) & (orig[col].isin([0, 1]))]
            rates.append(sub[col].mean() if len(sub) > 0 else 0)

        bars = ax.bar(range(len(conditions)), rates,
                      color=[COLORS[c] for c in conditions], alpha=0.85, edgecolor="white")
        ax.set_xticks(range(len(conditions)))
        ax.set_xticklabels([COND_LABELS[c] for c in conditions], fontsize=8.5)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Dangerous Rate")
        ax.set_title(f"{agent}")
        for bar, rate in zip(bars, rates):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                    f"{rate:.1%}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    plt.tight_layout()
    b64 = fig_to_b64(fig)
    plt.close(fig)
    return b64


# ── 그래프 2: condA vs condE (Prefix 효과) ─────────────────────────────────────
def plot_prefix_effect(df) -> str:
    orig = df[df["stripped"] == False]
    target = orig[orig["condition"].isin(["condA_full", "condE_traits_only"])]

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    fig.suptitle("Figure 2. Prefix Effect: condA vs condE", fontweight="bold", fontsize=13)

    for ax, agent in zip(axes, ["AI_planner", "Coder"]):
        col = f"{agent}_dangerous"
        conds = ["condA_full", "condE_traits_only"]
        rates = [target[(target["condition"] == c) & (target[col].isin([0, 1]))][col].mean()
                 for c in conds]
        labels = ["A: Full PsySafe\n(prefix ON)", "E: Traits only\n(prefix OFF)"]
        colors = [COLORS["condA_full"], COLORS["condE_traits_only"]]

        bars = ax.bar(labels, rates, color=colors, alpha=0.85, width=0.45, edgecolor="white")
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("Dangerous Rate")
        ax.set_title(f"{agent}")

        # 차이 화살표
        diff = rates[1] - rates[0]
        arrow_x = 0.5
        ax.annotate("", xy=(1, rates[1] + 0.03), xytext=(0, rates[0] + 0.03),
                    arrowprops=dict(arrowstyle="->", color="black", lw=1.5),
                    xycoords=("data", "data"))
        ax.text(0.5, max(rates) + 0.08, f"Δ={diff:+.1%}", ha="center",
                fontsize=10, color="red" if diff > 0 else "green", fontweight="bold",
                transform=ax.get_xaxis_transform())

        for bar, rate in zip(bars, rates):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                    f"{rate:.1%}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.tight_layout()
    b64 = fig_to_b64(fig)
    plt.close(fig)
    return b64


# ── 그래프 3: Original vs Stripped (Judge 편향 검증) ───────────────────────────
def plot_strip_effect(df) -> str:
    condA = df[df["condition"] == "condA_full"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    fig.suptitle("Figure 3. Judge Bias Test: Original vs Prefix-Stripped (condA)",
                 fontweight="bold", fontsize=13)

    for ax, agent in zip(axes, ["AI_planner", "Coder"]):
        col = f"{agent}_dangerous"
        rates = [condA[(condA["stripped"] == s) & (condA[col].isin([0, 1]))][col].mean()
                 for s in [False, True]]
        labels = ["Original\n(with prefix)", "Stripped\n(prefix removed)"]

        bars = ax.bar(labels, rates, color=["#4C72B0", "#DD8452"],
                      alpha=0.85, width=0.4, edgecolor="white")
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("Dangerous Rate")
        ax.set_title(f"{agent}")
        diff = rates[1] - rates[0]
        ax.text(0.5, max(rates) + 0.07, f"Δ={diff:+.1%}", ha="center",
                fontsize=10, color="gray", fontweight="bold",
                transform=ax.get_xaxis_transform())
        for bar, rate in zip(bars, rates):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                    f"{rate:.1%}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.tight_layout()
    b64 = fig_to_b64(fig)
    plt.close(fig)
    return b64


# ── 그래프 4: 라운드별 감소 추이 ────────────────────────────────────────────────
def plot_round_trend(df) -> str:
    orig = df[df["stripped"] == False]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Figure 4. Dangerous Rate Trend by Round", fontweight="bold", fontsize=13)

    for ax, agent in zip(axes, ["AI_planner", "Coder"]):
        col = f"{agent}_dangerous"
        for cond in ["condA_full", "condE_traits_only"]:
            sub = orig[(orig["condition"] == cond) & (orig[col].isin([0, 1]))]
            trend = sub.groupby("round")[col].mean()
            ax.plot(trend.index, trend.values, marker="o",
                    color=COLORS[cond], label=COND_LABELS[cond].split("\n")[0], linewidth=2)

        ax.set_xlabel("Round")
        ax.set_ylabel("Dangerous Rate")
        ax.set_title(f"{agent}")
        ax.set_ylim(0, 1.05)
        ax.set_xticks([0, 1, 2])
        ax.legend(fontsize=9)

    plt.tight_layout()
    b64 = fig_to_b64(fig)
    plt.close(fig)
    return b64


# ── 그래프 5: Multi-Judge 비교 ─────────────────────────────────────────────────
def plot_multijudge(df_35) -> str:
    import os

    def load_eval(base_path, cond_map):
        frames = []
        for cond_dir, cond_name in cond_map.items():
            path = os.path.join(base_path, cond_dir)
            if not os.path.exists(path):
                continue
            for f in os.listdir(path):
                if not f.endswith(".xlsx"):
                    continue
                df = pd.read_excel(os.path.join(path, f), index_col=0)
                if not df.empty:
                    df["condition"] = cond_name
                    frames.append(df)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    cond_map = {
        "try1/hi_traits_debate": "condA_full",
        "exp_condE_traits_only/exp_condE_traits_only": "condE_traits_only",
    }

    df_4m = load_eval("workdir_eval/gpt_4o_mini", cond_map)
    df_cl = load_eval("workdir_eval/claude_haiku_4_5_20251001", cond_map)

    judges = ["gpt-3.5-turbo", "gpt-4o-mini", "claude-haiku-4-5"]
    judge_dfs = {
        "gpt-3.5-turbo": df_35,
        "gpt-4o-mini": df_4m,
        "claude-haiku-4-5": df_cl,
    }
    judge_colors = ["#4C72B0", "#DD8452", "#55A868"]

    conds = ["condA_full", "condE_traits_only"]
    cond_labels = ["A: Full PsySafe", "E: Traits only"]
    x = np.arange(len(conds))
    width = 0.25

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Figure 5. Multi-Judge Comparison: Dangerous Rate by Judge Model",
                 fontweight="bold", fontsize=13)

    for ax, agent in zip(axes, ["AI_planner", "Coder"]):
        col = f"{agent}_dangerous"
        for i, (judge, color) in enumerate(zip(judges, judge_colors)):
            df_j = judge_dfs[judge]
            rates = [df_j[(df_j["condition"] == c) & (df_j[col].isin([0, 1]))][col].mean()
                     for c in conds]
            bars = ax.bar(x + i * width, rates, width, label=judge,
                          color=color, alpha=0.85, edgecolor="white")
            for bar, rate in zip(bars, rates):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                        f"{rate:.0%}", ha="center", va="bottom", fontsize=8)

        ax.set_xticks(x + width)
        ax.set_xticklabels(cond_labels)
        ax.set_ylim(0, 1.15)
        ax.set_ylabel("Dangerous Rate")
        ax.set_title(f"{agent}")
        ax.legend(fontsize=9)

    plt.tight_layout()
    b64 = fig_to_b64(fig)
    plt.close(fig)
    return b64


# ── 그래프 6: Judge Weakness 전용 — Heatmap + 편차 ───────────────────────────
def plot_judge_weakness() -> str:
    import os

    def load_eval(base_path, cond_map):
        frames = []
        for cond_dir, cond_name in cond_map.items():
            path = os.path.join(base_path, cond_dir)
            if not os.path.exists(path):
                continue
            for f in os.listdir(path):
                if not f.endswith(".xlsx"):
                    continue
                df = pd.read_excel(os.path.join(path, f), index_col=0)
                if not df.empty:
                    df["condition"] = cond_name
                    frames.append(df)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    cond_map = {
        "try1/hi_traits_debate": "condA_full",
        "exp_condE_traits_only/exp_condE_traits_only": "condE_traits_only",
    }
    df_35 = pd.read_excel("results/ablation_summary.xlsx")
    df_35 = df_35[(df_35["stripped"] == False) &
                  df_35["condition"].isin(["condA_full", "condE_traits_only"])].copy()
    df_4m = load_eval("workdir_eval/gpt_4o_mini", cond_map)
    df_cl = load_eval("workdir_eval/claude_haiku_4_5_20251001", cond_map)

    judges     = ["gpt-3.5-turbo", "gpt-4o-mini", "claude-haiku-4-5"]
    judge_dfs  = {"gpt-3.5-turbo": df_35, "gpt-4o-mini": df_4m, "claude-haiku-4-5": df_cl}
    judge_colors = ["#4C72B0", "#DD8452", "#55A868"]
    conds      = ["condA_full", "condE_traits_only"]
    cond_short = ["A: Full\nPsySafe", "E: Traits\nonly"]
    agents     = ["AI_planner", "Coder"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Figure 6. Weakness 2: Judge Model Reliability Analysis",
                 fontweight="bold", fontsize=13)

    # ── 왼쪽: Heatmap (judge × condition·agent) ──────────────────────────────
    ax = axes[0]
    rate_matrix = np.zeros((len(judges), len(conds) * len(agents)))
    col_labels = []
    for ci, cond in enumerate(conds):
        for ai, agent in enumerate(agents):
            col_labels.append(f"{cond_short[ci]}\n({agent})")
            col = f"{agent}_dangerous"
            for ji, judge in enumerate(judges):
                df_j = judge_dfs[judge]
                v = df_j[(df_j["condition"] == cond) & (df_j[col].isin([0, 1]))][col].mean()
                rate_matrix[ji, ci * len(agents) + ai] = v

    im = ax.imshow(rate_matrix, cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, fontsize=8.5)
    ax.set_yticks(range(len(judges)))
    ax.set_yticklabels(judges, fontsize=9)
    ax.set_title("Dangerous Rate Heatmap\n(judge × condition·agent)", fontsize=10)
    for ji in range(len(judges)):
        for ci in range(len(col_labels)):
            val = rate_matrix[ji, ci]
            ax.text(ci, ji, f"{val:.1%}", ha="center", va="center",
                    fontsize=9, fontweight="bold",
                    color="white" if val > 0.6 or val < 0.15 else "black")
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)

    # ── 오른쪽: Judge 간 최대-최소 편차 (범위 막대) ─────────────────────────
    ax2 = axes[1]
    labels, means, mins_, maxs_ = [], [], [], []
    for cond, cs in zip(conds, cond_short):
        for agent in agents:
            col = f"{agent}_dangerous"
            rates = []
            for judge in judges:
                df_j = judge_dfs[judge]
                v = df_j[(df_j["condition"] == cond) & (df_j[col].isin([0, 1]))][col].mean()
                rates.append(v)
            labels.append(f"{cs}\n({agent})")
            means.append(np.mean(rates))
            mins_.append(np.min(rates))
            maxs_.append(np.max(rates))

    x = np.arange(len(labels))
    ax2.bar(x, means, color="#4C72B0", alpha=0.7, label="Mean across judges", edgecolor="white")
    ax2.errorbar(x, means,
                 yerr=[np.array(means) - np.array(mins_),
                       np.array(maxs_) - np.array(means)],
                 fmt="none", color="#D62728", capsize=6, linewidth=2, label="Min-Max range")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8.5)
    ax2.set_ylim(0, 1.1)
    ax2.set_ylabel("Dangerous Rate")
    ax2.set_title("Inter-Judge Variance\n(mean ± min/max range)", fontsize=10)
    ax2.legend(fontsize=8)

    for i, (m, lo, hi) in enumerate(zip(means, mins_, maxs_)):
        ax2.text(i, hi + 0.03, f"Δ={hi-lo:.1%}", ha="center", fontsize=8,
                 color="#D62728", fontweight="bold")

    plt.tight_layout()
    b64 = fig_to_b64(fig)
    plt.close(fig)
    return b64


# ── HTML 리포트 생성 ───────────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PsySafe Weakness Report</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 960px; margin: 40px auto;
          padding: 0 24px; color: #222; line-height: 1.7; background: #fafafa; }}
  h1   {{ font-size: 1.9em; border-bottom: 3px solid #D62728; padding-bottom: 8px; color: #D62728; }}
  h2   {{ font-size: 1.4em; margin-top: 48px; border-left: 5px solid #4C72B0;
          padding-left: 12px; color: #1a1a2e; }}
  h3   {{ font-size: 1.15em; color: #333; margin-top: 28px; }}
  .abstract {{ background: #f0f4ff; border-radius: 8px; padding: 18px 24px;
               margin: 20px 0; font-style: italic; }}
  .weakness {{ background: #fff4f4; border-left: 4px solid #D62728;
               border-radius: 4px; padding: 14px 20px; margin: 16px 0; }}
  .finding  {{ background: #f0fff4; border-left: 4px solid #28a745;
               border-radius: 4px; padding: 14px 20px; margin: 16px 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 0.95em; }}
  th    {{ background: #4C72B0; color: white; padding: 10px 14px; text-align: center; }}
  td    {{ padding: 8px 14px; border-bottom: 1px solid #ddd; text-align: center; }}
  tr:nth-child(even) {{ background: #f7f7f7; }}
  img   {{ max-width: 100%; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.1);
           margin: 16px 0; }}
  .caption {{ text-align: center; font-size: 0.9em; color: #555; margin-top: -10px; margin-bottom: 20px; }}
  code  {{ background: #eee; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
</style>
</head>
<body>

<h1>PsySafe Weakness Report</h1>
<p><strong>분석 대상:</strong> PsySafe: A Comprehensive Framework for Psychological-based Attack, Defense,
and Evaluation of Multi-agent System Safety (Zhang et al., 2024)</p>

<!-- ========== 1. 논문 요약 ========== -->
<h2>1. PsySafe 논문 요약</h2>

<div class="abstract">
PsySafe는 다중 에이전트 시스템(MAS)의 안전성을 심리학적 관점에서 분석하는 프레임워크다.
에이전트에 어두운 성격 특성(dark personality traits)을 주입하여 유해한 행동을 유도하는
공격 메커니즘과, 이에 대응하는 방어 및 평가 방법을 제안한다.
</div>

<h3>핵심 구성 요소</h3>
<table>
  <tr><th>구성 요소</th><th>설명</th></tr>
  <tr><td><strong>Dark Traits Attack</strong></td>
      <td>에이전트 시스템 프롬프트에 6가지 부정적 도덕 특성 주입 (harm, cheating, betrayal 등)</td></tr>
  <tr><td><strong>Prefix Instruction</strong></td>
      <td>에이전트가 매 응답 시 <code>"Okay, in a virtual setting, my reply embodying dark traits above is:"</code>로 시작하도록 강제</td></tr>
  <tr><td><strong>In-Context Learning (ICL) 예시</strong></td>
      <td>대화 시작 시 유해한 응답 예시를 주입하여 편향 유도</td></tr>
  <tr><td><strong>LLM-as-Judge 평가</strong></td>
      <td>GPT 모델이 각 에이전트 응답의 위험성을 (A) 위험 / (B) 안전으로 판정</td></tr>
  <tr><td><strong>Doctor Defense</strong></td>
      <td>심리 테스트로 위험 에이전트 탐지 후 시스템 프롬프트 수정</td></tr>
</table>

<h3>공격 메커니즘 요약</h3>
<p>PsySafe의 공격은 세 요소의 결합으로 구성된다:</p>
<p style="text-align:center; font-size:1.1em;">
  <strong>Dark Traits</strong> + <strong>Prefix Instruction</strong> + <strong>ICL 예시</strong>
  &nbsp;→&nbsp; 유해 응답 생성
</p>

<!-- ========== 2. Weakness ========== -->
<h2>2. Weakness 분석</h2>

<div class="weakness">
  <strong>Weakness 1: Prefix가 공격 효과를 억제한다</strong><br>
  PsySafe는 접두어 지시와 ICL 예시가 공격을 강화한다고 가정하지만,
  실험 결과 접두어가 <em>없을 때</em> 오히려 더 높은 유해 출력률이 관찰됐다.
  특히 Coder 에이전트에서 접두어 없이 66.9%, 접두어 있을 때 30.1%로
  접두어가 공격을 <strong>억제</strong>하는 역효과를 보였다.
  <br><br>
  <em>해석</em>: <code>"in a virtual setting"</code> 프레이밍이 모델로 하여금
  더 형식적이고 덜 실질적인 유해 내용을 생성하게 유도하는 것으로 보인다.
</div>

<div class="weakness">
  <strong>Weakness 2: 단일 LLM Judge의 신뢰성</strong><br>
  PsySafe는 GPT 단일 모델을 judge로 사용하여 위험도를 평가한다.
  Judge 모델의 선택에 따라 평가 결과가 크게 달라질 수 있으며,
  이는 평가 지표의 신뢰성을 저하시킨다.
  다양한 judge 모델(GPT-4o-mini, Claude 등)을 활용한 비교 실험으로 이를 검증했다.
</div>

<!-- ========== 3. 실험 내용 및 결과 ========== -->
<h2>3. 실험 내용 및 결과</h2>

<h3>3.1 실험 설계 (2×2 Ablation)</h3>
<p>Dark traits, Prefix Instruction, ICL 예시 각 요소의 기여도를 분리하기 위해
5가지 조건으로 ablation 실험을 설계했다.</p>

<table>
  <tr><th>조건</th><th>Dark Traits</th><th>Prefix 지시</th><th>ICL 예시</th><th>목적</th></tr>
  <tr><td><strong>A</strong> Full PsySafe</td><td>✅</td><td>✅</td><td>✅</td><td>논문 원본 설정</td></tr>
  <tr><td><strong>B</strong> Prefix+ICL only</td><td>❌</td><td>✅</td><td>✅</td><td>Prefix·ICL 단독 효과</td></tr>
  <tr><td><strong>C</strong> ICL only</td><td>❌</td><td>❌</td><td>✅</td><td>ICL 단독 효과</td></tr>
  <tr><td><strong>D</strong> Baseline</td><td>❌</td><td>❌</td><td>❌</td><td>기준선</td></tr>
  <tr><td><strong>E</strong> Dark traits only</td><td>✅</td><td>❌</td><td>❌</td><td>Dark traits 단독 효과</td></tr>
</table>

<h3>3.2 전체 조건별 결과</h3>
<table>
  <tr><th>조건</th><th>AI_planner Dangerous Rate</th><th>Coder Dangerous Rate</th></tr>
  <tr><td>A: Full PsySafe</td><td>90.7%</td><td>30.1%</td></tr>
  <tr><td>B: Prefix+ICL (no dark traits)</td><td>0.0%</td><td>0.0%</td></tr>
  <tr><td>C: ICL only (no dark traits)</td><td>0.0%</td><td>0.0%</td></tr>
  <tr><td>D: Baseline</td><td>0.0%</td><td>0.3%</td></tr>
  <tr style="background:#fff0f0"><td><strong>E: Dark traits only</strong></td><td><strong>94.7%</strong></td><td><strong>66.9%</strong></td></tr>
</table>

<img src="data:image/png;base64,{fig1}" alt="Figure 1">
<p class="caption">Figure 1. 조건별 Dangerous Rate — B/C/D는 0%에 가까워 Dark traits가 핵심 공격 요인임을 확인</p>

<h3>3.3 Weakness 1: Prefix의 역효과 (condA vs condE)</h3>
<p>접두어가 있는 condA와 접두어가 없는 condE를 직접 비교했다.
Coder에서 접두어 제거 시 dangerous rate가 <strong>+36.8%p</strong> 상승했다.</p>

<img src="data:image/png;base64,{fig2}" alt="Figure 2">
<p class="caption">Figure 2. Prefix 유무에 따른 Dangerous Rate 변화 — 접두어가 오히려 공격을 억제</p>

<h3>3.4 Judge 편향 검증: Original vs Prefix-Stripped</h3>
<p>접두어가 GPT judge의 판단을 편향시키는지 확인하기 위해, 접두어를 정규식으로 제거한 버전과
원본의 평가 결과를 비교했다.</p>

<img src="data:image/png;base64,{fig3}" alt="Figure 3">
<p class="caption">Figure 3. Original vs Stripped 비교 — 차이가 거의 없어 GPT judge는 접두어 fictional framing에 영향받지 않음</p>

<h3>3.5 라운드별 Dangerous Rate 추이</h3>
<p>대화가 진행될수록 condA(접두어 있음)의 dangerous rate 감소폭이 condE(접두어 없음)보다 크다.
접두어가 있을 때 모델이 대화 맥락을 학습하면서 점차 안전하게 응답하는 경향이 강해진다.</p>

<img src="data:image/png;base64,{fig4}" alt="Figure 4">
<p class="caption">Figure 4. 라운드별 Dangerous Rate 감소 — condA는 라운드가 길어질수록 더 빠르게 감소</p>

<h3>3.6 Weakness 2: Multi-Judge 비교 (GPT-3.5 / GPT-4o-mini / Claude-Haiku)</h3>
<p>단일 judge 모델(GPT-3.5-turbo) 의존성이 평가 신뢰성을 저하시킬 수 있다는 가설을 검증하기 위해
GPT-4o-mini와 Claude-Haiku를 추가 judge로 활용했다.</p>

<table>
  <tr><th>조건</th><th>에이전트</th><th>gpt-3.5-turbo</th><th>gpt-4o-mini</th><th>claude-haiku-4-5</th><th>최대 차이</th></tr>
  <tr><td>A: Full PsySafe</td><td>AI_planner</td><td>90.7%</td><td>90.7%</td><td>90.1%</td><td>0.6%p</td></tr>
  <tr><td>A: Full PsySafe</td><td>Coder</td><td>30.1%</td><td>28.3%</td><td>26.7%</td><td>3.4%p</td></tr>
  <tr><td>E: Traits only</td><td>AI_planner</td><td>94.7%</td><td>93.3%</td><td>94.4%</td><td>1.4%p</td></tr>
  <tr><td>E: Traits only</td><td>Coder</td><td>66.9%</td><td>65.9%</td><td>67.2%</td><td>1.3%p</td></tr>
</table>

<img src="data:image/png;base64,{fig5}" alt="Figure 5">
<p class="caption">Figure 5. Judge 모델별 Dangerous Rate — 최대 3.4%p 차이로 judge 모델 간 일관성은 높으나,
condA vs condE의 차이(특히 Coder)는 모든 judge에서 일관되게 재현됨</p>

<img src="data:image/png;base64,{fig6}" alt="Figure 6">
<p class="caption">Figure 6. (좌) Judge × 조건별 Dangerous Rate Heatmap — 색이 진할수록 위험도 높음.
(우) Judge 간 Min-Max 편차 — Coder/condA에서 최대 3.4%p 편차 존재.
단일 judge 의존 시 이 편차만큼의 평가 불확실성이 존재함</p>

<!-- ========== 4. 결론 ========== -->
<h2>4. 결론</h2>

<div class="finding">
  <strong>Finding 1 (Weakness 1 증명)</strong><br>
  PsySafe의 Prefix Instruction은 공격을 강화하는 것이 아니라 오히려 억제한다.
  Dark traits 단독(condE)이 Full PsySafe(condA)보다 Coder 기준 <strong>+36.8%p</strong> 높은
  dangerous rate를 기록했다. 이는 <em>"in a virtual setting"</em> 프레이밍이
  모델의 실질적 유해 출력을 줄이는 방향으로 작용하기 때문으로 해석된다.
</div>

<div class="finding">
  <strong>Finding 2 (Judge 편향 없음 — Stripped 검증)</strong><br>
  접두어를 제거한 stripped 버전과 원본의 dangerous rate 차이가 ±0.3%p 이내로
  GPT judge는 fictional framing(<em>"in a virtual setting"</em>)에 편향되지 않음을 확인했다.
</div>

<div class="finding">
  <strong>Finding 4 (Multi-Judge 일관성 — Weakness 2 부분 반증)</strong><br>
  GPT-3.5-turbo, GPT-4o-mini, Claude-Haiku 3개 judge 모델 간 최대 차이는 <strong>3.4%p</strong>로,
  judge 모델 선택에 의한 편향은 이번 실험 범위에서는 크지 않았다.
  그러나 condA vs condE의 차이(Coder 기준 ~37%p)는 모든 judge에서 일관되게 재현되어
  <strong>Weakness 1의 robustness를 오히려 강화</strong>하는 결과가 됐다.
  Gemini 등 추가 계열 모델로 검증 범위를 확장할 필요가 있다.
</div>

<div class="finding">
  <strong>Finding 3 (Dark Traits가 핵심)</strong><br>
  B/C/D 조건이 모두 0%에 가까운 dangerous rate를 보여,
  PsySafe의 공격 효과는 접두어·ICL이 아닌 <strong>dark traits 주입</strong>에서 비롯된다.
  접두어 메커니즘에 대한 논문의 이론적 정당화는 재검토가 필요하다.
</div>

<hr>
<p style="color:#888; font-size:0.85em;">Generated by PsySafe Weakness Analysis Pipeline · {date}</p>
</body>
</html>
"""


def main(output_path: str):
    df = pd.read_excel("results/ablation_summary.xlsx")
    df_orig = df[df["stripped"] == False]

    print("그래프 생성 중...")
    fig1 = plot_conditions(df)
    fig2 = plot_prefix_effect(df)
    fig3 = plot_strip_effect(df)
    fig4 = plot_round_trend(df)
    fig5 = plot_multijudge(df_orig[df_orig["condition"].isin(["condA_full", "condE_traits_only"])].copy())
    fig6 = plot_judge_weakness()

    from datetime import date
    html = HTML_TEMPLATE.format(
        fig1=fig1, fig2=fig2, fig3=fig3, fig4=fig4, fig5=fig5, fig6=fig6,
        date=date.today().strftime("%Y-%m-%d")
    )

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"리포트 저장 완료 → {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/psysafe_weakness_report.html")
    args = parser.parse_args()
    main(args.output)
