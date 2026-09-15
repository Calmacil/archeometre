# core/engine.py

from typing import Dict
import numpy as np
from scipy.ndimage import map_coordinates

from .config import ConfigurationSimulation
from .enums import ElementKa
from .astrology import HorlogeAstrologique


class Engine:
    """
    Moteur de simulation magique basé sur NumPy et SciPy.
    Gère la diffusion laplacienne 2D, l'advection par les vents,
    la dissipation et les injections temporelles.
    """

    def __init__(self, config: ConfigurationSimulation):
        self.config = config
        self.H = config.hauteur
        self.W = config.largeur
        self.T = config.pas_de_temps_total

        # Instanciation de l'horloge astrologique
        self.horloge = HorlogeAstrologique(
            date_debut=config.temps.date_debut,
            duree_pas_str=config.temps.duree_pas_de_temps,
            facteur_hebdo=config.temps.facteur_hebdomadaire_base,
            facteur_zodiacal=config.temps.facteur_zodiacal_base,
            malus_samedi=config.temps.malus_orichalque_samedi,
            malus_verseau=config.temps.malus_orichalque_verseau,
        )

        # Allocations des grilles 3D pour chaque élément de Ka
        self.champs: Dict[ElementKa, np.ndarray] = {
            element: np.zeros((self.T, self.H, self.W), dtype=np.float32)
            for element in ElementKa
        }

        # Grilles 3D pour les champs vectoriels (vent_x, vent_y)
        self.vent_x = np.zeros((self.T, self.H, self.W), dtype=np.float32)
        self.vent_y = np.zeros((self.T, self.H, self.W), dtype=np.float32)

        # Copie de travail de la réserve des Nœuds
        self.reserves_noeuds = {
            noeud.id: float(noeud.reserve_courante) for noeud in self.config.noeuds
        }

        # Application des conditions initiales à t=0
        self._injecter_sources(t=0)
        self._mettre_a_jour_vents(t=0)

    def simuler(self) -> None:
        """Déroule la boucle temporelle complète de t = 0 à T-1."""
        for t in range(0, self.T - 1):
            self.calculer_pas_suivant(t)

    def calculer_pas_suivant(self, t: int) -> None:
        """Calcule l'état de la grille au pas t+1 à partir de l'état au pas t."""
        t_next = t + 1

        # Récupération des modificateurs astrologiques au pas t
        modificateurs = self.horloge.Calculer_modificateurs(t)

        # 1. Mise à jour des vents pour le pas courant
        self._mettre_a_jour_vents(t)

        vx = self.vent_x[t]
        vy = self.vent_y[t]

        for element in ElementKa:
            champ_actuel = self.champs[element][t]

            # Facteur d'amplification / réduction temporel (défaut: 1.0)
            mod_astro = np.float32(modificateurs.get(element, 1.0))

            # A. ADVECTION
            champ_advecte = self._advecter_champ(champ_actuel, vx, vy)

            # B. DIFFUSION (Spatiale / Laplacien modifiée par l'astrologie)
            alpha_base = np.float32(self.config.physique.coeff_diffusion.get(element, 0.1))
            alpha = alpha_base * mod_astro  # Multiplicateur appliqué

            laplacien = self._calculer_laplacien(champ_advecte)
            champ_diffuse = champ_advecte + alpha * laplacien

            # C. DISSIPATION / ENTROPIE
            gamma = np.float32(self.config.physique.coeff_dissipation_champ.get(element, 0.01))
            champ_final = champ_diffuse * (np.float32(1.0) - gamma)

            # Nettoyage des valeurs négatives
            np.maximum(champ_final, 0.0, out=champ_final)

            # Enregistrement pour t+1
            self.champs[element][t_next] = champ_final

        # 2. Injection des sources actives au pas t+1 avec prise en compte de l'astrologie
        # On passe les modificateurs calculés au pas t_next
        modificateurs_next = self.horloge.Calculer_modificateurs(t_next)
        self._injecter_sources(t_next, modificateurs_next)

    def _advecter_champ(self, grille: np.ndarray, vx: np.ndarray, vy: np.ndarray) -> np.ndarray:
        """
        Advection Semi-Lagrangienne :
        Pour chaque cellule (y, x), on retrouve la position d'origine (y - vy, x - vx)
        et on interpole la quantité de magie transmise.
        """
        # Génération des coordonnées de la grille
        grid_y, grid_x = np.indices((self.H, self.W), dtype=np.float32)

        # Calcul des positions d'origine ("remonter le vent")
        src_y = grid_y - vy
        src_x = grid_x - vx

        # Empaquetage pour map_coordinates (forme : [2, H, W])
        coords = np.array([src_y, src_x])

        # Interpolation bilinéaire avec gestion des bordures
        champ_transporte = map_coordinates(
            grille,
            coords,
            order=1,            # Interpolation bilinéaire (rapide et fluide)
            mode='nearest'      # Clamper aux bords de la carte
        )
        return champ_transporte.astype(np.float32)

    def _calculer_laplacien(self, grille: np.ndarray) -> np.ndarray:
        """Calcul du laplacien discret 2D (différences finies)."""
        padded = np.pad(grille, pad_width=1, mode='edge')
        laplacien = (
            padded[2:, 1:-1]
            + padded[:-2, 1:-1]
            + padded[1:-1, 2:]
            + padded[1:-1, :-2]
            - 4.0 * grille
        )
        return laplacien

    def _mettre_a_jour_vents(self, t: int) -> None:
        """
        Calcule les champs vectoriels vent_x et vent_y à partir
        des aspirations mobiles ou perturbations vectorielles au pas t.
        """
        # Réinitialisation des vents
        self.vent_x[t].fill(0.0)
        self.vent_y[t].fill(0.0)

        # Calcul de l'effet d'aspiration des perturbations/rayons
        for asp in self.config.aspirations:
            if t in asp.trajectoire:
                cy, cx = asp.trajectoire[t]

                # Grille de coordonnées locales autour du centre d'aspiration
                grid_y, grid_x = np.indices((self.H, self.W), dtype=np.float32)
                dy = cy - grid_y
                dx = cx - grid_x
                dist = np.sqrt(dx**2 + dy**2) + 1e-5  # Évite division par zéro

                masque_portee = dist <= asp.rayon_attraction

                # Le vecteur pointe vers le centre d'aspiration
                force = asp.force_aspiration * (1.0 - dist / asp.rayon_attraction)
                force = np.maximum(force, 0.0)

                self.vent_x[t] += np.where(masque_portee, (dx / dist) * force, 0.0)
                self.vent_y[t] += np.where(masque_portee, (dy / dist) * force, 0.0)

    def _injecter_sources(self, t: int, modificateurs: Dict[ElementKa, float] = None) -> None:
        """Injecte le Ka provenant des Nœuds et des Perturbations mobiles."""
        if modificateurs is None:
            modificateurs = self.horloge.Calculer_modificateurs(t)

        for noeud in self.config.noeuds:
            y, x = noeud.position
            if not (0 <= y < self.H and 0 <= x < self.W):
                continue

            reserve_disponible = self.reserves_noeuds[noeud.id]
            if reserve_disponible <= 0 and not noeud.permanent:
                continue

            for element, valeur in noeud.signature.items():
                mod_astro = np.float32(modificateurs.get(element, 1.0))
                # Valeur d'émanation modulée par l'astrologie
                val_injectee = np.float32(valeur) * mod_astro

                if not noeud.permanent:
                    gamma_noeud = self.config.physique.coeff_amortissement_noeuds.get(element, 0.02)
                    debit_reel = min(val_injectee, reserve_disponible)
                    self.champs[element][t, y, x] += np.float32(debit_reel)
                    self.reserves_noeuds[noeud.id] -= debit_reel * (1.0 + gamma_noeud)
                else:
                    self.champs[element][t, y, x] += val_injectee

        for pert in self.config.perturbations:
            if t in pert.trajectoire:
                cy, cx = pert.trajectoire[t]
                self._appliquer_zone_injection(t, cy, cx, pert.signature, pert.rayon_effet, modificateurs)

    def _appliquer_zone_injection(
        self, t: int, cy: int, cx: int, signature: Dict[ElementKa, float], rayon: int, modificateurs: Dict[ElementKa, float]
    ) -> None:
        y_min = max(0, cy - rayon)
        y_max = min(self.H, cy + rayon + 1)
        x_min = max(0, cx - rayon)
        x_max = min(self.W, cx + rayon + 1)

        y_indices, x_indices = np.ogrid[y_min:y_max, x_min:x_max]
        distances_sq = (y_indices - cy) ** 2 + (x_indices - cx) ** 2
        masque_disque = distances_sq <= (rayon ** 2)

        for element, valeur in signature.items():
            mod_astro = np.float32(modificateurs.get(element, 1.0))
            slice_courante = self.champs[element][t, y_min:y_max, x_min:x_max]
            slice_courante[masque_disque] += np.float32(valeur) * mod_astro

    def obtenir_axe_temps(self) -> list[str]:
        """Retourne la liste des timestamps ISO 8601 pour chaque pas de temps t."""
        return [
            self.horloge.Obtenir_date_pas(t).isoformat()
            for t in range(self.T)
        ]