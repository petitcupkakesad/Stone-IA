# exporter_schema.py
from typing import List, Dict, Any

# Ordre chronologique strict des 46 colonnes de sortie
COLONNES_SORTIE: List[str] = [
    "Laboratoire",
    "Date_export",
    "#Echantillon",
    "Run_Date",
    "Test_Xpert",
    "Annee",
    "Resultat_TB",
    "Charge_bacille",
    "RIF resistance",
    "Message_Erreur",
    "Sonde_D",
    "Sonde_C",
    "Sonde_E",
    "Sonde_B",
    "Sonde_A",
    "rpoB1_",
    "rpoB1_melt",
    "rpoB1_Mut_melt",
    "rpoB2_",
    "rpoB2_melt",
    "rpoB2_Mut_melt",
    "rpoB3_",
    "rpoB3_melt",
    "rpoB3_Mut_melt",
    "rpoB4_",
    "rpoB4_melt",
    "rpoB4_Mut_meltA",
    "rpoB4_Mut_meltB",
    "Result_VIH",
    "Charge_virale (copiesp/mL)",
    "Charge_virale (log)",
    "Message_Erreur",
    "Nombre_message_erreur",
    "Message_s",
    "Result_Covid19",
    "Infection-Covid19",
    "VIH_Qual_result",
    "HPV_result",
    "HPV_16",
    "HPV_18-45",
    "Module",
    "Lot_reactif",
    "Expiration_reactif",
    "Statut_erreur",
    "Statut_f",
    "Utilisateur"
]

def initialiser_ligne_patient_vierge() -> Dict[str, Any]:
    """
    Initialise une ligne de données patient structurée selon le Sous-bloc 1.
    Toutes les colonnes sont initialisées à None / chaîne vide dans l'ordre chronologique exact.
    """
    return {colonne: "" for colonne in COLONNES_SORTIE}

if __name__ == "__main__":
    ligne_test = initialiser_ligne_patient_vierge()
    print(f"✅ Sous-bloc 1 initialisé : {len(COLONNES_SORTIE)} colonnes créées dans l'ordre chronologique.")
    print("Exemple de clés :", list(ligne_test.keys())[:5], "...")