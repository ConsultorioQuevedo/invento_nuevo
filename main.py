import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import pytz
from datetime import datetime
from sklearn.linear_model import LinearRegression
import numpy as np

# 1. CONFIGURACIÓN DE INTERFAZ
st.set_page_config(page_title="SISTEMA QUEVEDO - OMNI", layout="wide")

# 2. MOTOR DE DATOS LOCAL (TOTALMENTE INDEPENDIENTE)
def iniciar_db():
    conn = sqlite3.connect("sistema_quevedo_master.db", check_same_thread=False)
    c = conn.cursor()
    # Tabla de Finanzas
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    # Tabla de Salud (Glucosa)
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, momento TEXT, valor INTEGER)')
    # Tabla de Medicamentos
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    # Tabla de Citas
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    conn.commit()
    return conn

conn = iniciar_db()

# 3. TIEMPO REAL (DOMINICANO)
zona = pytz.timezone('America/Santo_Domingo')
ahora = datetime.now(zona)
fecha_hoy = ahora.strftime("%d/%m/%Y")
hora_hoy = ahora.strftime("%I:%M %p")

# --- CABECERA ---
st.title("🌌 INVENTO: SISTEMA INTEGRAL QUEVEDO")
st.write(f"**Usuario:** Luis Rafael Quevedo | **Fecha:** {fecha_hoy} | **Hora:** {hora_hoy}")

# PESTAÑAS CON TODO EL CONTENIDO
t1, t2, t3, t4, t5 = st.tabs(["💰 FINANZAS", "🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS", "🧠 NÚCLEO IA"])

# --- SECCIÓN 1: FINANZAS ---
with t1:
    st.subheader("📝 Registro Financiero")
    with st.form("form_f", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([1,2,2,1])
        with col1: tipo = st.selectbox("TIPO", ["INGRESO", "GASTO"])
        with col2: cat = st.text_input("CATEGORÍA").upper()
        with col3: det = st.text_input("DETALLE").upper()
        with col4: mon = st.number_input("MONTO RD$", min_value=0.0)
        if st.form_submit_button("GUARDAR TRANSACCIÓN"):
            m_final = mon if tipo == "INGRESO" else -mon
            conn.execute("INSERT INTO finanzas (fecha, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?)", 
                         (fecha_hoy, tipo, cat, det, m_final))
            conn.commit()
            st.success("✅ Finanzas actualizadas.")

    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
    if not df_f.empty:
        st.dataframe(df_f, use_container_width=True, hide_index=True)
        st.metric("BALANCE DISPONIBLE", f"RD$ {df_f['monto'].sum():,.2f}")

# --- SECCIÓN 2: GLUCOSA ---
with t2:
    st.subheader("🩸 Monitor de Biometría")
    with st.form("form_g", clear_on_submit=True):
        v_g = st.number_input("Valor mg/dL:", min_value=0)
        m_g = st.selectbox("Momento:", ["Ayunas", "Post-Comida", "Antes de Dormir"])
        if st.form_submit_button("REGISTRAR GLUCOSA"):
            conn.execute("INSERT INTO glucosa (fecha, momento, valor) VALUES (?,?,?)", (fecha_hoy, m_g, v_g))
            conn.commit()
            st.success("✅ Nivel guardado.")
    
    df_g = pd.read_sql_query("SELECT * FROM glucosa", conn)
    if not df_g.empty:
        fig = px.line(df_g, x="id", y="valor", title="Tendencia de Salud", markers=True)
        st.plotly_chart(fig, use_container_width=True)

# --- SECCIÓN 3: MEDICAMENTOS ---
with t3:
    st.subheader("💊 Gestión de Medicinas")
    with st.form("form_m", clear_on_submit=True):
        n_m = st.text_input("Nombre del Medicamento:")
        d_m = st.text_input("Dosis (ej: 500mg):")
        h_m = st.text_input("Horario (ej: 8:00 AM):")
        if st.form_submit_button("AÑADIR MEDICAMENTO"):
            conn.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n_m.upper(), d_m, h_m))
            conn.commit()
    
    df_m = pd.read_sql_query("SELECT nombre, dosis, horario FROM medicamentos", conn)
    st.table(df_m)

# --- SECCIÓN 4: CITAS ---
with t4:
    st.subheader("📅 Agenda Médica")
    with st.form("form_c", clear_on_submit=True):
        doc = st.text_input("Especialista/Doctor:")
        fec = st.date_input("Fecha de la Cita:")
        mot = st.text_input("Motivo:")
        if st.form_submit_button("AGENDAR CITA"):
            conn.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc.upper(), str(fec), mot))
            conn.commit()
            st.success("✅ Cita agendada.")
    
    df_c = pd.read_sql_query("SELECT doctor, fecha, motivo FROM citas", conn)
    st.dataframe(df_c, use_container_width=True)

# --- SECCIÓN 5: NÚCLEO IA ---
with t5:
    st.header("🧠 Inteligencia Artificial Predictiva")
    if len(df_f) > 1:
        X = np.arange(len(df_f)).reshape(-1, 1)
        y = df_f["monto"].values
        model = LinearRegression().fit(X, y)
        pred = model.predict([[len(df_f) + 1]])
        st.metric("PRÓXIMO MOVIMIENTO ESTIMADO", f"RD$ {pred[0]:,.2f}")
        st.info("💡 La IA analiza tus patrones para sugerir mejores decisiones financieras.")
    else:
        st.warning("Se requieren al menos 2 registros para activar el análisis de IA.")

# --- PIE DE PÁGINA ---
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <p><strong>SISTEMA INVENTO - VERSIÓN AUTÓNOMA TOTAL</strong></p>
        <p>Diseñadores: Luis Rafael Quevedo</p>
    </div>
    """, 
    unsafe_allow_html=True
)
