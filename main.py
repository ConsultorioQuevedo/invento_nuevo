import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import pytz
from datetime import datetime
from sklearn.linear_model import LinearRegression
import numpy as np

# 1. CONFIGURACIÓN E INTERFAZ DE VANGUARDIA
st.set_page_config(page_title="SISTEMA QUEVEDO - OMNI", layout="wide")

# 2. MOTOR DE DATOS BLINDADO (TODO LOCAL, NADA DE GOOGLE)
def iniciar_db():
    conn = sqlite3.connect("sistema_quevedo_master.db", check_same_thread=False)
    c = conn.cursor()
    # Crear todas las tablas necesarias
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, momento TEXT, valor INTEGER, notas TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    conn.commit()
    return conn

conn = iniciar_db()

# 3. RELOJ DE PRECISIÓN (RD)
zona = pytz.timezone('America/Santo_Domingo')
ahora = datetime.now(zona)
f_hoy = ahora.strftime("%d/%m/%Y")
h_hoy = ahora.strftime("%I:%M %p")

# --- CABECERA DEL SISTEMA ---
st.title("🌌 INVENTO: SISTEMA INTEGRAL QUEVEDO")
st.write(f"**Usuario:** Luis Rafael Quevedo | **Estatus:** 100% Operativo | **Hora:** {h_hoy}")

# LAS 5 PESTAÑAS DEL PODER
t1, t2, t3, t4, t5 = st.tabs(["💰 FINANZAS", "🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS", "🧠 NÚCLEO IA"])

# --- PESTAÑA 1: FINANZAS PRO ---
with t1:
    st.subheader("📊 Control de Activos y Gastos")
    with st.form("f_finanzas", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([1,2,2,1])
        with c1: tipo = st.selectbox("TIPO", ["INGRESO", "GASTO"])
        with c2: cat = st.text_input("CATEGORÍA").upper()
        with c3: det = st.text_input("DETALLE").upper()
        with c4: mon = st.number_input("MONTO RD$", min_value=0.0)
        if st.form_submit_button("EJECUTAR REGISTRO"):
            m_final = mon if tipo == "INGRESO" else -mon
            conn.execute("INSERT INTO finanzas (fecha, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?)", 
                         (f_hoy, tipo, cat, det, m_final))
            conn.commit()
            st.success("✅ Transacción guardada en base de datos.")

    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
    if not df_f.empty:
        st.dataframe(df_f, use_container_width=True, hide_index=True)
        st.metric("BALANCE DISPONIBLE", f"RD$ {df_f['monto'].sum():,.2f}")

# --- PESTAÑA 2: MONITOR DE GLUCOSA ---
with t2:
    st.subheader("🩸 Biometría en Tiempo Real")
    with st.form("f_salud", clear_on_submit=True):
        col_s1, col_s2 = st.columns(2)
        with col_s1: val_g = st.number_input("Valor mg/dL:", min_value=0)
        with col_s2: mom_g = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Antes de Cena", "Post-Cena"])
        not_g = st.text_area("Notas adicionales:")
        if st.form_submit_button("REGISTRAR SALUD"):
            conn.execute("INSERT INTO glucosa (fecha, momento, valor, notas) VALUES (?,?,?,?)", 
                         (f_hoy, mom_g, val_g, not_g))
            conn.commit()
            st.success("✅ Biometría actualizada.")

    df_g = pd.read_sql_query("SELECT * FROM glucosa", conn)
    if not df_g.empty:
        fig = px.line(df_g, x="id", y="valor", title="Evolución Glucosa", markers=True)
        st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 3: GESTIÓN DE MEDICAMENTOS ---
with t3:
    st.subheader("💊 Inventario de Tratamientos")
    with st.form("f_meds", clear_on_submit=True):
        m_nom = st.text_input("Nombre:")
        m_dos = st.text_input("Dosis (ej. 500mg):")
        m_hor = st.text_input("Horario:")
        if st.form_submit_button("AÑADIR"):
            conn.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (m_nom.upper(), m_dos, m_hor))
            conn.commit()
    st.table(pd.read_sql_query("SELECT nombre, dosis, horario FROM medicamentos", conn))

# --- PESTAÑA 4: AGENDA DE CITAS ---
with t4:
    st.subheader("📅 Control de Consultas")
    with st.form("f_citas", clear_on_submit=True):
        c_doc = st.text_input("Doctor/Especialista:")
        c_fec = st.date_input("Fecha:")
        c_mot = st.text_input("Motivo:")
        if st.form_submit_button("AGENDAR"):
            conn.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (c_doc.upper(), str(c_fec), c_mot))
            conn.commit()
    st.dataframe(pd.read_sql_query("SELECT * FROM citas", conn), use_container_width=True)

# --- PESTAÑA 5: NÚCLEO DE SUPER INTELIGENCIA ---
with t5:
    st.header("🧠 Análisis IA Predictivo")
    col_ia1, col_ia2 = st.columns(2)
    
    with col_ia1:
        st.write("### 📈 Futuro Financiero")
        if len(df_f) > 1:
            X = np.arange(len(df_f)).reshape(-1, 1)
            y = df_f["monto"].values
            model = LinearRegression().fit(X, y)
            st.metric("Predicción Próximo Flujo", f"RD$ {model.predict([[len(df_f)+1]])[0]:,.2f}")
        else: st.info("IA: Esperando más datos financieros...")

    with col_ia2:
        st.write("### ❤️ Salud Inteligente")
        if not df_g.empty:
            ult = df_g["valor"].iloc[-1]
            if ult > 180: st.error(f"Alerta IA: Glucosa Alta ({ult})")
            elif ult < 70: st.warning(f"Aviso IA: Glucosa Baja ({ult})")
            else: st.success("Sistema IA: Niveles en rango óptimo.")

# --- PIE DE PÁGINA (CRÉDITOS) ---
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'><strong>SISTEMA INVENTO - DISEÑADORES: LUIS RAFAEL QUEVEDO</strong></p>", unsafe_allow_html=True)
