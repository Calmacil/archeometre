# core/io.py

from pathlib import Path
from typing import Dict
import numpy as np
import xarray as xr

from .config import ConfigurationSimulation
from .enums import ElementKa


def sauvegarder_simulation_netcdf(
    chemin_fichier: str | Path,
    champs: Dict[ElementKa, np.ndarray],
    timestamps_iso: list[str],
    config: ConfigurationSimulation,
) -> None:
    """
    Exporte le résultat de la simulation dans un fichier NetCDF.
    Les coordonnées temporelles sont enregistrées au format datetime64.
    """
    # 1. Conversion des dates ISO en type datetime64
    temps_coords = np.array(timestamps_iso, dtype="datetime64[ns]")

    # 2. Construction du dictionnaire des variables NetCDF
    data_vars = {}
    for element, grille_3d in champs.items():
        # grille_3d est de forme (T, H, W)
        data_vars[element.value] = (
            ("time", "y", "x"),
            grille_3d,
            {
                "long_name": f"Densité de Ka ({element.value})",
                "units": "unités de Ka",
            },
        )

    # 3. Métadonnées globales sur l'astrologie et la grille
    attributs_globaux = {
        "titre": "Simulation d'émanation de Ka",
        "date_debut_simulation": config.temps.date_debut,
        "duree_pas_de_temps": config.temps.duree_pas_de_temps,
        "facteur_hebdomadaire_base": config.temps.facteur_hebdomadaire_base,
        "facteur_zodiacal_base": config.temps.facteur_zodiacal_base,
        "hauteur_grille": config.hauteur,
        "largeur_grille": config.largeur,
    }

    # 4. Création du Dataset xarray
    ds = xr.Dataset(
        data_vars=data_vars,
        coords={
            "time": temps_coords,
            "y": np.arange(config.hauteur),
            "x": np.arange(config.largeur),
        },
        attrs=attributs_globaux,
    )

    # Enregistrement NetCDF (utilisation du moteur netcdf4 ou h5netcdf)
    ds.to_netcdf(chemin_fichier)