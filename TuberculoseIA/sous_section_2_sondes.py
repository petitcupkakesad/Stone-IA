# sous_section_2_sondes.py
from typing import Dict, Any, List

def traiter_sous_section_2_sondes(lignes_raw: List[str], ligne_patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Section 1 - Sous-section 2 : Extraction et conversion des valeurs des sondes Probe A à E.
    
    Règles appliquées :
    1. Détection de la section "Analyte Name,..." ou "Nom de l'analyte,...".
    2. Extraction des lignes commençant par "Probe A,", "Probe B,", "Probe C,", "Probe D,", "Probe E,".
    3. Remplacement systématique de la virgule (,) par " | " dans la chaîne extraite.
    4. Affectation dans les colonnes Sonde_A, Sonde_B, Sonde_C, Sonde_D, Sonde_E.
    """
    headers_analytes = (
        "analyte name,ct,endpt,analyte result,probe check result",
        "nom de l'analyte,ct,valeur finale,résultat analyte,résultat du contrôle de la sonde"
    )

    mapping_sondes = {
        "Probe A": "Sonde_A",
        "Probe B": "Sonde_B",
        "Probe C": "Sonde_C",
        "Probe D": "Sonde_D",
        "Probe E": "Sonde_E"
    }

    lecture_analytes = False

    for line_str in lignes_raw:
        line_clean = line_str.strip('\ufeff').strip()
        line_lower = line_clean.lower()

        # 1. Detection de l'en-tête du tableau d'analytes
        if any(line_lower.startswith(h) for h in headers_analytes):
            lecture_analytes = True
            continue

        if lecture_analytes:
            # Fin du tableau sur ligne vide ou nouveau bloc
            if not line_clean or line_clean.startswith("RESULT TABLE") or line_clean.startswith("History"):
                lecture_analytes = False
                continue

            # 1.a & 1.b. Extraction et substitution des virgules par " | " (Règle 1.b.1 & 2)
            for probe_key, col_target in mapping_sondes.items():
                if line_clean.startswith(f"{probe_key},"):
                    # Récupère tout ce qui suit "Probe X,"
                    valeur_brute = line_clean[len(probe_key) + 1:].strip()
                    # Substitue la virgule par " | "
                    valeur_formatee = valeur_brute.replace(",", " | ")
                    ligne_patient[col_target] = valeur_formatee
                    break

    return ligne_patient


if __name__ == "__main__":
    from exporter_schema import initialiser_ligne_patient_vierge

    # Test unitaire de la Sous-section 2
    lignes_test_sondes = [
        "RESULT TABLE",
        "Sample ID, PATIENT_TB_POS_01",
        "Test Result, MTB DETECTED HIGH",
        "Analyte Name,Ct,EndPt,Analyte Result,Probe Check Result",
        "Probe A, 18.2, 340, POS, PASS",
        "Probe B, 18.5, 310, POS, PASS",
        "Probe C, 19.0, 290, POS, PASS",
        "Probe D, 18.8, 305, POS, PASS",
        "Probe E, 18.1, 350, POS, PASS",
        "SPC, 24.1, 150, PASS, PASS",
        ""
    ]

    patient = initialiser_ligne_patient_vierge()
    patient = traiter_sous_section_2_sondes(lignes_test_sondes, patient)

    print("✅ Section 1 - Sous-section 2 exécutée avec succès :")
    print(f"   • Sonde_A : {patient['Sonde_A']}")
    print(f"   • Sonde_B : {patient['Sonde_B']}")
    print(f"   • Sonde_C : {patient['Sonde_C']}")
    print(f"   • Sonde_D : {patient['Sonde_D']}")
    print(f"   • Sonde_E : {patient['Sonde_E']}")