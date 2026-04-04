import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from datetime import datetime
import pytz
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. CONFIGURACIÓN DE PANTALLA Y ESTILOS
st.set_page_config(page_title="SISTEMA QUEVEDO INTEGRAL", layout="wide", page_icon="💎")

# --- CAPA DE SEGURIDAD ---
def verificar_acceso():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        st.markdown("<h1 style='text-align: center; color: #4CAF50;'>💎 SISTEMA QUEVEDO</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("DESBLOQUEAR"):
                if u == "admin" and p == "Quevedo2026":
                    st.session_state["autenticado"] = True
                    st.rerun()
                else: st.error("❌ Credenciales incorrectas")
        return False
    return True

if verificar_acceso():
    # Crear carpeta de archivador si no existe
    if not os.path.exists("archivador_quevedo"): os.makedirs("archivador_quevedo")

    # DISEÑO CSS (UI/UX)
    st.markdown("""
        <style>
        .main { background-color: #0e1117; }
        .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; font-weight: bold; height: 3.5em; border: none; }
        .card-resumen { background-color: #1e2130; padding: 20px; border-radius: 15px; border-top: 5px solid #4CAF50; text-align: center; }
        .card-datos { background-color: #1e2130; padding: 12px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
        .semaforo-rojo { background-color: #c62828; padding: 20px; border-radius: 15px; color: white; animation: pulse 2s infinite; text-align: center; font-weight: bold; }
        @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 15px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
        </style>
        """, unsafe_allow_html=True)

    # 2. MOTOR DE BASE DE DATOS (SQLITE)
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
    
    # 3. LISTA DE CONTACTOS DE EMERGENCIA
    contactos = {
        "Mi Hijo": "18292061693", "Mi Hija": "18292581449", 
        "Franklin": "16463746377", "Hermanito": "14077975432", 
        "Dorka": "18298811692", "Rosa": "18293800425", "Pedro": "18097100995"
    }

    # --- NAVEGACIÓN LATERAL ---
    st.sidebar.title("💎 SISTEMA QUEVEDO")
    menu = st.sidebar.radio("MENÚ PRINCIPAL", ["🏠 DASHBOARD", "💰 FINANZAS", "🩺 BIOMONITOR", "💊 AGENDA", "📸 ARCHIVADOR"])
    if st.sidebar.button("🔒 CERRAR SESIÓN"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- MÓDULO 1: DASHBOARD ---
    if menu == "🏠 DASHBOARD":
        st.header("🏠 Panel de Control - Luis Rafael Quevedo")
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
            st.markdown(f"<div class='card-resumen'><h3>💊 Agenda Médica</h3><h2 style='color:#FF9800'>{len(df_m)} Medicinas</h2></div>", unsafe_allow_html=True)

        if prom_g > 0:
            eA1c = (46.7 + prom_g) / 28.7
            st.info(f"📊 **Analítica:** Hemoglobina Glicosilada estimada: **{eA1c:.1f}%**")

    # --- MÓDULO 2: FINANZAS PRO ---
    elif menu == "💰 FINANZAS":
        st.header("💰 Gestión de Finanzas e IA")
        res_pre = pd.read_sql_query("SELECT limite FROM presupuesto ORDER BY id DESC LIMIT 1", conn)
        limite = res_pre['limite'].iloc[0] if not res_pre.empty else 0.0
        
        with st.expander("⚙️ CONFIGURAR LÍMITE DE GASTOS"):
            n_limite = st.number_input("RD$ Límite Mensual", value=float(limite))
            if st.button("Guardar"):
                conn.execute("INSERT INTO presupuesto (limite) VALUES (?)", (n_limite,))
                conn.commit(); st.rerun()

        with st.form("finanzas_form", clear_on_submit=True):
            col_a, col_b, col_c = st.columns(3)
            tipo_f = col_a.selectbox("TIPO", ["INGRESO", "GASTO"])
            cat_f = col_b.text_input("CONCEPTO (Ej: Supermercado)").upper()
            mon_f = col_c.number_input("MONTO RD$", min_value=0.0)
            if st.form_submit_button("REGISTRAR"):
                val = mon_f if tipo_f == "INGRESO" else -mon_f
                conn.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)", (tipo_f, cat_f, val, datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); st.rerun()

        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
        if not df_f.empty:
            gastos_t = abs(df_f[df_f['monto'] < 0]['monto'].sum())
            if limite > 0:
                st.write(f"**Presupuesto:** RD$ {gastos_t:,.2f} / {limite:,.2f}")
                st.progress(min(gastos_t / limite, 1.0))

            if len(df_f) > 2:
                X = np.arange(len(df_f)).reshape(-1, 1); y = df_f['monto'].cumsum().values
                proy = LinearRegression().fit(X, y).predict([[len(df_f) + 1]])[0]
                st.metric("PREDICCIÓN DE SALDO (IA)", f"RD$ {proy:,.2f}")

            busc = st.text_input("🔍 BUSCAR REGISTRO:").upper()
            if st.button("🗑️ ELIMINAR ÚLTIMO MOVIMIENTO"):
                conn.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); conn.commit(); st.rerun()
            
            for i, r in df_f.iterrows():
                if busc in r['categoria']:
                    color = "#4CAF50" if r['monto'] > 0 else "#FF5252"
                    st.markdown(f'<div class="card-datos"><span>{r["fecha"]} | {r["categoria"]}</span> <span style="color:{color}">RD$ {abs(r["monto"]):,.2f}</span></div>', unsafe_allow_html=True)

    # --- MÓDULO 3: BIOMONITOR ---
    elif menu == "🩺 BIOMONITOR":
        st.header("🩺 Monitor de Salud Luis")
        val_g = st.number_input("Nivel de Glucosa mg/dL:", min_value=0)
        
        if val_g > 160:
            st.markdown(f'<div class="semaforo-rojo">🚨 ALERTA CRÍTICA: {val_g} mg/dL</div>', unsafe_allow_html=True)
            st.write("Enviar alerta inmediata a:")
            cols_w = st.columns(4)
            for i, (nombre, numero) in enumerate(contactos.items()):
                msg = f"Emergencia Salud Luis: Glucosa en {val_g}"
                cols_w[i % 4].link_button(f"👤 {nombre}", f"https://api.whatsapp.com/send?phone={numero}&text={msg}")

        if st.button("💾 GUARDAR TOMA"):
            tz = pytz.timezone('America/Santo_Domingo'); ahora = datetime.now(tz)
            est = "NORMAL" if val_g <= 140 else "ALERTA" if val_g <= 160 else "CRÍTICO"
            conn.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), est))
            conn.commit(); st.rerun()

        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id ASC", conn)
        if not df_g.empty:
            st.plotly_chart(px.line(df_g, x="fecha", y="valor", markers=True, title="Tendencia Histórica"), use_container_width=True)
            if st.button("🗑️ BORRAR ÚLTIMA TOMA"):
                conn.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); conn.commit(); st.rerun()

    # --- MÓDULO 4: AGENDA ---
    elif menu == "💊 AGENDA":
        st.header("📅 Agenda de Salud")
        st.link_button("📧 IR A MI GMAIL", "https://mail.google.com")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("💊 Medicinas")
            with st.form("med_form", clear_on_submit=True):
                nm = st.text_input("Nombre Medicina:"); hr = st.text_input("Horario:")
                if st.form_submit_button("Añadir"):
                    conn.execute("INSERT INTO medicinas (nombre, horario) VALUES (?,?)", (nm.upper(), hr)); conn.commit(); st.rerun()
            if st.button("🗑️ Borrar Medicina"):
                conn.execute("DELETE FROM medicinas WHERE id = (SELECT MAX(id) FROM medicinas)"); conn.commit(); st.rerun()
            for i, r in pd.read_sql_query("SELECT * FROM medicinas", conn).iterrows(): st.info(f"{r['nombre']} - {r['horario']}")
        with c2:
            st.subheader("📅 Próximas Citas")
            with st.form("cita_form", clear_on_submit=True):
                dr = st.text_input("Doctor:"); fca = st.date_input("Fecha")
                if st.form_submit_button("Agendar"):
                    conn.execute("INSERT INTO citas (doctor, fecha) VALUES (?,?)", (dr.upper(), str(fca))); conn.commit(); st.rerun()
            if st.button("🗑️ Borrar Cita"):
                conn.execute("DELETE FROM citas WHERE id = (SELECT MAX(id) FROM citas)"); conn.commit(); st.rerun()

    # --- MÓDULO 5: ARCHIVADOR ---
    elif menu == "📸 ARCHIVADOR":
        st.header("📂 Archivador Inteligente")
        t1, t2 = st.tabs(["📸 Escanear Nuevo", "📂 Consultar Archivos"])
        with t1:
            foto = st.camera_input("Capturar Documento")
            desc_f = st.text_input("Descripción del archivo (Ej: Receta Médica):").upper()
            if foto and st.button("💾 GUARDAR EN ARCHIVADOR"):
                n_arch = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                with open(os.path.join("archivador_quevedo", n_arch), "wb") as f: f.write(foto.getbuffer())
                conn.execute("INSERT INTO archivador (nombre_archivo, descripcion, fecha) VALUES (?,?,?)", (n_arch, desc_f, datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); st.success("¡Documento archivado con éxito!")
        with t2:
            df_a = pd.read_sql_query("SELECT * FROM archivador ORDER BY id DESC", conn)
            bus_a = st.text_input("🔍 BUSCAR POR DESCRIPCIÓN:").upper()
            if st.button("🗑️ ELIMINAR ÚLTIMO ARCHIVO"):
                conn.execute("DELETE FROM archivador WHERE id = (SELECT MAX(id) FROM archivador)"); conn.commit(); st.rerun()
            for i, r in df_a.iterrows():
                if bus_a in r['descripcion']:
                    with st.expander(f"📄 {r['descripcion']} - {r['fecha']}"):
                        with open(os.path.join("archivador_quevedo", r['nombre_archivo']), "rb") as f:
                            st.download_button(f"📥 Descargar {r['nombre_archivo']}", f, file_name=r['nombre_archivo'])

    # --- CRÉDITOS ---
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"<div style='text-align:center; color:#555'><b>Sistema Quevedo v11.0</b><br>Desarrollado por Luis Rafael Quevedo</div>", unsafe_allow_html=True)
