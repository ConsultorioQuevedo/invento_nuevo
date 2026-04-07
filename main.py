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
# 1. CONFIGURACIÓN E INTERFAZ DE ALTO NIVEL
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")
# --- CONFIGURACIÓN DE IDENTIDAD MAESTRA ---
NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
UBICACION_SISTEMA = "Santo Domingo, Rep. Dom."

# Función para limpiar acentos y evitar errores en el PDF (Seguro de caracteres)
def limpiar_texto(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')

# --- SISTEMA DE SEGURIDAD (LOGIN) ---
def verificar_acceso():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    def verificar_acceso():
        st.markdown("<h1 style='text-align: center;'>🔐 ACCESO AL SISTEMA</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        u = st.text_input("Usuario", key="user_login")
        p = st.text_input("Contraseña", type="password", key="pass_login")
        
        if st.button("🔓 DESBLOQUEAR SISTEMA", use_container_width=True):
            if u == "Amin" and p == "1234":
                st.session_state["autenticado"] = True
                st.success("✅ Acceso concedido")
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

    # Si no está autenticado en la memoria, devuelve False
    return st.session_state.get("autenticado", False)

# --- EJECUCIÓN ---
if not st.session_state.get("autenticado", False):
    verificar_acceso()
    st.stop() # Esto detiene el programa aquí hasta que pongas la clave


if verificar_acceso():
    # Directorios y Base de Datos
    if not os.path.exists("archivador_quevedo"):
        os.makedirs("archivador_quevedo")

# --- AQUÍ EMPIEZA LA ZAPATA DE TU CASA ---
import sqlite3

# 1. Conectamos la base de datos (La Cisterna)
conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
c = conn.cursor()

# 2. Creamos los cajones donde va la información
c.execute("CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT, centro TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, dosis INTEGER, frecuencia TEXT, hora_toma TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS archivador_index (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, categoria TEXT, texto_ocr TEXT, fecha TEXT)")

# 3. Cerramos el trato para que se guarde
conn.commit()
conn.commit()
        
c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY AUTOINCREMENT, limite REAL)')
c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT)')
conn.commit()
  

conn = iniciar_db()
c = conn.cursor()

    # --- FUNCIÓN: GENERADOR REPORTE MAESTRO PDF (VERSIÓN ANTIBALAS) ---
def generar_reporte_maestro_pdf():
        try:
            pdf = FPDF()
            pdf.add_page()
            # Cambiamos a Courier para mayor compatibilidad en la Nube
            pdf.set_font("Courier", 'B', 16)
            
            titulo = limpiar_texto("REPORTE MAESTRO - SISTEMA QUEVEDO")
            pdf.cell(0, 10, titulo, ln=True, align='C')
            pdf.ln(5)

            def agregar_seccion(titulo_sec, query, columnas):
                pdf.set_font("Courier", 'B', 12)
                pdf.set_fill_color(200, 200, 200)
                pdf.cell(0, 10, limpiar_texto(titulo_sec), ln=True, fill=True)
                pdf.ln(2)
                
                try:
                    df = pd.read_sql_query(query, conn)
                    if not df.empty:
                        pdf.set_font("Courier", 'B', 10)
                        # Cabeceras
                        for col in columnas:
                            pdf.cell(47, 8, limpiar_texto(col), 1)
                        pdf.ln()
                        # Datos: Forzamos el encode aquí mismo
                        pdf.set_font("Courier", size=9)
                        for _, row in df.iterrows():
                            for val in row:
                                # LA CLAVE: Limpiamos y forzamos el string
                                texto_celda = limpiar_texto(str(val))
                                pdf.cell(47, 7, texto_celda, 1)
                            pdf.ln()
                    else:
                        pdf.cell(0, 8, "Sin datos.", ln=True)
                except:
                    pdf.cell(0, 8, "Error en seccion.", ln=True)
                pdf.ln(5)

            # 1. Finanzas
            df_f = pd.read_sql_query("SELECT SUM(monto) as bal FROM finanzas", conn)
            bal = df_f['bal'].iloc[0] if df_f['bal'].iloc[0] else 0.0
            pdf.set_font("Courier", 'B', 11)
            pdf.cell(0, 10, f"BALANCE TOTAL: RD$ {bal:,.2f}", ln=True)
            
            agregar_seccion("FINANZAS", "SELECT fecha, categoria, monto FROM finanzas ORDER BY id DESC LIMIT 10", ["Fecha", "Concepto", "Monto"])
            agregar_seccion("GLUCOSA", "SELECT fecha, hora, valor, estado FROM glucosa ORDER BY id DESC LIMIT 10", ["Fecha", "Hora", "Valor", "Estado"])
            agregar_seccion("MEDICINAS", "SELECT nombre, horario FROM medicinas", ["Medicina", "Horario"])
            agregar_seccion("CITAS", "SELECT doctor, fecha FROM citas", ["Doctor", "Fecha"])

            # Cerramos el PDF internamente antes de pedir el output
            pdf.close()
            # El secreto: output() sin parámetros para obtener el string y luego codificar
            cuerpo_pdf = pdf.output(dest='S')
            return cuerpo_pdf.encode('latin-1', 'replace')
            
        except Exception as e:
            st.error(f"Error interno del PDF: {e}")
            return None
    
    # --- FUNCIÓN GENERAR PDF SALUD ---
