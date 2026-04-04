import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from datetime import datetime
import pytz
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. CONFIGURACIÓN E INTERFAZ DE ALTO NIVEL
st.set_page_config(page_title="SISTEMA QUEVEDO SUPREMO", layout="wide", page_icon="💎")

# --- SISTEMA DE SEGURIDAD (LOGIN) ---
def verificar_acceso():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        st.markdown("<h1 style='text-align: center; color: #4CAF50;'>💎 SISTEMA QUEVEDO</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("DESBLOQUEAR SISTEMA"):
                if u == "admin" and p == "Quevedo2026":
                    st.session_state["autenticado"] = True
                    st.rerun()
                else: st.error("❌ Credenciales incorrectas")
        return False
    return True

if verificar_acceso():
    if not os.path.exists("archivador_quevedo"): os.makedirs("archivador_quevedo")

    # DISEÑO VISUAL Y ANIMACIONES (CSS)
    st.markdown("""
        <style>
        .main { background-color: #0e1117; }
        .stButton>button { width: 100%; border-radius: 10px; background-color: #1b5e20; color: white; font-weight: bold; height: 3em; }
        .card-resumen { background-color: #1e2130; padding: 20px; border-radius: 15px; border-top: 4px solid #4CAF50; text-align: center; margin-bottom: 10px; }
        .card-datos { background-color: #1e2130; padding: 10px; border-radius: 8px; border-left: 5px solid #4CAF50; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; }
        .semaforo-rojo { background-color: #c62828; padding: 20px; border-radius: 15px; color: white; animation: pulse 2s infinite; text-align: center; font-weight: bold; margin-bottom: 20px; }
        @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 15px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
        </style>
        """, unsafe_allow_html=True)

    # 2. BASE DE DATOS INTEGRAL
    def iniciar_db():
        conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY AUTOINCREMENT, limite REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS archivador (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_archivo TEXT, descripcion TEXT, fecha TEXT)')
        conn.commit()
        return conn

    conn = iniciar_db()
    
    # CONTACTOS FAMILIARES COMPLETOS
    contactos = {
        "Mi Hijo": "18292061693", "Mi Hija": "18292581449", 
        "Franklin": "16463746377", "Hermanito": "14077975432", 
        "Dorka": "18298811692", "Rosa": "18293800425", "Pedro": "18097100995"
    }

    # --- NAVEGACIÓN ---
    st.sidebar.title("💎 SISTEMA QUEVEDO")
    menu = st.sidebar.radio("MENÚ", ["🏠 DASHBOARD", "💰 FINANZAS PRO", "🩺 BIOMONITOR", "💊 AGENDA", "📸 ARCHIVADOR"])
    if st.sidebar.button("🔒 CERRAR SESIÓN"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- 1. DASHBOARD (PANEL DE CONTROL) ---
    if menu == "🏠 DASHBOARD":
        st.header(f"👋 Panel de Control - Luis Rafael Quevedo")
        
        df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
        df_g = pd.read_sql_query("SELECT * FROM glucosa", conn)
        df_m = pd.read_sql_query("SELECT * FROM medicinas", conn)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            bal = df_f['monto'].sum() if not df_f.empty else 0
            st.markdown(f"<div class='card-resumen'><h3>💰 Balance Neto</h3><h2 style='color:#4CAF50'>RD$ {bal:,.2f}</h2></div>", unsafe_allow_html=True)
        with c2:
            prom_g = df_g['valor'].mean() if not df_g.empty else 0
            st.markdown(f"<div class='card-resumen'><h3>🩺 Glucosa Prom.</h3><h2 style='color:#2196F3'>{prom_g:.1f} mg/dL</h2></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='card-resumen'><h3>💊 Agenda</h3><h2 style='color:#FF9800'>{len(df_m)} Medicinas</h2></div>", unsafe_allow_html=True)

        if prom_g > 0:
            eA1c = (46.7 + prom_g) / 28.7
            st.info(f"📊 **Análisis de Salud:** Tu Hemoglobina Glicosilada estimada ($eA1c$) es de **{eA1c:.1f}%**.")

    # --- 2. FINANZAS PRO (CON IA Y PRESUPUESTO) ---
    elif menu == "💰 FINANZAS PRO":
        st.header("💰 Inteligencia Financiera")
        
        # Gestión de Presupuesto
        res_pre = pd.read_sql_query("SELECT limite FROM presupuesto ORDER BY id DESC LIMIT 1", conn)
        limite = res_pre['limite'].iloc[0] if not res_pre.empty else 0.0
        
        with st.expander("📊 CONFIGURAR PRESUPUESTO"):
            n_limite = st.number_input("Establecer Límite Mensual RD$", value=float(limite))
            if st.button("Guardar Límite"):
                conn.execute("INSERT INTO presupuesto (limite) VALUES (?)", (n_limite,))
                conn.commit(); st.rerun()

        with st.form("fin", clear_on_submit=True):
            col_a, col_b, col_c = st.columns(3)
            t = col_a.selectbox("TIPO", ["INGRESO", "GASTO"])
            cat = col_b.text_input("CONCEPTO").upper()
            mon = col_c.number_input("RD$", min_value=0.0)
            if st.form_submit_button("REGISTRAR"):
                conn.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)", (t, cat, (mon if t=="INGRESO" else -mon), datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); st.rerun()

        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
        if not df_f.empty:
            gastos_t = abs(df_f[df_f['monto'] < 0]['monto'].sum())
            if limite > 0:
                st.write(f"Consumo de Presupuesto: **RD$ {gastos_t:,.2f} / RD$ {limite:,.2f}**")
                st.progress(min(gastos_t / limite, 1.0))

            # IA de Proyección
            if len(df_f) > 2:
                X = np.arange(len(df_f)).reshape(-1, 1); y = df_f['monto'].cumsum().values
                proy = LinearRegression().fit(X, y).predict([[len(df_f) + 1]])[0]
                st.metric("PREDICCIÓN DE SALDO PRÓXIMO MES (IA)", f"RD$ {proy:,.2f}")

            # Buscador
            busc = st.text_input("🔍 BUSCAR MOVIMIENTO:").upper()
            for i, r in df_f.iterrows():
                if busc in r['categoria']:
                    col = "#4CAF50" if r['monto'] > 0 else "#FF5252"
                    st.markdown(f'<div class="card-datos"><span>{r["fecha"]} | {r["categoria"]}</span> <span style="color:{col}">RD$ {abs(r["monto"]):,.2f}</span></div>', unsafe_allow_html=True)

    # --- 3. BIOMONITOR (CON SEMÁFORO Y WHATSAPP) ---
    elif menu == "🩺 BIOMONITOR":
        st.header("🩺 Control de Glucosa")
        val_g = st.number_input("Nivel mg/dL:", min_value=0)
        
        if val_g > 160:
            st.markdown(f'<div class="semaforo-rojo">🚨 ALERTA: NIVEL CRÍTICO {val_g} mg/dL</div>', unsafe_allow_html=True)
            st.warning("Notificar a familiares:")
            cols_w = st.columns(4)
            for i, (n, num) in enumerate(contactos.items()):
                msg = f"Alerta Salud Luis: Glucosa en {val_g}"
                cols_w[i % 4].link_button(f"📲 {n}", f"https://api.whatsapp.com/send?phone={num}&text={msg}")

        if st.button("💾 GUARDAR TOMA"):
            tz = pytz.timezone('America/Santo_Domingo'); ahora = datetime.now(tz)
            est = "NORMAL" if val_g <= 140 else "ALERTA" if val_g <= 160 else "CRÍTICO"
            conn.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), est))
            conn.commit(); st.rerun()

        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id ASC", conn)
        if not df_g.empty:
            st.plotly_chart(px.line(df_g, x="fecha", y="valor", markers=True, title="Historial de Glucosa"), use_container_width=True)

    # --- 4. AGENDA MÉDICA ---
    elif menu == "💊 AGENDA":
        st.header("📅 Medicinas y Citas")
        st.link_button("📧 ABRIR GMAIL", "https://mail.google.com")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("💊 Medicinas")
            with st.form("m"):
                nm = st.text_input("Medicina:"); hr = st.text_input("Hora:")
                if st.form_submit_button("Añadir"):
                    conn.execute("INSERT INTO medicinas (nombre, horario) VALUES (?,?)", (nm.upper(), hr)); conn.commit(); st.rerun()
            for i, r in pd.read_sql_query("SELECT * FROM medicinas", conn).iterrows(): st.info(f"{r['nombre']} - {r['horario']}")
        with c2:
            st.subheader("📅 Citas")
            with st.form("c"):
                dr = st.text_input("Doctor:"); fc = st.date_input("Fecha")
                if st.form_submit_button("Agendar"):
                    conn.execute("INSERT INTO citas (doctor, fecha) VALUES (?,?)", (dr.upper(), str(fc))); conn.commit(); st.rerun()

    # --- 5. ARCHIVADOR CON BUSCADOR ---
    elif menu == "📸 ARCHIVADOR":
        st.header("📸 Gestión de Documentos")
        t1, t2 = st.tabs(["Escanear/Subir", "Consultar"])
        with t1:
            foto = st.camera_input("Capturar")
            desc = st.text_input("Descripción del documento:")
            if foto and st.button("💾 GUARDAR DOCUMENTO"):
                n_arch = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                with open(os.path.join("archivador_quevedo", n_arch), "wb") as f: f.write(foto.getbuffer())
                conn.execute("INSERT INTO archivador (nombre_archivo, descripcion, fecha) VALUES (?,?,?)", (n_arch, desc.upper(), datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); st.success("Guardado.")
        with t2:
            df_a = pd.read_sql_query("SELECT * FROM archivador ORDER BY id DESC", conn)
            bus_a = st.text_input("🔍 Buscar en Archivador:").upper()
            for i, r in df_a.iterrows():
                if bus_a in r['descripcion']:
                    with st.expander(f"📄 {r['descripcion']} ({r['fecha']})"):
                        with open(os.path.join("archivador_quevedo", r['nombre_archivo']), "rb") as f:
                            st.download_button(f"Descargar {r['nombre_archivo']}", f, file_name=r['nombre_archivo'])

    # CRÉDITOS
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"<div style='text-align:center; color:#888'><b>Sistema Quevedo v10.0</b><br>Luis Rafael Quevedo</div>", unsafe_allow_html=True)
