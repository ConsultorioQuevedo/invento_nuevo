import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import pytz
from PIL import Image
import unicodedata
from fpdf import FPDF

# 1. ARRANQUE DIRECTO
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

# BYPASS DE SEGURIDAD (Entrada libre para Luis)
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = True

# 2. LA ZAPATA (Base de Datos y Carpetas)
if not os.path.exists("archivador_quevedo"):
    os.makedirs("archivador_quevedo")
    for folder in ["MEDICAL", "GASTOS", "PERSONALES", "RECETAS"]:
        os.makedirs(os.path.join("archivador_quevedo", folder), exist_ok=True)

conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
c = conn.cursor()

# Creación de tablas inteligentes
tablas = [
    "glucosa (id INTEGER PRIMARY KEY, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)",
    "finanzas (id INTEGER PRIMARY KEY, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)",
    "citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, hora TEXT, centro TEXT)",
    "medicinas (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, frecuencia TEXT, hora_toma TEXT)",
    "archivador_index (id INTEGER PRIMARY KEY, nombre TEXT, categoria TEXT, texto_ocr TEXT, fecha TEXT)"
]
for t in tablas:
    c.execute(f"CREATE TABLE IF NOT EXISTS {t}")
conn.commit()

# Diseño Visual (CSS)
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 10px; background-color: #1b5e20; color: white; height: 3em; }
    .card { background: #1e2130; padding: 20px; border-radius: 15px; border-left: 5px solid #4CAF50; }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.title("💎 SISTEMA QUEVEDO")
st.sidebar.info(f"Usuario: LUIS RAFAEL\n📍 Santo Domingo, RD")

menu = st.sidebar.radio("MENÚ PRINCIPAL", 
    ["🏠 INICIO", "💰 FINANZAS IA", "🩺 BIOMONITOR", "💊 AGENDA MÉDICA", "📸 ESCANER", "📂 ARCHIVADOR"])



if menu == "🏠 INICIO":
    st.header("🏠 Panel de Control - Luis Rafael Quevedo")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🩺 Salud")
        ult_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
        if not ult_g.empty:
            st.metric("Última Glucosa", f"{ult_g['valor'][0]} mg/dL")
        else:
            st.write("Sin datos")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("💰 Finanzas")
        total_f = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
        monto = total_f['total'][0] if total_f['total'][0] else 0
        st.metric("Total Gastos", f"RD$ {monto:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📅 Citas")
        prox_c = pd.read_sql_query("SELECT doctor, fecha FROM citas ORDER BY id DESC LIMIT 1", conn)
        if not prox_c.empty:
            st.write(f"{prox_c['doctor'][0]}")
            st.caption(f"Fecha: {prox_c['fecha'][0]}")
        else:
            st.write("No hay citas")
        st.markdown('</div>', unsafe_allow_html=True)



elif menu == "💰 FINANZAS IA":
    st.header("💰 Control Financiero - Sistema Quevedo")
    
    # 1. Panel de Registro
    with st.expander("📝 REGISTRAR NUEVO GASTO / PAGO", expanded=True):
        with st.form("registro_finanzas"):
            col_f1, col_f2 = st.columns(2)
            
            with col_f1:
                categoria = st.selectbox("Categoría", ["Salud (Laboratorio/Farmacia)", "Alimentos", "Servicios", "Hogar", "Otros"])
                monto = st.number_input("Monto (RD$)", min_value=0.0, step=100.0)
            
            with col_f2:
                detalle = st.text_input("Detalle del gasto", placeholder="Ej: Analítica en Referencia")
                fecha_manual = st.date_input("Fecha", datetime.now())

            if st.form_submit_button("💾 GUARDAR EN BASE DE DATOS"):
                c.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)",
                          (detalle, categoria, monto, fecha_manual.strftime("%d/%m/%Y")))
                conn.commit()
                st.success(f"✅ Registrado: RD$ {monto} en {categoria}")
                st.rerun()

    # 2. Resumen Inteligente
    st.subheader("📊 Historial de Movimientos")
    
    # Consultar datos
    df_f = pd.read_sql_query("SELECT fecha as Fecha, categoria as Categoría, tipo as Detalle, monto as 'Monto RD$' FROM finanzas ORDER BY id DESC", conn)
    
    if not df_f.empty:
        # Mostrar tabla
        st.dataframe(df_f, use_container_width=True)
        
        # Cálculo de totales
        total_gastado = df_f["Monto RD$"].sum()
        st.info(f"💰 **Total Acumulado en Registros:** RD$ {total_gastado:,.2f}")
        
        # Botón para limpiar (Solo si tú quieres resetear)
        if st.sidebar.button("🗑️ Limpiar Historial"):
            c.execute("DELETE FROM finanzas")
            conn.commit()
            st.rerun()
    else:
        st.warning("No hay gastos registrados todavía.")


