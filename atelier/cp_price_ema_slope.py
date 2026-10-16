# -*- coding: utf-8 -*-
"""
cp_price_ema_slope.py
Comparaison EWMA60 et cours + pente de régression linéaire (fenêtre 60 points).
Lit les données OHLCV dans la base duckdb TS_DB_PATH, exporte un PNG dans TS_GFX_DIR.
"""

import os
import re
import duckdb
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")  # rendu hors écran, pas d'affichage interactif
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D

# Longueur de la fenêtre d'analyse (EWMA et régression)
FENETRE = 60


# --------------------------------------------------------------------------
# Chargement des variables d'environnement depuis .envrc
# --------------------------------------------------------------------------
def _charger_envrc(chemin_envrc):
    """
    Parse un fichier .envrc : lignes 'export VAR="value"'.
    PATH_add et autres directives ignorés.
    '$(pwd)' est remplacé par le répertoire du fichier .envrc
    (comportement équivalent à direnv).
    """
    if not os.path.isfile(chemin_envrc):
        return
    repertoire_envrc = os.path.dirname(os.path.abspath(chemin_envrc))
    with open(chemin_envrc, "r", encoding="utf-8") as fh:
        for ligne in fh:
            ligne = ligne.strip()
            if not ligne.startswith("export "):
                continue  # PATH_add et autres directives ignorées
            corps = ligne[len("export "):].strip()
            if "=" not in corps:
                continue
            nom, valeur = corps.split("=", 1)
            nom = nom.strip()
            valeur = valeur.strip().strip('"').strip("'")
            valeur = valeur.replace("$(pwd)", repertoire_envrc)
            # Expansion des variables déjà définies ($TS_ROOT, etc.)
            valeur = os.path.expandvars(valeur)
            os.environ[nom] = valeur


def _charger_environnement():
    """Charge .envrc : python-dotenv si disponible, sinon parseur maison."""
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chemin_envrc = os.path.join(racine, ".envrc")
    try:
        from dotenv import load_dotenv
        load_dotenv(chemin_envrc, override=True)
    except ImportError:
        _charger_envrc(chemin_envrc)


def _variable_obligatoire(nom):
    valeur = os.environ.get(nom)
    if not valeur:
        raise ValueError(
            f"Variable d'environnement '{nom}' absente : charger .envrc au préalable."
        )
    return valeur


# --------------------------------------------------------------------------
# Accès aux données
# --------------------------------------------------------------------------
def _charger_ohlcv(con, ticker):
    """Vérifie la table ohlcv_{ticker} puis charge les données dans un DataFrame."""
    table = f"ohlcv_{ticker}"
    present = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
        [table],
    ).fetchone()[0]
    if not present:
        raise ValueError(f"Table '{table}' absente de la base duckdb.")

    df = con.execute(
        f"SELECT Date, Open, High, Low, Close, Volume FROM {table} ORDER BY Date"
    ).df()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df


# --------------------------------------------------------------------------
# Cartouche de légende manuel (fond blanc, bord arrondi, traits pleine largeur)
# --------------------------------------------------------------------------
def _largeur_texte_px(fig, texte, fontsize=9):
    """Mesure la largeur en pixels d'un texte via le renderer courant."""
    sonde = fig.text(0, 0, texte, fontsize=fontsize)
    largeur = sonde.get_window_extent(fig.canvas.get_renderer()).width
    sonde.remove()
    return largeur


def _dessiner_cartouche(fig, ax, entrees, dpi):
    """
    Dessine en bas à droite des axes un cartouche manuel.
    entrees : liste de (libelle, couleur).
    Largeur interne = largeur du texte le plus long + 5 px de chaque côté ;
    chaque trait coloré s'étend sur toute cette largeur interne.
    """
    fontsize = 9
    marge_px = 20          # marge par rapport au bord des axes
    pad_x_px = 5           # 5 px de chaque côté du texte le plus long
    pad_y_px = 8           # marges verticales internes
    ecart_texte_trait = 3  # espace entre le libellé et son trait
    pas_entree = 26        # hauteur verticale d'une entrée

    largeurs = [_largeur_texte_px(fig, lib, fontsize) for lib, _ in entrees]
    largeur_interne_px = max(largeurs) + 2 * pad_x_px
    hauteur_px = len(entrees) * pas_entree + 2 * pad_y_px

    # Repère de position : coin bas-droit des axes
    fig.canvas.draw()
    bbox_axes = ax.get_window_extent(fig.canvas.get_renderer())
    x0_px = bbox_axes.x1 - marge_px - largeur_interne_px
    y0_px = bbox_axes.y0 + marge_px

    # Conversion pixels -> coordonnées figure (0..1)
    fig_w_px = fig.get_figwidth() * dpi
    fig_h_px = fig.get_figheight() * dpi
    inv = fig.transFigure.inverted()
    x0f, y0f = inv.transform((x0_px, y0_px))
    wf = largeur_interne_px / fig_w_px
    hf = hauteur_px / fig_h_px

    # Rectangle arrondi : fond blanc, bord 2 px
    cartouche = FancyBboxPatch(
        (x0f, y0f), wf, hf,
        boxstyle="round,pad=0.004,rounding_size=0.008",
        transform=fig.transFigure,
        facecolor="#ffffff", edgecolor="#4a291f", linewidth=2,
        zorder=20,
    )
    fig.add_artist(cartouche)

    # Entrées : libellé surmontant un trait coloré pleine largeur
    for i, (libelle, couleur) in enumerate(entrees):
        y_haut_px = y0_px + hauteur_px - pad_y_px - i * pas_entree
        xf, y_texte_f = inv.transform((x0_px + pad_x_px, y_haut_px - fontsize))
        fig.text(
            xf, y_texte_f, libelle,
            fontsize=fontsize, color="#222222",
            ha="left", va="baseline", zorder=21,
        )
        _, y_trait_f = inv.transform((0, y_haut_px - fontsize - ecart_texte_trait))
        trait = Line2D(
            [x0f + 0.002, x0f + wf - 0.002], [y_trait_f, y_trait_f],
            transform=fig.transFigure,
            color=couleur, linewidth=2.5, solid_capstyle="butt",
            zorder=21,
        )
        fig.add_artist(trait)


