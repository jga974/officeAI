# OfficeAI 🚀

Assistant CLI pour Windows propulsé par **Google Gemini** pour l'automatisation, l'analyse et le traitement de masse de documents bureautiques (Excel, Word, CSV, etc.).

## Fonctionnalités

- 📊 **Analyse intelligente de données** : Lecture de fichiers Excel (`.xls`, `.xlsx`, `.csv`) et extraction automatique de statistiques.
- 📝 **Génération de documents Word stylisés** : Respect scrupuleux de la charte graphique d'un fichier modèle (`modele.docx`), styles de tableaux, polices, couleurs et balises Jinja2 (`docxtpl`).
- 🔄 **Traitement par lot (Batch)** : Application d'analyses ou de générations sur plusieurs fichiers avec barre de progression interactive.
- 💻 **CLI Windows moderne** : Propulsé par Typer & Rich, incluant un mode conversationnel interactif (`chat`).
- 🤖 **IA Google Gemini** : Utilise le SDK officiel `google-genai` avec auto-correction en cas d'erreur de script.

## Installation

```powershell
uv venv
uv pip install -e .
```

## Configuration

Définissez votre clé d'API Google Gemini dans une variable d'environnement ou dans un fichier `.env` :

```powershell
$env:GEMINI_API_KEY="votre_cle_api"
```

## Utilisation

```powershell
# Commande directe
officeai run "analyse les ventes dans f1.xls et génère rapport_ventes.docx selon la charte de modele.docx"

# Traitement par lot
officeai batch --pattern "*.xls" --prompt "analyse les ventes et crée un rapport Word pour chaque fichier"

# Inspection rapide d'un document
officeai inspect f1.xls
officeai inspect modele.docx

# Mode conversationnel
officeai chat
```
