# main.py

from pathlib import Path
from core.project import Project

if __name__ == "__main__":
    projet = Project.charger(Path("./projets/Affrontement_Paris_1890"))

    print("1. Simulation physique NumPy...")
    projet.executer_simulation()

    print("2. Génération automatique de tous les rendus (PNG + GIFs composites)...")
    resultats = projet.executer_rendus_parametres()

    print("\nRendus terminés avec succès :")
    for res in resultats:
        print(f" - {res.name}")