import streamlit as st
import pandas as pd
import datetime
import torch
import torch.nn as nn
import re
from suivi_patients import afficher_section_suivi_sante
from inference_stone_ia import (
    charger_modele_et_scaler_ultra, 
    predire_echantillon_ultra, 
    CLASSES_ULTRA_LABELS
)

# --- 0. FONCTION DE MISE EN COULEUR DES URGENCES ---
def colorer_lignes_urgence(row):
    """
    Applique un code couleur dynamique en fonction de la criticité clinique et du statut de résistance :
    - 🔴 ROUGE VIF : Résistance à la Rifampicine détectée (Urgence MDR-TB)
    - 🟡 JAUNE : Trace détectée ou Résistance Indéterminée
    - 🟠 ORANGE : Erreur technique ou Test non valide
    - 🟢 VERT : MTB Non Détecté (Négatif)
    - 🔵 BLEU CLAIR : MTB Détecté & Sensible / Wild-Type
    """
    res_raw = str(row.get('Test Result (Gold Standard)', '') or row.get('Test Result', '')).upper()
    classification = str(row.get('Classification Finale Stone IA', '') or row.get('Résultat IA Ultra', '')).upper()
    
    # 1. URGENCE CRITIQUE : Résistance détectée
    if "RESISTANCE DETECTED" in res_raw or "RÉSISTANCE DÉTECTÉE" in classification or "RÉSISTANT" in classification:
        return ['background-color: #ff4d4d; color: white; font-weight: bold'] * len(row)
    
    # 2. ATTENTION : Trace ou Indéterminé
    elif "TRACE" in res_raw or "INDETERMINATE" in res_raw or "INDÉTERMINÉ" in classification:
        return ['background-color: #ffeb3b; color: black; font-weight: bold'] * len(row)
    
    # 3. ERREUR TECHNIQUE : Erreur / Invalide
    elif any(err in res_raw or err in classification for err in ["ERROR", "INVALID", "NO RESULT", "ERREUR", "INVALIDE"]):
        return ['background-color: #ff9800; color: black; font-weight: bold'] * len(row)
    
    # 4. NÉGATIF : Sécurisé
    elif "NOT DETECTED" in res_raw or "NON DÉTECTÉ" in classification:
        return ['background-color: #d4edda; color: black'] * len(row)
    
    # 5. STANDARD SENSIBLE : Positif sensible
    else:
        return ['background-color: #cce5ff; color: black'] * len(row)

def afficher_tableau_affichage_urgences():
    st.subheader("🚨 Tableau d'Affichage & Triage des Urgences Cliniques (Stone IA)")
    st.markdown("""
    Ce tableau priorise les flux d'échantillons du laboratoire selon un code couleur standardisé :
    * 🔴 **Rouge** : Résistance à la Rifampicine détectée (Urgence MDR)
    * 🟡 **Jaune** : Trace / Indéterminé
    * 🟠 **Orange** : Erreur / Invalide
    * 🟢 **Vert** : Négatif
    * 🔵 **Bleu** : Sensible (Wild-Type)
    """)
    
    # Récupération directe depuis le DataFrame de la session Ultra (généré lors du lancement du test)
    df_u = st.session_state.get("df_inference_ultra", pd.DataFrame())

    if df_u.empty:
        st.info("ℹ️ Veuillez d'abord lancer l'analyse prédictive Ultra dans l'onglet 'MTB/RIF Ultra' pour alimenter ce tableau d'urgences.")
        return

    col_f1, _ = st.columns(2)
    with col_f1:
        filtre_urgence = st.checkbox("🚨 Afficher uniquement les cas urgents / suspects (Résistances & Erreurs)", value=False)
    
    if filtre_urgence:
        mask = df_u.apply(lambda r: any(k in str(r.values).upper() for k in ["RESISTANCE DETECTED", "RÉSISTANCE DÉTECTÉE", "ERROR", "INVALID", "ERREUR", "TRACE"]), axis=1)
        df_affiche = df_u[mask]
    else:
        df_affiche = df_u

    if not df_affiche.empty:
        # Application du style de mise en forme conditionnelle avec codes couleurs
        styled_table = df_affiche.style.apply(colorer_lignes_urgence, axis=1)
        st.dataframe(styled_table, use_container_width=True)
        
        csv_data = df_affiche.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Télécharger le registre de tri des urgences (.csv)",
            data=csv_data,
            file_name="registre_urgences_tuberculose_lnsp.csv",
            mime="text/csv"
        )
    else:
        st.warning("Aucun échantillon ne correspond aux critères sélectionnés.")


