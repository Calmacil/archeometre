from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
from .enums import ElementKa, SignatureKa

@dataclass
class NoeudMagique:
    """Simule les nexus et les plexus"""
    id: str
    position: Tuple[int, int]
    signature: SignatureKa
    reserve_initiale: float
    reserve_courante: float = field(init=False)
    permanent: bool = False
    
    def __post_init__(self):
        self.reserve_courante = self.reserve_initiale if not self.permanent else float('inf')

@dataclass
class PerturbationMobile:
    id: str
    signature: SignatureKa
    trajectoire: Dict[int, Tuple[int, int]]
    rayon_effet: int = 1

@dataclass
class VecteurAspirationMobile:
    id: str
    trajectoire: Dict[int, Tuple[int, int]]
    force_aspiration: float
    rayon_attraction: float
    element_affecte: Optional[ElementKa] = None
