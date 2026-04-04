import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

if not os.path.exists("archivador_quevedo"):
    os.makedirs("archivador_quevedo")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; height: 3.5em; font-weight: bold; border: none; transition: 0.3s; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 15px; border: 1px solid #3d4466; }
    .semaforo-verde { background-color: #1b5e20; padding: 15px; border-radius: 10px; color: white; font-weight: bold; border: 2px solid #4CAF50; margin-bottom: 10px; text-align: center; }
    .semaforo-amarillo { background-color: #fbc02d; padding: 15px; border-radius: 10px; color: black; font-weight: bold; border: 2px solid #fdd835; margin-bottom: 10px; text-align: center; }
    .semaforo-rojo { background-color: #c62828; padding: 15px; border-radius: 10px; color: white; font-weight: bold; border: 2px solid #ff5252; margin-bottom: 10px; text-align: center; animation: pulse 2s infinite; }
    @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 15px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
    .card-datos { background-color: #1e2130; padding: 12px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
    h1, h2, h3 { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. BASE DE DATOS CON AUTO-REPARACIÓN (Evita el KeyError)
def iniciar_db():
    conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY, limite REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT)')
    
    # PARCHE DE SEGURIDAD: Si la columna 'fecha' no existe en finanzas, la crea
    try:
        c.execute("SELECT fecha FROM finanzas LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE finanzas ADD COLUMN fecha TEXT DEFAULT 'Sin Fecha'")
        
    conn.commit()
    return conn

conn = iniciar_db()

# 3. CONTACTOS
contactos = {
    "Mi Hijo": "18292061693", "Mi Hija": "18292581449", "Franklin (Hno)": "16463746377",
    "Hermanito Loco": "14077975432", "Dorka Carpio": "18298811692", "Rosa": "18293800425",
    "Pedro (Hno)": "18097100995"
}

# 4. MOTOR IA
def motor_ia(df):
    if len(df) > 2:
        X = np.arange(len(df)).reshape(-1, 1)
        y = df['monto'].cumsum().values
        return round(LinearRegression().fit(X, y).predict([[len(df) + 1]])[0], 2)
    return None

# --- NAVEGACIÓN ---
st.sidebar.title("💎 SISTEMA QUEVEDO")
menu = st.sidebar.radio("MENÚ", ["💰 FINANZAS IA", "🩺 BIOMONITOR", "💊 AGENDA MÉDICA", "📸 ESCÁNER", "📂 ARCHIVADOR"])

# --- SECCIÓN 1: FINANZAS ---
if menu == "💰 FINANZAS IA":
    st.header("💰 Inteligencia Financiera")
    
    # Presupuesto
    res_pre = pd.read_sql_query("SELECT limite FROM presupuesto ORDER BY id DESC LIMIT 1", conn)
    limite_actual = res_pre['limite'].iloc[0] if not res_pre.empty else 0.0
    with st.expander("⚙️ Configurar Presupuesto"):
        n_limite = st.number_input("RD$", value=float(limite_actual))
        if st.button("Guardar"):
            conn.execute("INSERT INTO presupuesto (limite) VALUES (?)", (n_limite,))
            conn.commit(); st.rerun()

    with st.form("f", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        t = c1.selectbox("TIPO", ["INGRESO", "GASTO"])
        cat = c2.text_input("CONCEPTO").upper()
        mon = c3.number_input("RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            v = mon if t == "INGRESO" else -mon
            fecha_hoy = datetime.now().strftime("%d/%m/%Y")
            conn.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)", (t, cat, v, fecha_hoy))
            conn.commit(); st.rerun()

    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
    if not df_f.empty:
        bal = df_f['monto'].sum()
        gastos = abs(df_f[df_f['monto'] < 0]['monto'].sum())
        pred = motor_ia(df_f)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("BALANCE NETO", f"RD$ {bal:,.2f}")
        m2.metric("GASTOS", f"RD$ {gastos:,.2f}")
        if pred: m3.metric("PROYECCIÓN IA", f"RD$ {pred:,.2f}", delta=round(pred-bal, 2))
        
        st.subheader("📋 Historial (Borrado Activo)")
        for i, r in df_f.iterrows():
            c_txt, c_btn = st.columns([0.85, 0.15])
            with c_txt:
                color = "#4CAF50" if r['monto'] > 0 else "#FF5252"
                st.markdown(f'<div class="card-datos"><span>{r["fecha"]} | {r["categoria"]}</span> <span style="color:{color}">RD$ {abs(r["monto"]):,.2f}</span></div>', unsafe_allow_html=True)
            with c_btn:
                if st.button("🗑️", key=f"f_{r['id']}"):
                    conn.execute(f"DELETE FROM finanzas WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 2: SALUD ---
elif menu == "🩺 BIOMONITOR":
    st.header("🩺 Control de Salud")
    val_g = st.number_input("Glucosa mg/dL:", min_value=0)
    
    if val_g > 0:
        if val_g <= 140: st.markdown('<div class="semaforo-verde">🟢 NORMAL</div>', unsafe_allow_html=True)
        elif val_g <= 160: st.markdown('<div class="semaforo-amarillo">🟡 ALERTA</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="semaforo-rojo">🔴 CRÍTICO</div>', unsafe_allow_html=True)
            cols = st.columns(4)
            for i, (n, num) in enumerate(contactos.items()):
                link = f"https://api.whatsapp.com/send?phone={num}&text=Urgente%3A%20Luis%20Rafael%20Quevedo%20Glucosa%20en%20{val_g}"
                cols[i % 4].link_button(f"📲 {n}", link)

    if st.button("GUARDAR"):
        ahora = datetime.now(pytz.timezone('America/Santo_Domingo'))
        est = "NORMAL" if val_g <= 140 else "ALERTA" if val_g <= 160 else "CRÍTICO"
        conn.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), est))
        conn.commit(); st.rerun()

    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    for i, r in df_g.iterrows():
        c_t, c_b = st.columns([0.85, 0.15])
        with c_t:
            color = "#4CAF50" if r['estado'] == "NORMAL" else "#FBC02D" if r['estado'] == "ALERTA" else "#FF5252"
            st.markdown(f'<div class="card-datos"><span>{r["fecha"]} - {r["hora"]}</span> <span style="color:{color}">{r["valor"]} mg/dL ({r["estado"]})</span></div>', unsafe_allow_html=True)
        with c_b:
            if st.button("🗑️", key=f"g_{r['id']}"):
                conn.execute(f"DELETE FROM glucosa WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 3: AGENDA + GMAIL ---
elif menu == "💊 AGENDA MÉDICA":
    st.header("📅 Salud y Gmail")
    st.link_button("📧 ABRIR GMAIL", "https://mail.google.com")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💊 Medicinas")
        with st.form("m"):
            nom = st.text_input("Medicina:"); hor = st.text_input("Hora:")
            if st.form_submit_button("Añadir"):
                conn.execute("INSERT INTO medicinas (nombre, horario) VALUES (?,?)", (nom.upper(), hor)); conn.commit(); st.rerun()
        for i, r in pd.read_sql_query("SELECT * FROM medicinas", conn).iterrows():
            st.info(f"{r['nombre']} - {r['horario']}")
            if st.button("Borrar", key=f"m_{r['id']}"):
                conn.execute(f"DELETE FROM medicinas WHERE id={r['id']}"); conn.commit(); st.rerun()
    with col2:
        st.subheader("📅 Citas")
        with st.form("c"):
            dr = st.text_input("Doctor:"); fe = st.date_input("Fecha")
            if st.form_submit_button("Agendar"):
                conn.execute("INSERT INTO citas (doctor, fecha) VALUES (?,?)", (dr.upper(), str(fe))); conn.commit(); st.rerun()
        for i, r in pd.read_sql_query("SELECT * FROM citas", conn).iterrows():
            st.warning(f"{r['doctor']} - {r['fecha']}")
            if st.button("Borrar", key=f"c_{r['id']}"):
                conn.execute(f"DELETE FROM citas WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 4: ESCÁNER ---
elif menu == "📸 ESCÁNER":
    st.header("📸 Escáner")
    foto = st.camera_input("Capturar")
    if foto:
        n = f"foto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        with open(os.path.join("archivador_quevedo", n), "wb") as f:
            f.write(foto.getbuffer())
        st.success(f"Archivado: {n}")
        st.image(foto)
    if st.button("📄 GENERAR REPORTE PDF"):
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "REPORTE SISTEMA QUEVEDO", ln=True, align='C')
        n_p = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf.output(os.path.join("archivador_quevedo", n_p))
        st.success(f"PDF Guardado: {n_p}")

# --- SECCIÓN 5: ARCHIVADOR ---
elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador")
    for a in os.listdir("archivador_quevedo"):
        r_c = os.path.join("archivador_quevedo", a)
        with open(r_c, "rb") as f:
            st.download_button(f"💾 {a}", f, file_name=a)

# --- CRÉDITOS ---
st.sidebar.markdown("---")
st.sidebar.subheader("🚀 CRÉDITOS")
st.sidebar.write("💎 **SISTEMA QUEVEDO v8.0**")
st.sidebar.info("👨‍💻 **Desarrollador Principal:** \n\n **Luis Rafael Quevedo**")
