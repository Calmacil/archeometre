from dataclasses import dataclass, field
from typing import Dict, List, Optional
from .enums import ElementKa
from .entities import NoeudMagique, PerturbationMobile, VecteurAspirationMobile

@dataclass
class ParametresElementaires:
    coeff_diffusion: Dict[ElementKa, float] = field(default_factory=lambda: {
        ElementKa.FEU: 0.15,
        ElementKa.EAU: 0.10,
        ElementKa.AIR: 0.25,
        ElementKa.TERRE: 0.05,
        ElementKa.LUNE: 0.12,
        ElementKa.LUNE_NOIRE: 0.20,
    })

    coeff_dissipation_champ: Dict[ElementKa, float] = field(default_factory=lambda: {
        ElementKa.FEU: 0.01,
        ElementKa.EAU: 0.01,
        ElementKa.AIR: 0.01,
        ElementKa.TERRE: 0.005,
        ElementKa.LUNE: 0.02,
        ElementKa.LUNE_NOIRE: 0.15,
    })

    coeff_amortissement_noeuds: Dict[ElementKa, float] = field(default_factory=lambda: {
        ElementKa.FEU: 0.02,
        ElementKa.EAU: 0.02,
        ElementKa.AIR: 0.02,
        ElementKa.TERRE: 0.01,
        ElementKa.LUNE: 0.03,
        ElementKa.LUNE_NOIRE: 0.10,
    })

@dataclass
class ConfigTemps:
    date_debut: str = "1890-01-01T00:00:00"
    duree_pas_de_temps: str = "1h"
    facteur_hebdomadaire_base: float = 2.0
    facteur_zodiacal_base: float = 1.5
    malus_orichalque_samedi: float = 0.5
    malus_orichalque_verseau: float = 0.8

@dataclass
class ConfigExportIndividuel:
    element: ElementKa
    generer_png: bool = True
    generer_gif: bool = True

@dataclass
class ConfigExportComposite:
    nom: str
    elements: List[ElementKa]
    generer_png: bool = True
    generer_gif: bool = True

@dataclass
class ConfigRender:
    fps: int = 10
    alpha_max: float = 0.7
    colormaps: Dict[str, str] = field(default_factory=dict)
    exports_individuels: List[ConfigExportIndividuel] = field(default_factory=list)
    exports_composites: List[ConfigExportComposite] = field(default_factory=list)

@dataclass
class ConfigurationSimulation:
    hauteur: int
    largeur: int
    pas_de_temps_total: int
    temps: ConfigTemps
    physique: ParametresElementaires
    noeuds: List[NoeudMagique] = field(default_factory=list)
    perturbations: List[PerturbationMobile] = field(default_factory=list)
    aspirations: List[VecteurAspirationMobile] = field(default_factory=list)
    render: ConfigRender = field(default_factory=ConfigRender)
    image_fond_path: Optional[str] = None