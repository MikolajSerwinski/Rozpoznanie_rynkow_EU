import subprocess
import sys
from pathlib import Path

# Dodanie głównego katalogu projektu do ścieżki Pythona (rozwiązuje ModuleNotFoundError: 'src')
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.config import GOLD_DIR

DB_PATH = GOLD_DIR / "analytics.duckdb"

CN_LABELS = {
    "94": "94 – Meble ogółem (cały dział)",
    "9401": "9401 – Meble do siedzenia (krzesła, sofy, fotele)",
    "9403": "9403 – Pozostałe meble (drewniane, metalowe, biurowe, kuchenne)",
}

st.set_page_config(
    page_title="Rynki Eksportowe Mebli UE",
    page_icon="🪑",
    layout="wide",
)


@st.cache_data(ttl=300)
def load_data():
    """Wczytuje tabele analityczne z warstwy Gold (DuckDB)."""
    if not DB_PATH.exists():
        return None, None, None
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df_monthly = con.execute("SELECT * FROM fact_monthly_trade").df()
    df_annual = con.execute("SELECT * FROM mart_annual_summary").df()
    df_countries = con.execute("SELECT * FROM dim_countries").df()
    con.close()
    return df_monthly, df_annual, df_countries


def main():
    st.title("🪑 Rozpoznanie rynków eksportowych w UE dla polskiego producenta mebli")
    st.markdown(
        "Aplikacja analityczna wspierająca wybór nowych rynków zbytu na podstawie danych "
        "**Eurostat Comext**, wskaźników makroekonomicznych **Eurostat** oraz kursów walut **NBP**."
    )

    df_monthly, df_annual, df_countries = load_data()

    if df_monthly is None or df_monthly.empty:
        st.error(
            f"Brak bazy danych warstwy Gold (`{DB_PATH}`). "
            "Uruchom najpierw potok danych w terminalu (`uv run python -m src.run_pipeline`) "
            "lub kliknij przycisk poniżej."
        )
        if st.button("🔄 Uruchom potok danych teraz"):
            with st.spinner("Trwa pobieranie, przetwarzanie i testowanie danych..."):
                res = subprocess.run([sys.executable, "-m", "src.run_pipeline"], capture_output=True, text=True)
                if res.returncode == 0:
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.code(res.stdout + "\n" + res.stderr)
        return

    # --- PASEK BOCZNY (FILTRY I STEROWANIE) ---
    with st.sidebar:
        st.header("⚙️ Parametry analizy")

        available_cn = sorted(df_annual["cn_code"].unique())
        selected_cn = st.selectbox(
            "Grupa towarowa (Kod CN):",
            options=available_cn,
            format_func=lambda x: CN_LABELS.get(x, x),
        )

        available_years = sorted(df_annual["year"].unique())
        col_y1, col_y2 = st.columns(2)
        with col_y1:
            base_year = st.selectbox("Rok bazowy:", options=available_years, index=0)
        with col_y2:
            target_year = st.selectbox(
                "Rok docelowy:", options=available_years, index=len(available_years) - 1
            )

        min_import_mln = st.slider(
            "Min. roczny import rynku (mln EUR):",
            min_value=0,
            max_value=500,
            value=50,
            step=10,
            help="Odfiltrowuje mikro-rynki o niskiej chłonności (np. Malta, Cypr).",
        )

        st.divider()
        st.subheader("🛠️ Zarządzanie potokiem")
        if st.button("🔄 Odśwież dane (Uruchom Pipeline)", use_container_width=True):
            with st.spinner("Wykonywanie potoku ETL i testów jakości..."):
                res = subprocess.run(
                    [sys.executable, "-m", "src.run_pipeline"], capture_output=True, text=True
                )
                if res.returncode == 0:
                    st.success("Potok zakończony pomyślnie!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Błąd podczas wykonywania potoku!")
                    st.code(res.stderr)

    # Filtrowanie po wybranym kodzie CN
    df_m_cn = df_monthly[df_monthly["cn_code"] == selected_cn].copy()
    df_a_cn = df_annual[df_annual["cn_code"] == selected_cn].copy()

    # Wyliczenie średniego miesięcznego importu (aby porównywać uczciwie lata niepełne)
    df_a_cn["avg_monthly_import_eur"] = (
        df_a_cn["annual_total_import_eur"] / df_a_cn["months_reported"]
    )

    # Przygotowanie tabeli porównawczej (Rok bazowy vs Rok docelowy)
    df_base = df_a_cn[df_a_cn["year"] == base_year].set_index("importer_country")
    df_targ = df_a_cn[df_a_cn["year"] == target_year].set_index("importer_country")

    comp = df_targ[
        [
            "country_name_pl",
            "months_reported",
            "annual_total_import_eur",
            "avg_monthly_import_eur",
            "annual_pl_import_eur",
            "annual_pl_share_pct",
            "annual_market_eur_kg",
            "population",
            "gdp_per_capita_eur",
        ]
    ].copy()

    comp["base_avg_monthly_eur"] = df_base["avg_monthly_import_eur"]
    comp["base_pl_share_pct"] = df_base["annual_pl_share_pct"]

    # Dynamika wzrostu importu (%) liczona na średniej miesięcznej (odporna na niepełny rok bieżący)
    comp["import_growth_pct"] = (
        (comp["avg_monthly_import_eur"] - comp["base_avg_monthly_eur"])
        / comp["base_avg_monthly_eur"]
        * 100.0
    ).round(2)

    # Zmiana udziału Polski w punktach procentowych (pp)
    comp["pl_share_change_pp"] = (
        comp["annual_pl_share_pct"] - comp["base_pl_share_pct"]
    ).round(2)

    comp = comp.reset_index()
    comp = comp[comp["annual_total_import_eur"] >= min_import_mln * 1_000_000]

    # --- KARTY KPI NA GÓRZE ---
    total_eu_import_bln = comp["annual_total_import_eur"].sum() / 1e9
    total_pl_export_bln = comp["annual_pl_import_eur"].sum() / 1e9
    avg_eu_pl_share = (
        (comp["annual_pl_import_eur"].sum() / comp["annual_total_import_eur"].sum()) * 100
        if comp["annual_total_import_eur"].sum() > 0
        else 0
    )
    fastest_country = (
        comp.sort_values("import_growth_pct", ascending=False).iloc[0]
        if not comp.empty
        else None
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        f"Import badanych rynków UE ({target_year})",
        f"{total_eu_import_bln:.2f} mld EUR",
    )
    k2.metric(
        f"Import z Polski ({target_year})",
        f"{total_pl_export_bln:.2f} mld EUR",
    )
    k3.metric(
        f"Średni udział Polski w UE ({target_year})",
        f"{avg_eu_pl_share:.1f}%",
    )
    if fastest_country is not None:
        k4.metric(
            f"Lider wzrostu ({base_year} → {target_year})",
            f"{fastest_country['country_name_pl']}",
            f"{fastest_country['import_growth_pct']:+.1f}%",
        )

    st.divider()

    # --- 4 ZAKŁADKI ODPOWIADAJĄCE NA 4 PYTANIA BIZNESOWE ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 1. Dynamika importu (Kto rośnie najszybciej?)",
        "🇵🇱 2. Udział Polski i konkurencyjność",
        "💎 3. Cena EUR/kg (Rynki Tanie vs Premium)",
        "💱 4. Wpływ kursu EUR/PLN (Symulator)",
    ])

    # =========================================================================
    # ZAKŁADKA 1: PYTANIE 1 - KTÓRE KRAJE NAJSZYBCIEJ ZWIĘKSZAJĄ IMPORT MEBLI?
    # =========================================================================
    with tab1:
        st.subheader(
            f"Pytanie 1: Które kraje najszybciej zwiększają import mebli ({base_year} vs {target_year})?"
        )
        st.caption(
            "Dynamika liczona na podstawie średniego miesięcznego importu w danym roku, "
            "co zapewnia pełną porównywalność nawet przy niepełnym roku bieżącym."
        )

        col1, col2 = st.columns([3, 2])
        with col1:
            df_plot1 = comp.dropna(subset=["import_growth_pct"]).sort_values(
                "import_growth_pct", ascending=True
            )
            fig1 = px.bar(
                df_plot1,
                x="import_growth_pct",
                y="country_name_pl",
                orientation="h",
                color="import_growth_pct",
                color_continuous_scale="Tealgrn",
                labels={
                    "import_growth_pct": f"Zmiana śr. miesięcznego importu {base_year}→{target_year} (%)",
                    "country_name_pl": "Kraj importera",
                },
                title=f"Ranking dynamiki wzrostu importu mebli ({base_year} → {target_year})",
            )
            fig1.update_layout(height=550)
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.markdown("##### Tabela rankingowa rynków docelowych")
            display_df = comp[
                [
                    "country_name_pl",
                    "import_growth_pct",
                    "annual_total_import_eur",
                    "annual_pl_share_pct",
                    "annual_market_eur_kg",
                    "gdp_per_capita_eur",
                ]
            ].sort_values("import_growth_pct", ascending=False).copy()

            display_df["annual_total_import_eur"] = (
                display_df["annual_total_import_eur"] / 1e6
            ).round(1)

            display_df.columns = [
                "Kraj",
                "Wzrost (%)",
                "Import (mln EUR)",
                "Udział PL (%)",
                "Cena (EUR/kg)",
                "PKB/os. (EUR)",
            ]
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=450)

            # ROZSZERZENIE: Eksport wyników do CSV
            csv_bytes = display_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Pobierz ranking rynków (CSV)",
                data=csv_bytes,
                file_name=f"ranking_rynkow_CN{selected_cn}_{base_year}_{target_year}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # =========================================================================
    # ZAKŁADKA 2: PYTANIE 2 - JAKI UDZIAŁ W IMPORCIE MA POLSKA I CZY ROŚNIE?
    # =========================================================================
    with tab2:
        st.subheader("Pytanie 2: Jaki udział w ich imporcie ma Polska i czy ten udział rośnie?")

        c_left, c_right = st.columns(2)
        with c_left:
            df_share = comp.sort_values("annual_pl_share_pct", ascending=True)
            fig2a = px.bar(
                df_share,
                x="annual_pl_share_pct",
                y="country_name_pl",
                orientation="h",
                color="pl_share_change_pp",
                color_continuous_scale="RdYlGn",
                labels={
                    "annual_pl_share_pct": f"Udział Polski w imporcie w {target_year} (%)",
                    "country_name_pl": "Kraj importera",
                    "pl_share_change_pp": f"Zmiana udziału (pp)",
                },
                title=f"Udział Polski (%) w {target_year} (kolor = zmiana w pkt proc. względem {base_year})",
            )
            fig2a.update_layout(height=520)
            st.plotly_chart(fig2a, use_container_width=True)

        with c_right:
            selected_country_pl = st.selectbox(
                "Wybierz kraj do analizy miesięcznego trendu udziału Polski:",
                options= sorted(comp["country_name_pl"].unique()),
                index=0,
            )
            df_country_m = df_m_cn[df_m_cn["country_name_pl"] == selected_country_pl].sort_values("period")

            fig2b = go.Figure()
            fig2b.add_trace(
                go.Bar(
                    x=df_country_m["period"],
                    y=df_country_m["pl_import_eur"] / 1e6,
                    name="Import z Polski (mln EUR)",
                    marker_color="#2b5c8f",
                    yaxis="y1",
                )
            )
            fig2b.add_trace(
                go.Scatter(
                    x=df_country_m["period"],
                    y=df_country_m["pl_share_pct"],
                    name="Udział Polski (%)",
                    mode="lines+markers",
                    line=dict(color="#d95f02", width=3),
                    yaxis="y2",
                )
            )
            fig2b.update_layout(
                title=f"{selected_country_pl}: Miesięczny import z Polski (mln EUR) oraz udział rynkowy (%)",
                xaxis_title="Miesiąc",
                yaxis=dict(title="Import z Polski (mln EUR)", side="left"),
                yaxis2=dict(title="Udział Polski (%)", side="right", overlaying="y", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=450,
            )
            st.plotly_chart(fig2b, use_container_width=True)

    # =========================================================================
    # ZAKŁADKA 3: PYTANIE 3 - CENA JEDNOSTKOWA EUR/KG (TANI VS PREMIUM)
    # =========================================================================
    with tab3:
        st.subheader("Pytanie 3: Jaka jest średnia cena jednostkowa (EUR/kg) – rynek tani czy premium?")
        st.markdown(
            "Zestawienie **średniej ceny za 1 kg importowanych mebli (EUR/kg)** z **zamożnością rynku (PKB per capita)**. "
            "Wielkość bąbla oznacza populację kraju, a kolor – obecny udział Polski w rynku."
        )

        median_price = comp["annual_market_eur_kg"].median()
        median_gdp = comp["gdp_per_capita_eur"].median()

        fig3 = px.scatter(
            comp.dropna(subset=["annual_market_eur_kg", "gdp_per_capita_eur", "population"]),
            x="gdp_per_capita_eur",
            y="annual_market_eur_kg",
            size="population",
            color="annual_pl_share_pct",
            hover_name="country_name_pl",
            text="country_name_pl",
            size_max=55,
            color_continuous_scale="Viridis",
            labels={
                "gdp_per_capita_eur": "PKB per capita (EUR) – Zamożność rynku",
                "annual_market_eur_kg": "Średnia cena rynkowa (EUR/kg) – Pozycjonowanie",
                "annual_pl_share_pct": "Udział PL (%)",
                "population": "Ludność",
            },
            title=f"Mapa pozycjonowania rynków: Tani/Wolumenowy vs Premium ({target_year})",
        )
        fig3.add_hline(
            y=median_price,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Mediana ceny UE: {median_price:.2f} EUR/kg",
        )
        fig3.add_vline(
            x=median_gdp,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Mediana PKB/os.: {median_gdp:,.0f} EUR",
        )
        fig3.update_traces(textposition="top center")
        fig3.update_layout(height=550)
        st.plotly_chart(fig3, use_container_width=True)

    # =========================================================================
    # ZAKŁADKA 4: PYTANIE 4 - WPŁYW ZMIAN KURSU EUR/PLN NA PRZYCHÓD W PLN
    # =========================================================================
    with tab4:
        st.subheader("Pytanie 4: Jak zmiany kursu EUR/PLN wpływają na przychód eksportera w PLN?")

        # Historyczny przebieg kursu i wartości eksportu zagregowany dla całej UE
        df_fx_hist = (
            df_m_cn.groupby("period", as_index=False)
            .agg(
                pl_export_eur=("pl_import_eur", "sum"),
                pl_export_pln=("pl_import_pln", "sum"),
                avg_eur_pln=("avg_eur_pln", "mean"),
            )
            .sort_values("period")
        )

        # Obliczenie hipotetycznego przychodu przy stałym kursie z pierwszego miesiąca analizy
        first_rate = df_fx_hist["avg_eur_pln"].iloc[0]
        df_fx_hist["pl_export_pln_const_fx"] = df_fx_hist["pl_export_eur"] * first_rate
        df_fx_hist["fx_effect_mln_pln"] = (
            df_fx_hist["pl_export_pln"] - df_fx_hist["pl_export_pln_const_fx"]
        ) / 1e6

        col_sim, col_chart = st.columns([1, 2])

        with col_sim:
            st.markdown("#### 🧮 Symulator kontraktu eksportowego (Analiza scenariuszy)")
            contract_eur = st.number_input(
                "Planowany miesięczny eksport (w EUR):",
                min_value=10_000,
                max_value=10_000_000,
                value=250_000,
                step=50_000,
            )
            latest_rate = float(df_fx_hist["avg_eur_pln"].dropna().iloc[-1])
            min_hist_rate = float(df_fx_hist["avg_eur_pln"].min())
            max_hist_rate = float(df_fx_hist["avg_eur_pln"].max())

            sim_rate = st.slider(
                "Symulowany kurs EUR/PLN:",
                min_value=3.80,
                max_value=5.00,
                value=round(latest_rate, 2),
                step=0.01,
            )

            rev_current = contract_eur * latest_rate
            rev_sim = contract_eur * sim_rate
            diff_pln = rev_sim - rev_current

            st.metric(
                "Przychód przy symulowanym kursie:",
                f"{rev_sim:,.0f} PLN".replace(",", " "),
                f"{diff_pln:+,.0f} PLN względem ostatniego kursu NBP ({latest_rate:.4f})".replace(",", " "),
            )
            st.info(
                f"**Zakres historyczny w badanym okresie:**\n"
                f"* Min kurs NBP: **{min_hist_rate:.4f} PLN** → `{contract_eur * min_hist_rate:,.0f} PLN`\n"
                f"* Max kurs NBP: **{max_hist_rate:.4f} PLN** → `{contract_eur * max_hist_rate:,.0f} PLN`\n"
                f"* Różnica (ryzyko walutowe): **`{contract_eur * (max_hist_rate - min_hist_rate):,.0f} PLN`** na tym samym wolumenie EUR!"
            )

        with col_chart:
            fig4 = go.Figure()
            fig4.add_trace(
                go.Bar(
                    x=df_fx_hist["period"],
                    y=df_fx_hist["fx_effect_mln_pln"],
                    name="Efekt kursowy (mln PLN względem kursu startowego)",
                    marker_color=[
                        "#d95f02" if v < 0 else "#1b9e77" for v in df_fx_hist["fx_effect_mln_pln"]
                    ],
                    yaxis="y1",
                )
            )
            fig4.add_trace(
                go.Scatter(
                    x=df_fx_hist["period"],
                    y=df_fx_hist["avg_eur_pln"],
                    name="Średni kurs EUR/PLN (NBP)",
                    mode="lines+markers",
                    line=dict(color="#1f78b4", width=3),
                    yaxis="y2",
                )
            )
            fig4.update_layout(
                title=f"Wpływ wahań kursu EUR/PLN na przychody polskich eksporterów (względem kursu bazowego {first_rate:.4f})",
                xaxis_title="Miesiąc",
                yaxis=dict(title="Różnica przychodu z tytułu kursu (mln PLN)", side="left"),
                yaxis2=dict(title="Kurs średni EUR/PLN", side="right", overlaying="y", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=450,
            )
            st.plotly_chart(fig4, use_container_width=True)


if __name__ == "__main__":
    main()