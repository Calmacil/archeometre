from enum import Enum
from typing import Dict, List, Tuple, Optional, Callable


class ElementKa(str, Enum):
    FEU = "ka_feu"
    EAU = "ka_eau"
    AIR = "ka_air"
    TERRE = "ka_terre"
    LUNE = "ka_lune"
    LUNE_NOIRE = "ka_lune_noire"


# Représente la charge ou l'intensité d'injection pour chaque Ka
# Exemple : {ElementKa.FEU: 12.5, ElementKa.AIR: 2.0}
SignatureKa = Dict[ElementKa, float]
