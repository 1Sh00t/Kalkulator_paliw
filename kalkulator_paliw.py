import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.express as px

# =========================
# 1. SCRAPER (Aktualizacja raz na dobę za pomocą ttl=86400 sekund)
# =========================
@st.cache_data(ttl=86400)  # Dane są zamrożone w pamięci podręcznej przez 24 godziny
def get_fuel_data():
    url = "https://www.autocentrum.pl/paliwa/ceny-paliw/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")

    rows = []
    for tr in table.find_all("tr"):
        cols = tr.find_all(["td", "th"])
        cols = [c.get_text(strip=True) for c in cols]
        if cols:
            rows.append(cols)

    df = pd.DataFrame(rows)

    # ustaw nagłówki
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)

    # popraw nazwy kolumn
    df = df.rename(columns={df.columns[0]: "Województwo"})

    # usuń Polskę (opcjonalnie)
    df = df[df["Województwo"] != "Polska"]

    # kolumny paliw
    fuel_cols = ["95", "98", "ON", "ON+", "LPG"]

    for col in fuel_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace(" ", "", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


df_prices = get_fuel_data()

# =========================
# 2. STRUKTURA PODATKÓW
# =========================
TAX_STRUCTURE = {
    "95":   {"netto": 0.45, "vat": 0.08, "akcyza": 0.24, "oplaty": 0.08, "marza": 0.03},
    "98":   {"netto": 0.45, "vat": 0.08, "akcyza": 0.24, "oplaty": 0.08, "marza": 0.03},
    "ON":   {"netto": 0.50, "vat": 0.08, "akcyza": 0.20, "oplaty": 0.08, "marza": 0.03},
    "ON+":  {"netto": 0.50, "vat": 0.08, "akcyza": 0.20, "oplaty": 0.08, "marza": 0.03},
    "LPG":  {"netto": 0.48, "vat": 0.08, "akcyza": 0.16, "oplaty": 0.12, "marza": 0.05}
}

# =========================
# 3. UI STREAMLIT
# =========================
st.set_page_config(page_title="Kalkulator Paliw", layout="centered")

# ==============================================================================
# UKRYTY KOD WERYFIKACYJNY MYLEAD (Niewidoczny dla użytkownika, widoczny dla bota)
# ==============================================================================
st.markdown("<!-- mylead-verification: ecb3fa566077b260ab26f75ff7efd738 -->", unsafe_allow_html=True)

st.title("⛽ Kalkulator kosztów paliwa i ukrytych podatków")
st.caption("ℹ️ Ceny paliw są automatycznie odświeżane raz na dobę.")

# sidebar
st.sidebar.header("Parametry")

wojewodztwo = st.sidebar.selectbox(
    "Wybierz województwo",
    df_prices["Województwo"].dropna().unique()
)

rodzaj_paliwa = st.sidebar.selectbox(
    "Rodzaj paliwa",
    ["95", "98", "ON", "ON+", "LPG"]
)

dystans = st.sidebar.number_input("Dystans (km)", 1.0, value=100.0)
spalanie = st.sidebar.number_input("Spalanie (l/100km)", 1.0, value=7.5)

# =========================
# 4. DANE
# =========================
cena_litr = df_prices.loc[
    df_prices["Województwo"] == wojewodztwo,
    rodzaj_paliwa
].values

if len(cena_litr) == 0 or pd.isna(cena_litr[0]):
    st.error("Brak danych dla tego województwa/paliwa")
    st.stop()

cena_litr = cena_litr[0]

# =========================
# 5. OBLICZENIA
# =========================
litry = (dystans / 100) * spalanie
koszt = litry * cena_litr

tax = TAX_STRUCTURE[rodzaj_paliwa]

netto = koszt * tax["netto"]
vat = koszt * tax["vat"]
akcyza = koszt * tax["akcyza"]
oplaty = koszt * tax["oplaty"]
marza = koszt * tax["marza"]

# Podział binarny na czysty koszt vs państwo
suma_podatkow = vat + akcyza + oplaty + marza

# =========================
# 6. WYNIKI
# =========================
st.subheader(f"📊 Wyniki kalkulacji dla województwa: **{wojewodztwo}**")

col1, col2, col3 = st.columns(3)
col1.metric("Cena paliwa", f"{cena_litr:.2f} zł/l")
col2.metric("Potrzebne paliwo", f"{litry:.2f} l")
col3.metric("Łączny koszt (Brutto)", f"{koszt:.2f} zł")

st.markdown("---")

# Prezentacja głównych bloków kosztów
col_paliwo, col_podatki = st.columns(2)
with col_paliwo:
    st.info(f"**Cena czystego paliwa:**  \n### {netto:.2f} zł")
with col_podatki:
    st.warning(f"**Podatki i marże (Ukryte koszty):**  \n### {suma_podatkow:.2f} zł")

# Wizualizacja za pomocą wykresu kołowego (Plotly)
st.write("### 📈 Wizualizacja struktury ceny")

# Przygotowanie danych do wykresu
chart_data = pd.DataFrame({
    "Składnik": ["Czyste paliwo (Netto)", "Podatek VAT", "Akcyza", "Opłaty paliwowe", "Marża stacji"],
    "Kwota (zł)": [netto, vat, akcyza, oplaty, marza]
})

# Generowanie wykresu
fig = px.pie(
    chart_data, 
    values="Kwota (zł)", 
    names="Składnik",
    hole=0.4,  # Wykres typu "Donut" dla lepszej czytelności
    color_discrete_sequence=px.colors.sequential.YlOrRd[::-1]  # Ładne odcienie czerwieni i żółci
)

fig.update_traces(textposition='inside', textinfo='percent+label')
fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))