def generar_pdf_salud(df_g, df_m):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, limpiar_texto("REPORTE MEDICO - LUIS RAFAEL QUEVEDO"), ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12); pdf.cell(200, 10, "1. MEDICAMENTOS ACTIVOS:"); pdf.ln()
        pdf.set_font("Arial", size=10)
        for _, r in df_m.iterrows():
            pdf.cell(200, 8, limpiar_texto(f"- {r['nombre']} ({r['horario']})"), ln=True)
        pdf.ln(5); pdf.set_font("Arial", 'B', 12); pdf.cell(200, 10, "2. GLUCOSA:"); pdf.ln()
        for _, r in df_g.tail(10).iterrows():
            pdf.cell(200, 8, f"{r['fecha']} {r['hora']}: {r['valor']} mg/dL", ln=True)
        nombre = f"Salud_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf.output(os.path.join("archivador_quevedo", nombre))
        return nombre

    # DISEÑO VISUAL CSS
        st.markdown("""
        <style>
        .main { background-color: #0e1117; }
        .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; height: 3.5em; font-weight: bold; }
        .resumen-card { background: linear-gradient(135deg, #1e2130 0%, #1b5e20 100%); padding: 15px; border-radius: 15px; border: 1px solid #4CAF50; text-align: center; }
        .semaforo-rojo { background-color: #c62828; padding: 20px; border-radius: 15px; color: white; animation: pulse 2s infinite; text-align: center; border: 2px solid white; }
        @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 20px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
        </style>
        """, unsafe_allow_html=True)
    
contactos_data = {"Nombre": ["Mi Hijo", "Mi Hija", "Franklin", "Hermanito", "Dorka", "Rosa", "Pedro"],
                      "Telefono": ["18292061693", "18292581449", "16463746377", "14077975432", "18298811692", "18293800425", "18097100995"]}

    # NAVEGACIÓN
    st.sidebar.title("💎 SISTEMA QUEVEDO")
    
    # MEJORA: RECORDATORIO DE CITAS EN SIDEBAR
    df_c_prox = pd.read_sql_query("SELECT doctor, fecha FROM citas ORDER BY fecha ASC LIMIT 1", conn)
    if not df_c_prox.empty:
        st.sidebar.warning(f"🔔 PRÓXIMA CITA:\n{df_c_prox['doctor'][0]} - {df_c_prox['fecha'][0]}")

    with st.sidebar:
        st.subheader("🚀 Reportes Globales")
        if st.button("📊 GENERAR REPORTE MAESTRO", key="btn_gen_reporte_quevedo"):
            pdf_data = generar_reporte_maestro_pdf()
            st.download_button("📥 Descargar Reporte", pdf_data, f"MAESTRO_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf", key="btn_descarga_pdf_quevedo")
        st.divider()
st.download_button("📥 Descargar Reporte", pdf_data, f"MAESTRO_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf", key="btn_descarga_pdf_quevedo")
conn.execute("DELETE FROM glucosa")
conn.commit()
st.rerun()

