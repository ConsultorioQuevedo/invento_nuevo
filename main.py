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

# 1. CONFIGURACIÓN E INTERFAZ DE ALTO NIVEL
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

# --- SISTEMA DE SEGURIDAD (LOGIN) ---
def verificar_acceso():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.markdown("<h1 style='text-align: center; color: #4CAF50;'>💎 SISTEMA QUEVEDO</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>🔐 Acceso Privado - Luis Rafael Quevedo</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("DESBLOQUEAR SISTEMA"):
                if u == "admin" and p == "Quevedo2026":
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
        return False
    return True

if verificar_acceso():
    # Directorio de archivos
    if not os.path.exists("archivador_quevedo"):
        os.makedirs("archivador_quevedo")

    # DISEÑO VISUAL (CSS)
    st.markdown("""
        <style>
        .main { background-color: #0e1117; }
        .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; height: 3.5em; font-weight: bold; border: none; }
        .card-datos { background-color: #1e2130; padding: 12px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
        .semaforo-rojo { background-color: #c62828; padding: 15px; border-radius: 10px; color: white; animation: pulse 2s infinite; text-align: center; font-weight: bold; }
        @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 10px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
        </style>
        """, unsafe_allow_html=True)

    # 2. BASE DE DATOS LOCAL (sqlite)
    def iniciar_db():
        conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY AUTOINCREMENT, limite REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT)')
        conn.commit()
        return conn

    conn = iniciar_db()

    # 3. LISTA COMPLETA DE CONTACTOS (SIN EXCEPCIONES)
    contactos = {
        "Mi Hijo": "18292061693", 
        "Mi Hija": "18292581449", 
        "Franklin (Hno)": "16463746377",
        "Hermanito Loco": "14077975432", 
        "Dorka Carpio": "18298811692", 
        "Rosa": "18293800425",
        "Pedro (Hno)": "18097100995"
    }

    # --- NAVEGACIÓN ---
    st.sidebar.title("💎 SISTEMA QUEVEDO")
    if st.sidebar.button("🔒 CERRAR SESIÓN"):
        st.session_state["autenticado"] = False
        st.rerun()

    menu = st.sidebar.radio("MÓDULOS", ["💰 FINANZAS IA", "🩺 BIOMONITOR", "💊 AGENDA MÉDICA", "📸 ESCÁNER", "📂 ARCHIVADOR"])

    # --- SECCIÓN 1: FINANZAS + IA + PRESUPUESTO ---
    if menu == "💰 FINANZAS IA":
        st.header("💰 Finanzas e Inteligencia Artificial")
        
        # Presupuesto Mensual
        res_pre = pd.read_sql_query("SELECT limite FROM presupuesto ORDER BY id DESC LIMIT 1", conn)
        limite = res_pre['limite'].iloc[0] if not res_pre.empty else 0.0
        with st.expander("⚙️ Configurar Presupuesto Mensual"):
            n_limite = st.number_input("RD$ Límite Máximo", value=float(limite))
            if st.button("Guardar Configuración"):
                conn.execute("INSERT INTO presupuesto (limite) VALUES (?)", (n_limite,))
                conn.commit(); st.rerun()

        with st.form("finanzas_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            tipo = c1.selectbox("TIPO", ["INGRESO", "GASTO"])
            cat = c2.text_input("CONCEPTO").upper()
            mon = c3.number_input("RD$", min_value=0.0)
            if st.form_submit_button("REGISTRAR"):
                val = mon if tipo == "INGRESO" else -mon
                conn.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)", (tipo, cat, val, datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); st.rerun()

        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
        if not df_f.empty:
            bal = df_f['monto'].sum()
            gastos_t = abs(df_f[df_f['monto'] < 0]['monto'].sum())
            
            # Métrica de Proyección IA
            proy = None
            if len(df_f) > 2:
                X = np.arange(len(df_f)).reshape(-1, 1); y = df_f['monto'].cumsum().values
                proy = round(LinearRegression().fit(X, y).predict([[len(df_f) + 1]])[0], 2)

            m1, m2, m3 = st.columns(3)
            m1.metric("BALANCE NETO", f"RD$ {bal:,.2f}")
            m2.metric("GASTOS TOTALES", f"RD$ {gastos_t:,.2f}")
            if proy: m3.metric("SALDO ESTIMADO (IA)", f"RD$ {proy:,.2f}")

            if limite > 0:
                prog = min(gastos_t / limite, 1.0)
                st.write(f"Barra de Presupuesto: {prog*100:.1f}%")
                st.progress(prog)

            if st.button("🗑️ ELIMINAR ÚLTIMO REGISTRO"):
                conn.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); conn.commit(); st.rerun()

            for i, r in df_f.iterrows():
                color = "#4CAF50" if r['monto'] > 0 else "#FF5252"
                st.markdown(f'<div class="card-datos"><span>{r["fecha"]} | {r["categoria"]}</span> <span style="color:{color}">RD$ {abs(r["monto"]):,.2f}</span></div>', unsafe_allow_html=True)

    # --- SECCIÓN 2: BIOMONITOR + WHATSAPP ---
    elif menu == "🩺 BIOMONITOR":
        st.header("🩺 Salud de Luis Rafael Quevedo")
        val_g = st.number_input("Glucosa mg/dL:", min_value=0)
        
        if val_g > 160:
            st.markdown(f'<div class="semaforo-rojo">🚨 ALERTA CRÍTICA: {val_g} mg/dL</div>', unsafe_allow_html=True)
            st.info("📲 Notificar de inmediato a:")
            cols_w = st.columns(4)
            for i, (nombre, num) in enumerate(contactos.items()):
                msg = f"Ayuda! llamar a Dr: Quevedo: Dario tiene la glucosa en {val_g} mg/dL"
                link = f"https://api.whatsapp.com/send?phone={num}&text={msg.replace(' ', '%20')}"
                cols_w[i % 4].link_button(f"👤 {nombre}", link)

        if st.button("💾 GUARDAR TOMA DE GLUCOSA"):
            tz = pytz.timezone('America/Santo_Domingo'); ahora = datetime.now(tz)
            est = "NORMAL" if val_g <= 140 else "ALERTA" if val_g <= 160 else "CRÍTICO"
            conn.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), est))
            conn.commit(); st.rerun()

        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id ASC", conn)
        if not df_g.empty:
            fig = px.line(df_g, x="fecha", y="valor", title="📈 Historial de Glucosa", markers=True)
            fig.update_traces(line_color='#4CAF50')
            st.plotly_chart(fig, use_container_width=True)
            
            if st.button("🗑️ ELIMINAR ÚLTIMA TOMA"):
                conn.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); conn.commit(); st.rerun()

            for i, r in df_g.sort_index(ascending=False).iterrows():
                color = "#4CAF50" if r['estado'] == "NORMAL" else "#FBC02D" if r['estado'] == "ALERTA" else "#FF5252"
                st.markdown(f'<div class="card-datos"><span>{r["fecha"]} - {r["hora"]}</span> <span style="color:{color}">{r["valor"]} mg/dL ({r["estado"]})</span></div>', unsafe_allow_html=True)

    # --- SECCIÓN 3: AGENDA MÉDICA ---
    elif menu == "💊 AGENDA MÉDICA":
        st.header("📅 Agenda y Comunicaciones")
        st.link_button("📧 REVISAR MI GMAIL", "https://mail.google.com")
        
        ca, cb = st.columns(2)
        with ca:
            st.subheader("💊 Medicinas")
            with st.form("med_form"):
                nm = st.text_input("Medicina:"); hr = st.text_input("Horario:")
                if st.form_submit_button("Añadir"):
                    conn.execute("INSERT INTO medicinas (nombre, horario) VALUES (?,?)", (nm.upper(), hr)); conn.commit(); st.rerun()
            if st.button("🗑️ Borrar Última Medicina"):
                conn.execute("DELETE FROM medicinas WHERE id = (SELECT MAX(id) FROM medicinas)"); conn.commit(); st.rerun()
            for i, r in pd.read_sql_query("SELECT * FROM medicinas", conn).iterrows():
                st.info(f"📍 {r['nombre']} - {r['horario']}")
        with cb:
            st.subheader("📅 Citas")
            with st.form("cita_form"):
                dr = st.text_input("Doctor:"); f_c = st.date_input("Fecha")
                if st.form_submit_button("Agendar"):
                    conn.execute("INSERT INTO citas (doctor, fecha) VALUES (?,?)", (dr.upper(), str(f_c))); conn.commit(); st.rerun()
            if st.button("🗑️ Borrar Última Cita"):
                conn.execute("DELETE FROM citas WHERE id = (SELECT MAX(id) FROM citas)"); conn.commit(); st.rerun()
            for i, r in pd.read_sql_query("SELECT * FROM citas", conn).iterrows():
                st.warning(f"🏥 {r['doctor']} - {r['fecha']}")

    # --- SECCIÓN 4: ESCÁNER ---
    elif menu == "📸 ESCÁNER":
        st.header("📸 Escáner de Documentos")
        foto = st.camera_input("Capturar Receta o Factura")
        if foto:
            nombre = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            with open(os.path.join("archivador_quevedo", nombre), "wb") as f: f.write(foto.getbuffer())
            st.success(f"✅ Guardado en Archivador como: {nombre}")

    # --- SECCIÓN 5: ARCHIVADOR ---
    elif menu == "📂 ARCHIVADOR":
        st.header("📂 Archivador Seguro")
        archivos = os.listdir("archivador_quevedo")
        if not archivos:
            st.info("El archivador está vacío.")
        for archi in archivos:
            with open(os.path.join("archivador_quevedo", archi), "rb") as f:
                st.download_button(f"💾 Descargar: {archi}", f, file_name=archi)

    # --- CRÉDITOS ---
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
