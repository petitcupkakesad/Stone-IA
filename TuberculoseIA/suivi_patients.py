# suivi_patients.py
import streamlit as st
import pandas as pd
import datetime
import io
from dashboard import afficher_tableau_labo

def afficher_section_suivi_sante(user_info):
    """
    Affiche la vue de suivi des patients côté Personnel de Santé,
    en différenciant les patients en attente et les patients traités par le laboratoire.
    """
    file_attente = st.session_state.get("file_attente_labo", [])
    
    if not file_attente:
        st.info("ℹ️ Aucun patient n'a encore été enregistré ou transmis aujourd'hui.")
        return

    df_global = pd.DataFrame(file_attente)

    # Filtrer les patients du service connecté
    service_user = user_info.get("service", "Pneumologie")
    if "Service" in df_global.columns:
        df_service = df_global[df_global["Service"] == service_user]
    else:
        df_service = df_global

    if df_service.empty:
        st.info(f"ℹ️ Aucun patient enregistré pour le service **{service_user}**.")
        return

    # Séparation selon le statut
    patients_en_attente = df_service[df_service["Statut"] == "En attente d'examen Labo"]
    patients_traites = df_service[df_service["Statut"] == "Analysé et Validé par le Labo"]

    # KPIs Dynamiques pour le Personnel de Santé
    st.subheader("📊 État d'avancement des examens de mon service")
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    kpi_col1.metric("Total Patients Admis", len(df_service))
    kpi_col2.metric("En attente au Labo ⏳", len(patients_en_attente))
    kpi_col3.metric("Patients Traités (Résultats disponibles) 🟢", len(patients_traites))

    st.divider()

    # Alerte de notification si des résultats sont prêts
    if len(patients_traites) > 0:
        st.success(f"✅ **{len(patients_traites)} patient(s)** de votre service ont été analysés par le laboratoire. Les résultats complets sont disponibles ci-dessous !")

    # Notification s'il y a des patients encore en cours de traitement
    if len(patients_en_attente) > 0:
        st.info(f"⏳ **{len(patients_en_attente)} patient(s)** sont actuellement en file d'attente auprès du Technicien de Laboratoire.")

    # Tableau Complet des Résultats
    st.subheader("📋 Registre Synthétique & Suivi Complet des Patients")
    
    # Réorganisation des colonnes clés pour un affichage lisible
    colonnes_affichage = [
        "ID_Transmission", "Num_Serie_Labo", "Date_Reception", "Patient", "Sexe", "Âge", 
        "Service", "Docteur", "Nature_Echantillon", "Infection_VIH", "TB_Anterieur", 
        "Type_Examen", "Suivi_Mois", "Statut", "Xpert_Resultat", "Microscopie_Resultat", "Observations"
    ]
    
    # S'assurer de ne sélectionner que les colonnes existantes dans le DataFrame
    cols_existantes = [col for col in colonnes_affichage if col in df_service.columns]
    df_affichage = df_service[cols_existantes].copy()

    # Stylisation du statut dans le tableau
    if "Statut" in df_affichage.columns:
        df_affichage["Statut"] = df_affichage["Statut"].apply(
            lambda x: "🟢 Résultat Disponible" if x == "Analysé et Validé par le Labo" else "⏳ En Attente Labo"
        )

    afficher_tableau_labo(df_affichage, hauteur=450)

    # Boutons d'exportation du registre consolidé
    st.subheader("💾 Exportation du Registre du Service")
    col_exp1, col_exp2 = st.columns(2)

    # Export Excel
    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
        df_affichage.to_excel(writer, sheet_name="Registre_Complet", index=False)
    col_exp1.download_button(
        label="📥 Télécharger le Registre Complet (.xlsx)",
        data=buffer_excel.getvalue(),
        file_name=f"Registre_Complet_{service_user}_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Export CSV
    csv_data = df_affichage.to_csv(index=False).encode('utf-8')
    col_exp2.download_button(
        label="📥 Télécharger le Registre au format CSV (.csv)",
        data=csv_data,
        file_name=f"Registre_Complet_{service_user}_{datetime.date.today()}.csv",
        mime="text/csv"
    )