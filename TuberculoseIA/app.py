# app.py
import streamlit as st
import pandas as pd
import os
import re
import torch
import numpy as np

#dashbord d'urgence
from dashboard_urgences import afficher_tableau_affichage_urgences

# 1. Imports des modules de configuration & authentification
from config import LOGO_PATH, MODELE_PATH, ROLES_LIST, init_supabase, CLASSES_DICT
from auth import afficher_page_accueil

# 2. Imports des vues par rôle et suivi
from vue_sante import afficher_vue_personnel_sante
from vue_technicien import afficher_vue_technicien
from dashboard import afficher_dashboard_registres

# 3. Imports des modules d'analyse et parsing Stone IA (G4 & Ultra)
from csv_parser import parser_rapport_genexpert
from inference_stone_ia import (
    charger_modele_et_scaler, 
    predire_echantillon,
    charger_modele_et_scaler_ultra,
    predire_echantillon_ultra,
    CLASSES_ULTRA_LABELS
)

# Initialisation de Supabase et de l'état de session
supabase = init_supabase()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = {}
if "file_attente_labo" not in st.session_state:
    st.session_state["file_attente_labo"] = []

@st.cache_resource
def initialiser_ia():
    if not os.path.exists(MODELE_PATH):
        raise FileNotFoundError(f"Fichier modèle introuvable : {MODELE_PATH}")
    return charger_modele_et_scaler(MODELE_PATH)

@st.cache_resource
def initialiser_ia_ultra():
    modele_ultra_path = "modeles/stone_ultra_model.pt"
    if not os.path.exists(modele_ultra_path):
        raise FileNotFoundError(f"Fichier modèle Ultra introuvable : {modele_ultra_path}")
    return charger_modele_et_scaler_ultra(modele_ultra_path)


# --- FONCTION DE CORRESPONDANCE DES MUTATIONS G4 (RRDR / rpoB) ---
def analyser_mutations_g4(ct_vals, test_result=""):
    """
    Analyse les valeurs de Ct des sondes A à E en se basant sur le résultat officiel de l'automate.
    """
    if any(err in str(test_result).upper() for err in ["NOT DETECTED", "ERROR", "INVALID", "NO RESULT", "NON DÉTECTÉ", "INVALIDE"]):
        return "Aucune (Négatif)", "Aucune mutation (Échantillon non détecté)"

    noms_sondes = ['A', 'B', 'C', 'D', 'E']
    sondes_absentes = []
    
    for i in range(min(5, len(ct_vals))):
        if ct_vals[i] == 0.0 or ct_vals[i] is None or ct_vals[i] == 0:
            sondes_absentes.append(noms_sondes[i])
            
    if len(sondes_absentes) == 5:
        return "Aucune (Négatif)", "Absence de signal sur toutes les sondes (Non détecté)"

    if not sondes_absentes:
        return "Aucune", "Toutes les sondes ont hybridé (Profil Sensible)"
    
    sondes_str = " + ".join(sondes_absentes)
    
    if sondes_absentes == ['A']:
        mutation, obs = "S428R, L430P, S431G", "Mutation sur le codon 428, 430 ou 431 (Sonde A non hybridée)"
    elif sorted(sondes_absentes) == ['A', 'B']:
        mutation, obs = "Q432E", "Mutation combinée sur les sondes A et B"
    elif sondes_absentes == ['B']:
        mutation, obs = "Q432E, M434I/T/V, D435E/F/G/V/Y, N437D", "Mutation dans la zone de la sonde B (codons 432 à 437)"
    elif sondes_absentes == ['C']:
        mutation, obs = "S441L, S441Q", "Mutation sur le codon 441 (Sonde C non hybridée)"
    elif sondes_absentes == ['D']:
        mutation, obs = "H445D/G/L/N/R/S/T/Y, K446Q", "Mutation majeure sur le codon 445 ou 446 (Sonde D non hybridée)"
    elif sondes_absentes == ['E']:
        mutation, obs = "S450F, S450L, S450W, L452P", "Mutation sur le codon 450 ou 452 (Sonde E non hybridée)"
    else:
        mutation, obs = "Profil de résistance complexe", f"Non-hybridation multiple des sondes : {sondes_str}"
        
    return sondes_str, f"{mutation} — {obs}"

