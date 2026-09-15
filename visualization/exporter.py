# visualization/exporter.py

from pathlib import Path
from typing import List, Union
import imageio.v2 as imageio


class Exporter:
    """
    Module responsable de l'assemblage des séquences d'images PNG
    en animations (GIF) ou vidéos (MP4).
    """

    @staticmethod
    def creer_gif(
        dossier_images: Union[str, Path],
        fichier_sortie: Union[str, Path],
        fps: int = 10,
        motif_fichier: str = "*.png"
    ) -> Path:
        """
        Lit toutes les images PNG d'un dossier et les rassemble dans un GIF animé.

        :param dossier_images: Dossier contenant les PNG (ex: 'rendu_feu')
        :param fichier_sortie: Chemin du fichier GIF final (ex: 'animation_feu.gif')
        :param fps: Images par seconde (Frames Per Second)
        :param motif_fichier: Pattern de recherche des fichiers (ex: '*.png')
        """
        dossier = Path(dossier_images)
        path_sortie = Path(fichier_sortie)

        if not dossier.exists():
            raise FileNotFoundError(f"Le dossier d'images n'existe pas : {dossier}")

        # Récupération et tri alphabétique/numérique des images (ex: ka_feu_t0000.png, ka_feu_t0001.png)
        fichiers_images: List[Path] = sorted(list(dossier.glob(motif_fichier)))

        if not fichiers_images:
            raise FileNotFoundError(f"Aucune image trouvée avec le motif '{motif_fichier}' dans {dossier}")

        print(f"Compilation de {len(fichiers_images)} images dans {path_sortie.name} ({fps} FPS)...")

        # Lecture des images avec imageio
        images = []
        for img_path in fichiers_images:
            images.append(imageio.imread(img_path))

        # Assure que le dossier parent de sortie existe
        path_sortie.parent.mkdir(parents=True, exist_ok=True)

        # Calcul de la durée par image en millisecondes
        duration = 1000 / fps

        # Écriture du fichier GIF
        imageio.mimsave(path_sortie, images, duration=duration, loop=0)

        print(f"GIF généré avec succès : {path_sortie.resolve()}")
        return path_sortie

    @staticmethod
    def creer_mp4(
        dossier_images: Union[str, Path],
        fichier_sortie: Union[str, Path],
        fps: int = 15,
        motif_fichier: str = "*.png"
    ) -> Path:
        """
        Compile les PNG en vidéo MP4.
        Nécessite le paquet `imageio-ffmpeg` (pip install imageio-ffmpeg).
        """
        dossier = Path(dossier_images)
        path_sortie = Path(fichier_sortie)

        fichiers_images = sorted(list(dossier.glob(motif_fichier)))
        if not fichiers_images:
            raise FileNotFoundError(f"Aucune image trouvée dans {dossier}")

        print(f"Compilation MP4 de {len(fichiers_images)} images vers {path_sortie.name}...")

        writer = imageio.get_writer(path_sortie, fps=fps, codec="libx264")
        for img_path in fichiers_images:
            writer.append_data(imageio.imread(img_path))
        writer.close()

        print(f"Vidéo MP4 générée : {path_sortie.resolve()}")
        return path_sortie