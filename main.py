import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz
import numpy as np
import unicodedata
from PIL import Image
import io
from streamlit_gsheets import GSheetsConnection
from pyzbar.pyzbar import decode

# ==========================================
# 1. CONFIGURACIÓN E IDENTIDAD (SIN LOGIN)
# ==========================================
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
UBICACION_SISTEMA = "Santo Domingo, Rep. Dom."
ZONA_HORARIA = pytz.timezone('America/Santo_Domingo')

# Conexión a Google Sheets (Nube)
conn_gs = st.connection("gsheets", type=GSheetsConnection)

def limpiar_texto(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')

# ==========================================
# 2. BASE DE DATOS Y DIRECTORIOS
# ==========================================
def inicializar_todo():
    # Estructura de Carpetas
    base = "archivador_quevedo"
    folders = ["MEDICAL", "GASTOS", "PERSONALES", "RECETAS_COCINA"]
    if not os.path.exists(base):
        os.makedirs(base)
    for f in folders:
        os.makedirs(os.path.join(base, f), exist_ok=True)
    
    # Base de Datos SQLite
    db_conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
    db_c = db_conn.cursor()
    # Tablas
    db_c.execute("CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)")
    db_c.execute("CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT, centro TEXT)")
    db_c.execute("CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, dosis INTEGER, frecuencia TEXT, hora_toma TEXT)")
    db_c.execute("CREATE TABLE IF NOT EXISTS archivador_index (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, categoria TEXT, texto_ocr TEXT, fecha TEXT)")
    db_c.execute("CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)")
    db_conn.commit()
    return db_conn, db_c

conn, c = inicializar_todo()

# ==========================================
# 3. INTERFAZ Y ESTILOS
# ==========================================
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; font-weight: bold; height: 3em; }
    .resumen-card { background: linear-gradient(135deg, #1e2130 0%, #1b5e20 100%); padding: 20px; border-radius: 15px; border: 1px solid #4CAF50; text-align: center; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Navegación
st.sidebar.title("💎 QUEVEDO INTEGRAL")
menu = st.sidebar.radio("MODULOS PRINCIPALES", 
    ["🏠 INICIO", "💰 FINANZAS", "🩺 BIOMONITOR", "💊 AGENDA MÉDICA", "📸 ESCÁNER IA", "📂 ARCHIVADOR", "🤖 ASISTENTE"])

# ==========================================
# 4. LÓGICA DE MÓDULOS
# ==========================================

# --- INICIO ---
if menu == "🏠 INICIO":
    st.header(f"📊 Panel de Control: {NOMBRE_PROPIETARIO}")
    c1, c2, c3 = st.columns(3)
    
    try:
        df_fin = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
        df_glu = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
        
        with c1:
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
            st.metric("💰 BALANCE TOTAL", f"RD$ {df_fin['total'][0] or 0:,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
            st.metric("🩺 ÚLTIMA GLUCOSA", f"{df_glu['valor'][0] if not df_glu.empty else '0'} mg/dL")
            st.markdown('</div>', unsafe_allow_html=True)
    except:
        st.warning("Inicializando datos...")

# --- MÓDULO: FINANZAS ROBUSTO (IA & ANALÍTICA) ---
elif menu == "💰 FINANZAS":
    st.header("💰 Gestión Financiera Inteligente")
    
    # 1. ENTRADA DE DATOS

    with st.form("form_finanzas_ingresos", clear_on_submit=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        tipo = col_f1.selectbox("Tipo de Movimiento", ["GASTO", "INGRESO"])
        categoria = col_f2.selectbox("Categoría", ["Comida", "Salud", "Hogar", "Transporte", "Negocio", "Otros"])
        monto = col_f3.number_input("Monto RD$", min_value=0.0, step=100.0)
        
        if st.form_submit_button("🚀 REGISTRAR MOVIMIENTO"):
            # Si es gasto, lo guardamos como negativo para que la suma sea automática
            monto_final = monto if tipo == "INGRESO" else -monto
            c.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)",
                      (tipo, categoria, monto_final, datetime.now(ZONA_HORARIA).strftime("%d/%m/%y")))
            conn.commit()
            st.success(f"¡{tipo} de RD$ {monto:,.2f} registrado con éxito!")
            st.rerun()

    st.divider()

    # 2. CÁLCULO DE BALANCE (EL CEREBRO DEL MÓDULO)
    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    
    if not df_f.empty:
        ingresos = df_f[df_f['monto'] > 0]['monto'].sum()
        gastos = abs(df_f[df_f['monto'] < 0]['monto'].sum())
        balance = ingresos - gastos
        
        # Métricas principales con diseño visual
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("📥 TOTAL INGRESOS", f"RD$ {ingresos:,.2f}", delta_color="normal")
        c_m2.metric("📤 TOTAL GASTOS", f"RD$ {gastos:,.2f}", delta="-"+f"{gastos:,.2f}", delta_color="inverse")
        c_m3.metric("💎 BALANCE NETO", f"RD$ {balance:,.2f}", delta=f"{balance:,.2f}")

        # 3. ANÁLISIS DE IA (ROBUSTEZ)
        st.subheader("🤖 Análisis de IA Financiera")
        if ingresos > 0:
            porcentaje_gasto = (gastos / ingresos) * 100
            if porcentaje_gasto > 80:
                st.error(f"⚠️ **ALERTA IA:** Estás gastando el {porcentaje_gasto:.1f}% de tus ingresos. Peligro de liquidez.")
            elif porcentaje_gasto > 50:
                st.warning(f"💡 **SUGERENCIA IA:** Tus gastos ocupan el {porcentaje_gasto:.1f}%. Considera reducir categorías no esenciales.")
            else:
                st.success(f"✅ **IA STATUS:** Finanzas saludables. Gastas solo el {porcentaje_gasto:.1f}% de lo que entra.")
        
        # 4. GRÁFICOS DE DISTRIBUCIÓN
        st.divider()
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.write("### 📊 Gastos por Categoría")
            df_gastos = df_f[df_f['monto'] < 0].copy()
            df_gastos['monto'] = abs(df_gastos['monto'])
            if not df_gastos.empty:
                fig_pie = px.pie(df_gastos, values='monto', names='categoria', hole=0.4,
                                 color_discrete_sequence=px.colors.sequential.Greens_r)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No hay gastos para mostrar gráfico.")

        with col_g2:
            st.write("### 📈 Historial de Movimientos")
            st.dataframe(df_f.tail(10), use_container_width=True, hide_index=True)

        # 5. BOTÓN DE LIMPIEZA
        if st.button("🗑️ REINICIAR CONTABILIDAD"):
            c.execute("DELETE FROM finanzas")
            conn.commit()
            st.rerun()
    else:
        st.info("Aún no hay movimientos registrados. Empieza agregando un ingreso o gasto arriba.")


# --- BIOMONITOR ---
elif menu == "🩺 BIOMONITOR":
    st.header("🩺 Control Biométrico")
    col_g1, col_g2 = st.columns([1, 2])
    with col_g1:
        val_g = st.number_input("Nivel de Glucosa (mg/dL)", min_value=0, step=1)
        if st.button("💾 GUARDAR MEDICIÓN"):
            ahora = datetime.now(ZONA_HORARIA)
            c.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", 
                      (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), "REGISTRADO"))
            conn.commit()
            st.success("¡Dato guardado!")
            st.rerun()
    with col_g2:
        df_hist = pd.read_sql_query("SELECT valor, fecha, hora FROM glucosa ORDER BY id DESC LIMIT 10", conn)
        if not df_hist.empty:
            fig = px.line(df_hist, x="fecha", y="valor", title="Tendencia Reciente", markers=True)
            st.plotly_chart(fig, use_container_width=True)
            
