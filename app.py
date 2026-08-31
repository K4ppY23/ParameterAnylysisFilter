import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import uuid

st.set_page_config(page_title="Zaawansowany Analizator GPS", layout="wide")
st.title("🛰️ Zaawansowany Analizator Danych GPS")


# -----------------------------------------------------------------------------
# POMOCNICZE FUNKCJE LOGICZNE
# -----------------------------------------------------------------------------
def evaluate_conditions(df, time_col, start_dt, end_dt, conditions):
    """Ewaluuje listę warunków z uwzględnieniem operatorów AND, OR, XOR."""
    time_mask = (df[time_col] >= pd.to_datetime(start_dt)) & (df[time_col] <= pd.to_datetime(end_dt))

    if not conditions:
        return time_mask

    accumulated_mask = None

    for idx, cond in enumerate(conditions):
        col = cond['column']
        op = cond['operator']
        val = cond['value']

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


def get_default_chart_params(conditions, available_cols):
    """Zwraca parametry użyte w warunkach jako domyślne dla wykresu."""
    used_cols = [c['column'] for c in conditions if c.get('column') in available_cols]
    unique_cols = list(dict.fromkeys(used_cols))
    return unique_cols if unique_cols else ([available_cols[0]] if available_cols else [])


# -----------------------------------------------------------------------------
# IMPORT PLIKU CSV
# -----------------------------------------------------------------------------
uploaded_file = st.file_uploader("Wczytaj plik CSV z urządzenia GPS", type=["csv"])

