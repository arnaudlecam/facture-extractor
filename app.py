
import streamlit as st
import zipfile
import os
import tempfile
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import re
import pandas as pd

st.set_page_config(page_title="Extraction de factures PDF Image", layout="wide")
st.title("🧾 Application d'extraction de données de factures (PDF image)")

uploaded_zip = st.file_uploader("Déposez ici un fichier ZIP contenant plusieurs fichiers PDF image", type=["zip"])

if uploaded_zip:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "uploaded.zip")
        with open(zip_path, "wb") as f:
            f.write(uploaded_zip.getbuffer())
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)

        pdf_files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.lower().endswith(".pdf")]
        st.info(f"{len(pdf_files)} fichiers PDF trouvés.")

        data_rows = []

        for pdf_path in pdf_files:
            images = convert_from_path(pdf_path, dpi=300, grayscale=True)
            ocr_text = ""
            for img in images:
                ocr_text += pytesseract.image_to_string(img, config="--oem 3 --psm 6") + "\n"

            def extract(text):
                data = {}
                data["Nom du fichier PDF"] = os.path.basename(pdf_path)
                match = re.search(r'facture\s*(n°|numéro)?\s*[:\-]?\s*([A-Z0-9\-\/]+)', text, re.IGNORECASE)
                data["Numéro de facture"] = match.group(2) if match else ""
                match = re.search(r'facture\s*(n°|numéro)?\s*[A-Z0-9\-\/]+\s*du\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
                data["Date de facture"] = match.group(2) if match else ""
                ht = re.search(r'Montant Hors Taxe\s*([\d\s,\.]+)\s*€', text)
                tva = re.search(r'Montant TVA\s*([\d\s,\.]+)\s*€', text)
                if ht and tva:
                    try:
                        ht_val = float(ht.group(1).replace(',', '.').replace(' ', ''))
                        tva_val = float(tva.group(1).replace(',', '.').replace(' ', ''))
                        data["Prix en €HT"] = ht_val
                        data["Montant de TVA en €"] = tva_val
                        data["Prix en €TTC"] = ht_val + tva_val
                    except:
                        data["Prix en €HT"] = data["Montant de TVA en €"] = data["Prix en €TTC"] = ""
                else:
                    data["Prix en €HT"] = data["Montant de TVA en €"] = data["Prix en €TTC"] = ""
                match = re.search(r'MAIRIE\s+DE\s+[A-ZÉÈA-Z\- ]+', text)
                data["Nom du client"] = match.group(0).strip() if match else ""
                match = re.search(r'antargaz', text, re.IGNORECASE)
                data["Nom du fournisseur"] = "ANTARGAZ" if match else ""
                quant_fields = ["Quantité en L livrés", "Quantité en litres livrés", "Quantité en m³ livrés",
                                "Quantité en kg livrés", "Quantité en T livrées", "Quantité en tonnes livrées",
                                "Masse volumique exprimée en kg/m³", "Densité exprimée en kg/m³",
                                "Masse volumique exprimée en kg/L", "Densité exprimée en kg/L",
                                "Masse volumique exprimée en T/m³", "Densité exprimée en T/m³",
                                "Date de livraison"]
                for f in quant_fields:
                    data[f] = ""
                return data

            row = extract(ocr_text)
            data_rows.append(row)

        df = pd.DataFrame(data_rows)
        st.dataframe(df)
        st.download_button("Télécharger les résultats (.xlsx)", df.to_excel(index=False), file_name="resultats_factures.xlsx")