# --- MÓDULO: AGENDA MÉDICA PRO (CITAS Y MEDICINAS) ---
elif menu == "💊 AGENDA MÉDICA":
        st.header("📅 Agenda Médica y Control de Fármacos")
        tab1, tab2 = st.tabs(["📝 CITAS MÉDICAS", "💊 MEDICAMENTOS"])

        # --- SUB-MÓDULO: CITAS MÉDICAS ---
        with tab1:
            st.subheader("🏥 Programar Nueva Cita")
            with st.form("form_citas", clear_on_submit=True):
                col_c1, col_c2 = st.columns(2)
                especialidad = col_c1.text_input("Especialidad / Doctor")
                fecha_cita = col_c2.date_input("Fecha de la Cita")
                
                col_c3, col_c4 = st.columns(2)
                hora = col_c3.time_input("Hora de la Cita")
                centro = col_c4.text_input("Centro Médico / Clínica")
                
                if st.form_submit_button("💾 AGENDAR CITA"):
                    hora_fmt = hora.strftime("%I:%M %p").upper()
                    c.execute("INSERT INTO citas (doctor, fecha, hora, centro) VALUES (?,?,?,?)",
                              (especialidad, str(fecha_cita), hora_fmt, centro))
                    conn.commit()
                    st.success(f"✅ Cita con {especialidad} agendada.")
                    st.rerun()

            st.divider()
            st.subheader("📋 Citas Programadas")
            
            try:
                df_citas = pd.read_sql_query("SELECT id, doctor, fecha, hora, centro FROM citas ORDER BY fecha ASC", conn)
            except Exception:
                c.execute("""CREATE TABLE IF NOT EXISTS citas 
                             (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT, centro TEXT)""")
                conn.commit()
                df_citas = pd.DataFrame(columns=["id", "doctor", "fecha", "hora", "centro"])
            
            if not df_citas.empty:
                st.dataframe(df_citas, use_container_width=True, hide_index=True)
                if st.button("🗑️ LIMPIAR TODAS LAS CITAS", key="btn_borrar_citas"):
                    c.execute("DELETE FROM citas")
                    conn.commit()
                    st.warning("Historial de citas eliminado.")
                    st.rerun()
            else:
                st.info("No tienes citas pendientes en este momento.")

        # --- SUB-MÓDULO: MEDICAMENTOS ---
        with tab2:
            st.subheader("💊 Registro de Tratamiento")
            with st.form("form_meds", clear_on_submit=True):
                col_m1, col_m2 = st.columns(2)
                med_nombre = col_m1.text_input("Nombre del Medicamento")
                dosis = col_m2.number_input("Dosis (mg/ml/pastillas)", min_value=0, step=1)
                
                col_m3, col_m4 = st.columns(2)
                cada_cuanto = col_m3.selectbox("Frecuencia", ["Cada 4 horas", "Cada 6 horas", "Cada 8 horas", "Cada 12 horas", "Una vez al día"])
                prox_toma = col_m4.time_input("Hora de la próxima toma")
                
                if st.form_submit_button("💾 GUARDAR MEDICAMENTO"):
                    toma_fmt = prox_toma.strftime("%I:%M %p").upper()
                    c.execute("INSERT INTO medicinas (nombre, dosis, frecuencia, hora_toma) VALUES (?,?,?,?)",
                              (med_nombre, dosis, cada_cuanto, toma_fmt))
                    conn.commit()
                    st.success(f"✅ {med_nombre} agregado.")
                    st.rerun()

            st.divider()
            st.subheader("💊 Medicación Activa")
            
            try:
                df_meds = pd.read_sql_query("SELECT * FROM medicinas", conn)
            except Exception:
                c.execute("CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, dosis INTEGER, frecuencia TEXT, hora_toma TEXT)")
                conn.commit()
                df_meds = pd.DataFrame(columns=["id", "nombre", "dosis", "frecuencia", "hora_toma"])
            
            if not df_meds.empty:
                st.dataframe(df_meds, use_container_width=True, hide_index=True)
                
                # IA de análisis de carga
                conteo = len(df_meds)
                if conteo > 5:
                    st.warning(f"⚠️ IA Alerta: Tienes {conteo} medicamentos activos. Consulta interacciones.")
                else:
                    st.info("🤖 IA: Carga de medicación estable.")
                
                if st.button("🗑️ VACIAR BOTIQUÍN", key="btn_borrar_meds"):
                    c.execute("DELETE FROM medicinas")
                    conn.commit()
                    st.rerun()
            else:
                st.info("No hay medicamentos registrados.")