if menu == "🩺 BIOMONITOR":
    st.header("🩺 Control Biométrico Inteligente")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("📝 Nueva Medición")
        val_g = st.number_input("Nivel de Glucosa (mg/dL)", min_value=0, key="gluc_input")
        if st.button("💾 REGISTRAR Y ANALIZAR"):
            ahora = datetime.now(pytz.timezone('America/Santo_Dominico'))
            # Lógica de Semáforo
            if val_g < 70: est = "🚨 BAJA"; col = "blue"
            elif val_g <= 140: est = "✅ NORMAL"; col = "green"
            else: est = "⚠️ ALTA"; col = "red"
            
            c.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)",
                      (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), est))
            conn.commit()
            st.success(f"Registrado como {est}")
            
            # Alerta de Emergencia (190+)
            if val_g > 190:
                msg = f"ALERTA: Glucosa de Luis Rafael en {val_g} mg/dL".replace(" ", "%20")
                st.error("🚨 NIVEL CRÍTICO: Notificar por WhatsApp")
                st.markdown(f"[📲 ENVIAR ALERTA A LA FAMILIA](https://wa.me/18292061693?text={msg})")

    with col2:
        st.subheader("📈 Historial Reciente")
        df_g = pd.read_sql_query("SELECT fecha, hora, valor, estado FROM glucosa ORDER BY id DESC LIMIT 10", conn)
        st.table(df_g)


elif menu == "💊 AGENDA MÉDICA":
    st.header("💊 Gestión de Salud y Citas")
    
    tab1, tab2 = st.tabs(["📅 Citas Médicas", "💊 Mis Medicamentos"])
    
    with tab1:
        st.subheader("🗓️ Programar Nueva Cita")
        with st.form("form_citas"):
            col_c1, col_c2 = st.columns(2)
            doc = col_c1.text_input("Doctor / Especialidad", placeholder="Ej: Cardiólogo")
            centro = col_c2.text_input("Centro Médico", placeholder="Ej: Referencia / Plaza de la Salud")
            f_cita = col_c1.date_input("Fecha de la cita")
            h_cita = col_c2.time_input("Hora de la cita")
            
            if st.form_submit_button("💾 AGENDAR CITA"):
                c.execute("INSERT INTO citas (doctor, fecha, hora, centro) VALUES (?,?,?,?)",
                          (doc, f_cita.strftime("%d/%m/%Y"), h_cita.strftime("%I:%M %p"), centro))
                conn.commit()
                st.success(f"Cita con {doc} agendada!")
                st.rerun()

        st.subheader("📋 Citas Pendientes")
        df_c = pd.read_sql_query("SELECT fecha as Fecha, hora as Hora, doctor as Doctor, centro as Lugar FROM citas ORDER BY id DESC", conn)
        st.table(df_c)

    with tab2:
        st.subheader("💊 Registro de Tratamientos")
        with st.expander("➕ Añadir Medicamento", expanded=False):
            with st.form("form_meds"):
                m_nombre = st.text_input("Nombre del Medicamento")
                col_m1, col_m2 = st.columns(2)
                m_dosis = col_m1.text_input("Dosis (Ej: 500mg)")
                m_frec = col_m2.selectbox("Frecuencia", ["Cada 8 horas", "Cada 12 horas", "Una vez al día", "Según necesidad"])
                m_hora = st.time_input("Hora de la próxima toma")
                
                if st.form_submit_button("💾 GUARDAR MEDICINA"):
                    c.execute("INSERT INTO medicinas (nombre, dosis, frecuencia, hora_toma) VALUES (?,?,?,?)",
                              (m_nombre, m_dosis, m_frec, m_hora.strftime("%I:%M %p")))
                    conn.commit()
                    st.success(f"{m_nombre} añadido al tratamiento")
                    st.rerun()

        st.subheader("📑 Lista de Medicamentos Actual")
        df_m = pd.read_sql_query("SELECT nombre as Medicina, dosis as Dosis, frecuencia as Frecuencia, hora_toma as 'Próxima Toma' FROM medicinas", conn)
        st.dataframe(df_m, use_container_width=True)



