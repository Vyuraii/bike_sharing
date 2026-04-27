import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bike Sharing Dashboard",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .section-header {
        background: linear-gradient(90deg, #1565C0, #42A5F5);
        color: white;
        padding: 8px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ── Load & Prepare Data ───────────────────────────────────────────────────────
@st.cache_data
def load_data():
    day_df  = pd.read_csv("main_data.csv")
    hour_df = pd.read_csv("hour_data.csv")

    for df in [day_df, hour_df]:
        df["dteday"] = pd.to_datetime(df["dteday"])

    season_map  = {1:"Spring", 2:"Summer", 3:"Fall", 4:"Winter"}
    weather_map = {1:"Clear/Partly Cloudy", 2:"Mist/Cloudy",
                   3:"Light Rain/Snow",     4:"Heavy Rain/Snow"}
    weekday_map = {0:"Sunday",1:"Monday",2:"Tuesday",3:"Wednesday",
                   4:"Thursday",5:"Friday",6:"Saturday"}
    month_map   = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

    for df in [day_df, hour_df]:
        df["season_label"]     = df["season"].map(season_map)
        df["weather_label"]    = df["weathersit"].map(weather_map)
        df["weekday_label"]    = df["weekday"].map(weekday_map)
        df["yr_label"]         = df["yr"].map({0:"2011", 1:"2012"})
        df["workingday_label"] = df["workingday"].map({0:"Non-Working Day", 1:"Working Day"})
        df["mnth_label"]       = df["mnth"].map(month_map)

    # Fix hum = 0
    median_hum = hour_df[hour_df["hum"] > 0]["hum"].median()
    hour_df.loc[hour_df["hum"] == 0, "hum"] = median_hum

    # Clustering manual binning
    q1 = day_df["cnt"].quantile(0.25)
    q2 = day_df["cnt"].quantile(0.50)
    q3 = day_df["cnt"].quantile(0.75)
    bins   = [0, q1, q2, q3, day_df["cnt"].max() + 1]
    labels = ["Low", "Medium-Low", "Medium-High", "High"]
    day_df["rental_cluster"] = pd.cut(day_df["cnt"], bins=bins, labels=labels)

    # Denormalisasi suhu & kelembapan
    day_df["temp_c"]   = day_df["temp"]  * 41
    day_df["hum_pct"]  = day_df["hum"]   * 100
    hour_df["temp_c"]  = hour_df["temp"] * 41
    hour_df["hum_pct"] = hour_df["hum"]  * 100

    return day_df, hour_df

day_df, hour_df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🚲 Bike Sharing")
    st.markdown("**Washington D.C. | 2011–2012**")
    st.divider()

    st.header("🔍 Filter Data")
    selected_year = st.selectbox(
        "Tahun", ["All", "2011", "2012"]
    )
    selected_season = st.selectbox(
        "Musim", ["All"] + sorted(day_df["season_label"].dropna().unique().tolist())
    )
    selected_weather = st.selectbox(
        "Kondisi Cuaca",
        ["All", "Clear/Partly Cloudy", "Mist/Cloudy", "Light Rain/Snow"]
    )

    st.divider()
    st.markdown("### 📋 Pertanyaan Bisnis")
    st.markdown("""
1. 📈 Tren penyewaan bulanan 2011 vs 2012
2. 🕐 Pola per jam: Hari kerja vs non-kerja
3. 🌦️ Pengaruh cuaca & musim
4. 👥 Casual vs Registered
5. 🔍 Clustering intensitas penyewaan
""")
    st.divider()
    st.caption("Dataset: Capital Bikeshare D.C. (2011–2012)")

# ── Apply Filters ─────────────────────────────────────────────────────────────
def filter_df(df):
    d = df.copy()
    if selected_year    != "All": d = d[d["yr_label"]      == selected_year]
    if selected_season  != "All": d = d[d["season_label"]  == selected_season]
    if selected_weather != "All": d = d[d["weather_label"] == selected_weather]
    return d

fday  = filter_df(day_df)
fhour = filter_df(hour_df)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🚲 Bike Sharing Analytics Dashboard")
st.markdown("Analisis lengkap pola penyewaan sepeda Capital Bikeshare, Washington D.C. (2011–2012)")
st.divider()

# ── KPI Cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("📦 Total Penyewaan", f"{fday['cnt'].sum():,.0f}")
with c2:
    st.metric("📅 Rata-rata Harian", f"{fday['cnt'].mean():,.0f}")
with c3:
    st.metric("🏆 Penyewaan Tertinggi", f"{fday['cnt'].max():,.0f}")
with c4:
    pct_reg = fday["registered"].sum() / fday["cnt"].sum() * 100 if not fday.empty else 0
    st.metric("👤 % Registered", f"{pct_reg:.1f}%")
with c5:
    total_days = len(fday)
    st.metric("🗓️ Total Hari", f"{total_days:,}")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# PERTANYAAN 1 — TREN BULANAN
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 📈 Tren Penyewaan Bulanan 2011 vs 2012")
st.caption("Bagaimana tren pertumbuhan total penyewaan sepeda secara bulanan antara 2011 dan 2012, dan bulan mana yang mengalami pertumbuhan tertinggi?")

month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

monthly_data = day_df.groupby(["yr_label","mnth_label"])["cnt"].sum().reset_index()
pivot_mn = monthly_data.pivot(index="mnth_label", columns="yr_label", values="cnt").reindex(month_order)

fig1, axes1 = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"height_ratios":[3,1]})

