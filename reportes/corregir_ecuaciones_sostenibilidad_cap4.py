from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile


DOCX = Path("reportes/reporte_tt2_portocarrero_r_habid/DocumentoTecnicoTT_Habid_V1_copia_codex.docx")


REPLACEMENTS = {
    "=2.5\u2008min=0.0417": "=3 min=0.05",
    "=140\u2008W\u22c50.0417=5.83\u2008Wh": "=140 W\u22c50.05=7 Wh",
    "5.83Wh=0.00583kWh": "7Wh=0.007kWh",
    "=0.00583\u22c50.434=0.00253kgC": "=0.007\u22c50.434=0.00304kgC",
    "=0.00253kgC": "=0.00304kgC",
}


def main():
    with ZipFile(DOCX, "r") as zin, NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp_path = Path(tmp.name)
        with ZipFile(tmp, "w", ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/document.xml":
                    text = data.decode("utf-8")
                    for old, new in REPLACEMENTS.items():
                        text = text.replace(old, new)
                    data = text.encode("utf-8")
                zout.writestr(item, data)

    tmp_path.replace(DOCX)
    print("Ecuaciones de sostenibilidad actualizadas.")


if __name__ == "__main__":
    main()
