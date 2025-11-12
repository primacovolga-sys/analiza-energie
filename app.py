import streamlit as st
import pandas as pd
import io
from datetime import datetime
import plotly.express as px
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

st.set_page_config(page_title="Analiza Energiei", layout="wide")
st.title("Analiza Interactivă a Energiei – Streamlit")

st.markdown("""
1) Încărcați CSV/XLSX (sistemul energetic RO).  
2) Alegeți intervalul de date și tipurile de energie.  
3) Vizualizați graficele și descărcați raportul PDF sumar.
""")

uploaded = st.file_uploader("Încarcă fișier CSV/XLSX", type=["csv", "xlsx"])

def detect_time_col(df: pd.DataFrame):
    c = [c for c in df.columns if c.lower() in ["datetime","date","timestamp","time","ora","data"]]
    if not c:
        c = [x for x in df.columns if any(k in x.lower() for k in ["date","time","ora","data"])]
    return c[0] if c else None

def gen_pdf_bytes(period_text: str, cols_text: str, rows_count: int):
    # PDF simplu (sumar textual) – compatibil pe Streamlit Cloud
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    c.setFont("Helvetica-Bold", 14); c.drawString(2*cm, H-2*cm, "Raport Analiza Energiei")
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, H-3*cm, f"Generat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(2*cm, H-4*cm, f"Perioadă: {period_text}")
    c.drawString(2*cm, H-5*cm, f"Tipuri selectate: {cols_text}")
    c.drawString(2*cm, H-6*cm, f"Observații: {rows_count} rânduri filtrate")
    c.showPage(); c.save()
    buf.seek(0)
    return buf.read()

if uploaded:
    df = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
    t = detect_time_col(df)
    if not t:
        st.error("Nu am găsit o coloană de timp (datetime/date/time/ora/data).")
        st.stop()

    df[t] = pd.to_datetime(df[t], errors="coerce")
    df = df.dropna(subset=[t]).sort_values(t)

    # derivate + coloane numerice
    df["year"] = df[t].dt.year
    df["month"] = df[t].dt.month
    num_cols = df.select_dtypes("number").columns.tolist()

    # coloane energie candidate
    energy_cols = [c for c in num_cols if any(k in c.lower() for k in
        ["solar","fotovolta","pv","eolian","wind","hidro","hydro","nuclear","coal","carbune","gas","gaz"])]

    # filtre
    st.sidebar.header("Filtre")
    dmin, dmax = df[t].min().date(), df[t].max().date()
    date_range = st.sidebar.date_input("Interval de date", (dmin, dmax))
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = [pd.to_datetime(x) for x in date_range]
        df = df[(df[t] >= start) & (df[t] <= end)]
    else:
        start, end = df[t].min(), df[t].max()

    chosen = st.sidebar.multiselect("Tipuri de energie", options=energy_cols, default=energy_cols[:5])

    # grafice
    if chosen:
        st.subheader("Serii temporale (selectate)")
        st.plotly_chart(px.line(df, x=t, y=chosen), use_container_width=True)

        st.subheader("Agregare lunară (sumă)")
        fm = df.set_index(t).groupby(pd.Grouper(freq="M"))[chosen].sum().reset_index()
        st.plotly_chart(px.bar(fm, x=t, y=chosen, barmode="group"), use_container_width=True)
    else:
        st.info("Alegeți cel puțin o coloană numerică de energie în sidebar.")

    # export
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Descarcă PDF sumar"):
            period_text = f"{start.date()} – {end.date()}"
            cols_text = ", ".join(chosen) if chosen else "(nimic selectat)"
            pdf_bytes = gen_pdf_bytes(period_text, cols_text, len(df))
            st.download_button("Descarcă raport.pdf", data=pdf_bytes,
                               file_name="raport.pdf", mime="application/pdf")
    with col2:
        cols_for_csv = [t] + (chosen if chosen else num_cols[:5])
        csv_bytes = df[cols_for_csv].to_csv(index=False).encode()
        st.download_button("Descarcă date filtrate (CSV)", data=csv_bytes,
                           file_name="date_filtrate.csv", mime="text/csv")
else:
    st.info("Încărcați un fișier pentru a începe.")