if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)

    st.sidebar.header("⚙️ Konfiguracja Danych")
    time_column = st.sidebar.selectbox("Kolumna reprezentująca czas:", data.columns)
    data[time_column] = pd.to_datetime(data[time_column], errors='coerce')
    data = data.sort_values(by=time_column).reset_index(drop=True)

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

        st.markdown("#### Warunki wycinania (AND / OR / XOR)")
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
                slog = c_log.selectbox(f"Łącznik #{idx + 1}", ["AND", "OR", "XOR"],
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

        tab_t1_grid, tab_t1_chart = st.tabs(["📋 Tabela Wyników", "📈 Wykresy i Odczyt Czasowy"])

        with tab_t1_grid:
            st.dataframe(df_t1, use_container_width=True)

        with tab_t1_chart:
            defaults_t1 = get_default_chart_params(st.session_state.filter_conditions_t1, available_columns)

            col_sel, col_mode = st.columns([3, 1])
            selected_params_t1 = col_sel.multiselect(
                "Wybierz parametry do wyświetlenia:",
                available_columns,
                default=defaults_t1,
                key="multi_y_t1"
            )
            chart_mode_t1 = col_mode.radio("Typ wykresu:", ["Subplots (Osobne)", "Połączony (Jedna oś)"], key="mode_t1")

            # Sekcja wprowadzania daty i godziny dla wskazówki
            st.markdown("---")
            c_input_dt, c_info = st.columns([2, 3])

            min_t1_time = df_t1[time_column].min() if not df_t1.empty else data[time_column].min()
            max_t1_time = df_t1[time_column].max() if not df_t1.empty else data[time_column].max()

            user_target_dt_t1 = c_input_dt.datetime_input(
                "⏱️ Wpisz/wybierz datę i godzinę wskazówki (naciśnij Enter):",
                value=min_t1_time,
                key="dt_picker_t1"
            )

            if selected_params_t1 and not df_t1.empty:
                # Wyszukiwanie odczytu w tabeli dla wpisanej godziny
                time_diffs_t1 = (df_t1[time_column] - pd.to_datetime(user_target_dt_t1)).abs()
                nearest_idx_t1 = time_diffs_t1.idxmin()
                found_row_t1 = df_t1.loc[nearest_idx_t1]
                actual_dt_t1 = found_row_t1[time_column]

                with c_info:
                    st.info(f"📍 **Wskazówka na:** `{pd.to_datetime(actual_dt_t1).strftime('%Y-%m-%d %H:%M:%S')}`")

                # Rysowanie wykresu bez kropek (mode='lines')
                if chart_mode_t1 == "Subplots (Osobne)":
                    fig_t1 = make_subplots(
                        rows=len(selected_params_t1), cols=1,
                        shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=[f"Przebieg: {p}" for p in selected_params_t1]
                    )
                    for idx_p, param in enumerate(selected_params_t1, start=1):
                        fig_t1.add_trace(
                            go.Scatter(x=df_t1[time_column], y=df_t1[param], mode='lines', name=param,
                                       line=dict(width=2)),
                            row=idx_p, col=1
                        )
                    fig_t1.add_vline(x=str(actual_dt_t1), line_width=2, line_dash="dash", line_color="#FF1744")
                    fig_t1.update_layout(height=280 * len(selected_params_t1), hovermode="x unified")
                else:
                    norm_t1 = st.checkbox("Normalizuj wartości (0 - 100%)", key="norm_t1")
                    fig_t1 = go.Figure()
                    for param in selected_params_t1:
                        y_data = df_t1[param]
                        if norm_t1 and y_data.max() != y_data.min():
                            y_plot = (y_data - y_data.min()) / (y_data.max() - y_data.min()) * 100
                            ht = f"<b>{param}</b>: %{{customdata:.2f}}<br>Znorm.: %{{y:.1f}}%<extra></extra>"
                        else:
                            y_plot = y_data
                            ht = f"<b>{param}</b>: %{{y:.2f}}<extra></extra>"

                        fig_t1.add_trace(
                            go.Scatter(x=df_t1[time_column], y=y_plot, mode='lines', name=param, customdata=y_data,
                                       hovertemplate=ht))

                    fig_t1.add_vline(x=str(actual_dt_t1), line_width=2, line_dash="dash", line_color="#FF1744")
                    fig_t1.update_layout(height=500, hovermode="x unified",
                                         legend=dict(title="Kliknij, aby ukryć/pokazać"))

                st.plotly_chart(fig_t1, use_container_width=True)

                # Panel z wynikami parametrów w miejscu wskazówki
                st.markdown(
                    f"##### 📊 Odczyt wybranych parametrów z godziny `{pd.to_datetime(actual_dt_t1).strftime('%Y-%m-%d %H:%M:%S')}`:")
                readout_cols = st.columns(min(len(selected_params_t1), 4))
                for i, param in enumerate(selected_params_t1):
                    val = found_row_t1[param]
                    readout_cols[i % 4].metric(label=param,
                                               value=f"{val:.2f}" if isinstance(val, (int, float)) else str(val))

    # =========================================================================
    # ZAKŁADKA 2: PODŚWIETLANIE I OZNACZANIE NA PEŁNYCH DANYCH
    # =========================================================================
    with main_tab2:
        st.header("Wyróżnianie wartości na tle wszystkich danych")
        st.info(
            "💡 W tym trybie widoczne są WSZYSTKIE dane. Przefiltrowane rekordy zostaną wyróżnione ramką w tabeli oraz wskazówką na wykresie.")

        if 'filter_conditions_t2' not in st.session_state:
            st.session_state.filter_conditions_t2 = [
                {'id': str(uuid.uuid4()), 'logic_op': 'AND', 'column': available_columns[0], 'operator': '>',
                 'value': 0.0}
            ]

        with st.expander("📅 Zakres czasowy", expanded=False):
            c1_2, c2_2 = st.columns(2)
            start_dt_t2 = c1_2.datetime_input("Czas OD (T2):", data[time_column].min(), key="t2_dt1")
            end_dt_t2 = c2_2.datetime_input("Czas DO (T2):", data[time_column].max(), key="t2_dt2")

        st.markdown("#### Warunki wyróżnienia (AND / OR / XOR)")
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
                slog = c_log.selectbox(f"Łącznik #{idx + 1}", ["AND", "OR", "XOR"],
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

        tab_t2_grid, tab_t2_chart = st.tabs([
            "📋 Tabela z Wyrazistym Obramowaniem",
            "📈 Wykres z Wskazówką Czasową"
        ])

        # ---------------------------------------------------------------------
        # TABELA Z WYRAZISTYM OBRAMOWANIEM KOMÓREK
        # ---------------------------------------------------------------------
        with tab_t2_grid:
            df_display = data.copy()
            df_display.insert(0, "Status", ["🎯 SPEŁNIA WARUNKI" if m else "⚪ STANDARD" for m in mask_t2])


            def style_high_contrast_v3(row):
                if row["Status"] == "🎯 SPEŁNIA WARUNKI":
                    return [
                        'background-color: #E8F5E9; '
                        'color: #1B5E20; '
                        'font-weight: bold; '
                        'border: 2px solid #2E7D32;'
                        for _ in row
                    ]
                return [
                    'background-color: #FAFAFA; '
                    'color: #757575; '
                    'border: 1px solid #E0E0E0;'
                    for _ in row
                ]


            styled_df = df_display.style.apply(style_high_contrast_v3, axis=1)
            st.dataframe(styled_df, use_container_width=True)

        # ---------------------------------------------------------------------
        # WYKRES OVERLAY Z WSKAZÓWKĄ CZASOWĄ I ODCZYTEM
        # ---------------------------------------------------------------------
        with tab_t2_chart:
            defaults_t2 = get_default_chart_params(st.session_state.filter_conditions_t2, available_columns)

            col_sel_2, col_mode_2 = st.columns([3, 1])
            selected_params_t2 = col_sel_2.multiselect(
                "Wybierz parametry do wyświetlenia na wykresie:",
                available_columns,
                default=defaults_t2,
                key="multi_y_t2"
            )
            chart_mode_t2 = col_mode_2.radio("Typ wykresu:", ["Subplots (Osobne)", "Połączony (Jedna oś)"],
                                             key="mode_t2")

            # Sekcja wprowadzania daty i godziny dla wskazówki
            st.markdown("---")
            c_input_dt2, c_info2 = st.columns([2, 3])

            user_target_dt_t2 = c_input_dt2.datetime_input(
                "⏱️ Wpisz/wybierz datę i godzinę wskazówki (naciśnij Enter):",
                value=data[time_column].min(),
                key="dt_picker_t2"
            )

            if selected_params_t2:
                # Wyszukiwanie najbliższego odczytu w bazie danych
                time_diffs_t2 = (data[time_column] - pd.to_datetime(user_target_dt_t2)).abs()
                nearest_idx_t2 = time_diffs_t2.idxmin()
                found_row_t2 = data.loc[nearest_idx_t2]
                actual_dt_t2 = found_row_t2[time_column]
                is_matched_dt = mask_t2.iloc[nearest_idx_t2]

                with c_info2:
                    status_text = "🎯 SPEŁNIA WARUNKI" if is_matched_dt else "⚪ STAN STANDARDOWY"
                    st.info(
                        f"📍 **Wskazówka na:** `{pd.to_datetime(actual_dt_t2).strftime('%Y-%m-%d %H:%M:%S')}` | **Status:** `{status_text}`")

                # Generowanie wykresu bez kropek (mode='lines')
                if chart_mode_t2 == "Subplots (Osobne)":
                    fig_t2 = make_subplots(
                        rows=len(selected_params_t2), cols=1,
                        shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=[f"Przebieg: {p}" for p in selected_params_t2]
                    )
                    for idx_p, param in enumerate(selected_params_t2, start=1):
                        fig_t2.add_trace(
                            go.Scatter(x=data[time_column], y=data[param], mode='lines', name=param,
                                       line=dict(width=2)),
                            row=idx_p, col=1
                        )
                    fig_t2.add_vline(x=str(actual_dt_t2), line_width=2, line_dash="dash", line_color="#FF1744")
                    fig_t2.update_layout(height=300 * len(selected_params_t2), hovermode="x unified")
                else:
                    norm_t2 = st.checkbox("Normalizuj wartości (0 - 100%)", key="norm_t2")
                    fig_t2 = go.Figure()
                    for param in selected_params_t2:
                        y_all = data[param]
                        if norm_t2 and y_all.max() != y_all.min():
                            y_plot_all = (y_all - y_all.min()) / (y_all.max() - y_all.min()) * 100
                            ht_all = f"<b>{param}</b>: %{{customdata:.2f}}<br>Znorm.: %{{y:.1f}}%<extra></extra>"
                        else:
                            y_plot_all = y_all
                            ht_all = f"<b>{param}</b>: %{{y:.2f}}<extra></extra>"

                        fig_t2.add_trace(go.Scatter(
                            x=data[time_column], y=y_plot_all, mode='lines', name=param,
                            customdata=y_all, hovertemplate=ht_all
                        ))

                    fig_t2.add_vline(x=str(actual_dt_t2), line_width=2, line_dash="dash", line_color="#FF1744")
                    fig_t2.update_layout(height=520, hovermode="x unified",
                                         legend=dict(title="Kliknij, aby ukryć/pokazać"))

                st.plotly_chart(fig_t2, use_container_width=True)

                # Panel z wynikami parametrów w miejscu wskazówki
                st.markdown(
                    f"##### 📊 Odczyt wszystkich wybranych parametrów z godziny `{pd.to_datetime(actual_dt_t2).strftime('%Y-%m-%d %H:%M:%S')}`:")
                readout_cols2 = st.columns(min(len(selected_params_t2), 4))
                for i, param in enumerate(selected_params_t2):
                    val = found_row_t2[param]
                    readout_cols2[i % 4].metric(label=param,
                                                value=f"{val:.2f}" if isinstance(val, (int, float)) else str(val))