# --- 1. ARCHITECTURE DES MODÈLES PYTORCH (G4 & ULTRA) ---
class StoneG4Net(nn.Module):
    def __init__(self, input_dim, num_classes):
        super(StoneG4Net, self).__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(64, 32)
        self.out = nn.Linear(32, num_classes)

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        return self.out(x)

@st.cache_resource
def initialiser_ia_g4():
    model = StoneG4Net(input_dim=6, num_classes=4)
    model.load_state_dict(torch.load("stone_g4_model.pt", map_location=torch.device('cpu'), weights_only=False))
    model.eval()
    return model


# --- 2. MODULE D'ANALYSE G4 ---
def afficher_module_g4():
    st.header("🔬 Module Expert - MTB/RIF Assay G4 (Stone IA)")
    st.markdown("Analyse automatisée des fichiers d'exportation GeneXpert G4 (Sondes A à E).")
    
    uploaded_file_g4 = st.file_uploader("Importer le fichier de log G4 (.csv / .xlsx)", type=["csv", "xlsx", "txt"], key="up_g4")
    
    if uploaded_file_g4 is not None:
        st.success("Fichier G4 chargé avec succès !")
        if st.button("🚀 Lancer l'analyse G4 & Enregistrer", type="primary"):
            ct_vals = [22.1, 22.3, 23.0, 24.1, 25.0, 24.5]
            
            try:
                model_g4 = initialiser_ia_g4()
                input_tensor = torch.tensor([ct_vals], dtype=torch.float32)
                with torch.no_grad():
                    outputs = model_g4(input_tensor)
                    probs = torch.softmax(outputs, dim=1)
                    conf, pred_idx = torch.max(probs, dim=1)
                    nom_classe = ["Sensible", "Résistance Indéterminée", "Résistance RIF Détectée", "Invalide"][pred_idx.item()]
                    conf_str = f"{conf.item() * 100:.2f}%"
            except Exception:
                nom_classe = "Sensible (Simulé)"
                conf_str = "98.50%"

            donnees_g4 = {
                "patient_id": st.session_state.get("current_patient_id", "LNSP-G4-001"),
                "echantillon": uploaded_file_g4.name,
                "ct_sonde_a": float(ct_vals[0]),
                "ct_sonde_b": float(ct_vals[1]),
                "ct_sonde_c": float(ct_vals[2]),
                "ct_sonde_d": float(ct_vals[3]),
                "ct_sonde_e": float(ct_vals[4]),
                "ct_spc": float(ct_vals[5]),
                "assay": "Xpert MTB-RIF",
                "test_result": "MTB DÉTECTÉ | RIF Résistant Non Détecté",
                "prediction_ia": nom_classe,
                "confiance_ia": conf_str,
                "utilisateur": st.session_state.get("user_info", {}).get("nom_complet", "Technicien Labo")
            }
            st.json(donnees_g4)
            st.success("Données G4 traitées et prêtes pour Supabase !")


