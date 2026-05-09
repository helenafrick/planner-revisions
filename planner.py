from __future__ import annotations

import random
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st


# =============================================================================
# Configuration générale
# =============================================================================

DB_PATH = Path(__file__).with_name("planning_revisions.db")
HEURES_PAR_ECTS = 30

CITATIONS_ET_CONSEILS = [
    "Une séance réussie commence par une intention claire : aujourd’hui, je maîtrise un point précis.",
    "La relecture rassure, mais le rappel actif transforme vraiment la mémoire.",
    "Travaille comme une stratège : peu de gestes, mais les bons gestes.",
    "Une fiche courte après une séance vaut mieux qu’un long cours relu sans attention.",
    "Le cerveau adore les contrastes : alterne théorie, exercices, oral et mini-tests.",
    "Quand tu bloques, change de format : schéma, voix haute, tableau ou flashcards.",
    "Un examen se gagne souvent dans les détails répétés plusieurs fois avec calme.",
    "Le sommeil n’est pas une pause dans la réussite : c’est une partie de la stratégie.",
    "Chaque session doit produire une trace : une fiche, trois questions, un exercice ou une erreur comprise.",
    "Une erreur corrigée aujourd’hui est un point gagné le jour de l’examen.",
    "Commencer petit est une forme d’intelligence, pas un manque d’ambition.",
    "Lis moins longtemps, mais interroge-toi davantage.",
    "La régularité élégante bat toujours la panique spectaculaire.",
    "Ton planning doit te servir, pas t’intimider.",
    "Un bon objectif de séance tient en une phrase : à la fin, je sais expliquer X.",
    "Quand tout paraît urgent, commence par ce qui rapporte le plus de points.",
    "Le vrai luxe académique, c’est une tête claire.",
    "Une matière difficile devient moins menaçante dès qu’elle est découpée.",
    "Révise avec une question en tête : qu’est-ce que le professeur peut vraiment me demander ?",
    "Le calme est une arme intellectuelle.",
    "Fais de tes pauses des vraies pauses : pas une fuite, une recharge.",
    "La mémoire aime les rendez-vous courts et fréquents.",
    "Un exercice fait lentement et compris vaut trois exercices copiés vite.",
    "Quand tu maîtrises un concept, explique-le comme si tu donnais un mini-cours.",
    "L’élégance dans le travail, c’est de savoir exactement pourquoi tu fais ce que tu fais.",
    "Une journée imparfaite peut rester utile si elle contient une vraie victoire.",
    "Plus la matière est dense, plus la structure devient ton alliée.",
    "La confiance vient après les preuves, pas avant : crée les preuves chaque jour.",
    "Ton futur toi mérite des notes claires, pas des captures chaotiques.",
    "Ne cherche pas à tout apprendre d’un coup : cherche à ne rien laisser flou.",
    "La concentration se protège comme un bijou.",
    "Un planning doux peut être très ambitieux s’il est cohérent.",
    "Les révisions les plus efficaces sont souvent les moins dramatiques.",
    "Une question bien formulée vaut déjà la moitié d’une réponse.",
    "À chaque séance : comprendre, retenir, vérifier.",
    "Le cerveau retient mieux ce qu’il reconstruit que ce qu’il contemple.",
    "Ne confonds pas fatigue et incapacité : parfois, il faut juste changer de rythme.",
    "Le progrès discret est encore du progrès.",
    "Fais des examens passés tes répétitions générales.",
    "Réviser, ce n’est pas remplir du temps : c’est réduire l’incertitude.",
    "Une matière devient élégante quand tu en comprends la logique.",
    "Travaille les points faibles avec douceur, mais sans les fuir.",
    "Le charisme académique, c’est pouvoir expliquer simplement une idée complexe.",
    "Une bonne session commence avec un bureau calme et une seule priorité.",
    "La constance donne un charme fou aux ambitions sérieuses.",
    "Le stress baisse quand le prochain geste devient évident.",
    "Répéter n’est pas ennuyeux : c’est sculpter la maîtrise.",
    "Tu n’as pas besoin d’une journée parfaite, seulement d’une prochaine action claire.",
    "La réussite aime les systèmes plus que les élans de panique.",
    "Chaque heure bien placée devient une petite rente de confiance.",
]

