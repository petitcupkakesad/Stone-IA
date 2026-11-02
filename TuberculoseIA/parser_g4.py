# parser_g4.py
import pandas as pd
import numpy as np
import os

def nettoyer_et_fusionner_g4(chemin_csv_input: str) -> pd.DataFrame:
    """
    Lit le fichier brut G4, nettoie les en-têtes, regroupe les lignes par Sample ID 
    et extrait strictement la PREMIÈRE occurrence de chaque sonde (amplification initiale).
    """
    df_raw = None
    for enc in ["utf-8-sig", "latin1", "cp1252", "utf-16"]:
        try:
            df_raw = pd.read_csv(chemin_csv_input, encoding=enc)
            if not df_raw.empty and len(df_raw.columns) > 1:
                break
        except Exception:
            continue

    if df_raw is None or df_raw.empty:
        df_raw = pd.read_csv(chemin_csv_input, encoding="latin1")

    # Nettoyage des espaces superflus dans les noms de colonnes
    df_raw.columns = [str(c).strip() for c in df_raw.columns]

    # Recherche dynamique de la colonne Sample ID
    col_sample_id = next((c for c in df_raw.columns if 'SAMPLE ID' in c.upper()), None)
    if not col_sample_id:
        raise KeyError(f"⚠️ Colonne 'Sample ID' introuvable. Colonnes dispo : {df_raw.columns.tolist()}")

    features_list = ['Probe A', 'Probe B', 'Probe C', 'Probe D', 'Probe E', 'SPC']
    lignes_unifiees = []

    # Fusion par Sample ID pour unifier l'en-tête et la ligne de sondes
    for sample_id, group in df_raw.groupby(col_sample_id):
        if pd.isna(sample_id) or str(sample_id).strip() == "":
            continue
        sample_id_str = str(sample_id).strip()

        row_unifiee = {}
        for col in df_raw.columns:
            valid_vals = group[col].dropna().tolist()
            if valid_vals:
                if 'PROBES' in col.upper() or 'PROBE' in col.upper():
                    # On privilégie la ligne contenant le bloc d'essais
                    probe_vals = [v for v in valid_vals if 'EFFECTUÉ' in str(v).upper() or 'PROBE A' in str(v).upper()]
                    row_unifiee[col] = probe_vals[0] if probe_vals else valid_vals[0]
                else:
                    row_unifiee[col] = valid_vals[0]
            else:
                row_unifiee[col] = None

        # Récupération des métadonnées clés
        patient_col = next((c for c in df_raw.columns if 'PATIENT' in c.upper()), None)
        test_res_col = next((c for c in df_raw.columns if 'TEST RESULT' in c.upper() or 'RESULT' in c.upper()), None)
        module_col = next((c for c in df_raw.columns if 'MODULE' in c.upper()), None)
        start_time_col = next((c for c in df_raw.columns if 'START TIME' in c.upper()), None)
        probes_col = next((c for c in df_raw.columns if 'PROBES' in c.upper() or 'RESULTS' in c.upper()), None)

        patient_id = str(row_unifiee.get(patient_col, "Inconnu")) if patient_col else "Inconnu"
        test_result = str(row_unifiee.get(test_res_col, "Inconnu")) if test_res_col else "Inconnu"
        module_name = str(row_unifiee.get(module_col, "Inconnu")) if module_col else "Inconnu"
        start_time = str(row_unifiee.get(start_time_col, "Inconnu")) if start_time_col else "Inconnu"
        texte_probes = str(row_unifiee.get(probes_col, "")) if probes_col else ""

        # Extraction chirurgicale STRICTE de la PREMIÈRE occurrence de chaque sonde
        ct_dict_ligne = {}
        valeurs_patient = []

        for idx_f, sonde in enumerate(features_list):
            val = 0.0
            statut_probe = "Inconnu"
            sonde_upper = sonde.upper()
            
            # On cherche UNIQUEMENT la première position de la sonde dans la chaîne
            pos = texte_probes.upper().find(sonde_upper)
            if pos != -1:
                # On extrait un segment court juste après le nom de la sonde (ex: "Probe A,0,0,3")
                segment = texte_probes[pos:pos + 35]
                parts = [p.strip() for p in segment.split(',')]
                try:
                    # Gestion du format décimal (ex: 28,7 -> 28.7) ou entier simple
                    if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
                        val = float(f"{parts[1]}.{parts[2]}")
                    elif len(parts) >= 2 and parts[1].replace('.','',1).isdigit():
                        val = float(parts[1])
                except ValueError:
                    val = 0.0

                # Recherche du statut (NÉG, POS, RÉUSSITE, etc.) dans les parts suivantes
                for p in parts[3:]:
                    if p in ["POS", "NÉG", "RÉUSSITE", "SO", "ERREUR", "FAIL"]:
                        statut_probe = p
                        break

            valeurs_patient.append(float(val))
            lettre = chr(65+idx_f) if idx_f < 5 else "SPC"
            # Si la valeur est 0.0 (négatif), on met NaN ou 0.0 selon la préférence (ici 0.0 pour l'IA)
            ct_dict_ligne[f"Ct_Probe_{lettre}"] = val if val > 0 else 0.0
            ct_dict_ligne[f"Statut_{lettre}"] = statut_probe

        lignes_unifiees.append({
            "Fichier": os.path.basename(chemin_csv_input),
            "Sample_ID": sample_id_str,
            "Patient_ID": patient_id,
            "Module": module_name,
            "Date_Start": start_time,
            "Resultat_Instrument": test_result,
            **ct_dict_ligne,
            "_vecteur_brut": valeurs_patient
        })

    return pd.DataFrame(lignes_unifiees)