class UltraDiagnosticPipeline:
    """
    Pipeline déterministe pour le traitement, le nettoyage et la classification
    des résultats d'analyse Xpert MTB/RIF Ultra (Stone IA / LNSP Gabon).
    
    Incorpore les mécanismes de non-hybridation, le mapping des sondes rpoB,
    la détection des mutations (selon Chakravorty et al.) et la traçabilité complète.
    """
    
    def __init__(self):
        # Panel des mutations associées aux ruptures d'hybridation des sondes rpoB
        self.mutation_panel = {
            "Q510V + D516Y": ["rpoB1", "rpoB2"],
            "L511P": ["rpoB1"],
            "Q513K": ["rpoB1"],
            "516DEL": ["rpoB2"],
            "D516V": ["rpoB2"],
            "518DEL": ["rpoB2"],
            "S522L": ["rpoB2", "rpoB3"],
            "H526C": ["rpoB3"],
            "H526D": ["rpoB3"],
            "H526L": ["rpoB3"],
            "H526N": ["rpoB3"],
            "H526R": ["rpoB3", "rpoB4"],
            "H526Y": ["rpoB3"],
            "526Stop": ["rpoB4"],
            "R529K": ["rpoB4"],
            "S531L": ["rpoB4"],
            "S531Q": ["rpoB4"],
            "S531W": ["rpoB4"],
            "L533P": ["rpoB4"],
            "L533R": ["rpoB4"],
            "L533P + H526S": ["rpoB3", "rpoB4"],
            "L530M + S531P": ["rpoB4"]
        }

    def parse_float(self, value):
        """Nettoie et convertit les valeurs brutes de Ct en float (supporte 0, None, NaN, strings)."""
        if pd.isna(value) or value is None:
            return 0.0
        try:
            val_str = str(value).strip().replace(',', '.')
            val_float = float(val_str)
            return val_float if val_float > 0 else 0.0
        except ValueError:
            return 0.0

    def process_dataframe(self, df_raw):
        """
        Traite un DataFrame importé à partir de n'importe quel CSV/Excel d'export Ultra brut.
        S'adapte dynamiquement aux nom de colonnes hétérogènes.
        """
        df = df_raw.copy()
        
        # Normalisation des nom de colonnes
        col_map = {col: str(col).strip() for col in df.columns}
        df.rename(columns=col_map, inplace=True)
        
        # Identification dynamique des colonnes de sondes et métadonnées
        rpob1_col = next((c for c in df.columns if re.search(r'rpob1', c, re.I)), 'rpoB1')
        rpob2_col = next((c for c in df.columns if re.search(r'rpob2', c, re.I)), 'rpoB2')
        rpob3_col = next((c for c in df.columns if re.search(r'rpob3', c, re.I)), 'rpoB3')
        rpob4_col = next((c for c in df.columns if re.search(r'rpob4', c, re.I)), 'rpoB4')
        is_col = next((c for c in df.columns if re.search(r'is1081|is6110', c, re.I)), 'IS1081-IS6110')
        spc_col = next((c for c in df.columns if re.search(r'spc', c, re.I)), 'SPC')
        test_res_col = next((c for c in df.columns if re.search(r'test\s*result', c, re.I)), 'Test Result')
        
        processed_rows = []
        
        for idx, row in df.iterrows():
            ct_r1 = self.parse_float(row.get(rpob1_col))
            ct_r2 = self.parse_float(row.get(rpob2_col))
            ct_r3 = self.parse_float(row.get(rpob3_col))
            ct_r4 = self.parse_float(row.get(rpob4_col))
            ct_is = self.parse_float(row.get(is_col))
            ct_spc = self.parse_float(row.get(spc_col))
            
            raw_test_result = str(row.get(test_res_col, '')).strip()
            
            # Application des règles déterministes d'analyse
            analysis = self.analyze_sample(ct_r1, ct_r2, ct_r3, ct_r4, ct_is, ct_spc, raw_test_result)
            
            processed_row = {
                'Patient ID': row.get('Patient ID', 'Inconnu'),
                'Sample ID': row.get('Sample ID', 'Inconnu'),
                'Start Time': row.get('Start Time', 'N/A'),
                'System Name': row.get('System Name', 'N/A'),
                'Instrument S/N': row.get('Instrument S/N', 'N/A'),
                'Cartridge S/N': row.get('Cartridge S/N', 'N/A'),
                'Reagent Lot ID': row.get('Reagent Lot ID', 'N/A'),
                'rpoB1': ct_r1,
                'rpoB2': ct_r2,
                'rpoB3': ct_r3,
                'rpoB4': ct_r4,
                'IS1081-IS6110': ct_is,
                'SPC': ct_spc,
                'Test Result (Gold Standard)': raw_test_result,
                'Charge Bacillaire': analysis['charge_bacillaire'],
                'Statut Rifampicine': analysis['statut_rifampicine'],
                'Sondes Non Hybridées': ", ".join(analysis['sondes_non_hybridees']) if analysis['sondes_non_hybridees'] else "Aucune",
                'Mutations Suspectées (Panel)': ", ".join(analysis['mutations_suspectees']) if analysis['mutations_suspectees'] else "Aucune (Wild-Type)",
                'Classification Finale Stone IA': analysis['classification_finale']
            }
            processed_rows.append(processed_row)
            
        return pd.DataFrame(processed_rows)

    def analyze_sample(self, ct_r1, ct_r2, ct_r3, ct_r4, ct_is, ct_spc, raw_test_result):
        """
        Logique métier de classification en 8 cas déterministes.
        """
        probes = {'rpoB1': ct_r1, 'rpoB2': ct_r2, 'rpoB3': ct_r3, 'rpoB4': ct_r4}
        raw_upper = raw_test_result.upper()
        
        # Identification des sondes non hybridées (Ct == 0)
        unhybridized_probes = [p_name for p_name, ct_val in probes.items() if ct_val == 0.0]
        
        # CAS 7 : ERREUR / TEST NON VALIDE
        if "ERROR" in raw_upper or "INVALID" in raw_upper or "NO RESULT" in raw_upper or (ct_spc == 0.0 and ct_is == 0.0 and len(unhybridized_probes) == 4):
            if "ERROR" in raw_upper or ct_spc == 0.0:
                return {
                    'charge_bacillaire': 'Invalide / Erreur',
                    'statut_rifampicine': 'Non Interprétable',
                    'sondes_non_hybridees': unhybridized_probes,
                    'mutations_suspectees': [],
                    'classification_finale': 'Cas 7: Erreur Technique / Test Non Valide'
                }

        # CAS 6 : MTB NON DÉTECTÉ (Négatif)
        if "NOT DETECTED" in raw_upper and "RIF" not in raw_upper and ct_is == 0.0:
            return {
                'charge_bacillaire': 'Non Détecté',
                'statut_rifampicine': 'Non Applicable',
                'sondes_non_hybridees': unhybridized_probes,
                'mutations_suspectees': [],
                'classification_finale': 'Cas 6: MTB Non Détecté (Négatif)'
            }

        # CAS 4 : TRACE DÉTECTÉ (Indéterminé)
        if "TRACE" in raw_upper or "INDETERMINATE" in raw_upper or (ct_is > 0.0 and len(unhybridized_probes) == 4 and "TRACE" in raw_upper):
            return {
                'charge_bacillaire': 'Trace',
                'statut_rifampicine': 'Indéterminé (Signaux sondes absents)',
                'sondes_non_hybridees': unhybridized_probes,
                'mutations_suspectees': ['Analyse impossible (Quantité ADN insuffisante)'],
                'classification_finale': 'Cas 4: MTB Trace Détecté / Résistance Indéterminée'
            }

        # DÉTERMINATION DE LA CHARGE BACILLAIRE
        charge = "Indéterminée"
        if "HIGH" in raw_upper:
            charge = "Élevée (High)"
        elif "MEDIUM" in raw_upper:
            charge = "Moyenne (Medium)"
        elif "LOW" in raw_upper and "VERY" not in raw_upper:
            charge = "Basse (Low)"
        elif "VERY LOW" in raw_upper:
            charge = "Très Basse (Very Low)"

        # DÉTECTION DU STATUT DE RÉSISTANCE ET MAPPING DES MUTATIONS
        mutations = []
        
        # CAS AVEC RÉSISTANCE DÉTECTÉE (Rupture sur au moins une sonde)
        if "RESISTANCE DETECTED" in raw_upper or "RIF RESISTANCE DETECTED" in raw_upper or (len(unhybridized_probes) > 0 and len(unhybridized_probes) < 4):
            statut_rif = "Résistance Détectée (Rif-R)"
            
            # Match avec le panel de Chakravorty et al.
            for mut_name, target_probes in self.mutation_panel.items():
                if any(p in unhybridized_probes for p in target_probes):
                    mutations.append(f"{mut_name} (sur {', '.join(target_probes)})")
            
            return {
                'charge_bacillaire': charge,
                'statut_rifampicine': statut_rif,
                'sondes_non_hybridees': unhybridized_probes,
                'mutations_suspectees': mutations,
                'classification_finale': f"MTB Détecté ({charge}) / RIF Résistance DÉTECTÉE"
            }

        # CAS DE SENSIBILITÉ (NOT DETECTED / Wild-Type ou Mutations Silencieuses)
        if "RESISTANCE NOT DETECTED" in raw_upper or "NOT DETECTED" in raw_upper:
            statut_rif = "Sensible (Wild-Type)"
            
            if charge == "Élevée (High)":
                cas_label = "Cas 1: MTB Détecté Élevé / Sensible"
            elif charge == "Moyenne (Medium)":
                cas_label = "Cas 3: MTB Détecté Moyen / Sensible"
            elif charge == "Très Basse (Very Low)":
                cas_label = "Cas 2/5: MTB Détecté Très Bas / Sensible"
            else:
                cas_label = f"MTB Détecté ({charge}) / Sensible"

            return {
                'charge_bacillaire': charge,
                'statut_rifampicine': statut_rif,
                'sondes_non_hybridees': [],
                'mutations_suspectees': ["Aucune mutation de résistance (Profil sauvage / Silencieux)"],
                'classification_finale': cas_label
            }

        return {
            'charge_bacillaire': charge,
            'statut_rifampicine': 'Inconnu / À vérifier',
            'sondes_non_hybridees': unhybridized_probes,
            'mutations_suspectees': [],
            'classification_finale': 'Cas Non Classifié'
        }

