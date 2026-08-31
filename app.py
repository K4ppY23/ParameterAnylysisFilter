import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import uuid

st.set_page_config(page_title="Zaawansowany Analizator GPS", layout="wide")
st.title("🛰️ Zaawansowany Analizator Danych GPS")


# -----------------------------------------------------------------------------
# POMOCNICZA FUNKCJA LOGICZNA (EVALUATE CONDITIONS WITH AND/OR/XOR)
# -----------------------------------------------------------------------------
def evaluate_conditions(df, time_col, start_dt, end_dt, conditions):
    # Maska zakresu czasowego
    time_mask = (df[time_col] >= pd.to_datetime(start_dt)) & (df[time_col] <= pd.to_datetime(end_dt))

    if not conditions:
        return time_mask

    accumulated_mask = None

    for idx, cond in enumerate(conditions):
        col = cond['column']
        op = cond['operator']
        val = cond['value']

        # Pojedynczy warunek
        if op == ">":
            c_mask = (df[col] > val)
        elif op == "<":
            c_mask = (df[col] < val)
        elif op == "=":
            c_mask = (df[col] == val)
        elif op == ">=":
            c_mask = (df[col] >= val)
        elif op == "<=":
            c_mask = (df[col] <= val)
        elif op == "!=":
            c_mask = (df[col] != val)
        else:
            c_mask = pd.Series(True, index=df.index)

        if idx == 0:
            accumulated_mask = c_mask
        else:
            logic_op = cond.get('logic_op', 'AND')
            if logic_op == 'AND':
                accumulated_mask = accumulated_mask & c_mask
            elif logic_op == 'OR':
                accumulated_mask = accumulated_mask | c_mask
            elif logic_op == 'XOR':
                accumulated_mask = accumulated_mask ^ c_mask

    return time_mask & accumulated_mask


# -----------------------------------------------------------------------------
# 1. IMPORT PLIKU CSV
# -----------------------------------------------------------------------------
uploaded_file = st.file_uploader("Wczytaj plik CSV z urządzenia GPS", type=["csv"])

