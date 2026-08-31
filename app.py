import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import uuid

# Configuration
st.set_page_config(page_title="Zaawansowany Analizator GPS", layout="wide")
st.title("🛰️ Zaawansowany Analizator Danych GPS")


# -----------------------------------------------------------------------------
# POMOCNICZE FUNKCJE LOGICZNE I STYLOWANIA
# -----------------------------------------------------------------------------
def evaluate_conditions(df, time_col, start_dt, end_dt, conditions):
    """Ewaluuje zdefiniowane warunki logiczne na ramce danych."""
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
    """Dobiera domyślne parametry na wykres na podstawie użytych w filtrach."""
    used_cols = [c['column'] for c in conditions if c.get('column') in available_cols]
    unique_cols = list(dict.fromkeys(used_cols))
    return unique_cols if unique_cols else ([available_cols[0]] if available_cols else [])


def extract_selection_mask(df, time_col, event_data):
    """Wyciąga maskę zaznaczonych wierszy z obiektu zdarzenia zaznaczenia Plotly."""
    if not event_data or "selection" not in event_data:
        return pd.Series(False, index=df.index)

    sel = event_data["selection"]

    # 1. Zaznaczenie zakresem (Box select / range zoom)
    if "range" in sel and sel["range"] and "x" in sel["range"]:
        x_range = sel["range"]["x"]
        if len(x_range) >= 2:
            start_x = pd.to_datetime(x_range[0])
            end_x = pd.to_datetime(x_range[1])
            return (df[time_col] >= start_x) & (df[time_col] <= end_x)

    # 2. Zaznaczenie punktowe (Lasso / Box point select)
    if "points" in sel and len(sel["points"]) > 0:
        indices = [p["point_index"] for p in sel["points"] if "point_index" in p]
        if indices:
            return df.index.isin(indices)
        x_vals = [pd.to_datetime(p["x"]) for p in sel["points"] if "x" in p]
        if x_vals:
            return df[time_col].isin(x_vals)

    return pd.Series(False, index=df.index)


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
            st.session_state.filtered_df_t1 = data[mask_t1].copy().reset_index(drop=True)

        df_t1 = st.session_state.filtered_df_t1
        st.subheader(f"Wyniki (Przefiltrowano {len(df_t1)} z {len(data)} rekordów)")

        # --- SEKCJA WYKRESU W JEDNYM WIDOKU ---
        defaults_t1 = get_default_chart_params(st.session_state.filter_conditions_t1, available_columns)

        col_sel, col_mode = st.columns([3, 1])
        selected_params_t1 = col_sel.multiselect(
            "Wybierz parametry do wyświetlenia na wykresie:",
            available_columns,
            default=defaults_t1,
            key="multi_y_t1"
        )
        chart_mode_t1 = col_mode.radio("Typ wykresu:", ["Subplots (Osobne)", "Połączony (Jedna oś)"], key="mode_t1")

        c_input_dt, c_info = st.columns([2, 3])
        min_t1_time = df_t1[time_column].min() if not df_t1.empty else data[time_column].min()

        user_target_dt_t1 = c_input_dt.datetime_input(
            "⏱️ Wpisz/wybierz datę i godzinę wskazówki (naciśnij Enter):",
            value=min_t1_time,
            key="dt_picker_t1"
        )

        chart_event_t1 = None

        if selected_params_t1 and not df_t1.empty:
            time_diffs_t1 = (df_t1[time_column] - pd.to_datetime(user_target_dt_t1)).abs()
            nearest_idx_t1 = time_diffs_t1.idxmin()
            found_row_t1 = df_t1.loc[nearest_idx_t1]
            actual_dt_t1 = found_row_t1[time_column]

            with c_info:
                st.info(f"📍 **Wskazówka na:** `{pd.to_datetime(actual_dt_t1).strftime('%Y-%m-%d %H:%M:%S')}`")

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
                fig_t1.update_layout(height=480, hovermode="x unified", legend=dict(title="Kliknij, aby ukryć/pokazać"))

            # Przechwytywanie zaznaczenia z narzędzi Box Select / Lasso Select
            chart_event_t1 = st.plotly_chart(
                fig_t1,
                use_container_width=True,
                on_select="rerun",
                selection_mode=["box", "lasso"],
                key="plotly_t1"
            )

            # Odczyt parametrów z punktu wskazówki
            st.markdown(
                f"##### 📊 Odczyt parametrów z punktu czasowego `{pd.to_datetime(actual_dt_t1).strftime('%Y-%m-%d %H:%M:%S')}`:")
            readout_cols = st.columns(min(len(selected_params_t1), 4))
            for i, param in enumerate(selected_params_t1):
                val = found_row_t1[param]
                readout_cols[i % 4].metric(label=param,
                                           value=f"{val:.2f}" if isinstance(val, (int, float)) else str(val))

        # --- SEKCJA ESTETYCZNIE STYLOWANEJ TABELI DANYCH ---
        st.markdown("---")
        st.markdown("### 📋 Tabela Danych (Podświetlanie Zaznaczenia z Wykresu)")

        # Ekstrakcja zaznaczenia z wykresu
        chart_sel_mask_t1 = extract_selection_mask(df_t1, time_column, chart_event_t1)

        if chart_sel_mask_t1.sum() > 0:
            st.success(
                f"🎯 **Zaznaczono na wykresie {chart_sel_mask_t1.sum()} rekordów.** Odpowiednie komórki/wiersze zostały wyróżnione na złoto poniżej.")
        else:
            st.caption(
                "💡 *Wskazówka: Zaznacz obszar na wykresie powyżej za pomocą narzędzia Box Select lub Lasso Select, aby podświetlić te dane w tabeli.*")


        # Funkcja dekorująca i kolorująca tabelę dla Trybu 1
        def style_t1_table(df, sel_mask):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            for idx in df.index:
                if sel_mask.loc[idx]:
                    # Zaznaczony obszar z wykresu: Złote tło z kontrastową ramką
                    styles.loc[
                        idx] = 'background-color: #FFF59D; color: #B71C1C; font-weight: bold; border: 2px solid #F57F17;'
                else:
                    # Estetyczny, naprzemienny niebieski styl dla Trybu 1
                    if idx % 2 == 0:
                        styles.loc[idx] = 'background-color: #F0F7FF; color: #0D47A1; border: 1px solid #D0E1F9;'
                    else:
                        styles.loc[idx] = 'background-color: #FFFFFF; color: #1565C0; border: 1px solid #E3F2FD;'
            return styles


        styled_t1 = df_t1.style.apply(lambda r: style_t1_table(df_t1, chart_sel_mask_t1).loc[r.name], axis=1)
        st.dataframe(styled_t1, use_container_width=True)

    # =========================================================================
    # ZAKŁADKA 2: PODŚWIETLANIE I OZNACZANIE NA PEŁNYCH DANYCH
    # =========================================================================
    with main_tab2:
        st.header("Wyróżnianie wartości na tle wszystkich danych")
        st.info(
            "💡 Wszystkie dane są widoczne w jednym miejscu. Rekordy spełniające filtry są oznaczone na zielono, a obszar zaznaczony na wykresie – na złoto.")

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

        # --- SEKCJA WYKRESU I ODZYTU (BEZ PRZEŁĄCZANIA ZAKŁADEK) ---
        defaults_t2 = get_default_chart_params(st.session_state.filter_conditions_t2, available_columns)

        col_sel_2, col_mode_2 = st.columns([3, 1])
        selected_params_t2 = col_sel_2.multiselect(
            "Wybierz parametry do wyświetlenia na wykresie:",
            available_columns,
            default=defaults_t2,
            key="multi_y_t2"
        )
        chart_mode_t2 = col_mode_2.radio("Typ wykresu:", ["Subplots (Osobne)", "Połączony (Jedna oś)"], key="mode_t2")

        c_input_dt2, c_info2 = st.columns([2, 3])
        user_target_dt_t2 = c_input_dt2.datetime_input(
            "⏱️ Wpisz/wybierz datę i godzinę wskazówki (naciśnij Enter):",
            value=data[time_column].min(),
            key="dt_picker_t2"
        )

        chart_event_t2 = None

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
                fig_t2.update_layout(height=500, hovermode="x unified", legend=dict(title="Kliknij, aby ukryć/pokazać"))

            chart_event_t2 = st.plotly_chart(
                fig_t2,
                use_container_width=True,
                on_select="rerun",
                selection_mode=["box", "lasso"],
                key="plotly_t2"
            )

            st.markdown(
                f"##### 📊 Odczyt parametrów z punktu czasowego `{pd.to_datetime(actual_dt_t2).strftime('%Y-%m-%d %H:%M:%S')}`:")
            readout_cols2 = st.columns(min(len(selected_params_t2), 4))
            for i, param in enumerate(selected_params_t2):
                val = found_row_t2[param]
                readout_cols2[i % 4].metric(label=param,
                                            value=f"{val:.2f}" if isinstance(val, (int, float)) else str(val))

        # --- SEKCJA TABELI DANYCH Z PODWÓJNYM HIGHLIGHTEM ---
        st.markdown("---")
        st.markdown("### 📋 Tabela Danych (Podświetlanie Warunkowe + Zaznaczenie z Wykresu)")

        chart_sel_mask_t2 = extract_selection_mask(data, time_column, chart_event_t2)

        if chart_sel_mask_t2.sum() > 0:
            st.success(
                f"🎯 **Zaznaczono na wykresie {chart_sel_mask_t2.sum()} rekordów.** Odpowiednie wiersze zostały wyróżnione poniżej.")
        else:
            st.caption(
                "💡 *Użyj narzędzia zaznaczania (Box Select / Lasso Select) na wykresie powyżej, aby dynamicznie podświetlić konkretne wiersze w tabeli.*")

        df_display_t2 = data.copy()
        df_display_t2.insert(0, "Status", ["🎯 SPEŁNIA WARUNKI" if m else "⚪ STANDARD" for m in mask_t2])


        def style_t2_table_combined(df, match_mask, sel_mask):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            for idx in df.index:
                is_m = match_mask.loc[idx]
                is_s = sel_mask.loc[idx]

                if is_m and is_s:
                    # Spełnia warunek ORAZ zaznaczony na wykresie -> Złoto-czerwony z grubą obramówką
                    styles.loc[
                        idx] = 'background-color: #FFF176; color: #880E4F; font-weight: bold; border: 3px solid #D50000;'
                elif is_s:
                    # Zaznaczony tylko na wykresie -> Złoty z pomarańczową obramówką
                    styles.loc[
                        idx] = 'background-color: #FFF59D; color: #E65100; font-weight: bold; border: 2px solid #F57C00;'
                elif is_m:
                    # Spełnia warunek filtru -> Wyrazista zielona ramka i jasnozielone tło
                    styles.loc[
                        idx] = 'background-color: #E8F5E9; color: #1B5E20; font-weight: bold; border: 2px solid #2E7D32;'
                else:
                    # Standardowy wiersz
                    styles.loc[idx] = 'background-color: #FAFAFA; color: #757575; border: 1px solid #E0E0E0;'
            return styles


        styled_t2 = df_display_t2.style.apply(
            lambda r: style_t2_table_combined(df_display_t2, mask_t2, chart_sel_mask_t2).loc[r.name], axis=1)
        st.dataframe(styled_t2, use_container_width=True)