# core/project.py

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Optional, Union, List

from .config import ConfigurationSimulation
from .config_loader import charger_configuration
from .engine import Engine
from .io import sauvegarder_simulation_netcdf
from visualization.exporter import Exporter
from visualization.renderer import Renderer


@dataclass
class Project:
    """
    Gestionnaire d'un projet de simulation Nephilim.
    Encapsule la configuration, l'exécution et la gestion des fichiers sur disque.
    """
    nom: str
    dossier_racine: Path
    description: str = ""
    date_creation: str = field(default_factory=lambda: datetime.now().isoformat())
    date_modification: str = field(default_factory=lambda: datetime.now().isoformat())

    # Chemins internes résolus
    def __post_init__(self):
        self.dossier_racine = Path(self.dossier_racine).resolve()

    @property
    def fichier_meta(self) -> Path:
        return self.dossier_racine / "project.json"

    @property
    def fichier_config(self) -> Path:
        return self.dossier_racine / "config.yaml"

    @property
    def dossier_assets(self) -> Path:
        return self.dossier_racine / "assets"

    @property
    def dossier_outputs(self) -> Path:
        return self.dossier_racine / "outputs"

    @property
    def fichier_netcdf(self) -> Path:
        return self.dossier_outputs / "simulation.nc"

    # --- Méthodes de Gestion de Projet ---

    @classmethod
    def creer(cls, nom: str, dossier_parent: Union[str, Path], description: str = "") -> "Project":
        """Créer un nouveau projet sur le disque avec sa arborescence."""
        racine = Path(dossier_parent) / nom
        racine.mkdir(parents=True, exist_ok=True)

        projet = cls(nom=nom, dossier_racine=racine, description=description)
        projet.dossier_assets.mkdir(exist_ok=True)
        projet.dossier_outputs.mkdir(exist_ok=True)
        (projet.dossier_outputs / "exports" / "png").mkdir(parents=True, exist_ok=True)
        (projet.dossier_outputs / "exports" / "gif").mkdir(parents=True, exist_ok=True)

        projet.sauvegarder_metadonnees()
        return projet

    @classmethod
    def charger(cls, chemin_dossier_projet: Union[str, Path]) -> "Project":
        """Charger un projet existant depuis son dossier."""
        racine = Path(chemin_dossier_projet).resolve()
        meta_file = racine / "project.json"

        if not meta_file.exists():
            raise FileNotFoundError(f"Impossible de trouver project.json dans {racine}")

        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            nom=data["nom"],
            dossier_racine=racine,
            description=data.get("description", ""),
            date_creation=data.get("date_creation", ""),
            date_modification=data.get("date_modification", ""),
        )

    def sauvegarder_metadonnees(self) -> None:
        """Sauvegarder project.json avec la date à jour."""
        self.date_modification = datetime.now().isoformat()
        data = {
            "nom": self.nom,
            "description": self.description,
            "date_creation": self.date_creation,
            "date_modification": self.date_modification,
        }
        with open(self.fichier_meta, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def sauvegarder_config(self) -> None:
        """Exporte la configuration actuelle dans le fichier config.yaml du projet."""
        if not hasattr(self, "config") or self.config is None:
            return

        # Ou en direct si ConfigLoader s'en charge :
        from .config_loader import ConfigLoader
        ConfigLoader.sauvegarder(self.config, self.fichier_config)

    def sauvegarder_tout(self) -> None:
        """Sauvegarde à la fois les métadonnées json et la config yaml."""
        self.sauvegarder_metadonnees()
        self.sauvegarder_config()

    def charger_configuration(self) -> ConfigurationSimulation:
        """Charger l'objet ConfigurationSimulation associé au projet."""
        if not self.fichier_config.exists():
            raise FileNotFoundError(f"Aucun fichier config.yaml trouvé dans {self.dossier_racine}")
        return charger_configuration(self.fichier_config)

    # --- Pipeline Exécutable ---

    def executer_simulation(self) -> None:
        """Lancer la simulation NumPy et sauvegarder dans outputs/simulation.nc."""
        config = self.charger_configuration()
        engine = Engine(config)
        engine.simuler()

        axe_temps = engine.obtenir_axe_temps()

        # Délégation de l'export à io.py
        sauvegarder_simulation_netcdf(
            chemin_fichier=self.fichier_netcdf,
            champs=engine.champs,
            timestamps_iso=axe_temps,
            config=config
        )

    def exporter_animation_element(
        self, element: str, fps: int = 10, image_fond: Optional[str] = None
    ) -> Path:
        if not self.fichier_netcdf.exists():
            self.executer_simulation()

        config = self.charger_configuration()

        path_fond = None
        chemin_ref = image_fond or config.image_fond_path
        if chemin_ref:
            path_fond = (self.dossier_racine / chemin_ref).resolve()

        dir_png = self.dossier_outputs / "exports" / "png" / element
        fichier_gif = self.dossier_outputs / "exports" / "gif" / f"anim_{element}.gif"

        renderer = Renderer(
            self.fichier_netcdf,
            colormaps_personnalisees=config.render.colormaps
        )
        renderer.exporter_sequence_element(
            element=element,
            dossier_sortie=dir_png,
            image_fond_path=path_fond,
            alpha_max=config.render.alpha_max
        )
        renderer.fermer()

        return Exporter.creer_gif(
            dossier_images=dir_png,
            fichier_sortie=fichier_gif,
            fps=fps,
        )

    def exporter_animation_composite(
        self,
        elements: List[str],
        fps: int = 10,
        image_fond: Optional[str] = None
    ) -> Path:
        """
        Génère un GIF animé combinant plusieurs éléments de Ka
        superposés sur l'image de fond.
        """
        if not self.fichier_netcdf.exists():
            self.executer_simulation()

        config = self.charger_configuration()

        path_fond = None
        chemin_ref = image_fond or config.image_fond_path
        if chemin_ref:
            path_fond = (self.dossier_racine / chemin_ref).resolve()

        nom_combo = "_".join(elements)
        dir_png = self.dossier_outputs / "exports" / "png" / f"composite_{nom_combo}"
        fichier_gif = self.dossier_outputs / "exports" / "gif" / f"anim_composite_{nom_combo}.gif"

        renderer = Renderer(self.fichier_netcdf)
        renderer.exporter_sequence_composite(
            elements=elements,
            dossier_sortie=dir_png,
            image_fond_path=path_fond
        )
        renderer.fermer()

        return Exporter.creer_gif(
            dossier_images=dir_png,
            fichier_sortie=fichier_gif,
            fps=fps
        )

    def executer_rendus_parametres(self) -> List[Path]:
        """
        Exécute tous les exports PNG/GIF configurés dans la section `render` du YAML.
        """
        config = self.charger_configuration()
        render_cfg = config.render
        fichiers_generes = []

        path_fond = None
        if config.image_fond_path:
            path_fond = (self.dossier_racine / config.image_fond_path).resolve()

        renderer = Renderer(self.fichier_netcdf, colormaps_personnalisees=render_cfg.colormaps)

        # 1. Traitement des exports individuels
        for exp in render_cfg.exports_individuels:
            elem_str = exp.element.value
            dir_png = self.dossier_outputs / "exports" / "png" / elem_str
            fichier_gif = self.dossier_outputs / "exports" / "gif" / f"anim_{elem_str}.gif"

            renderer.exporter_sequence_element(
                element=elem_str,
                dossier_sortie=dir_png,
                image_fond_path=path_fond,
                alpha_max=render_cfg.alpha_max
            )

            if exp.generer_gif:
                gif = Exporter.creer_gif(dir_png, fichier_gif, fps=render_cfg.fps)
                fichiers_generes.append(gif)

            if not exp.generer_png:
                # Nettoyage automatique des PNG si seul le GIF était demandé
                for p in dir_png.glob("*.png"):
                    p.unlink()

        # 2. Traitement des exports composites
        for comp in render_cfg.exports_composites:
            elems_str = [e.value for e in comp.elements]
            dir_png = self.dossier_outputs / "exports" / "png" / f"composite_{comp.nom}"
            fichier_gif = self.dossier_outputs / "exports" / "gif" / f"anim_{comp.nom}.gif"

            renderer.exporter_sequence_composite(
                elements=elems_str,
                dossier_sortie=dir_png,
                image_fond_path=path_fond,
                alpha_max=render_cfg.alpha_max
            )

            if comp.generer_gif:
                gif = Exporter.creer_gif(dir_png, fichier_gif, fps=render_cfg.fps)
                fichiers_generes.append(gif)

            if not comp.generer_png:
                for p in dir_png.glob("*.png"):
                    p.unlink()

        renderer.fermer()
        return fichiers_generes