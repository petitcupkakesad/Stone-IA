# sous_section5.py
import re
from typing import Dict, Any, Tuple

def traiter_sous_section5(ligne_patient: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Sous-section 5 : Résultats charge bacillaire et résistance à la RIF
    Sous-section 5.1 : Orientation Expert MTB/RIF vs Xpert MTB/RIF Ultra
    """
    res_tb = str(ligne_patient.get("Resultat_TB", "") or "").strip()

    # 1.a) Supprimer les caractères de tête "|" (pipe) avant "MTB"
    res_tb_cleaned = re.sub(r"^\|+", "", res_tb).strip()
    ligne_patient["Resultat_TB"] = res_tb_cleaned

    # 1.b) Extraction de la charge bacillaire (High, Medium, Low, Very Low, Trace)
    # Recherche insensible à la casse
    charge_match = re.search(
        r"\b(High|Medium|Low|Very\s+low|Trace)\b", 
        res_tb_cleaned, 
        flags=re.IGNORECASE
    )
    if charge_match:
        ligne_patient["Charge_bacille"] = charge_match.group(1).capitalize()
    else:
        ligne_patient["Charge_bacille"] = "null"

    # 1.c) Extraction de la résistance à la rifampicine (NOT DETECTED, DETECTED, INDETERMINATE)
    rif_match = re.search(
        r"(Rif\s+Resistance\s+(?:NOT\s+DETECTED|DETECTED|INDETERMINATE))", 
        res_tb_cleaned, 
        flags=re.IGNORECASE
    )
    if rif_match:
        # Standardisation en majuscules pour maintenir la cohérence avec le reste du pipeline
        ligne_patient["RIF resistance"] = rif_match.group(1).upper()
    else:
        ligne_patient["RIF resistance"] = "null"

    # Sous-section 5.1 : Routage selon la présence de "Ultra" dans Test_Xpert
    test_xpert = str(ligne_patient.get("Test_Xpert", "") or "")

    if "Ultra" in test_xpert:
        prochaine_etape = "SOUS_SECTION_3"
    else:
        # 5.1.2) Conserver la chaîne complète dans Resultat_TB pour MTB/RIF standard
        prochaine_etape = "SOUS_SECTION_2"

    return ligne_patient, prochaine_etape


# Exemple d'utilisation / test unitaire basique
if __name__ == "__main__":
    patient_test_ultra = {
        "Test_Xpert": "Xpert MTB/RIF Ultra",
        "Resultat_TB": "||MTB DETECTED High; Rif Resistance DETECTED"
    }
    
    patient_test_std = {
        "Test_Xpert": "Xpert MTB/RIF",
        "Resultat_TB": "|MTB DETECTED Low; Rif Resistance NOT DETECTED"
    }

    res_ultra, prochaine_u = traiter_sous_section5(patient_test_ultra)
    res_std, prochaine_s = traiter_sous_section5(patient_test_std)

    print("--- Test Ultra ---")
    print(res_ultra)
    print("Prochaine étape :", prochaine_u)

    print("\n--- Test Standard ---")
    print(res_std)
    print("Prochaine étape :", prochaine_s)