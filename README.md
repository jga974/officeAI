# OfficeAI 🚀

> **Assistant CLI intelligent pour le poste de travail Windows**  
> Automatisation, analyse de données et génération de documents bureautiques haute fidélité (Excel, Word, OpenOffice, PDF), propulsé par des modèles d'IA souverains et avancés (**Google Gemini**, **Albert / DINUM - État**, **Mistral AI**).

---

## 📌 À Propos du Projet

**OfficeAI** a été conçu pour résoudre un défi quotidien rencontré par les collaborateurs, décideurs et agents administratifs : **la charge répétitive liée à l'exploitation des données et à la rédaction de rapports bureautiques formatés**.

Plutôt que d'envoyer des documents volumineux et confidentiels sur des serveurs distants, OfficeAI utilise une architecture novatrice en **Code-Interpreter local** :
1. **Inspection sémantique légère** : L'outil extrait uniquement la structure de vos fichiers (noms de colonnes, types, métadonnées de style) sans exposer vos données sensibles.
2. **Conception par l'IA** : Le modèle de langage (Gemini, Albert Souverain de l'État, ou Mistral) génère un script Python d'automatisation sur-mesure.
3. **Exécution 100% locale** : Le script s'exécute sur votre propre poste Windows en mémoire RAM, calcule les agrégats exacts et génère les livrables finaux sur votre disque.

### Le Cas d'Usage de Référence
> *"Prends le fichier `f1.xls`, analyse le nombre de ventes et génère un document Word `rapport_ventes.docx` en respectant scrupuleusement la charte graphique de `modele.docx`."*

---

## ✨ Fonctionnalités Principales

- 📊 **Prise en charge Multi-Formats** :
  - **Tableurs** : Microsoft Excel moderne (`.xlsx`), Excel 97-2003 binaire (`.xls`), OpenOffice / LibreOffice Calc (`.ods`), fichiers délimités (`.csv`, `.tsv`).
  - **Traitements de texte** : Microsoft Word (`.docx`), OpenOffice Writer (`.odt`).
  - **Modèles hybrides** : Support du clonage de charte graphique (polices, marges, styles de titres, logos) et des gabarits balisés Jinja2 (`docxtpl`).
  - **Visualisations** : Génération et intégration automatique de graphiques statistiques (`matplotlib`) harmonisés avec la palette d'entreprise.

- 🛡️ **Architecture Multi-LLM & Souveraineté** :
  - **Google Gemini** : Via le SDK officiel moderne `google-genai` (`gemini-2.5-flash`, `gemini-2.5-pro`).
  - **LLM Souverain de l'État (Albert / DINUM)** : Prêt à l'emploi pour le secteur public et les administrations françaises via l'API interministérielle.
  - **Mistral AI** : Modèles souverains européens hébergés sous cadre de confiance SecNumCloud.
  - **Mode Démo / Hors-ligne** : Scénario autonome permettant de tester immédiatement l'outil sans aucune clé d'API.

- 🔄 **Traitements de Masse (Batch Processing)** :
  - Application d'analyses ou de générations sur des dizaines de fichiers en une seule commande via des filtres glob (ex: `f*.xls`).
  - Suivi d'avancement en temps réel avec des barres de progression interactives `rich`.
  - Variables dynamiques : `{file}`, `{stem}`, `{name}`.

- ⌨️ **Ergonomie Windows & Autocomplétion** :
  - Autocomplétion dynamique avec la touche **`[TAB]`** pour compléter instantanément les noms de fichiers dans la console.
  - Commandes intégrées : `/files` (inventaire), `/inspect` (métadonnées), `/ls`.
  - Détection automatique UTF-8 garantissant l'absence de plantage d'encodage `cp1252` sur les accents et symboles monétaires (`€`).

- 🔒 **Garantie RGPD & Confidentialité** :
  - **Principe du « Zéro Donnée Brute Envoyée au Cloud »** : vos chiffres, noms de clients et données métiers ne quittent jamais votre machine.

---

## 🛠️ Installation

Le projet s'appuie sur le gestionnaire ultra-rapide **`uv`** (ou `pip`) :