elif menu == "📸 ESCANER":
    st.header("📸 Inteligencia Visual (OCR)")
    foto = st.camera_input("📷 Captura el resultado o medicina")
    
    if foto:
        img = Image.open(foto)
        st.image(img, caption="Imagen capturada", width=300)
        
        if st.button("📂 GUARDAR EN ARCHIVADOR"):
            fname = f"DOC_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            img.save(os.path.join("archivador_quevedo", "MEDICAL", fname))
            # Aquí se puede agregar la lógica de GSheets para la nube
            st.success(f"Archivo {fname} guardado en carpeta MEDICAL.")

elif menu == "📂 ARCHIVADOR":
    st.header("📂 Expediente Digital de Quevedo")
    carpeta = st.selectbox("Carpeta", ["MEDICAL", "GASTOS", "RECETAS"])
    archivos = os.listdir(os.path.join("archivador_quevedo", carpeta))
    
    if archivos:
        for arc in archivos:
            st.write(f"📄 {arc}")
    else:
        st.info("No hay documentos en esta sección.")


elif menu == "🤖 ASISTENTE":
    st.header("🤖 Asistente Inteligente Quevedo")
    st.info("Pregúntame sobre tus niveles de azúcar, tus gastos o tus documentos.")

    # 1. Memoria del Chat
    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []

    # Mostrar historial de la conversación
    for m in st.session_state.mensajes:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # 2. Entrada del Usuario
    if prompt := st.chat_input("¿En qué te ayudo hoy, Luis?"):
        st.session_state.mensajes.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 3. Lógica de Respuesta IA (Simulada o Conectada)
        with st.chat_message("assistant"):
            respuesta = ""
            # Ejemplo de análisis inteligente basado en tus datos
            if "glucosa" in prompt.lower():
                ult_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
                if not ult_g.empty:
                    valor = ult_g['valor'][0]
                    respuesta = f"Luis, tu última lectura fue de {valor} mg/dL. "
                    respuesta += "Está un poco alta, recuerda beber mucha agua." if valor > 140 else "Vas muy bien, mantente así."
                else:
                    respuesta = "Aún no tengo registros de glucosa para analizar."
            
            elif "gastos" in prompt.lower() or "dinero" in prompt.lower():
                total = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)['total'][0]
                respuesta = f"Hasta ahora has registrado un total de RD$ {total:,.2f} en gastos. ¿Quieres ver el detalle por categorías?"
            
            else:
                respuesta = "Entendido, Luis. Estoy analizando tu petición en el Archivador de Quevedo. ¿Quieres que busque una receta o un análisis médico específico?"

            st.markdown(respuesta)
            st.session_state.mensajes.append({"role": "assistant", "content": respuesta})



