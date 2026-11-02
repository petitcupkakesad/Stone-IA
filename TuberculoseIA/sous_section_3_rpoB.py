# sous_section_3_rpoB.py
import re
from typing import Dict, Any, List

def traiter_sous_section_3_rpob(lignes_raw: List[str], ligne_patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Section 1 - Sous-section 3 : Extraction des sondes rpoB (1 à 4) et des pics de fusion (Melt Peaks).
    
    Règles appliquées :
    1. Extraction dans "Analyte Result" de rpoB1 à rpoB4.
    2. Extraction dans "Melt Peaks" des pics de fusion (rpoB_melt, rpoB_Mut_melt, etc.).
    3. Remplacement des valeurs manquantes ou sections vides par "null" sans générer d'erreur.
    4. Substitution des virgules (,) par " | " uniquement pour ces colonnes rpoB.
    5. Nettoyage des guillemets (") autour des valeurs.
    """
    cols_rpob = {
        "rpoB1_": "rpoB1",
        "rpoB2_": "rpoB2",
        "rpoB3_": "rpoB3",
        "rpoB4_": "rpoB4",
        "rpoB1_melt": "rpoB1 melt",
        "rpoB2_melt": "rpoB2 melt",
        "rpoB3_melt": "rpoB3 melt",
        "rpoB4_melt": "rpoB4 melt",
        "rpoB1_Mut_melt": "rpoB1 Mut melt",
        "rpoB2_Mut_melt": "rpoB2 Mut melt",
        "rpoB3_Mut_melt": "rpoB3 Mut melt",
        "rpoB4_Mut_meltA": "rpoB4 Mut melt A",
        "rpoB4_Mut_meltB": "rpoB4 Mut melt B"
    }

    # Initialisation à "null" par défaut pour éviter de générer des erreurs (Règle 3.b & 3.c)
    for col in cols_rpob.keys():
        if not ligne_patient.get(col):
            ligne_patient[col] = "null"

    headers_analytes = ("analyte name,ct,endpt,analyte result", "nom de l'analyte,ct,valeur finale,résultat analyte")
    headers_melts = ("analyte name,melt peak temperature", "nom de l'analyte,température pic de fusion")

    mode = None

    for line_str in lignes_raw:
        line_clean = line_str.strip('\ufeff').strip()
        line_lower = line_clean.lower()

        if any(h in line_lower for h in headers_analytes):
            mode = "ANALYTES"
            continue
        elif any(h in line_lower for h in headers_melts):
            mode = "MELTS"
            continue
        elif not line_clean or line_clean.startswith("RESULT TABLE") or line_clean.startswith("History"):
            mode = None
            continue

        if mode == "ANALYTES":
            for col, key in [("rpoB1_", "rpoB1"), ("rpoB2_", "rpoB2"), ("rpoB3_", "rpoB3"), ("rpoB4_", "rpoB4")]:
                if line_clean.startswith(f"{key},"):
                    val = line_clean[len(key) + 1:].strip().replace('"', '').replace(',', ' | ')
                    ligne_patient[col] = val if val else "null"

        elif mode == "MELTS":
            keys_melts = [
                ("rpoB1_melt", "rpoB1 melt"), ("rpoB2_melt", "rpoB2 melt"),
                ("rpoB3_melt", "rpoB3 melt"), ("rpoB4_melt", "rpoB4 melt"),
                ("rpoB1_Mut_melt", "rpoB1 Mut melt"), ("rpoB2_Mut_melt", "rpoB2 Mut melt"),
                ("rpoB3_Mut_melt", "rpoB3 Mut melt"),
                ("rpoB4_Mut_meltA", "rpoB4 Mut melt A"), ("rpoB4_Mut_meltB", "rpoB4 Mut melt B")
            ]
            for col, key in keys_melts:
                if line_clean.startswith(f"{key},"):
                    val = line_clean[len(key) + 1:].strip().replace('"', '').replace(',', ' | ')
                    ligne_patient[col] = val if val else "null"

    return ligne_patient


if __name__ == "__main__":
    from exporter_schema import initialiser_ligne_patient_vierge

    lignes_test = [
        "Analyte Name,Ct,EndPt,Analyte Result,Probe Check Result",
        'rpoB1, "19.5, POS, PASS"',
        "Nom de l'analyte,Température pic de fusion,Hauteur pic de fusion",
        'rpoB1 melt, "78.5, 1200"'
    ]

    patient = initialiser_ligne_patient_vierge()
    patient = traiter_sous_section_3_rpob(lignes_test, patient)

    print("✅ Section 1 - Sous-section 3 exécutée avec succès :")
    print(f"   • rpoB1_     : {patient['rpoB1_']}")
    print(f"   • rpoB1_melt : {patient['rpoB1_melt']}")
    print(f"   • rpoB2_melt : {patient['rpoB2_melt']} (comportement 'null' vérifié)")