# --- MÓDULO: 📸 ESCÁNER IA ROBUSTO (BARCODE, QR & OCR) ---
elif menu == "📸 ESCÁNER IA":
        st.header("📸 Estación de Escaneo Profesional")
        st.info("Sostenga el documento de forma firme y con buena luz para un escaneo óptimo.")

        img_file = st.camera_input("📷 CAPTURAR DOCUMENTO O CÓDIGO")

        if img_file is not None:
            try:
                # 1. SEGURIDAD Y PREPARACIÓN
                import cv2
                import numpy as np
                import pytesseract
                from pyzbar.pyzbar import decode
                from PIL import Image

                img = Image.open(img_file)
                img_np = np.array(img.convert('RGB')) 

                col_res1, col_res2 = st.columns(2)

                with col_res1:
                    st.image(img, caption="Imagen Capturada", use_container_width=True)

                with col_res2:
                    with st.spinner("🤖 IA Analizando..."):
                        # --- MOTOR 1: DETECCIÓN DE CÓDIGOS (BARCODE/QR) ---
                        codigos = decode(img)
                        if codigos:
                            st.subheader("🏷️ Códigos Detectados")
                            for obj in codigos:
                                tipo = obj.type
                                datos = obj.data.decode('utf-8')
                                st.success(f"**TIPO:** {tipo}")
                                st.code(datos)
                                if "http" in datos:
                                    st.link_button("🌐 Abrir Enlace", datos)
                        else:
                            st.warning("🔍 No se detectaron códigos.")

                        # --- MOTOR 2: LECTURA DE TEXTO (OCR) ---
                        st.subheader("📝 Contenido del Documento")
                        gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
                        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                        
                        texto_extraido = pytesseract.image_to_string(thresh, lang='spa')

                        if texto_extraido.strip():
                            st.text_area("Texto Detectado:", texto_extraido, height=200)
                            
                            # --- MOTOR 3: IA DE CLASIFICACIÓN ---
                            palabras_clave = ["glucosa", "hemoglobina", "receta", "mg/dl", "laboratorio"]
                            encontradas = [p for p in palabras_clave if p in texto_extraido.lower()]
                            
                            if encontradas:
                                st.info(f"💡 **Sugerencia IA:** Tipo detectado: **{', '.join(encontradas).upper()}**.")
                        else:
                            st.error("No se pudo extraer texto legible.")

                # 2. ACCIONES DE ARCHIVADO
                st.divider()
                col_acc1, col_acc2 = st.columns(2)
                
                with col_acc1:
                    cat_save = st.selectbox("Clasificar como:", ["MEDICAL", "GASTOS", "PERSONALES"])
                
                with col_acc2:
                    if st.button("💾 ARCHIVAR PERMANENTEMENTE", key="btn_archivar_robusto"):
                        nombre_archivo = f"SCAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        # Aseguramos que la carpeta existe
                        if not os.path.exists(os.path.join("archivador_quevedo", cat_save)):
                            os.makedirs(os.path.join("archivador_quevedo", cat_save))
                        
                        ruta = os.path.join("archivador_quevedo", cat_save, nombre_archivo)
                        img.save(ruta, "JPEG", quality=90)
                        
                        c.execute("INSERT INTO archivador_index (nombre, categoria, texto_ocr, fecha) VALUES (?,?,?,?)",
                                  (nombre_archivo, cat_save, texto_extraido, datetime.now().strftime("%d/%m/%y")))
                        conn.commit()
                        st.success(f"✅ Documento blindado y guardado en {cat_save}")

            except Exception as e:
                st.error(f"❌ Error en el motor de visión: {str(e)}")

                        