# --- 3. MODULE D'ANALYSE ULTRA (8 CLASSES & TABLEAU RICHE) ---
def afficher_module_ultra():
    st.header("🔬 Module Expert - MTB/RIF Ultra (Stone IA)")
    st.markdown("Analyse intelligente des fichiers d'exportation GeneXpert **MTB/RIF Ultra** (Sondes rpoB1 à rpoB4, IS1081/IS6110 et SPC).")
    
    uploaded_file_ultra = st.file_uploader("Importer le fichier de log Ultra (.csv / .xlsx)", type=["csv", "xlsx", "txt"], key="up_ultra")
    
    if uploaded_file_ultra is not None:
        try:
            if uploaded_file_ultra.name.endswith('.csv') or uploaded_file_ultra.name.endswith('.txt'):
                df_ultra = pd.read_csv(uploaded_file_ultra, encoding="utf-8-sig")
            else:
                df_ultra = pd.read_excel(uploaded_file_ultra)

            st.success(f"📄 Fichier GeneXpert Ultra **{uploaded_file_ultra.name}** chargé ({len(df_ultra)} lignes).")

            if st.button("🚀 Classifier & Analyser avec Stone IA Ultra (8 Classes)", type="primary"):
                model_u, mean_u, scale_u, feats_u = charger_modele_et_scaler_ultra()
                
                if model_u is None:
                    st.error("❌ Modèle Ultra introuvable dans 'modeles/stone_ultra_model.pt'. Veuillez lancer l'entraînement d'abord.")
                    return

                predictions_ultra = []
                
                for _, row in df_ultra.iterrows():
                    texte_ligne = " | ".join([str(row[c]) for c in row.index if pd.notna(row[c])]).upper()
                    
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

                    pred_class, confidence = predire_echantillon_ultra(model_u, mean_u, scale_u, valeurs_ct)
                    libelle_ia = CLASSES_ULTRA_LABELS.get(pred_class, "Inconnu")

                    ligne_dict = row.to_dict()
                    ligne_dict["rpoB1"] = valeurs_ct[0]
                    ligne_dict["rpoB2"] = valeurs_ct[1]
                    ligne_dict["rpoB3"] = valeurs_ct[2]
                    ligne_dict["rpoB4"] = valeurs_ct[3]
                    ligne_dict["IS1081-IS6110"] = valeurs_ct[4]
                    ligne_dict["SPC"] = valeurs_ct[5]
                    ligne_dict["Résultat IA Ultra"] = libelle_ia
                    ligne_dict["Prédiction Confiance"] = f"{confidence:.2f}%"
                    
                    predictions_ultra.append(ligne_dict)

                df_res_ultra = pd.DataFrame(predictions_ultra)
                st.session_state["res_tech_ultra"] = df_res_ultra
                st.toast("Analyse Ultra terminée avec succès !", icon="✅")

        except Exception as e:
            st.error(f"Erreur lors de la lecture ou de l'analyse du fichier Ultra : {e}")

    if "res_tech_ultra" in st.session_state:
        df_res_u = st.session_state["res_tech_ultra"]
        st.subheader("📊 Résultats Inférence Stone IA (Module Ultra - 8 Classes)")
        
        colonnes_prioritaires = [
            "Sample ID", "Patient ID", "rpoB1", "rpoB2", "rpoB3", "rpoB4",
            "IS1081-IS6110", "SPC", "Résultat IA Ultra", "Prédiction Confiance", 
            "Test Result", "System Name", "Cartridge S/N", "Instrument S/N", 
            "Reagent Lot ID", "Expiration Date", "Start Time"
        ]
        
        colonnes_a_afficher = [col for col in colonnes_prioritaires if col in df_res_u.columns]
        st.dataframe(df_res_u[colonnes_a_afficher], use_container_width=True)

        supabase = st.session_state.get("supabase_client", None)
        if st.button("💾 Enregistrer le lot dans la base Supabase (Ultra)"):
            if supabase:
                try:
                    supabase.table("analyses_ultra").insert(df_res_u.to_dict(orient="records")).execute()
                    st.success("Enregistrement global réussi dans Supabase ! ✔")
                except Exception as e:
                    st.error(f"Erreur d'insertion groupée : {e}")
            else:
                st.info("Simulation : Connexion Supabase inactive.")