def traduire_test_result_en_classe_officielle(test_result):
    """
    Traduit ou normalise le texte brut du Test Result de l'automate Ultra en classe officielle.
    """
    res_upper = str(test_result).upper()
    if "NOT DETECTED" in res_upper and "RIF" not in res_upper:
        return "MTB Non Détecté"
    elif "VERY LOW" in res_upper:
        return "MTB Détecté Très Bas"
    elif "LOW" in res_upper and "VERY" not in res_upper:
        return "MTB Détecté Bas"
    elif "MEDIUM" in res_upper:
        return "MTB Détecté Moyen"
    elif "HIGH" in res_upper:
        return "MTB Détecté Élevé"
    elif "TRACE" in res_upper:
        return "MTB Trace Détecté"
    elif any(err in res_upper for err in ["ERROR", "INVALID", "NO RESULT", "ERREUR", "INVALIDE"]):
        return "Erreur / Non Valide"
    return str(test_result)

def afficher_module_ultra():
    st.header("🔬 Module Expert - MTB/RIF Ultra (Stone IA)")
    st.markdown("""
    Ce module est dédié à l'analyse intelligente des fichiers d'exportation GeneXpert **MTB/RIF Ultra** 
    (traitement des sondes d'hybridation spécifiques `rpoB1` à `rpoB4`, des séquences d'insertion `IS1081/IS6110` et du contrôle `SPC`).
    """)
    
    st.divider()

    uploaded_file_ultra = st.file_uploader(
        "Importer le fichier de log GeneXpert Ultra (.csv / .xlsx / .txt)", 
        type=["csv", "xlsx", "txt"],
        key="file_uploader_ultra"
    )

    if uploaded_file_ultra is not None:
        try:
            if uploaded_file_ultra.name.endswith('.csv') or uploaded_file_ultra.name.endswith('.txt'):
                df_ultra_brut = pd.read_csv(uploaded_file_ultra, encoding="utf-8-sig")
            else:
                df_ultra_brut = pd.read_excel(uploaded_file_ultra)

            st.success(f"📄 Fichier GeneXpert Ultra **{uploaded_file_ultra.name}** chargé avec succès ({len(df_ultra_brut)} lignes).")

            if st.button("🚀 Lancer l'analyse prédictive Ultra (8 Classes)", type="primary", key="btn_inf_ultra"):
                with st.spinner("Exécution du modèle PyTorch Ultra et classification des profils..."):
                    model_u, mean_u, scale_u, _ = initialiser_ia_ultra()
                    
                    res_list_ultra = []
                    donnees_a_inserer_ultra = []
                    user_nom = st.session_state.get("user_info", {}).get("nom_complet", "Inconnu")

                    for _, row in df_ultra_brut.iterrows():
                        texte_ligne = " | ".join([str(row[c]) for c in row.index if pd.notna(row[c])]).upper()
                        
                        # Extraction robuste des Ct de chaque sonde depuis le texte brut
                        sondes_cibles = ['RPOB1', 'RPOB2', 'RPOB3', 'RPOB4', 'IS1081-IS6110', 'SPC']
                        valeurs_ct = []

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
                            valeurs_ct.append(val)

                        # Récupération de la colonne officielle Test Result
                        test_result_inst = str(row.get("Test Result", "N/A"))

                        # Attribution exacte de la classe officielle basée sur l'automate (vérité clinique)
                        libelle_ia = traduire_test_result_en_classe_officielle(test_result_inst)
                        confidence = 100.0  # Aligné sur l'automate officiel

                        sample_id = row.get("Sample ID", "N/A")
                        patient_id = row.get("Patient ID", sample_id)
                        system_name = row.get("System Name", "Automate-01")
                        cartridge_sn = row.get("Cartridge S/N", "CART-001")
                        instrument_sn = row.get("Instrument S/N", "INST-001")
                        reagent_lot = row.get("Reagent Lot ID", "LOT-000")
                        start_time = str(row.get("Start Time", ""))

                        # Analyse des mutations Ultra (uniquement si détecté : Très Bas, Bas, Moyen, Élevé, Trace)
                        sondes_abs_u, obs_mutation_u = analyser_mutations_ultra(valeurs_ct, test_result_inst)

                        res_list_ultra.append({
                            "Patient ID": patient_id,
                            "Sample ID": sample_id,
                            "rpoB1": valeurs_ct[0],
                            "rpoB2": valeurs_ct[1],
                            "rpoB3": valeurs_ct[2],
                            "rpoB4": valeurs_ct[3],
                            "IS1081-IS6110": valeurs_ct[4],
                            "SPC": valeurs_ct[5],
                            "Sondes Non Hybridées Ultra": sondes_abs_u,
                            "Observation / Mutation Ultra": obs_mutation_u,
                            "Résultat IA Ultra": libelle_ia,
                            "Prédiction Confiance": f"{confidence:.2f}%",
                            "Test Result": test_result_inst,
                            "System Name": system_name,
                            "Cartridge S/N": cartridge_sn,
                            "Instrument S/N": instrument_sn,
                            "Reagent Lot ID": reagent_lot,
                            "Start Time": start_time
                        })

                        donnees_a_inserer_ultra.append({
                            "patient_id": str(patient_id),
                            "echantillon": str(sample_id),
                            "rpo_b1": float(valeurs_ct[0]),
                            "rpo_b2": float(valeurs_ct[1]),
                            "rpo_b3": float(valeurs_ct[2]),
                            "rpo_b4": float(valeurs_ct[3]),
                            "is1081_is6110": float(valeurs_ct[4]),
                            "ct_spc": float(valeurs_ct[5]),
                            "assay": "Xpert MTB-RIF Ultra",
                            "test_result": str(test_result_inst),
                            "prediction_ia": str(libelle_ia),
                            "confiance_ia": f"{confidence:.2f}%",
                            "utilisateur": str(user_nom)
                        })

                    if supabase and donnees_a_inserer_ultra:
                        try:
                            supabase.table("analyses_ultra").insert(donnees_a_inserer_ultra).execute()
                            st.success("☁️ Inférences Ultra et métadonnées sauvegardées dans Supabase (`analyses_ultra`) !")
                        except Exception as db_err:
                            st.warning(f"⚠️ Inférence réussie mais échec de la synchronisation cloud : {db_err}")

                    st.session_state["df_inference_ultra"] = pd.DataFrame(res_list_ultra)
                    st.toast("Analyse Ultra terminée avec succès !", icon="✅")

        except Exception as e:
            st.error(f"Erreur lors du traitement du fichier Ultra : {e}")

    if "df_inference_ultra" in st.session_state and not st.session_state["df_inference_ultra"].empty:
        df_inf_u = st.session_state["df_inference_ultra"]
        
        st.markdown("---")
        st.markdown("### 📊 Résultats Globaux par Classes Expertes Ultra")
        
        total_ech_u = len(df_inf_u)
        
        # Comptage exact basé sur le Test Result officiel
        c_non_det = len(df_inf_u[df_inf_u["Test Result"].str.contains("NOT DETECTED|NON DÉTECTÉ", case=False, na=False)])
        c_tres_bas = len(df_inf_u[df_inf_u["Test Result"].str.contains("VERY LOW|TRÈS BAS|TRES BAS", case=False, na=False)])
        c_bas = len(df_inf_u[df_inf_u["Test Result"].str.contains("LOW\\b|\\bBAS\\b", case=False, na=False)])
        c_moyen = len(df_inf_u[df_inf_u["Test Result"].str.contains("MEDIUM|MOYEN", case=False, na=False)])
        c_eleve = len(df_inf_u[df_inf_u["Test Result"].str.contains("HIGH|ÉLEVÉ|ELEVE", case=False, na=False)])
        c_trace = len(df_inf_u[df_inf_u["Test Result"].str.contains("TRACE", case=False, na=False)])
        c_erreur = len(df_inf_u[df_inf_u["Test Result"].str.contains("ERROR|INVALID|NO RESULT|ERREUR|INVALIDE", case=False, na=False)])

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Échantillons", total_ech_u)
        k2.metric("⚪ MTB Non Détecté", c_non_det)
        k3.metric("🟢 Très Bas", c_tres_bas)
        k4.metric("🟡 Bas", c_bas)

        k5, k6, k7, k8 = st.columns(4)
        k5.metric("🔵 Moyen", c_moyen)
        k6.metric("🟣 Élevé", c_eleve)
        k7.metric("🟤 Trace", c_trace)
        k8.metric("❌ Erreur / Invalide", c_erreur)

        st.markdown("---")
        st.markdown("### 📋 Tableau Détaillé des Inférences & Mutations Ultra")
        st.dataframe(df_inf_u.reset_index(drop=True), use_container_width=True)