# ==========================================
# MÓDULO INTEGRADO: FINANZAS & ARCHIVADOR PRO
# ==========================================

# --- MÓDULO: 💰 FINANZAS (IA & ANALÍTICA) ---
if menu == "💰 FINANZAS":
    st.header("💰 Gestión Financiera Inteligente")
    
    with st.form("form_finanzas_reportes", clear_on_submit=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        tipo = col_f1.selectbox("Tipo de Movimiento", ["GASTO", "INGRESO"])
        categoria = col_f2.selectbox("Categoría", ["Comida", "Salud", "Hogar", "Transporte", "Negocio", "Otros"])
        monto = col_f3.number_input("Monto RD$", min_value=0.0, step=100.0)
        
        if st.form_submit_button("🚀 REGISTRAR MOVIMIENTO"):
            # Lógica Robusta: Los gastos se guardan negativos para balance automático
            monto_final = monto if tipo == "INGRESO" else -monto
            ahora = datetime.now(ZONA_HORARIA).strftime("%d/%m/%y")
            c.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)",
                      (tipo, categoria, monto_final, ahora))
            conn.commit()
            st.success(f"✅ {tipo} registrado: RD$ {monto:,.2f}")
            st.rerun()

    st.divider()

    # Cerebro Analítico de Finanzas
    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    
    if not df_f.empty:
        ingresos = df_f[df_f['monto'] > 0]['monto'].sum()
        gastos = abs(df_f[df_f['monto'] < 0]['monto'].sum())
        balance = ingresos - gastos
        
        # Panel de Métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("📥 INGRESOS", f"RD$ {ingresos:,.2f}")
        m2.metric("📤 GASTOS", f"RD$ {gastos:,.2f}", delta=f"-{gastos:,.2f}", delta_color="inverse")
        m3.metric("💎 BALANCE", f"RD$ {balance:,.2f}", delta=f"{balance:,.2f}")

        # --- IA DE ANÁLISIS FINANCIERO ---
        st.subheader("🤖 Análisis de IA")
        if ingresos > 0:
            ratio = (gastos / ingresos) * 100
            if ratio > 80:
                st.error(f"⚠️ **ALERTA IA:** Gastos críticos ({ratio:.1f}%). Se recomienda frenar salidas de efectivo.")
            elif ratio > 50:
                st.warning(f"💡 **SUGERENCIA IA:** Gastos moderados ({ratio:.1f}%). Vigile la categoría '{df_f[df_f['monto'] < 0]['categoria'].mode()[0]}'.")
            else:
                st.success(f"✅ **IA STATUS:** Finanzas saludables. Capacidad de ahorro del {100-ratio:.1f}%.")

        # Gráfico de Distribución
        df_gasto_chart = df_f[df_f['monto'] < 0].copy()
        df_gasto_chart['monto'] = abs(df_gasto_chart['monto'])
        if not df_gasto_chart.empty:
            fig = px.pie(df_gasto_chart, values='monto', names='categoria', hole=0.5, title="Distribución de Gastos")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Esperando datos para iniciar análisis financiero.")