IMAGES_AMBIANCE = [
    "https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1524758631624-e2822e304c36?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1497032628192-86f99bcd76bc?auto=format&fit=crop&w=1200&q=80",
]

PALETTE = {
    "fond": "#FFF9F8",
    "fond_secondaire": "#FFF3F6",
    "bloc": "#FFFFFF",
    "rose_poudre": "#F7DDE8",
    "rose": "#E8AFC6",
    "rose_fonce": "#A45C78",
    "lilas": "#DCCEF4",
    "champagne": "#F6E8D9",
    "ivoire": "#FFFDFB",
    "texte": "#594A55",
    "texte_doux": "#9B8A96",
    "bordure": "#F0DCE6",
    "ombre": "rgba(119, 76, 96, 0.10)",
}


# =============================================================================
# Modèles de données
# =============================================================================

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


# =============================================================================
# Base de données
# =============================================================================

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
    username = username.strip()

    if len(username) < 3:
        return False, "Le nom d’utilisateur doit contenir au moins 3 caractères.", None

    try:
        with connexion_db() as conn:
            utilisateur = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()

            if utilisateur:
                return True, "Profil retrouvé.", int(utilisateur["id"])

            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, ""),
            )
            utilisateur = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()

        return True, "Profil créé.", int(utilisateur["id"]) if utilisateur else None

    except sqlite3.IntegrityError:
        return False, "Impossible d’utiliser ce nom d’utilisateur.", None


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


# =============================================================================
# Fonctions utilitaires
# =============================================================================

def format_date_fr(valeur: date) -> str:
    return valeur.strftime("%d/%m/%Y")


def statut_examen(examen: Examen) -> str:
    return "Passé" if examen.date_examen < date.today() else "À venir"


def examens_utilisateur() -> list[Examen]:
    if not st.session_state.user_id:
        return []
    return charger_examens(st.session_state.user_id)


def indisponibilites_utilisateur() -> list[Indisponibilite]:
    if not st.session_state.user_id:
        return []
    return charger_indisponibilites(st.session_state.user_id)


