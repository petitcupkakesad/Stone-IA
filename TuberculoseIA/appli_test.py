# app.py
import streamlit as st
import pandas as pd
import numpy as np
import datetime
import os
import tempfile
import plotly.express as px
from supabase import create_client, Client
import io
import re

# Imports des modules de parsing et d'inférence validés
from csv_parser import parser_rapport_genexpert
from inference_stone_ia import charger_modele_et_scaler, predire_echantillon

# Imports des modules annexes du projet
try:
    from main import (
        lire_fichier_gxx,
        extraire_blocs_patients,
        parser_bloc_patient
    )
except ImportError:
    pass

try:
    from section4_5_bloc4 import (
        traiter_section4_vih_qual,
        traiter_section5_hpv
    )
except ImportError:
    pass

try:
    from bloc5_export import generer_excel_final
except ImportError:
    pass

LOGO_PATH = "Logo.png"
MODELE_PATH = "modeles/stone_g4_model.pt"

# Dictionnaire explicatif des 4 classes
CLASSES_DICT = {
    0: ("🟢 Négatif", "MTB Non Détecté"),
    1: ("🟡 Positif Sensible", "MTB Détecté - Sensible à la Rifampicine"),
    2: ("🔴 Positif Résistant", "MTB Détecté - Résistant à la Rifampicine"),
    3: ("⚪ Erreur / Invalide", "Résultat Invalide ou Erreur Technique")
}

ROLES_LIST = [
    "Personnel de santé",
    "Technicien de laboratoire",
    "Ingénieur de laboratoire",
    "Docteur",
    "Professeur titulaire"
]

# ---------------------------------------------------------
# 1. Configuration & Supabase
# ---------------------------------------------------------
st.set_page_config(
    page_title="Stone IA - Système Tuberculose & Diagnostic",
    page_icon="🧬",
    layout="wide"
)

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    supabase = None

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = {}
if "file_attente_labo" not in st.session_state:
    st.session_state["file_attente_labo"] = []

# Chargement du modèle PyTorch mis en cache
@st.cache_resource
def initialiser_ia():
    if not os.path.exists(MODELE_PATH):
        raise FileNotFoundError(f"Fichier modèle introuvable : {MODELE_PATH}")
    return charger_modele_et_scaler(MODELE_PATH)

# ---------------------------------------------------------
# 2. Authentification & Profils
# ---------------------------------------------------------
def charger_profil_utilisateur(user_id, email, profession_secours="Personnel de santé", service_secours="Pneumologie", docteur_secours="Dr. Non renseigné"):
    if not supabase:
        st.session_state["user_info"] = {
            "id": user_id,
            "nom_complet": email.split('@')[0].capitalize(),
            "profession": profession_secours,
            "profession_titulaire": profession_secours,
            "service": service_secours,
            "docteur_referent": docteur_secours,
            "email": email
        }
        st.session_state["authenticated"] = True
        return

    try:
        res = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if res.data:
            data = res.data[0]
            st.session_state["user_info"] = {
                "id": user_id,
                "nom_complet": f"{data.get('prenom', '')} {data.get('nom', '')}".strip() or email,
                "profession": data.get("profession", profession_secours),
                "profession_titulaire": data.get("profession", profession_secours),
                "service": data.get("service", service_secours),
                "docteur_referent": data.get("docteur_referent", docteur_secours),
                "email": email
            }
        else:
            st.session_state["user_info"] = {
                "id": user_id,
                "nom_complet": email,
                "profession": profession_secours,
                "profession_titulaire": profession_secours,
                "service": service_secours,
                "docteur_referent": docteur_secours,
                "email": email
            }
        st.session_state["authenticated"] = True
    except Exception as e:
        st.error(f"Erreur lors du chargement du profil : {e}")

