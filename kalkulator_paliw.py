import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# =========================
# 1. SCRAPER
# =========================
@st.cache_data
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
    "95":   {"netto": 0.45, "vat": 0.19, "akcyza": 0.25, "oplaty": 0.08, "marza": 0.03},
    "98":   {"netto": 0.45, "vat": 0.19, "akcyza": 0.25, "oplaty": 0.08, "marza": 0.03},
    "ON":   {"netto": 0.50, "vat": 0.19, "akcyza": 0.20, "oplaty": 0.08, "marza": 0.03},
    "ON+":  {"netto": 0.50, "vat": 0.19, "akcyza": 0.20, "oplaty": 0.08, "marza": 0.03},
    "LPG":  {"netto": 0.48, "vat": 0.19, "akcyza": 0.16, "oplaty": 0.12, "marza": 0.05}
}

# =========================
# 3. UI STREAMLIT
# =========================
st.set_page_config(page_title="Kalkulator Paliw", layout="centered")

st.title("⛽ Kalkulator kosztów paliwa")

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

# =========================
# 6. WYNIKI
# =========================
st.subheader(f"📍 {wojewodztwo}")

col1, col2, col3 = st.columns(3)

col1.metric("Cena/l", f"{cena_litr:.2f} zł")
col2.metric("Litry", f"{litry:.2f}")
col3.metric("Koszt", f"{koszt:.2f} zł")

st.markdown("---")

st.write("### 💰 Podział kosztów")

st.write(f"Czyste paliwo: {netto:.2f} zł")
st.write(f"VAT: {vat:.2f} zł")
st.write(f"Akcyza: {akcyza:.2f} zł")
st.write(f"Opłaty: {oplaty:.2f} zł")
st.write(f"Marża: {marza:.2f} zł")