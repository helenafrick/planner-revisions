# Planning de revisions Streamlit

Application Streamlit en francais pour generer un planning de revisions doux, realiste et intelligent.

## Fichiers importants

- `app.py` : logique principale de l'application
- `streamlit_app.py` : point d'entree simple pour Streamlit Cloud
- `requirements.txt` : dependances Python

## Lancer en local

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Publier sur Streamlit Cloud

1. Creer un depot GitHub.
2. Envoyer dedans `app.py`, `streamlit_app.py` et `requirements.txt`.
3. Aller sur [Streamlit Cloud](https://share.streamlit.io/).
4. Choisir le depot GitHub.
5. Indiquer comme fichier principal : `streamlit_app.py`.
6. Lancer le deploy.
