# auth.py
import streamlit as st
import os
from config import supabase, LOGO_PATH, ROLES_LIST

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

def afficher_page_accueil():
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=130)
        else:
            st.write("🧬")
    with col_title:
        st.title("Stone IA — Socle de Technologie d'Observation Nationale et d'Exploitation des données")
        st.subheader("Votre Système d'analyse, d'extraction , d'exploitation et de structuration de traçabilité des données issues des platformes GeneXpert")

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