import streamlit as st
import pandas as pd
import plotly.express as px

COULEURS_DIAG = {
    "Négatif": "#28a745",
    "Positif Sensible": "#ffc107",
    "Positif Résistant": "#dc3545",
    "Invalide / Erreur": "#6c757d",
    "Invalide": "#6c757d"
}

# Palette spécifique élargie pour les 8 classes du module Ultra
COULEURS_ULTRA = {
    "MTB Non Détecté": "#28a745",
    "MTB Détecté Très Bas | RIF Résistance Non Détecté": "#17a2b8",
    "MTB Détecté Très Bas | RIF Résistance Détecté / Indéterminé": "#ffc107",
    "MTB Détecté Bas | RIF Résistance Non Détecté / Indéterminé": "#ff851b",
    "MTB Détecté Moyen | RIF Résistance Non Détecté": "#b10dc9",
    "MTB Détecté Élevé | RIF Résistance Détecté / Non Détecté": "#dc3545",
    "MTB Trace Détecté | RIF Résistance Indéterminé": "#39cccc",
    "Erreur / Non Valide / Pas de Résultat": "#6c757d"
}

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

def afficher_dashboard_registres(supabase):
    st.header("Tableau de Bord & Registres Tuberculose")
    
    if not supabase:
        st.warning("⚠️ Supabase n'est pas configuré. Impossible d'afficher les registres en ligne.")
        return

    tables_registres = {
        "🔬 Inférences Stone IA G4 (public.analyses_g4)": "analyses_g4",
        "⚡ Inférences Stone IA Ultra (public.analyses_ultra)": "analyses_ultra",
        "Registre TB 2023 (public.registre_tb_2023)": "registre_tb_2023",
        "Registre TB Historique (public.registre_tb)": "registre_tb",
        "Patients / Fiches Cliniques (public.patients)": "patients"
    }

    col_table, col_ref = st.columns([3, 1])
    with col_table:
        choix_label = st.selectbox("Sélectionner la table de registre à charger :", options=list(tables_registres.keys()), key="select_table_registre")
        nom_table = tables_registres[choix_label]

    with st.spinner(f"Chargement complet de la table `{nom_table}`..."):
        try:
            if nom_table in ["analyses_g4", "analyses_ultra"]:
                # Récupération par pagination par blocs de 1000 pour contourner la limite de Supabase
                all_data = []
                batch_size = 1000
                start = 0
                while True:
                    response = supabase.table(nom_table).select("*").range(start, start + batch_size - 1).execute()
                    chunk = response.data if response.data else []
                    if not chunk:
                        break
                    all_data.extend(chunk)
                    if len(chunk) < batch_size:
                        break
                    start += batch_size
                df = pd.DataFrame(all_data)
            else:
                response = supabase.table(nom_table).select("*").execute()
                df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        except Exception as e:
            st.error(f"Erreur d'accès à l'API Supabase pour la table `{nom_table}` : {e}")
            df = pd.DataFrame()

    if df.empty:
        st.warning(f"La table `{nom_table}` ne contient aucune donnée ou est inaccessible.")
        return

    st.markdown("---")

    # --- TABLE SPÉCIFIQUE : ANALYSES G4 ---
    if nom_table == "analyses_g4":
        st.subheader("Filtres & Pilotage de l'Activité G4")
        
        if "created_at" in df.columns:
            df["created_at_dt"] = pd.to_datetime(df["created_at"], errors='coerce')
            df["date_jour"] = df["created_at_dt"].dt.date
        
        col_f1, col_f2 = st.columns(2)
        
        operateurs = ["Tous"] + list(df["utilisateur"].dropna().unique()) if "utilisateur" in df.columns else ["Tous"]
        op_choisi = col_f1.selectbox("Filtrer par Opérateur / Utilisateur", operateurs)
        if op_choisi != "Tous":
            df = df[df["utilisateur"] == op_choisi]

        if "created_at_dt" in df.columns and df["created_at_dt"].notna().any():
            min_date = df["created_at_dt"].min().date()
            max_date = df["created_at_dt"].max().date()
            plage_dates = col_f2.date_input("Filtrer par période", [min_date, max_date])
            if len(plage_dates) == 2:
                d_debut, d_fin = plage_dates
                df = df[(df["created_at_dt"].dt.date >= d_debut) & (df["created_at_dt"].dt.date <= d_fin)]

        st.markdown("---")
        st.subheader("Indicateurs Clés G4 (Total complet)")
        k1, k2, k3, k4, k5 = st.columns(5)
        
        total_analyses = len(df)
        k1.metric("Total Analyses", total_analyses)

        col_pred = "prediction_ia" if "prediction_ia" in df.columns else "Prédiction IA"
        if col_pred in df.columns:
            nb_neg = len(df[df[col_pred].str.contains("Négatif", case=False, na=False)])
            nb_sens = len(df[df[col_pred].str.contains("Sensible", case=False, na=False)])
            nb_res = len(df[df[col_pred].str.contains("Résistant", case=False, na=False)])
            
            k2.metric("🟢 Négatifs", nb_neg)
            k3.metric("🟡 Sensibles", nb_sens)
            k4.metric("🔴 Résistants", nb_res)
            
            taux_positivite = ((nb_sens + nb_res) / total_analyses * 100) if total_analyses > 0 else 0.0
            k5.metric("📈 Taux de Positivité", f"{taux_positivite:.1f}%")

        st.markdown("---")
        st.subheader("Visualisations & Évolution Temporelle")
        
        c_ch1, c_ch2 = st.columns(2)
        with c_ch1:
            if col_pred in df.columns:
                fig_pie = px.pie(
                    df, names=col_pred, title="Répartition Globale des Diagnostics IA", hole=0.4,
                    color=col_pred, color_discrete_map=COULEURS_DIAG
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with c_ch2:
            if "date_jour" in df.columns and not df["date_jour"].dropna().empty:
                df_grouped = df.groupby(["date_jour", col_pred]).size().reset_index(name="Nombre")
                fig_time = px.bar(
                    df_grouped, x="date_jour", y="Nombre", color=col_pred, 
                    title="Évolution du Volume d'Analyses par Jour", labels={"date_jour": "Date"},
                    color_discrete_map=COULEURS_DIAG
                )
                st.plotly_chart(fig_time, use_container_width=True)

    # --- TABLE SPÉCIFIQUE : ANALYSES ULTRA (8 CLASSES EXPERT) ---
    elif nom_table == "analyses_ultra":
        st.subheader("Filtres & Pilotage de l'Activité GeneXpert Ultra (8 Classes)")
        
        if "created_at" in df.columns:
            df["created_at_dt"] = pd.to_datetime(df["created_at"], errors='coerce')
            df["date_jour"] = df["created_at_dt"].dt.date
        
        col_f1, col_f2 = st.columns(2)
        
        operateurs = ["Tous"] + list(df["utilisateur"].dropna().unique()) if "utilisateur" in df.columns else ["Tous"]
        op_choisi = col_f1.selectbox("Filtrer par Opérateur / Utilisateur (Ultra)", operateurs, key="op_ultra_filter")
        if op_choisi != "Tous":
            df = df[df["utilisateur"] == op_choisi]

        if "created_at_dt" in df.columns and df["created_at_dt"].notna().any():
            min_date = df["created_at_dt"].min().date()
            max_date = df["created_at_dt"].max().date()
            plage_dates = col_f2.date_input("Filtrer par période (Ultra)", [min_date, max_date], key="date_ultra_filter")
            if len(plage_dates) == 2:
                d_debut, d_fin = plage_dates
                df = df[(df["created_at_dt"].dt.date >= d_debut) & (df["created_at_dt"].dt.date <= d_fin)]

        st.markdown("---")
        st.subheader("Indicateurs Clés Ultra (8 Classes Expert)")
        u1, u2, u3, u4 = st.columns(4)
        
        total_analyses_u = len(df)
        u1.metric("Total Analyses Ultra", total_analyses_u)

        col_pred_u = "prediction_ia" if "prediction_ia" in df.columns else ("Résultat IA Ultra" if "Résultat IA Ultra" in df.columns else "Prédiction IA")
        if col_pred_u in df.columns:
            nb_neg_u = len(df[df[col_pred_u].str.contains("Non Détecté", case=False, na=False) & ~df[col_pred_u].str.contains("Résistant", case=False, na=False)])
            nb_pos_u = total_analyses_u - nb_neg_u
            
            u2.metric("🟢 MTB Non Détectés", nb_neg_u)
            u3.metric("🔬 MTB Détectés / Traces", nb_pos_u)
            
            taux_pos_u = (nb_pos_u / total_analyses_u * 100) if total_analyses_u > 0 else 0.0
            u4.metric("📈 Taux de Détection Ultra", f"{taux_pos_u:.1f}%")

        st.markdown("---")
        st.subheader("Visualisations & Répartition 8 Classes Ultra")
        
        uc_ch1, uc_ch2 = st.columns(2)
        with uc_ch1:
            if col_pred_u in df.columns:
                fig_pie_u = px.pie(
                    df, names=col_pred_u, title="Répartition des 8 Classes Expert Ultra", hole=0.4,
                    color=col_pred_u, color_discrete_map=COULEURS_ULTRA
                )
                st.plotly_chart(fig_pie_u, use_container_width=True)

        with uc_ch2:
            if "date_jour" in df.columns and not df["date_jour"].dropna().empty:
                df_grouped_u = df.groupby(["date_jour", col_pred_u]).size().reset_index(name="Nombre")
                fig_time_u = px.bar(
                    df_grouped_u, x="date_jour", y="Nombre", color=col_pred_u, 
                    title="Évolution journalière des diagnostics Ultra", labels={"date_jour": "Date"},
                    color_discrete_map=COULEURS_ULTRA
                )
                st.plotly_chart(fig_time_u, use_container_width=True)

    # --- AUTRES TABLES DE REGISTRE ---
    else:
        st.subheader("Indicateurs Clés Cliniques")
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
    st.subheader("Registre Détaillé en Ligne")
    afficher_tableau_labo(df, hauteur=450)