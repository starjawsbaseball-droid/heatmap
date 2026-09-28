# -*- coding: utf-8 -*-
"""Streamlit版 野球ゾーン別 打率・被打率ヒートマップ

CSVはアプリ内に埋め込まれているため、ファイルアップロードは不要です。
元の完成版 zone_heatmap_generator(1).py の集計ロジックをStreamlit向けに移植しています。
"""

import io
import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib import font_manager

# Streamlit Cloud（Linux）でもヒートマップ画像内の日本語を確実に描画するため、
# アプリに同梱した Noto Sans CJK JP をMatplotlibへ直接登録する。
FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT_REGULAR = FONT_DIR / "NotoSansCJK-Regular.ttc"
FONT_BOLD = FONT_DIR / "NotoSansCJK-Bold.ttc"

if FONT_REGULAR.exists():
    font_manager.fontManager.addfont(str(FONT_REGULAR))
if FONT_BOLD.exists():
    font_manager.fontManager.addfont(str(FONT_BOLD))

try:
    if FONT_REGULAR.exists():
        _jp_font = font_manager.FontProperties(fname=str(FONT_REGULAR))
        _jp_font_name = _jp_font.get_name()
        plt.rcParams["font.family"] = _jp_font_name
        plt.rcParams["font.sans-serif"] = [_jp_font_name]
    else:
        import japanize_matplotlib  # noqa: F401
except Exception:
    try:
        import japanize_matplotlib  # noqa: F401
    except Exception:
        pass

plt.rcParams["axes.unicode_minus"] = False