if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)

    st.sidebar.header("⚙️ Konfiguracja Danych")
    time_column = st.sidebar.selectbox("Kolumna reprezentująca czas:", data.columns)
    data[time_column] = pd.to_datetime(data[time_column], errors='coerce')

    numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns.tolist()
    available_columns = numeric_columns if numeric_columns else data.columns.tolist()

    main_tab1, main_tab2 = st.tabs([
        "✂️ Tryb 1: Ukrywanie niedopasowanych (Filtrowanie)",
        "🎯 Tryb 2: Podświetlanie na pełnych danych"
    ])

    # =========================================================================
    # ZAKŁADKA 1: FILTROWANIE (UKRYWANIE NIEDOPASOWANYCH)
    # =========================================================================
    with main_tab1:
        st.header("Wycinanie / Filtrowanie danych")

        if 'filter_conditions_t1' not in st.session_state:
            st.session_state.filter_conditions_t1 = [
                {'id': str(uuid.uuid4()), 'logic_op': 'AND', 'column': available_columns[0], 'operator': '>',
                 'value': 0.0}
            ]

        with st.expander("📅 Zakres czasowy", expanded=False):
            c1, c2 = st.columns(2)
            start_dt_t1 = c1.datetime_input("Czas OD (T1):", data[time_column].min(), key="t1_dt1")
            end_dt_t1 = c2.datetime_input("Czas DO (T1):", data[time_column].max(), key="t1_dt2")

        st.markdown("#### Warunki wycinania z operatorami logicznymi")
        btn_add_t1, btn_clr_t1, _ = st.columns([1, 1, 3])

        if btn_add_t1.button("➕ Dodaj warunek", key="add_t1"):
            st.session_state.filter_conditions_t1.append(
                {'id': str(uuid.uuid4()), 'logic_op': 'AND', 'column': available_columns[0], 'operator': '>',
                 'value': 0.0}
            )
            st.rerun()

        if btn_clr_t1.button("🗑️ Wyczyść warunki", key="clr_t1"):
            st.session_state.filter_conditions_t1 = []
            st.rerun()

        to_remove_t1 = None
        for idx, cond in enumerate(st.session_state.filter_conditions_t1):
            cid = cond['id']

            if idx == 0:
                c_col, c_op, c_val, c_del = st.columns([3, 2, 3, 1])
                slog = 'AND'
            else:
                c_log, c_col, c_op, c_val, c_del = st.columns([1.5, 3, 2, 3, 1])
                slog = c_log.selectbox(f"Lącznik #{idx + 1}", ["AND", "OR", "XOR"],
                                       index=["AND", "OR", "XOR"].index(cond.get('logic_op', 'AND')),
                                       key=f"t1_log_{cid}")

            scol = c_col.selectbox(f"Parametr #{idx + 1}", available_columns,
                                   index=available_columns.index(cond['column']) if cond[
                                                                                        'column'] in available_columns else 0,
                                   key=f"t1_col_{cid}")
            sop = c_op.selectbox(f"Warunek #{idx + 1}", [">", "<", "=", ">=", "<=", "!="],
                                 index=[">", "<", "=", ">=", "<=", "!="].index(cond['operator']),
                                 key=f"t1_op_{cid}")
            sval = c_val.number_input(f"Wartość #{idx + 1}", value=float(cond['value']), key=f"t1_val_{cid}")

            if c_del.button("❌", key=f"t1_del_{cid}"):
                to_remove_t1 = cid

            cond['logic_op'], cond['column'], cond['operator'], cond['value'] = slog, scol, sop, sval

        if to_remove_t1:
            st.session_state.filter_conditions_t1 = [c for c in st.session_state.filter_conditions_t1 if
                                                     c['id'] != to_remove_t1]
            st.rerun()

        exec_t1 = st.button("🚀 Wykonaj zapytanie i przefiltruj", type="primary", key="exec_t1",
                            use_container_width=True)

        if 'filtered_df_t1' not in st.session_state:
            st.session_state.filtered_df_t1 = data.copy()

        if exec_t1:
            mask_t1 = evaluate_conditions(data, time_column, start_dt_t1, end_dt_t1,
                                          st.session_state.filter_conditions_t1)
            st.session_state.filtered_df_t1 = data[mask_t1].copy()

        df_t1 = st.session_state.filtered_df_t1
        st.subheader(f"Wyniki (Znaleziono {len(df_t1)} z {len(data)} rekordów)")

        tab_t1_grid, tab_t1_chart = st.tabs(["📋 Tabela Wyników", "📈 Wykres Wieloparametrowy"])

        with tab_t1_grid:
            st.dataframe(df_t1, use_container_width=True)

        with tab_t1_chart:
            selected_params_t1 = st.multiselect(
                "Wybierz parametry do wyświetlenia na wykresie:",
                available_columns,
                default=[available_columns[0]] if available_columns else [],
                key="multi_y_t1"
            )

            if selected_params_t1:
                fig_t1 = make_subplots(
                    rows=len(selected_params_t1), cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.08,
                    subplot_titles=[f"Przebieg: {p}" for p in selected_params_t1]
                )

                for idx_p, param in enumerate(selected_params_t1, start=1):
                    fig_t1.add_trace(
                        go.Scatter(x=df_t1[time_column], y=df_t1[param], mode='lines+markers', name=param),
                        row=idx_p, col=1
                    )

                fig_t1.update_layout(height=300 * len(selected_params_t1), hovermode="x unified")
                fig_t1.update_xaxes(rangeslider_visible=True, row=len(selected_params_t1), col=1)
                st.plotly_chart(fig_t1, use_container_width=True)

    # =========================================================================
    # ZAKŁADKA 2: PODŚWIETLANIE I OZNACZANIE NA PEŁNYCH DANYCH
    # =========================================================================
    with main_tab2:
        st.header("Wyróżnianie wartości na tle wszystkich danych")
        st.info("💡 W tym trybie widoczne są WSZYSTKIE dane. Wybrane warunki zostaną oznaczone po kliknięciu przycisku.")

        if 'filter_conditions_t2' not in st.session_state:
            st.session_state.filter_conditions_t2 = [
                {'id': str(uuid.uuid4()), 'logic_op': 'AND', 'column': available_columns[0], 'operator': '>',
                 'value': 0.0}
            ]

        with st.expander("📅 Zakres czasowy", expanded=False):
            c1_2, c2_2 = st.columns(2)
            start_dt_t2 = c1_2.datetime_input("Czas OD (T2):", data[time_column].min(), key="t2_dt1")
            end_dt_t2 = c2_2.datetime_input("Czas DO (T2):", data[time_column].max(), key="t2_dt2")

        st.markdown("#### Warunki wyróżnienia z operatorami logicznymi")
        btn_add_t2, btn_clr_t2, _ = st.columns([1, 1, 3])

        if btn_add_t2.button("➕ Dodaj warunek", key="add_t2"):
            st.session_state.filter_conditions_t2.append(
                {'id': str(uuid.uuid4()), 'logic_op': 'AND', 'column': available_columns[0], 'operator': '>',
                 'value': 0.0}
            )
            st.rerun()

        if btn_clr_t2.button("🗑️ Wyczyść warunki", key="clr_t2"):
            st.session_state.filter_conditions_t2 = []
            st.rerun()

        to_remove_t2 = None
        for idx, cond in enumerate(st.session_state.filter_conditions_t2):
            cid = cond['id']

            if idx == 0:
                c_col, c_op, c_val, c_del = st.columns([3, 2, 3, 1])
                slog = 'AND'
            else:
                c_log, c_col, c_op, c_val, c_del = st.columns([1.5, 3, 2, 3, 1])
                slog = c_log.selectbox(f"Lącznik #{idx + 1}", ["AND", "OR", "XOR"],
                                       index=["AND", "OR", "XOR"].index(cond.get('logic_op', 'AND')),
                                       key=f"t2_log_{cid}")

            scol = c_col.selectbox(f"Parametr #{idx + 1}", available_columns,
                                   index=available_columns.index(cond['column']) if cond[
                                                                                        'column'] in available_columns else 0,
                                   key=f"t2_col_{cid}")
            sop = c_op.selectbox(f"Warunek #{idx + 1}", [">", "<", "=", ">=", "<=", "!="],
                                 index=[">", "<", "=", ">=", "<=", "!="].index(cond['operator']),
                                 key=f"t2_op_{cid}")
            sval = c_val.number_input(f"Wartość #{idx + 1}", value=float(cond['value']), key=f"t2_val_{cid}")

            if c_del.button("❌", key=f"t2_del_{cid}"):
                to_remove_t2 = cid

            cond['logic_op'], cond['column'], cond['operator'], cond['value'] = slog, scol, sop, sval

        if to_remove_t2:
            st.session_state.filter_conditions_t2 = [c for c in st.session_state.filter_conditions_t2 if
                                                     c['id'] != to_remove_t2]
            st.rerun()

        exec_t2 = st.button("🚀 Wykonaj zapytanie i oznacz dane", type="primary", key="exec_t2",
                            use_container_width=True)

        # Inicjalizacja lub aktualizacja po kliknięciu przycisku
        if 'applied_mask_t2' not in st.session_state or len(st.session_state.applied_mask_t2) != len(data):
            st.session_state.applied_mask_t2 = evaluate_conditions(data, time_column, start_dt_t2, end_dt_t2,
                                                                   st.session_state.filter_conditions_t2)

        if exec_t2:
            st.session_state.applied_mask_t2 = evaluate_conditions(data, time_column, start_dt_t2, end_dt_t2,
                                                                   st.session_state.filter_conditions_t2)

        mask_t2 = st.session_state.applied_mask_t2
        matched_count = mask_t2.sum()

        st.markdown(
            f"**Wyróżniono {matched_count} z {len(data)} rekordów** (Dopasowanie: {matched_count / len(data) * 100:.1f}%)")

        tab_t2_grid, tab_t2_chart = st.tabs(
            ["📋 Tabela z Wyróżnieniem High-Contrast", "📈 Wykres Wieloparametrowy Overlay"])

        # 1. TABELA Z PODŚWIETLANIEM WIERSZY
        with tab_t2_grid:
            df_display = data.copy()
            df_display.insert(0, "Status", ["🎯 SPEŁNIA WARUNKI" if m else "⚪ STANDARD" for m in mask_t2])


            # Stylizacja wysokie kontrasty
            def style_high_contrast(row):
                if row["Status"] == "🎯 SPEŁNIA WARUNKI":
                    return [
                        'background-color: #d1e7dd; color: #0f5132; font-weight: bold; border-left: 6px solid #198754'] * len(
                        row)
                return ['background-color: #f8f9fa; color: #6c757d'] * len(row)


            styled_df = df_display.style.apply(style_high_contrast, axis=1)
            st.dataframe(styled_df, use_container_width=True)

        # 2. WYKRES WIELOPARAMETROWY OVERLAY
        with tab_t2_chart:
            selected_params_t2 = st.multiselect(
                "Wybierz parametry do wyświetlenia na wykresie:",
                available_columns,
                default=[available_columns[0]] if available_columns else [],
                key="multi_y_t2"
            )

            if selected_params_t2:
                fig_t2 = make_subplots(
                    rows=len(selected_params_t2), cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.08,
                    subplot_titles=[f"Przebieg: {p} (Tło vs Wyróżnienie)" for p in selected_params_t2]
                )

                matched_df = data[mask_t2]

                for idx_p, param in enumerate(selected_params_t2, start=1):
                    # Tło: Wszystkie dane wygaszone
                    fig_t2.add_trace(
                        go.Scatter(
                            x=data[time_column], y=data[param],
                            mode='lines+markers',
                            name=f"{param} (Wszystkie)",
                            line=dict(color='#CFD8DC', width=1.5),
                            marker=dict(color='#90A4AE', size=3, opacity=0.4)
                        ),
                        row=idx_p, col=1
                    )

                    # Nakładka: Punkty spełniające warunki (Neonowa Czerwień z białą obwódką)
                    if len(matched_df) > 0:
                        fig_t2.add_trace(
                            go.Scatter(
                                x=matched_df[time_column], y=matched_df[param],
                                mode='markers',
                                name=f"🎯 {param} (Dopasowanie)",
                                marker=dict(
                                    color='#FF1744',
                                    size=10,
                                    symbol='circle',
                                    line=dict(color='#FFFFFF', width=1.5)
                                )
                            ),
                            row=idx_p, col=1
                        )

                fig_t2.update_layout(height=320 * len(selected_params_t2), hovermode="x unified")
                fig_t2.update_xaxes(rangeslider_visible=True, row=len(selected_params_t2), col=1)
                st.plotly_chart(fig_t2, use_container_width=True)