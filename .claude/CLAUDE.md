## Environment

Host environment: ~/Trading_System 

## Important notice

>**Toute création ou modification de code Python opérationnel doit être déléguée à l'agent codeur préférentiellement.**

## Structure of the current project (and how any other should be 😀)

- atelier : Where all the work in progress, samples, parameters and tests should go
- historique_résultats : Where all previous results go after differerent runs for further reference
- notes : User's personnal notes regarding refinement, bugs to correct later, ideas, etc.
- potentiel : Where promising work go for deeper tests before going to production.
- production : Where all projects should go at the end. One day, maybe... 
other files are immediate results, other (older) parameters, input files, minor texts, etc.

### duckdb database : 

See appropriate skill.

## Contexte spécifique sur le paper trading IBKR :

Le processus de paper trading se déroule en deux parties :
1. Pipeline de prévision (exécuté chaque matin à ~11h00) qui génère les recommandations
2. Execution IBKR (exécuté chaque jour à 15h00) qui exécute les ordres basés sur les recommandations

### Logique de calcul :
- Le script lit le solde disponible et toutes les positions ouvertes dans IBKR
- Il calcule le capital disponible pour les nouveaux achats
- Il détecte les déviations critiques et s'arrête si elles dépassent le seuil (5% du cash disponible)

## Access to the host environment :
- For everydays' use, only access to /Users/pnan9/my_files 
- ** Any other directory should be accessed very cautiously, on user's request and under his authority only! ** 

## Conversation form rules :
**Merci de faire les réponses en français! **

## Fichiers coomplémentaires à lire immédiatement 
@/Users/pnan9/.claude/projects/-Users-pnan9-Trading-System/memory/ibkr_paper_trade_complete_process_summary.md