colors_yr = {"2011":"#90CAF9", "2012":"#1565C0"}
for yr in ["2011","2012"]:
    if yr in pivot_mn.columns:
        axes1[0].plot(
            month_order, pivot_mn[yr],
            marker="o", linewidth=2.5, markersize=7,
            color=colors_yr[yr], label=yr, zorder=3
        )
        for i, val in enumerate(pivot_mn[yr]):
            if not pd.isna(val):
                axes1[0].annotate(
                    f"{val/1000:.0f}K", (month_order[i], val),
                    textcoords="offset points", xytext=(0,8),
                    ha="center", fontsize=7, color=colors_yr[yr]
                )

if "2011" in pivot_mn.columns and "2012" in pivot_mn.columns:
    axes1[0].fill_between(
        month_order, pivot_mn["2011"], pivot_mn["2012"],
        alpha=0.1, color="#1565C0"
    )

axes1[0].set_title("Total Penyewaan Sepeda per Bulan — 2011 vs 2012", fontsize=12, fontweight="bold")
axes1[0].set_ylabel("Total Penyewaan", fontsize=10)
axes1[0].legend(title="Tahun", fontsize=9)
axes1[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x):,}"))
axes1[0].set_xticks(range(len(month_order)))
axes1[0].set_xticklabels(month_order)
sns.despine(ax=axes1[0])

if "2011" in pivot_mn.columns and "2012" in pivot_mn.columns:
    growth = ((pivot_mn["2012"] - pivot_mn["2011"]) / pivot_mn["2011"] * 100).fillna(0)
    bar_colors = ["#66BB6A" if g >= 0 else "#EF5350" for g in growth]
    bars = axes1[1].bar(month_order, growth, color=bar_colors, edgecolor="white", linewidth=0.8)
    for bar, val in zip(bars, growth):
        axes1[1].text(
            bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
            f"{val:.0f}%", ha="center", fontsize=7.5, fontweight="bold"
        )
    axes1[1].axhline(0, color="grey", linewidth=0.8, linestyle="--")
    axes1[1].set_title("Pertumbuhan Bulanan YoY (2012 vs 2011)", fontsize=10, fontweight="bold")
    axes1[1].set_ylabel("Pertumbuhan (%)", fontsize=9)
    axes1[1].set_ylim(0, growth.max() * 1.35 if growth.max() > 0 else 150)
    sns.despine(ax=axes1[1])

plt.tight_layout(pad=2)
st.pyplot(fig1)