# ============================================================
# 埋め込みCSVデータ（ヒートマップ.csv）
# ============================================================
EMBEDDED_CSV = '投手名,打者名,ボールx座標,ボールy座標,結果,カテゴリ,日付,対戦相手\nSJ野田,JY阿部,-1.0,-0.5,B,中野区大会,2026/09/27,城山ヤンガース\nSJ野田,JY福島,0.0,-0.5,K,中野区大会,2026/09/27,城山ヤンガース\nSJ野田,JY小城,1.0,1.0,B,中野区大会,2026/09/27,城山ヤンガース\nSJ野田,JY窪田,0.0,0.0,0,中野区大会,2026/09/27,城山ヤンガース\nSJ野田,JY渡部,-0.5,0.0,K,中野区大会,2026/09/27,城山ヤンガース\nJY福島,SJ北見,1.0,1.0,B,中野区大会,2026/09/27,城山ヤンガース\nJY福島,SJ井川,-1.0,0.0,B,中野区大会,2026/09/27,城山ヤンガース\nJY福島,SJ高野,0.5,0.0,K,中野区大会,2026/09/27,城山ヤンガース\nJY福島,SJ有馬,-1.0,0.0,B,中野区大会,2026/09/27,城山ヤンガース\nJY福島,SJ齋藤,0.0,0.0,0,中野区大会,2026/09/27,城山ヤンガース\nJY福島,SJ野田,1.0,0.0,DB,中野区大会,2026/09/27,城山ヤンガース\nJY福島,SJ小川,0.5,0.0,4,中野区大会,2026/09/27,城山ヤンガース\nJY福島,SJ向,0.5,-1.0,B,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ鈴木,-1.0,0.5,DB,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ北見,0.0,-1.0,B,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ井川,0.0,-1.0,B,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ高野,-0.5,0.0,K,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ有馬,0.5,0.0,4,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ齋藤,0.5,0.0,4,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ野田,0.0,-1.0,B,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ小川,-0.5,-1.0,B,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ向,1.0,0.0,B,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ鈴木,0.5,0.0,K,中野区大会,2026/09/27,城山ヤンガース\nSJ野田,JY青山,0.0,1.0,K,中野区大会,2026/09/27,城山ヤンガース\nSJ野田,JY金井,0.0,0.0,K,中野区大会,2026/09/27,城山ヤンガース\nSJ野田,JY根橋,-0.5,0.0,K,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ北見,-0.5,-0.5,0,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ味澤,0.5,0.5,0,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ島居,0.5,0.0,1,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ門司,-1.0,-1.0,DB,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ齋藤,-1.0,0.0,B,中野区大会,2026/09/27,城山ヤンガース\nJY阿部,SJ深沢,0.5,0.5,K,中野区大会,2026/09/27,城山ヤンガース\nJY窪田,SJ小川,0.5,0.5,1,中野区大会,2026/09/27,城山ヤンガース\nJY窪田,SJ波形,-0.5,1.0,B,中野区大会,2026/09/27,城山ヤンガース\nJY窪田,SJ深沢,-0.5,0.0,4,中野区大会,2026/09/27,城山ヤンガース\nJY窪田,SJ北見,0.0,0.0,0,中野区大会,2026/09/27,城山ヤンガース\nJY窪田,SJ味澤,-1.0,-1.0,B,中野区大会,2026/09/27,城山ヤンガース\nJY窪田,SJ島居,0.0,0.0,1,中野区大会,2026/09/27,城山ヤンガース\nJY窪田,SJ門司,-1.0,-1.0,DB,中野区大会,2026/09/27,城山ヤンガース\nJY窪田,SJ齋藤,0.0,0.0,4,中野区大会,2026/09/27,城山ヤンガース\nJY窪田,SJ野田,0.5,0.0,0,中野区大会,2026/09/27,城山ヤンガース\nJY窪田,SJ小川,0.5,0.5,1,中野区大会,2026/09/27,城山ヤンガース\nJY窪田,SJ波形,0.0,-0.5,0,中野区大会,2026/09/27,城山ヤンガース\nSJ野田,JY瀧澤,-0.5,0.0,K,中野区大会,2026/09/27,城山ヤンガース\nSJ野田,JY阿部,-0.5,1.0,B,中野区大会,2026/09/27,城山ヤンガース\nSJ野田,JY小城,0.5,0.5,0,中野区大会,2026/09/27,城山ヤンガース\nSJ野田,JY窪田,0.0,0.0,0,中野区大会,2026/09/27,城山ヤンガース\nSJ齋藤,KR坂井響,0.5,0.0,1,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR古瀬,0.5,0.0,0,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR坂井奏,0.0,1.0,B,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR南谷,-0.5,0.0,0,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR福田,0.0,0.5,K,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ味澤,-1.0,0.0,K,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ有馬,0.0,0.5,1,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ齋藤,0.0,0.0,2,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ深沢,1.0,-1.0,K,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ島居,-0.5,0.0,0,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR宮下,-0.5,0.0,K,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR江渕,-0.5,0.0,1,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR金子,-0.5,0.0,SAC,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR小芸,0.0,1.0,K,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ野田,0.0,0.5,0,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ北見,0.0,0.0,1,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ波形,-0.5,0.0,SAC,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ門司,0.5,0.5,0,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR坂井響,1.0,0.0,1,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR古瀬,-0.5,-0.5,K,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR坂井奏 ,-0.5,0.0,0,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR南谷,0.0,0.0,1,城北大会,2026/09/27,梶山レッドスターズ\nSJ齋藤,KR福田,0.0,-0.5,K,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ味澤,0.5,0.0,0,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ有馬,1.0,0.0,0,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ齋藤,0.5,-0.5,0,城北大会,2026/09/27,梶山レッドスターズ\nSJ北見,KR宮下,-0.5,0.0,K,城北大会,2026/09/27,梶山レッドスターズ\nSJ北見,KR江渕,0.5,-0.5,K,城北大会,2026/09/27,梶山レッドスターズ\nSJ北見,KR金子,0.0,-0.5,0,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ深沢,-0.5,0.5,0,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ島居,0.0,0.0,0,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ野田,-1.0,0.0,K,城北大会,2026/09/27,梶山レッドスターズ\nSJ北見,KR小芸,-0.5,-0.5,K,城北大会,2026/09/27,梶山レッドスターズ\nSJ北見,KR坂井響,0.0,0.0,K,城北大会,2026/09/27,梶山レッドスターズ\nSJ北見,KR古瀬,0.0,-0.5,K,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ北見,0.0,0.0,0,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ小川,-0.5,0.0,0,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ門司,0.5,0.0,0,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ味澤,-1.0,-1.0,DB,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ有馬,1.0,-0.5,1,城北大会,2026/09/27,梶山レッドスターズ\nKR南谷,SJ齋藤,1.0,-0.5,0,城北大会,2026/09/27,梶山レッドスターズ\n'