```powershell
# Cloner le dépôt
git clone https://github.com/jga974/officeAI.git
cd officeAI

# Créer l'environnement virtuel et installer les dépendances
uv venv
uv pip install -e .
```

---

## ⚡ Démarrage Rapide (En 1 Seule Commande)

Pour découvrir l'outil en action sans avoir à renseigner de clé d'API, lancez le scénario guidé :

```powershell
.venv\Scripts\python.exe -m officeai.cli demo
```
Cette commande inspecte vos données d'essai, produit un rapport Word stylisé et exécute un traitement par lot en direct.

---

## 📖 Utilisation

### 1. Poser des questions ouvertes ou générales
L'IA vous répond directement dans la console sans toucher à vos fichiers :
```powershell
officeai run "quel est le cours du yen ?"
officeai run "quelle est la différence entre un fichier .xls et .xlsx ?"
```

### 2. Consulter vos fichiers locaux
```powershell
# Liste des fichiers du répertoire courant
officeai run "liste de mes fichiers ?"

# Connaître le nombre de lignes et colonnes
officeai run "nombre de lignes de f1.xls ?"
officeai run "nombre de lignes de ventes_nationales.ods ?"

# Inspection visuelle détaillée de la structure
officeai inspect f1.xls
officeai inspect modele.docx
```

### 3. Calculer et extraire des indicateurs sans créer de fichier
```powershell
officeai run "qui a fait le plus de ventes dans f1.xls ?"
```

### 4. Générer des documents Word conformes à votre charte
```powershell
officeai run "analyse les ventes dans f1.xls et génère rapport_ventes.docx en respectant la charte de modele.docx"
```

### 5. Convertir un Word ou un ODT en PDF
```powershell
officeai pdf rapport.docx          # un fichier
officeai pdf "*.docx" notes.odt    # plusieurs fichiers / motifs
officeai pdf rapport.docx --force  # ecrase un PDF existant (sinon refuse)
```
Conversion 100% locale via **LibreOffice** (a installer ; sinon definir `OFFICEAI_SOFFICE` avec le chemin de `soffice`).
Le PDF est cree a cote du source, dans le repertoire de travail. En mode chat : `/pdf rapport.docx`.

### 6. Traitement de masse (Batch)
```powershell
officeai batch --pattern "f*.xls" --prompt "analyse les ventes de {file} et génère rapport_{stem}.docx avec la charte de modele.docx" --yes
```

### 7. Mode interactif conversationnel (Chat)
```powershell
officeai chat
```
*Astuce : tapez quelques lettres et appuyez sur **`[TAB]`** pour autocompléter le nom de n'importe quel fichier.*

---

## 🔑 Configuration des Modèles d'IA

Vous pouvez sélectionner votre fournisseur d'IA selon vos impératifs de confidentialité :

| Fournisseur | Commande de configuration | Utilisation |
| :--- | :--- | :--- |
| **Google Gemini** | `officeai config --api-key <VOTRE_CLE>` | `officeai run "..." --provider gemini` |
| **LLM Souverain État (Albert)** | `$env:ALBERT_API_KEY="<CLE_DINUM>"` | `officeai run "..." --provider albert` |
| **Mistral AI** | `$env:MISTRAL_API_KEY="<CLE_MISTRAL>"` | `officeai run "..." --provider mistral` |
| **Mode Démo (Hors-ligne)** | *Aucune configuration requise* | `officeai run "..." --provider demo` |

---

## 🧪 Tests Automatisés

OfficeAI inclut une suite de tests unitaires garantissant le bon fonctionnement de tous les modules :

```powershell
.venv\Scripts\python.exe -m pytest
```

---

## 📚 En Savoir Plus

- 📋 **[Cahier des Charges & Spécifications](docs/cahier_des_charges.md)** : Vision produit, architecture technique, formats cibles et roadmap v1/v2/v3.
- 🚀 **[Scénario de Prise en Main](SCENARIO_PRISE_EN_MAIN.md)** : Guide pas-à-pas illustré pour les nouveaux utilisateurs.

---

## 📄 Licence

Ce projet est sous licence MIT. Libre d'utilisation, de modification et de distribution.
