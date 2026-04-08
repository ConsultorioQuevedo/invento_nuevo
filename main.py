import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz
from PIL import Image
from pyzbar.pyzbar import decode

# ==========================================
# 1. CONFIGURACIÓN E IDENTIDAD (SIN LOGIN)
# ==========================================
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
ZONA_HORARIA = pytz.timezone('America/Santo_Domingo')

# Estilos de Ingeniería
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; font-weight: bold; height: 3.5em; border: 1px solid #4CAF50; }
    .resumen-card { background: linear-gradient(135deg, #1e2130 0%, #1b5e20 100%); padding: 20px; border-radius: 15px; border: 1px solid #4CAF50; text-align: center; }
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE BASE DE DATOS (ESTRUCTURA CORREGIDA)
# ==========================================
def inicializar_db():
    # Usamos V4 para asegurar que las columnas nuevas (concepto) se creen hoy
    conn = sqlite3.connect("sistema_quevedo_v4.db", check_same_thread=False)
    c = conn.cursor()
    
    # Tabla Finanzas (CORREGIDA: Ahora incluye 'concepto')
    c.execute("""CREATE TABLE IF NOT EXISTS finanzas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  tipo TEXT, 
                  categoria TEXT, 
                  concepto TEXT, 
                  monto REAL, 
                  fecha TEXT)""")
    
    # Tabla Presupuesto
    c.execute("CREATE TABLE IF NOT EXISTS presupuesto (monto_limite REAL)")
    
    # Tabla Salud (Glucosa)
    c.execute("CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT)")
    
    # Tabla Archivador Digital (Para el Escáner)
    c.execute("CREATE TABLE IF NOT EXISTS archivador (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, categoria TEXT, contenido TEXT, fecha TEXT)")
    
    conn.commit()
    return conn, c

conn, c = inicializar_db()

# ==========================================
# 3. MENÚ LATERAL
# ==========================================
st.sidebar.title("💎 QUEVEDO INTEGRAL")
menu = st.sidebar.radio("MÓDULOS", ["🏠 INICIO", "💰 FINANZAS", "📸 ESCÁNER IA", "🩺 SALUD", "🤖 ASISTENTE"])

# ==========================================
# 4. LÓGICA DE MÓDULOS
# ==========================================

# --- INICIO: PANEL DE CONTROL ---
if menu == "🏠 INICIO":
    st.header(f"📊 Panel de Control: {NOMBRE_PROPIETARIO}")
    c1, c2, c3 = st.columns(3)
    
    df_f = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
    df_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
    num_docs = pd.read_sql_query("SELECT COUNT(*) as total FROM archivador", conn)['total'][0]
    
    with c1:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        st.metric("💰 BALANCE NETO", f"RD$ {df_f['total'][0] or 0:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        st.metric("🩺 ÚLTIMA GLUCOSA", f"{df_g['valor'][0] if not df_g.empty else '0'} mg/dL")
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        st.metric("📂 ARCHIVADOR", f"{num_docs} Registros")
        st.markdown('</div>', unsafe_allow_html=True)

# --- FINANZAS: PRESUPUESTO Y SEMÁFORO ---
elif menu == "💰 FINANZAS":
    st.header("💰 Gestión Financiera con Presupuesto")
    
    # Manejo de Presupuesto Mensual
    res_pre = pd.read_sql_query("SELECT monto_limite FROM presupuesto", conn)
    if res_pre.empty:
        limite = st.number_input("Define tu presupuesto mensual RD$:", value=20000.0)
        if st.button("ESTABLECER LÍMITE"):
            c.execute("INSERT INTO presupuesto VALUES (?)", (limite,))
            conn.commit()
            st.rerun()
    else:
        limite = res_pre['monto_limite'][0]

    with st.form("registro_gastos", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        tipo = col1.selectbox("Tipo", ["GASTO", "INGRESO"])
        cat = col2.selectbox("Categoría", ["Comida", "Salud", "Hogar", "Transporte", "Negocio", "Otros"])
        con = col3.text_input("Concepto (Ej: Supermercado)")
        mon = col4.number_input("Monto RD$", min_value=0.0)
        
        if st.form_submit_button("🚀 REGISTRAR MOVIMIENTO"):
            m_final = mon if tipo == "INGRESO" else -mon
            ahora = datetime.now(ZONA_HORARIA).strftime("%Y-%m-%d")
            c.execute("INSERT INTO finanzas (tipo, categoria, concepto, monto, fecha) VALUES (?,?,?,?,?)",
                      (tipo, cat, con, m_final, ahora))
            conn.commit()
            st.success("Registrado correctamente.")
            st.rerun()

    st.divider()
    
    # Análisis Visual y Semáforo
    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    if not df_f.empty:
        gastos_totales = abs(df_f[df_f['monto'] < 0]['monto'].sum())
        balance = df_f['monto'].sum()
        porcentaje = min(gastos_totales / limite, 1.0)
        
        # Lógica de Color del Semáforo
        color_semaforo = "#4CAF50" if porcentaje < 0.6 else "#FFA500" if porcentaje < 0.9 else "#FF4B4B"
        
        st.markdown(f"### Estado del Gasto: <span style='color:{color_semaforo}'>{gastos_totales:,.2f} / {limite:,.2f} RD$</span>", unsafe_allow_html=True)
        st.progress(porcentaje)
        
        st.write("### Historial Reciente")
        st.dataframe(df_f.sort_values(by="id", ascending=False), use_container_width=True, hide_index=True)
        
        # Botón de Borrado
        id_a_borrar = st.number_input("Escribe el ID para eliminar", min_value=1, step=1)
        if st.button("🗑️ ELIMINAR REGISTRO SELECCIONADO"):
            c.execute(f"DELETE FROM finanzas WHERE id = {id_a_borrar}")
            conn.commit()
            st.rerun()

# --- ESCÁNER IA: QR Y BARRAS ---
elif menu == "📸 ESCÁNER IA":
    st.header("📸 Escáner de Códigos Inteligente")
    st.info("Apunta la cámara a un código QR o de Barras.")
    
    img_file = st.camera_input("Capturar")
    if img_file:
        img = Image.open(img_file)
        decoded_objs = decode(img)
        if decoded_objs:
            for obj in decoded_objs:
                dato = obj.data.decode('utf-8')
                st.success(f"✅ Código {obj.type} Detectado: {dato}")
                if st.button("💾 ARCHIVAR EN SISTEMA"):
                    c.execute("INSERT INTO archivador (nombre, categoria, contenido, fecha) VALUES (?,?,?,?)",
                              (f"Scan_{obj.type}", "DIGITAL", dato, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.toast("Dato guardado en el archivador!")
        else:
            st.warning("No se detectó ningún código. Intenta con mejor luz.")

# --- SALUD: BIOMONITOR ---
elif menu == "🩺 SALUD":
    st.header("🩺 Control de Glucosa")
    col_s1, col_s2 = st.columns([1, 2])
    
    with col_s1:
        valor = st.number_input("Nivel mg/dL", min_value=0, step=1)
        if st.button("💾 GUARDAR MEDICIÓN"):
            ahora = datetime.now(ZONA_HORARIA)
            c.execute("INSERT INTO glucosa (valor, fecha, hora) VALUES (?,?,?)",
                      (valor, ahora.strftime("%Y-%m-%d"), ahora.strftime("%I:%M %p")))
            conn.commit()
            st.success("Medición guardada.")
            st.rerun()
            
    with col_s2:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC LIMIT 10", conn)
        if not df_g.empty:
            fig = px.line(df_g, x="fecha", y="valor", title="Tendencia de Glucosa", markers=True)
            st.plotly_chart(fig, use_container_width=True)

# --- ASISTENTE: BUSCADOR Y ENLACES ---
elif menu == "🤖 ASISTENTE":
    st.header("🤖 Centro de Mando: Luis Rafael")
    
    st.subheader("🔍 Buscador Universal")
    q = st.text_input("¿Qué buscas en tu historial?")
    
    if q:
        # Búsqueda segura en Finanzas y Archivador
        try:
            res_f = pd.read_sql_query(f"SELECT * FROM finanzas WHERE categoria LIKE '%{q}%' OR concepto LIKE '%{q}%'", conn)
            res_a = pd.read_sql_query(f"SELECT * FROM archivador WHERE contenido LIKE '%{q}%'", conn)
            
            if not res_f.empty:
                st.write("💰 Coincidencias en Finanzas:")
                st.dataframe(res_f, use_container_width=True)
            if not res_a.empty:
                st.write("📂 Coincidencias en Archivador:")
                st.dataframe(res_a, use_container_width=True)
            if res_f.empty and res_a.empty:
                st.error("No se encontró nada con esa palabra.")
        except Exception as e:
            st.error("Hubo un error en la búsqueda. Asegúrate de que la base de datos esté actualizada.")

    st.divider()
    st.subheader("📲 Enlaces Rápidos")
    col1, col2, col3 = st.columns(3)
    col1.link_button("🏥 Clínica Referencia", "https://www.referencia.do/")
    col2.link_button("💬 WhatsApp Doctor", "https://wa.me/18095551234?text=Hola%20Luis%20Rafael%20reportando")
    col3.link_button("📧 Abrir Gmail", "https://mail.google.com")

# --- PIE DE PÁGINA ---
st.markdown(f"<br><hr><center>🚀 <b>INVENTO NUEVO: SISTEMA QUEVEDO</b> | {datetime.now().year}</center>", unsafe_allow_html=True)