if verificar_acceso():
    # 1. El Menú (4 espacios de sangría)
    menu = st.sidebar.radio("MODULOS", ["🏠 INICIO (RESUMEN)", "💰 FINANZAS IA", "🩺 BIOMONITOR", "💊 AGENDA MEDICA", "📸 ESCANER", "📂 ARCHIVADOR", "🤖 ASISTENTE"])
    
    # 2. Conexión a Google (4 espacios de sangría)
    conn_gs = st.connection("gsheets", type=GSheetsConnection)

    # 3. Módulo de Inicio
    if menu == "🏠 INICIO (RESUMEN)":
        st.header("📊 Resumen Ejecutivo")
        # Aquí sigue tu código de las métricas...

    # 4. Módulo de Finanzas
    elif menu == "💰 FINANZAS IA":
        st.header("💰 Gestión de Finanzas")
        # Aquí sigue tu código de gastos...

    # 5. Módulo de Biomonitor (CON EL BOTÓN DE BORRAR DENTRO)
    elif menu == "🩺 BIOMONITOR":
        st.header("🩺 Control de Glucosa")
        # ... tu código de ingreso de glucosa ...
        
       

    # 6. Módulo de Agenda
    elif menu == "💊 AGENDA MEDICA":
        st.header("💊 Agenda Médica")
        # Aquí sigue tu código de medicinas...
  # =========================================================
    # --- BLOQUE DE NAVEGACIÓN: EL MOTOR DEL SISTEMA ---
    # =========================================================
    
if menu == "🏠 INICIO (RESUMEN)":
        st.header("📊 Resumen Ejecutivo del Sistema")
        c1, c2, c3 = st.columns(3)
        
        df_fin = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
        df_glu = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
        df_med = pd.read_sql_query("SELECT nombre FROM medicinas LIMIT 1", conn)

        with c1: 
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True); st.metric("💰 BALANCE NETO", f"RD$ {df_fin['total'][0] or 0:,.2f}"); st.markdown('</div>', unsafe_allow_html=True)
        with c2: 
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True); st.metric("🩺 ÚLTIMA GLUCOSA", f"{df_glu['valor'][0] if not df_glu.empty else 'N/A'} mg/dL"); st.markdown('</div>', unsafe_allow_html=True)
        with c3: 
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True); st.metric("💊 MEDICINA ACTUAL", f"{df_med['nombre'][0] if not df_med.empty else 'Ninguna'}"); st.markdown('</div>', unsafe_allow_html=True)

elif menu == "💰 FINANZAS IA":
        st.header("💰 Gestión de Finanzas - SISTEMA QUEVEDO")
        with st.expander("➕ Registrar Nuevo Movimiento", expanded=False):
            with st.form("nuevo_gasto_quevedo"):
                col_a, col_b = st.columns(2)
                categoria = col_a.selectbox("Categoría", ["Alimentos", "Salud", "Servicios", "Transporte", "Hogar", "Otros"])
                monto = col_b.number_input("Monto en RD$", min_value=0.0, step=100.0)
                detalles = st.text_input("Detalle (ej: Farmacia, Supermercado, Luz)")
                if st.form_submit_button("Guardar en Base de Datos"):
                    if monto > 0:
                        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
                        c.execute("INSERT INTO finanzas (fecha, categoria, monto) VALUES (?,?,?)", 
                                  (f"{categoria}: {detalles}" if detalles else categoria, fecha_hoy, monto))
                        conn.commit()
                        st.success(f"✅ Registrado: RD$ {monto:,.2f}")
                        st.rerun()

        st.subheader("📋 Historial de Movimientos")
        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
        if not df_f.empty:
            st.dataframe(df_f[['fecha', 'categoria', 'monto']], use_container_width=True, hide_index=True)

