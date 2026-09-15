# gui/main_window.py

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QLabel, QStatusBar, QPushButton
)
from PyQt6.QtCore import Qt

# Import de ton objet Projet existant
from core.project import Project


class MainWindow(QMainWindow):
    """
    Fenêtre principale de l'application Archéomètre.
    Gère la coquille de l'IHM, les menus et l'instance active du Project.
    """

    def __init__(self):
        super().__init__()

        self.projet: Project | None = None
        self.chemin_yaml_actuel: Path | None = None

        self._initialiser_ui()

    def _initialiser_ui(self) -> None:
        """Configuration des composants graphiques de base."""
        self.setWindowTitle("Archéomètre - Studio de Simulation Magique")
        self.resize(1100, 750)

        # 1. Barre de Menu
        self._creer_menu()

        # 2. Zone Centrale (Layout temporaire avant l'intégration carte / configurateur)
        widget_central = QWidget(self)
        self.setCentralWidget(widget_central)

        layout_principal = QVBoxLayout(widget_central)

        # Indicateur d'état du projet chargé
        self.label_statut = QLabel("Aucun projet chargé. Ouvrez un fichier config.yaml pour démarrer.")
        self.label_statut.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_statut.setStyleSheet("font-size: 14px; color: #666; font-style: italic;")
        layout_principal.addWidget(self.label_statut)

        # 3. Barre d'état (Status Bar)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt.")

    def _creer_menu(self) -> None:
        """Crée la barre de menus (Fichier, Simulation, etc.)."""
        barre_menu = self.menuBar()

        # Menu Fichier
        menu_fichier = barre_menu.addMenu("&Fichier")

        action_ouvrir = menu_fichier.addAction("&Ouvrir une configuration...")
        action_ouvrir.setShortcut("Ctrl+O")
        action_ouvrir.triggered.connect(self._action_ouvrir_config)

        action_sauvegarder = menu_fichier.addAction("&Enregistrer")
        action_sauvegarder.setShortcut("Ctrl+S")
        action_sauvegarder.triggered.connect(self._action_sauvegarder_config)

        action_sauvegarder_sous = menu_fichier.addAction("Enregistrer &sous...")
        action_sauvegarder_sous.setShortcut("Ctrl+Shift+S")
        action_sauvegarder_sous.triggered.connect(self._action_sauvegarder_sous_config)

        menu_fichier.addSeparator()

        action_quitter = menu_fichier.addAction("&Quitter")
        action_quitter.setShortcut("Ctrl+Q")
        action_quitter.triggered.connect(self.close)

    # --- LOGIQUE D'INTÉGRATION AVEC L'OBJET PROJET ---

    def _action_ouvrir_config(self) -> None:
        """Ouvre un dialogue pour sélectionner un dossier de projet ou un fichier de configuration."""
        # On permet de sélectionner soit project.json, soit config.yaml, soit directement le dossier
        fichier, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un projet Archéomètre",
            "",
            "Fichiers de projet (*.json *.yaml *.yml);;Tous les fichiers (*)"
        )

        if fichier:
            chemin = Path(fichier)
            # Si l'utilisateur a sélectionné config.yaml ou project.json, le dossier du projet est son parent
            dossier_projet = chemin.parent if chemin.is_file() else chemin
            self.charger_projet(dossier_projet)

    def charger_projet(self, dossier_projet: Path) -> None:
        """Instancie le projet via Project.charger() et met à jour l'IHM."""
        try:
            # Appel direct de la méthode de classe de ton objet Project
            self.project = Project.charger(dossier_projet)
            self.chemin_dossier_actuel = dossier_projet

            # Récupération des informations pour la mise à jour de l'affichage
            nom_projet = self.project.nom

            # Si la config est chargée sur l'instance self.project (ex: self.project.config)
            cfg_info = ""
            if hasattr(self.project, "config") and self.project.config:
                cfg = self.project.config
                cfg_info = (
                    f"<br><b>Grille :</b> {cfg.largeur}x{cfg.hauteur} px | "
                    f"<b>Pas de temps :</b> {cfg.pas_de_temps_total} steps | "
                    f"<b>Nœuds :</b> {len(cfg.noeuds)} | "
                    f"<b>Perturbations :</b> {len(cfg.perturbations)}"
                )

            info_texte = (
                f"<b>Projet chargé :</b> {nom_projet}<br>"
                f"<b>Racine :</b> <code>{self.project.dossier_racine}</code>"
                f"{cfg_info}"
            )
            self.label_statut.setText(info_texte)
            self.label_statut.setStyleSheet("font-size: 14px; color: #222;")

            self.setWindowTitle(f"Archéomètre - {nom_projet}")
            self.status_bar.showMessage(f"Projet chargé depuis : {dossier_projet}", 5000)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur de chargement",
                f"Impossible de charger le projet depuis {dossier_projet} :\n{str(e)}"
            )
            self.status_bar.showMessage("Erreur lors du chargement.", 5000)

    def _action_sauvegarder_config(self) -> None:
        """Sauvegarde la configuration actuelle."""
        if not self.projet or not self.chemin_yaml_actuel:
            QMessageBox.warning(self, "Avertissement", "Aucun projet à sauvegarder.")
            return

        self.sauvegarder_projet(self.chemin_yaml_actuel)

    def _action_sauvegarder_sous_config(self) -> None:
        """Sauvegarde sous un nouveau fichier."""
        if not self.projet:
            QMessageBox.warning(self, "Avertissement", "Aucun projet à sauvegarder.")
            return

        fichier, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer la configuration sous...",
            str(self.chemin_yaml_actuel or ""),
            "Fichiers YAML (*.yaml *.yml)"
        )

        if fichier:
            self.sauvegarder_projet(Path(fichier))

    def sauvegarder_projet(self, chemin_destination: Path) -> None:
        """Exporte l'état actuel de la configuration dans le YAML spécifié."""
        try:
            # Si ta classe Projet ou ConfigLoader possède une méthode d'export YAML, l'appeler ici.
            # Exemple : self.projet.sauvegarder_config(str(chemin_destination))

            self.chemin_yaml_actuel = chemin_destination
            self.setWindowTitle(f"Archéomètre - {chemin_destination.name}")
            self.status_bar.showMessage(f"Configuration enregistrée dans : {chemin_destination}", 5000)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur de sauvegarde",
                f"Erreur lors de l'enregistrement de la configuration :\n{str(e)}"
            )