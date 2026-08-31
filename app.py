import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import uuid

st.set_page_config(page_title="Analizator GPS z Wyróżnianiem", layout="wide")
st.title("🛰️ Analizator Danych GPS")

# 1. Import pliku CSV z urządzenia GPS
uploaded_file = st.file_uploader("Wczytaj plik CSV z urządzenia GPS", type=["csv"])

if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)

    st.sidebar.header("⚙️ Konfiguracja danych")
    time_column = st.sidebar.selectbox("Kolumna reprezentująca czas:", data.columns)
    data[time_column] = pd.to_datetime(data[time_column], errors='coerce')

    numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns.tolist()
    available_columns = numeric_columns if numeric_columns else data.columns.tolist()

    # Dwie główne zakładki trybów pracy
    main_tab1, main_tab2 = st.tabs([
        "✂️ Tryb 1: Ukrywanie niedopasowanych",
        "🎯 Tryb 2: Podświetlanie na pełnych danych"
    ])

    # =========================================================================
    # ZAKŁADKA 1: FILTROWANIE (UKRYWANIE NIEDOPASOWANYCH)
    # =========================================================================
    with main_tab1:
        st.header("Wycinanie / Filtrowanie danych")

        if 'filter_conditions_t1' not in st.session_state:
            st.session_state.filter_conditions_t1 = [
                {'id': str(uuid.uuid4()), 'column': available_columns[0], 'operator': '>', 'value': 0.0}
            ]

        with st.expander("📅 Zakres czasowy", expanded=False):
            c1, c2 = st.columns(2)
            start_dt_t1 = c1.datetime_input("Czas OD (T1):", data[time_column].min(), key="t1_dt1")
            end_dt_t1 = c2.datetime_input("Czas DO (T1):", data[time_column].max(), key="t1_dt2")

        st.markdown("#### Warunki wycinania danych")
        btn_add_t1, btn_clr_t1, _ = st.columns([1, 1, 3])

        if btn_add_t1.button("➕ Dodaj warunek", key="add_t1"):
            st.session_state.filter_conditions_t1.append(
                {'id': str(uuid.uuid4()), 'column': available_columns[0], 'operator': '>', 'value': 0.0}
            )
            st.rerun()

        if btn_clr_t1.button("🗑️ Wyczyść warunki", key="clr_t1"):
            st.session_state.filter_conditions_t1 = []
            st.rerun()

        to_remove_t1 = None
        for idx, cond in enumerate(st.session_state.filter_conditions_t1):
            cid = cond['id']
            c_col, c_op, c_val, c_del = st.columns([3, 2, 3, 1])

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

            cond['column'], cond['operator'], cond['value'] = scol, sop, sval

        if to_remove_t1:
            st.session_state.filter_conditions_t1 = [c for c in st.session_state.filter_conditions_t1 if
                                                     c['id'] != to_remove_t1]
            st.rerun()

        exec_t1 = st.button("🚀 Filtruj i ukryj resztę", type="primary", key="exec_t1", use_container_width=True)

        if 'filtered_df_t1' not in st.session_state:
            st.session_state.filtered_df_t1 = data.copy()

        if exec_t1:
            res = data.copy()
            res = res[
                (res[time_column] >= pd.to_datetime(start_dt_t1)) & (res[time_column] <= pd.to_datetime(end_dt_t1))]
            for c in st.session_state.filter_conditions_t1:
                col, op, val = c['column'], c['operator'], c['value']
                if op == ">":
                    res = res[res[col] > val]
                elif op == "<":
                    res = res[res[col] < val]
                elif op == "=":
                    res = res[res[col] == val]
                elif op == ">=":
                    res = res[res[col] >= val]
                elif op == "<=":
                    res = res[res[col] <= val]
                elif op == "!=":
                    res = res[res[col] != val]
            st.session_state.filtered_df_t1 = res

        df_t1 = st.session_state.filtered_df_t1
        st.subheader(f"Wyniki (Wyselekcjonowano {len(df_t1)} z {len(data)} rekordów)")

        tab_t1_grid, tab_t1_chart = st.tabs(["📋 Tabela", "📈 Wykres"])
        with tab_t1_grid:
            st.dataframe(df_t1, use_container_width=True)
        with tab_t1_chart:
            y_col_t1 = st.selectbox("Parametr na osi Y:", available_columns, key="y_t1")
            fig_t1 = px.line(df_t1, x=time_column, y=y_col_t1, markers=True, title=f"Filtrowany wykres: {y_col_t1}")
            fig_t1.update_xaxes(rangeslider_visible=True)
            st.plotly_chart(fig_t1, use_container_width=True)

    # =========================================================================
    # ZAKŁADKA 2: PODŚWIETLANIE I OZNACZANIE NA PEŁNYCH DANYCH
    # =========================================================================
    with main_tab2:
        st.header("Wyróżnianie wartości na tle wszystkich danych")
        st.info(
            "💡 W tym trybie widoczne są WSZYSTKIE dane. Wybrane warunki zostaną oznaczone kolorem na tabeli i wykresie.")

        if 'filter_conditions_t2' not in st.session_state:
            st.session_state.filter_conditions_t2 = [
                {'id': str(uuid.uuid4()), 'column': available_columns[0], 'operator': '>', 'value': 0.0}
            ]

        with st.expander("📅 Zakres czasowy", expanded=False):
            c1_2, c2_2 = st.columns(2)
            start_dt_t2 = c1_2.datetime_input("Czas OD (T2):", data[time_column].min(), key="t2_dt1")
            end_dt_t2 = c2_2.datetime_input("Czas DO (T2):", data[time_column].max(), key="t2_dt2")

        st.markdown("#### Warunki do wyróżnienia")
        btn_add_t2, btn_clr_t2, _ = st.columns([1, 1, 3])

        if btn_add_t2.button("➕ Dodaj warunek", key="add_t2"):
            st.session_state.filter_conditions_t2.append(
                {'id': str(uuid.uuid4()), 'column': available_columns[0], 'operator': '>', 'value': 0.0}
            )
            st.rerun()

        if btn_clr_t2.button("🗑️ Wyczyść warunki", key="clr_t2"):
            st.session_state.filter_conditions_t2 = []
            st.rerun()

        to_remove_t2 = None
        for idx, cond in enumerate(st.session_state.filter_conditions_t2):
            cid = cond['id']
            c_col, c_op, c_val, c_del = st.columns([3, 2, 3, 1])

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

            cond['column'], cond['operator'], cond['value'] = scol, sop, sval

        if to_remove_t2:
            st.session_state.filter_conditions_t2 = [c for c in st.session_state.filter_conditions_t2 if
                                                     c['id'] != to_remove_t2]
            st.rerun()

        exec_t2 = st.button("🚀 Oznacz / Podświetl dane", type="primary", key="exec_t2", use_container_width=True)

        # Wyznaczenie maski logicznej dla całej tabeli
        mask = (data[time_column] >= pd.to_datetime(start_dt_t2)) & (data[time_column] <= pd.to_datetime(end_dt_t2))

        # Jeśli przycisk kliknięty lub zapytanie jest aktywne
        if len(st.session_state.filter_conditions_t2) > 0:
            for c in st.session_state.filter_conditions_t2:
                col, op, val = c['column'], c['operator'], c['value']
                if op == ">":
                    mask &= (data[col] > val)
                elif op == "<":
                    mask &= (data[col] < val)
                elif op == "=":
                    mask &= (data[col] == val)
                elif op == ">=":
                    mask &= (data[col] >= val)
                elif op == "<=":
                    mask &= (data[col] <= val)
                elif op == "!=":
                    mask &= (data[col] != val)

        matched_count = mask.sum()
        st.markdown(
            f"**Wyróżniono {matched_count} z {len(data)} rekordów** (Dopasowanie: {matched_count / len(data) * 100:.1f}%)")

        tab_t2_grid, tab_t2_chart = st.tabs(["📋 Tabela z podświetleniem", "📈 Wykres z oznaczonymi punktami"])

        # 1. TABELA Z PODŚWIETLANIEM WIERSZY
        with tab_t2_grid:
            df_display = data.copy()
            df_display.insert(0, "Status_Dopasowania", ["🎯 Dopasowany" if m else "⚪ Standard" for m in mask])


            # Funkcja stylująca wiersze w Pandas
            def highlight_matched_rows(row):
                if row["Status_Dopasowania"] == "🎯 Dopasowany":
                    return ['background-color: rgba(46, 204, 113, 0.25); font-weight: bold'] * len(row)
                return [''] * len(row)


            styled_df = df_display.style.apply(highlight_matched_rows, axis=1)
            st.dataframe(styled_df, use_container_width=True)

        # 2. WYKRES Z OZNACZONYMI PUNKTAMI (OVERLAY)
        with tab_t2_chart:
            y_col_t2 = st.selectbox("Parametr na osi Y:", available_columns, key="y_t2")

            fig_t2 = go.Figure()

            # Seria 1: Wszystkie dane (szara ciągła linia tła)
            fig_t2.add_trace(go.Scatter(
                x=data[time_column],
                y=data[y_col_t2],
                mode='lines+markers',
                name='Wszystkie dane',
                line=dict(color='lightgray', width=1.5),
                marker=dict(color='gray', size=4, opacity=0.5)
            ))

            # Seria 2: Wyselekcjonowane punkty (duże czerwone kropki nanieść na tło)
            matched_df = data[mask]
            if len(matched_df) > 0:
                fig_t2.add_trace(go.Scatter(
                    x=matched_df[time_column],
                    y=matched_df[y_col_t2],
                    mode='markers',
                    name='🎯 Spełnia warunki',
                    marker=dict(color='#FF2B2B', size=10, symbol='circle')
                ))

            fig_t2.update_layout(
                title=f"Przebieg parametru {y_col_t2} (Wszystkie punkty + wyróżnienie)",
                xaxis_title="Czas / Godzina",
                yaxis_title=y_col_t2,
                hovermode="x unified"
            )
            fig_t2.update_xaxes(rangeslider_visible=True)
            st.plotly_chart(fig_t2, use_container_width=True)