# --------------------------------------------------------------------------
# Fonction principale
# --------------------------------------------------------------------------
def cp_PriceEMASlope(ticker: str) -> dict:
    """
    Calcule l'EWMA60 du cours et la pente de la régression linéaire
    sur les 60 derniers points, trace le graphique et exporte un PNG.

    Retour : dict plat avec ticker, dernier cours, EWMA60, pente, dates, PNG.
    """
    if not re.fullmatch(r"[A-Za-z0-9._-]+", ticker):
        raise ValueError(f"Ticker invalide : {ticker!r}")

    _charger_environnement()
    db_path = _variable_obligatoire("TS_DB_PATH")
    gfx_dir = _variable_obligatoire("TS_GFX_DIR")
    os.makedirs(gfx_dir, exist_ok=True)

    con = duckdb.connect(db_path)
    try:
        df = _charger_ohlcv(con, ticker)
    finally:
        con.close()

    closes = df["Close"].astype(float)

    # EWMA(60) du Close, convention adjust=False
    ewma60 = closes.ewm(span=FENETRE, adjust=False).mean()

    # Régression linéaire sur la fenêtre des FENETRE derniers points
    y_fen = closes.iloc[-FENETRE:].to_numpy()
    x_fen = np.arange(FENETRE, dtype=float)
    pente, ordonnee = np.polyfit(x_fen, y_fen, 1)
    droite = pente * x_fen + ordonnee

    # Fenêtre tracée : les FENETRE derniers points
    fen_dates = df.index[-FENETRE:]
    close_fen = closes.iloc[-FENETRE:]
    ewma_fen = ewma60.iloc[-FENETRE:]

    # Affichage console
    print(f"Dernier cours ({fen_dates[-1].date()}) : {close_fen.iloc[-1]:.4f}")
    print(f"Pente régression (60 j)          : {pente:.6f} prix/jour")
    print(f"EWMA60 ({fen_dates[-1].date()})        : {ewma_fen.iloc[-1]:.4f}")

    # ------------------------------------------------------------------
    # Graphique
    # ------------------------------------------------------------------
    dpi = 150
    fig, ax = plt.subplots(figsize=(11, 6), dpi=dpi)
    fig.set_facecolor("#eeeeee")
    ax.set_facecolor("#eeeeee")

    # Remplissages cours vs EWMA60
    ax.fill_between(
        fen_dates, close_fen, ewma_fen,
        where=(close_fen > ewma_fen),
        color="#349c17", alpha=0.4, interpolate=True,
    )
    ax.fill_between(
        fen_dates, close_fen, ewma_fen,
        where=(close_fen <= ewma_fen),
        color="#b83d18", alpha=0.4, interpolate=True,
    )

    # Cours, EWMA60, droite de régression
    ax.plot(fen_dates, close_fen, color="#c7d132", linewidth=1.5, zorder=4)
    ax.plot(fen_dates, ewma_fen, color="#cfe3e3", linewidth=1.8, zorder=3)
    ax.plot(fen_dates, droite, color="#32d1ce", linewidth=1.8, linestyle="--", zorder=5)

    ax.set_title("Comparaison EWMA60 et cours + Slope")
    ax.set_ylabel("Prix")
    fig.autofmt_xdate()
    fig.tight_layout()

    # Cartouche de légende manuel
    _dessiner_cartouche(
        fig, ax,
        entrees=[
            ("Cours (Close)", "#c7d132"),
            ("Régression (pente)", "#32d1ce"),
            ("EWMA60", "#cfe3e3"),
        ],
        dpi=dpi,
    )

    chemin_png = os.path.join(gfx_dir, f"{ticker}_PxEMASlp.png")
    fig.savefig(chemin_png, dpi=dpi, facecolor="#eeeeee")
    plt.close(fig)

    return {
        "ticker": ticker,
        "date_dernier_cours": str(fen_dates[-1].date()),
        "dernier_cours": float(close_fen.iloc[-1]),
        "ewma60": float(ewma_fen.iloc[-1]),
        "pente_prix_par_jour": float(pente),
        "date_debut_fenetre": str(fen_dates[0].date()),
        "date_fin_fenetre": str(fen_dates[-1].date()),
        "fichier_graphique": chemin_png,
    }