with st.expander("💡 Insight "):
    if "2011" in pivot_mn.columns and "2012" in pivot_mn.columns:
        total_11 = day_df[day_df["yr_label"]=="2011"]["cnt"].sum()
        total_12 = day_df[day_df["yr_label"]=="2012"]["cnt"].sum()
        growth_yoy = (total_12 - total_11) / total_11 * 100
        st.markdown(f"""
- Total penyewaan tumbuh **{growth_yoy:.1f}%** dari **{total_11:,.0f}** (2011) menjadi **{total_12:,.0f}** (2012).
- Pola musiman **konsisten** di kedua tahun: rendah di Jan–Feb, memuncak di Jun–Sep, turun di Nov–Des.
- Pertumbuhan YoY terbesar terjadi di bulan-bulan musim dingin (Jan–Mar) — menandakan peningkatan loyalitas pengguna.
- **Juni** adalah bulan dengan total penyewaan tertinggi di 2012.
""")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# PERTANYAAN 2 — POLA PER JAM
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🕐 Pola Penyewaan Per Jam Hari Kerja vs Non-Hari Kerja")
st.caption("Bagaimana pola rata-rata penyewaan per jam dan pada jam berapa penyewaan mencapai puncaknya di setiap kategori?")

hourly_pat = fhour.groupby(["hr","workingday_label"])["cnt"].mean().reset_index()

fig2, ax2 = plt.subplots(figsize=(12, 4.5))
colors_wd = {"Working Day":"#1E88E5", "Non-Working Day":"#FB8C00"}

for tipe, grp in hourly_pat.groupby("workingday_label"):
    ax2.plot(
        grp["hr"], grp["cnt"],
        marker="o", linewidth=2.5, markersize=6,
        color=colors_wd.get(tipe,"grey"), label=tipe, zorder=3
    )
    if not grp.empty:
        peak = grp.loc[grp["cnt"].idxmax()]
        ax2.annotate(
            f"Puncak: {peak['cnt']:.0f}\n(Jam {int(peak['hr']):02d}:00)",
            xy=(peak["hr"], peak["cnt"]),
            xytext=(peak["hr"] - 2.5, peak["cnt"] - 50),
            fontsize=8.5, color=colors_wd.get(tipe,"grey"), fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=colors_wd.get(tipe,"grey"), lw=1.5)
        )

ax2.axvspan(7,  9,  alpha=0.07, color="#1E88E5")
ax2.axvspan(16, 19, alpha=0.07, color="#1E88E5")
ax2.text(7.8,  5, "Rush\nPagi", fontsize=7, color="#1E88E5", ha="center")
ax2.text(17.2, 5, "Rush\nSore", fontsize=7, color="#1E88E5", ha="center")

ax2.set_title("Rata-rata Penyewaan Sepeda Per Jam — Hari Kerja vs Non-Hari Kerja", fontsize=12, fontweight="bold")
ax2.set_xlabel("Jam dalam Sehari")
ax2.set_ylabel("Rata-rata Penyewaan")
ax2.set_xticks(range(0, 24))
ax2.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, ha="right", fontsize=7.5)
ax2.legend(title="Tipe Hari", fontsize=9)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x):,}"))
ax2.set_ylim(bottom=0)
sns.despine()
plt.tight_layout()
st.pyplot(fig2)

with st.expander("💡 Insight "):
    st.markdown("""
- **Hari Kerja:** Pola **bimodal** dengan puncak di jam **08:00** dan **17:00** → penggunaan sebagai **sarana komuter**.
- **Non-Hari Kerja:** Pola **unimodal** dengan puncak di jam **13:00** → penggunaan untuk **rekreasi siang hari**.
- Jam **00:00–05:00** sangat sepi di kedua tipe hari (< 20 penyewaan rata-rata).
- Interval jam **07:00–09:00** dan **16:00–19:00** adalah jam sibuk hari kerja — prioritas ketersediaan armada.
""")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# PERTANYAAN 3 — CUACA & MUSIM
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🌦️ Pengaruh Kondisi Cuaca & Musim Terhadap Penyewaan Harian")
st.caption("Kondisi cuaca dan musim mana yang paling mendorong atau menghambat penyewaan sepeda?")

season_order = ["Spring","Summer","Fall","Winter"]
weather_order = ["Clear/Partly Cloudy","Mist/Cloudy","Light Rain/Snow"]

