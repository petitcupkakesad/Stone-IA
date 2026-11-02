# vue_sante.py
import streamlit as st
import pandas as pd
import datetime
from suivi_patients import afficher_section_suivi_sante

def afficher_vue_personnel_sante(user_info):
    st.header("🟢 Espace Personnel de Santé — Admission & Suivi des Examens")
    st.caption("Mission : Enregistrement des patients, transmission directe au laboratoire et consultation des résultats.")

    tab_admission, tab_suivi = st.tabs(["📝 Nouvelle Admission Patient", "📊 Patients Traités & Résultats Disponibles"])

    with tab_admission:
        st.subheader("📝 Fiche Clinique et Administrative du Patient")

        with st.form("form_admission_sante", clear_on_submit=True):
            col_l1_a, col_l1_b = st.columns(2)
            with col_l1_a:
                num_serie_labo = st.text_input("N° de Série / Registre Labo *", placeholder="ex: LAB-2026-089")
            with col_l1_b:
                date_reception = st.date_input("Date de réception *", value=datetime.date.today())

            col_l2_a, col_l2_b, col_l2_c = st.columns([2, 1, 1])
            with col_l2_a:
                nom_patient = st.text_input("Nom & Prénom / ID Patient *", placeholder="ex: KOUKOUBA Marcel")
            with col_l2_b:
                sexe = st.selectbox("Sexe *", ["Masculin", "Féminin"])
            with col_l2_c:
                age = st.number_input("Âge (ans) *", min_value=0, max_value=120, value=30)

            col_l3_a, col_l3_b, col_l3_c = st.columns(3)
            with col_l3_a:
                adresse = st.text_input("Adresse", placeholder="ex: Nkembo, Libreville")
            with col_l3_b:
                telephone = st.text_input("Téléphone", placeholder="ex: 077123456")
            with col_l3_c:
                structure_adressante = st.text_input("Structure adressante / Service demandeur *", value=user_info.get("service", "Pneumologie"))

            col_l4_a, col_l4_b, col_l4_c = st.columns(3)
            with col_l4_a:
                nature_echantillon = st.selectbox("Nature de l'échantillon *", [
                    "Crachats / Expectorations", "Tubage gastrique", "Expectoration induite",
                    "Liquide pleural", "Liquide céphalo-rachidien", "Biopsie / Tissu", "Autre"
                ])
            with col_l4_b:
                infection_vih = st.selectbox("Infection VIH *", ["Inconnu", "Négatif", "Positif", "En cours de dépistage"])
            with col_l4_c:
                tb_anterieur = st.selectbox("TB Antérieur (Antécédent) *", ["Non (Nouveau cas)", "Oui (Récidive)", "Oui (Échec)", "Oui (Perdu de vue)"])

            col_l5_a, col_l5_b, col_l5_c = st.columns(3)
            with col_l5_a:
                type_examen = st.selectbox("Type d'Examen *", ["Diagnostic initial", "Suivi sous traitement", "Contrôle de guérison"])
            with col_l5_b:
                suivi_mois = st.selectbox("Suivi (Mois) *", ["Non applicable (Diagnostic)", "M2", "M3", "M5", "M6", "M8", "Autre"])
            with col_l5_c:
                docteur_referent = st.text_input("Docteur référent (Nom / ID) *", value=user_info.get("docteur_referent", "Dr. ALAME-EMANE"))

            submitted = st.form_submit_button("🚀 Enregistrer & Envoyer au Technicien de Laboratoire", type="primary")

            if submitted:
                if not (num_serie_labo and nom_patient and structure_adressante and docteur_referent):
                    st.error("❌ Veuillez remplir tous les champs obligatoires (*).")
                else:
                    nouveau_patient = {
                        "ID_Transmission": f"TR-{len(st.session_state['file_attente_labo']) + 101}",
                        "Num_Serie_Labo": num_serie_labo,
                        "Date_Reception": str(date_reception),
                        "Patient": nom_patient,
                        "Sexe": sexe,
                        "Âge": age,
                        "Adresse": adresse,
                        "Téléphone": telephone,
                        "Service": structure_adressante,
                        "Nature_Echantillon": nature_echantillon,
                        "Infection_VIH": infection_vih,
                        "TB_Anterieur": tb_anterieur,
                        "Type_Examen": type_examen,
                        "Suivi_Mois": suivi_mois,
                        "Docteur": docteur_referent,
                        "Statut": "En attente d'examen Labo",
                        "Heure_Envoi": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Xpert_Resultat": "En attente",
                        "Microscopie_Resultat": "En attente",
                        "Observations": "En cours de traitement"
                    }
                    st.session_state["file_attente_labo"].append(nouveau_patient)
                    st.success("✅ Fiche patient enregistrée et transmise avec succès au laboratoire !")
                    st.balloons()

    with tab_suivi:
        afficher_section_suivi_sante(user_info)