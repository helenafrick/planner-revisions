from __future__ import annotations

import random
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st


DB_PATH = Path(__file__).with_name("planning_revisions.db")
HEURES_PAR_ECTS = 30

CONSEILS_REVISION = [
    "Travaille en rappel actif : ferme le cours et reformule l'essentiel de memoire.",
    "Alterner les matieres aide a mieux retenir qu'un long bloc monotone.",
    "Une fiche courte en fin de seance vaut souvent mieux qu'une relecture passive.",
    "Teste-toi souvent : se poser des questions est l'un des meilleurs leviers de memorisation.",
    "Quand tu bloques, change de support : schema, oral, flashcards ou exercices.",
    "Des pauses courtes et vraies protègent la concentration sur la duree.",
    "Dormir suffisamment fait partie du travail : la consolidation de la memoire en depend.",
    "Commencer par un objectif simple rend plus facile l'entree dans la seance.",
]

PALETTE = {
    "fond": "#FAF9F7",
    "fond_secondaire": "#FBFAF8",
    "bloc": "#FFFFFF",
    "bloc_fonce": "#EDE7F6",
    "accent": "#C8B6E2",
    "accent_fonce": "#4B3F5C",
    "texte": "#6F6877",
    "texte_doux": "#938B9C",
    "bordure": "#E8E2EE",
    "blanc": "#FFFFFF",
    "perle": "#F7F4FA",
}


@dataclass
class Examen:
    id: int
    matiere: str
    date_examen: date
    ects: float
    heures_effectuees: float

    @property
    def heures_totales(self) -> float:
        return round(self.ects * HEURES_PAR_ECTS, 2)

    @property
    def heures_restantes(self) -> float:
        return round(max(0.0, self.heures_totales - self.heures_effectuees), 2)


@dataclass
class Indisponibilite:
    id: int
    date_indispo: date
    heure_debut: time
    heure_fin: time
    note: str


def connexion_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialiser_db() -> None:
    with connexion_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS examens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                matiere TEXT NOT NULL,
                date_examen TEXT NOT NULL,
                ects REAL NOT NULL,
                heures_effectuees REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS indisponibilites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date_indispo TEXT NOT NULL,
                heure_debut TEXT NOT NULL,
                heure_fin TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )


def creer_ou_recuperer_utilisateur(username: str) -> tuple[bool, str, int | None]:
    if len(username.strip()) < 3:
        return False, "Le nom d'utilisateur doit contenir au moins 3 caracteres.", None

    try:
        with connexion_db() as conn:
            utilisateur = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username.strip(),),
            ).fetchone()
            if utilisateur:
                return True, "Profil retrouve.", int(utilisateur["id"])

            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username.strip(), ""),
            )
            utilisateur = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username.strip(),),
            ).fetchone()
        return True, "Profil cree.", int(utilisateur["id"]) if utilisateur else None
    except sqlite3.IntegrityError:
        return False, "Impossible d'utiliser ce nom d'utilisateur.", None


def recuperer_utilisateur(username: str) -> int | None:
    with connexion_db() as conn:
        utilisateur = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    return int(utilisateur["id"]) if utilisateur else None


def charger_examens(user_id: int) -> list[Examen]:
    with connexion_db() as conn:
        lignes = conn.execute(
            """
            SELECT id, matiere, date_examen, ects, heures_effectuees
            FROM examens
            WHERE user_id = ?
            ORDER BY date_examen ASC, matiere ASC
            """,
            (user_id,),
        ).fetchall()

    examens = []
    for ligne in lignes:
        examens.append(
            Examen(
                id=int(ligne["id"]),
                matiere=str(ligne["matiere"]),
                date_examen=datetime.strptime(ligne["date_examen"], "%Y-%m-%d").date(),
                ects=float(ligne["ects"]),
                heures_effectuees=float(ligne["heures_effectuees"]),
            )
        )
    return examens


def charger_indisponibilites(user_id: int) -> list[Indisponibilite]:
    with connexion_db() as conn:
        lignes = conn.execute(
            """
            SELECT id, date_indispo, heure_debut, heure_fin, note
            FROM indisponibilites
            WHERE user_id = ?
            ORDER BY date_indispo ASC, heure_debut ASC
            """,
            (user_id,),
        ).fetchall()

    indisponibilites = []
    for ligne in lignes:
        indisponibilites.append(
            Indisponibilite(
                id=int(ligne["id"]),
                date_indispo=datetime.strptime(ligne["date_indispo"], "%Y-%m-%d").date(),
                heure_debut=datetime.strptime(ligne["heure_debut"], "%H:%M").time(),
                heure_fin=datetime.strptime(ligne["heure_fin"], "%H:%M").time(),
                note=str(ligne["note"] or ""),
            )
        )
    return indisponibilites


