import streamlit as st
import zipfile
import os
import tempfile
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
from PIL import Image
from datetime import datetime
import re

st.set_page_config(page_title="Extracteur de Factures PDF", layout="wide")

st.title("📄 Extracteur Automatique de Factures PDF")
st.markdown("Chargez une archive ZIP contenant vos fichiers PDF de factures. Les données extraites seront affichées et exportables en Excel.")

uploaded_file = st.file_uploader("📁 Charger une archive ZIP contenant des fichiers PDF", type="zip")

def is_text_pdf(path):
    try:
        with open(path, "rb") as f:
            return b"/Font" in f.read(1024 * 1024)
    except:
        return False

@st.cache_data
def extract_text_from_pdf(pdf_path):
    images = convert_from_path(pdf_path, dpi=300)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img, lang="fra+eng") + "\n"
    return text

def extract_data(text, filename):
    data = {
        "Nom du fichier PDF": filename,
        "Numéro de facture": "",
        "Date de facture": "",
        "Date de livraison": "",
        "Quantité en L livrés": "",
        "Quantité en litres livrés": "",
        "Quantité en m³ livrés": "",
        "Quantité en kg livrés": "",
        "Quantité en T livrées": "",
        "Quantité en tonnes livrées": "",
        "Masse volumique exprimée en kg/m³": "",
        "Densité exprimée en kg/m³": "",
        "Masse volumique exprimée en kg/L": "",
        "Densité exprimée en kg/L": "",
        "Masse volumique exprimée en T/m³": "",
        "Densité exprimée en T/m³": "",
        "Prix en €TTC": "",
        "Prix en €HT": "",
        "Montant de TVA en €": "",
        "Nom du client": "",
        "Nom du fournisseur": ""
    }

    num_facture = re.search(r"(?i)facture\D*(\d{6,})", text)
    date_facture = re.search(r"(\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4})", text)
    ttc = re.search(r"(\d[\d\s.,]*?)\s*(€|EUR).*TTC", text, re.IGNORECASE)
    ht = re.search(r"(\d[\d\s.,]*?)\s*(€|EUR).*HT", text, re.IGNORECASE)
    tva = re.search(r"(\d[\d\s.,]*?)\s*(€|EUR).*TVA", text, re.IGNORECASE)
    client = re.search(r"(?i)(client|livré à|destinataire)\s*[:\-]?\s*([A-ZÉÈÀ].{2,40})", text)
    fournisseur = re.search(r"(?i)(ANTARGAZ|TOTAL|BUTAGAZ|fournisseur)\s*[:\-]?", text)

    if num_facture: data["Numéro de facture"] = num_facture.group(1)
    if date_facture: data["Date de facture"] = date_facture.group(1)
    if ttc: data["Prix en €TTC"] = ttc.group(1).replace(" ", "")
    if ht: data["Prix en €HT"] = ht.group(1).replace(" ", "")
    if tva: data["Montant de TVA en €"] = tva.group(1).replace(" ", "")
    if client: data["Nom du client"] = client.group(2).strip()
    if fournisseur: data["Nom du fournisseur"] = fournisseur.group(1).strip()

    return data

if uploaded_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
            zip_ref.extractall(tmpdir)

        results = []
        pdf_files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.lower().endswith(".pdf")]
        progress = st.progress(0)

        for i, pdf in enumerate(pdf_files):
            filename = os.path.basename(pdf)
            st.write(f"🔍 Traitement : `{filename}`")

            if is_text_pdf(pdf):
                st.write("→ PDF texte détecté (OCR non requis).")
                text = extract_text_from_pdf(pdf)
            else:
                st.write("→ PDF image détecté. Application de l’OCR...")
                text = extract_text_from_pdf(pdf)

            data = extract_data(text, filename)
            results.append(data)
            progress.progress((i + 1) / len(pdf_files))

        df = pd.DataFrame(results)
        st.dataframe(df)

        xlsx_name = f"factures_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(xlsx_name, index=False)

        with open(xlsx_name, "rb") as f:
            st.download_button("📥 Télécharger les résultats Excel", f, file_name=xlsx_name)