col_left, col_right = st.columns(2)

with col_left:
    season_avg = fday.groupby("season_label")["cnt"].mean().reindex(season_order).dropna()
    palette_s = ["#A5D6A7","#FFE082","#FF8A65","#90CAF9"]

    fig3a, ax3a = plt.subplots(figsize=(6, 4.5))
    bars = ax3a.bar(
        range(len(season_avg)), season_avg.values,
        color=palette_s[:len(season_avg)], edgecolor="white", linewidth=1, width=0.55
    )
    ax3a.set_xticks(range(len(season_avg)))
    ax3a.set_xticklabels(season_avg.index)
    for bar in bars:
        h = bar.get_height()
        ax3a.text(bar.get_x()+bar.get_width()/2, h+30, f"{h:,.0f}", ha="center", fontsize=10, fontweight="bold")
    ax3a.set_title("Rata-rata Penyewaan per Musim", fontsize=11, fontweight="bold")
    ax3a.set_xlabel("Musim")
    ax3a.set_ylabel("Rata-rata Penyewaan/Hari")
    ax3a.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x):,}"))
    ax3a.set_ylim(0, season_avg.max()*1.25 if not season_avg.empty else 7000)
    sns.despine()
    plt.tight_layout()
    st.pyplot(fig3a)

with col_right:
    weather_avg = fday.groupby("weather_label")["cnt"].mean().reindex(weather_order).dropna()
    palette_w = ["#4FC3F7","#78909C","#B0BEC5"]

    fig3b, ax3b = plt.subplots(figsize=(6, 4.5))
    bars2 = ax3b.bar(
        range(len(weather_avg)), weather_avg.values,
        color=palette_w[:len(weather_avg)], edgecolor="white", linewidth=1, width=0.5
    )
    ax3b.set_xticks(range(len(weather_avg)))
    ax3b.set_xticklabels(
        ["Cerah/Berawan\nSebagian","Berkabut/\nMendung","Hujan/\nSalju Ringan"][:len(weather_avg)],
        fontsize=9
    )
    for bar in bars2:
        h = bar.get_height()
        ax3b.text(bar.get_x()+bar.get_width()/2, h+30, f"{h:,.0f}", ha="center", fontsize=10, fontweight="bold")

    if len(weather_avg) >= 2:
        top = weather_avg.iloc[0]
        bot = weather_avg.iloc[-1]
        pct_drop = (top - bot) / top * 100
        ax3b.annotate(
            f"Turun {pct_drop:.0f}%\nvs cuaca cerah",
            xy=(len(weather_avg)-1, bot),
            xytext=(len(weather_avg)-1.6, bot + 900),
            fontsize=9, color="#C62828",
            arrowprops=dict(arrowstyle="->", color="#C62828")
        )

    ax3b.set_title("Rata-rata Penyewaan per Kondisi Cuaca", fontsize=11, fontweight="bold")
    ax3b.set_xlabel("Kondisi Cuaca")
    ax3b.set_ylabel("Rata-rata Penyewaan/Hari")
    ax3b.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x):,}"))
    ax3b.set_ylim(0, weather_avg.max()*1.3 if not weather_avg.empty else 6000)
    sns.despine()
    plt.tight_layout()
    st.pyplot(fig3b)

with st.expander("💡 Insight "):
    st.markdown("""
- **Musim Fall** adalah musim terbaik (~5.644 penyewaan/hari). **Spring** adalah musim terburuk (~2.604/hari).
- **Cuaca cerah** mendorong ~4.876 penyewaan/hari. **Hujan/salju ringan** menurunkan penyewaan **63%** menjadi ~1.803/hari.
- Temperatur berkorelasi positif kuat (**r = 0,63**) — makin hangat, makin banyak pengguna.
- Variabilitas tinggi di musim Fall & Summer → faktor lain (event kota, hari kerja) juga berpengaruh.
""")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# PERTANYAAN 4 — CASUAL VS REGISTERED
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 👥 Proporsi Pengguna Casual vs Registered per Tipe Hari")
st.caption("Bagaimana perbandingan proporsi dan volume pengguna kasual vs terdaftar berdasarkan hari kerja vs non-kerja?")

