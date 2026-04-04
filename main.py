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

# 1. CONFIGURACIÓN E INTERFAZ PROFESIONAL
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

if not os.path.exists("archivador_quevedo"):
    os.makedirs("archivador_quevedo")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; height: 3.5em; font-weight: bold; border: none; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 15px; border: 1px solid #3d4466; }
    .semaforo-verde { background-color: #1b5e20; padding: 15px; border-radius: 10px; color: white; font-weight: bold; border: 2px solid #4CAF50; margin-bottom: 10px; text-align: center; }
    .semaforo-amarillo { background-color: #fbc02d; padding: 15px; border-radius: 10px; color: black; font-weight: bold; border: 2px solid #fdd835; margin-bottom: 10px; text-align: center; }
    .semaforo-rojo { background-color: #c62828; padding: 15px; border-radius: 10px; color: white; font-weight: bold; border: 2px solid #ff5252; margin-bottom: 10px; text-align: center; animation: pulse 2s infinite; }
    @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 10px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
    .card-datos { background-color: #1e2130; padding: 12px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
    h1, h2, h3 { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. BASE DE DATOS (CON PARCHE DE SEGURIDAD)
def iniciar_db():
    conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY AUTOINCREMENT, limite REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT)')
    try:
        c.execute("SELECT fecha FROM finanzas LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE finanzas ADD COLUMN fecha TEXT DEFAULT '04/04/2026'")
    conn.commit()
    return conn

conn = iniciar_db()

# 3. MOTOR DE INTELIGENCIA ARTIFICIAL (PREDICCIÓN)
def motor_ia(df):
    if len(df) > 2:
        try:
            X = np.arange(len(df)).reshape(-1, 1)
            y = df['monto'].cumsum().values
            modelo = LinearRegression().fit(X, y)
            prediccion = modelo.predict([[len(df) + 1]])
            return round(prediccion[0], 2)
        except: return None
    return None

# 4. CONTACTOS WHATSAPP APP
contactos = {
    "Mi Hijo": "18292061693", "Mi Hija": "18292581449", "Franklin (Hno)": "16463746377",
    "Hermanito Loco": "14077975432", "Dorka Carpio": "18298811692", "Rosa": "18293800425",
    "Pedro (Hno)": "18097100995"
}

# --- NAVEGACIÓN ---
st.sidebar.title("💎 SISTEMA QUEVEDO")
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["💰 FINANZAS IA", "🩺 BIOMONITOR", "💊 AGENDA MÉDICA", "📸 ESCÁNER", "📂 ARCHIVADOR"])

# --- SECCIÓN 1: FINANZAS + IA + PRESUPUESTO ---
if menu == "💰 FINANZAS IA":
    st.header("💰 Inteligencia Financiera y Presupuesto")
    
    # Gestión de Presupuesto
    res_pre = pd.read_sql_query("SELECT limite FROM presupuesto ORDER BY id DESC LIMIT 1", conn)
    limite_actual = res_pre['limite'].iloc[0] if not res_pre.empty else 0.0
    
    with st.expander("⚙️ Configurar Límite Mensual"):
        nuevo_limite = st.number_input("RD$ Límite de Gasto", value=float(limite_actual))
        if st.button("Guardar Presupuesto"):
            conn.execute("INSERT INTO presupuesto (limite) VALUES (?)", (nuevo_limite,))
            conn.commit(); st.rerun()

    with st.form("form_finanzas", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        tipo = c1.selectbox("TIPO", ["INGRESO", "GASTO"])
        cat = c2.text_input("CONCEPTO (Ej: Supermercado)").upper()
        monto = c3.number_input("MONTO RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR MOVIMIENTO"):
            valor = monto if tipo == "INGRESO" else -monto
            fecha_act = datetime.now().strftime("%d/%m/%Y")
            conn.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)", (tipo, cat, valor, fecha_act))
            conn.commit(); st.rerun()

    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
    if not df_f.empty:
        balance = df_f['monto'].sum()
        gastos_totales = abs(df_f[df_f['monto'] < 0]['monto'].sum())
        proyeccion = motor_ia(df_f)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("BALANCE NETO", f"RD$ {balance:,.2f}")
        m2.metric("GASTOS TOTALES", f"RD$ {gastos_totales:,.2f}")
        if proyeccion: m3.metric("PRÓXIMO SALDO (IA)", f"RD$ {proyeccion:,.2f}", delta=round(proyeccion-balance, 2))
        
        if limite_actual > 0:
            porcentaje = min(gastos_totales / limite_actual, 1.0)
            st.write(f"📊 Uso del Presupuesto: {porcentaje*100:.1f}%")
            st.progress(porcentaje)
            if gastos_totales > limite_actual:
                st.warning(f"⚠️ Has excedido el presupuesto por RD$ {gastos_totales - limite_actual:,.2f}")

        if st.button("🗑️ ELIMINAR ÚLTIMO MOVIMIENTO"):
            conn.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)")
            conn.commit(); st.rerun()
            
        st.subheader("📋 Historial de Movimientos")
        for i, r in df_f.iterrows():
            color_f = "#4CAF50" if r['monto'] > 0 else "#FF5252"
            st.markdown(f'<div class="card-datos"><span>{r["fecha"]} | {r["categoria"]}</span> <span style="color:{color_f}">RD$ {abs(r["monto"]):,.2f}</span></div>', unsafe_allow_html=True)

# --- SECCIÓN 2: BIOMONITOR + GRÁFICOS + WHATSAPP ---
elif menu == "🩺 BIOMONITOR":
    st.header("🩺 Control de Salud y Glucosa")
    val_g = st.number_input("Nivel de Glucosa mg/dL:", min_value=0)
    
    if val_g > 0:
        if val_g <= 140: st.markdown(f'<div class="semaforo-verde">🟢 NORMAL: {val_g} mg/dL</div>', unsafe_allow_html=True)
        elif val_g <= 160: st.markdown(f'<div class="semaforo-amarillo">🟡 ALERTA: {val_g} mg/dL</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="semaforo-rojo">🔴 CRÍTICO: {val_g} mg/dL</div>', unsafe_allow_html=True)
            st.error("🚨 ENVIAR ALERTA INMEDIATA")
            cols_w = st.columns(4)
            for i, (n, num) in enumerate(contactos.items()):
                msg = f"URGENTE: Soy Luis. Mi glucosa está en {val_g}."
                link = f"https://api.whatsapp.com/send?phone={num}&text={msg.replace(' ', '%20')}"
                cols_w[i % 4].link_button(f"📲 {n}", link)

    if st.button("💾 GUARDAR REGISTRO DE SALUD"):
        tz = pytz.timezone('America/Santo_Domingo')
        ahora = datetime.now(tz)
        estado_g = "NORMAL" if val_g <= 140 else "ALERTA" if val_g <= 160 else "CRÍTICO"
        conn.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), estado_g))
        conn.commit(); st.rerun()

    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id ASC", conn)
    if not df_g.empty:
        fig_g = px.line(df_g, x="fecha", y="valor", title="📈 Evolución de Glucosa", markers=True, line_shape="spline")
        fig_g.update_traces(line_color='#4CAF50')
        st.plotly_chart(fig_g, use_container_width=True)
        
        if st.button("🗑️ ELIMINAR ÚLTIMA TOMA"):
            conn.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)")
            conn.commit(); st.rerun()

        for i, r in df_g.sort_index(ascending=False).iterrows():
            color_g = "#4CAF50" if r['estado'] == "NORMAL" else "#FBC02D" if r['estado'] == "ALERTA" else "#FF5252"
            st.markdown(f'<div class="card-datos"><span>{r["fecha"]} - {r["hora"]}</span> <span style="color:{color_g}">{r["valor"]} mg/dL ({r["estado"]})</span></div>', unsafe_allow_html=True)

