from fpdf import FPDF
import datetime
import os

class EPMReport(FPDF):
    def header(self):
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Move to the right
        self.cell(80)
        # Title
        self.cell(30, 10, 'Reporte de Analisis EPM - TT 2026', 0, 0, 'C')
        # Line break
        self.ln(20)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Pagina ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

def generate_pdf_report(user_name, role, kpis, filename="reporte_epm.pdf"):
    """
    Generates a PDF report with the session results.
    kpis: dictionary with values like 'tiempo_total', 'tiempo_abiertos', etc.
    """
    pdf = EPMReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)

    # Metadata
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Informacion de la Sesion', 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 10, f'Investigador: {user_name} ({role})', 0, 1)
    pdf.cell(0, 10, f'Fecha: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
    pdf.ln(10)

    # KPIs
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Indicadores Clave (KPIs)', 0, 1)
    pdf.set_font('Arial', '', 11)
    
    pdf.cell(0, 10, f"- Tiempo Total: {kpis.get('tiempo_total', 0):.1f} s", 0, 1)
    pdf.cell(0, 10, f"- Tiempo en Brazos Abiertos: {kpis.get('tiempo_abiertos', 0):.1f} s ({kpis.get('pref_abiertos', 0):.1f}%)", 0, 1)
    pdf.cell(0, 10, f"- Tiempo en Brazos Cerrados: {kpis.get('tiempo_cerrados', 0):.1f} s", 0, 1)
    pdf.cell(0, 10, f"- Numero de Entradas (Actividad): {kpis.get('entradas', 0)}", 0, 1)
    
    pdf.ln(10)
    
    # Interpretation
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Resumen de Comportamiento', 0, 1)
    pdf.set_font('Arial', '', 11)
    
    pref = kpis.get('pref_abiertos', 0)
    text = ""
    if pref < 15:
        text = "El especimen muestra niveles elevados de ansiedad, permaneciendo principalmente en los brazos cerrados."
    elif pref < 30:
        text = "El especimen muestra un comportamiento de exploracion moderado."
    else:
        text = "El especimen muestra una alta exploracion de brazos abiertos, lo cual puede indicar un efecto ansiolitico."
        
    pdf.multi_cell(0, 10, text)

    # Save
    os.makedirs("reports", exist_ok=True)
    full_path = os.path.join("reports", filename)
    pdf.output(full_path)
    return full_path