seg_wd  = fday.groupby("workingday_label")[["casual","registered"]].mean()
seg_pct = seg_wd.div(seg_wd.sum(axis=1), axis=0) * 100

col4a, col4b = st.columns(2)

with col4a:
    fig4a, ax4a = plt.subplots(figsize=(6, 4.5))
    seg_pct.plot(
        kind="bar", stacked=True, ax=ax4a,
        color=["#FFB74D","#42A5F5"], edgecolor="white", linewidth=1, rot=0
    )
    for i, (idx, row) in enumerate(seg_pct.iterrows()):
        ax4a.text(i, row["casual"]/2, f"{row['casual']:.1f}%",
                  ha="center", va="center", fontsize=11, fontweight="bold", color="white")
        ax4a.text(i, row["casual"]+row["registered"]/2, f"{row['registered']:.1f}%",
                  ha="center", va="center", fontsize=11, fontweight="bold", color="white")
    ax4a.set_title("Proporsi Pengguna per Tipe Hari", fontsize=11, fontweight="bold")
    ax4a.set_xlabel("Tipe Hari")
    ax4a.set_ylabel("Proporsi (%)")
    ax4a.legend(["Casual","Registered"], title="Tipe Pengguna", fontsize=9)
    ax4a.set_ylim(0, 115)
    sns.despine()
    plt.tight_layout()
    st.pyplot(fig4a)

with col4b:
    x = np.arange(len(seg_wd.index))
    w = 0.35
    fig4b, ax4b = plt.subplots(figsize=(6, 4.5))
    ax4b.bar(x-w/2, seg_wd["casual"],     width=w, label="Casual",     color="#FFB74D", edgecolor="white")
    ax4b.bar(x+w/2, seg_wd["registered"], width=w, label="Registered", color="#42A5F5", edgecolor="white")
    for xi, (c, r) in zip(x, zip(seg_wd["casual"], seg_wd["registered"])):
        ax4b.text(xi-w/2, c+15, f"{c:.0f}", ha="center", fontsize=9, fontweight="bold")
        ax4b.text(xi+w/2, r+15, f"{r:.0f}", ha="center", fontsize=9, fontweight="bold")
    ax4b.set_title("Rata-rata Penyewaan Casual vs Registered", fontsize=11, fontweight="bold")
    ax4b.set_xlabel("Tipe Hari")
    ax4b.set_ylabel("Rata-rata Penyewaan/Hari")
    ax4b.set_xticks(x)
    ax4b.set_xticklabels(seg_wd.index)
    ax4b.legend(["Casual","Registered"], fontsize=9)
    ax4b.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{int(x):,}"))
    sns.despine()
    plt.tight_layout()
    st.pyplot(fig4b)

with st.expander("💡 Insight "):
    total_casual = fday["casual"].sum()
    total_reg    = fday["registered"].sum()
    total_all    = fday["cnt"].sum()
    st.markdown(f"""
- Pengguna **registered mendominasi** total penyewaan: **{total_reg/total_all*100:.1f}%** dari keseluruhan.
- Di **hari kerja**, registered mencapai **~83%** — komuter setia harian.
- Di **non-hari kerja**, porsi casual naik ke **~36%** — hampir 2× lipat vs hari kerja (17%).
- Dua segmen berbeda: **komuter terdaftar** (weekday) vs **pengguna rekreasi kasual** (weekend/holiday).
""")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# PERTANYAAN 5 — CLUSTERING
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🔍 Karakteristik Cluster Intensitas Penyewaan Harian")
st.caption("Apa saja karakteristik hari High vs Low dari sisi suhu, kelembapan, dan musim?")

cluster_order   = ["Low","Medium-Low","Medium-High","High"]
cluster_palette = {"Low":"#EF9A9A","Medium-Low":"#FFCC80","Medium-High":"#A5D6A7","High":"#42A5F5"}

col5a, col5b, col5c = st.columns(3)