# Wyświetlenie wykresu w Streamlit
st.plotly_chart(fig, use_container_width=True)

# Szczegółowa tabela pod wykresem
st.write("### 🔍 Szczegółowe zestawienie kosztów:")
st.write(f"• **Czyste paliwo:** {netto:.2f} zł ({tax['netto']*100:.0f}%)")
st.write(f"• **Podatek VAT:** {vat:.2f} zł ({tax['vat']*100:.0f}%)")
st.write(f"• **Akcyza:** {akcyza:.2f} zł ({tax['akcyza']*100:.0f}%)")
st.write(f"• **Opłaty drogowe i środowiskowe:** {oplaty:.2f} zł ({tax['oplaty']*100:.0f}%)")
st.write(f"• **Szacowana marża stacji:** {marza:.2f} zł ({tax['marza']*100:.0f}%)")

# =========================
# 7. SEKCJA AFILIACYJNA (ZAROBKOWA)
# =========================
st.markdown("---")
st.subheader("💡 Jak płacić mniej za podróż?")

# Tworzymy układ dwóch kolumn na oferty
col_aff1, col_aff2 = st.columns(2)

with col_aff1:
    st.markdown(
        """
        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; height: 100%;">
            <h4>🚗 Tanie ubezpieczenie OC/AC</h4>
            <p>Koszty paliwa rosną, ale na ubezpieczeniu możesz zaoszczędzić nawet do 500 zł. Sprawdź darmowy kalkulator i znajdź najtańszą ofertę.</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    # Twój link afiliacyjny jako estetyczny przycisk
    st.link_button("🔥 Porównaj ceny OC/AC", "https://twoj-link-afiliacyjny-z-rankomat.pl")

with col_aff2:
    st.markdown(
        """
        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #1428a0; height: 100%;">
            <h4>💳 Darmowe paliwo od PKO BP</h4>
            <p>Załóż kultowe Konto za Zero w aktualnej promocji i zgarnij gwarantowaną premię gotówkową na start. Wykorzystaj darmowe środki, aby sfinansować kolejny pełny bak paliwa!</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    # Wklej tutaj swój unikalny link partnerski wygenerowany w MyLead dla kampanii PKO BP
    st.link_button("🎁 Odbierz premię od PKO BP", "https://twoj-link-afiliacyjny-do-pko.pl")

