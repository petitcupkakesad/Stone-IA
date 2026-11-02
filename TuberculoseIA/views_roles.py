# views_roles.py
import streamlit as st
import pandas as pd
import datetime
import io
import re
from csv_parser import parser_rapport_genexpert
from inference_stone_ia import predire_echantillon
# Import des fonctions d'inférence Ultra créées dans inference_stone_ia.py
from inference_stone_ia import (
    charger_modele_et_scaler_ultra, 
    predire_echantillon_ultra, 
    CLASSES_ULTRA_LABELS
)

CLASSES_DICT = {
    0: ("🟢 Négatif", "MTB Non Détecté"),
    1: ("🟡 Positif Sensible", "MTB Détecté - Sensible à la Rifampicine"),
    2: ("🔴 Positif Résistant", "MTB Détecté - Résistant à la Rifampicine"),
    3: ("⚪ Erreur / Invalide", "Résultat Invalide ou Erreur Technique")
}

# ---------------------------------------------------------
# VUE 1 : PERSONNEL DE SANTÉ
# ---------------------------------------------------------
def afficher_vue_personnel_sante(user_info):
    st.header("🟢 Espace Personnel de Santé — Admission & Transmission")
    st.caption("Mission : Enregistrement rigoureux des patients sans erreur de saisie et transmission directe au laboratoire.")

    df_attente = pd.DataFrame(st.session_state.get("file_attente_labo", []))
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    
    total_service = len(df_attente[df_attente["Service"] == user_info.get("service")]) if not df_attente.empty else 0
    transmis_labo = len(df_attente) if not df_attente.empty else 0

    col_kpi1.metric("Patients admis (Mon service)", total_service)
    col_kpi2.metric("En attente d'examen au Labo", transmis_labo)
    col_kpi3.metric("Statut liaison Laboratoire", "En ligne 🟢")

    st.divider()

    st.subheader("📝 Nouvelle Fiche Patient & Demande d'Examen GeneXpert")
    
    with st.form("form_admission_sante", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nom_patient = st.text_input("Nom & Prénom / ID Patient *", placeholder="ex: KOUKOUBA Marcel / ID-884")
            sexe = st.selectbox("Sexe *", ["Masculin", "Féminin"])
            age = st.number_input("Âge (ans) *", min_value=0, max_value=120, value=35)
            nature_echantillon = st.selectbox("Type d'échantillon", [
                "Crachats / Expectorations", "Tubage gastrique", "Expectoration induite", 
                "Liquide pleural", "Liquide céphalo-rachidien", "Autre"
            ])

        with col2:
            service_demandeur = st.text_input("Nom du service récepteur / demandeur *", value=user_info.get("service", "Pneumologie"))
            docteur_referent = st.text_input("Docteur référent (Nom / ID) *", value=user_info.get("docteur_referent", "Dr. ALAME-EMANE"))
            priorite = st.selectbox("Degré d'urgence", ["Normal", "Urgent 🔴", "STAT / Réanimation ⚡"])
            remarques = st.text_area("Remarques cliniques / Symptômes", placeholder="ex: Toux persistante depuis 3 semaines, sueurs nocturnes.")

        btn_envoyer = st.form_submit_button("🚀 Enregistrer & Envoyer au Technicien de Laboratoire", type="primary")

        if btn_envoyer:
            if not (nom_patient and service_demandeur and docteur_referent):
                st.error("❌ Veuillez remplir tous les champs obligatoires (*).")
            else:
                nouveau_patient = {
                    "ID_Transmission": f"TR-{len(st.session_state['file_attente_labo']) + 101}",
                    "Patient": nom_patient,
                    "Sexe": sexe,
                    "Âge": age,
                    "Échantillon": nature_echantillon,
                    "Service": service_demandeur,
                    "Docteur": docteur_referent,
                    "Priorité": priorite,
                    "Remarques": remarques,
                    "Heure_Envoi": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Agent_Saisie": user_info.get("nom_complet", "Inconnu"),
                    "Statut": "En attente d'analyse"
                }

                st.session_state["file_attente_labo"].append(nouveau_patient)
                st.success(f"✅ Fiche transmise au Laboratoire ! (ID Transmission: {nouveau_patient['ID_Transmission']})")
                st.balloons()

    st.divider()

    st.subheader("📋 Registre des admissions & Sauvegarde de mon service")
    
    if not df_attente.empty:
        df_service = df_attente[df_attente["Service"] == user_info.get("service")] if "Service" in df_attente.columns else df_attente
        st.dataframe(df_service, use_container_width=True)

        col_exp1, col_exp2 = st.columns(2)
        
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
            df_service.to_excel(writer, sheet_name="Registre_Admissions", index=False)
        
        col_exp1.download_button(
            label="💾 Sauvegarder le Registre du Service (.xlsx)",
            data=buffer_excel.getvalue(),
            file_name=f"Registre_Tuberculose_{user_info.get('service')}_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        csv_data = df_service.to_csv(index=False).encode('utf-8')
        col_exp2.download_button(
            label="💾 Sauvegarder au format CSV (.csv)",
            data=csv_data,
            file_name=f"Registre_{user_info.get('service')}_{datetime.date.today()}.csv",
            mime="text/csv"
        )
    else:
        st.info("Aucun patient enregistré aujourd'hui dans ce service.")

# ---------------------------------------------------------
# VUE 2 : TECHNICIEN DE LABORATOIRE (AVEC G4 ET ULTRA)
# ---------------------------------------------------------
def afficher_vue_technicien_labo(user_info, model_ia_tuple):
    st.header("🟡 Espace Technicien de Laboratoire — Analyses GeneXpert (G4 & Ultra)")
    st.caption("Mission : Réception des patients et inférence IA automatisée sur automates GeneXpert.")

    nb_en_attente = len(st.session_state.get("file_attente_labo", []))
    if nb_en_attente > 0:
        st.warning(f"🔔 **{nb_en_attente} patient(s) reçu(s)** du Personnel de Santé en attente d'examen !")
        with st.expander("📥 Voir la file d'attente transmise", expanded=False):
            df_attente = pd.DataFrame(st.session_state["file_attente_labo"])
            st.dataframe(df_attente[["ID_Transmission", "Patient", "Sexe", "Âge", "Échantillon", "Service", "Docteur", "Priorité", "Heure_Envoi"]], use_container_width=True)
    else:
        st.success("✔ Aucun patient en attente dans la file de transmission instantanée.")

    st.divider()

    # --- ONGLETS EXPERTS G4 & ULTRA ---
    tab_g4, tab_ultra = st.tabs(["🔬 MTB/RIF Assay G4", "🔬 MTB/RIF Ultra"])

    # 1. MODULE G4
    with tab_g4:
        st.subheader("Importation & Analyse G4 (Sondes A à E)")
        fichier_g4 = st.file_uploader("Fichier G4 (.csv / .xlsx)", type=["csv", "xlsx", "txt"], key="up_g4_role")
        if fichier_g4 is not None:
            st.info(f"📄 Fichier G4 chargé : {fichier_g4.name}")
            # Inférence & affichage G4 déjà existant...



# =========================================================
# 2. MODULE ULTRA (MIS À JOUR AVEC L'IA & TABLEAU RICHE)
# =========================================================
def afficher_module_ultra(tab_ultra):
    with tab_ultra:
        st.subheader("Importation & Analyse Ultra (rpoB1-4, IS1081/6110, SPC)")
        fichier_ultra = st.file_uploader("Fichier Ultra (.csv / .xlsx)", type=["csv", "xlsx", "txt"], key="up_ultra_role")
        
        if fichier_ultra is not None:
            try:
                if fichier_ultra.name.endswith('.csv') or fichier_ultra.name.endswith('.txt'):
                    df_ultra = pd.read_csv(fichier_ultra, encoding="utf-8-sig")
                else:
                    df_ultra = pd.read_excel(fichier_ultra)

                st.success(f"📄 Fichier Ultra **{fichier_ultra.name}** chargé ({len(df_ultra)} lignes).")

                if st.button("🚀 Classifier & Analyser avec Stone IA Ultra", type="primary"):
                    # Chargement du modèle Ultra et du scaler
                    model_u, mean_u, scale_u, feats_u = charger_modele_et_scaler_ultra()
                    
                    if model_u is None:
                        st.error("❌ Modèle Ultra introuvable dans 'modeles/stone_ultra_model.pt'. Veuillez lancer l'entraînement d'abord.")
                        return

                    predictions_ultra = []
                    
                    # Itération ligne par ligne sur le fichier importé
                    for _, row in df_ultra.iterrows():
                        texte_ligne = " | ".join([str(row[c]) for c in row.index if pd.notna(row[c])]).upper()
                        
                        # Extraction dynamique des valeurs de Ct pour les 6 sondes Ultra
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

                        # Inférence IA Ultra
                        pred_class, confidence = predire_echantillon_ultra(model_u, mean_u, scale_u, valeurs_ct)
                        libelle_ia = CLASSES_ULTRA_LABELS.get(pred_class, "Inconnu")

                        # Copie de la ligne avec enrichissement des colonnes demandées
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
            st.subheader("📊 Résultats Inférence Stone IA (Module Ultra)")
            
            # Sélection rigoureuse des colonnes à afficher dans l'interface
            colonnes_prioritaires = [
                "Sample ID", 
                "Patient ID", 
                "rpoB1", "rpoB2", "rpoB3", "rpoB4",
                "IS1081-IS6110", 
                "SPC", 
                "Résultat IA Ultra", 
                "Prédiction Confiance", 
                "Test Result", 
                "System Name", 
                "Cartridge S/N", 
                "Instrument S/N", 
                "Reagent Lot ID", 
                "Expiration Date", 
                "Start Time"
            ]
            
            # Ne garder que les colonnes qui existent réellement dans le dataframe généré
            colonnes_a_afficher = [col for col in colonnes_prioritaires if col in df_res_u.columns]
            
            st.dataframe(df_res_u[colonnes_a_afficher], use_container_width=True)

# ---------------------------------------------------------
# AUTRES VUES À ENRICHIR (Prochaines étapes)
# ---------------------------------------------------------
def afficher_vue_ingenieur_labo(user_info):
    st.header("🟠 Espace Ingénieur de Laboratoire — Validabilité & Parc Automate")
    st.info("🛠️ Module Ingénieur : Analyse du taux d'erreur, état des sondes A-E/SPC et statut des diagnostics fiables/douteux.")

def afficher_vue_docteur(user_info):
    st.header("🔵 Espace Docteur — Consultation Synthétique & Recommandations Cliniques")
    st.info("🩺 Module Docteur : Résultats synthétiques patients, probabilités Stone IA et recommandations cliniques.")

def afficher_vue_professeur(user_info):
    st.header("🟣 Espace Professeur Titulaire — Surveillance Épidémiologique Nationale")
    st.info("📊 Module Professeur : Dashboard national, clusters de résistance RIF par région et exports globaux.")