# --- MÓDULO: 📂 ARCHIVADOR (CON VALIDACIÓN DE SEGURIDAD) ---
elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador Inteligente v3.0")
    t_bus, t_sub = st.tabs(["🔍 BUSCADOR IA", "📤 SUBIDA PROTEGIDA"])

    with t_bus:
        q = st.text_input("Buscar palabra clave en documentos...")
        if q:
            res = pd.read_sql_query("SELECT nombre, categoria, fecha FROM archivador_index WHERE texto_ocr LIKE ?", conn, params=(f'%{q}%',))
            if not res.empty:
                st.write(res)
            else:
                st.warning("No se encontraron coincidencias.")

    with t_sub:
        st.subheader("📤 Indexar Documento")
        u_file = st.file_uploader("Subir imagen", type=["jpg", "png", "jpeg"])
        u_cat = st.selectbox("Destino", ["MEDICAL", "GASTOS", "PERSONALES", "RECETAS_COCINA"])

        if u_file is not None:
            try:
                # VALIDACIÓN DE SEGURIDAD: Evita el UnidentifiedImageError
                u_file.seek(0) # Resetear puntero
                img_check = Image.open(u_file)
                
                # Normalización de formato para robustez
                if img_check.mode in ("RGBA", "P"):
                    img_check = img_check.convert("RGB")
                
                st.image(img_check, width=300, caption="Documento detectado")

                if st.button("🚀 PROCESAR Y ARCHIVAR"):
                    with st.spinner("🤖 IA Analizando archivo..."):
                        fname = f"{u_cat}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        path = os.path.join("archivador_quevedo", u_cat, fname)
                        
                        # Guardado Seguro
                        img_check.save(path, format="JPEG", quality=85)
                        
                        # Registro en Base de Datos
                        c.execute("INSERT INTO archivador_index (nombre, categoria, fecha) VALUES (?,?,?)",
                                  (fname, u_cat, datetime.now(ZONA_HORARIA).strftime("%d/%m/%y")))
                        conn.commit()
                        
                        st.success(f"✅ Archivado correctamente en {u_cat}")
                        st.balloons()
            
            except Exception as e:
                st.error("❌ Error de Seguridad: El archivo no es una imagen válida o está corrupto.")

    # Resumen de Almacén
    st.divider()
    st.subheader("📊 Estado del Archivador")
    cols = st.columns(4)
    for i, folder in enumerate(["MEDICAL", "GASTOS", "PERSONALES", "RECETAS_COCINA"]):
        path = os.path.join("archivador_quevedo", folder)
        count = len(os.listdir(path)) if os.path.exists(path) else 0
        cols[i].metric(folder, f"{count} Docs")


