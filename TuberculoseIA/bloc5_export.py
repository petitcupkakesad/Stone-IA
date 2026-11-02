# bloc5_export.py
import pandas as pd
import openpyxl
from openpyxl.styles import PatternFill, Font
from typing import List, Dict, Any

def generer_excel_final(
    donnees_principales: List[Dict[str, Any]],
    donnees_mutations: List[Dict[str, Any]],
    fichier_sortie: str = "GeneXpert_final extraction from .csv-log.xlsx"
):
    """Génère le fichier Excel final complet avec mises en forme et déduplication."""
    df_main = pd.DataFrame(donnees_principales)
    df_mut = pd.DataFrame(donnees_mutations)

    # --- SÉCURISATION ABSOLUE DES COLONNES ---
    if df_main.empty:
        df_main = pd.DataFrame([{
            "Patient ID": "PAT-001",
            "Sample ID": "ECH-001",
            "Test_Xpert": "N/A",
            "Test Result": "N/A",
            "Result_VIH": "null",
            "Result_Covid19": "null"
        }])

    if "Patient ID" not in df_main.columns:
        if "Sample ID" in df_main.columns:
            df_main["Patient ID"] = df_main["Sample ID"]
        elif "Sample_ID" in df_main.columns:
            df_main["Patient ID"] = df_main["Sample_ID"]
        else:
            df_main["Patient ID"] = [f"PAT-{i+1:03d}" for i in range(len(df_main))]

    if "Sample ID" not in df_main.columns:
        if "Sample_ID" in df_main.columns:
            df_main["Sample ID"] = df_main["Sample_ID"]
        else:
            df_main["Sample ID"] = df_main["Patient ID"]

    # 1. Traitement de la Déduplication
    counts = df_main["Patient ID"].value_counts()
    dup_ids = counts[counts > 1].index.tolist()

    lignes_dedup = []
    for pid in dup_ids:
        sub = df_main[df_main["Patient ID"] == pid]
        freq = len(sub)
        first_row = sub.iloc[0]
        lignes_dedup.append({
            "nom_prénom": first_row.get("Patient ID", "null"),
            "Sample_ID": first_row.get("Sample ID", "null"),
            "Fréquence": freq,
            "Infection-TB": first_row.get("Test Result", "null"),
            "Diagnostic-VIH": first_row.get("Result_VIH", "null"),
            "Suivi-VIH": first_row.get("VIH_Qual_result", "null"),
            "Infection-Covid19": first_row.get("Result_Covid19", "null")
        })

    df_dedup = pd.DataFrame(lignes_dedup)

    # 2. Écriture Excel
    with pd.ExcelWriter(fichier_sortie, engine='openpyxl') as writer:
        df_main.to_excel(writer, sheet_name="Extraction_Principale", index=False)
        df_dedup.to_excel(writer, sheet_name="Dé_duplication", index=False)
        if not df_mut.empty:
            df_mut.to_excel(writer, sheet_name="Identification_mutations", index=False)

    # 3. Application des styles OpenPyXL
    wb = openpyxl.load_workbook(fichier_sortie)

    fill_orange = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
    fill_yellow_0 = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    fill_pale_yellow = PatternFill(start_color="FFFACD", end_color="FFFACD", fill_type="solid")
    font_italic_gray = Font(italic=True, color="D9D9D9")

    ws_main = wb["Extraction_Principale"]
    header_main = [cell.value for cell in ws_main[1]]

    def col_idx(name: str) -> int:
        return header_main.index(name) + 1 if name in header_main else -1

    idx_pid = col_idx("Patient ID")
    idx_xpert = col_idx("Test_Xpert")
    idx_res_tb = col_idx("Test Result")
    idx_res_vih = col_idx("Result_VIH")
    idx_res_covid = col_idx("Result_Covid19")

    for row in ws_main.iter_rows(min_row=2, max_row=ws_main.max_row):
        pid_val = str(row[idx_pid - 1].value or "").strip() if idx_pid > 0 else ""
        xpert_val = str(row[idx_xpert - 1].value or "").strip() if idx_xpert > 0 else ""
        res_tb_val = str(row[idx_res_tb - 1].value or "").strip() if idx_res_tb > 0 else ""
        res_vih_val = str(row[idx_res_vih - 1].value or "").strip() if idx_res_vih > 0 else ""
        res_covid_val = str(row[idx_res_covid - 1].value or "").strip() if idx_res_covid > 0 else ""

        incoherence = False
        if not pid_val or not xpert_val:
            incoherence = True
        elif "MTB-RIF" in xpert_val and not res_tb_val:
            incoherence = True
        elif "Viral Load" in xpert_val and not res_vih_val:
            incoherence = True
        elif "SARS-CoV-2" in xpert_val and not res_covid_val:
            incoherence = True

        if incoherence:
            for cell in row:
                cell.fill = fill_orange

        for cell in row:
            val_str = str(cell.value)
            if val_str == "null":
                cell.font = font_italic_gray
            elif val_str == "0.0":
                cell.fill = fill_yellow_0
            elif "PRESUMPTIVE" in val_str.upper():
                cell.fill = fill_pale_yellow

    wb.save(fichier_sortie)
    print(f"✅ Exportation finale réussie : '{fichier_sortie}'")


if __name__ == "__main__":
    p_demo = [{
        "Patient ID": "PAT_001", "Sample ID": "S_001", "Test_Xpert": "Xpert MTB-RIF Ultra",
        "Test Result": "MTB DETECTED", "Result_VIH": "null", "Result_Covid19": "null"
    }]
    generer_excel_final(p_demo, [], "GeneXpert_Test.xlsx")