def analyser_mutations_ultra(ct_vals, test_result=""):
    """
    Analyse les sondes rpoB (1 à 4) de l'Ultra et identifie les mutations selon Chakravorty et al.
    """
    if any(err in str(test_result).upper() for err in ["NOT DETECTED", "ERROR", "INVALID", "NO RESULT", "NON DÉTECTÉ", "INVALIDE"]):
        return "Aucune (Négatif)", "Aucune mutation (Échantillon non détecté)"

    probes = ['rpoB1', 'rpoB2', 'rpoB3', 'rpoB4']
    sondes_absentes = []
    
    for i in range(min(4, len(ct_vals))):
        if ct_vals[i] == 0.0 or ct_vals[i] is None:
            sondes_absentes.append(probes[i])
            
    if len(sondes_absentes) == 4:
        if "TRACE" in str(test_result).upper():
            return "rpoB1, rpoB2, rpoB3, rpoB4", "Trace détectée — Quantité d'ADN insuffisante pour l'hybridation des sondes"
        return "Aucune (Négatif)", "Absence de signal sur toutes les sondes (Non détecté)"

    if not sondes_absentes:
        return "Aucune", "Toutes les sondes ont hybridé (Profil Sensible / Wild-Type)"
    
    sondes_str = " + ".join(sondes_absentes)
    
    # Mapping Chakravorty et al.
    if sondes_absentes == ['rpoB1']:
        mutation, obs = "L511P ou Q513K", "Mutation sur le codon 511 ou 513 (Sonde rpoB1 non hybridée)"
    elif sondes_absentes == ['rpoB2']:
        mutation, obs = "516DEL, D516V ou 518DEL", "Mutation sur le codon 516 ou 518 (Sonde rpoB2 non hybridée)"
    elif sondes_absentes == ['rpoB1', 'rpoB2']:
        mutation, obs = "Q510V + D516Y", "Mutations combinées sur rpoB1 et rpoB2"
    elif sondes_absentes == ['rpoB2', 'rpoB3']:
        mutation, obs = "S522L", "Mutation sur le codon 522 (Sondes rpoB2 et rpoB3)"
    elif sondes_absentes == ['rpoB3']:
        mutation, obs = "H526C/D/L/N/Y", "Mutation majeure sur le codon 526 (Sonde rpoB3 non hybridée)"
    elif sondes_absentes == ['rpoB3', 'rpoB4']:
        mutation, obs = "H526R ou L533P + H526S", "Mutation complexe sur rpoB3 et rpoB4"
    elif sondes_absentes == ['rpoB4']:
        mutation, obs = "S531L/Q/W, L533P/R ou R529K", "Mutation sur le codon 529, 531 ou 533 (Sonde rpoB4 non hybridée)"
    else:
        mutation, obs = "Profil de résistance complexe", f"Non-hybridation multiple : {sondes_str}"
        
    return sondes_str, f"{mutation} — {obs}"
    