# ---------------------------------------------------------
# 3. PAGE D'ACCUEIL (Connexion & Inscription)
# ---------------------------------------------------------
def afficher_page_accueil():
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=130)
        else:
            st.write("🧬")
    with col_title:
        st.title("Stone IA — Socle de Technologie d'Observation Nationale et d'Epidémiosurveillance")
        st.subheader("Votre Système d'analyse et de traçabilité des données Epidémiologiques de la Tuberculose et des diagnostics associés")

    st.write("Veuillez vous identifier pour accéder à la plateforme.")
    st.divider()

    tab_login, tab_signup = st.tabs(["🔐 Se connecter", "📝 S'inscrire"])

    with tab_login:
        st.write("### Connexion à votre compte")
        if st.button("🌐 Se connecter avec Google", key="login_google"):
            if supabase:
                try:
                    supabase.auth.sign_in_with_oauth({"provider": "google"})
                except Exception as e:
                    st.error(f"Erreur : {e}")
            else:
                charger_profil_utilisateur("google_demo", "agent.sante@lnsp.ga", "Personnel de santé", "Pneumologie")
                st.rerun()

        st.markdown("**OU avec votre adresse e-mail :**")
        email_log = st.text_input("Adresse e-mail", key="log_email")
        password_log = st.text_input("Mot de passe", type="password", key="log_pass")

        if st.button("Connexion", type="primary"):
            if email_log and password_log:
                if supabase:
                    try:
                        res = supabase.auth.sign_in_with_password({
                            "email": email_log,
                            "password": password_log
                        })
                        charger_profil_utilisateur(res.user.id, res.user.email)
                        st.success("Connexion réussie !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Échec de connexion : {e}")
                else:
                    charger_profil_utilisateur("local_id", email_log)
                    st.rerun()
            else:
                st.error("Veuillez remplir tous les champs.")

    with tab_signup:
        st.write("### Créer un nouveau compte")
        with st.form("form_inscription"):
            col_a, col_b = st.columns(2)
            with col_a:
                prenom = st.text_input("Prénom *")
                nom = st.text_input("Nom *")
                email = st.text_input("Adresse e-mail *")
                service_demande = st.text_input("Service d'affectation / demandeur *", value="Pneumologie", help="Ex: Pneumologie, Urgences")
            with col_b:
                profession = st.selectbox("Profession / Rôle *", ROLES_LIST)
                docteur_ref = st.text_input("Nom / ID du Docteur référent", placeholder="ex: Dr. ALAME-EMANE / ID-04")
                password = st.text_input("Créer un mot de passe *", type="password")
                password_confirm = st.text_input("Confirmer le mot de passe *", type="password")

            btn_sinscrire = st.form_submit_button("Créer mon compte", type="primary")

            if btn_sinscrire:
                if not (prenom and nom and email and password and service_demande):
                    st.error("Veuillez remplir tous les champs requis (*).")
                elif password != password_confirm:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    if supabase:
                        try:
                            res = supabase.auth.sign_up({
                                "email": email,
                                "password": password,
                                "options": {
                                    "data": {
                                        "nom": nom,
                                        "prenom": prenom,
                                        "profession": profession,
                                        "service": service_demande,
                                        "docteur_referent": docteur_ref
                                    }
                                }
                            })
                            st.success("Compte créé avec succès !")
                            if res.user:
                                charger_profil_utilisateur(res.user.id, email, profession, service_demande, docteur_ref)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erreur lors de la création du compte : {e}")
                    else:
                        charger_profil_utilisateur("local_id", email, profession, service_demande, docteur_ref)
                        st.success("Compte créé en mode local !")
                        st.rerun()

# ---------------------------------------------------------
# 4. DASHBOARD & TABLEAUX
# ---------------------------------------------------------
def afficher_tableau_labo(df, hauteur=450):
    html = df.to_html(classes="styled-table", index=False)
    st.markdown(
        f"""
        <div style="max-height: {hauteur}px; overflow-y: auto; border: 1px solid #333; border-radius: 6px; margin-bottom: 1em;">
            <style>
                .styled-table {{ width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; }}
                .styled-table th {{ position: sticky; top: 0; background-color: #1e2029; color: white; padding: 10px; text-align: left; z-index: 1; }}
                .styled-table td {{ padding: 8px 10px; border-bottom: 1px solid #333; white-space: nowrap; }}
                .styled-table tr:nth-child(even) {{ background-color: #161821; }}
            </style>
            {html}
        </div>
        """,
        unsafe_allow_html=True
    )