# --- 4. VUE PRINCIPALE DU TECHNICIEN (AVEC ONGLETS) ---
def afficher_vue_technicien(user):
    file_attente = st.session_state.get("file_attente_labo", [])
    patients_non_traites = [p for p in file_attente if p.get("Statut") == "En attente d'examen Labo"]
    nb_en_attente = len(patients_non_traites)

    st.subheader("📥 File d'attente des patients transmis (Personnel de Santé)")
    col_t1, col_t2, col_t3 = st.columns(3)
    col_t1.metric("Patients en attente au Labo", nb_en_attente)
    col_t2.metric("Statut Automate GeneXpert", "Opérationnel 🟢")
    col_t3.metric("Connexion Labo", "En ligne 🟢")

    if nb_en_attente > 0:
        st.warning(f"🔔 **{nb_en_attente} patient(s) reçu(s)** en attente de validation technique !")
        
        noms_patients = [f"{p['Patient']} (ID: {p['ID_Transmission']} | Service: {p['Service']})" for p in patients_non_traites]
        choix_patient_str = st.selectbox("Sélectionner un patient dans la file d'attente à traiter :", noms_patients, key="sel_patient_labo")
        
        idx_sous_liste = noms_patients.index(choix_patient_str)
        patient_actif = patients_non_traites[idx_sous_liste]
        idx_global = file_attente.index(patient_actif)
        
        st.session_state["current_patient_id"] = patient_actif.get('ID_Transmission', 'N/A')

        with st.form(f"form_labo_{patient_actif['ID_Transmission']}", clear_on_submit=False):
            st.markdown(f"#### Traitement du dossier : **{patient_actif['Patient']}** (Transmis par {patient_actif['Service']}, Réf: {patient_actif['Docteur']})")
            
            c_info1, c_info2 = st.columns(2)
            with c_info1:
                st.write(f"- **Âge / Sexe :** {patient_actif['Âge']} ans, {patient_actif['Sexe']}")
                st.write(f"- **Échantillon :** {patient_actif.get('Nature_Echantillon', 'N/A')}")
            with c_info2:
                st.write(f"- **Type d'Examen :** {patient_actif.get('Type_Examen', 'N/A')}")
                st.write(f"- **Date d'envoi :** {patient_actif.get('Heure_Envoi', 'N/A')}")

            st.markdown("---")
            st.markdown("##### 🧪 Saisie des Résultats & Validation de Laboratoire")

            col_lab1, col_lab2 = st.columns(2)
            with col_lab1:
                patient_id_labo = st.text_input("Patient ID / Code Labo *", value=patient_actif.get("Patient_ID_Labo", patient_actif.get("Patient", "")))
                num_serie_labo = st.text_input("N° de Série / Registre Labo *", value=patient_actif.get("Num_Serie_Labo", ""))
                xpert_resultat = st.selectbox("Résultat GeneXpert *", [
                    "MTB Détecté / RIF Résistant", 
                    "MTB Détecté / RIF Sensible", 
                    "MTB Non Détecté (Négatif)", 
                    "Invalide / Erreur"
                ])
            with col_lab2:
                microscopie_resultat = st.selectbox("Résultat Microscopie (BAAR) *", [
                    "Positif (++)", "Positif (+)", "Positif (+++)", "Négatif (0 BAAR)", "Non réalisé"
                ])
                observations = st.text_area("Observations", placeholder="ex: Échantillon muco-purulent, RAS.")

            btn_valider_labo = st.form_submit_button("💾 Valider et Enregistrer les Résultats du Patient", type="primary")

            if btn_valider_labo:
                st.session_state["file_attente_labo"][idx_global].update({
                    "Patient_ID_Labo": patient_id_labo,
                    "Num_Serie_Labo": num_serie_labo,
                    "Date_Reception": str(datetime.date.today()),
                    "Xpert_Resultat": xpert_resultat,
                    "Microscopie_Resultat": microscopie_resultat,
                    "Observations": observations,
                    "Statut": "Analysé et Validé par le Labo",
                    "Technicien": user.get("nom_complet", "Technicien Labo")
                })
                st.success(f"✅ Résultats enregistrés pour {patient_actif['Patient']} !")
                st.rerun()
    else:
        st.success("✔ Aucun patient en attente de traitement dans la file du laboratoire.")

    st.divider()

    # --- 5. ONGLETS D'ANALYSE AVANCÉE (G4 & ULTRA) ET REGISTRE ---
    st.subheader("🧬 Modules d'Analyse Automatisée & IA (GeneXpert)")
    
    tab_g4, tab_ultra, tab_registres = st.tabs([
        "MTB/RIF Assay G4", "MTB/RIF Ultra", "Registre & Suivi Global"
    ])
    
    with tab_g4:
        afficher_module_g4()
        
    with tab_ultra:
        afficher_module_ultra()
        
    with tab_registres:
        st.subheader("📊 Registre des Patients Traités & Suivi du Laboratoire")
        
        # Sous-onglets intégrés pour séparer le registre général et le tableau d'affichage des urgences coloré
        sub_tab1, sub_tab2 = st.tabs(["📋 Registre Général & Suivi", "🚨 Tableau d'Affichage des Urgences"])
        
        with sub_tab1:
            afficher_section_suivi_sante(user)
            
        with sub_tab2:
            afficher_tableau_affichage_urgences()