def afficher_message(message: str, titre: str = "Information") -> None:
    st.markdown(
        f"""
        <div class="soft-message">
            <div class="soft-message-title">{titre}</div>
            <div>{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# Style
# =============================================================================

def injecter_style() -> None:
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

            :root {{
                --fond: {PALETTE["fond"]};
                --fond-secondaire: {PALETTE["fond_secondaire"]};
                --bloc: {PALETTE["bloc"]};
                --rose-poudre: {PALETTE["rose_poudre"]};
                --rose: {PALETTE["rose"]};
                --rose-fonce: {PALETTE["rose_fonce"]};
                --lilas: {PALETTE["lilas"]};
                --champagne: {PALETTE["champagne"]};
                --ivoire: {PALETTE["ivoire"]};
                --texte: {PALETTE["texte"]};
                --texte-doux: {PALETTE["texte_doux"]};
                --bordure: {PALETTE["bordure"]};
                --ombre: {PALETTE["ombre"]};
            }}

            html, body, [class*="css"] {{
                font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
            }}

            .stApp {{
                background:
                    radial-gradient(circle at top left, rgba(247, 221, 232, 0.70), transparent 32%),
                    radial-gradient(circle at 85% 8%, rgba(220, 206, 244, 0.45), transparent 28%),
                    linear-gradient(135deg, #FFF9F8 0%, #FFFDFB 42%, #FFF4F7 100%);
                color: var(--texte);
            }}

            .block-container {{
                max-width: 1180px;
                padding-top: 2.2rem;
                padding-bottom: 4rem;
                padding-left: 2.3rem;
                padding-right: 2.3rem;
            }}

            h1, h2, h3, h4 {{
                font-family: "Cormorant Garamond", Georgia, serif;
                color: var(--rose-fonce);
                letter-spacing: -0.02em;
            }}

            h1 {{
                font-size: 3.1rem !important;
                line-height: 1.02 !important;
                margin-bottom: 0.35rem !important;
            }}

            h2 {{
                font-size: 2.05rem !important;
            }}

            h3 {{
                font-size: 1.45rem !important;
                margin-bottom: 0.6rem !important;
            }}

            p, label, div, span, li {{
                color: var(--texte);
            }}

            .page-header {{
                background:
                    linear-gradient(135deg, rgba(255,255,255,0.88), rgba(255,243,246,0.78)),
                    url("{IMAGES_AMBIANCE[0]}");
                background-size: cover;
                background-position: center;
                border: 1px solid rgba(240, 220, 230, 0.95);
                border-radius: 32px;
                padding: 2.3rem;
                min-height: 230px;
                box-shadow: 0 24px 60px var(--ombre);
                margin-bottom: 1.45rem;
                overflow: hidden;
                position: relative;
            }}

            .page-header::after {{
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(90deg, rgba(255,255,255,0.84), rgba(255,255,255,0.50));
                pointer-events: none;
            }}

            .page-header-content {{
                position: relative;
                z-index: 1;
                max-width: 720px;
            }}

            .eyebrow {{
                text-transform: uppercase;
                letter-spacing: 0.14em;
                font-size: 0.76rem;
                color: var(--rose-fonce);
                font-weight: 700;
                margin-bottom: 0.8rem;
            }}

            .subtitle {{
                color: var(--texte-doux);
                font-size: 1rem;
                line-height: 1.75;
                max-width: 720px;
            }}

            .glass-card {{
                background: rgba(255, 255, 255, 0.78);
                border: 1px solid rgba(240, 220, 230, 0.95);
                border-radius: 26px;
                padding: 1.35rem;
                box-shadow: 0 18px 42px rgba(119, 76, 96, 0.07);
                backdrop-filter: blur(18px);
                margin-bottom: 1.2rem;
            }}

            .mini-card {{
                background: rgba(255, 255, 255, 0.86);
                border: 1px solid var(--bordure);
                border-radius: 22px;
                padding: 1rem 1.1rem;
                box-shadow: 0 12px 28px rgba(119, 76, 96, 0.045);
                margin-bottom: 0.85rem;
            }}

            .quote-card {{
                background: linear-gradient(135deg, rgba(255,255,255,0.88), rgba(247,221,232,0.45));
                border: 1px solid var(--bordure);
                border-radius: 24px;
                padding: 1.15rem 1.25rem;
                box-shadow: 0 14px 34px rgba(119, 76, 96, 0.055);
                margin-bottom: 1.1rem;
            }}

            .quote-card strong {{
                font-family: "Cormorant Garamond", Georgia, serif;
                color: var(--rose-fonce);
                font-size: 1.25rem;
                font-weight: 700;
            }}

            .soft-message {{
                background: linear-gradient(135deg, rgba(255,255,255,0.88), rgba(255,243,246,0.72));
                border: 1px solid var(--bordure);
                border-radius: 20px;
                padding: 1rem 1.1rem;
                box-shadow: 0 10px 24px rgba(119, 76, 96, 0.045);
                margin: 0.8rem 0;
            }}

            .soft-message-title {{
                font-family: "Cormorant Garamond", Georgia, serif;
                color: var(--rose-fonce);
                font-size: 1.22rem;
                font-weight: 700;
                margin-bottom: 0.15rem;
            }}

            .exam-card {{
                background: rgba(255, 255, 255, 0.86);
                border: 1px solid var(--bordure);
                border-radius: 22px;
                padding: 1.1rem 1.15rem;
                box-shadow: 0 12px 30px rgba(119, 76, 96, 0.045);
                margin-bottom: 0.9rem;
            }}

            .exam-title {{
                font-family: "Cormorant Garamond", Georgia, serif;
                color: var(--rose-fonce);
                font-size: 1.35rem;
                font-weight: 700;
                margin-bottom: 0.2rem;
            }}

            .exam-meta {{
                color: var(--texte-doux);
                font-size: 0.92rem;
                margin-bottom: 0.7rem;
            }}

            .mini-tag {{
                display: inline-block;
                border: 1px solid var(--bordure);
                background: rgba(255, 243, 246, 0.85);
                border-radius: 999px;
                padding: 0.26rem 0.62rem;
                color: var(--rose-fonce);
                font-size: 0.82rem;
                font-weight: 600;
                margin-right: 0.35rem;
                margin-bottom: 0.35rem;
            }}

            .agenda-block {{
                background: linear-gradient(135deg, rgba(247,221,232,0.55), rgba(255,255,255,0.90));
                border: 1px solid var(--bordure);
                border-left: 5px solid var(--rose);
                border-radius: 20px;
                padding: 1rem 1.1rem;
                margin-bottom: 0.8rem;
                box-shadow: 0 10px 24px rgba(119, 76, 96, 0.045);
            }}

            .agenda-hour {{
                color: var(--rose-fonce);
                font-weight: 700;
                letter-spacing: 0.02em;
            }}

            .agenda-title {{
                font-family: "Cormorant Garamond", Georgia, serif;
                color: var(--rose-fonce);
                font-size: 1.25rem;
                font-weight: 700;
            }}

            .agenda-sub {{
                color: var(--texte-doux);
                font-size: 0.92rem;
            }}

            .indispo-card {{
                background: rgba(255, 243, 246, 0.85);
                border: 1px solid var(--bordure);
                border-radius: 18px;
                padding: 0.9rem 1rem;
                margin-bottom: 0.7rem;
            }}

            [data-testid="stMetric"] {{
                background: rgba(255,255,255,0.78);
                border: 1px solid var(--bordure);
                border-radius: 24px;
                padding: 1.1rem 1.15rem;
                box-shadow: 0 14px 34px rgba(119, 76, 96, 0.055);
            }}

            [data-testid="stMetricLabel"] {{
                color: var(--texte-doux);
                font-weight: 600;
            }}

            [data-testid="stMetricValue"] {{
                color: var(--rose-fonce);
                font-family: "Cormorant Garamond", Georgia, serif;
                font-size: 2rem;
            }}

            .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
                background: linear-gradient(135deg, #F7DDE8, #EEDDF7);
                color: var(--rose-fonce);
                border-radius: 999px;
                border: 1px solid var(--bordure);
                padding: 0.72rem 1.15rem;
                min-height: 2.8rem;
                box-shadow: 0 10px 22px rgba(119, 76, 96, 0.08);
                font-weight: 700;
                transition: transform 0.16s ease, box-shadow 0.16s ease, filter 0.16s ease;
            }}

            .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
                color: var(--rose-fonce);
                border-color: var(--rose);
                transform: translateY(-1px);
                box-shadow: 0 14px 28px rgba(119, 76, 96, 0.12);
                filter: brightness(1.01);
            }}

            .stButton > button[kind="primary"] {{
                background: linear-gradient(135deg, #A45C78, #7D5A8C);
                color: white;
                border-color: transparent;
            }}

            .stButton > button[kind="primary"]:hover {{
                color: white;
            }}



            section[data-testid="stSidebar"] {{
                background:
                    linear-gradient(180deg, rgba(255,243,246,0.96), rgba(255,253,251,0.96));
                border-right: 1px solid var(--bordure);
            }}

            section[data-testid="stSidebar"] .block-container {{
                padding-top: 1.6rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }}

            .sidebar-card {{
                background: rgba(255,255,255,0.72);
                border: 1px solid var(--bordure);
                border-radius: 26px;
                padding: 1.15rem;
                margin-bottom: 1rem;
                box-shadow: 0 12px 28px rgba(119, 76, 96, 0.055);
            }}

            .sidebar-name {{
                font-family: "Cormorant Garamond", Georgia, serif;
                color: var(--rose-fonce);
                font-size: 1.45rem;
                font-weight: 700;
                margin-bottom: 0.35rem;
            }}

            .sidebar-sub {{
                color: var(--texte-doux);
                line-height: 1.65;
                font-size: 0.92rem;
            }}

            .subtle {{
                color: var(--texte-doux);
                font-size: 0.94rem;
                line-height: 1.65;
            }}

            div[data-testid="stVerticalBlockBorderWrapper"] {{
                background: rgba(255,255,255,0.76) !important;
                border: 1px solid var(--bordure) !important;
                border-radius: 26px !important;
                box-shadow: 0 18px 42px rgba(119, 76, 96, 0.07) !important;
                padding: 1.3rem !important;
            }}



            .stAlert, .stDataFrame {{
                display: none;
            }}

            hr {{
                border-color: var(--bordure);
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# Session
# =============================================================================

def initialiser_session() -> None:
    valeurs_defaut = {
        "user_id": None,
        "username": None,
        "citation_revision": random.choice(CITATIONS_ET_CONSEILS),
        "agenda_genere": pd.DataFrame(),
        "page_active": "Tableau de bord",
        "agenda_jour_index": 0,
    }

    for cle, valeur in valeurs_defaut.items():
        if cle not in st.session_state:
            st.session_state[cle] = valeur


# =============================================================================
# Cartes visuelles
# =============================================================================

def header_page(titre: str, sous_titre: str, etiquette: str = "Planner de révisions") -> None:
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-header-content">
                <div class="eyebrow">{etiquette}</div>
                <h1>{titre}</h1>
                <p class="subtitle">{sous_titre}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def afficher_citation(nombre: int = 1) -> None:
    citations = random.sample(CITATIONS_ET_CONSEILS, k=min(nombre, len(CITATIONS_ET_CONSEILS)))

    for citation in citations:
        st.markdown(
            f"""
            <div class="quote-card">
                <strong>Conseils</strong><br>
                <span>{citation}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def afficher_examen_card(examen: Examen) -> None:
    statut = statut_examen(examen)
    st.markdown(
        f"""
        <div class="exam-card">
            <div class="exam-title">📁 {examen.matiere}</div>
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
            <strong>{format_date_fr(indispo.date_indispo)}</strong><br>
            <span class="subtle">{indispo.heure_debut.strftime("%H:%M")} - {indispo.heure_fin.strftime("%H:%M")}{note}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def afficher_bloc_agenda(ligne: pd.Series) -> None:
    st.markdown(
        f"""
        <div class="agenda-block">
            <div class="agenda-hour">{ligne["Début"]} - {ligne["Fin"]}</div>
            <div class="agenda-title">{ligne["Matière"]}</div>
            <div class="agenda-sub">{ligne["Tâche"]} · Examen le {ligne["Examen"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# Génération de l’agenda
# =============================================================================

def chevauche(debut_a: datetime, fin_a: datetime, debut_b: datetime, fin_b: datetime) -> bool:
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
                    "Tâche": f"Révision ciblée · {round(duree_reelle, 2)} h",
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


# =============================================================================
# Pages
# =============================================================================

def afficher_authentification() -> None:
    header_page(
        "Planning de révisions",
        "Un espace doux, rosé et structuré pour organiser tes examens avec calme, élégance et ambition.",
        "Bienvenue",
    )

    st.markdown("### Entrer dans mon espace")
    with st.form("connexion_simple"):
        username = st.text_input("Nom d’utilisateur", key="simple_username")
        submit = st.form_submit_button("Continuer", use_container_width=True)

    if submit:
        succes, message, user_id = creer_ou_recuperer_utilisateur(username)

        if not succes or user_id is None:
            afficher_message(message, "Connexion")
        else:
            st.session_state.user_id = user_id
            st.session_state.username = username.strip()
            st.rerun()

    st.markdown(
        '<p class="subtle">Si le nom existe déjà, tu retrouves tes anciennes entrées. Sinon, un nouvel espace est créé automatiquement.</p>',
        unsafe_allow_html=True,
    )


def afficher_indicateurs(examens: list[Examen]) -> None:
    aujourd_hui = date.today()
    total = len(examens)
    a_venir = len([ex for ex in examens if ex.date_examen >= aujourd_hui])
    passes = len([ex for ex in examens if ex.date_examen < aujourd_hui])
    heures_restantes = sum(ex.heures_restantes for ex in examens if ex.date_examen >= aujourd_hui)
    ects_total = sum(ex.ects for ex in examens)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Examens", total)
    col2.metric("À venir", a_venir)
    col3.metric("ECTS cumulés", f"{ects_total:.1f}")
    col4.metric("Heures restantes", f"{heures_restantes:.1f} h")

    if passes:
        st.markdown(
            f'<p class="subtle">{passes} examen(s) passé(s) restent visibles dans le résumé, mais jamais dans l’agenda.</p>',
            unsafe_allow_html=True,
        )


def page_tableau_de_bord(examens: list[Examen]) -> None:
    header_page(
        f"Bonjour {st.session_state.username}",
        "Ton espace transforme ta charge de travail en plan clair, réaliste et motivant.",
        "Tableau de bord",
    )

    afficher_indicateurs(examens)

    col1, col2 = st.columns([1.25, 0.75], gap="large")

    with col1:
        examens_a_venir = [ex for ex in examens if ex.date_examen >= date.today()]

        if examens_a_venir:
            plus_proche = min(examens_a_venir, key=lambda ex: ex.date_examen)

            st.markdown(
                f"""
                <div class="glass-card">
                    <h3>Priorité actuelle</h3>
                    <p><strong>{plus_proche.matiere}</strong> · examen le {format_date_fr(plus_proche.date_examen)}</p>
                    <p>{plus_proche.heures_restantes:.1f} h restantes sur {plus_proche.heures_totales:.1f} h au total.</p>
                    <p class="subtle">Le planning favorisera cette matière si la date approche ou si la charge restante reste élevée.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            afficher_message(
                "Aucun examen à venir pour le moment. Tu peux en ajouter dans la page Mes examens.",
                "Espace calme",
            )

    with col2:
        afficher_citation(nombre=2)


def page_examens(examens: list[Examen]) -> None:
    header_page(
        "Mes examens",
        "Ajoute tes matières, suis ton avancement et garde une vision claire de ce qu’il te reste à conquérir.",
        "Organisation académique",
    )

    gauche, droite = st.columns([1, 1.15], gap="large")

    with gauche:
        st.markdown("### Ajouter un examen")

        with st.form("ajout_examen", clear_on_submit=True):
            matiere = st.text_input("Nom de la matière", placeholder="Ex. Finance publique")
            date_examen = st.date_input(
                "Date de l’examen",
                value=date.today() + timedelta(days=10),
                format="DD/MM/YYYY",
            )
            ects = st.number_input(
                "Nombre d’ECTS",
                min_value=0.5,
                max_value=30.0,
                value=3.0,
                step=0.5,
            )
            heures_effectuees = st.number_input(
                "Heures déjà travaillées",
                min_value=0.0,
                max_value=500.0,
                value=0.0,
                step=0.5,
            )

            total_calcule = ects * HEURES_PAR_ECTS
            restant_calcule = max(0.0, total_calcule - heures_effectuees)

            st.markdown(
                f"""
                <div class="soft-message">
                    <div class="soft-message-title">Calcul des heures</div>
                    {ects:.1f} ECTS = {total_calcule:.1f} h de travail · {restant_calcule:.1f} h restantes.
                </div>
                """,
                unsafe_allow_html=True,
            )

            submit = st.form_submit_button("Enregistrer l’examen", use_container_width=True)

        if submit:
            if not matiere.strip():
                afficher_message("Entre d’abord le nom de la matière.", "Champ manquant")
            else:
                ajouter_examen_db(
                    st.session_state.user_id,
                    matiere,
                    date_examen,
                    ects,
                    min(heures_effectuees, total_calcule),
                )
                st.session_state.agenda_genere = pd.DataFrame()
                st.rerun()

    with droite:
        st.markdown("### Résumé")

        if not examens:
            afficher_message("Aucun examen enregistré pour l’instant.", "Résumé vide")
        else:
            for examen in examens:
                afficher_examen_card(examen)

                col_a, col_b = st.columns([1.15, 0.85], gap="medium")

                with col_a:
                    nouvelles_heures = st.number_input(
                        f"Heures déjà effectuées · {examen.matiere}",
                        min_value=0.0,
                        max_value=float(examen.heures_totales),
                        value=float(min(examen.heures_effectuees, examen.heures_totales)),
                        step=0.5,
                        key=f"progression_{examen.id}",
                    )

                with col_b:
                    st.write("")
                    st.write("")

                    if st.button("Mettre à jour", use_container_width=True, key=f"maj_{examen.id}"):
                        mettre_a_jour_heures_db(
                            examen.id,
                            st.session_state.user_id,
                            nouvelles_heures,
                        )
                        st.session_state.agenda_genere = pd.DataFrame()
                        st.rerun()

                    if st.button("Supprimer", use_container_width=True, key=f"supprimer_{examen.id}"):
                        supprimer_examen_db(examen.id, st.session_state.user_id)
                        st.session_state.agenda_genere = pd.DataFrame()
                        st.rerun()


def parametres_agenda() -> tuple[float, float, int, bool]:
    st.markdown("### Paramètres de génération")

    heures_semaine = st.number_input(
        "Temps de révision par jour en semaine",
        min_value=1.0,
        max_value=14.0,
        value=3.0,
        step=0.5,
    )
    heures_weekend = st.number_input(
        "Temps de révision par jour le week-end",
        min_value=1.0,
        max_value=14.0,
        value=4.5,
        step=0.5,
    )
    duree_creneau = st.number_input(
        "Durée d’un créneau (minutes)",
        min_value=30,
        max_value=180,
        value=60,
        step=15,
    )

    lancer = st.button("Générer mon agenda visuel", use_container_width=True)

    return heures_semaine, heures_weekend, duree_creneau, lancer


def afficher_agenda_visuel(df_agenda: pd.DataFrame) -> None:
    if df_agenda.empty:
        afficher_message(
            "Aucun créneau à afficher. Les examens passés sont exclus de l’agenda.",
            "Agenda vide",
        )
        return

    if "Tâche" not in df_agenda.columns:
        df_agenda = df_agenda.copy()
        df_agenda["Tâche"] = df_agenda.get("Durée (h)", 0).apply(
            lambda valeur: f"Révision ciblée · {valeur} h"
        )

    jours = list(df_agenda.groupby("Date", sort=False))

    st.session_state.agenda_jour_index = min(
        st.session_state.agenda_jour_index,
        max(len(jours) - 1, 0),
    )

    col_prev, col_title, col_next = st.columns([1, 3, 1])

    with col_prev:
        if st.button(
            "<",
            use_container_width=True,
            disabled=st.session_state.agenda_jour_index == 0,
        ):
            st.session_state.agenda_jour_index -= 1
            st.rerun()

    with col_title:
        jour, groupe = jours[st.session_state.agenda_jour_index]
        st.markdown(
            f"""
            <div class="glass-card" style="text-align:center;">
                <h3>{jour}</h3>
                <p class="subtle">Jour {st.session_state.agenda_jour_index + 1} / {len(jours)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_next:
        if st.button(
            ">",
            use_container_width=True,
            disabled=st.session_state.agenda_jour_index >= len(jours) - 1,
        ):
            st.session_state.agenda_jour_index += 1
            st.rerun()

    for _, ligne in groupe.iterrows():
        afficher_bloc_agenda(ligne)

    with st.container(border=True):
        st.markdown("### Vue compacte des jours")
        chips = [f'<span class="mini-tag">{jour}</span>' for jour, _ in jours]
        st.markdown("".join(chips), unsafe_allow_html=True)


def page_agenda(examens: list[Examen]) -> None:
    header_page(
        "Mon agenda de révisions",
        "Génère automatiquement des créneaux réalistes en tenant compte de tes examens, de tes ECTS et de tes indisponibilités.",
        "Planification",
    )

    if not examens:
        afficher_message("Ajoute d’abord des examens pour générer un agenda.", "Avant de commencer")
        return

    indisponibilites = indisponibilites_utilisateur()

    gauche, droite = st.columns([0.9, 1.1], gap="large")

    with gauche:
        heures_semaine, heures_weekend, duree_creneau, lancer = parametres_agenda()

        st.markdown("### Mes indisponibilités")

        with st.form("ajout_indisponibilite", clear_on_submit=True):
            date_indispo = st.date_input(
                "Date indisponible",
                value=date.today(),
                format="DD/MM/YYYY",
                key="date_indispo",
            )

            col1, col2 = st.columns(2)

            with col1:
                heure_debut = st.time_input("Heure de début", value=time(hour=12, minute=0), step=900)

            with col2:
                heure_fin = st.time_input("Heure de fin", value=time(hour=14, minute=0), step=900)

            note = st.text_input("Note optionnelle", placeholder="Cours, travail, rendez-vous")
            ajouter = st.form_submit_button("Ajouter cette indisponibilité", use_container_width=True)

        if ajouter:
            if heure_fin <= heure_debut:
                afficher_message("L’heure de fin doit être après l’heure de début.", "Indisponibilité")
            else:
                ajouter_indisponibilite_db(
                    st.session_state.user_id,
                    date_indispo,
                    heure_debut,
                    heure_fin,
                    note,
                )
                st.session_state.agenda_genere = pd.DataFrame()
                st.rerun()

        if indisponibilites:
            for indispo in indisponibilites:
                afficher_indisponibilite_card(indispo)

                if st.button(
                    "Supprimer ce bloc",
                    key=f"indispo_{indispo.id}",
                    use_container_width=False,
                ):
                    supprimer_indisponibilite_db(indispo.id, st.session_state.user_id)
                    st.session_state.agenda_genere = pd.DataFrame()
                    st.rerun()
        else:
            afficher_message("Aucune indisponibilité enregistrée pour le moment.", "Disponibilité")

    with droite:
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
                "Génère l’agenda pour voir une version visuelle de tes créneaux.",
                "Planning à générer",
            )
            afficher_citation(nombre=2)


def page_conseils(examens: list[Examen]) -> None:
    header_page(
        "Conseils et méthode",
        "Une bibliothèque de rappels stratégiques pour réviser avec plus de clarté, de mémoire et de confiance.",
        "Méthode",
    )

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        afficher_citation(nombre=5)

    with col2:
        with st.container(border=True):
            st.markdown("### Comment l’application calcule tes heures")
            st.markdown(
                """
                Chaque ECTS vaut **30 heures de travail**.

                **Heures totales = ECTS × 30**

                **Heures restantes = heures totales - heures déjà effectuées**
                """
            )

        if examens:
            with st.container(border=True):
                st.markdown("### Tes examens")
                for examen in examens:
                    afficher_examen_card(examen)


# =============================================================================
# Navigation
# =============================================================================

def barre_laterale() -> str:
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-card">
                <div class="sidebar-name">Bonjour {st.session_state.username}</div>
                <div class="sidebar-sub">Ton planner rosé, clair et organisé. Une petite base de contrôle pour réviser sans chaos.</div>
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

        if st.button("Se déconnecter", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.agenda_genere = pd.DataFrame()
            st.session_state.page_active = "Tableau de bord"
            st.rerun()

    return st.session_state.page_active


# =============================================================================
# Application
# =============================================================================

def main() -> None:
    st.set_page_config(
        page_title="Planning de révisions",
        page_icon="🌷",
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