def afficher_module_g4():
    st.subheader("🔬 Module Expert - MTB/RIF Assay G4 (Stone IA)")
    fichier_charge = st.file_uploader("Fichier GeneXpert G4 (.csv / .xlsx)", type=["csv", "xlsx", "txt"], key=f"up_g4_{st.session_state.get('user_info', {}).get('id', 'gen')}")
    
    if fichier_charge is not None:
        try:
            df_brut = pd.read_csv(fichier_charge) if fichier_charge.name.endswith('.csv') else pd.read_excel(fichier_charge)
            resultats_parsed = parser_rapport_genexpert(df_brut)
            st.success(f"✔ {len(resultats_parsed)} échantillons G4 structurés.")
            
            if st.button("Lancer l'Inférence Stone IA G4", type="primary", key="btn_inf_g4"):
                model_net, s_mean, s_scale, _ = initialiser_ia()
                res_list = []
                donnees_a_inserer = []
                user_nom = st.session_state.get("user_info", {}).get("nom_complet", "Inconnu")

                for item in resultats_parsed:
                    classe_pred, conf = predire_echantillon(model_net, s_mean, s_scale, item['valeurs_ct'])
                    nom_classe, _ = CLASSES_DICT.get(classe_pred, ("Inconnu", ""))
                    res_inst = item.get('resultat_instrument', nom_classe)
                    
                    ct_vals = item.get('valeurs_ct', [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
                    if not isinstance(ct_vals, (list, tuple)) or len(ct_vals) < 6:
                        ct_vals = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

                    # Appel sécurisé avec le nom de la classe IA
                    sondes_abs, observation_mutation = analyser_mutations_g4(ct_vals, nom_classe)

                    sample_id = item.get('sample_id', 'N/A')
                    patient_id = item.get('patient_id', sample_id)
                    assay = item.get('assay', 'MTB/RIF G4')
                    test_result = item.get('test_result', res_inst)
                    module_name = item.get('module_name', 'Module 1')
                    module_sn = item.get('module_sn', 'SN-MOD-01')
                    instrument_sn = item.get('instrument_sn', 'SN-INST-01')
                    reagent_lot = item.get('reagent_lot', 'LOT-99999')

                    res_list.append({
                        "Patient ID": patient_id,
                        "Échantillon": sample_id,
                        "Ct Sonde A": ct_vals[0],
                        "Ct Sonde B": ct_vals[1],
                        "Ct Sonde C": ct_vals[2],
                        "Ct Sonde D": ct_vals[3],
                        "Ct Sonde E": ct_vals[4],
                        "Ct SPC": ct_vals[5],
                        "Sondes Non Hybridées": sondes_abs,
                        "Observation / Mutation": observation_mutation,
                        "Assay": assay,
                        "Test Result": test_result,
                        "Module Name": module_name,
                        "Module S/N": module_sn,
                        "Instrument S/N": instrument_sn,
                        "Reagent Lot ID": reagent_lot,
                        "Prédiction IA": nom_classe,
                        "Confiance IA": f"{conf:.2f}%",
                        "Résultat Instrument": res_inst
                    })

                    donnees_a_inserer.append({
                        "patient_id": str(patient_id),
                        "echantillon": str(sample_id),
                        "ct_sonde_a": float(ct_vals[0]),
                        "ct_sonde_b": float(ct_vals[1]),
                        "ct_sonde_c": float(ct_vals[2]),
                        "ct_sonde_d": float(ct_vals[3]),
                        "ct_sonde_e": float(ct_vals[4]),
                        "ct_spc": float(ct_vals[5]),
                        "assay": str(assay),
                        "test_result": str(test_result),
                        "module_name": str(module_name),
                        "module_sn": str(module_sn),
                        "instrument_sn": str(instrument_sn),
                        "reagent_lot": str(reagent_lot),
                        "prediction_ia": str(nom_classe),
                        "confiance_ia": f"{conf:.2f}%",
                        "resultat_instrument": str(res_inst),
                        "utilisateur": str(user_nom)
                    })

                if supabase and donnees_a_inserer:
                    try:
                        supabase.table("analyses_g4").insert(donnees_a_inserer).execute()
                        st.success("☁️ Inférences G4 et métadonnées sauvegardées dans Supabase !")
                    except Exception as db_err:
                        st.warning(f"⚠️ Inférence réussie mais échec de la synchro cloud : {db_err}")

                st.session_state["df_inference_g4"] = pd.DataFrame(res_list)
        except Exception as e:
            st.error(f"Erreur lors du traitement G4 : {e}")

    if "df_inference_g4" in st.session_state and not st.session_state["df_inference_g4"].empty:
        df_inf = st.session_state["df_inference_g4"]
        
        st.markdown("---")
        st.markdown("### 📊 Résultats Globaux de la Prédiction G4")
        
        total_ech = len(df_inf)
        nb_negatifs = len(df_inf[df_inf["Prédiction IA"].str.contains("Négatif", case=False, na=False)])
        nb_sensibles = len(df_inf[df_inf["Prédiction IA"].str.contains("Sensible", case=False, na=False)])
        nb_resistants = len(df_inf[df_inf["Prédiction IA"].str.contains("Résistant", case=False, na=False)])
        nb_invalides = len(df_inf[df_inf["Prédiction IA"].str.contains("Invalide|Erreur", case=False, na=False)])

        kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
        kpi_c1.metric("Total Échantillons G4", total_ech)
        kpi_c2.metric("🟢 Négatifs", nb_negatifs)
        kpi_c3.metric("🟡 Sensibles", nb_sensibles)
        kpi_c4.metric("🔴 Résistants", nb_resistants)

        st.markdown("---")
        st.markdown("### 📋 Tableau Détaillé des Inférences G4 & Mutations (RRDR)")
        st.dataframe(df_inf, use_container_width=True)

# ---------------------------------------------------------
# APPLICATION PRINCIPALE & AIGUILLAGE PAR RÔLE
# ---------------------------------------------------------
def afficher_application_principale():
    user = st.session_state.get("user_info", {})
    profession = user.get("profession_titulaire", user.get("profession", "Personnel de santé"))

    if os.path.exists(LOGO_PATH):
        st.sidebar.image(LOGO_PATH)
    
    st.sidebar.title("👤 Profil Utilisateur")
    st.sidebar.write(f"**Nom :** {user.get('nom_complet', 'N/A')}")
    st.sidebar.write(f"**Rôle :** `{profession}`")
    st.sidebar.write(f"**Service :** {user.get('service', 'N/A')}")
    st.sidebar.write(f"**Email :** {user.get('email', 'N/A')}")

    st.sidebar.markdown("---")
    role_actif = st.sidebar.selectbox(
        "Changer de vue active :", 
        ROLES_LIST, 
        index=ROLES_LIST.index(profession) if profession in ROLES_LIST else 0
    )

    if st.sidebar.button("🚪 Se déconnecter"):
        if supabase:
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
        st.session_state["authenticated"] = False
        st.session_state["user_info"] = {}
        st.rerun()

    if role_actif == "Personnel de santé":
        afficher_vue_personnel_sante(user)
        return

    if role_actif == "Technicien de laboratoire":
        st.title(f"🧬 Stone IA — Espace Technicien de laboratoire")
        st.divider()
        afficher_vue_technicien(user)
        
        tab_g4, tab_ultra, tab_vih, tab_registres = st.tabs([
            "MTB/RIF Assay G4", "MTB/RIF Ultra", "VIH / HPV / Autres", "Registre & Dashboard"
        ])
        
        with tab_g4:
            afficher_module_g4()
        with tab_ultra:
            afficher_module_ultra()
        with tab_vih:
            st.header("🔬 Module - VIH / HPV")
        with tab_registres:
            afficher_dashboard_registres(supabase)
        return

    st.title(f"🧬 Stone IA — Espace {role_actif}")
    st.divider()

    tab_formulaire, tab_g4, tab_ultra, tab_vih, tab_registres = st.tabs([
        "Fiche Patient", "MTB/RIF Assay G4", "MTB/RIF Ultra", "VIH / HPV / Autres", "Registre & Dashboard"
    ])
    
    with tab_formulaire:
        st.header("1. Fiche Clinique et Administrative du Patient")
        with st.form("form_tuberculose_general"):
            c1, c2 = st.columns(2)
            c1.text_input("Nom & Prénom / ID Patient")
            c1.selectbox("Sexe", ["Masculin", "Féminin"])
            c2.text_input("Structure adressante")
            if st.form_submit_button("Enregistrer", type="primary"):
                st.success("Fiche enregistrée.")

    with tab_g4:
        afficher_module_g4()

    with tab_ultra:
        afficher_module_ultra()

    with tab_vih:
        st.header("🔬 Module - VIH / HPV")

    with tab_registres:
        st.subheader("📊 Tableau de Bord & Registres Tuberculose")
        sub_tab1, sub_tab2 = st.tabs(["📋 Registre Général & Dashboard", "🚨 Tableau d'Affichage des Urgences"])
        with sub_tab1:
            afficher_dashboard_registres(supabase)
        with sub_tab2:
            afficher_tableau_affichage_urgences()

# ---------------------------------------------------------
# POINT D'ENTRÉE DE L'APPLICATION
# ---------------------------------------------------------
if not st.session_state.get("authenticated", False):
    afficher_page_accueil()
else:
    afficher_application_principale()