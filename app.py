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


def extract_selected_timestamps(select_event):
    """Wyciąga zestaw timestampów zaznaczonych na wykresie przez użytkownika."""
    selected_set = set()
    if select_event and "selection" in select_event and "points" in select_event["selection"]:
        for pt in select_event["selection"]["points"]:
            if "x" in pt:
                try:
                    dt_str = str(pd.to_datetime(pt["x"]))
                    selected_set.add(dt_str)
                except Exception:
                    pass
    return selected_set


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

        # ---------------------------------------------------------------------
        # SEKCJA WYKRESU I ODCZYTU CZASOWEGO
        # ---------------------------------------------------------------------
        defaults_t1 = get_default_chart_params(st.session_state.filter_conditions_t1, available_columns)

        col_sel, col_mode = st.columns([3, 1])
        selected_params_t1 = col_sel.multiselect(
            "Wybierz parametry do wyświetlenia na wykresie:",
            available_columns,
            default=defaults_t1,
            key="multi_y_t1"
        )
        chart_mode_t1 = col_mode.radio("Typ wykresu:", ["Subplots (Osobne)", "Połączony (Jedna oś)"], key="mode_t1")

        st.markdown("---")
        st.caption(
            "💡 **Interaktywne zaznaczanie:** Użyj narzędzia `Box Select` lub `Lasso Select` w prawym górnym rogu wykresu, aby podświetlić te punkty na pomarańczowo w tabeli poniżej.")

        c_input_dt, c_info = st.columns([2, 3])
        min_t1_time = df_t1[time_column].min() if not df_t1.empty else data[time_column].min()

        user_target_dt_t1 = c_input_dt.datetime_input(
            "⏱️ Wpisz/wybierz datę i godzinę wskazówki (naciśnij Enter):",
            value=min_t1_time,
            key="dt_picker_t1"
        )

        selected_ts_t1 = set()
        if selected_params_t1 and not df_t1.empty:
            time_diffs_t1 = (df_t1[time_column] - pd.to_datetime(user_target_dt_t1)).abs()
            nearest_idx_t1 = time_diffs_t1.idxmin()
            found_row_t1 = df_t1.loc[nearest_idx_t1]
            actual_dt_t1 = found_row_t1[time_column]

            with c_info:
                st.info(f"📍 **Wskazówka na:** `{pd.to_datetime(actual_dt_t1).strftime('%Y-%m-%d %H:%M:%S')}`")

            # Tworzenie wykresu Plotly (linie bez punktów)
            if chart_mode_t1 == "Subplots (Osobne)":
                fig_t1 = make_subplots(
                    rows=len(selected_params_t1), cols=1,
                    shared_xaxes=True, vertical_spacing=0.08,
                    subplot_titles=[f"Przebieg: {p}" for p in selected_params_t1]
                )
                for idx_p, param in enumerate(selected_params_t1, start=1):
                    fig_t1.add_trace(
                        go.Scatter(x=df_t1[time_column], y=df_t1[param], mode='lines', name=param, line=dict(width=2)),
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
                fig_t1.update_layout(height=500, hovermode="x unified", legend=dict(title="Kliknij, aby ukryć/pokazać"))

            # Zdarzenie zaznaczenia na wykresie
            select_event_t1 = st.plotly_chart(
                fig_t1,
                use_container_width=True,
                on_select="rerun",
                selection_mode=["box", "lasso"],
                key="chart_plotly_t1"
            )
            selected_ts_t1 = extract_selected_timestamps(select_event_t1)

            # Panel odczytu z godziny wskazówki
            st.markdown(
                f"##### 📊 Odczyt wybranych parametrów z godziny `{pd.to_datetime(actual_dt_t1).strftime('%Y-%m-%d %H:%M:%S')}`:")
            readout_cols = st.columns(min(len(selected_params_t1), 4))
            for i, param in enumerate(selected_params_t1):
                val = found_row_t1[param]
                readout_cols[i % 4].metric(label=param,
                                           value=f"{val:.2f}" if isinstance(val, (int, float)) else str(val))

        # ---------------------------------------------------------------------
        # STYLOWY WIDOK TABELARYCZNY Z PODŚWIETLENIEM ZAZNACZENIA
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.markdown("### 📋 Tabela Wyników")
        if selected_ts_t1:
            st.success(
                f"🔍 **Zaznaczono {len(selected_ts_t1)} punktów na wykresie** (podświetlone na pomarańczowo w tabeli)")

        df_t1_disp = df_t1.copy()


        def style_tryb1_table(row):
            ts_str = str(pd.to_datetime(row[time_column]))
            is_selected = ts_str in selected_ts_t1
            if is_selected:
                # Zaznaczone na wykresie -> Akcent bursztynowy / pomarańczowy
                return [
                    'background-color: #FFF3E0; '
                    'color: #D35400; '
                    'font-weight: bold; '
                    'border: 2px solid #E67E22;'
                    for _ in row
                ]
            else:
                # Estetyczny niebieskawo-szary odcień dla standardowych wierszy tabeli
                bg_color = '#F4F6F7' if (row.name % 2 == 0) else '#EBF5FB'
                return [
                    f'background-color: {bg_color}; '
                    'color: #1B4F72; '
                    'border: 1px solid #D5D8DC;'
                    for _ in row
                ]


        styled_t1 = df_t1_disp.style.apply(style_tryb1_table, axis=1)
        st.dataframe(styled_t1, use_container_width=True)

    # =========================================================================
    # ZAKŁADKA 2: PODŚWIETLANIE I OZNACZANIE NA PEŁNYCH DANYCH
    # =========================================================================
    with main_tab2:
        st.header("Wyróżnianie wartości na tle wszystkich danych")
        st.info(
            "💡 W tym trybie widoczne są WSZYSTKIE dane. Przefiltrowane rekordy oraz punkty zaznaczone na wykresie zostaną podświetlone w tabeli poniżej.")

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
            f"**Wyróżniono {matched_count} z {len(data)} rekordów przez warunki** (Dopasowanie: {matched_count / len(data) * 100:.1f}%)")

        # ---------------------------------------------------------------------
        # WIDOK WYKRESU I ODZYTU W JEDNYM WIDOKU
        # ---------------------------------------------------------------------
        defaults_t2 = get_default_chart_params(st.session_state.filter_conditions_t2, available_columns)

        col_sel_2, col_mode_2 = st.columns([3, 1])
        selected_params_t2 = col_sel_2.multiselect(
            "Wybierz parametry do wyświetlenia na wykresie:",
            available_columns,
            default=defaults_t2,
            key="multi_y_t2"
        )
        chart_mode_t2 = col_mode_2.radio("Typ wykresu:", ["Subplots (Osobne)", "Połączony (Jedna oś)"], key="mode_t2")

        st.markdown("---")
        st.caption(
            "💡 **Interaktywne zaznaczanie:** Użyj narzędzia `Box Select` lub `Lasso Select` na wykresie, aby równocześnie podświetlić te serie w tabeli poniżej odrębnym kolorem!")

        c_input_dt2, c_info2 = st.columns([2, 3])
        user_target_dt_t2 = c_input_dt2.datetime_input(
            "⏱️ Wpisz/wybierz datę i godzinę wskazówki (naciśnij Enter):",
            value=data[time_column].min(),
            key="dt_picker_t2"
        )

        selected_ts_t2 = set()
        if selected_params_t2:
            time_diffs_t2 = (data[time_column] - pd.to_datetime(user_target_dt_t2)).abs()
            nearest_idx_t2 = time_diffs_t2.idxmin()
            found_row_t2 = data.loc[nearest_idx_t2]
            actual_dt_t2 = found_row_t2[time_column]
            is_matched_dt = mask_t2.iloc[nearest_idx_t2]

            with c_info2:
                status_text = "🎯 SPEŁNIA WARUNKI" if is_matched_dt else "⚪ STAN STANDARDOWY"
                st.info(
                    f"📍 **Wskazówka na:** `{pd.to_datetime(actual_dt_t2).strftime('%Y-%m-%d %H:%M:%S')}` | **Status:** `{status_text}`")

            # Wykres Plotly
            if chart_mode_t2 == "Subplots (Osobne)":
                fig_t2 = make_subplots(
                    rows=len(selected_params_t2), cols=1,
                    shared_xaxes=True, vertical_spacing=0.08,
                    subplot_titles=[f"Przebieg: {p}" for p in selected_params_t2]
                )
                for idx_p, param in enumerate(selected_params_t2, start=1):
                    fig_t2.add_trace(
                        go.Scatter(x=data[time_column], y=data[param], mode='lines', name=param, line=dict(width=2)),
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
                fig_t2.update_layout(height=520, hovermode="x unified", legend=dict(title="Kliknij, aby ukryć/pokazać"))

            select_event_t2 = st.plotly_chart(
                fig_t2,
                use_container_width=True,
                on_select="rerun",
                selection_mode=["box", "lasso"],
                key="chart_plotly_t2"
            )
            selected_ts_t2 = extract_selected_timestamps(select_event_t2)

            # Panel odczytu z godziny wskazówki
            st.markdown(
                f"##### 📊 Odczyt wszystkich wybranych parametrów z godziny `{pd.to_datetime(actual_dt_t2).strftime('%Y-%m-%d %H:%M:%S')}`:")
            readout_cols2 = st.columns(min(len(selected_params_t2), 4))
            for i, param in enumerate(selected_params_t2):
                val = found_row_t2[param]
                readout_cols2[i % 4].metric(label=param,
                                            value=f"{val:.2f}" if isinstance(val, (int, float)) else str(val))

        # ---------------------------------------------------------------------
        # TABELA Z MULTI-KOLOROWYM PODŚWIETLANIEM (FILTR + ZAZNACZENIE Z WYKRESU)
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.markdown("### 📋 Tabela z Wyróżnionymi i Zaznaczonymi Danymi")

        df_display = data.copy()

        status_list = []
        for i, m in enumerate(mask_t2):
            ts_str = str(pd.to_datetime(df_display.iloc[i][time_column]))
            is_sel = ts_str in selected_ts_t2

            if m and is_sel:
                status_list.append("🎯 SPEŁNIA + 🔍 ZAZNACZONE")
            elif is_sel:
                status_list.append("🔍 ZAZNACZONE NA WYKRESIE")
            elif m:
                status_list.append("🎯 SPEŁNIA WARUNKI")
            else:
                status_list.append("⚪ STANDARD")

        df_display.insert(0, "Status", status_list)


        def style_multi_highlight(row):
            st_val = row["Status"]
            if st_val == "🎯 SPEŁNIA + 🔍 ZAZNACZONE":
                # Fioletowy / Purpurowy - Synergia filtra i zaznaczenia na wykresie
                return [
                    'background-color: #F3E5F5; '
                    'color: #4A148C; '
                    'font-weight: bold; '
                    'border: 2px solid #8E24AA;'
                    for _ in row
                ]
            elif st_val == "🔍 ZAZNACZONE NA WYKRESIE":
                # Bursztynowy / Pomarańczowy - Tylko zaznaczenie z wykresu
                return [
                    'background-color: #FFF3E0; '
                    'color: #E65100; '
                    'font-weight: bold; '
                    'border: 2px solid #FB8C00;'
                    for _ in row
                ]
            elif st_val == "🎯 SPEŁNIA WARUNKI":
                # Wyrazisty Ciemnozielony - Spełniony warunek filtra
                return [
                    'background-color: #E8F5E9; '
                    'color: #1B5E20; '
                    'font-weight: bold; '
                    'border: 2px solid #2E7D32;'
                    for _ in row
                ]
            else:
                # Standardowy neutralny wiersz
                return [
                    'background-color: #FAFAFA; '
                    'color: #616161; '
                    'border: 1px solid #E0E0E0;'
                    for _ in row
                ]


        styled_t2 = df_display.style.apply(style_multi_highlight, axis=1)
        st.dataframe(styled_t2, use_container_width=True)