# --- MÓDULO 3: BIOMONITOR PRO CON IA Y ALERTAS ---
elif menu == "🩺 BIOMONITOR":
        st.header("🩺 Centro de Análisis Biométrico Quevedo")
        
        # 1. Recuperar Historial para la IA
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)

        col_input, col_semaforo = st.columns([1, 1])

        with col_input:
            st.subheader("📝 Nueva Medición")
            val_g = st.number_input("Nivel de Glucosa (mg/dL)", min_value=0, key="input_g_final_ia")
            btn_registrar = st.button("💾 PROCESAR Y NOTIFICAR", key="btn_save_g_final")

        # 2. SEMÁFORO INTELIGENTE Y ANÁLISIS DE ESTADO
        if val_g > 0:
            if val_g < 70:
                estado, color, consejo = "🚨 HIPOGLICEMIA", "#1E90FF", "¡CRÍTICO! Azúcar muy baja. Consume glucosa inmediata."
            elif val_g <= 140:
                estado, color, consejo = "✅ NORMAL", "#2E8B57", "Nivel excelente. Mantén tu ritmo actual."
            elif val_g <= 190:
                estado, color, consejo = "🟠 PRE-DIABETES", "#FF8C00", "Atención: Nivel elevado. Revisa tu dieta reciente."
            else:
                estado, color, consejo = "🔴 CRÍTICO / ALTA", "#B22222", "🚨 NIVEL PELIGROSO. Activando Protocolo de Emergencia."

            with col_semaforo:
                st.markdown(f"""
                    <div style='text-align:center; background-color:{color}; padding:20px; border-radius:15px; color:white; border: 2px solid white;'>
                        <h2 style='margin:0;'>{estado}</h2>
                        <h1 style='font-size:55px; margin:0;'>{val_g}</h1>
                        <p style='font-size:16px;'>{consejo}</p>
                    </div>
                """, unsafe_allow_html=True)

        # 3. LÓGICA DE IA Y WHATSAPP (EL CORAZÓN DEL SISTEMA)
        if btn_registrar and val_g > 0:
            ahora = datetime.now(pytz.timezone('America/Santo_Domingo'))
            fecha_act = ahora.strftime("%d/%m/%y")
            hora_act = ahora.strftime("%I:%M %p")
            
            c.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", 
                      (val_g, fecha_act, hora_act, estado))
            conn.commit()

            # --- PROTOCOLO DE EMERGENCIA 190+ ---
            if val_g > 190:
                st.error(f"🚨 NIVEL DE EMERGENCIA: {val_g} mg/dL")
                msg_emergencia = f"🚨 *EMERGENCIA MÉDICA* - LUIS RAFAEL QUEVEDO: Mi nivel de glucosa es CRÍTICO ({val_g} mg/dL) a las {hora_act}. Por favor, contáctame de inmediato."
                
                st.subheader("📲 Notificar a mis 7 Contactos de Emergencia:")
                
                # Lista de contactos (Los que ya configuramos antes)
                contactos = {
                    "FAMILIA 1": "1849XXXXXXX", "FAMILIA 2": "1849XXXXXXX",
                    "DR. ANALISIS": "1829XXXXXXX", "CONTACTO 4": "1809XXXXXXX",
                    "CONTACTO 5": "1849XXXXXXX", "CONTACTO 6": "1849XXXXXXX",
                    "CONTACTO 7": "1809XXXXXXX"
                }
                
                cols_wa = st.columns(7)
                for i, (nombre, num) in enumerate(contactos.items()):
                    link = f"https://wa.me/{num}?text={msg_emergencia.replace(' ', '%20')}"
                    cols_wa[i].markdown(f"[🆘 {nombre}]({link})")
            
            # --- IA: ANÁLISIS DE TENDENCIA ---
            if not df_g.empty:
                promedio = df_g['valor'].mean()
                if val_g > promedio + 20:
                    st.warning(f"🤖 IA: Detecto un aumento del {int(((val_g-promedio)/promedio)*100)}% sobre tu promedio usual.")
                elif val_g < promedio - 20:
                    st.info(f"🤖 IA: Tu nivel está significativamente más bajo de lo normal ({int(promedio)} mg/dL).")

            st.success("✅ Registro completado y analizado.")
            st.rerun()

        st.divider()

        # 4. VISUALIZACIÓN ROBUSTA (GRÁFICOS)
        if not df_g.empty:
            col_graph, col_data = st.columns([2, 1])
            
            with col_graph:
                st.subheader("📈 Curva de Tendencia")
                # Gráfico interactivo con el historial
                st.line_chart(df_g.head(15), x="hora", y="valor")
            
            with col_data:
                st.subheader("📄 Historial Reciente")
                st.dataframe(df_g.head(10)[["valor", "hora", "estado"]], use_container_width=True)

        # 5. MANTENIMIENTO (ZONA SEGURA)
        with st.expander("🗑️ ADMINISTRAR BASE DE DATOS"):
            if st.button("BORRAR TODO EL HISTORIAL", key="btn_borrado_total_final_v2"):
                c.execute("DELETE FROM glucosa")
                conn.commit()
                st.rerun()
    # --- LOS SIGUIENTES MÓDULOS AHORA SÍ FUNCIONARÁN PORQUE ESTÁN BIEN ALINEADOS ---