with col5a:
    fig5a, ax5a = plt.subplots(figsize=(5, 4))
    valid_clusters = [c for c in cluster_order if c in fday["rental_cluster"].cat.categories and
                      c in fday["rental_cluster"].values]
    if valid_clusters:
        sns.boxplot(
            data=fday, x="rental_cluster", y="temp_c",
            order=valid_clusters,
            palette={k:v for k,v in cluster_palette.items() if k in valid_clusters},
            ax=ax5a, width=0.55, linewidth=1.5
        )
        for i, cl in enumerate(valid_clusters):
            mt = fday[fday["rental_cluster"]==cl]["temp_c"].mean()
            ax5a.text(i, mt+0.3, f"{mt:.1f}°C", ha="center", fontsize=8, fontweight="bold")
    ax5a.set_title("Suhu per Cluster", fontsize=11, fontweight="bold")
    ax5a.set_xlabel("Cluster")
    ax5a.set_ylabel("Suhu (°C)")
    sns.despine()
    plt.tight_layout()
    st.pyplot(fig5a)

with col5b:
    fig5b, ax5b = plt.subplots(figsize=(5, 4))
    if valid_clusters:
        sns.boxplot(
            data=fday, x="rental_cluster", y="hum_pct",
            order=valid_clusters,
            palette={k:v for k,v in cluster_palette.items() if k in valid_clusters},
            ax=ax5b, width=0.55, linewidth=1.5
        )
    ax5b.set_title("Kelembapan per Cluster", fontsize=11, fontweight="bold")
    ax5b.set_xlabel("Cluster")
    ax5b.set_ylabel("Kelembapan (%)")
    sns.despine()
    plt.tight_layout()
    st.pyplot(fig5b)

with col5c:
    cluster_season_dist = fday.groupby(["rental_cluster","season_label"], observed=True).size().unstack(fill_value=0)
    valid_idx = [c for c in cluster_order if c in cluster_season_dist.index]
    cluster_season_dist = cluster_season_dist.reindex(valid_idx)
    season_colors = {"Spring":"#A5D6A7","Summer":"#FFE082","Fall":"#FF8A65","Winter":"#90CAF9"}

    fig5c, ax5c = plt.subplots(figsize=(5, 4))
    if not cluster_season_dist.empty:
        cluster_season_dist.plot(
            kind="bar", stacked=True, ax=ax5c,
            color=[season_colors.get(c,"grey") for c in cluster_season_dist.columns],
            edgecolor="white", linewidth=0.7, rot=0
        )
    ax5c.set_title("Distribusi Musim per Cluster", fontsize=11, fontweight="bold")
    ax5c.set_xlabel("Cluster")
    ax5c.set_ylabel("Jumlah Hari")
    ax5c.legend(title="Musim", fontsize=7, loc="upper right")
    sns.despine()
    plt.tight_layout()
    st.pyplot(fig5c)

# Tabel profil cluster
st.markdown("#### 📋 Tabel Profil Lengkap Cluster")
profile = fday.groupby("rental_cluster", observed=True).agg(
    Jml_Hari      = ("cnt",        "count"),
    Avg_Sewa      = ("cnt",        lambda x: round(x.mean(), 0)),
    Avg_Suhu      = ("temp_c",     lambda x: round(x.mean(), 1)),
    Avg_Kelembapan= ("hum_pct",    lambda x: round(x.mean(), 1)),
    Pct_WorkingDay= ("workingday", lambda x: f"{x.mean()*100:.1f}%"),
    Pct_Cerah     = ("weathersit", lambda x: f"{(x==1).mean()*100:.1f}%"),
    Musim_Dominan = ("season_label",lambda x: x.value_counts().index[0] if len(x) > 0 else "-"),
).reset_index()
profile.columns = ["Cluster","Jml Hari","Avg Sewa/Hari","Suhu Rata2 (°C)",
                   "Kelembapan (%)","% Hari Kerja","% Cuaca Cerah","Musim Dominan"]
st.dataframe(profile, use_container_width=True, hide_index=True)

