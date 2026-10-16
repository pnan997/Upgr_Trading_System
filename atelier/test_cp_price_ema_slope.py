# -*- coding: utf-8 -*-
"""
test_cp_price_ema_slope.py
Appelle cp_PriceEMASlope("AAPL") et affiche le résultat et le PNG produit.
"""

from cp_price_ema_slope import cp_PriceEMASlope

if __name__ == "__main__":
    resultat = cp_PriceEMASlope("AAPL")
    print("\nDict retourné :")
    for cle, valeur in resultat.items():
        print(f"  {cle} : {valeur}")
    print(f"\nPNG produit : {resultat['fichier_graphique']}")