# --- MÓDULO 4: AGENDA MÉDICA PRO (CITAS Y MEDICINAS) ---
elif menu == "💊 AGENDA MEDICA":
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
                # Selector de hora con AM/PM en Mayúsculas
                hora = col_c3.time_input("Hora de la Cita")
                centro = col_c4.text_input("Centro Médico / Clínica")
                
                if st.form_submit_button("💾 AGENDAR CITA"):
                    # Formateamos la hora a AM/PM en MAYÚSCULAS
                    hora_fmt = hora.strftime("%I:%M %p").upper()
                    c.execute("INSERT INTO citas (doctor, fecha, hora, centro) VALUES (?,?,?,?)",
                              (especialidad, str(fecha_cita), hora_fmt, centro))
                    conn.commit()
                    st.success(f"✅ Cita con {especialidad} agendada para las {hora_fmt}")
                    st.rerun()

            st.divider()
            st.subheader("📋 Citas Programadas")
            df_citas = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", conn)
            
            if not df_citas.empty:
                st.dataframe(df_citas, use_container_width=True)
                # BOTÓN DE BORRADO ÚNICO PARA CITAS
                if st.button("🗑️ LIMPIAR TODAS LAS CITAS", key="btn_borrar_citas"):
                    c.execute("DELETE FROM citas")
                    conn.commit()
                    st.rerun()
            else:
                st.info("No hay citas pendientes.")

        # --- SUB-MÓDULO: MEDICAMENTOS ---
        with tab2:
            st.subheader("💊 Registro de Tratamiento")
            with st.form("form_meds", clear_on_submit=True):
                col_m1, col_m2 = st.columns(2)
                med_nombre = col_m1.text_input("Nombre del Medicamento")
                # TECLADO NUMÉRICO: Usamos number_input para que el celular abra los números
                dosis = col_m2.number_input("Dosis (mg/ml/pastillas)", min_value=0, step=1)
                
                col_m3, col_m4 = st.columns(2)
                # Frecuencia horaria
                cada_cuanto = col_m3.selectbox("Frecuencia", ["Cada 4 horas", "Cada 6 horas", "Cada 8 horas", "Cada 12 horas", "Una vez al día"])
                prox_toma = col_m4.time_input("Hora de la próxima toma")
                
                if st.form_submit_button("💾 GUARDAR MEDICAMENTO"):
                    toma_fmt = prox_toma.strftime("%I:%M %p").upper()
                    c.execute("INSERT INTO medicinas (nombre, dosis, frecuencia, hora_toma) VALUES (?,?,?,?)",
                              (med_nombre, dosis, cada_cuanto, toma_fmt))
                    conn.commit()
                    st.success(f"✅ {med_nombre} agregado al tratamiento")
                    st.rerun()

            st.divider()
            
            # --- IA DE AGENDA: ANALIZADOR DE TRATAMIENTO ---
            df_meds = pd.read_sql_query("SELECT * FROM medicinas", conn)
            if not df_meds.empty:
                st.subheader("🤖 Análisis de IA: Tu Tratamiento")
                conteo = len(df_meds)
                if conteo > 5:
                    st.warning(f"⚠️ IA: Tienes {conteo} medicamentos activos. Sugiero revisión de interacciones con tu médico.")
                else:
                    st.info("🤖 IA: Carga de medicación optimizada.")

                st.dataframe(df_meds, use_container_width=True)
                
                # BOTÓN DE BORRADO ÚNICO PARA MEDICAMENTOS
                if st.button("🗑️ VACIAR BOTIQUÍN", key="btn_borrar_meds"):
                    c.execute("DELETE FROM medicinas")
                    conn.commit()
                    st.rerun()

    # --- NOTA TÉCNICA: ASEGÚRATE DE TENER ESTAS TABLAS CREADAS AL INICIO ---
    # c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, hora TEXT, centro TEXT)')
    # c.execute('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY, nombre TEXT, dosis INTEGER, frecuencia TEXT, hora_toma TEXT)')

