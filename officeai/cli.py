"""
Interface en ligne de commande (CLI) principale pour OfficeAI.
Supporte le Multi-LLM (Google Gemini, Albert Souverain État, Mistral, Mode Démo).
"""

from __future__ import annotations
import sys
import os
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import Completer, Completion

# Configuration de l'encodage pour le terminal Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from officeai import __version__
from officeai.config import Config
from officeai.core.agent import OfficeAIAgent
from officeai.batch.batch_processor import BatchProcessor
from officeai.inspectors.excel_inspector import ExcelInspector
from officeai.inspectors.word_inspector import WordInspector
from officeai.core.providers.factory import ProviderFactory
from officeai.converters.pdf_converter import PdfConverter, PdfConversionError

app = typer.Typer(
    name="officeai",
    help="Assistant CLI Windows pour l'automatisation bureautique propulsee par l'IA (Gemini, Albert Souverain, Mistral).",
    add_completion=False,
)
console = Console(legacy_windows=False)


def confirm_deletion(deletions: list[str]) -> bool:
    """Confirmation explicite des suppressions (jamais automatique, meme avec --yes)."""
    try:
        return typer.confirm("[ATTENTION] Autoriser la SUPPRESSION de fichiers par ce script ?", default=False)
    except typer.Abort:
        return False


def make_confirm_cb(auto: bool = False):
    def confirm_cb(explanation: str, code: str) -> bool:
        console.print(Panel(explanation, title="[bold cyan]Demarche Proposee par l'IA[/bold cyan]"))
        console.print(Panel(Syntax(code, "python", theme="monokai", line_numbers=True), title="[bold green]Script Python a Executer[/bold green]"))
        if auto:
            return True
        return typer.confirm("Souhaitez-vous executer ce script sur vos fichiers ?", default=True)
    return confirm_cb


def version_callback(value: bool):
    if value:
        console.print(f"[bold cyan]OfficeAI[/bold cyan] version [bold green]{__version__}[/bold green]")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True, help="Affiche la version d'OfficeAI."
    )
):
    pass


@app.command()
def run(
    prompt: str = typer.Argument(..., help="Instruction en langage naturel (ex: 'analyse f1.xls et genere rapport.docx')"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Executer automatiquement sans demander de confirmation."),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Fournisseur d'IA : gemini, albert (souverain), mistral, demo."),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Nom du modele specifique."),
):
    """Execute une instruction bureautique en langage naturel."""
    chosen_provider = provider or os.getenv("OFFICEAI_PROVIDER", "gemini")

    if chosen_provider == "gemini" and not Config.is_configured():
        console.print(
            "[yellow]Note : Aucune cle d'API Gemini detectee.[/yellow]\n"
            "Bascule automatique en [bold cyan]mode demo / hors-ligne[/bold cyan] pour ce test.\n"
            "Pour configurer votre cle : [bold green]officeai config --api-key <VOTRE_CLE>[/bold green]\n"
            "Pour utiliser le LLM Souverain de l'Etat : [bold green]officeai run ... --provider albert[/bold green]\n"
        )
        chosen_provider = "demo"

    agent = OfficeAIAgent(provider_name=chosen_provider, model_name=model, console=console)

    result = agent.process_request(
        user_prompt=prompt,
        confirm_callback=make_confirm_cb(auto=yes),
        delete_callback=confirm_deletion,
    )

    if result.success:
        if result.script_path != Path("conversation"):
            console.print("\n[bold green][OK] Traitement termine avec succes ![/bold green]")
            if result.stdout.strip():
                console.print(Panel(result.stdout.strip(), title="Resultat de l'execution"))
            if result.created_files:
                console.print("\n[bold cyan]Nouveau(x) fichier(s) genere(s) :[/bold cyan]")
                for f in result.created_files:
                    console.print(f"  -> [bold green]{f.name}[/bold green] ({f.stat().st_size} octets)")
    else:
        console.print(f"\n[bold red][ERREUR] Echec du traitement.[/bold red] (code retour {result.return_code})")
        raise typer.Exit(code=result.return_code or 1)