# --- SECCIÓN 3: AGENDA MÉDICA + GMAIL ---
elif menu == "💊 AGENDA MÉDICA":
    st.header("📅 Agenda de Luis Rafael Quevedo")
    st.link_button("📧 ABRIR MI GMAIL", "https://mail.google.com")
    st.divider()
    
    col_m, col_c = st.columns(2)
    with col_m:
        st.subheader("💊 Medicinas")
        with st.form("med", clear_on_submit=True):
            n_med = st.text_input("Medicina:"); h_med = st.text_input("Horario:")
            if st.form_submit_button("Añadir"):
                conn.execute("INSERT INTO medicinas (nombre, horario) VALUES (?,?)", (n_med.upper(), h_med))
                conn.commit(); st.rerun()
        if st.button("🗑️ Borrar Última Medicina"):
            conn.execute("DELETE FROM medicinas WHERE id = (SELECT MAX(id) FROM medicinas)"); conn.commit(); st.rerun()
        for i, r in pd.read_sql_query("SELECT * FROM medicinas", conn).iterrows():
            st.info(f"💊 {r['nombre']} - {r['horario']}")

    with col_c:
        st.subheader("📅 Citas")
        with st.form("cit", clear_on_submit=True):
            doctor = st.text_input("Doctor:"); fecha_c = st.date_input("Fecha")
            if st.form_submit_button("Agendar"):
                conn.execute("INSERT INTO citas (doctor, fecha) VALUES (?,?)", (doctor.upper(), str(fecha_c)))
                conn.commit(); st.rerun()
        if st.button("🗑️ Borrar Última Cita"):
            conn.execute("DELETE FROM citas WHERE id = (SELECT MAX(id) FROM citas)"); conn.commit(); st.rerun()
        for i, r in pd.read_sql_query("SELECT * FROM citas", conn).iterrows():
            st.warning(f"📅 {r['doctor']} | {r['fecha']}")

