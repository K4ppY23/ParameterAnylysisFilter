import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(layout="wide")

# Inicjalizacja pamięci podręcznej stanu aplikacji (session_state)
if 'chart_metrics' not in st.session_state:
    st.session_state.chart_metrics = []
if 'selected_ids' not in st.session_state:
    st.session_state.selected_ids = {2, 5, 12}  # Przykładowo zaznaczone ID

# Przykładowe dane
@st.cache_data
def load_data():
    np.random.seed(42)
    return pd.DataFrame({
        'id': range(1, 101),
        'temperatura': np.random.normal(50, 15, 100),
        'cisnienie': np.random.normal(100, 25, 100),
        'predkosc': np.random.normal(60, 10, 100),
        'wilgotnosc': np.random.normal(45, 5, 100)
    })

df = load_data()

st.title("Zintegrowany Panel Algorytmów i Wykresów")

# --- 1. POŁĄCZONA ZAKŁADKA / PANEL ALGORYTMÓW ---
st.header("1. Konfiguracja Algorytmów i Filtrów")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Algorytm A")
    metric_a = st.selectbox("Wybierz metrykę (A):", ['temperatura', 'cisnienie', 'predkosc', 'wilgotnosc'], index=0)
    min_val_a = st.number_input("Min. wartość (A):", value=40.0)

with col2:
    st.subheader("Algorytm B")
    metric_b = st.selectbox("Wybierz metrykę (B):", ['temperatura', 'cisnienie', 'predkosc', 'wilgotnosc'], index=1)
    max_val_b = st.number_input("Max. wartość (B):", value=110.0)

# PRZYCISK URUCHOMIENIA FILTRA
if st.button("Uruchom filtry i wygeneruj wykres", type="primary"):
    # WYMAGANIE 2: Wyciągamy parametry użyte w filtrze i ustawiamy je domyślnie dla wykresu
    used_metrics = list(dict.fromkeys([metric_a, metric_b]))
    st.session_state.chart_metrics = used_metrics
    st.success(f"Filtr zastosowany! Wykres domyślnie ustawiono dla parametrów: {', '.join(used_metrics)}")

# --- 2. CHECKBOXY WIDOCZNOŚCI ---
st.header("2. Opcje Widoczności Danych")

c1, c2, c3 = st.columns(3)
show_all = c1.checkbox("Wszystkie", value=False)
show_selected = c2.checkbox("Zaznaczone", value=False)
show_condition = c3.checkbox("Spełniające warunek", value=True)

# Obliczenie warunku algorytmu
condition_mask = (df[metric_a] >= min_val_a) & (df[metric_b] <= max_val_b)
df['meets_condition'] = condition_mask
df['is_selected'] = df['id'].isin(st.session_state.selected_ids)

# Łączenie filtrowania w zależności od checkboxów (suma logiczna OR)
final_mask = pd.Series(False, index=df.index)
if show_all:
    final_mask = final_mask | True
if show_selected:
    final_mask = final_mask | df['is_selected']
if show_condition:
    final_mask = final_mask | df['meets_condition']

filtered_df = df[final_mask]

# --- 3. WYKRES DANYCH ---
st.header("3. Wykres Danych")

# Jeśli użytkownik jeszcze nie kliknął przycisku, ustawiamy domyślnie parametru z kontrolek
default_chart_params = st.session_state.chart_metrics if st.session_state.chart_metrics else [metric_a, metric_b]

selected_chart_params = st.multiselect(
    "Parametry widoczne na wykresie:",
    options=['temperatura', 'cisnienie', 'predkosc', 'wilgotnosc'],
    default=default_chart_params
)

if not filtered_df.empty and selected_chart_params:
    fig = px.line(
        filtered_df,
        x='id',
        y=selected_chart_params,
        title="Wykres przefiltrowanych parametrów",
        markers=True
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Brak danych do wyświetlenia (zmieniaj opcje widoczności lub serie wykresu).")