def afficher_dashboard_registres():
    st.header("Tableau de Bord & Registres Tuberculose")
    
    if not supabase:
        st.warning("⚠️ Supabase n'est pas configuré. Impossible d'afficher les registres en ligne.")
        return

    tables_registres = {
        "Registre TB 2023 (public.registre_tb_2023)": "registre_tb_2023",
        "Registre TB Historique (public.registre_tb)": "registre_tb",
        "Patients / Fiches Cliniques (public.patients)": "patients"
    }

    col_table, col_ref = st.columns([3, 1])
    with col_table:
        choix_label = st.selectbox("Sélectionner la table de registre à charger :", options=list(tables_registres.keys()))
        nom_table = tables_registres[choix_label]
    with col_ref:
        st.write("")
        st.write("")

    with st.spinner(f"Chargement des données API de `{nom_table}`..."):
        try:
            response = supabase.table(nom_table).select("*").execute()
            df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        except Exception as e:
            st.error(f"Erreur d'accès à l'API Supabase pour la table `{nom_table}` : {e}")
            df = pd.DataFrame()

    if df.empty:
        st.warning(f"La table `{nom_table}` ne contient aucune donnée ou est inaccessible.")
        return

    st.markdown("---")
    st.subheader("Indicateurs Clés")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Patients Registrés", len(df))

    if "sexe" in df.columns:
        df["sexe_clean"] = df["sexe"].astype(str).str.upper().str.strip()
        nb_hommes = len(df[df["sexe_clean"].isin(["M", "MASCULIN", "HOMME"])])
        nb_femmes = len(df[df["sexe_clean"].isin(["F", "FEMININ", "FEMME"])])
        kpi2.metric("Hommes (M)", nb_hommes)
        kpi3.metric("Femmes (F)", nb_femmes)
        ratio = round(nb_hommes / nb_femmes, 2) if nb_femmes > 0 else 0
        kpi4.metric("Ratio H/F", ratio)

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        if "sexe" in df.columns:
            fig_sexe = px.pie(df, names="sexe", title="Répartition par Sexe (M/F)", hole=0.4)
            st.plotly_chart(fig_sexe, use_container_width=True)

    with col_chart2:
        if "age" in df.columns and df["age"].notna().any():
            df["age_num"] = pd.to_numeric(df["age"], errors='coerce')
            fig_age = px.histogram(
                df, x="age_num", nbins=15, title="Distribution par Tranche d'Âge",
                labels={"age_num": "Âge (ans)", "count": "Nombre"},
                color_discrete_sequence=["#17a2b8"]
            )
            st.plotly_chart(fig_age, use_container_width=True)

    st.markdown("---")
    afficher_tableau_labo(df, hauteur=450)

