# core/config_loader.py

import json
from pathlib import Path
from typing import Union
import yaml

from .config import (
    ConfigurationSimulation, ParametresElementaires, ConfigRender,
    ConfigExportIndividuel, ConfigExportComposite, ConfigTemps
)
from .entities import NoeudMagique, PerturbationMobile, VecteurAspirationMobile
from .enums import ElementKa


def charger_configuration(chemin_fichier: Union[str, Path]) -> ConfigurationSimulation:
    chemin = Path(chemin_fichier)

    with open(chemin, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) if chemin.suffix in [".yaml", ".yml"] else json.load(f)

    # Bloc TEMPS & ASTROLOGIE
    temps_data = data.get("temps", {})
    config_temps = ConfigTemps(
        date_debut=temps_data.get("date_debut", "1890-01-01T00:00:00"),
        duree_pas_de_temps=temps_data.get("duree_pas_de_temps", "1h"),
        facteur_hebdomadaire_base=float(temps_data.get("facteur_hebdomadaire_base", 2.0)),
        facteur_zodiacal_base=float(temps_data.get("facteur_zodiacal_base", 1.5)),
        malus_orichalque_samedi=float(temps_data.get("malus_orichalque_samedi", 0.5)),
        malus_orichalque_verseau=float(temps_data.get("malus_orichalque_verseau", 0.8)),
    )

    # --- 1. Bloc SIMULATION ---
    sim_data = data.get("simulation", {})

    physique_data = sim_data.get("physique", {})
    physique = ParametresElementaires()
    if "coeff_diffusion" in physique_data:
        physique.coeff_diffusion.update({
            ElementKa(k): float(v) for k, v in physique_data["coeff_diffusion"].items()
        })
    if "coeff_dissipation_champ" in physique_data:
        physique.coeff_dissipation_champ.update({
            ElementKa(k): float(v) for k, v in physique_data["coeff_dissipation_champ"].items()
        })

    noeuds = [
        NoeudMagique(
            id=n["id"],
            position=tuple(n["position"]),
            signature={ElementKa(k): float(v) for k, v in n["signature"].items()},
            reserve_initiale=float(n["reserve_initiale"]),
            permanent=n.get("permanent", False)
        ) for n in sim_data.get("noeuds", [])
    ]

    perturbations = [
        PerturbationMobile(
            id=p["id"],
            signature={ElementKa(k): float(v) for k, v in p["signature"].items()},
            trajectoire={int(t): tuple(pos) for t, pos in p["trajectoire"].items()},
            rayon_effet=p.get("rayon_effet", 1)
        ) for p in sim_data.get("perturbations", [])
    ]

    aspirations = [
        VecteurAspirationMobile(
            id=a["id"],
            trajectoire={int(t): tuple(pos) for t, pos in a["trajectoire"].items()},
            force_aspiration=float(a["force_aspiration"]),
            rayon_attraction=float(a["rayon_attraction"]),
            element_affecte=ElementKa(a["element_affecte"]) if a.get("element_affecte") else None
        ) for a in sim_data.get("aspirations", [])
    ]

    # --- 2. Bloc RENDER ---
    render_data = data.get("render", {})

    exports_indiv = [
        ConfigExportIndividuel(
            element=ElementKa(exp["element"]),
            generer_png=exp.get("generer_png", True),
            generer_gif=exp.get("generer_gif", True)
        ) for exp in render_data.get("exports_individuels", [])
    ]

    exports_comp = [
        ConfigExportComposite(
            nom=exp["nom"],
            elements=[ElementKa(e) for e in exp["elements"]],
            generer_png=exp.get("generer_png", True),
            generer_gif=exp.get("generer_gif", True)
        ) for exp in render_data.get("exports_composites", [])
    ]

    config_render = ConfigRender(
        fps=render_data.get("fps", 10),
        alpha_max=render_data.get("alpha_max", 0.7),
        colormaps=render_data.get("colormaps", {}),
        exports_individuels=exports_indiv,
        exports_composites=exports_comp
    )

    return ConfigurationSimulation(
        hauteur=data["hauteur"],
        largeur=data["largeur"],
        pas_de_temps_total=data["pas_de_temps_total"],
        temps=config_temps,
        physique=physique,
        noeuds=noeuds,
        perturbations=perturbations,
        aspirations=aspirations,
        render=config_render,
        image_fond_path=data.get("image_fond_path")
    )