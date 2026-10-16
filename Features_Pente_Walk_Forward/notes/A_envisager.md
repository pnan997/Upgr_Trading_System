## Faire un graphique à partir du résumé d'un run

### Objets pour le calcul du graphique 

> - Répertoires d'entrée possibles : 
    /app/working/workspaces/FinCodeur95/duckdb/Features_Pente/
    /app/working/workspaces/FinCodeur95/duckdb/Features_Pente/historique_résultats/
> - Fichier d'entrée : 
    knn_backtest.summary*.csv

### But du graphique

- Etudier l'évolution du portefeuille.
- Voir les éventuels biais et avantages
- Saisir d'un coup d'oeil la dynamique du portefeuille
- Conparer avec une tendance, une perf, un indice.

### Aspect 

> graphique principal : Courbe pertes et gains
** type : une courbe centrée sur un axe rectilige par jour (légende Temps : Non chiffré sur l'axe ) Bornes date 'Début :', 'Fin :' **
** axe x : 0 pour la position. La position est relative, ce qui donne un axe toujours = 0 **
** axe y : label : pref %  -  pas : 0.2%
  - En bleu la courbe des gains en %, avec remplissage de l'aire au dessus de l'axe 
  - En rouge la courbe des pertes en % avec remplissage de l'aire au dessous de l'axe
  - Un marqueur gap (même couleur que la courbe) pour délenchement en dessous du SL ou au dessus du TP
  - Une ligne pointillée en bleu plus foncé donnant le meilleur gain du run 
  - Une ligne pointillée en rouge plus foncé donnant la pire perte du run

> graphique secondaire 1 : Courbe de l'évolution du cash et du capital
** type : une courbe au dessus d'un axe rectiligne par jour (légende Temps : Non chiffré sur l'axe) Bornes date 'Début :', 'Fin :' **
__ remarque : On peut utiliser la même légende que l'axe x du graphique principal __
** axe x : 0 pour le montant en cash et en capital **
** axe y : labels : 'cash :', 'capital :' - Pas : 100 - Base : La valeur minimal arrondie au 100 inférieurs. Exemple : min = 15257 -> Base = 15200 **
  - En vert amande la courbe quotidienne du montant en pending_cash avec remplissage de l'aire au dessus de l'axe
  - En jaune moyen (entre vanille et citron) la courbe quotidienne du montant en capital avec remplissage de l'aire au dessus de l'axe. remplissage invisible sous la courbe en cash.

> graphique secondaire 1 : Petit histogramme cumulé cash de base, cash final, capital final
** type : Un histogramme cumulé avec couleur pour chaque partie excédentaire, et une ligne de séparation légendée du montant. Ex : Ligne cash de base : 15000 - Ligne cash final : 17500 - Ligne capital final : 37500 **
  - En noir le delta 0 - cash de base
  - En vert amande le delta cash de base  - cash final
  - En jaune moyen le delta cash final - capital final

  ### Titre général
  > Placé en haut centré avec marge verticale
  > Encadré
  > Caractères blancs sur fond vert
  > Fonte à déterminer

  ### Placement légende
  > En bas à droite. Face au petit histogramme cumulé.
  > Encadrée. Cadre de la légende aligné à droite. Texte de la légende aligné à gauche.
  > A décider : Fond dégradé bicolore?