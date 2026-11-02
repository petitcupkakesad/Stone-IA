# bloc6_mutations.py
from typing import Tuple
import re
from typing import Dict, Any, List, Optional, Tuple

RULES_ULTRA = [
    ("i", [69.57, 0, 73.29, 0, 75.96, 0, 67.27, 0, 0], [0.16, 0, 0.16, 0, 0.22, 0, 0.15, 0, 0], "WildeType"),
    ("ii", [0, 63.52, 73.22, 0, 75.93, 0, 67.28, 0, 0], [0, 0.05, 0.05, 0, 0.05, 0, 0.05, 0, 0], "511CCG"),
    ("iii", [68.17, 0, 75.1, 0, 75.93, 0, 67.47, 0, 0], [0.06, 0, 0.17, 0, 0.21, 0, 0.15, 0, 0], "513CAG (Silent mutation)"),
    ("iv", [70.06, 0, 0, 69.72, 75.81, 0, 67.42, 0, 0], [0.12, 0, 0, 0.1, 0.11, 0, 0.18, 0, 0], "516GTC"),
    ("v", [69.71, 0, 0, 68.91, 75.7, 0, 67.39, 0, 0], [0.12, 0, 0, 0.17, 0.14, 0, 0.13, 0, 0], "516TAC"),
    ("vi", [70.12, 0, 0, 68.83, 0, 73.95, 67.12, 0, 0], [0.1, 0, 0, 0.1, 0, 0.06, 0.05, 0, 0], "522CAG"),
    ("vii", [69.6, 0, 0, 70.2, 0, 73.66, 67.26, 0, 0], [0.07, 0, 0, 0.07, 0, 0.09, 0.05, 0, 0], "522TTG"),
    ("viii", [69.47, 0, 73.45, 0, 0, 71.7, 66.08, 0, 0], [0.05, 0, 0.06, 0, 0, 0.30, 0.1, 0, 0], "526CCC"),
    ("ix", [69.27, 0, 73.17, 0, 0, 71.7, 67.57, 0, 0], [0.06, 0, 0.12, 0, 0, 0.1, 0.06, 0, 0], "526TAA"),
    ("x", [69.44, 0, 73.49, 0, 0, 72.83, 67.29, 0, 0], [0.1, 0, 0.13, 0, 0, 0.13, 0.16, 0, 0], "526TAC"),
    ("xi", [69.37, 0, 73.37, 0, 0, 70.63, 67.3, 0, 0], [0.06, 0, 0.15, 0, 0, 0.12, 0.1, 0, 0], "526TCC"),
    ("xii", [69.4, 0, 73.43, 0, 0, 71.7, 68.43, 0, 0], [0.1, 0, 0.12, 0, 0, 0.1, 0.06, 0, 0], "526TGC"),
    ("xiii", [69.27, 0, 73.33, 0, 0, 71.23, 67.1, 0, 0], [0.06, 0, 0.06, 0, 0, 0.06, 0.30, 0, 0], "531CAG"),
    ("xiv", [69.62, 0, 73.78, 0, 0, 73.54, 0, 71.06, 0], [0.08, 0, 0.08, 0, 0, 0.09, 0, 0.05, 0], "531TGG"),
    ("xv", [69.5, 0, 74.27, 0, 0, 73.44, 0, 73.89, 0], [0.12, 0, 0.16, 0, 0, 0.19, 0, 0.13, 0], "531TTG"),
    ("xvi", [69.64, 0, 73.3, 0, 75.98, 0, 0, 0, 61.68], [0.13, 0, 0.12, 0, 0.1, 0, 0, 0, 0.13], "533CCG"),
    ("xvii", [69.53, 0, 72.98, 0, 0, 0, 0, 0, 64.08], [0.05, 0, 0.08, 0, 0, 0, 0, 0, 0.08], "529AAA"),
    ("xviii", [69.53, 0, 0, 65.73, 75.5, 0, 66.93, 0, 0], [0.21, 0, 0, 0.38, 0.26, 0, 0.06, 0, 0], "518AAC del"),
    ("xix", [0, 65.73, 0, 69.07, 75.77, 0, 67.47, 0, 0], [0, 0.06, 0, 0.12, 0.12, 0, 0.06, 0, 0], "510CTG_516TAC"),
    ("xx", [0, 65.9, 71.87, 0, 75.83, 0, 67.47, 0, 0], [0, 0.1, 0.15, 0, 0.12, 0, 0.06, 0, 0], "511CCG_516GGC"),
    ("xxi", [0, 63.7, 73.67, 0, 0, 72.53, 67.53, 0, 0], [0, 0.1, 0.12, 0, 0, 0.15, 0.06, 0, 0], "512CGC_526AAC"),
    ("xxii", [0, 66.75, 74.05, 0, 0, 73.65, 0, 71.1, 0], [0, 0.06, 0.06, 0, 0, 0.13, 0, 0.08, 0], "512GGC_531TGG"),
    ("xxiii", [0, 0, 71.55, 0, 0, 72.28, 67.08, 0, 0], [0, 0, 0.06, 0, 0, 0.05, 0.13, 0, 0], "513CTA_523GAG"),
    ("xxiv", [0, 0, 73.23, 0, 0, 71.8, 67.7, 0, 0], [0, 0, 0.15, 0, 0, 0.1, 0.1, 0, 0], "513CTA_526TAA"),
    ("xxv", [69.87, 0, 0, 68.74, 75.81, 0, 67.2, 0, 0], [0.17, 0, 0, 0.19, 0.12, 0, 0.1, 0, 0], "515ATT_516TAC"),
    ("xxvi", [69.6, 0, 0, 70.03, 0, 72.5, 67.17, 0, 0], [0.1, 0, 0, 0.06, 0, 0.30, 0.12, 0, 0], "515ATT_526AAC"),
    ("xxvii", [70.85, 0, 71.77, 0, 75.78, 0, 0, 0, 61.62], [0.1, 0, 0.05, 0, 0.08, 0, 0, 0, 0.13], "516GGC_533CCG"),
    ("xxviii", [69.8, 0, 0, 68.5, 0, 73.23, 0, 73.8, 0], [0.1, 0, 0, 0.1, 0, 0.06, 0, 0.1, 0], "516TAC_531TTG"),
    ("xxix", [69.57, 0, 0, 70.3, 0, 72.87, 67.7, 0, 0], [0.31, 0, 0, 0.1, 0, 0.12, 0.1, 0, 0], "522TTG_531GCG"),
    ("xxx", [69.5, 0, 73.63, 0, 0, 69.53, 0, 0, 64.0], [0.17, 0, 0.21, 0, 0, 0.12, 0, 0, 0.1], "530ATG_531TTC"),
    ("xxxi", [0, 61.62, 0, 69.9, 0, 72.53, 67.48, 0, 0], [0, 0.04, 0, 0.06, 0, 0.08, 0.1, 0, 0], "512ACC_515ATT_526AAC"),
    ("xxxii", [69.4, 0, 73.5, 0, 0, 71.5, 68.9, 0, 0], [0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30], "526AGC-1"),
    ("xxxiii", [69.53, 0, 73.61, 0, 0, 71.59, 0, 0, 0], [0.11, 0, 0.18, 0, 0, 0.13, 0, 0, 0], "526AGC-2"),
    ("xxxiv", [69.51, 0, 73.46, 0, 0, 74.25, 0, 69.36, 0], [0.03, 0, 0.05, 0, 0, 0.05, 0, 0.07, 0], "526CGC-1"),
    ("xxxv", [69.55, 0, 73.49, 0, 0, 0, 0, 69.39, 0], [0.08, 0, 0.08, 0, 0, 0, 0, 0.09, 0], "526CGC-2"),
    ("xxxvi", [0, 66.1, 73.47, 0, 0, 74.27, 0, 69.43, 0], [0, 0.15, 0.05, 0, 0, 0.05, 0, 0.1, 0], "509AGG_526CGC-1"),
    ("xxxvii", [0, 66.09, 73.55, 0, 0, 0, 0, 69.3, 0], [0, 0.14, 0.14, 0, 0, 0, 0, 0.21, 0], "509AGG_526CGC-2"),
    ("xxxviii", [69.42, 0, 0, 0, 75.77, 0, 0, 0, 61.45], [0.13, 0, 0, 0, 0.12, 0, 0, 0, 0.14], "518GAC_533CCG-1"),
    ("xxxix", [69.6, 0, 71.5, 0, 75.9, 0, 0, 0, 61.7], [0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30], "518GAC_533CCG-2"),
    ("xl", [69.2, 0, 0, 71.1, 75.6, 0, 0, 0, 61.3], [0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30], "518GAC_533CCG-3"),
    ("xli", [69.38, 0, 73.29, 0, 0, 72.41, 67.47, 0, 0], [0.13, 0, 0.1, 0, 0, 0.06, 0.09, 0, 0], "526AAC or 526CTC"),
    ("xlii", [69.42, 0, 73.56, 0, 0, 72.19, 68.15, 0, 0], [0.17, 0, 0.23, 0, 0, 0.21, 0.15, 0, 0], "526GAC or 531TTC"),
    ("xliii", [69.65, 0, 0, 66.75, 75.75, 0, 67.14, 0, 0], [0.09, 0, 0, 0.13, 0.09, 0, 0.11, 0, 0], "516GAC del or 516GTC_518GAC")
]

