# core/astrology.py

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from .enums import ElementKa

SIGNE_ELEMENT_MAP = {
    "Belier": ElementKa.FEU,
    "Taureau": ElementKa.TERRE,
    "Gemeaux": ElementKa.EAU,
    "Cancer": ElementKa.LUNE,
    "Lion": "SOLEIL",  # Règle spéciale : double la conjonction hebdo
    "Vierge": ElementKa.EAU,
    "Balance": ElementKa.TERRE,
    "Scorpion": ElementKa.FEU,
    "Sagittaire": ElementKa.AIR,
    "Capricorne": ElementKa.LUNE,
    "Verseau": "ORICHALQUE",  # Malus général
    "Poissons": ElementKa.EAU,
}

JOUR_ELEMENT_MAP = {
    0: ElementKa.LUNE,        # Lundi
    1: ElementKa.FEU,         # Mardi
    2: ElementKa.EAU,         # Mercredi
    3: ElementKa.AIR,         # Jeudi
    4: ElementKa.TERRE,       # Vendredi
    5: "ORICHALQUE",          # Samedi
    6: "SOLEIL",              # Dimanche : double la conjonction zodiacale
}


class HorlogeAstrologique:
    """Gère le temps et les coefficients d'influence astrologique."""

    def __init__(
        self,
        date_debut: str,
        duree_pas_str: str = "1h",
        facteur_hebdo: float = 2.0,
        facteur_zodiacal: float = 1.5,
        malus_samedi: float = 0.5,
        malus_verseau: float = 0.8,
    ):
        self.date_debut = datetime.fromisoformat(date_debut)
        self.duree_pas = self._parse_duree(duree_pas_str)
        self.facteur_hebdo = facteur_hebdo
        self.facteur_zodiacal = facteur_zodiacal
        self.malus_samedi = malus_samedi
        self.malus_verseau = malus_verseau

    @staticmethod
    def _parse_duree(duree_str: str) -> timedelta:
        unite = duree_str[-1].lower()
        valeur = int(duree_str[:-1])
        if unite == "m":
            return timedelta(minutes=valeur)
        elif unite == "h":
            return timedelta(hours=valeur)
        elif unite == "d":
            return timedelta(days=valeur)
        raise ValueError(f"Unité de temps non reconnue : {unite} (utilisez m, h ou d)")

    def Obtenir_date_pas(self, pas_de_temps: int) -> datetime:
        return self.date_debut + (pas_de_temps * self.duree_pas)

    @staticmethod
    def Obtenir_signe_zodiacal(dt: datetime) -> str:
        mois, jour = dt.month, dt.day
        if (mois == 3 and jour >= 21) or (mois == 4 and jour <= 19): return "Belier"
        if (mois == 4 and jour >= 20) or (mois == 5 and jour <= 20): return "Taureau"
        if (mois == 5 and jour >= 21) or (mois == 6 and jour <= 20): return "Gemeaux"
        if (mois == 6 and jour >= 21) or (mois == 7 and jour <= 22): return "Cancer"
        if (mois == 7 and jour >= 23) or (mois == 8 and jour <= 22): return "Lion"
        if (mois == 8 and jour >= 23) or (mois == 9 and jour <= 22): return "Vierge"
        if (mois == 9 and jour >= 23) or (mois == 10 and jour <= 22): return "Balance"
        if (mois == 10 and jour >= 23) or (mois == 11 and jour <= 21): return "Scorpion"
        if (mois == 11 and jour >= 22) or (mois == 12 and jour <= 21): return "Sagittaire"
        if (mois == 12 and jour >= 22) or (mois == 1 and jour <= 19): return "Capricorne"
        if (mois == 1 and jour >= 20) or (mois == 2 and jour <= 18): return "Verseau"
        return "Poissons"

    def Calculer_modificateurs(self, pas_de_temps: int) -> Dict[ElementKa, float]:
        """Calcul les facteurs multiplicateurs pour chaque élément à t."""
        dt = self.Obtenir_date_pas(pas_de_temps)
        signe = self.Obtenir_signe_zodiacal(dt)
        jour_semaine = dt.weekday()  # 0 = Lundi, 6 = Dimanche

        elem_hebdo = JOUR_ELEMENT_MAP[jour_semaine]
        elem_zodiacal = SIGNE_ELEMENT_MAP[signe]

        # Base 1.0 pour chaque élément
        mods: Dict[ElementKa, float] = {elem: 1.0 for elem in ElementKa}

        # 1. Traitement Hebdomadaire
        if elem_hebdo == "ORICHALQUE":
            for elem in mods:
                if elem != ElementKa.LUNE_NOIRE:
                    mods[elem] *= self.malus_samedi
        elif elem_hebdo == "SOLEIL":
            # Le dimanche double la conjonction du mois astrologique en cours !
            if isinstance(elem_zodiacal, ElementKa):
                mods[elem_zodiacal] *= (self.facteur_zodiacal * 2.0)
        elif isinstance(elem_hebdo, ElementKa):
            mods[elem_hebdo] *= self.facteur_hebdo

        # 2. Traitement Zodiacal
        if elem_zodiacal == "ORICHALQUE":
            for elem in mods:
                if elem != ElementKa.LUNE_NOIRE:
                    mods[elem] *= self.malus_verseau
        elif elem_zodiacal == "SOLEIL":
            # Le Lion double la conjonction du jour !
            if isinstance(elem_hebdo, ElementKa):
                mods[elem_hebdo] *= (self.facteur_hebdo * 2.0)
        elif isinstance(elem_zodiacal, ElementKa) and elem_hebdo != "SOLEIL":
            # Appliqué si le dimanche n'a pas déjà compté le doublement
            mods[elem_zodiacal] *= self.facteur_zodiacal

        return mods