with st.expander("💡 Insight "):
    st.markdown("""
- Cluster **High** → suhu rata-rata **~26°C**, kelembapan **~60%**, cuaca cerah **89%**, dominan musim **Fall/Summer**.
- Cluster **Low** → suhu rata-rata **~8°C**, kelembapan **~70%**, cuaca cerah hanya **47%**, dominan musim **Spring/Winter**.
- **Suhu** adalah pembeda terkuat antar cluster (~18°C perbedaan antara High dan Low).
- Kombinasi **suhu hangat + kelembapan rendah + cuaca cerah + musim gugur/panas** = kondisi ideal penyewaan tinggi.
""")

st.divider()

# ── Conclusion & Recommendation ───────────────────────────────────────────────
st.markdown("### 📝 Kesimpulan & Rekomendasi")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Q1: Tren", "🕐 Q2: Per Jam", "🌦️ Q3: Cuaca", "👥 Q4: Segmen", "🔍 Q5: Cluster", "🎯 Rekomendasi"
])

with tab1:
    st.markdown("""
**Kesimpulan Pertanyaan 1:**
Total penyewaan tumbuh **64,9%** dari 1.243.103 (2011) menjadi 2.049.576 (2012). Pola musiman konsisten di kedua tahun — rendah di Jan–Feb, puncak di Jun–Sep. Pertumbuhan YoY tertinggi di musim dingin menandakan peningkatan loyalitas pengguna.
""")

with tab2:
    st.markdown("""
**Kesimpulan Pertanyaan 2:**
Hari kerja menunjukkan pola bimodal (jam 08:00 & 17:00) = komuter. Non-kerja menunjukkan pola unimodal (jam 13:00) = rekreasi. Jam 07:00–09:00 dan 16:00–19:00 adalah periode kritis armada hari kerja.
""")

with tab3:
    st.markdown("""
**Kesimpulan Pertanyaan 3:**
Musim Fall terbaik (5.644/hari), Spring terburuk (2.604/hari). Cuaca cerah mendorong ~4.876/hari; hujan/salju menurunkan penyewaan 63%. Suhu berkorelasi positif kuat (r=0,63) dengan jumlah penyewaan.
""")

with tab4:
    st.markdown("""
**Kesimpulan Pertanyaan 4:**
Pengguna registered mendominasi (81%). Di hari kerja 83% adalah registered (komuter). Di non-kerja, casual naik ke 36% — hampir 2× lipat. Dua segmen dengan kebutuhan berbeda memerlukan strategi berbeda.
""")

with tab5:
    st.markdown("""
**Kesimpulan Pertanyaan 5:**
Hari High: suhu ~26°C, lembap rendah, cerah, Fall/Summer. Hari Low: suhu ~8°C, lembap tinggi, Spring/Winter. Suhu adalah pembeda utama (~18°C gap). Profil ini berguna sebagai panduan alokasi armada berbasis prediksi cuaca.
""")

with tab6:
    st.markdown("""
**🎯 Rekomendasi Action Item:**

1. **⏰ Optimalkan Armada Berbasis Jam** — Tambah ketersediaan sepeda jam 07:00–09:00 & 16:00–19:00 (hari kerja) dan 10:00–15:00 (non-kerja) di area rekreasi.

2. **🎁 Kampanye Promosi Musiman** — Diskon 20–30% di musim Spring dan hari hujan/kabut untuk mendorong penyewaan di periode rendah.

3. **🏅 Program Loyalitas Registered** — Prioritaskan reward, langganan bulanan murah, dan reservasi untuk 81% pengguna registered sebagai tulang punggung bisnis.

4. **📣 Konversi Casual → Registered** — Manfaatkan aktivitas tinggi casual di akhir pekan untuk menawarkan trial membership gratis atau diskon pendaftaran pertama.

5. **🌡️ Perencanaan Berbasis Prediksi Cuaca** — Gunakan profil cluster (suhu >20°C + cerah + Fall/Summer) sebagai sinyal antisipasi hari High untuk memaksimalkan ketersediaan armada.
""")

st.caption("📦 Dataset: Bike Sharing Dataset — Capital Bikeshare, Washington D.C. (2011–2012) | Fanaee-T & Gama (2013)")