# ---------------------------------------------------------
# 5. VUE DÉDIÉE : PERSONNEL DE SANTÉ
# ---------------------------------------------------------
def afficher_vue_personnel_sante(user_info):
    st.header("🟢 Espace Personnel de Santé — Admission & Transmission")
    st.caption("Mission : Enregistrement rigoureux des patients sans erreur de saisie et transmission directe au laboratoire avant examen.")

    df_attente = pd.DataFrame(st.session_state.get("file_attente_labo", []))
    col1, col2, col3 = st.columns(3)
    total_service = len(df_attente[df_attente["Service"] == user_info.get("service")]) if not df_attente.empty else 0
    col1.metric("Patients admis (Mon service)", total_service)
    col2.metric("Transmis au Labo", len(df_attente) if not df_attente.empty else 0)
    col3.metric("Statut Laboratoire", "Connecté 🟢")

    st.divider()
    st.subheader("📝 Fiche Clinique et Administrative du Patient")

    with st.form("form_admission_sante", clear_on_submit=True):
        col_l1_a, col_l1_b = st.columns(2)
        with col_l1_a:
            nom_du_laboratoire = st.text_input("Nom du Laboratoire *", placeholder="ex: LAB-2026-089")
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
            if not (nom_du_laboratoire and nom_patient and structure_adressante and docteur_referent):
                st.error("❌ Veuillez remplir tous les champs obligatoires (*).")
            else:
                nouveau_patient = {
                    "ID_Transmission": f"TR-{len(st.session_state['file_attente_labo']) + 101}",
                    "nom_du_laboratoire": nom_du_laboratoire,
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
                    "Heure_Envoi": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state["file_attente_labo"].append(nouveau_patient)
                st.success("✅ Fiche patient enregistrée et transmise avec succès au laboratoire !")
                st.balloons()

    st.divider()
    st.subheader("📋 Registre des admissions de mon service & Sauvegardes")
    if not df_attente.empty:
        df_service = df_attente[df_attente["Service"] == user_info.get("service")] if "Service" in df_attente.columns else df_attente
        st.dataframe(df_service, use_container_width=True)

        col_exp1, col_exp2 = st.columns(2)
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
            df_service.to_excel(writer, sheet_name="Registre_Service", index=False)
        col_exp1.download_button(
            label="💾 Sauvegarder le registre du service (.xlsx)",
            data=buffer_excel.getvalue(),
            file_name=f"Registre_{user_info.get('service')}_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        csv_data = df_service.to_csv(index=False).encode('utf-8')
        col_exp2.download_button(
            label="💾 Sauvegarder au format CSV (.csv)",
            data=csv_data,
            file_name=f"Registre_{user_info.get('service')}_{datetime.date.today()}.csv",
            mime="text/csv"
        )

# ---------------------------------------------------------
# 6. APPLICATION PRINCIPALE & ONGLETS (Technicien, Ingénieur, Docteur, Professeur)
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
    st.sidebar.title("🤖 Statut Stone IA")
    
    try:
        model, scaler_mean, scaler_scale, features_list = initialiser_ia()
        st.sidebar.success("Modèle Stone IA G4 opérationnel ✔")
    except Exception as e:
        st.sidebar.error(f"❌ Erreur modèle PyTorch : {e}")
        model = None

    # Sélecteur de rôle interactif pour la démonstration
    st.sidebar.markdown("---")
    role_actif = st.sidebar.selectbox("Changer de vue active :", ROLES_LIST, index=ROLES_LIST.index(profession) if profession in ROLES_LIST else 0)

    if st.sidebar.button("🚪 Se déconnecter"):
        if supabase:
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
        st.session_state["authenticated"] = False
        st.session_state["user_info"] = {}
        st.rerun()

    # Si le rôle actif est Personnel de santé, on affiche sa vue dédiée
    if role_actif == "Personnel de santé":
        afficher_vue_personnel_sante(user)
        return

    # Pour les autres rôles -> Accès aux 4 onglets complets
    st.title(f"🧬 Stone IA — Espace {role_actif}")
    st.divider()

    # --- SECTION INTERACTIVE DU TECHNICIEN DE LABORATOIRE ---
    if role_actif == "Technicien de laboratoire":
        file_attente = st.session_state.get("file_attente_labo", [])
        nb_en_attente = len(file_attente)

        st.subheader("📥 File d'attente des patients transmis (Personnel de Santé)")
        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("Patients en attente au Labo", nb_en_attente)
        col_t2.metric("Statut Automate GeneXpert", "Opérationnel 🟢")
        col_t3.metric("Connexion Labo", "En ligne 🟢")

        if nb_en_attente > 0:
            st.warning(f"🔔 **{nb_en_attente} patient(s) reçu(s)** en attente de validation technique !")
            noms_patients = [f"{p['Patient']} (ID: {p['ID_Transmission']} - Service: {p['Service']})" for p in file_attente]
            choix_patient_str = st.selectbox("Sélectionner un patient dans la file d'attente à traiter :", noms_patients, key="sel_patient_labo")
            
            idx_selection = noms_patients.index(choix_patient_str)
            patient_actif = file_attente[idx_selection]

            with st.form(f"form_labo_{patient_actif['ID_Transmission']}", clear_on_submit=False):
                st.markdown(f"#### Traitement du dossier : **{patient_actif['Patient']}** (Transmis par {patient_actif['Service']}, Réf: {patient_actif['Docteur']})")
                
                c_info1, c_info2 = st.columns(2)
                with c_info1:
                    st.write(f"- **Âge / Sexe :** {patient_actif['Âge']} ans, {patient_actif['Sexe']}")
                    st.write(f"- **Échantillon :** {patient_actif['Nature_Echantillon']}")
                    st.write(f"- **Infection VIH :** {patient_actif['Infection_VIH']}")
                with c_info2:
                    st.write(f"- **TB Antérieur :** {patient_actif['TB_Anterieur']}")
                    st.write(f"- **Type d'Examen :** {patient_actif['Type_Examen']} ({patient_actif['Suivi_Mois']})")
                    st.write(f"- **Date d'envoi :** {patient_actif.get('Heure_Envoi', 'N/A')}")

                st.markdown("---")
                st.markdown("##### 🧪 Saisie des Résultats & Validation de Laboratoire")

                col_lab1, col_lab2 = st.columns(2)
                with col_lab1:
                    num_serie_labo = st.text_input("N° de Série / Registre Labo *", value=patient_actif.get("Num_Serie_Labo", ""))
                    date_reception = st.date_input("Date de réception au Labo *", value=datetime.date.today())
                    xpert_resultat = st.selectbox("Résultat GeneXpert (Xpert) *", [
                        "MTB Détecté / RIF Résistant", 
                        "MTB Détecté / RIF Sensible", 
                        "MTB Non Détecté (Négatif)", 
                        "Invalide / Erreur"
                    ])
                with col_lab2:
                    microscopie_resultat = st.selectbox("Résultat Microscopie (BAAR) *", [
                        "Positif (++)", "Positif (+)", "Positif (+++)", "Négatif (0 BAAR)", "Non réalisé"
                    ])
                    observations = st.text_area("Observations / Remarques du Technicien", placeholder="ex: Échantillon muco-purulent, RAS.")

                btn_valider_labo = st.form_submit_button("💾 Valider et Enregistrer les Résultats du Patient", type="primary")

                if btn_valider_labo:
                    st.session_state["file_attente_labo"][idx_selection].update({
                        "Num_Serie_Labo": num_serie_labo,
                        "Date_Reception": str(date_reception),
                        "Xpert_Resultat": xpert_resultat,
                        "Microscopie_Resultat": microscopie_resultat,
                        "Observations": observations,
                        "Statut": "Analysé et Validé par le Labo",
                        "Technicien": user.get("nom_complet", "Technicien Labo")
                    })
                    st.success(f"✅ Résultats de laboratoire enregistrés pour le patient {patient_actif['Patient']} !")
                    st.rerun()
        else:
            st.success("✔ Aucun patient en attente dans la file de transmission du Personnel de Santé.")
        st.divider()

    tab_formulaire, tab_g4, tab_ultra, tab_vih, tab_registres = st.tabs([
        "Fiche Patient",
        "MTB/RIF Assay G4", 
        "MTB/RIF Ultra", 
        "VIH / HPV / Autres",
        "Registre & Dashboard"
    ])

    with tab_formulaire:
        st.header("1. Fiche Clinique et Administrative du Patient")
        dict_echantillons = {
            "Formes intra-pulmonaires": ["Crachats / expectorations", "Tubage gastrique", "Expectoration induite", "Autre"],
            "Formes extra-pulmonaires": ["Urines", "Liquides biologiques", "Biopsies / Tissus", "Sang et Moelle osseuse", "Autre"]
        }

        col_forme, col_echantillon = st.columns(2)
        with col_forme:
            forme_tb = st.selectbox("Forme de la Tuberculose", options=list(dict_echantillons.keys()))
        with col_echantillon:
            nature_echantillon = st.selectbox("Nature de l'échantillon", options=dict_echantillons[forme_tb])

        with st.form("form_tuberculose"):
            col1, col2 = st.columns(2)
            with col1:
                nom_patient = st.text_input("Nom & Prénom / ID Patient")
                sexe = st.selectbox("Sexe", ["Masculin", "Féminin"])
                date_reception = st.date_input("Date de réception", value=datetime.date.today())
            with col2:
                adresse = st.text_input("Adresse")
                telephone = st.text_input("Téléphone")
                nom_adressant = st.text_input("Structure adressante")

            submitted = st.form_submit_button("Enregistrer la fiche patient", type="primary")
            if submitted:
                st.success("Fiche patient enregistrée avec succès.")

    with tab_g4:
        st.header("🔬 Module Expert - MTB/RIF Assay G4 (Stone IA)")
        st.markdown("Importez n'importe quel rapport GeneXpert (CSV ou Excel) pour exécuter l'inférence dynamique du réseau de neurones Stone IA (4 Classes).")
        
        fichier_charge = st.file_uploader(
            "Glissez-déposez un fichier CSV ou Excel (.csv / .xlsx)",
            type=["csv", "xlsx", "txt"],
            key="up_g4_dyn"
        )

        if fichier_charge is not None:
            try:
                if fichier_charge.name.endswith('.csv') or fichier_charge.name.endswith('.txt'):
                    try:
                        df_brut = pd.read_csv(fichier_charge, encoding="utf-8")
                    except UnicodeDecodeError:
                        df_brut = pd.read_csv(fichier_charge, encoding="latin1")
                else:
                    df_brut = pd.read_excel(fichier_charge)

                st.info(f"📄 Fichier **{fichier_charge.name}** chargé ({len(df_brut)} lignes brutes).")

                resultats_parsed = parser_rapport_genexpert(df_brut)
                st.success(f"✔ {len(resultats_parsed)} échantillons analysés et structurés par le parser.")

                if st.button("🚀 Lancer l'Analyse d'Inférence du fichier à Stone", type="primary", key="btn_run_g4_dyn"):
                    try:
                        model_net, s_mean, s_scale, _ = initialiser_ia()
                        
                        with st.spinner("Exécution du réseau de neurones StoneG4Net..."):
                            predictions_df = []
                            for item in resultats_parsed:
                                val_ct = item['valeurs_ct']
                                classe_pred, confiance = predire_echantillon(model_net, s_mean, s_scale, val_ct)
                                
                                nom_classe, desc_classe = CLASSES_DICT[classe_pred]
                                nom_label_reel, _ = CLASSES_DICT.get(item['label_reel'], ("Inconnu", ""))

                                predictions_df.append({
                                    "Échantillon": item['sample_id'],
                                    "Patient ID": item['patient_id'],
                                    "Probe A": val_ct[0],
                                    "Probe B": val_ct[1],
                                    "Probe C": val_ct[2],
                                    "Probe D": val_ct[3],
                                    "Probe E": val_ct[4],
                                    "SPC": val_ct[5],
                                    "Prédiction IA": nom_classe,
                                    "Confiance IA": f"{confiance:.2f}%",
                                    "Résultat Instrument (Parser)": nom_label_reel
                                })

                            df_res_final = pd.DataFrame(predictions_df)
                            st.session_state["df_ia_res_g4"] = df_res_final

                        st.toast("Inférence réalisée avec succès !", icon="✅")
                    except Exception as err_model:
                        st.error(f"❌ Impossible d'exécuter le modèle ({MODELE_PATH}) : {err_model}")

            except Exception as e:
                st.error(f"❌ Erreur lors du traitement du fichier : {e}")

        if "df_ia_res_g4" in st.session_state and not st.session_state["df_ia_res_g4"].empty:
            df_res = st.session_state["df_ia_res_g4"]
            
            st.divider()
            st.subheader("📊 Résultats Globaux de la Prédiction de Stone")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Patient", len(df_res))
            m2.metric("Négatifs", sum(df_res["Prédiction IA"].str.contains("Négatif")))
            m3.metric("Sensibles", sum(df_res["Prédiction IA"].str.contains("Sensible")))
            m4.metric("Résistants", sum(df_res["Prédiction IA"].str.contains("Résistant")))

            st.subheader("📋 Tableau Détaillé des Inférences")
            afficher_tableau_labo(df_res, hauteur=400)

            csv_data = df_res.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Télécharger les Résultats d'Inférence (CSV)",
                data=csv_data,
                file_name="predictions_stone_ia_g4.csv",
                mime="text/csv",
                type="primary"
            )
            
    with tab_ultra:
        st.header("🔬 Module Expert - MTB/RIF Ultra")
        st.file_uploader("Fichiers Ultra (.gxx / .csv)", type=["gxx", "csv"], key="up_ultra")

    with tab_vih:
        st.header("🔬 Module - VIH / HPV / Autres")
        st.file_uploader("Fichiers VIH / HPV (.gxx / .csv)", type=["gxx", "csv"], key="up_vih")

    with tab_registres:
        afficher_dashboard_registres()

# ---------------------------------------------------------
# 7. AIGUILLAGE GLOBAL
# ---------------------------------------------------------
if not st.session_state.get("authenticated", False):
    afficher_page_accueil()
else:
    afficher_application_principale()