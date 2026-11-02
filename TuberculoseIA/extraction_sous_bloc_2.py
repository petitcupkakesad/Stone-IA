# extraction_sous_bloc_2.py
import re
from typing import Dict, Any, List, Tuple

def extraire_metadonnees_globales(contenu_texte: str) -> Tuple[Dict[str, str], List[str]]:
    """
    Sous-bloc 2 : Extraction du laboratoire et de la date d'exportation.
    
    Règles appliquées :
    1. Laboratoire : Première occurrence de "System Name," ou "Nom du système,".
       - Avertissement consigné si plusieurs occurrences distinctes sont détectées.
    2. Date_export : "Exported Date," ou "Date d'exportation," formatée en JJ/MM/20AA (sans l'heure).
    """
    logs: List[str] = []
    metadonnees = {
        "Laboratoire": "",
        "Date_export": ""
    }

    lignes = contenu_texte.splitlines()

    # --- 1. Extraction du Laboratoire ("System Name," / "Nom du système,") ---
    labo_occurrences = []
    pattern_labo = re.compile(r"(?:System\s*Name|Nom\s*du\s*système)\s*,\s*([^\r\n,]+)", re.IGNORECASE)

    for line in lignes:
        match = pattern_labo.search(line)
        if match:
            valeur = match.group(1).strip()
            if valeur:
                labo_occurrences.append(valeur)

    if labo_occurrences:
        metadonnees["Laboratoire"] = labo_occurrences[0]
        if len(set(labo_occurrences)) > 1:
            logs.append(
                f"[AVERTISSEMENT Logs] Plusieurs noms de laboratoire détectés : {labo_occurrences}. "
                f"La première occurrence '{labo_occurrences[0]}' a été conservée."
            )

    # --- 2. Extraction de Date_export ("Exported Date," / "Date d'exportation,") ---
    pattern_date = re.compile(
        r"(?:Exported\s*Date|Date\s*d'exportation)\s*,\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{2})(?:\s+\d{1,2}:\d{1,2}(?::\d{1,2})?)?",
        re.IGNORECASE
    )

    for line in lignes:
        match = pattern_date.search(line)
        if match:
            jour, mois, annee_2d = match.groups()[:3]
            # Formate JJ/MM/20AA en ommettant l'heure
            metadonnees["Date_export"] = f"{int(jour):02d}/{int(mois):02d}/20{annee_2d}"
            break  # On conserve la première date d'exportation trouvée

    return metadonnees, logs


if __name__ == "__main__":
    # Test unitaire du Sous-bloc 2
    contenu_test = """
    System Name, LNSP_TBC_LAB
    Exported Date, 18/09/26 14:30:22
    RESULT TABLE
    Sample ID, PAT001
    System Name, LNSP_TBC_LAB_OLD
    """
    
    meta, journal = extraire_metadonnees_globales(contenu_test)
    print("✅ Sous-bloc 2 exécuté avec succès :")
    print(f"   • Laboratoire : {meta['Laboratoire']}")
    print(f"   • Date_export : {meta['Date_export']}")
    if journal:
        print("   • Logs enregistrés :", journal)