def ajouter_examen_db(
    user_id: int,
    matiere: str,
    date_examen: date,
    ects: float,
    heures_effectuees: float,
) -> None:
    with connexion_db() as conn:
        conn.execute(
            """
            INSERT INTO examens (user_id, matiere, date_examen, ects, heures_effectuees)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, matiere.strip(), date_examen.isoformat(), ects, heures_effectuees),
        )


def ajouter_indisponibilite_db(
    user_id: int,
    date_indispo: date,
    heure_debut: time,
    heure_fin: time,
    note: str,
) -> None:
    with connexion_db() as conn:
        conn.execute(
            """
            INSERT INTO indisponibilites (user_id, date_indispo, heure_debut, heure_fin, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                date_indispo.isoformat(),
                heure_debut.strftime("%H:%M"),
                heure_fin.strftime("%H:%M"),
                note.strip(),
            ),
        )


def supprimer_examen_db(examen_id: int, user_id: int) -> None:
    with connexion_db() as conn:
        conn.execute(
            "DELETE FROM examens WHERE id = ? AND user_id = ?",
            (examen_id, user_id),
        )


def supprimer_indisponibilite_db(indispo_id: int, user_id: int) -> None:
    with connexion_db() as conn:
        conn.execute(
            "DELETE FROM indisponibilites WHERE id = ? AND user_id = ?",
            (indispo_id, user_id),
        )


def mettre_a_jour_heures_db(examen_id: int, user_id: int, heures_effectuees: float) -> None:
    with connexion_db() as conn:
        conn.execute(
            """
            UPDATE examens
            SET heures_effectuees = ?
            WHERE id = ? AND user_id = ?
            """,
            (heures_effectuees, examen_id, user_id),
        )


def format_date_fr(valeur: date) -> str:
    return valeur.strftime("%d/%m/%Y")


