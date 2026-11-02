# csv_parser.py
import re
import pandas as pd

def parser_rapport_genexpert(df):
    """
    Parse un DataFrame pandas issu de n'importe quel fichier GeneXpert (CSV/Excel).
    Extrait les valeurs de Ct (PROBE A-E, SPC) avec tolérance aux virgules décimales,
    récupère toutes les colonnes clés et applique la labélisation rigoureuse à 4 classes.
    """
    sondes_cibles = ['PROBE A', 'PROBE B', 'PROBE C', 'PROBE D', 'PROBE E', 'SPC']
    resultats_analyses = []

    if 'Test Result' in df.columns:
        df_clean = df[df['Test Result'].notna()].copy()
    else:
        df_clean = df.copy()

    for _, row in df_clean.iterrows():
        texte_ligne = " | ".join([str(row[c]) for c in df_clean.columns if pd.notna(row[c])]).upper()
        resultat_instr = str(row.get('Test Result', '')).upper()

        # 1. Extraction robuste des Ct (tolère les virgules comme Probe D,21,9)
        valeurs_patient = []
        for sonde in sondes_cibles:
            pattern = re.compile(rf"{sonde}\s*,\s*([0-9]+)\s*[\.,\,]\s*([0-9]+)", re.IGNORECASE)
            matches = pattern.findall(texte_ligne)
            val = 0.0
            if matches:
                ent, dec = matches[0]
                try:
                    v = float(f"{ent}.{dec}")
                    if 0 < v < 50:
                        val = v
                except ValueError:
                    pass
            valeurs_patient.append(val)

        sondes_ae = valeurs_patient[:5]
        spc_valeur = valeurs_patient[5]
        sondes_actives = [v for v in sondes_ae if v > 0.0]
        nb_actives = len(sondes_actives)

        # 2. Analyse textuelle et des règles cliniques
        is_error = any(err in resultat_instr for err in ['ERREUR', 'ERROR', 'INVALID', 'NON VALIDE', 'NO RESULT', 'PAS DE RÃ'])
        is_non_detecte = any(nd in resultat_instr for nd in ['NON DÉTECTÉ', 'NOT DETECTED', 'NON DÃ', 'NON DETECTE'])
        
        is_detecte = ('DÉTECTÉ' in resultat_instr or 'DETECTED' in resultat_instr or 'DÃ' in resultat_instr) and not is_non_detecte
        
        is_rif_non_detecte = 'RIF RESISTANCE NON' in resultat_instr or 'RIF RESISTANCE NOT' in resultat_instr or 'RESISTANCE NON DÃ' in resultat_instr
        is_rif_detecte = ('RESISTANCE DETECTED' in resultat_instr or 'RÉSISTANCE DÉTECTÉE' in resultat_instr or 'RÃ‰SISTANCE' in resultat_instr) and not is_rif_non_detecte

        # 3. Attribution stricte et robuste des 4 classes
        if is_error or (nb_actives == 0 and spc_valeur == 0.0 and not is_non_detecte):
            label_reel = 3  # Erreur / Invalide
        elif nb_actives >= 2 or is_detecte:
            # Si on a 2 sondes ou plus avec des Ct valides, c'est obligatoirement POSITIF
            if is_rif_detecte:
                label_reel = 2  # Positif Résistant
            else:
                label_reel = 1  # Positif Sensible (par défaut si pas de résistance avérée)
        else:
            label_reel = 0  # Vrai Négatif (pas de Ct et texte non détecté)

        # Récupération des informations demandées
        sample_id = str(row.get('Sample ID', row.get('Échantillon', 'Anonyme')))
        patient_id = str(row.get('Patient ID', 'N/A'))
        assay = str(row.get('Assay', 'N/A'))
        test_result = str(row.get('Test Result', 'N/A'))
        module_name = str(row.get('Module Name', 'N/A'))
        module_sn = str(row.get('Module S/N', 'N/A'))
        cartridge_sn = str(row.get('Cartridge S/N', 'N/A'))
        instrument_sn = str(row.get('Instrument S/N', 'N/A'))
        reagent_lot_id = str(row.get('Reagent Lot ID', 'N/A'))
        expiration_date = str(row.get('Expiration Date', 'N/A'))
        start_time = str(row.get('Start Time', 'N/A'))

        resultats_analyses.append({
            'sample_id': sample_id,
            'patient_id': patient_id,
            'assay': assay,
            'test_result': test_result,
            'module_name': module_name,
            'module_sn': module_sn,
            'cartridge_sn': cartridge_sn,
            'instrument_sn': instrument_sn,
            'reagent_lot_id': reagent_lot_id,
            'expiration_date': expiration_date,
            'start_time': start_time,
            'valeurs_ct': valeurs_patient,
            'label_reel': label_reel,
            'texte_brut': resultat_instr
        })

    return resultats_analyses