# ============================================================
# 設定
# ============================================================
X_EDGES = [-1.0, -0.6, -0.2, 0.2, 0.6, 1.0]
Y_EDGES = [-1.0, -0.6, -0.2, 0.2, 0.6, 1.0]
STRIKE_X_MIN, STRIKE_X_MAX = -0.65, 0.65
STRIKE_Y_MIN, STRIKE_Y_MAX = -0.65, 0.65
FIGSIZE = (8, 8)
DPI = 180

AB_RESULTS = {"0", "1", "2", "3", "4", "K", "E", "BO", "BH", "BK"}
K_RESULTS = {"K", "BK"}
HIT_RESULTS = {"1", "2", "3", "4", "BH"}
VALID_RESULTS = AB_RESULTS | {"B", "DB", "SF", "SAC"}


# ============================================================
# データ処理
# ============================================================
def normalize_result(v):
    if pd.isna(v):
        return ""
    s = str(v).strip().upper()
    if s.endswith(".0") and s[:-2] in {"0", "1", "2", "3", "4"}:
        s = s[:-2]
    return s


@st.cache_data
def load_data():
    df = pd.read_csv(io.StringIO(EMBEDDED_CSV))
    return prepare(df)


def prepare(df):
    required = [
        "投手名", "打者名", "ボールx座標", "ボールy座標",
        "結果", "カテゴリ", "日付", "対戦相手"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("CSVに必要な列がありません: " + ", ".join(missing))

    w = df[required].copy()

    for c in ["投手名", "打者名", "カテゴリ", "対戦相手"]:
        w[c] = w[c].fillna("").astype(str).str.strip()

    w["ボールx座標"] = pd.to_numeric(w["ボールx座標"], errors="coerce")
    w["ボールy座標"] = pd.to_numeric(w["ボールy座標"], errors="coerce")
    w["結果"] = w["結果"].map(normalize_result)
    w["日付_dt"] = pd.to_datetime(w["日付"], errors="coerce")

    if w["日付_dt"].isna().any():
        n = int(w["日付_dt"].isna().sum())
        raise ValueError(f"日付を認識できない行が {n} 件あります。")

    bad = w["ボールx座標"].isna() | w["ボールy座標"].isna()
    if bad.any():
        raise ValueError(
            f"ボールx座標・y座標が数値でない行が {int(bad.sum())} 件あります。"
        )

    if (
        (w["投手名"] == "")
        | (w["打者名"] == "")
        | (w["カテゴリ"] == "")
        | (w["対戦相手"] == "")
    ).any():
        raise ValueError("投手名・打者名・カテゴリ・対戦相手には空欄を作らないでください。")

    unknown = sorted(set(w["結果"]) - VALID_RESULTS - {""})
    if unknown:
        raise ValueError("未対応の結果コード: " + ", ".join(unknown))

    if (w["結果"] == "").any():
        raise ValueError("結果が空欄の行があります。")

    inside = (
        w["ボールx座標"].between(X_EDGES[0], X_EDGES[-1])
        & w["ボールy座標"].between(Y_EDGES[0], Y_EDGES[-1])
    )
    w = w.loc[inside].copy()

    w["x_zone"] = pd.cut(
        w["ボールx座標"], X_EDGES, labels=False, include_lowest=True
    )
    w["y_zone"] = pd.cut(
        w["ボールy座標"], Y_EDGES, labels=False, include_lowest=True
    )
    w["AB"] = w["結果"].isin(AB_RESULTS).astype(int)
    w["H"] = w["結果"].isin(HIT_RESULTS).astype(int)
    w["K"] = w["結果"].isin(K_RESULTS).astype(int)
    return w


def stats(df):
    ab = int(df.AB.sum())
    h = int(df.H.sum())
    k = int(df.K.sum())
    return (h / ab if ab else np.nan), ab, h, k


# ============================================================
# ヒートマップ
# ============================================================
def make_heatmap(g, title, rate_label):
    ab = np.zeros((5, 5), dtype=int)
    h = np.zeros((5, 5), dtype=int)
    k = np.zeros((5, 5), dtype=int)

    z = (
        g.groupby(["y_zone", "x_zone"], observed=True)[["AB", "H", "K"]]
        .sum()
        .reset_index()
    )

    for _, r in z.iterrows():
        y, x = int(r.y_zone), int(r.x_zone)
        ab[y, x] = int(r.AB)
        h[y, x] = int(r.H)
        k[y, x] = int(r.K)

    rate = np.divide(
        h.astype(float),
        ab,
        out=np.full((5, 5), np.nan, dtype=float),
        where=ab > 0,
    )
    masked_rate = np.ma.masked_where(ab == 0, rate)

    cmap = plt.get_cmap("Reds").copy()
    cmap.set_bad(color="white", alpha=1.0)

    fig, ax = plt.subplots(figsize=FIGSIZE)

    im = ax.pcolormesh(
        X_EDGES,
        Y_EDGES,
        masked_rate,
        cmap=cmap,
        vmin=0,
        vmax=1,
        shading="flat",
    )

    for x in X_EDGES[1:-1]:
        ax.axvline(x, color="white", linewidth=1)
    for y in Y_EDGES[1:-1]:
        ax.axhline(y, color="white", linewidth=1)

    ax.add_patch(
        plt.Rectangle(
            (STRIKE_X_MIN, STRIKE_Y_MIN),
            STRIKE_X_MAX - STRIKE_X_MIN,
            STRIKE_Y_MAX - STRIKE_Y_MIN,
            fill=False,
            edgecolor="tab:blue",
            linewidth=2.5,
        )
    )

    xs = [(X_EDGES[i] + X_EDGES[i + 1]) / 2 for i in range(5)]
    ys = [(Y_EDGES[i] + Y_EDGES[i + 1]) / 2 for i in range(5)]

    for yi, yc in enumerate(ys):
        for xi, xc in enumerate(xs):
            rr = rate[yi, xi]
            txt = f"{rr:.3f}" if not np.isnan(rr) else "-"
            ax.text(
                xc, yc + 0.10, txt,
                ha="center", va="center",
                fontsize=12, fontweight="bold"
            )
            ax.text(
                xc, yc, f"AB={ab[yi, xi]}",
                ha="center", va="center", fontsize=10
            )
            ax.text(
                xc, yc - 0.10, f"K={k[yi, xi]}",
                ha="center", va="center", fontsize=10
            )

    overall, total_ab, total_h, total_k = stats(g)
    overall_txt = (
        f"{rate_label}：{overall:.3f}　AB={total_ab}　K={total_k}"
        if not np.isnan(overall)
        else f"{rate_label}：-　AB={total_ab}　K={total_k}"
    )

    ax.set_title(f"{title}\n{overall_txt}", fontsize=15, pad=14)
    ax.set_xlabel("ボールx座標")
    ax.set_ylabel("ボールy座標")
    ax.set_xlim(X_EDGES[0], X_EDGES[-1])
    ax.set_ylim(Y_EDGES[0], Y_EDGES[-1])
    ax.set_xticks(X_EDGES)
    ax.set_yticks(Y_EDGES)

    cbar = fig.colorbar(im, ax=ax, fraction=.06, pad=.04)
    cbar.set_label(rate_label)

    plt.tight_layout()
    return fig


# ============================================================
# Streamlit UI
# ============================================================
st.set_page_config(
    page_title="野球ゾーン別 打率・被打率ヒートマップ",
    layout="wide",
)

st.title("⚾ 野球ゾーン別 打率・被打率ヒートマップ")
st.caption("ヒートマップ.csv のデータをアプリ内に埋め込んでいます。CSVアップロードは不要です。")

try:
    df = load_data()
except Exception as e:
    st.error(str(e))
    st.stop()

# サイドバー
st.sidebar.header("分析条件")

categories = sorted(df["カテゴリ"].unique().tolist())
opponents = sorted(df["対戦相手"].unique().tolist())
players_batter = sorted(df["打者名"].unique().tolist())
players_pitcher = sorted(df["投手名"].unique().tolist())

selected_categories = st.sidebar.multiselect(
    "カテゴリ（複数選択可）",
    categories,
    default=categories,
)

selected_opponents = st.sidebar.multiselect(
    "対戦相手（複数選択可）",
    opponents,
    default=opponents,
)

min_date = df["日付_dt"].min().date()
max_date = df["日付_dt"].max().date()

date_range = st.sidebar.date_input(
    "日付範囲",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

filtered = df.copy()

if selected_categories:
    filtered = filtered[filtered["カテゴリ"].isin(selected_categories)]
else:
    filtered = filtered.iloc[0:0]

if selected_opponents:
    filtered = filtered[filtered["対戦相手"].isin(selected_opponents)]
else:
    filtered = filtered.iloc[0:0]

filtered = filtered[
    (filtered["日付_dt"].dt.date >= start_date)
    & (filtered["日付_dt"].dt.date <= end_date)
]

st.sidebar.markdown("---")
st.sidebar.write(f"全データ: **{len(df):,}件**")
st.sidebar.write(f"分析対象: **{len(filtered):,}件**")

if filtered.empty:
    st.warning("指定した条件に該当するデータがありません。")
    st.stop()

# 統計
overall, total_ab, total_h, total_k = stats(filtered)
m1, m2, m3, m4 = st.columns(4)
m1.metric("分析件数", f"{len(filtered):,}")
m2.metric("AB", f"{total_ab:,}")
m3.metric("安打", f"{total_h:,}")
m4.metric("打率 / 被打率", "-" if np.isnan(overall) else f"{overall:.3f}")

st.markdown(
    f"**条件:** カテゴリ = {'、'.join(selected_categories)} / "
    f"対戦相手 = {'、'.join(selected_opponents)} / "
    f"{start_date} ～ {end_date}"
)

# タブ
tab_batter, tab_pitcher, tab_data = st.tabs(
    ["打者別 打率", "投手別 被打率", "分析対象データ"]
)

with tab_batter:
    batter_options = sorted(filtered["打者名"].dropna().unique().tolist())
    default_batters = [name for name in batter_options if str(name).startswith("SJ")]
    selected_batters = st.multiselect(
        "表示する打者（複数選択可）",
        batter_options,
        default=default_batters,
        key="batters",
    )
    batter_cols = st.slider(
        "1行あたりの人数",
        min_value=1,
        max_value=4,
        value=3,
        key="batter_cols",
    )

    if not selected_batters:
        st.info("表示する打者を選択してください。")
    else:
        for start in range(0, len(selected_batters), batter_cols):
            row_names = selected_batters[start:start + batter_cols]
            cols = st.columns(batter_cols)
            for col, batter in zip(cols, row_names):
                with col:
                    g = filtered[filtered["打者名"] == batter]
                    avg, ab, h, k = stats(g)
                    st.markdown(
                        f"**{batter}**  \n"
                        f"打率 **{avg:.3f}**　AB={ab}　安打={h}　K={k}"
                    )
                    fig = make_heatmap(g, batter, "打率")
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)

with tab_pitcher:
    pitcher_options = sorted(filtered["投手名"].dropna().unique().tolist())
    default_pitchers = [name for name in pitcher_options if str(name).startswith("SJ")]
    selected_pitchers = st.multiselect(
        "表示する投手（複数選択可）",
        pitcher_options,
        default=default_pitchers,
        key="pitchers",
    )
    pitcher_cols = st.slider(
        "1行あたりの人数",
        min_value=1,
        max_value=4,
        value=3,
        key="pitcher_cols",
    )

    if not selected_pitchers:
        st.info("表示する投手を選択してください。")
    else:
        for start in range(0, len(selected_pitchers), pitcher_cols):
            row_names = selected_pitchers[start:start + pitcher_cols]
            cols = st.columns(pitcher_cols)
            for col, pitcher in zip(cols, row_names):
                with col:
                    g = filtered[filtered["投手名"] == pitcher]
                    avg, ab, h, k = stats(g)
                    st.markdown(
                        f"**{pitcher}**  \n"
                        f"被打率 **{avg:.3f}**　AB={ab}　被安打={h}　K={k}"
                    )
                    fig = make_heatmap(g, pitcher, "被打率")
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)

with tab_data:
    st.subheader("分析対象データ")
    display_cols = [
        "投手名", "打者名", "ボールx座標", "ボールy座標",
        "結果", "カテゴリ", "日付", "対戦相手"
    ]
    st.dataframe(
        filtered[display_cols].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )

    csv_download = filtered[display_cols].to_csv(
        index=False, encoding="utf-8-sig"
    )
    st.download_button(
        "分析対象データをCSVでダウンロード",
        data=csv_download,
        file_name="分析対象データ.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption(
    "AB=0（B・DB・SF・SAC）のゾーンはデータなしとして白表示。"
    " BHは安打、BOはAB、BKはABかつ三振として計算。"
)
