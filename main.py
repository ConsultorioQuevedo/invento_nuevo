import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. CONFIGURACIÓN E INTERFAZ VISUAL DE NUEVA GENERACIÓN
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

# Aplicando el "Maquillaje" Premium (CSS)
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #2e7d32; color: white; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #1b5e20; transform: scale(1.02); }
    .stMetric { background-color: #1e2130; padding: 20px; border-radius: 15px; border: 1px solid #3d4466; }
    .card { background-color: #1e2130; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 10px; }
    h1, h2, h3 { color: #ffffff !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stTextInput>div>div>input { background-color: #262730; color: white; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# 2. MOTOR DE DATOS PERMANENTE
def iniciar_db():
    conn = sqlite3.connect("sistema_quevedo_premium.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, tipo TEXT, categoria TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY, nombre TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, hora TEXT)')
    conn.commit()
    return conn

conn = iniciar_db()

# 3. BASE DE DATOS DE CONTACTOS (Tus 7 contactos reales)
contactos = {
    "Mi Hijo": "18292061693", "Mi Hija": "18292581449", "Franklin (Hno)": "16463746377",
    "Hermanito Loco": "14077975432", "Dorka Carpio": "18298811692", "Rosa": "18293800425",
    "Pedro (Hno)": "18097100995"
}

# 4. INTELIGENCIA ARTIFICIAL (IA)
def motor_ia_predictivo(df):
    if len(df) > 3:
        X = np.arange(len(df)).reshape(-1, 1)
        y = df['monto'].cumsum().values
        modelo = LinearRegression().fit(X, y)
        return round(modelo.predict([[len(df) + 1]])[0], 2)
    return None

# --- NAVEGACIÓN ---
st.sidebar.title("💎 QUEVEDO OMNI")
st.sidebar.info(f"Usuario: Luis Rafael Quevedo")
menu = st.sidebar.radio("CENTRO DE CONTROL", ["💰 FINANZAS IA", "🩺 BIOMONITOR", "💊 AGENDA MÉDICA", "📸 ESCÁNER & PDF"])

# --- SECCIÓN 1: FINANZAS CON IA ---
if menu == "💰 FINANZAS IA":
    st.title("💰 Inteligencia Financiera")
    with st.container():
        with st.form("f_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            t = c1.selectbox("FLUJO", ["INGRESO", "GASTO", "PRESUPUESTO"])
            cat = c2.text_input("CONCEPTO").upper()
            mon = c3.number_input("RD$", min_value=0.0)
            if st.form_submit_button("REGISTRAR MOVIMIENTO"):
                v = mon if t != "GASTO" else -mon
                conn.execute("INSERT INTO finanzas (tipo, categoria, monto) VALUES (?,?,?)", (t, cat, v))
                conn.commit()

    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    if not df_f.empty:
        bal = df_f['monto'].sum()
        pred = motor_ia_predictivo(df_f)
        
        col1, col2 = st.columns(2)
        col1.metric("BALANCE NETO", f"RD$ {bal:,.2f}")
        if pred:
            col2.metric("PROYECCIÓN IA", f"RD$ {pred:,.2f}", delta=round(pred-bal, 2))
            if pred < 1500:
                st.warning("⚠️ ALERTA IA: Balance futuro crítico.")
                st.link_button("📲 Avisar a Mi Hijo", f"https://wa.me/{contactos['Mi Hijo']}?text=Alerta Financiera IA.")

        st.subheader("Historial Permanente")
        for i, r in df_f.iterrows():
            c_a, c_b = st.columns([6, 1])
            c_a.markdown(f'<div class="card"><b>{r["tipo"]}</b>: {r["categoria"]} | RD$ {abs(r["monto"]):,.2f}</div>', unsafe_allow_html=True)
            if c_b.button("🗑️", key=f"f_{r['id']}"):
                conn.execute(f"DELETE FROM finanzas WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 2: BIOMONITOR (SEMÁFORO) ---
elif menu == "🩺 BIOMONITOR":
    st.title("🩸 Monitor de Glucosa")
    val_g = st.number_input("Nivel (mg/dL):", min_value=0)
    if st.button("GUARDAR EN BIORREGISTRO"):
        tz = pytz.timezone('America/Santo_Domingo')
        ahora = datetime.now(tz)
        est = "🟢 NORMAL" if val_g < 140 else "🟡 ALERTA" if val_g <= 160 else "🔴 CRÍTICO"
        conn.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", 
                     (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), est))
        conn.commit()

    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    if not df_g.empty:
        st.plotly_chart(px.area(df_g, x="fecha", y="valor", title="Tendencia Bio-Salud", color_discrete_sequence=['#4CAF50']))
        
        if val_g > 160:
            st.error("🚨 EMERGENCIA: NIVEL ROJO")
            st.write("Avisar a contactos de emergencia:")
            cols = st.columns(len(contactos))
            for i, (n, num) in enumerate(contactos.items()):
                m_g = f"Urgente: Mi nivel de glucosa es {val_g}. Necesito asistencia."
                cols[i].link_button(f"📲 {n}", f"https://wa.me/{num}?text={m_g.replace(' ', '%20')}")

        for i, r in df_g.iterrows():
            color = "#28a745" if "NORMAL" in r['estado'] else "#ffc107" if "ALERTA" in r['estado'] else "#dc3545"
            st.markdown(f'<div style="border-left:10px solid {color}; padding:15px; background:#1e2130; border-radius:10px; margin-bottom:5px">'
                        f'<b>{r["fecha"]} {r["hora"]}</b> | <b>{r["valor"]} mg/dL</b> | {r["estado"]}</div>', unsafe_allow_html=True)
            if st.button(f"Borrar #{r['id']}", key=f"g_{r['id']}"):
                conn.execute(f"DELETE FROM glucosa WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 3: AGENDA MÉDICA ---
elif menu == "💊 AGENDA MÉDICA":
    st.title("📅 Gestión Médica")
    c_m, c_c = st.columns(2)
    with c_m:
        st.subheader("Medicamentos")
        with st.form("m_f"):
            nom = st.text_input("Medicina:"); hor = st.text_input("Hora/Frecuencia:")
            if st.form_submit_button("Añadir"):
                conn.execute("INSERT INTO medicinas (nombre, horario) VALUES (?,?)", (nom.upper(), hor)); conn.commit()
        for i, r in pd.read_sql_query("SELECT * FROM medicinas", conn).iterrows():
            st.info(f"💊 {r['nombre']} - {r['horario']}")
            if st.button("Eliminar", key=f"m_{r['id']}"):
                conn.execute(f"DELETE FROM medicinas WHERE id={r['id']}"); conn.commit(); st.rerun()

    with c_c:
        st.subheader("Próximas Citas")
        with st.form("c_f"):
            dr = st.text_input("Doctor:"); fe = st.date_input("Fecha"); hr = st.time_input("Hora")
            if st.form_submit_button("Agendar"):
                conn.execute("INSERT INTO citas (doctor, fecha, hora) VALUES (?,?,?)", (dr.upper(), str(fe), str(hr))); conn.commit()
        for i, r in pd.read_sql_query("SELECT * FROM citas", conn).iterrows():
            st.warning(f"📅 {r['doctor']} | {r['fecha']} a las {r['hora']}")
            if st.button("Eliminar", key=f"c_{r['id']}"):
                conn.execute(f"DELETE FROM citas WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 4: ESCÁNER & REPORTES ---
elif menu == "📸 ESCÁNER & PDF":
    st.title("📸 Centro de Documentos")
    col_a, col_b = st.columns(2)
    col_a.link_button("📧 Acceder a Gmail", "https://mail.google.com")
    col_b.link_button("💬 WhatsApp Web", "https://web.whatsapp.com")
    
    st.divider()
    img = st.camera_input("Escanear Factura o Receta Médica")
    if img:
        st.image(img, caption="Documento Analizado")
        st.download_button("📥 Guardar Escaneo", img, file_name="quevedo_doc.png")

    if st.button("📄 GENERAR REPORTE PDF COMPLETO"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "SISTEMA QUEVEDO: REPORTE DE GESTIÓN", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(200, 10, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
        pdf.cell(200, 10, f"Usuario: Luis Rafael Quevedo", ln=True)
        out = pdf.output(dest='S').encode('latin-1')
        st.download_button("⬇️ DESCARGAR PDF", out, "Reporte_Quevedo.pdf", "application/pdf")

# PIE DE PÁGINA
st.sidebar.markdown("---")
st.sidebar.write("💎 **SISTEMA QUEVEDO v7.0**")
st.sidebar.write("Diseño: Luis Rafael Quevedo")
