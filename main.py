import os
import sys
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename

# Configuración de rutas multiplataforma
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Inicialización de la aplicación Flask
app = Flask(__name__,
            static_folder=os.path.join(BASE_DIR, 'static'),
            template_folder=os.path.join(BASE_DIR, 'templates'))
app.secret_key = 'tu_clave_secreta_aqui'  # Cambia esto en producción

# Configuración de la aplicación
ALLOWED_EXTENSIONS = {'xlsx'}
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    """Verifica si la extensión del archivo está permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generar_xml_uif(archivo_excel):
    """
    Función principal que genera el XML para UIF a partir de un archivo Excel
    Retorna: (ruta_del_xml_generado, mensaje_de_error)
    """
    hojas_requeridas = ['encabezado', 'persona_moral', 'operaciones']

    try:
        # Validación 1: Verificar que el archivo existe
        if not os.path.isfile(archivo_excel):
            raise FileNotFoundError(f"El archivo '{archivo_excel}' no existe")

        # Validación 2: Verificar que tiene las hojas requeridas
        xls = pd.ExcelFile(archivo_excel)
        for hoja in hojas_requeridas:
            if hoja not in xls.sheet_names:
                raise ValueError(f"Falta la hoja requerida: '{hoja}'")

        # Cargar datos de las hojas
        encabezado_df = pd.read_excel(xls, 'encabezado')
        persona_df = pd.read_excel(xls, 'persona_moral')

        # Crear nombre del archivo XML de salida
        denominacion = persona_df.iloc[0]['denominacion_razon'].replace(' ', '_').replace('.', '')[:30]
        mes_reportado = str(encabezado_df.iloc[0]['mes_reportado'])
        xml_salida = os.path.join(app.config['UPLOAD_FOLDER'], f"informe1.0_{denominacion}_{mes_reportado}.xml")

        # Validación 3: Verificar columnas requeridas en hoja 'encabezado'
        columnas_requeridas = ['mes_reportado', 'clave_sujeto_obligado', 'clave_actividad',
                               'referencia_aviso', 'prioridad', 'tipo_alerta']
        for col in columnas_requeridas:
            if col not in encabezado_df.columns:
                raise KeyError(f"Columna faltante en 'encabezado': {col}")

        # Configurar namespaces XML según requerimientos UIF
        ET.register_namespace('', "http://www.uif.shcp.gob.mx/recepcion/tcv")
        ET.register_namespace('xsi', "http://www.w3.org/2001/XMLSchema-instance")

        # Crear estructura base del XML
        root = ET.Element("{http://www.uif.shcp.gob.mx/recepcion/tcv}archivo")
        root.set("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation",
                 "http://www.uif.shcp.gob.mx/recepcion/tcv tcv.xsd")

        informe = ET.SubElement(root, "informe")

        # Sección 1: Mes reportado
        mes_reportado_xml = str(encabezado_df.iloc[0]['mes_reportado'])
        ET.SubElement(informe, "mes_reportado").text = mes_reportado_xml

        # Sección 2: Sujeto obligado
        sujeto = ET.SubElement(informe, "sujeto_obligado")
        ET.SubElement(sujeto, "clave_sujeto_obligado").text = str(encabezado_df.iloc[0]['clave_sujeto_obligado'])
        ET.SubElement(sujeto, "clave_actividad").text = str(encabezado_df.iloc[0]['clave_actividad'])

        # Sección 3: Aviso
        aviso = ET.SubElement(informe, "aviso")
        ET.SubElement(aviso, "referencia_aviso").text = str(encabezado_df.iloc[0]['referencia_aviso'])
        ET.SubElement(aviso, "prioridad").text = str(encabezado_df.iloc[0]['prioridad'])

        # Sección 4: Alerta
        alerta = ET.SubElement(aviso, "alerta")
        ET.SubElement(alerta, "tipo_alerta").text = str(encabezado_df.iloc[0]['tipo_alerta'])

        # Sección 5: Persona (moral) del aviso
        persona_aviso = ET.SubElement(aviso, "persona_aviso")
        tipo_persona = ET.SubElement(persona_aviso, "tipo_persona")
        persona_moral = ET.SubElement(tipo_persona, "persona_moral")

        # Datos básicos de la persona moral
        datos_persona = {
            'denominacion_razon': persona_df.iloc[0]['denominacion_razon'],
            'fecha_constitucion': persona_df.iloc[0]['fecha_constitucion'],
            'rfc': persona_df.iloc[0]['rfc'],
            'pais_nacionalidad': persona_df.iloc[0]['pais_nacionalidad'],
            'giro_mercantil': persona_df.iloc[0]['giro_mercantil']
        }

        for tag, valor in datos_persona.items():
            ET.SubElement(persona_moral, tag).text = str(valor)

        # Sección 6: Representante legal/apoderado
        representante = ET.SubElement(persona_moral, "representante_apoderado")
        datos_representante = {
            'nombre': persona_df.iloc[0]['nombre_representante'],
            'apellido_paterno': persona_df.iloc[0]['apellido_paterno_representante'],
            'apellido_materno': persona_df.iloc[0]['apellido_materno_representante'],
            'fecha_nacimiento': persona_df.iloc[0]['fecha_nacimiento_representante'],
            'rfc': persona_df.iloc[0]['rfc_representante'],
            'curp': persona_df.iloc[0]['curp_representante']
        }

        for tag, valor in datos_representante.items():
            ET.SubElement(representante, tag).text = str(valor)

        # Sección 7: Domicilio
        tipo_domicilio = ET.SubElement(persona_aviso, "tipo_domicilio")
        nacional = ET.SubElement(tipo_domicilio, "nacional")

        datos_domicilio = {
            'colonia': persona_df.iloc[0]['colonia'],
            'calle': persona_df.iloc[0]['calle'],
            'numero_exterior': persona_df.iloc[0]['numero_exterior'],
            'codigo_postal': str(persona_df.iloc[0]['codigo_postal']).zfill(5)
        }

        for tag, valor in datos_domicilio.items():
            ET.SubElement(nacional, tag).text = str(valor)

        # Sección 8: Contacto telefónico
        telefono = ET.SubElement(persona_aviso, "telefono")
        ET.SubElement(telefono, "clave_pais").text = str(persona_df.iloc[0]['clave_pais'])
        ET.SubElement(telefono, "numero_telefono").text = str(persona_df.iloc[0]['numero_telefono'])
        ET.SubElement(telefono, "correo_electronico").text = persona_df.iloc[0]['correo_electronico']

        # Sección 9: Operaciones (hoja 'operaciones')
        operaciones_df = pd.read_excel(xls, 'operaciones')
        detalle_operaciones = ET.SubElement(aviso, "detalle_operaciones")

        for _, operacion in operaciones_df.iterrows():
            datos_op = ET.SubElement(detalle_operaciones, "datos_operacion")

            # Fecha y tipo de operación
            fecha_op = str(operacion['fecha_operacion']).split('.')[0]
            ET.SubElement(datos_op, "fecha_operacion").text = fecha_op

            tipo_operacion = str(operacion['tipo_operacion']).split('.')[0]
            ET.SubElement(datos_op, "tipo_operacion").text = tipo_operacion

            # Tipo de bien (efectivo/instrumentos)
            tipo_bien = ET.SubElement(datos_op, "tipo_bien")
            datos_efectivo = ET.SubElement(tipo_bien, "datos_efectivo_instrumentos")
            ET.SubElement(datos_efectivo, "instrumento_monetario").text = \
            str(operacion['instrumento_monetario']).split('.')[0]
            ET.SubElement(datos_efectivo, "moneda").text = str(operacion['moneda']).split('.')[0]

            try:
                ET.SubElement(datos_efectivo, "monto_operacion").text = f"{float(operacion['monto_operacion']):.2f}"
            except (ValueError, TypeError):
                ET.SubElement(datos_efectivo, "monto_operacion").text = "0.00"

            # Recepción
            recepcion = ET.SubElement(datos_op, "recepcion")
            ET.SubElement(recepcion, "tipo_servicio").text = str(operacion['tipo_servicio']).split('.')[0]
            fecha_recep = str(operacion['fecha_recepcion']).split('.')[0]
            ET.SubElement(recepcion, "fecha_recepcion").text = fecha_recep
            cp_recep = str(operacion['codigo_postal_recepcion']).split('.')[0]
            ET.SubElement(recepcion, "codigo_postal").text = cp_recep

            # Custodia (solo para operación 1003)
            if tipo_operacion == "1003":
                custodia = ET.SubElement(datos_op, "custodia")

                fecha_ini = str(operacion.get('fecha_inicio_custodia', '')).split('.')[0]
                fecha_fin = str(operacion.get('fecha_fin_custodia', '')).split('.')[0]

                ET.SubElement(custodia, "fecha_inicio").text = fecha_ini if fecha_ini else ''
                ET.SubElement(custodia, "fecha_fin").text = fecha_fin if fecha_fin else ''

                tipo_custodia_node = ET.SubElement(custodia, "tipo_custodia")
                datos_sucursal = ET.SubElement(tipo_custodia_node, "datos_sucursal")
                cp_sucursal = str(operacion.get('codigo_postal_sucursal', '')).split('.')[0]
                ET.SubElement(datos_sucursal, "codigo_postal").text = cp_sucursal if cp_sucursal else ''

            # Entrega
            entrega = ET.SubElement(datos_op, "entrega")
            fecha_ent = str(operacion['fecha_entrega']).split('.')[0]
            ET.SubElement(entrega, "fecha_entrega").text = fecha_ent
            tipo_entrega = ET.SubElement(entrega, "tipo_entrega")
            nacional_entrega = ET.SubElement(tipo_entrega, "nacional")
            cp_entrega = str(operacion['codigo_postal_entrega']).split('.')[0]
            ET.SubElement(nacional_entrega, "codigo_postal").text = cp_entrega

            # Destinatario
            destinatario = ET.SubElement(datos_op, "destinatario")
            dest_persona = str(operacion['destinatario_persona_aviso']).upper()
            ET.SubElement(destinatario, "destinatario_persona_aviso").text = dest_persona

        # Generar XML formateado
        xml_str = ET.tostring(root, encoding='utf-8')
        xml_formateado = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding="utf-8")

        with open(xml_salida, "wb") as f:
            f.write(xml_formateado)

        return xml_salida, None

    except Exception as e:
        return None, str(e)


@app.route('/', methods=['GET', 'POST'])
def index():
    """Manejador de la página principal (subida de archivos)"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            xml_path, error = generar_xml_uif(filepath)

            if error:
                flash(f'Error al procesar el archivo: {error}', 'error')
                return redirect(request.url)
            else:
                flash('Archivo XML generado con éxito!', 'success')
                return render_template('result.html', xml_file=os.path.basename(xml_path))
        else:
            flash('Solo se permiten archivos Excel (.xlsx)', 'error')
            return redirect(request.url)

    return render_template('upload.html')


@app.route('/download/<filename>')
def download(filename):
    """Permite descargar el XML generado"""
    return send_file(
        os.path.join(app.config['UPLOAD_FOLDER'], filename),
        as_attachment=True,
        download_name=filename
    )


if __name__ == '__main__':
    # Crear carpetas necesarias si no existen
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'static'), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'templates'), exist_ok=True)

    # Modo de operación: CLI o Web
    if len(sys.argv) > 1 and sys.argv[1] == '--cli':
        # Modo consola (Command Line Interface)
        if len(sys.argv) > 2:
            input_file = sys.argv[2]
        else:
            input_file = "datos.xlsx"

        print(f"Procesando archivo: {input_file}")
        xml_path, error = generar_xml_uif(input_file)

        if error:
            print(f"\nError: {error}")
            sys.exit(1)
        else:
            print(f"\nXML generado exitosamente: {xml_path}")
            sys.exit(0)
    else:
        # Modo web (Flask)
        app.run(debug=False, host='0.0.0.0', port=5000)