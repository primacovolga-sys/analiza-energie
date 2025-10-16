import os, io, zipfile
import gradio as gr
import pandas as pd
import plotly.express as px

def detect_time_col(df):
    c = [c for c in df.columns if c.lower() in ["datetime","date","timestamp","time","ora","data"]]
    if not c: c = [x for x in df.columns if any(k in x.lower() for k in ["date","time","ora","data"])]
    return c[0] if c else None

def load_any(file):
    name = file.name
    return pd.read_csv(name) if name.lower().endswith(".csv") else pd.read_excel(name)

def get_meta(file):
    if file is None: return "Încarcă CSV/XLSX.", gr.update(choices=[], value=[])
    df = load_any(file); t = detect_time_col(df)
    if t is None: return "Nu am coloană de timp.", gr.update(choices=[], value=[])
    df[t] = pd.to_datetime(df[t], errors="coerce"); df = df.dropna(subset=[t]).sort_values(t)
    nums = df.select_dtypes("number").columns.tolist()
    if not nums: return "Nu am coloane numerice.", gr.update(choices=[], value=[])
    info = f"Rânduri: {len(df)} | Coloane: {len(df.columns)} | Timp: {t} | Interval: {df[t].min()} → {df[t].max()}"
    return info, gr.update(choices=nums, value=nums[:5])

def make_plots(file, cols):
    if file is None: return "Încarcă fișierul.", None, None, None, None
    df = load_any(file); t = detect_time_col(df)
    if t is None: return "Nu am coloană de timp.", None, None, None, None
    df[t] = pd.to_datetime(df[t], errors="coerce"); df = df.dropna(subset=[t]).sort_values(t)
    if not cols: return "Selectează cel puțin o coloană numerică.", None, None, None, None
    fig_ts = px.line(df, x=t, y=cols, title="Serii temporale")
    fm = df.set_index(t).groupby(pd.Grouper(freq="M"))[cols].sum().reset_index()
    fig_m = px.bar(fm, x=t, y=cols, barmode="group", title="Agregare lunară (sumă)")
    csv_bytes = df[[t]+cols].to_csv(index=False).encode()
    csv_file = ("date.csv", csv_bytes)
    html_zip = io.BytesIO()
    with zipfile.ZipFile(html_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("serii_temporale.html", fig_ts.to_html(include_plotlyjs="cdn"))
        z.writestr("agregare_lunara.html",  fig_m.to_html(include_plotlyjs="cdn"))
    html_zip.seek(0)
    return "", fig_ts, fig_m, csv_file, ("grafice.zip", html_zip.read())

with gr.Blocks(title="Analiza Energiei - Gradio") as app:
    gr.Markdown("## Analiza Interactivă a Energiei ⚡\nÎncarcă CSV/XLSX și selectează coloanele numerice.")
    file = gr.File(label="CSV/XLSX")
    info = gr.Markdown(); cols = gr.CheckboxGroup(label="Coloane numerice")
    load_btn = gr.Button("1) Metadate"); run_btn = gr.Button("2) Grafice", variant="primary")
    out = gr.Markdown(); fig1 = gr.Plot(); fig2 = gr.Plot(); dl_csv = gr.File(); dl_zip = gr.File()
    load_btn.click(get_meta, inputs=file, outputs=[info, cols])
    run_btn.click(make_plots, inputs=[file, cols], outputs=[out, fig1, fig2, dl_csv, dl_zip])

if __name__ == "__main__":
    # Render setează PORT; expune pe 0.0.0.0
    app.queue().launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")), show_api=False, share=False)
