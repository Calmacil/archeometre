# visualization/renderer.py

from pathlib import Path
from typing import Dict, List, Optional, Union
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import xarray as xr

CMAPS_ELEMENTS_DEFAUT = {
    "ka_feu": "YlOrRd",
    "ka_eau": "Blues",
    "ka_air": "YlGnBu",
    "ka_terre": "YlOrBr",
    "ka_lune": "Purples",
    "ka_lune_noire": "magma"
}


class Renderer:
    """
    Module de rendu chargé de transformer les tranches spatio-temporelles NetCDF
    en fichiers images PNG colorés avec affichage de la date.
    """

    def __init__(
        self,
        fichier_netcdf: Union[str, Path],
        colormaps_personnalisees: Optional[Dict[str, str]] = None
    ):
        self.fichier_netcdf = Path(fichier_netcdf)
        if not self.fichier_netcdf.exists():
            raise FileNotFoundError(f"Fichier NetCDF introuvable : {self.fichier_netcdf}")

        self.ds = xr.open_dataset(self.fichier_netcdf)

        # Fusion des colormaps par défaut avec celles du YAML
        self.colormaps = CMAPS_ELEMENTS_DEFAUT.copy()
        if colormaps_personnalisees:
            self.colormaps.update(colormaps_personnalisees)

    def _obtenir_titre_date(self, pas_de_temps: int) -> str:
        """Extrait et formate la date ISO du pas t pour les titres."""
        val = self.ds.coords["time"].isel(time=pas_de_temps).values
        ts = pd.to_datetime(val)
        return ts.strftime("%d/%m/%Y %H:%M")

    def _calculer_calque_element(
        self, element: str, pas_de_temps: int, alpha_max: float = 0.7
    ) -> Image.Image:
        """Génère un calque PIL RGBA pour un élément à t."""
        tranche_2d = self.ds[element].isel(time=pas_de_temps).values

        cmap_name = self.colormaps.get(element, "viridis")
        cmap = plt.get_cmap(cmap_name)

        vmax = max(1.0, float(np.nanmax(tranche_2d)))
        norm = np.clip(tranche_2d / vmax, 0.0, 1.0)

        rgba_float = cmap(norm)
        masque_visibilite = (norm > 0.01).astype(np.float32)
        rgba_float[:, :, 3] = norm * alpha_max * masque_visibilite

        rgba_uint8 = (rgba_float * 255).astype(np.uint8)
        return Image.fromarray(rgba_uint8, mode="RGBA")

    def exporter_carte_pas_de_temps(
        self,
        element: str,
        pas_de_temps: int,
        fichier_sortie: Union[str, Path],
        image_fond_path: Optional[Union[str, Path]] = None,
        alpha_max: float = 0.7,
        cmap: Optional[str] = None
    ) -> Path:
        """Génère une image PNG simple pour un seul élément avec date."""
        if element not in self.ds:
            raise KeyError(f"Variable '{element}' absente du fichier NetCDF.")

        tranche_2d = self.ds[element].isel(time=pas_de_temps).values
        hauteur, largeur = tranche_2d.shape
        date_str = self._obtenir_titre_date(pas_de_temps)

        colormap = cmap or self.colormaps.get(element, "viridis")

        dpi = 100
        fig, ax = plt.subplots(figsize=(largeur / dpi, hauteur / dpi), dpi=dpi)

        # Laisse un petit espace en haut pour le titre
        fig.subplots_adjust(left=0, right=1, bottom=0, top=0.92)

        if image_fond_path and Path(image_fond_path).exists():
            img_fond = Image.open(image_fond_path).convert("RGB")
            img_fond = img_fond.resize((largeur, hauteur))
            ax.imshow(img_fond, extent=[0, largeur, hauteur, 0])

        data_masquee = np.ma.masked_where(tranche_2d < 0.01, tranche_2d)
        vmax = max(1.0, float(np.nanmax(tranche_2d)))

        ax.imshow(
            data_masquee,
            cmap=colormap,
            alpha=alpha_max,
            vmin=0.0,
            vmax=vmax,
            extent=[0, largeur, hauteur, 0],
            interpolation="bicubic"
        )

        ax.set_title(f"{element.upper()} — {date_str}", fontsize=10, pad=4)
        ax.axis("off")

        path_sortie = Path(fichier_sortie)
        path_sortie.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(path_sortie, format="png", bbox_inches="tight", pad_inches=0.1, dpi=dpi)
        plt.close(fig)

        return path_sortie

    def exporter_sequence_element(
        self,
        element: str,
        dossier_sortie: Union[str, Path],
        image_fond_path: Optional[Union[str, Path]] = None,
        alpha_max: float = 0.7
    ) -> Path:
        """Exporte la suite complète d'images PNG pour un seul élément."""
        dossier = Path(dossier_sortie)
        dossier.mkdir(parents=True, exist_ok=True)

        nb_pas = len(self.ds.coords["time"])
        print(f"Génération de la séquence PNG pour '{element}' ({nb_pas} images)...")

        for t in range(nb_pas):
            nom_fichier = dossier / f"{element}_t{t:04d}.png"
            self.exporter_carte_pas_de_temps(
                element=element,
                pas_de_temps=t,
                fichier_sortie=nom_fichier,
                image_fond_path=image_fond_path,
                alpha_max=alpha_max
            )

        return dossier

    def exporter_carte_composite(
        self,
        elements: List[str],
        pas_de_temps: int,
        fichier_sortie: Union[str, Path],
        image_fond_path: Optional[Union[str, Path]] = None,
        alpha_max: float = 0.7
    ) -> Path:
        """Exporte une image PNG composite combinant plusieurs éléments avec date."""
        premier_elem = elements[0]
        hauteur, largeur = self.ds[premier_elem].isel(time=pas_de_temps).shape
        date_str = self._obtenir_titre_date(pas_de_temps)

        if image_fond_path and Path(image_fond_path).exists():
            base = Image.open(image_fond_path).convert("RGBA")
            base = base.resize((largeur, hauteur))
        else:
            base = Image.new("RGBA", (largeur, hauteur), (30, 30, 30, 255))

        for element in elements:
            if element not in self.ds:
                continue
            calque = self._calculer_calque_element(
                element, pas_de_temps, alpha_max=alpha_max
            )
            base = Image.alpha_composite(base, calque)

        # Incrustation de la date en incrustation sur l'image PIL composite
        draw = ImageDraw.Draw(base)
        texte = f"Composite — {date_str}"

        # Arrière-plan sombre semi-transparent sous le texte
        draw.rectangle([(8, 8), (180, 26)], fill=(0, 0, 0, 160))
        draw.text((12, 10), texte, fill=(255, 255, 255, 255))

        path_sortie = Path(fichier_sortie)
        path_sortie.parent.mkdir(parents=True, exist_ok=True)
        base.convert("RGB").save(path_sortie, format="PNG")

        return path_sortie

    def exporter_sequence_composite(
        self,
        elements: List[str],
        dossier_sortie: Union[str, Path],
        image_fond_path: Optional[Union[str, Path]] = None,
        alpha_max: float = 0.7
    ) -> Path:
        """Exporte toute la séquence temporelle composite (t=0 -> T-1)."""
        dossier = Path(dossier_sortie)
        dossier.mkdir(parents=True, exist_ok=True)

        nb_pas = len(self.ds.coords["time"])
        noms_elem = "_".join(elements)
        print(f"Génération de la séquence composite [{noms_elem}] ({nb_pas} images)...")

        for t in range(nb_pas):
            nom_fichier = dossier / f"composite_t{t:04d}.png"
            self.exporter_carte_composite(
                elements=elements,
                pas_de_temps=t,
                fichier_sortie=nom_fichier,
                image_fond_path=image_fond_path,
                alpha_max=alpha_max
            )

        return dossier

    def fermer(self) -> None:
        """Ferme proprement le fichier NetCDF."""
        self.ds.close()