def separer_temp_hauteur(val_str: str) -> Tuple[str, str]:
    """Extrait T° et Height séparés par '|'."""
    if not val_str or val_str == "null" or "|" not in val_str:
        return "null", "null"
    parts = [p.strip() for p in val_str.split("|")]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return "null", "null"


def extraire_ct(val_str: str) -> str:
    """Conserve uniquement la valeur Ct (1er élément avant '|')."""
    if not val_str or val_str == "null":
        return "null"
    parts = [p.strip() for p in val_str.split("|")]
    return parts[0]


def evaluer_patient_mutations(row: Dict[str, Any]) -> Dict[str, Any]:
    """Applique le Bloc 6 et le Sous-bloc 5 sur une ligne patient sélectionnée."""
    # c) Duplication et séparation des colonnes melt
    melt_cols = [
        ("rpoB1_melt", "rpoB1_T°", "rpoB1_Height"),
        ("rpoB1_Mut_melt", "rpoB1-Mut_T°", "rpoB1-Mut_Height"),
        ("rpoB2_melt", "rpoB2_T°", "rpoB2_Height"),
        ("rpoB2_Mut_melt", "rpoB2-Mut_T°", "rpoB2-Mut_Height"),
        ("rpoB3_melt", "rpoB3_T°", "rpoB3_Height"),
        ("rpoB3_Mut_melt", "rpoB3-Mut_T°", "rpoB3-Mut_Height"),
        ("rpoB4_melt", "rpoB4_T°", "rpoB4_Height"),
        ("rpoB4_Mut_meltA", "rpoB4-MutA_T°", "rpoB4-MutA_Height"),
        ("rpoB4_Mut_meltB", "rpoB4-MutB_T°", "rpoB4-Mut_Height")
    ]
    for src, col_t, col_h in melt_cols:
        t_val, h_val = separer_temp_hauteur(row.get(src, "null"))
        row[col_t] = t_val
        row[col_h] = h_val

    # d.iii. Extraction Ct pour Sondes A-E et rpoB1-4
    for ct_col in ["Sonde_A", "Sonde_B", "Sonde_C", "Sonde_D", "Sonde_E", "rpoB1_", "rpoB2_", "rpoB3_", "rpoB4_"]:
        row[ct_col] = extraire_ct(row.get(ct_col, "null"))

    test_xpert = str(row.get("Test_Xpert", ""))

    # e-h) Traitement spécifique MTB-RIF Standard (non-Ultra)
    if "MTB-RIF" in test_xpert and "Ultra" not in test_xpert:
        sondes_defaillantes = []
        mapping_codons = {
            "Sonde_A": "codons 428, 430, 431",
            "Sonde_B": "codons 430, 431, 432, 434, 435",
            "Sonde_C": "codons 435, 437, 441",
            "Sonde_D": "codons 444, 445, 446",
            "Sonde_E": "codons 450, 452"
        }
        for s in ["Sonde_A", "Sonde_B", "Sonde_C", "Sonde_D", "Sonde_E"]:
            if row.get(s) == "0.0":
                sondes_defaillantes.append(s)

        if len(sondes_defaillantes) == 1:
            s_unique = sondes_defaillantes[0]
            row["Profile_resistance"] = s_unique
            row["Codons associés"] = mapping_codons[s_unique]
        elif len(sondes_defaillantes) > 1:
            row["Profile_resistance"] = " | ".join(sondes_defaillantes)
            row["Codons associés"] = "null"
        else:
            row["Profile_resistance"] = "null"
            row["Codons associés"] = "null"
        row["Conflit_codons"] = "null"

    # Sous-bloc 5 : Traitement Ultra
    elif "Ultra" in test_xpert:
        row["Profile_resistance"] = "null"
        t_keys = ["rpoB1_T°", "rpoB1-Mut_T°", "rpoB2_T°", "rpoB2-Mut_T°", "rpoB3_T°", "rpoB3-Mut_T°", "rpoB4_T°", "rpoB4-MutA_T°", "rpoB4-MutB_T°"]
        vals_obs = []
        for k in t_keys:
            try:
                vals_obs.append(float(row.get(k, 0)))
            except (ValueError, TypeError):
                vals_obs.append(0.0)

        matches = []
        for rule_id, targets, tols, label in RULES_ULTRA:
            match = True
            for obs, tgt, tol in zip(vals_obs, targets, tols):
                if not (tgt - tol <= obs <= tgt + tol):
                    match = False
                    break
            if match:
                matches.append(label)

        if len(matches) == 0:
            row["Codons associés"] = "Génotype indéterminé"
            row["Conflit_codons"] = "null"
        elif len(matches) == 1:
            row["Codons associés"] = matches[0]
            row["Conflit_codons"] = "null"
        else:
            row["Codons associés"] = matches[0]
            row["Conflit_codons"] = " | ".join(matches)

    return row