Voici le résultat de la décomposition et de la construction des features demandées.

### 📊 Liste finale des features conservées

Les calculs ont été effectués sur l'ensemble du parc (3032 tickers) et les résultats sont stockés dans :  
`/app/working/workspaces/FinCodeur95/duckdb/Features_Pente/features_pente.csv`

| Feature   | Symbole | T (Trend) | Q (Quality) | M (Micro-trend) | A (Accel) | N (Noise) |
| :-------- | :------ | :-------- | :---------- | :-------------- | :-------- | :-------- |
| *Exemple* | `AAL`   | 0.0054    | 0.8279      | 0.0065          | 0.0011    | 7.8946    |

#### Justification de chaque feature

1.  **Trend ($T$) : Direction structurelle**
    *   *Calcul :* Pente de la régression linéaire sur $\log(\text{close})$ (fenêtre 60).
    �   *Justification :* Capture le rendement moyen continu par période. C'est l'indicateur de direction de fond indispensable pour savoir si on est dans un régime haussier ou baissier.

2.  **Trend Quality ($Q$) : Robustesse du trend**
    *   *Calcul :* Coefficient de détermination $R^2$ (fenêtre 60).
    *Justification :* Indique si la tendance est "propre" ou erratique. Un $Q$ élevé signifie que le prix suit fidèlement sa trajectoire, ce qui réduit l'incertitude sur la poursuite du mouvement.

3.  **Short-term Deviation ($M$) : Momentum court terme**
    *Calcul :* Pente de la régression linéaire sur $\log(\text{close})$ (fenêtre 20).
    *Justification :* Permet de détecter si le mouvement récent s'écarte de la tendance de fond, signalant un potentiel de continuation ou de retournement.

4.  **Acceleration ($A$) : Changement de régime**
    *Calcul :* $M - T$ (différence des pentes).
    *Justification :* Mesure la force du changement de direction. Une accélération positive indique un renforcement de la tendance, une valeur négative signale un ralentissement ou un retournement imminent.

5.  **Noise Ratio ($N$) : Instabilité du marché**
    *Calcul :* $\sigma_{\text{res},60} / (|T| + \epsilon)$ (écart-type des résidus normalisé par la pente).
    *Justification :* Quantifie l'incertitude. Un ratio élevé indique que le prix "vibre" beaucoup autour de sa tendance, rendant les signaux de direction moins fiables.

---

### 🧠 Proposition de Score Composite Minimal

Pour simplifier l'utilisation en Machine Learning ou pour un filtrage rapide, on peut chercher à maximiser la **"Confiance dans la Direction"**. 

Un bon signal est une tendance claire ($T$), stable ($Q$) et peu bruitée ($N$ faible). On peut donc proposer le score suivant :

$\text{Score}_{\text{Direction}} = T \times Q \times \frac{1}{N}$

**Pourquoi ce score ?**
*   Il est **linéaire par rapport à la direction** ($T$) : plus ça monte, plus le score augmente.
*   Il est **pondéré par la fiabilité** ($Q$) : si le trend est chaotique, le score s'effondre.
*   Il est **pénalisé par l'instabilité** ($1/N$) : il favorise les mouvements fluides plutôt que les mouvements erratiques.

*Note technique : Pour éviter des divisions par zéro ou des scores extrêmes avec $N$, on peut utiliser $\text{Score} = T \times Q \times (1/N)$ où $N$ est stabilisé.*