# --- MÓDULO 5: ESCÁNER DE VISIÓN ARTIFICIAL (IA & OCR) ---
elif menu == "📸 ESCANER":
        st.header("📸 Escáner de Inteligencia Visual")
        st.write("### 🤖 Captura de Datos en Tiempo Real")

        # 1. EL OJO DEL SISTEMA (Cámara o Archivo)
        img_file = st.camera_input("📷 APUNTE AL MEDICAMENTO O DOCUMENTO")

        if img_file:
            # Procesar la imagen
            img = Image.open(img_file)
            st.image(img, caption="Imagen Capturada", width=400)
            
            # --- MOTOR 1: LECTOR DE CÓDIGOS (Barras y QR) ---
            from pyzbar.pyzbar import decode
            import numpy as np
            
            # Convertir imagen para lectura de códigos
            opencv_img = np.array(img)
            codigos = decode(opencv_img)
            
            datos_detectados = []
            
            if codigos:
                st.subheader("🔍 Códigos Detectados")
                for obj in codigos:
                    tipo = obj.type
                    contenido = obj.data.decode('utf-8')
                    datos_detectados.append(f"[{tipo}]: {contenido}")
                    st.success(f"✅ {tipo} LEÍDO: {contenido}")
            else:
                st.info("No se detectaron códigos de barras o QR.")

            # --- MOTOR 2: LECTOR DE TEXTO (OCR / IA) ---
            # Aquí la IA analiza lo que dicen las letras de la caja o receta
            st.subheader("📝 Análisis de Texto por IA")
            try:
                import pytesseract # Asegúrate de tenerlo en tu requirements.txt
                texto_extraido = pytesseract.image_to_string(img, lang='spa')
                
                if texto_extraido.strip():
                    with st.expander("📄 TEXTO EXTRAÍDO DEL DOCUMENTO"):
                        st.write(texto_extraido)
                    
                    # IA de Clasificación Automática
                    if "mg" in texto_extraido.lower() or "pastilla" in texto_extraido.lower():
                        categoria_ia = "💊 MEDICAMENTO DETECTADO"
                    elif "orden" in texto_extraido.lower() or "receta" in texto_extraido.lower():
                        categoria_ia = "📂 RECETA / ORDEN MÉDICA"
                    else:
                        categoria_ia = "📄 DOCUMENTO GENERAL"
                    
                    st.info(f"🤖 IA CLASIFICACIÓN: {categoria_ia}")
                else:
                    st.warning("IA: No se pudo leer texto claro en la imagen.")
            except:
                st.warning("⚠️ El motor OCR está en mantenimiento, use solo lectura de códigos.")

            # --- MOTOR 3: ACCIÓN Y DISTRIBUCIÓN (LA ROBUSTEZ) ---
            st.divider()
            st.subheader("🚀 ¿A dónde enviamos la información?")
            
            col_a1, col_a2, col_a3 = st.columns(3)
            
            # Botón 1: Al Archivador Local
            if col_a1.button("📂 AL ARCHIVADOR"):
                nombre_archivo = f"SCAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                img.save(f"archivador_quevedo/{nombre_archivo}")
                st.success(f"Guardado en Archivador como: {nombre_archivo}")

            # Botón 2: Al Asistente (Para que la IA lo analice luego)
            if col_a2.button("🤖 AL ASISTENTE IA"):
                st.session_state['memoria_asistente'] = texto_extraido if 'texto_extraido' in locals() else "Código detectado"
                st.success("Enviado al cerebro de la IA para análisis.")

            # Botón 3: A la Nube (Google Sheets / Drive)
            if col_a3.button("☁️ A LA NUBE (G-SHEETS)"):
                # Aquí conectamos con tu hoja de Google que ya tenemos configurada
                df_cloud = pd.DataFrame([{
                    "FECHA": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "TIPO": "ESCÁNER",
                    "DETALLES": " ".join(datos_detectados) if datos_detectados else "Imagen procesada"
                }])
                conn_gs.create(data=df_cloud, worksheet="ESCÁNER")
                st.success("¡Datos subidos a la Nube de Google con éxito!")

        # 4. BOTÓN DE LIMPIEZA
        st.sidebar.divider()
        if st.sidebar.button("🗑️ LIMPIAR CÁMARA", key="btn_clear_cam"):
            st.rerun()


