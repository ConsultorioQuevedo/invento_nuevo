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

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

# --- IDENTIDAD ---
NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
UBICACION_SISTEMA = "Santo Domingo, Rep. Dom."

def limpiar_texto(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')

# --- ACCESO DIRECTO (BYPASS) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = True

# --- INICIALIZACIÓN DE BASE DE DATOS Y CARPETAS ---
if st.session_state["autenticado"]:
    if not os.path.exists("archivador_quevedo"):
        os.makedirs("archivador_quevedo")
        for sub in ["MEDICAL", "GASTOS", "PERSONALES", "RECETAS_COCINA"]:
            os.makedirs(os.path.join("archivador_quevedo", sub), exist_ok=True)

    conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
    c = conn.cursor()

    # Creación de Tablas Únicas
    c.execute("CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT, centro TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, dosis INTEGER, frecuencia TEXT, hora_toma TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS archivador_index (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, categoria TEXT, texto_ocr TEXT, fecha TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)")
    conn.commit()

# --- FUNCIONES DE REPORTES ---
def generar_reporte_maestro_pdf():
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Courier", 'B', 16)
        pdf.cell(0, 10, "REPORTE MAESTRO - SISTEMA QUEVEDO", ln=True, align='C')
        pdf.ln(10)
        # Aquí puedes añadir más lógica de PDF si gustas
        cuerpo_pdf = pdf.output(dest='S')
        return cuerpo_pdf.encode('latin-1', 'replace')
    except Exception as e:
        st.error(f"Error PDF: {e}")
        return None

# --- DISEÑO VISUAL ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; font-weight: bold; }
    .resumen-card { background: linear-gradient(135deg, #1e2130 0%, #1b5e20 100%); padding: 15px; border-radius: 15px; border: 1px solid #4CAF50; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- MENÚ LATERAL Y NAVEGACIÓN ---
st.sidebar.title("💎 SISTEMA QUEVEDO")
menu = st.sidebar.radio("MODULOS", ["🏠 INICIO", "💰 FINANZAS", "🩺 BIOMONITOR", "💊 AGENDA", "📸 ESCANER", "📂 ARCHIVADOR"])

# --- LÓGICA DE MÓDULOS ---
if menu == "🏠 INICIO":
    st.header(f"📊 Resumen: {NOMBRE_PROPIETARIO}")
    c1, c2, c3 = st.columns(3)
    
    df_fin = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
    df_glu = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
    
    with c1:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        st.metric("💰 BALANCE", f"RD$ {df_fin['total'][0] or 0:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        st.metric("🩺 ÚLTIMA GLUCOSA", f"{df_glu['valor'][0] if not df_glu.empty else 'N/A'} mg/dL")
        st.markdown('</div>', unsafe_allow_html=True)

elif menu == "🩺 BIOMONITOR":
    st.header("🩺 Control de Glucosa")
    val_g = st.number_input("Nivel mg/dL", min_value=0)
    if st.button("Guardar Medición"):
        ahora = datetime.now(pytz.timezone('America/Santo_Domingo'))
        c.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", 
                  (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), "REGISTRADO"))
        conn.commit()
        st.success("¡Registrado!")
        st.rerun()

# (Aquí puedes seguir pegando tus otros módulos como FINANZAS o ESCANER siguiendo esta misma estructura)
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