@app.command()
def batch(
    pattern: str = typer.Option(..., "--pattern", "-p", help="Motif de fichiers a traiter (ex: '*.xls', 'data/*.xlsx')"),
    prompt: str = typer.Option(..., "--prompt", help="Modele d'instruction (utilise {file}, {name}, {stem})"),
    provider: Optional[str] = typer.Option(None, "--provider", help="Fournisseur d'IA (gemini, albert, mistral, demo)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Executer automatiquement sans confirmation par fichier."),
):
    """Effectue un traitement de masse sur un ensemble de fichiers du repertoire."""
    chosen_provider = provider or os.getenv("OFFICEAI_PROVIDER", "gemini")
    if chosen_provider == "gemini" and not Config.is_configured():
        chosen_provider = "demo"

    agent = OfficeAIAgent(provider_name=chosen_provider, console=console)
    processor = BatchProcessor(agent=agent, console=console)

    results = processor.process_batch(
        pattern=pattern,
        prompt_template=prompt,
        auto_confirm=yes,
        delete_callback=confirm_deletion,
    )

    success_count = sum(1 for _, r in results if r.success)
    console.print(f"\n[bold green][OK] Lot termine : {success_count}/{len(results)} fichier(s) traites avec succes.[/bold green]")


@app.command()
def inspect(
    file_path: Path = typer.Argument(..., help="Chemin du fichier Excel (.xls/.xlsx/.ods) ou Word (.docx) a inspecter")
):
    """Inspecte la structure, colonnes, donnees ou styles d'un document bureautique."""
    if not file_path.exists():
        console.print(f"[bold red]Fichier introuvable : {file_path}[/bold red]")
        raise typer.Exit(code=1)

    ext = file_path.suffix.lower()

    if ExcelInspector.can_inspect(file_path):
        data = ExcelInspector.inspect(file_path)
        console.print(f"\n[bold cyan]Fichier Tableur :[/bold cyan] {data['file_name']} ({data['size_kb']} Ko)")
        for sname, sinfo in data["sheets"].items():
            table = Table(title=f"Feuille : {sname} ({sinfo['total_rows_inspected']} lignes analysees)")
            table.add_column("Colonne", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Valeurs nulles", style="yellow")
            table.add_column("Exemple de valeur", style="green")

            for col in sinfo["columns"]:
                table.add_row(col["name"], col["type"], str(col["nulls"]), str(col["example"] or ""))
            console.print(table)

    elif WordInspector.can_inspect(file_path):
        data = WordInspector.inspect(file_path)
        console.print(f"\n[bold cyan]Document Word :[/bold cyan] {data['file_name']}")
        console.print(f"Modele Jinja2 : [bold]{'OUI' if data['is_jinja_template'] else 'NON'}[/bold]")
        if data["jinja_variables"]:
            console.print(f"Variables Jinja2 : [green]{', '.join(data['jinja_variables'])}[/green]")

        table = Table(title="Styles de paragraphe identifies")
        table.add_column("Style", style="cyan")
        for s in data["paragraph_styles"][:12]:
            table.add_row(s)
        console.print(table)
    else:
        console.print(f"[yellow]Type de fichier non supporte pour l'inspection : {ext}[/yellow]")


def expand_file_args(files: list[str]) -> list[Path]:
    """Developpe les motifs (*.docx) que le shell Windows ne developpe pas."""
    paths: list[Path] = []
    for f in files:
        if any(c in f for c in "*?["):
            paths.extend(sorted(Path.cwd().glob(f)))
        else:
            paths.append(Path(f))
    return paths


@app.command()
def pdf(
    files: list[str] = typer.Argument(..., help="Fichier(s) Word (.docx/.doc) ou OpenDocument (.odt) a convertir (motifs acceptes : *.docx)"),
    force: bool = typer.Option(False, "--force", "-f", help="Ecraser un PDF existant du meme nom."),
):
    """Convertit des documents Word ou ODT en PDF (traitement 100% local via LibreOffice)."""
    targets = expand_file_args(files)
    if not targets:
        console.print("[yellow]Aucun fichier ne correspond.[/yellow]")
        raise typer.Exit(code=1)

    table = Table(title="Conversion PDF")
    table.add_column("Source", style="cyan")
    table.add_column("PDF", style="green")
    table.add_column("Statut")
    failures = 0
    for src in targets:
        existed = src.with_suffix(".pdf").exists()
        try:
            with console.status(f"[bold blue]Conversion de {src.name}...[/bold blue]"):
                out = PdfConverter.convert(src, overwrite=force)
            table.add_row(src.name, f"{out.name} ({out.stat().st_size / 1024:.1f} Ko)",
                          "[bold yellow]ecrase[/bold yellow]" if existed else "[bold green]OK[/bold green]")
        except PdfConversionError as exc:
            failures += 1
            table.add_row(src.name, "-", f"[bold red]{exc}[/bold red]")
    console.print(table)
    if failures:
        raise typer.Exit(code=1)


@app.command()
def config(
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="Cle d'API Google Gemini"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Fournisseur par defaut : gemini, albert, mistral, demo"),
    show: bool = typer.Option(False, "--show", help="Affiche la configuration actuelle"),
):
    """Affiche ou met a jour la configuration d'OfficeAI (.env)."""
    if show or (not api_key and not provider):
        curr_key = Config.get_api_key()
        masked_key = (curr_key[:6] + "..." + curr_key[-4:]) if curr_key and len(curr_key) > 10 else "Non configuree"
        console.print(f"Fournisseur actuel : [bold cyan]{os.getenv('OFFICEAI_PROVIDER', 'gemini')}[/bold cyan]")
        console.print(f"Cle d'API Gemini : [bold green]{masked_key}[/bold green]")
        console.print(f"Modele configure : [bold cyan]{Config.get_model()}[/bold cyan]")
        if not api_key and not provider:
            return

    if api_key:
        env_path = Config.set_api_key(api_key)
        console.print(f"[bold green][OK] Cle d'API enregistree dans {env_path}[/bold green]")

    if provider:
        target_file = Path.cwd() / ".env"
        lines = []
        found = False
        if target_file.exists():
            for line in target_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("OFFICEAI_PROVIDER="):
                    lines.append(f"OFFICEAI_PROVIDER={provider.strip().lower()}")
                    found = True
                else:
                    lines.append(line)
        if not found:
            lines.append(f"OFFICEAI_PROVIDER={provider.strip().lower()}")
        target_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.environ["OFFICEAI_PROVIDER"] = provider.strip().lower()
        console.print(f"[bold green][OK] Fournisseur par defaut configure sur '{provider}'.[/bold green]")


@app.command()
def demo():
    """Lance un scenario guide de prise en main pour decouvrir OfficeAI."""
    console.print(Panel(
        "[bold cyan][*] SCENARIO GUIDE DE PRISE EN MAIN OFFICEAI[/bold cyan]\n\n"
        "Ce scenario va vous guider a travers les 3 etapes fondamentales :\n"
        "1. [bold yellow]Inspection[/bold yellow] d'un fichier tableur (Excel/OpenOffice) et d'un modele Word.\n"
        "2. [bold yellow]Generation automatique[/bold yellow] d'un rapport Word avec calculs et charte graphique.\n"
        "3. [bold yellow]Traitement par lot (Batch)[/bold yellow] sur plusieurs fichiers avec barre de progression.",
        title="Bienvenue dans OfficeAI"
    ))

    # Etape 1 : Inspection
    console.print("\n[bold cyan][>] ETAPE 1 : Inspection de la source de donnees et du modele[/bold cyan]")
    if Path("ventes_nationales.ods").exists():
        inspect(Path("ventes_nationales.ods"))
    elif Path("f1.xls").exists():
        inspect(Path("f1.xls"))

    if Path("modele.docx").exists():
        inspect(Path("modele.docx"))

    # Etape 2 : Execution
    console.print("\n[bold cyan][>] ETAPE 2 : Traitement d'analyse et production du document[/bold cyan]")
    console.print("Instruction : [italic]'utilise le fichier f1.xls et fais une analyse des ventes dans un fichier Word avec la charte de modele.docx'[/italic]")
    run(
        prompt="analyse les ventes dans f1.xls et genere rapport_ventes.docx en respectant la charte de modele.docx",
        yes=True,
        provider="demo",
        model=None,
    )

    # Etape 3 : Traitement par lot
    console.print("\n[bold cyan][>] ETAPE 3 : Traitement par lot (Batch) sur tous les fichiers f*.xls[/bold cyan]")
    batch(
        pattern="f*.xls",
        prompt="analyse les ventes de {file} et genere rapport_{stem}.docx avec la charte de modele.docx",
        provider="demo",
        yes=True,
    )

    console.print(Panel(
        "[bold green][OK] Felicitations ! Votre scenario de prise en main est termine.[/bold green]\n\n"
        "Fichiers generes disponibles dans votre repertoire :\n"
        "- [bold]rapport_ventes.docx[/bold]\n"
        "- [bold]rapport_f1.docx[/bold], [bold]rapport_f2.docx[/bold], [bold]rapport_f3.docx[/bold]\n\n"
        "Pour utiliser vos propres cles d'IA :\n"
        "- Google Gemini : [cyan]officeai config --api-key <VOTRE_CLE>[/cyan]\n"
        "- LLM Souverain Etat (Albert) : [cyan]officeai run ... --provider albert[/cyan]\n"
        "- Mistral AI : [cyan]officeai run ... --provider mistral[/cyan]",
        title="Bilan du Scenario"
    ))


class OfficeFileCompleter(Completer):
    """Compléteur interactif intelligent pour les fichiers bureautiques du répertoire."""

    def get_completions(self, document, complete_event):
        word = document.get_word_before_cursor().lower()
        cwd = Path.cwd()
        for f in sorted(list(cwd.glob("*"))):
            if f.is_file() and not f.name.startswith("."):
                name = f.name
                ext = f.suffix.lower()
                meta = (
                    "Excel" if ext in (".xls", ".xlsx", ".xlsm")
                    else "OpenOffice Calc" if ext == ".ods"
                    else "Word" if ext == ".docx"
                    else "OpenOffice Writer" if ext == ".odt"
                    else "PowerPoint" if ext in (".pptx", ".odp")
                    else "PDF" if ext == ".pdf"
                    else "CSV" if ext == ".csv"
                    else "Fichier"
                )
                if not word or word in name.lower():
                    yield Completion(
                        name,
                        start_position=-len(word),
                        display=name,
                        display_meta=meta,
                    )


def print_detected_files():
    """Affiche la liste des fichiers bureautiques du dossier courant."""
    cwd = Path.cwd()
    files = [f for f in sorted(list(cwd.glob("*"))) if f.is_file() and not f.name.startswith(".")]
    if files:
        table = Table(title="Fichiers disponibles dans le repertoire", show_header=True)
        table.add_column("Nom du fichier", style="cyan")
        table.add_column("Format", style="magenta")
        table.add_column("Taille", style="green")
        for f in files:
            ext = f.suffix.lower()
            ftype = (
                "Excel (.xls/.xlsx)" if ext in (".xls", ".xlsx")
                else "OpenOffice (.ods)" if ext == ".ods"
                else "Word (.docx)" if ext == ".docx"
                else "Texte (.odt)" if ext == ".odt"
                else ext or "Inconnu"
            )
            table.add_row(f.name, ftype, f"{f.stat().st_size / 1024:.1f} Ko")
        console.print(table)


@app.command()
def chat(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Fournisseur d'IA : gemini, albert, mistral, demo"),
):
    """Demarre une session interactive dans le terminal."""
    chosen_provider = provider or os.getenv("OFFICEAI_PROVIDER", "gemini")
    if chosen_provider == "gemini" and not Config.is_configured():
        chosen_provider = "demo"

    console.print(Panel(
        f"[bold cyan]Console interactive OfficeAI (Fournisseur : {chosen_provider.upper()})[/bold cyan]\n\n"
        "💡 [bold yellow]Astuces d'aide à la saisie des fichiers :[/bold yellow]\n"
        "• [bold green]Touche [TAB][/bold green] : Appuyez sur [TAB] pour autocompléter le nom de n'importe quel fichier !\n"
        "• Tapez [bold cyan]/files[/bold cyan] ou [bold cyan]/ls[/bold cyan] pour réafficher la liste des fichiers.\n"
        "• Tapez [bold cyan]/inspect <fichier>[/bold cyan] pour examiner un fichier immédiatement.\n"
        "• Tapez [bold cyan]/pdf <fichier>[/bold cyan] pour convertir un Word/ODT en PDF.\n"
        "• Tapez [bold yellow]exit[/bold yellow] ou [bold yellow]quit[/bold yellow] pour quitter.",
        title="OfficeAI Chat"
    ))

    print_detected_files()

    session = PromptSession(history=InMemoryHistory(), completer=OfficeFileCompleter())
    agent = OfficeAIAgent(provider_name=chosen_provider, console=console)

    while True:
        try:
            user_input = session.prompt("\nOfficeAI > ").strip()
            if not user_input:
                continue

            cmd_lower = user_input.lower()
            if cmd_lower in ("exit", "quit", "q"):
                console.print("[cyan]Au revoir ![/cyan]")
                break
            elif cmd_lower in ("/files", "/ls"):
                print_detected_files()
                continue
            elif cmd_lower.startswith("/pdf"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    try:
                        pdf(files=[parts[1].strip()], force=False)
                    except typer.Exit:
                        pass
                else:
                    console.print("[yellow]Usage : /pdf <fichier.docx|fichier.odt>[/yellow]")
                continue
            elif cmd_lower.startswith("/inspect"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    inspect(Path(parts[1].strip()))
                else:
                    console.print("[yellow]Usage : /inspect <nom_du_fichier>[/yellow]")
                continue

            res = agent.process_request(
                user_input,
                confirm_callback=make_confirm_cb(),
                delete_callback=confirm_deletion,
            )
            if res.success and res.created_files:
                console.print("[bold green]Fichiers generes :[/bold green]")
                for f in res.created_files:
                    console.print(f"  -> {f.name}")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[cyan]Session terminee.[/cyan]")
            break


if __name__ == "__main__":
    app()