# --- MÓDULO: 🤖 ASISTENTE IA PERSONAL (PROACTIVO) ---
elif menu == "🤖 ASISTENTE IA":
        st.header(f"👋 ¡Buen día, Luis Rafael!")
        st.subheader("Soy tu IA Personal. Aquí está el estado de tu sistema:")

        # 1. ESTADO DEL SISTEMA (Resumen de Inteligencia)
        col_st1, col_st2, col_st3 = st.columns(3)
        
        try:
            total_citas = len(pd.read_sql_query("SELECT id FROM citas", conn))
            total_meds = len(pd.read_sql_query("SELECT id FROM medicinas", conn))
            total_docs = len(pd.read_sql_query("SELECT id FROM archivador_index", conn))
        except:
            total_citas = total_meds = total_docs = 0

        col_st1.metric("📅 Citas", total_citas)
        col_st2.metric("💊 Medicinas", total_meds)
        col_st3.metric("📂 Documentos", total_docs)

        st.divider()

        # 2. PANEL DE CONTROL PROACTIVO
        tab_ia1, tab_ia2, tab_ia3 = st.tabs(["🚀 ACCIONES RÁPIDAS", "🩺 ANÁLISIS DE SALUD", "🔍 BÚSQUEDA GLOBAL"])

        with tab_ia1:
            st.write("### 🚨 Pendientes para hoy")
            hoy = datetime.now().strftime("%Y-%m-%d")
            
            # Recordatorio de Citas
            try:
                proxima = pd.read_sql_query(f"SELECT * FROM citas WHERE fecha >= '{hoy}' ORDER BY fecha ASC LIMIT 1", conn)
                if not proxima.empty:
                    st.warning(f"⚠️ **ATENCIÓN:** Tu próxima cita es con **{proxima['doctor'][0]}** el día **{proxima['fecha'][0]}**.")
                    # Cálculo de días (Predicción)
                    dias = (datetime.strptime(proxima['fecha'][0], "%Y-%m-%d") - datetime.now()).days
                    st.info(f"💡 Faltan **{dias}** días. ¿Quieres que preparemos los documentos?")
                else:
                    st.success("✅ No tienes compromisos médicos pendientes.")
            except:
                st.write("No hay datos en la agenda.")

        with tab_ia2:
            st.write("### 🤖 Análisis de Tratamiento")
            try:
                df_meds = pd.read_sql_query("SELECT * FROM medicinas", conn)
                if not df_meds.empty:
                    st.write(f"Actualmente manejas **{len(df_meds)}** fármacos.")
                    if len(df_meds) > 4:
                        st.error("❗ **ALERTA IA:** Carga de medicamentos alta. Verifica con tu médico posibles interacciones.")
                    else:
                        st.success("✔ Carga de medicamentos bajo control.")
                    
                    st.info("📌 **Sugerencia:** Mantén tu hidratación alta al tomar estos medicamentos.")
                else:
                    st.write("No tienes medicamentos registrados.")
            except:
                st.write("Módulo de medicinas no inicializado.")

        with tab_ia3:
            st.write("### 🕵️ Explorador del Sistema")
            query = st.text_input("Dime qué buscas (Nombre de médico, medicina o documento):")
            if query:
                # La IA recorre las 3 tablas principales al mismo tiempo
                res_c = pd.read_sql_query(f"SELECT * FROM citas WHERE doctor LIKE '%{query}%'", conn)
                res_m = pd.read_sql_query(f"SELECT * FROM medicinas WHERE nombre LIKE '%{query}%'", conn)
                res_a = pd.read_sql_query(f"SELECT * FROM archivador_index WHERE texto_ocr LIKE '%{query}%'", conn)
                
                if not res_c.empty: st.write("📅 En Citas:", res_c)
                if not res_m.empty: st.write("💊 En Medicinas:", res_m)
                if not res_a.empty: st.write("📂 En Archivador:", res_a)
                if res_c.empty and res_m.empty and res_a.empty:
                    st.error("No encontré nada con ese nombre en el Archivador de Quevedo.")

        st.divider()
        # 3. CONECTIVIDAD TOTAL
        st.write("### 📲 Enlaces de Emergencia")
        c1, c2, c3 = st.columns(3)
        c1.link_button("🏥 Mi Clínica", "https://referencia.do") # Como está en Referencia ahora mismo...
        c2.link_button("📩 Email Médico", "mailto:doctor@ejemplo.com")
        c3.link_button("📞 WhatsApp", "https://wa.me/tu_numero")         
    


# --- PIE DE PÁGINA PERSONALIZADO ---
st.divider()
st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: transparent;
        color: grey;
        text-align: center;
        font-size: 12px;
        padding: 10px;
    }
    </style>
    <div class="footer">
        <p>🚀 <b>Invento Nuevo: El Archivador de Quevedo</b> | Desarrollado por <b>Luis Rafael</b> © 2026</p>
    </div>
    """,
    unsafe_allow_html=True
)