def injecter_style() -> None:
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@400;500;600;700&family=Playfair+Display:wght@500;600&display=swap');
            html, body, [class*="css"] {{
                font-family: "Raleway", "Inter", "Lato", "Source Sans 3", -apple-system, BlinkMacSystemFont, sans-serif;
            }}
            .block-container {{
                max-width: 1140px;
                padding-top: 2.8rem;
                padding-bottom: 4rem;
                padding-left: 2.4rem;
                padding-right: 2.4rem;
            }}
            .stApp {{
                background: {PALETTE["fond"]};
                color: {PALETTE["texte"]};
            }}
            h1, h2, h3, h4 {{
                font-family: "Playfair Display", Georgia, "Times New Roman", serif;
                color: {PALETTE["accent_fonce"]};
                font-weight: 500;
            }}
            p, label, div, span, li {{
                color: {PALETTE["texte"]};
            }}
            h1 {{
                font-size: 2.15rem !important;
                line-height: 1.18;
                letter-spacing: -0.02em;
                margin-bottom: 0.4rem;
            }}
            h2 {{
                font-size: 1.5rem !important;
                margin-top: 0.2rem;
                margin-bottom: 1rem;
            }}
            h3 {{
                font-size: 1.02rem !important;
                letter-spacing: -0.01em;
            }}
            p, label, li {{
                line-height: 1.7;
            }}
            [data-testid="stMetric"] {{
                background: {PALETTE["blanc"]};
                border: 1px solid {PALETTE["bordure"]};
                border-radius: 18px;
                padding: 1.2rem 1.15rem 1.1rem 1.15rem;
                box-shadow: 0 8px 24px rgba(75, 63, 92, 0.03);
            }}
            [data-testid="stMetricLabel"] {{
                color: {PALETTE["texte_doux"]};
            }}
            [data-testid="stMetricValue"] {{
                color: {PALETTE["accent_fonce"]};
            }}
            .hero, .bloc-lilas, .agenda-jour, .citation-lilas, .auth-card, .message-card {{
                background: {PALETTE["blanc"]};
                border: 1px solid {PALETTE["bordure"]};
                box-shadow: 0 10px 28px rgba(75, 63, 92, 0.035);
            }}
            .hero {{
                border-radius: 20px;
                padding: 2rem 2rem 1.8rem 2rem;
                margin-bottom: 1.7rem;
            }}
            .bloc-lilas {{
                border-radius: 18px;
                padding: 1.5rem;
                margin-bottom: 1.45rem;
            }}
            .citation-lilas {{
                border-radius: 18px;
                padding: 1.1rem 1.25rem;
                margin-bottom: 1.35rem;
                background: {PALETTE["perle"]};
            }}
            .auth-card {{
                border-radius: 18px;
                padding: 1.6rem;
                max-width: 620px;
            }}
            .agenda-jour {{
                border-radius: 18px;
                padding: 1.45rem;
                margin-bottom: 1.35rem;
                background: {PALETTE["blanc"]};
            }}
            .agenda-date {{
                font-family: "Playfair Display", Georgia, "Times New Roman", serif;
                font-size: 1.2rem;
                font-weight: 500;
                margin-bottom: 1.2rem;
                color: {PALETTE["accent_fonce"]};
            }}
            .agenda-slot {{
                background: {PALETTE["perle"]};
                border: 1px solid {PALETTE["bordure"]};
                border-left: 4px solid {PALETTE["accent"]};
                border-radius: 14px;
                padding: 1rem 1rem 0.95rem 1rem;
                margin-bottom: 1rem;
                box-shadow: none;
            }}
            .agenda-hour {{
                color: {PALETTE["texte_doux"]};
                font-size: 0.82rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-bottom: 0.45rem;
            }}
            .agenda-subject {{
                color: {PALETTE["accent_fonce"]};
                font-family: "Playfair Display", Georgia, serif;
                font-size: 1.02rem;
                margin-bottom: 0.2rem;
            }}
            .agenda-meta {{
                color: {PALETTE["texte_doux"]};
                font-size: 0.9rem;
            }}
            .planner-shell {{
                display: grid;
                grid-template-columns: 180px 1fr;
                gap: 1.1rem;
                align-items: start;
            }}
            .planner-hours {{
                padding-top: 0.15rem;
            }}
            .planner-hour-row {{
                height: 84px;
                border-bottom: 1px solid {PALETTE["bordure"]};
                color: {PALETTE["texte_doux"]};
                font-size: 0.9rem;
                display: flex;
                align-items: flex-start;
                padding-top: 0.25rem;
            }}
            .planner-grid {{
                border: 1px solid {PALETTE["bordure"]};
                border-radius: 16px;
                overflow: hidden;
                background: {PALETTE["blanc"]};
            }}
            .planner-row {{
                min-height: 84px;
                border-bottom: 1px solid {PALETTE["bordure"]};
                padding: 0.65rem 0.8rem;
                display: flex;
                align-items: stretch;
            }}
            .planner-row:last-child, .planner-hour-row:last-child {{
                border-bottom: none;
            }}
            .planner-empty {{
                color: {PALETTE["texte_doux"]};
                font-size: 0.9rem;
                align-self: center;
            }}
            .study-block {{
                width: 100%;
                background: {PALETTE["bloc_fonce"]};
                border: 1px solid {PALETTE["bordure"]};
                border-radius: 14px;
                padding: 0.85rem 0.95rem;
            }}
            .study-block-title {{
                font-family: "Playfair Display", Georgia, serif;
                font-size: 1rem;
                color: {PALETTE["accent_fonce"]};
                margin-bottom: 0.25rem;
            }}
            .study-block-sub {{
                color: {PALETTE["texte_doux"]};
                font-size: 0.9rem;
            }}
            .day-nav-wrap {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 1rem;
                margin-bottom: 1.15rem;
            }}
            .day-pill {{
                border: 1px solid {PALETTE["bordure"]};
                border-radius: 999px;
                padding: 0.45rem 0.9rem;
                color: {PALETTE["accent_fonce"]};
                background: {PALETTE["perle"]};
                font-size: 0.88rem;
            }}
            .exam-card {{
                border: 1px solid {PALETTE["bordure"]};
                border-radius: 16px;
                padding: 1.05rem 1.1rem;
                background: {PALETTE["blanc"]};
                margin-bottom: 0.9rem;
            }}
            .exam-title {{
                font-family: "Playfair Display", Georgia, serif;
                color: {PALETTE["accent_fonce"]};
                font-size: 1.05rem;
                margin-bottom: 0.25rem;
            }}
            .exam-meta {{
                color: {PALETTE["texte_doux"]};
                font-size: 0.92rem;
                margin-bottom: 0.65rem;
            }}
            .mini-tag {{
                display: inline-block;
                border: 1px solid {PALETTE["bordure"]};
                background: {PALETTE["perle"]};
                border-radius: 999px;
                padding: 0.2rem 0.55rem;
                color: {PALETTE["accent_fonce"]};
                font-size: 0.82rem;
                margin-right: 0.35rem;
                margin-bottom: 0.35rem;
            }}
            .indispo-card {{
                border: 1px solid {PALETTE["bordure"]};
                border-radius: 14px;
                padding: 0.9rem 1rem;
                background: {PALETTE["perle"]};
                margin-bottom: 0.75rem;
            }}
            .statut-passe {{
                color: {PALETTE["texte_doux"]};
                font-weight: 700;
            }}
            .statut-a-venir {{
                color: {PALETTE["accent_fonce"]};
                font-weight: 700;
            }}
            .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
                background: {PALETTE["bloc_fonce"]};
                color: {PALETTE["accent_fonce"]};
                border-radius: 12px;
                border: 1px solid {PALETTE["bordure"]};
                padding: 0.7rem 1.15rem;
                min-height: 2.8rem;
                box-shadow: none;
                font-weight: 500;
            }}
            .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
                color: {PALETTE["accent_fonce"]};
                background: {PALETTE["perle"]};
                border-color: {PALETTE["accent"]};
                transform: translateY(-1px);
            }}
            .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
                transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease;
            }}
            .stButton > button[kind="primary"] {{
                background: {PALETTE["accent_fonce"]};
                color: {PALETTE["blanc"]};
                border-color: {PALETTE["accent_fonce"]};
            }}
            .stButton > button[kind="primary"]:hover {{
                background: {PALETTE["accent_fonce"]};
                color: {PALETTE["blanc"]};
                filter: brightness(1.03);
            }}
            .stTextInput input, .stNumberInput input, .stDateInput input, textarea {{
                border-radius: 12px !important;
                border: 1px solid {PALETTE["bordure"]} !important;
                background: {PALETTE["blanc"]} !important;
                min-height: 3rem !important;
            }}
            .stSelectbox div[data-baseweb="select"] > div,
            .stMultiSelect div[data-baseweb="select"] > div {{
                border-radius: 12px !important;
                border: 1px solid {PALETTE["bordure"]} !important;
                background: {PALETTE["blanc"]} !important;
            }}
            .stSlider, .stSelectSlider {{
                padding-top: 0.7rem;
                padding-bottom: 0.8rem;
            }}
            .stAlert {{
                display: none;
            }}
            .stDataFrame {{
                display: none;
            }}
            div[data-baseweb="tab-list"] button {{
                border-radius: 12px;
                border: 1px solid {PALETTE["bordure"]};
                background: {PALETTE["blanc"]};
                color: {PALETTE["texte"]};
            }}
            div[data-baseweb="tab-list"] button[aria-selected="true"] {{
                background: {PALETTE["bloc_fonce"]};
                color: {PALETTE["accent_fonce"]};
            }}
            div[data-baseweb="tab-list"] {{
                gap: 0.55rem;
                padding-bottom: 0.95rem;
            }}
            section[data-testid="stSidebar"] {{
                background: {PALETTE["fond_secondaire"]};
                border-right: 1px solid {PALETTE["bordure"]};
            }}
            section[data-testid="stSidebar"] .block-container {{
                padding-top: 1.8rem;
                padding-left: 1.1rem;
                padding-right: 1.1rem;
            }}
            .sidebar-card {{
                background: rgba(255,255,255,0.74);
                border: 1px solid {PALETTE["bordure"]};
                border-radius: 18px;
                padding: 1rem;
                margin-bottom: 1rem;
            }}
            .subtle {{
                color: {PALETTE["texte_doux"]};
                font-size: 0.95rem;
            }}
            .message-card {{
                border-radius: 16px;
                padding: 0.95rem 1rem;
                margin-top: 0.9rem;
                margin-bottom: 0.3rem;
            }}
            .message-card strong {{
                color: {PALETTE["accent_fonce"]};
                display: block;
                margin-bottom: 0.25rem;
                font-family: Georgia, "Times New Roman", serif;
                font-weight: 500;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialiser_session() -> None:
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None
    if "citation_revision" not in st.session_state:
        st.session_state.citation_revision = random.choice(CONSEILS_REVISION)
    if "agenda_genere" not in st.session_state:
        st.session_state.agenda_genere = pd.DataFrame()
    if "page_active" not in st.session_state:
        st.session_state.page_active = "Tableau de bord"
    if "agenda_jour_index" not in st.session_state:
        st.session_state.agenda_jour_index = 0


def afficher_message(message: str, titre: str = "Information") -> None:
    st.markdown(
        f"""
        <div class="message-card">
            <strong>{titre}</strong>
            <span>{message}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def afficher_examen_card(examen: Examen) -> None:
    statut = "Passe" if examen.date_examen < date.today() else "A venir"
    st.markdown(
        f"""
        <div class="exam-card">
            <div class="exam-title">{examen.matiere}</div>
            <div class="exam-meta">Examen le {format_date_fr(examen.date_examen)} · {statut}</div>
            <span class="mini-tag">{examen.ects:.1f} ECTS</span>
            <span class="mini-tag">{examen.heures_totales:.1f} h totales</span>
            <span class="mini-tag">{examen.heures_restantes:.1f} h restantes</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def afficher_indisponibilite_card(indispo: Indisponibilite) -> None:
    note = f" · {indispo.note}" if indispo.note else ""
    st.markdown(
        f"""
        <div class="indispo-card">
            <div class="exam-meta">{format_date_fr(indispo.date_indispo)} · {indispo.heure_debut.strftime("%H:%M")} - {indispo.heure_fin.strftime("%H:%M")}{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def afficher_study_block(ligne: pd.Series) -> None:
    with st.container(border=True):
        st.markdown(
            f"**{ligne['Matière']}**",
        )
        st.caption(f"{ligne['Début']} - {ligne['Fin']}")
        st.write(ligne["Tache"])
        st.markdown(
            f'<p class="subtle">Examen le {ligne["Examen"]}</p>',
            unsafe_allow_html=True,
        )


def examens_utilisateur() -> list[Examen]:
    if not st.session_state.user_id:
        return []
    return charger_examens(st.session_state.user_id)


def indisponibilites_utilisateur() -> list[Indisponibilite]:
    if not st.session_state.user_id:
        return []
    return charger_indisponibilites(st.session_state.user_id)


def chevauche(
    debut_a: datetime,
    fin_a: datetime,
    debut_b: datetime,
    fin_b: datetime,
) -> bool:
    return debut_a < fin_b and fin_a > debut_b


def creer_creneaux(
    jour: date,
    heures_cible: float,
    duree_creneau: int,
    indisponibilites: list[Indisponibilite],
) -> list[datetime]:
    creneaux = []
    minutes_totales = int(heures_cible * 60)
    if minutes_totales <= 0:
        return creneaux

    debut_journee = datetime.combine(jour, time(hour=8, minute=0))
    fin_journee = datetime.combine(jour, time(hour=20, minute=0))
    curseur = debut_journee
    minutes_planifiees = 0
    indispos_du_jour = [item for item in indisponibilites if item.date_indispo == jour]

    while (
        minutes_planifiees + duree_creneau <= minutes_totales
        and curseur + timedelta(minutes=duree_creneau) <= fin_journee
    ):
        fin_creneau = curseur + timedelta(minutes=duree_creneau)
        conflit = None
        for indispo in indispos_du_jour:
            debut_indispo = datetime.combine(jour, indispo.heure_debut)
            fin_indispo = datetime.combine(jour, indispo.heure_fin)
            if chevauche(curseur, fin_creneau, debut_indispo, fin_indispo):
                conflit = fin_indispo
                break

        if conflit is not None:
            curseur = conflit + timedelta(minutes=15)
            continue

        creneaux.append(curseur)
        curseur = fin_creneau + timedelta(minutes=15)
        minutes_planifiees += duree_creneau
    return creneaux


def choisir_matiere_score(
    examens: list[Examen],
    jour: date,
    matieres_du_jour: list[str],
    derniere_matiere: str | None,
) -> Examen | None:
    candidats = [
        examen
        for examen in examens
        if examen.heures_restantes > 0 and examen.date_examen > jour
    ]
    if not candidats:
        return None

    compteur_jour = Counter(matieres_du_jour)
    analyses = []

    for examen in candidats:
        jours_restants = max((examen.date_examen - jour).days, 1)
        pression = examen.heures_restantes / jours_restants
        urgence = 7 / jours_restants
        penalite_suite = 1.8 if derniere_matiere == examen.matiere else 0
        penalite_jour = compteur_jour[examen.matiere] * 0.95
        score = (pression * 3.2) + (urgence * 2.6) - penalite_suite - penalite_jour
        analyses.append(
            {
                "examen": examen,
                "score": score,
                "pression": pression,
                "date_examen": examen.date_examen,
            }
        )

    analyses.sort(
        key=lambda item: (
            item["score"],
            item["pression"],
            -item["date_examen"].toordinal(),
        ),
        reverse=True,
    )

    meilleur = analyses[0]["examen"]
    if len(analyses) > 1 and derniere_matiere == meilleur.matiere:
        for option in analyses[1:]:
            alternative = option["examen"]
            if alternative.matiere != derniere_matiere:
                ecart = analyses[0]["score"] - option["score"]
                if ecart < 1.5 or compteur_jour[meilleur.matiere] >= 2:
                    return alternative
    return meilleur


def generer_agenda(
    examens: list[Examen],
    heures_semaine: float,
    heures_weekend: float,
    duree_creneau: int,
    indisponibilites: list[Indisponibilite],
) -> pd.DataFrame:
    aujourd_hui = date.today()
    examens_a_venir = [
        Examen(
            id=examen.id,
            matiere=examen.matiere,
            date_examen=examen.date_examen,
            ects=examen.ects,
            heures_effectuees=examen.heures_effectuees,
        )
        for examen in examens
        if examen.date_examen >= aujourd_hui
    ]
    if not examens_a_venir:
        return pd.DataFrame()

    derniere_date = max(examen.date_examen for examen in examens_a_venir)
    agenda = []
    jour = aujourd_hui

    while jour <= derniere_date:
        heures_du_jour = heures_weekend if jour.weekday() >= 5 else heures_semaine
        creneaux = creer_creneaux(jour, heures_du_jour, duree_creneau, indisponibilites)
        matieres_du_jour: list[str] = []
        derniere_matiere: str | None = None

        for debut_creneau in creneaux:
            examen_choisi = choisir_matiere_score(
                examens_a_venir,
                jour,
                matieres_du_jour,
                derniere_matiere,
            )
            if examen_choisi is None:
                break

            duree_heures = duree_creneau / 60
            duree_reelle = min(duree_heures, examen_choisi.heures_restantes)
            fin_creneau = debut_creneau + timedelta(hours=duree_reelle)

            agenda.append(
                {
                    "Date": format_date_fr(jour),
                    "Date_obj": jour,
                    "Début": debut_creneau.strftime("%H:%M"),
                    "Fin": fin_creneau.strftime("%H:%M"),
                    "Matière": examen_choisi.matiere,
                    "Examen": format_date_fr(examen_choisi.date_examen),
                    "Durée (h)": round(duree_reelle, 2),
                    "Jours restants": (examen_choisi.date_examen - jour).days,
                    "Tache": f"Revision ciblee · {round(duree_reelle, 2)} h",
                }
            )

            examen_choisi.heures_effectuees = round(
                examen_choisi.heures_effectuees + duree_reelle,
                2,
            )
            matieres_du_jour.append(examen_choisi.matiere)
            derniere_matiere = examen_choisi.matiere

        jour += timedelta(days=1)

    return pd.DataFrame(agenda)


def dataframe_examens(examens: list[Examen]) -> pd.DataFrame:
    aujourd_hui = date.today()
    lignes = []
    for examen in examens:
        statut = "Passe" if examen.date_examen < aujourd_hui else "A venir"
        lignes.append(
            {
                "ID": examen.id,
                "Matiere": examen.matiere,
                "Date d'examen": format_date_fr(examen.date_examen),
                "ECTS": examen.ects,
                "Heures totales": examen.heures_totales,
                "Heures deja faites": examen.heures_effectuees,
                "Heures restantes": examen.heures_restantes,
                "Statut": statut,
            }
        )
    return pd.DataFrame(lignes)


def afficher_citation() -> None:
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(
            f"""
            <div class="citation-lilas">
                <strong>Conseil du moment</strong><br>
                {st.session_state.citation_revision}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        if st.button("Changer", key="changer_conseil"):
            st.session_state.citation_revision = random.choice(CONSEILS_REVISION)
            st.rerun()


def afficher_authentification() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>Planning de revisions</h1>
            <p>Une interface douce, claire et motivante pour organiser tes revisions avec calme.</p>
            <p class="subtle">Entre simplement ton nom d'utilisateur pour retrouver automatiquement ton espace.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    with st.form("connexion_simple"):
        username = st.text_input("Nom d'utilisateur", key="simple_username")
        submit = st.form_submit_button("Entrer dans mon espace")
    if submit:
        succes, message, user_id = creer_ou_recuperer_utilisateur(username)
        if not succes or user_id is None:
            afficher_message(message, "Nom d'utilisateur")
        else:
            st.session_state.user_id = user_id
            st.session_state.username = username.strip()
            afficher_message(message, "Bienvenue")
            st.rerun()
    st.markdown(
        '<p class="subtle">Si le nom existe deja, tu retrouves tes anciennes entrees. Sinon, un nouvel espace est cree automatiquement.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def afficher_indicateurs(examens: list[Examen]) -> None:
    aujourd_hui = date.today()
    total = len(examens)
    a_venir = len([ex for ex in examens if ex.date_examen >= aujourd_hui])
    passes = len([ex for ex in examens if ex.date_examen < aujourd_hui])
    heures_restantes = sum(ex.heures_restantes for ex in examens if ex.date_examen >= aujourd_hui)
    ects_total = sum(ex.ects for ex in examens)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Examens", total)
    col2.metric("A venir", a_venir)
    col3.metric("ECTS cumules", f"{ects_total:.1f}")
    col4.metric("Heures restantes", f"{heures_restantes:.1f} h")

    if passes:
        st.markdown(
            f'<p class="subtle">{passes} examen(s) passe(s) restent visibles dans le resume, mais jamais dans l agenda.</p>',
            unsafe_allow_html=True,
        )


def page_tableau_de_bord(examens: list[Examen]) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>Bonjour {st.session_state.username}</h1>
            <p>Ton espace conserve tes examens d'une session a l'autre et transforme tes objectifs en planning doux et realiste.</p>
            <p class="subtle">Les heures restantes sont calculees automatiquement a partir des ECTS et de ton avancement deja effectue.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    afficher_citation()
    afficher_indicateurs(examens)

    examens_a_venir = [ex for ex in examens if ex.date_examen >= date.today()]
    if examens_a_venir:
        plus_proche = min(examens_a_venir, key=lambda ex: ex.date_examen)
        st.markdown(
            f"""
            <div class="bloc-lilas">
                <h3>Priorite actuelle</h3>
                <p><strong>{plus_proche.matiere}</strong> le {format_date_fr(plus_proche.date_examen)}</p>
                <p>{plus_proche.heures_restantes:.1f} h restantes sur {plus_proche.heures_totales:.1f} h au total.</p>
                <p class="subtle">Le planning favorisera cette matiere si la date approche ou si la charge restante reste elevee.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        afficher_message(
            "Aucun examen a venir pour le moment. Tu peux en ajouter dans la page Mes examens.",
            "Espace calme",
        )


def page_examens(examens: list[Examen]) -> None:
    st.subheader("Mes examens")
    gauche, droite = st.columns([1, 1.2], gap="large")

    with gauche:
        st.markdown('<div class="bloc-lilas">', unsafe_allow_html=True)
        st.markdown("### Ajouter un examen")
        with st.form("ajout_examen", clear_on_submit=True):
            matiere = st.text_input("Nom de la matiere", placeholder="Ex. Finance publique")
            date_examen = st.date_input(
                "Date de l'examen",
                value=date.today() + timedelta(days=10),
                format="DD/MM/YYYY",
            )
            ects = st.number_input("Nombre d'ECTS", min_value=0.5, max_value=30.0, value=3.0, step=0.5)
            heures_effectuees = st.number_input(
                "Heures deja travaillees",
                min_value=0.0,
                max_value=500.0,
                value=0.0,
                step=0.5,
            )
            total_calcule = ects * HEURES_PAR_ECTS
            restant_calcule = max(0.0, total_calcule - heures_effectuees)
            afficher_message(
                f"Calcul automatique : {ects:.1f} ECTS = {total_calcule:.1f} h de travail, il reste {restant_calcule:.1f} h.",
                "Calcul des heures",
            )
            submit = st.form_submit_button("Enregistrer l'examen")

        if submit:
            if not matiere.strip():
                afficher_message("Entre d'abord le nom de la matiere.", "Champ manquant")
            else:
                ajouter_examen_db(
                    st.session_state.user_id,
                    matiere,
                    date_examen,
                    ects,
                    min(heures_effectuees, total_calcule),
                )
                afficher_message("Examen enregistre.", "Ajout effectue")
                st.session_state.agenda_genere = pd.DataFrame()
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with droite:
        st.markdown('<div class="bloc-lilas">', unsafe_allow_html=True)
        st.markdown("### Resume")
        if not examens:
            afficher_message("Aucun examen enregistre pour l'instant.", "Resume vide")
        else:
            for examen in examens:
                afficher_examen_card(examen)
                col_a, col_b = st.columns([1.1, 0.9], gap="small")
                with col_a:
                    nouvelles_heures = st.number_input(
                        f"Heures deja effectuees · {examen.matiere}",
                        min_value=0.0,
                        max_value=float(examen.heures_totales),
                        value=float(min(examen.heures_effectuees, examen.heures_totales)),
                        step=0.5,
                        key=f"progression_{examen.id}",
                    )
                with col_b:
                    st.write("")
                    st.write("")
                    if st.button("Mettre a jour", use_container_width=True, key=f"maj_{examen.id}"):
                        mettre_a_jour_heures_db(
                            examen.id,
                            st.session_state.user_id,
                            nouvelles_heures,
                        )
                        st.session_state.agenda_genere = pd.DataFrame()
                        afficher_message("Progression mise a jour.", "Avancement")
                        st.rerun()
                    if st.button("Supprimer", use_container_width=True, key=f"supprimer_{examen.id}"):
                        supprimer_examen_db(examen.id, st.session_state.user_id)
                        st.session_state.agenda_genere = pd.DataFrame()
                        afficher_message("Examen supprime.", "Modification")
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def parametres_agenda() -> tuple[float, float, int, bool]:
    st.markdown('<div class="bloc-lilas">', unsafe_allow_html=True)
    st.markdown("### Parametres de generation")
    heures_semaine = st.number_input(
        "Temps de revision par jour en semaine",
        min_value=1.0,
        max_value=14.0,
        value=3.0,
        step=0.5,
    )
    heures_weekend = st.number_input(
        "Temps de revision par jour le week-end",
        min_value=1.0,
        max_value=14.0,
        value=4.5,
        step=0.5,
    )
    duree_creneau = st.number_input(
        "Duree d'un creneau (minutes)",
        min_value=30,
        max_value=180,
        value=60,
        step=15,
    )
    lancer = st.button("Generer mon agenda visuel", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return heures_semaine, heures_weekend, duree_creneau, lancer


def afficher_agenda_visuel(df_agenda: pd.DataFrame) -> None:
    if df_agenda.empty:
        afficher_message(
            "Aucun creneau a afficher. Les examens passes sont exclus de l agenda.",
            "Agenda vide",
        )
        return

    if "Tache" not in df_agenda.columns:
        df_agenda = df_agenda.copy()
        df_agenda["Tache"] = df_agenda.get("Durée (h)", 0).apply(
            lambda valeur: f"Revision ciblee · {valeur} h"
        )

    jours = list(df_agenda.groupby("Date", sort=False))
    st.session_state.agenda_jour_index = min(
        st.session_state.agenda_jour_index,
        max(len(jours) - 1, 0),
    )

    col_prev, col_title, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("Jour precedent", use_container_width=True, disabled=st.session_state.agenda_jour_index == 0):
            st.session_state.agenda_jour_index -= 1
            st.rerun()
    with col_title:
        jour, groupe = jours[st.session_state.agenda_jour_index]
        st.markdown(
            f"""
            <div class="day-nav-wrap">
                <div class="agenda-date">{jour}</div>
                <div class="day-pill">{st.session_state.agenda_jour_index + 1} / {len(jours)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("Jour suivant", use_container_width=True, disabled=st.session_state.agenda_jour_index >= len(jours) - 1):
            st.session_state.agenda_jour_index += 1
            st.rerun()

    st.markdown('<div class="agenda-jour">', unsafe_allow_html=True)
    for _, ligne in groupe.iterrows():
        col_heure, col_bloc = st.columns([0.18, 0.82], gap="medium")
        with col_heure:
            st.markdown(
                f"""
                <div class="agenda-hour">
                    {ligne["Début"]}<br>
                    <span class="subtle">{ligne["Fin"]}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_bloc:
            afficher_study_block(ligne)
        st.write("")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="bloc-lilas">', unsafe_allow_html=True)
    st.markdown("### Vue compacte des jours")
    chips = [f'<span class="mini-tag">{jour}</span>' for jour, _ in jours]
    st.markdown("".join(chips), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def page_agenda(examens: list[Examen]) -> None:
    st.subheader("Mon agenda de revisions")
    if not examens:
        afficher_message("Ajoute d'abord des examens pour generer un agenda.", "Avant de commencer")
        return

    indisponibilites = indisponibilites_utilisateur()
    heures_semaine, heures_weekend, duree_creneau, lancer = parametres_agenda()
    st.markdown('<div class="bloc-lilas">', unsafe_allow_html=True)
    st.markdown("### Mes indisponibilites")
    with st.form("ajout_indisponibilite", clear_on_submit=True):
        date_indispo = st.date_input("Date indisponible", value=date.today(), format="DD/MM/YYYY", key="date_indispo")
        col1, col2 = st.columns(2)
        with col1:
            heure_debut = st.time_input("Heure de debut", value=time(hour=12, minute=0), step=900)
        with col2:
            heure_fin = st.time_input("Heure de fin", value=time(hour=14, minute=0), step=900)
        note = st.text_input("Note optionnelle", placeholder="Cours, travail, rendez-vous")
        ajouter = st.form_submit_button("Ajouter cette indisponibilite")

    if ajouter:
        if heure_fin <= heure_debut:
            afficher_message("L heure de fin doit etre apres l heure de debut.", "Indisponibilite")
        else:
            ajouter_indisponibilite_db(
                st.session_state.user_id,
                date_indispo,
                heure_debut,
                heure_fin,
                note,
            )
            st.session_state.agenda_genere = pd.DataFrame()
            afficher_message("Indisponibilite ajoutee.", "Agenda personnel")
            st.rerun()

    if indisponibilites:
        for indispo in indisponibilites:
            afficher_indisponibilite_card(indispo)
            if st.button("Supprimer ce bloc", key=f"indispo_{indispo.id}", use_container_width=False):
                supprimer_indisponibilite_db(indispo.id, st.session_state.user_id)
                st.session_state.agenda_genere = pd.DataFrame()
                st.rerun()
    else:
        afficher_message("Aucune indisponibilite enregistree pour le moment.", "Disponibilite")
    st.markdown("</div>", unsafe_allow_html=True)

    if lancer:
        st.session_state.agenda_jour_index = 0
        st.session_state.agenda_genere = generer_agenda(
            examens,
            heures_semaine,
            heures_weekend,
            duree_creneau,
            indisponibilites,
        )

    if not st.session_state.agenda_genere.empty:
        afficher_agenda_visuel(st.session_state.agenda_genere)
    else:
        afficher_message(
            "Genere l agenda pour voir une version visuelle de tes creneaux.",
            "Planning a generer",
        )


def page_conseils(examens: list[Examen]) -> None:
    st.subheader("Conseils et methode")
    afficher_citation()
    st.markdown(
        """
        <div class="bloc-lilas">
            <h3>Comment l'application calcule tes heures</h3>
            <p>Chaque ECTS vaut 30 heures de travail. L'application calcule donc automatiquement :</p>
            <p><strong>heures totales = ECTS × 30</strong></p>
            <p><strong>heures restantes = heures totales - heures deja effectuees</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if examens:
        for examen in examens:
            afficher_examen_card(examen)


def barre_laterale() -> str:
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-card">
                <h3>Bonjour {st.session_state.username}</h3>
                <p class="subtle">Ton planner de revisions reste ici, simple et organise.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        pages = ["Tableau de bord", "Mes examens", "Agenda", "Conseils"]
        for page in pages:
            bouton_type = "primary" if st.session_state.page_active == page else "secondary"
            if st.button(page, use_container_width=True, type=bouton_type):
                st.session_state.page_active = page
                st.rerun()

        st.write("")
        if st.button("Se deconnecter", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.agenda_genere = pd.DataFrame()
            st.session_state.page_active = "Tableau de bord"
            st.rerun()
    return st.session_state.page_active


def main() -> None:
    st.set_page_config(
        page_title="Planning de revisions",
        page_icon="📚",
        layout="wide",
    )
    initialiser_db()
    initialiser_session()
    injecter_style()

    if st.session_state.user_id is None:
        afficher_authentification()
        return

    examens = examens_utilisateur()
    page = barre_laterale()

    if page == "Tableau de bord":
        page_tableau_de_bord(examens)
    elif page == "Mes examens":
        page_examens(examens)
    elif page == "Agenda":
        page_agenda(examens)
    else:
        page_conseils(examens)


if __name__ == "__main__":
    main()
