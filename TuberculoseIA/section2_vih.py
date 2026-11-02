# section2_vih.py
import re
from typing import Dict, Any, List, Tuple

def traiter_section2_vih(lignes_raw: List[str], ligne_patient: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Section 2 & Sous-section 4 : Traitement des résultats de la Charge Virale VIH-1.
    
    Règles appliquées :
    1. Extraction de 'Result_VIH' à partir de 'Test Result,' ou 'Résultat du test,'.
    2. Routage :
       - Non détecté -> Bloc 4
       - Erreur / Invalide / No Result -> Sous-section 1
       - Détecté -> Extraction Sous-section 4 (copies/mL et log)
    """
    resultat_brut = ""
    for line_str in lignes_raw:
        line_clean = line_str.strip('\ufeff').strip()
        if line_clean.startswith("Test Result,") or line_clean.startswith("Résultat du test,"):
            parts = [p.strip() for p in line_clean.split(',')]
            if len(parts) >= 2:
                resultat_brut = parts[1]
                break

    res_clean = resultat_brut.rstrip('|').strip()
    ligne_patient["Result_VIH"] = res_clean
    res_upper = res_clean.upper()

    # Erreurs / Invalides
    mots_cles_erreur = ["INVALID", "INVALIDE", "ERROR", "ERREUR", "NO RESULT", "AUCUN RÉSULTAT", "PAS DE RÉSULTAT"]
    if any(err in res_upper for err in mots_cles_erreur):
        return ligne_patient, "SOUS_SECTION_1_ERREURS"

    # Non Détecté
    if "HIV-1 NON DÉTECTÉ" in res_upper or "HIV-1 NOT DETECTED" in res_upper:
        return ligne_patient, "BLOC_4"

    # Détecté -> Traitement Sous-section 4
    if "HIV-1 DÉTECTÉ" in res_upper or "HIV-1 DETECTED" in res_upper:
        # a) Cas < 40 copies/mL
        if "< 40" in res_clean:
            ligne_patient["Charge_virale (copiesp/mL)"] = "< 40"
            match_log = re.search(r"\(log\s*([\d.]+)\)", res_clean, re.IGNORECASE)
            ligne_patient["Charge_virale (log)"] = match_log.group(1) if match_log else "null"
        else:
            # b) Extraction des valeurs numériques (notation scientifique ou entière)
            match_scientific = re.search(r"(\d+(?:\.\d+)?E\+?\d+|\d+)\s*copies/mL", res_clean, re.IGNORECASE)
            if match_scientific:
                val_str = match_scientific.group(1)
                try:
                    val_float = float(val_str)
                    ligne_patient["Charge_virale (copiesp/mL)"] = str(round(val_float))
                except ValueError:
                    ligne_patient["Charge_virale (copiesp/mL)"] = val_str
            else:
                ligne_patient["Charge_virale (copiesp/mL)"] = "null"

            # Isolement de la valeur décimale entre parenthèses (ex: log)
            match_log = re.search(r"\(([\d.]+)\)", res_clean)
            if match_log:
                ligne_patient["Charge_virale (log)"] = match_log.group(1)
            else:
                ligne_patient["Charge_virale (log)"] = "null"

        return ligne_patient, "BLOC_4"

    return ligne_patient, "BLOC_4"


if __name__ == "__main__":
    from exporter_schema import initialiser_ligne_patient_vierge

    cas_tests_vih = [
        ("Test Result, HIV-1 DETECTED < 40 copies/mL (log 1.60)", "Copies: < 40, Log: 1.60"),
        ("Test Result, HIV-1 DETECTED 9.12E04 copies/mL (4.96)", "Copies attendues: 91200, Log: 4.96"),
        ("Test Result, HIV-1 NOT DETECTED", "Routage vers BLOC_4")
    ]

    print("✅ Section 2 (Charge Virale VIH) exécutée avec succès :")
    for line, note in cas_tests_vih:
        p = initialiser_ligne_patient_vierge()
        p, route = traiter_section2_vih([line], p)
        print(f"   • {p['Result_VIH']} --> Copies: {p['Charge_virale (copiesp/mL)']}, Log: {p['Charge_virale (log)']} ({note})")