# --- SECCIÓN 4: ESCÁNER ---
elif menu == "📸 ESCÁNER":
    st.header("📸 Escáner de Documentos")
    foto_doc = st.camera_input("Capturar Factura o Receta")
    if foto_doc:
        nombre_foto = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        ruta_foto = os.path.join("archivador_quevedo", nombre_foto)
        with open(ruta_foto, "wb") as f:
            f.write(foto_doc.getbuffer())
        st.success(f"✅ Guardado en Archivador: {nombre_foto}")
        st.image(foto_doc)

    if st.button("📄 GENERAR REPORTE PDF"):
        pdf_gen = FPDF()
        pdf_gen.add_page(); pdf_gen.set_font("Arial", 'B', 16)
        pdf_gen.cell(200, 10, "REPORTE SISTEMA QUEVEDO", ln=True, align='C')
        nombre_pdf = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_gen.output(os.path.join("archivador_quevedo", nombre_pdf))
        st.success(f"✅ Reporte PDF guardado: {nombre_pdf}")

# --- SECCIÓN 5: ARCHIVADOR ---
elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador Permanente")
    lista_archivos = os.listdir("archivador_quevedo")
    if not lista_archivos:
        st.info("No hay documentos guardados aún.")
    else:
        for archi in lista_archivos:
            ruta_archi = os.path.join("archivador_quevedo", archi)
            with open(ruta_archi, "rb") as f_desc:
                st.download_button(f"💾 Descargar: {archi}", f_desc, file_name=archi)

# --- CRÉDITOS FINALES ---
st.sidebar.markdown("---")
st.sidebar.subheader("🚀 CRÉDITOS")
st.sidebar.markdown(f"""
    <div style="background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #4CAF50;">
        <p style="margin: 0; color: #4CAF50; font-weight: bold;">👨‍💻 Desarrollador Principal:</p>
        <p style="margin: 0; font-size: 1.1em;">Luis Rafael Quevedo</p>
        <hr style="margin: 10px 0; border: 0.5px solid #3d4466;">
        <p style="margin: 0; color: #888;">🤖 Asistencia Técnica:</p>
        <p style="margin: 0; font-style: italic;">Gemini AI</p>
    </div>
""", unsafe_allow_html=True)
