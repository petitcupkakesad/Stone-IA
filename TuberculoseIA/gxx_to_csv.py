import os
import re
import pandas as pd
import numpy as np

def decoder_fichier_gxx(chemin_gxx):
    with open(chemin_gxx, "rb") as f:
        contenu = f.read()

    nom_fichier = os.path.basename(chemin_gxx)
    
    donnees_extraites = {
        "Fichier": nom_fichier,
        "Sample_ID": os.path.splitext(nom_fichier)[0],  # Fallback sur le nom du fichier
        "MTB_Result": "NON_DETECTE",
        "RIF_Resist": "INDETERMINE",
        "Ct_Probe_A": np.nan,
        "Ct_Probe_B": np.nan,
        "Ct_Probe_C": np.nan,
        "Ct_Probe_D": np.nan,
        "Ct_Probe_E": np.nan,
        "Ct_SPC": np.nan,
    }

    # 1. Extraction du texte (ASCII + UTF-16)
    textes_ascii = [t.decode('utf-8', errors='ignore') for t in re.findall(b'[\x20-\x7E]{3,}', contenu)]
    textes_utf16 = [t.decode('utf-16le', errors='ignore') for t in re.findall(b'(?:[\x20-\x7E]\x00){3,}', contenu)]
    texte_complet = " ".join(textes_ascii + textes_utf16)

    # Recherche du Sample ID / Patient ID dans le texte
    id_match = re.search(r'(?:Sample|Echantillon|Patient|ID)[\s:=_-]+([A-Za-z0-9_-]+)', texte_complet, re.IGNORECASE)
    if id_match and len(id_match.group(1)) > 2:
        donnees_extraites["Sample_ID"] = id_match.group(1)

    # Détection des résultats
    texte_upper = texte_complet.upper()
    if "MTB DETECTED" in texte_upper or "DETECTED" in texte_upper or "POSITIF" in texte_upper:
        donnees_extraites["MTB_Result"] = "DETECTE"
    
    if "RIF RESISTANCE DETECTED" in texte_upper:
        donnees_extraites["RIF_Resist"] = "RESISTANT"
    elif "RIF RESISTANCE NOT DETECTED" in texte_upper or "NOT DETECTED" in texte_upper:
        donnees_extraites["RIF_Resist"] = "SENSIBLE"

    # 2. Extraction des valeurs Ct (Scan des flottants IEEE 754 32-bit)
    floats_trouves = []
    for i in range(0, len(contenu) - 4, 2):  # Pas de 2 pour ne pas rater les offsets impairs
        val = np.frombuffer(contenu[i:i+4], dtype=np.float32)[0]
        if 8.0 <= val <= 45.0 and not np.isnan(val):
            val_arrondie = round(float(val), 2)
            floats_trouves.append(val_arrondie)

    # Filtrage des doublons
    cts_filtres = []
    for f_val in floats_trouves:
        if not cts_filtres or abs(cts_filtres[-1] - f_val) > 0.05:
            cts_filtres.append(f_val)

    # Attribution aux 6 sondes
    noms_sondes = ["Ct_Probe_A", "Ct_Probe_B", "Ct_Probe_C", "Ct_Probe_D", "Ct_Probe_E", "Ct_SPC"]
    for idx, ct in enumerate(cts_filtres[:6]):
        donnees_extraites[noms_sondes[idx]] = ct

    return donnees_extraites

def convertir_dossier_gxx_en_csv(dossier_entree, fichier_sortie_csv):
    resultats = []
    fichiers = [f for f in os.listdir(dossier_entree) if f.endswith('.gxx') or f.endswith('.bin')]
    
    print(f"[+] Traitement de {len(fichiers)} fichiers...")
    for f in fichiers:
        chemin = os.path.join(dossier_entree, f)
        res = decoder_fichier_gxx(chemin)
        resultats.append(res)

    df = pd.DataFrame(resultats)
    df.to_csv(fichier_sortie_csv, index=False, encoding='utf-8')
    print(f"[✔] Conversion terminée ! Fichier généré : {fichier_sortie_csv}")
    return df

if __name__ == "__main__":
    df = convertir_dossier_gxx_en_csv("./", "donnees_tuberculose_converties.csv")
    print("\n--- Aperçu des données extraites ---")
    print(df.to_string())