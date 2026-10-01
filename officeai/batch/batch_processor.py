"""
Moteur de traitement par lot (Batch) pour OfficeAI avec suivi de progression Rich.
"""

from __future__ import annotations
from pathlib import Path
from typing import Callable
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

from officeai.core.agent import OfficeAIAgent
from officeai.core.runner import ExecutionResult


class BatchProcessor:
    """Orchestre les traitements de masse sur des collections de fichiers."""

    def __init__(self, agent: OfficeAIAgent, console: Console | None = None):
        self.agent = agent
        self.console = console or Console()

    def process_batch(
        self,
        pattern: str,
        prompt_template: str,
        working_dir: Path | None = None,
        auto_confirm: bool = True,
    ) -> list[tuple[Path, ExecutionResult]]:
        """
        Trouve tous les fichiers correspondant au pattern (ex: '*.xls') et applique
        l'instruction pour chacun d'entre eux.
        Permet l'utilisation des variables : {file}, {name}, {stem} dans le prompt_template.
        """
        cwd = working_dir or Path.cwd()
        matching_files = sorted(list(cwd.glob(pattern)))

        if not matching_files:
            self.console.print(f"[yellow]Aucun fichier ne correspond au motif '{pattern}' dans {cwd}.[/yellow]")
            return []

        self.console.print(
            f"[bold cyan]Démarrage du traitement par lot :[/bold cyan] "
            f"[bold green]{len(matching_files)}[/bold green] fichier(s) trouvé(s)."
        )

        results: list[tuple[Path, ExecutionResult]] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            main_task = progress.add_task("[cyan]Traitement par lot...", total=len(matching_files))

            for current_file in matching_files:
                file_prompt = prompt_template.format(
                    file=str(current_file.relative_to(cwd) if current_file.is_relative_to(cwd) else current_file.name),
                    name=current_file.name,
                    stem=current_file.stem,
                )

                progress.update(main_task, description=f"[cyan]Traitement de {current_file.name}...")

                # Callback de confirmation si non automatique
                confirm_cb = None
                if not auto_confirm:
                    def confirm_cb(exp: str, code: str) -> bool:
                        return True

                res = self.agent.process_request(
                    user_prompt=file_prompt,
                    working_dir=cwd,
                    confirm_callback=confirm_cb,
                )

                results.append((current_file, res))
                progress.advance(main_task)

        return results
