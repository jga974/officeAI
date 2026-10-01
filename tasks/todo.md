# OfficeAI - Task List & Roadmap

## Phase 1 : Initialisation & Environnement
- [x] Task 1 : Initialisation du projet `officeai` (`pyproject.toml`, configuration `uv`, structure des packages, `.env.example`).
- [x] Task 2 : Configuration & Client Gemini (`officeai/config.py`, `officeai/core/gemini_client.py` utilisant le SDK `google-genai`).

## Phase 2 : Inspecteurs Bureautiques
- [x] Task 3 : Inspecteur Excel (`officeai/inspectors/excel_inspector.py`) pour formats `.xls`, `.xlsx`, `.csv` et support OpenOffice `.ods` (échantillonnage, colonnes, types, statistiques).
- [x] Task 4 : Inspecteur Word & Charte Graphique (`officeai/inspectors/word_inspector.py`) pour extraction des styles, polices, couleurs XML et détection des balises Jinja2.

## Phase 3 : Moteur d'Exécution & Agentic Loop
- [x] Task 5 : Cloneur & Moteur de style Word (`officeai/templates/docx_styler.py` avec support hybride `python-docx` + `docxtpl`) et graphiques (`officeai/templates/chart_styler.py`).
- [x] Task 6 : Architecture Multi-LLM (`officeai/core/providers/`) avec support de Google Gemini, **Albert (LLM Souverain de l'État / DINUM)**, **Mistral AI** et mode Démo/Hors-ligne.
- [x] Task 7 : Exécuteur de scripts Python sécurisé avec boucle d'auto-correction et gestion d'encodage Windows UTF-8 (`officeai/core/runner.py`).

## Phase 4 : Moteur de Traitement par Lot (Batch) & CLI
- [x] Task 8 : Processeur de masse / batch (`officeai/batch/batch_processor.py` avec barres de progression `rich`).
- [x] Task 9 : Interface Ligne de Commande Typer (`officeai/cli.py` : commandes `run`, `batch`, `inspect`, `config`, `chat`, et commande d'onboarding `demo`).

## Phase 5 : Jeu d'Essai, Scénario & Validation Complète
- [x] Task 10 : Création du jeu d'essai multi-formats (`f1.xls`, `f2.xls`, `f3.xls`, `ventes_nationales.ods`, `modele.docx`).
- [x] Task 11 : Rédaction du guide pas-à-pas et scénario de prise en main (`SCENARIO_PRISE_EN_MAIN.md`).
- [x] Task 12 : Tests automatisés `pytest` (7/7 passés avec succès).