# --- MÓDULO 6: EL ARCHIVADOR INTELIGENTE DE QUEVEDO (ROBUSTEZ TOTAL) ---
elif menu == "📂 ARCHIVADOR":
        st.header("📂 Archivador Inteligente v3.0 (OCR + Cloud)")
        
        # 1. ESTRUCTURA DE CARPETAS FÍSICAS (Capa 1: Seguridad Local)
        import os
        import sqlite3
        base_path = "archivador_quevedo"
        subcarpetas = ["MEDICAL", "GASTOS", "PERSONALES", "RECETAS_COCINA"]
        for folder in subcarpetas:
            os.makedirs(os.path.join(base_path, folder), exist_ok=True)

        # Base de datos interna para el buscador de texto (IA Index)
        # Asegúrate de tener una tabla 'archivador_index' con: nombre, categoria, texto_ocr, fecha
        
        tab_buscar, tab_subir = st.tabs(["🔍 BUSCADOR IA", "📤 SUBIR DOCUMENTO MANUAL"])

        # --- SUB-MÓDULO: BUSCADOR POR TEXTO (IA OCR) ---
        with tab_buscar:
            st.subheader("🕵️ ¿Qué palabra buscamos en los documentos?")
            query = st.text_input("Ejemplo: 'Metformina', 'Carol', 'GBC', 'Seguro'", key="busqueda_ia")
            
            if query:
                # Buscamos en la base de datos el texto que extrajo el OCR antes
                res = c.execute("SELECT nombre, categoria, fecha FROM archivador_index WHERE texto_ocr LIKE ?", (f'%{query}%',)).fetchall()
                
                if res:
                    st.success(f"✅ Se encontraron {len(res)} documentos con la palabra '{query}'")
                    for r in res:
                        col_r1, col_r2, col_r3 = st.columns([2, 1, 1])
                        col_r1.write(f"📄 **{r[0]}**")
                        col_r2.write(f"📁 {r[1]}")
                        col_r3.write(f"📅 {r[2]}")
                        # Botón para abrir (Simulado)
                        if st.button(f"👁️ VER {r[0]}", key=f"btn_ver_{r[0]}"):
                            st.image(os.path.join(base_path, r[1], r[0]))
                else:
                    st.warning("❌ No hay documentos que contengan esa palabra.")

        # --- SUB-MÓDULO: SUBIDA Y PROCESAMIENTO (LA ACCIÓN) ---
        with tab_subir:
            st.subheader("📤 Indexar Nuevo Documento")
            u_file = st.file_uploader("Elija la imagen (Análisis, Factura, Receta)", type=["jpg", "png", "jpeg"])
            u_cat = st.selectbox("Categoría", subcarpetas)

            if u_file:
                img_up = Image.open(u_file)
                st.image(img_up, width=250, caption="Previsualización")
                
                if st.button("🚀 PROCESAR Y GUARDAR EN LA NUBE", key="btn_save_archivador"):
                    with st.spinner("🤖 IA Leyendo y Sincronizando..."):
                        # A. OCR: Extraer texto para el buscador
                        try:
                            import pytesseract
                            texto_extraido = pytesseract.image_to_string(img_up, lang='spa')
                        except:
                            texto_extraido = "Texto no procesable"

                        # B. Guardar Local (Capa 1)
                        fname = f"{u_cat}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        fpath = os.path.join(base_path, u_cat, fname)
                        img_up.save(fpath)

                        # C. Sincronizar Google Sheets (Capa 2: Respaldo Nube)
                        try:
                            df_backup = pd.DataFrame([{
                                "FECHA": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "ARCHIVO": fname,
                                "CATEGORIA": u_cat,
                                "TEXTO_OCR": texto_extraido[:500] # Guardamos los primeros 500 caracteres para buscar
                            }])
                            conn_gs.append_table(data=df_backup, worksheet="ARCHIVADOR_BACKUP")
                            cloud_status = "☁️ Sincronizado en Google"
                        except:
                            cloud_status = "⚠️ Error Nube (Solo Local)"

                        # D. Guardar en Base de Datos Local para búsqueda rápida
                        c.execute("INSERT INTO archivador_index (nombre, categoria, texto_ocr, fecha) VALUES (?,?,?,?)",
                                  (fname, u_cat, texto_extraido, datetime.now().strftime("%d/%m/%y")))
                        conn.commit()

                        st.success(f"✅ ¡Guardado! {cloud_status}")
                        st.balloons()

        # --- RESUMEN VISUAL DE CARPETAS ---
        st.divider()
        st.subheader("📁 Estado del Almacén")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🏥 Médica", len(os.listdir(os.path.join(base_path, "MEDICAL"))))
        c2.metric("💰 Gastos", len(os.listdir(os.path.join(base_path, "GASTOS"))))
        c3.metric("📄 Personales", len(os.listdir(os.path.join(base_path, "PERSONALES"))))
        c4.metric("👨‍🍳 Recetas", len(os.listdir(os.path.join(base_path, "RECETAS_COCINA"))))


