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

# 1. CONFIGURACIÓN E INTERFAZ "NUEVA GENERACIÓN"
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

# Crear carpeta para el Archivador si no existe
if not os.path.exists("archivador_quevedo"):
    os.makedirs("archivador_quevedo")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; height: 3.5em; font-weight: bold; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #2e7d32; transform: scale(1.02); }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 15px; border: 1px solid #3d4466; }
    /* Semáforo de Salud */
    .semaforo-verde { background-color: #1b5e20; padding: 20px; border-radius: 15px; text-align: center; color: white; font-weight: bold; border: 2px solid #4CAF50; }
    .semaforo-amarillo { background-color: #fbc02d; padding: 20px; border-radius: 15px; text-align: center; color: black; font-weight: bold; border: 2px solid #fdd835; }
    .semaforo-rojo { background-color: #c62828; padding: 20px; border-radius: 15px; text-align: center; color: white; font-weight: bold; border: 2px solid #ff5252; animation: pulse 2s infinite; }
    @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 15px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
    .card-item { background-color: #262730; padding: 10px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 8px; }
    h1, h2, h3 { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. BASE DE DATOS MAESTRA (PERMANENTE)
def iniciar_db():
    conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, tipo TEXT, categoria TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY, limite REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY, nombre TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, hora TEXT)')
    conn.commit()
    return conn

conn = iniciar_db()

# 3. CONTACTOS PARA APP WHATSAPP
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
st.sidebar.write("Usuario: Luis Rafael Quevedo")
menu = st.sidebar.radio("MENÚ", ["💰 FINANZAS IA", "🩺 BIOMONITOR", "💊 AGENDA MÉDICA", "📸 ESCÁNER", "📂 ARCHIVADOR"])

# --- SECCIÓN 1: FINANZAS + PRESUPUESTO + IA ---
if menu == "💰 FINANZAS IA":
    st.header("💰 Inteligencia Financiera y Presupuesto")
    
    # Gestión de Presupuesto
    res_pre = pd.read_sql_query("SELECT limite FROM presupuesto ORDER BY id DESC LIMIT 1", conn)
    limite_actual = res_pre['limite'].iloc[0] if not res_pre.empty else 0.0
    
    with st.expander("⚙️ Configurar Presupuesto Mensual"):
        nuevo_limite = st.number_input("Establecer Límite RD$", value=float(limite_actual))
        if st.button("Guardar Presupuesto"):
            conn.execute("INSERT INTO presupuesto (limite) VALUES (?)", (nuevo_limite,))
            conn.commit(); st.rerun()

    # Registro de Movimientos
    with st.form("form_f", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        t = c1.selectbox("TIPO", ["INGRESO", "GASTO"])
        cat = c2.text_input("CONCEPTO").upper()
        mon = c3.number_input("RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            v = mon if t == "INGRESO" else -mon
            conn.execute("INSERT INTO finanzas (tipo, categoria, monto) VALUES (?,?,?)", (t, cat, v))
            conn.commit(); st.rerun()

    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    if not df_f.empty:
        bal = df_f['monto'].sum()
        gastos_totales = abs(df_f[df_f['monto'] < 0]['monto'].sum())
        pred = motor_ia(df_f)
        
        col_ia1, col_ia2, col_ia3 = st.columns(3)
        col_ia1.metric("BALANCE NETO", f"RD$ {bal:,.2f}")
        col_ia2.metric("GASTOS TOTALES", f"RD$ {gastos_totales:,.2f}")
        if pred: col_ia3.metric("PROYECCIÓN IA", f"RD$ {pred:,.2f}", delta=round(pred-bal, 2))
        
        # Alerta de Presupuesto
        if limite_actual > 0:
            progreso = gastos_totales / limite_actual
            st.write(f"📊 Consumo de Presupuesto: {progreso*100:.1f}%")
            st.progress(min(progreso, 1.0))
            if gastos_totales > limite_actual:
                st.warning(f"⚠️ ¡HAS SUPERADO TU PRESUPUESTO POR RD$ {gastos_totales - limite_actual:,.2f}!")

# --- SECCIÓN 2: BIOMONITOR + SEMÁFORO + WHATSAPP APP ---
elif menu == "🩺 BIOMONITOR":
    st.header("🩺 Monitor de Salud")
    val_g = st.number_input("Nivel mg/dL:", min_value=0)
    
    if val_g > 0:
        if val_g <= 140:
            st.markdown(f'<div class="semaforo-verde">🟢 NORMAL: {val_g} mg/dL</div>', unsafe_allow_html=True)
        elif val_g <= 160:
            st.markdown(f'<div class="semaforo-amarillo">🟡 ALERTA: {val_g} mg/dL</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="semaforo-rojo">🔴 CRÍTICO: {val_g} mg/dL</div>', unsafe_allow_html=True)
            st.error("🚨 ENVIAR ALERTA INMEDIATA A FAMILIARES")
            cols = st.columns(4)
            for i, (n, num) in enumerate(contactos.items()):
                msg = f"URGENTE: Soy Luis. Mi glucosa está en {val_g}. Necesito asistencia."
                link = f"https://api.whatsapp.com/send?phone={num}&text={msg.replace(' ', '%20')}"
                cols[i % 4].link_button(f"📲 {n}", link)

    if st.button("💾 GUARDAR REGISTRO"):
        tz = pytz.timezone('America/Santo_Domingo')
        ahora = datetime.now(tz)
        est = "NORMAL" if val_g <= 140 else "ALERTA" if val_g <= 160 else "CRÍTICO"
        conn.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), est))
        conn.commit(); st.rerun()
    
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    if not df_g.empty:
        st.plotly_chart(px.line(df_g, x="fecha", y="valor", title="Tendencia de Glucosa"))

# --- SECCIÓN 3: AGENDA MÉDICA + GMAIL ---
elif menu == "💊 AGENDA MÉDICA":
    st.header("📅 Gestión Médica y Correo")
    st.link_button("📧 ABRIR MI GMAIL", "https://mail.google.com")
    st.divider()
    
    col_med, col_cit = st.columns(2)
    with col_med:
        st.subheader("💊 Medicamentos")
        with st.form("med", clear_on_submit=True):
            n_m = st.text_input("Medicina:"); h_m = st.text_input("Horario:")
            if st.form_submit_button("Añadir"):
                conn.execute("INSERT INTO medicinas (nombre, horario) VALUES (?,?)", (n_m.upper(), h_m)); conn.commit(); st.rerun()
        for i, r in pd.read_sql_query("SELECT * FROM medicinas", conn).iterrows():
            st.info(f"💊 {r['nombre']} - {r['horario']}")
            if st.button("Borrar", key=f"m_{r['id']}"):
                conn.execute(f"DELETE FROM medicinas WHERE id={r['id']}"); conn.commit(); st.rerun()

    with col_cit:
        st.subheader("📅 Próximas Citas")
        with st.form("cit", clear_on_submit=True):
            dr = st.text_input("Doctor:"); fe = st.date_input("Fecha"); hr = st.time_input("Hora")
            if st.form_submit_button("Agendar"):
                conn.execute("INSERT INTO citas (doctor, fecha, hora) VALUES (?,?,?)", (dr.upper(), str(fe), str(hr))); conn.commit(); st.rerun()
        for i, r in pd.read_sql_query("SELECT * FROM citas", conn).iterrows():
            st.warning(f"📅 {r['doctor']} | {r['fecha']} - {r['hora']}")
            if st.button("Borrar", key=f"c_{r['id']}"):
                conn.execute(f"DELETE FROM citas WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 4: ESCÁNER ---
elif menu == "📸 ESCÁNER":
    st.header("📸 Escáner Inteligente")
    foto = st.camera_input("Capturar Documento")
    if foto:
        nombre_f = f"foto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        ruta_f = os.path.join("archivador_quevedo", nombre_f)
        with open(ruta_f, "wb") as f:
            f.write(foto.getbuffer())
        st.success(f"✅ Archivado en: {nombre_f}")
        st.image(foto)

    if st.button("📄 GENERAR REPORTE PDF"):
        pdf = FPDF()
        pdf.add_page(); pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "REPORTE SISTEMA QUEVEDO", ln=True, align='C')
        nombre_p = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf.output(os.path.join("archivador_quevedo", nombre_p))
        st.success(f"✅ Reporte guardado en Archivador: {nombre_p}")

# --- SECCIÓN 5: ARCHIVADOR ---
elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador Permanente")
    archivos = os.listdir("archivador_quevedo")
    if not archivos:
        st.info("El archivador está vacío.")
    else:
        for a in archivos:
            r_c = os.path.join("archivador_quevedo", a)
            with open(r_c, "rb") as f:
                st.download_button(label=f"💾 Descargar: {a}", data=f, file_name=a)
            st.markdown(f'<div class="card-item">Archivo guardado: {a}</div>', unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.write("💎 **Luis Rafael Quevedo**")
