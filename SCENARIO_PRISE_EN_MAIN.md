# Guide & Scénario de Prise en Main : OfficeAI 🚀

Bienvenue dans le scénario de prise en main d'**OfficeAI**. Ce guide est conçu pour vous accompagner pas-à-pas dans l'utilisation de l'assistant bureautique sur votre poste de travail Windows.

---

## 📁 1. Fichiers d'Exemple Disponibles

Votre espace de travail est déjà équipé d'un jeu d'essai complet :

| Fichier | Format | Description |
| :--- | :--- | :--- |
| [`f1.xls`](file:///C:/Users/jga97/Nextcloud/python/officeAI/f1.xls) | Excel 97-2003 (`.xls`) | Données de ventes régionales avec montants et quantités. |
| [`f2.xls`](file:///C:/Users/jga97/Nextcloud/python/officeAI/f2.xls), [`f3.xls`](file:///C:/Users/jga97/Nextcloud/python/officeAI/f3.xls) | Excel 97-2003 (`.xls`) | Fichiers complémentaires pour les tests de traitement par lot (Batch). |
| [`ventes_nationales.ods`](file:///C:/Users/jga97/Nextcloud/python/officeAI/ventes_nationales.ods) | OpenOffice / LibreOffice Calc (`.ods`) | Tableau de suivi d'activité OpenDocument. |
| [`modele.docx`](file:///C:/Users/jga97/Nextcloud/python/officeAI/modele.docx) | Microsoft Word (`.docx`) | Document de référence portant la charte graphique (Bleu marine `#1F497D`, polices Calibri, en-tête et pied de page institutionnels). |

---

## ⚡ 2. Démarrage Express en 1 Commande (Mode Démo)

Pour voir l'outil fonctionner immédiatement sans configuration préalable de clé d'API, lancez :

```powershell
.venv\Scripts\python.exe -m officeai.cli demo
```

Cette commande exécute automatiquement les 3 étapes clés :
1. **Inspection** des structures du tableur et de la charte graphique Word.
2. **Génération d'un rapport** [`rapport_ventes.docx`](file:///C:/Users/jga97/Nextcloud/python/officeAI/rapport_ventes.docx) respectant les styles du modèle.
3. **Traitement par lot** sur `f1.xls`, `f2.xls`, `f3.xls` générant 3 rapports distincts avec barre de progression.

---

## 🔍 3. Parcours Guidé Étape par Étape

### Étape 1 : Inspecter un document (Excel ou OpenOffice)
Avant de lancer une analyse, l'inspecteur permet de visualiser instantanément les colonnes, les types et un échantillon :

```powershell
# Inspection du fichier Excel binaire (.xls)
.venv\Scripts\python.exe -m officeai.cli inspect f1.xls

# Inspection du fichier OpenOffice Calc (.ods)
.venv\Scripts\python.exe -m officeai.cli inspect ventes_nationales.ods

# Inspection de la charte graphique du document Word
.venv\Scripts\python.exe -m officeai.cli inspect modele.docx
```

---

### Étape 2 : Analyser et générer un rapport stylisé
Demandez en langage naturel l'analyse de vos données :

```powershell
# Traitement sur Excel (.xls) avec application de la charte graphique de modele.docx
.venv\Scripts\python.exe -m officeai.cli run "analyse les ventes dans f1.xls et genere rapport_ventes.docx en respectant la charte de modele.docx"

# Traitement sur OpenOffice (.ods)
.venv\Scripts\python.exe -m officeai.cli run "analyse les ventes dans ventes_nationales.ods et cree synthese_nationale.docx avec les styles de modele.docx"
```

*L'IA vous présente la démarche, le script Python généré, et vous demande confirmation avant d'écrire le fichier sur votre disque.*

---

### Étape 3 : Traitement de masse (Batch)
Pour traiter automatiquement tous les fichiers correspondants à un motif dans le répertoire courant :

```powershell
.venv\Scripts\python.exe -m officeai.cli batch --pattern "f*.xls" --prompt "analyse les ventes de {file} et genere rapport_{stem}.docx avec la charte de modele.docx" --yes
```

---

### Étape 4 : Mode Conversationnel (Chat)
Pour dialoguer directement avec l'assistant bureautique dans votre terminal :

```powershell
.venv\Scripts\python.exe -m officeai.cli chat
```

---

## 🛡️ 4. Choix du Fournisseur d'IA & Souveraineté

OfficeAI supporte plusieurs moteurs d'IA interchangeables :

### Option A : Google Gemini (Par défaut)
```powershell
# Configuration de votre clé (gratuite sur aistudio.google.com)
.venv\Scripts\python.exe -m officeai.cli config --api-key "VOTRE_CLE_GEMINI"

# Exécution avec Gemini
.venv\Scripts\python.exe -m officeai.cli run "..." --provider gemini
```

### Option B : LLM Souverain de l'État (Albert / DINUM)
Pour les administrations et collectivités soumises au cadre de confiance et à la souveraineté des données :
```powershell
# Définition de la clé d'API Albert (DINUM)
$env:ALBERT_API_KEY = "votre_cle_albert"

# Exécution avec le LLM Souverain
.venv\Scripts\python.exe -m officeai.cli run "..." --provider albert
```

### Option C : Mistral AI (Souverain européen / SecNumCloud)
```powershell
$env:MISTRAL_API_KEY = "votre_cle_mistral"
.venv\Scripts\python.exe -m officeai.cli run "..." --provider mistral
```

---

## 🔒 5. Principe de Confidentialité des Données (RGPD)

> [!IMPORTANT]
> **Aucune donnée sensible ou nominative n'est transmise aux serveurs d'IA.**  
> - Seul le **schéma technique** (noms des colonnes, types de variables, quelques valeurs d'exemple) est analysé par l'IA pour écrire le script d'automatisation.
> - **L'ensemble des calculs, des regroupements et de la volumétrie** est exécuté **localement sur votre machine** par l'interpréteur Python.