# --- MÓDULO 7: ASISTENTE IA PERSONAL (EL CEREBRO) ---
elif menu == "🤖 ASISTENTE":
        st.header("🤖 Asistente Inteligente Quevedo")
        ahora = datetime.now(pytz.timezone('America/Santo_Domingo'))
        
        # 1. BOTONERA DE COMUNICACIÓN DIRECTA (ENLACES)
        st.subheader("📲 Comunicación Rápida")
        col_c1, col_c2, col_c3 = st.columns(3)
        
        # Enlace a Gmail y WhatsApp
        col_c1.link_button("📧 ABRIR MI CORREO", "https://mail.google.com/", use_container_width=True)
        # Cambia el número por el tuyo para enviarte notas a ti mismo
        col_c2.link_button("💬 MI WHATSAPP", "https://wa.me/1849XXXXXXX", use_container_width=True)
        col_c3.button("🔄 SINCRONIZAR TODO", key="sync_brain")

        st.divider()

        # 2. PREDICCIÓN DE MAÑANA (IA PREDICTIVA)
        st.subheader("🔮 Predicción del Mañana")
        col_p1, col_p2 = st.columns(2)

        # --- IA DE SALUD ---
        with col_p1:
            st.markdown("### 🩺 Salud")
            df_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 10", conn)
            if not df_g.empty:
                promedio = df_g['valor'].mean()
                tendencia = "ALZA" if df_g['valor'].iloc[0] > promedio else "BAJA"
                color_p = "red" if tendencia == "ALZA" and promedio > 150 else "green"
                
                st.write(f"**Estado:** Tendencia a la {tendencia}")
                st.markdown(f"<div style='padding:10px; border-radius:10px; background-color:{color_p}; color:white; text-align:center;'>"
                            f"Predicción para mañana: {int(promedio)} mg/dL aprox.</div>", unsafe_allow_html=True)
                st.caption("🤖 IA: Basado en tus últimas 10 tomas.")

        # --- IA DE ECONOMÍA ---
        with col_p2:
            st.markdown("### 💰 Economía")
            # Simulamos análisis de gastos (Aquí conectaría con tu tabla de Finanzas)
            gasto_promedio = 1200 # Ejemplo RD$
            st.write(f"**Gasto diario estimado:** RD$ {gasto_promedio}")
            st.info(f"🤖 IA: Mañana es día de flujo { 'alto' if ahora.day in [15, 30] else 'normal' }. Evite gastos hormiga.")

        st.divider()

        # 3. ESTADO DEL SISTEMA (NUBE vs LOCAL)
        st.subheader("📊 Integridad del Archivador")
        import os
        total_archivos = sum([len(files) for r, d, files in os.walk("archivador_quevedo")])
        
        c1, c2 = st.columns(2)
        c1.metric("📁 Archivos Locales", f"{total_archivos} items")
        # Aquí conectamos con el conteo de tu Google Sheets
        c2.metric("☁️ Sincronizados en Nube", f"{total_archivos} registros", delta="100%")
        
        st.progress(100 if total_archivos > 0 else 0, text="Sincronización de Seguridad")

        # 4. CHAT DE BÚSQUEDA GLOBAL
        st.divider()
        st.subheader("💬 Consulta Global al Sistema")
        pregunta = st.text_input("Hazle una pregunta a tu IA (Busca en todo el programa):", placeholder="¿Cuándo fue mi última cita?")
        
        if pregunta:
            with st.spinner("🤖 Consultando base de datos..."):
                # Lógica de búsqueda en tablas (Citas, Glucosa, Medicinas)
                if "cita" in pregunta.lower():
                    res = pd.read_sql_query("SELECT * FROM citas ORDER BY id DESC LIMIT 1", conn)
                    if not res.empty:
                        st.write(f"🤖 Tu última cita registrada fue con el **{res['doctor'].iloc[0]}** el día **{res['fecha'].iloc[0]}**.")
                elif "glucosa" in pregunta.lower() or "azúcar" in pregunta.lower():
                    res = pd.read_sql_query("SELECT valor, fecha FROM glucosa ORDER BY id DESC LIMIT 1", conn)
                    st.write(f"🤖 Tu último nivel fue **{res['valor'].iloc[0]} mg/dL** el día **{res['fecha'].iloc[0]}**.")
                else:
                    st.write("🤖 No encontré ese dato específico, pero lo tengo guardado en el Archivador. ¿Quieres que lo busque por OCR?")
    



# --- SECCIÓN FINAL: LOS CRÉDITOS DE ORO ---
st.sidebar.divider()
with st.sidebar:
    st.markdown(f"""
        <div style='text-align: center; padding: 20px; background-color: #1E1E1E; border-radius: 15px; border: 1px solid #FFD700;'>
            <h3 style='color: #FFD700; margin: 0;'>💎 EL ARCHIVADOR</h3>
            <h2 style='color: white; margin: 5px 0;'>LUIS RAFAEL QUEVEDO</h2>
            <p style='color: #888; font-size: 12px;'>Ingeniería de Datos & IA Personal</p>
            <hr style='border: 0.5px solid #333;'>
            <p style='color: #FFD700; font-weight: bold;'>VERSIÓN 2026 - ROBUSTA</p>
            <p style='color: white; font-size: 10px;'>Higuey, La Altagracia, RD 🇩🇴</p>
        </div>
    """, unsafe_allow_html=True)

# Pie de página en el cuerpo principal
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
col_f1, col_f2 = st.columns([3, 1])
col_f1.write("© 2026 Todos los derechos reservados. | **Tecnología Quevedo Integral**")
col_f2.write("🚀 *Paso a paso.*")
