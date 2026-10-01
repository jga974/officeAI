"""
Agent d'orchestration Gemini pour l'automatisation bureautique.
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Any, Callable
from rich.console import Console
from rich.panel import Panel

from officeai.config import Config
from officeai.core.providers.base import LLMProvider
from officeai.core.providers.factory import ProviderFactory
from officeai.core.runner import ScriptRunner, ExecutionResult
from officeai.core.sandbox import analyze_code
from officeai.inspectors.excel_inspector import ExcelInspector
from officeai.inspectors.word_inspector import WordInspector

SYSTEM_INSTRUCTION = """Tu es un expert d'élite en automatisation bureautique Python et ingénierie documentaire Office (Word, Excel, OpenOffice ODS/ODT, PowerPoint) pour Windows.
Ton rôle est de concevoir et générer des scripts Python robustes, autonomes et immédiatement exécutables pour répondre aux demandes de l'utilisateur.

RÈGLES D'OR SUR LES RÉPONSES ET LE CODE :
1. RÉPONSES DIRECTES EN TEXTE (SANS AUCUN CODE PYTHON) :
   - Salutations, culture, météo, cours de change, conversation (ex: "bonjour", "cours du yen", "quelle date ?", "qui es-tu ?").
   - Inventaire des fichiers (ex: "liste de mes fichiers ?", "quels fichiers sont présents ?", "montre les fichiers du dossier").
   - Métadonnées et statistiques élémentaires déjà visibles dans le contexte (ex: "nombre de lignes de f1.xls ?", "quelles sont les colonnes de f1.xls ?", "taille du fichier").
   -> Dans tous ces cas, RÉPONDS DIRECTEMENT ET PRÉCISÉMENT EN TEXTE CLAIR (Markdown). Ne génère AUCUN bloc de code Python (aucun ```python).

2. CODE PYTHON POUR TRAITEMENT DE DONNÉES OU CRÉATION DE DOCUMENTS :
   - Ne génère un bloc de code Python (dans un unique ```python ... ```) QUE si l'utilisateur demande explicitement :
     * Un calcul, filtre, regroupement ou croisement sur des données locales (ex: "calcule le meilleur vendeur", "trouve les doublons", "combien de ventes dans la région Nord").
     * La génération, modification ou sauvegarde d'un document sur disque (ex: "génère un rapport Word", "mets le résultat dans rapport.docx selon modele.docx", "crée un fichier Excel").
   - Bibliothèques autorisées : pandas, openpyxl, xlrd, odf (engine='odf'), python-docx, docxtpl, matplotlib.pyplot, pathlib, os, sys.
   - Si création de rapport Word avec modèle : utilise `DocxStyler.clone_template_blank(template_path, output_path)` et applique les styles existants.
   - Pense toujours à afficher les résultats dans stdout avec `print()`.

3. SÉCURITÉ (NON NÉGOCIABLE) :
   - Tu travailles UNIQUEMENT dans le répertoire courant (et ses sous-dossiers). Utilise exclusivement des chemins relatifs.
     Jamais de chemin absolu, de `..`, de `~`, de lecteur Windows (C:\\) ni de dossier utilisateur.
   - Interdits : subprocess, os.system, socket/réseau, ctypes, eval/exec, importlib. Ce code sera refusé.
   - Ne supprime, n'écrase et ne déplace JAMAIS un fichier existant sauf demande explicite de l'utilisateur.
     Pour produire un résultat, crée un NOUVEAU fichier. Si l'utilisateur demande une suppression, fais-la
     uniquement pour les fichiers nommés, et affiche chaque fichier supprimé avec `print()`.
   - Pour les questions sur les fichiers du dossier, base-toi uniquement sur la section « INVENTAIRE DU RÉPERTOIRE »
     et sur les inspections fournies dans le contexte ; n'invente jamais de fichier.
"""


class OfficeAIAgent:
    """Agent qui coordonne l'analyse des fichiers, la génération de code par le LLM et son exécution."""

    def __init__(
        self,
        provider_name: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        console: Console | None = None,
    ):
        self.console = console or Console()
        self.provider = ProviderFactory.create(
            provider_name=provider_name,
            api_key=api_key,
            model_name=model_name,
        )

    @staticmethod
    def list_directory(cwd: Path) -> str:
        """Inventaire textuel (fichiers et sous-dossiers de premier niveau) du répertoire de travail."""
        lines = [
            "=== INVENTAIRE DU RÉPERTOIRE ===",
            f"Répertoire de travail : {cwd.name} ({cwd})",
            f"Date du jour : {datetime.now():%d/%m/%Y %H:%M}",
        ]
        entries = [p for p in sorted(cwd.iterdir(), key=lambda p: p.name.lower()) if not p.name.startswith(".")]
        if not entries:
            lines.append("(répertoire vide)")
        for p in entries:
            if p.is_dir():
                lines.append(f"- [dossier] {p.name}/")
            else:
                st = p.stat()
                lines.append(f"- {p.name} ({st.st_size / 1024:.1f} Ko, modifié le {datetime.fromtimestamp(st.st_mtime):%d/%m/%Y %H:%M})")
        return "\n".join(lines)

    def scan_and_inspect_directory(self, working_dir: Path | None = None) -> str:
        """Inventaire du dossier courant + inspection des fichiers bureautiques."""
        cwd = working_dir or Path.cwd()
        reports = [self.list_directory(cwd)]

        # Lister les fichiers Excel / CSV
        for p in sorted(cwd.glob("*")):
            if p.is_file() and ExcelInspector.can_inspect(p):
                try:
                    reports.append(ExcelInspector.format_for_prompt(p))
                except Exception as e:
                    reports.append(f"Fichier tableur détecté {p.name} (erreur inspection: {e})")

        # Lister les fichiers Word
        for p in cwd.glob("*"):
            if p.is_file() and WordInspector.can_inspect(p):
                try:
                    reports.append(WordInspector.format_for_prompt(p))
                except Exception as e:
                    reports.append(f"Fichier Word détecté {p.name} (erreur inspection: {e})")

        return "\n\n".join(reports)

    def _report_changes(self, result: ExecutionResult, cwd: Path) -> None:
        """Informe toujours l'utilisateur des fichiers supprimés ou modifiés par le script."""
        def rel(p: Path) -> str:
            try:
                return str(p.relative_to(cwd.resolve()))
            except ValueError:
                return str(p)

        if result.deleted_files:
            self.console.print(Panel(
                "\n".join(f"- {rel(p)}" for p in result.deleted_files),
                title=f"[bold red]{len(result.deleted_files)} fichier(s)/dossier(s) SUPPRIME(S)[/bold red]",
                border_style="red",
            ))
        if result.modified_files:
            self.console.print(Panel(
                "\n".join(f"- {rel(p)}" for p in result.modified_files),
                title=f"[bold yellow]{len(result.modified_files)} fichier(s) MODIFIE(S)/ecrase(s)[/bold yellow]",
                border_style="yellow",
            ))

    def process_request(
        self,
        user_prompt: str,
        working_dir: Path | None = None,
        max_retries: int = 3,
        confirm_callback: Callable[[str, str], bool] | None = None,
        delete_callback: Callable[[list[str]], bool] | None = None,
    ) -> ExecutionResult:
        """
        Traite une requête utilisateur de bout en bout :
        1. Inspection du contexte
        2. Appel Gemini pour planifier et générer le script
        3. Confirmation utilisateur optionnelle
        4. Exécution et boucle d'auto-réparation si nécessaire
        """
        cwd = working_dir or Path.cwd()

        # 1. Inspection des fichiers locaux
        with self.console.status("[bold blue]Inspection des fichiers bureautiques du dossier...[/bold blue]"):
            context = self.scan_and_inspect_directory(cwd)

        # 2. Appel au modèle de langage
        provider_title = self.provider.__class__.__name__.replace("Provider", "")
        with self.console.status(f"[bold magenta]Conception de la solution avec l'IA ({provider_title})...[/bold magenta]"):
            explanation, python_code = self.provider.generate_plan_and_code(
                system_instruction=SYSTEM_INSTRUCTION,
                user_prompt=user_prompt,
                context=context,
            )

        # Si aucun script n'est nécessaire (question générale / salutation / réponse textuelle)
        if not python_code or not python_code.strip():
            self.console.print(Panel(explanation, title=f"[bold cyan]OfficeAI ({provider_title})[/bold cyan]"))
            return ExecutionResult(
                success=True,
                stdout=explanation,
                stderr="",
                return_code=0,
                script_path=Path("conversation"),
                created_files=[],
            )

        # 3. Confirmation utilisateur si fournie
        if confirm_callback:
            approved = confirm_callback(explanation, python_code)
            if not approved:
                self.console.print("[yellow]Exécution annulée par l'utilisateur.[/yellow]")
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr="Annulé par l'utilisateur",
                    return_code=-1,
                    script_path=Path("cancelled"),
                    created_files=[],
                )

        # 3 bis. Suppression de fichiers : confirmation explicite et séparée, refusée par défaut
        allow_delete = False
        analysis = analyze_code(python_code)
        if analysis.deletes_files:
            self.console.print(Panel(
                "Ce script contient des opérations de SUPPRESSION :\n- " + "\n- ".join(analysis.deletions),
                title="[bold red]ATTENTION : suppression de fichiers[/bold red]",
                border_style="red",
            ))
            allow_delete = bool(delete_callback and delete_callback(analysis.deletions))
            if not allow_delete:
                self.console.print("[yellow]Suppression non approuvée : exécution annulée. Aucun fichier n'a été touché.[/yellow]")
                return ExecutionResult(
                    success=False, stdout="", stderr="Suppression refusée par l'utilisateur",
                    return_code=-1, script_path=Path("cancelled"), created_files=[],
                )

        # 4. Exécution du script
        current_code = python_code
        for attempt in range(1, max_retries + 1):
            with self.console.status(f"[bold green]Exécution du traitement (tentative {attempt}/{max_retries})...[/bold green]"):
                result = ScriptRunner.run_code(current_code, working_dir=cwd, allow_delete=allow_delete)
            self._report_changes(result, cwd)

            if result.success:
                return result

            # En cas d'échec, tentative de correction automatique par le provider
            self.console.print(f"[bold red]Erreur rencontrée :[/bold red]\n{result.stderr.strip()}")
            if attempt < max_retries:
                with self.console.status(f"[bold yellow]Auto-correction du script par l'IA ({provider_title})...[/bold yellow]"):
                    current_code = self.provider.auto_repair_code(
                        failed_code=current_code,
                        error_message=result.stderr,
                        context=context,
                    )
            else:
                self.console.print("[bold red]Nombre maximal de tentatives atteint.[/bold red]")

        return result
