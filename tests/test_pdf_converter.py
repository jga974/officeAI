"""Tests de la conversion Word/ODT -> PDF (LibreOffice requis pour les tests d'integration)."""

from pathlib import Path
import shutil
import subprocess
import pytest
import docx
from typer.testing import CliRunner

from officeai.cli import app
from officeai.converters.pdf_converter import PdfConverter, PdfConversionError

needs_soffice = pytest.mark.skipif(PdfConverter.find_soffice() is None, reason="LibreOffice absent")
runner = CliRunner()


def _make_docx(path: Path, text: str = "Rapport d'activité — éàç €"):
    d = docx.Document()
    d.add_paragraph(text)
    d.save(str(path))


def test_rejects_unsupported_extension(tmp_path: Path):
    (tmp_path / "a.xlsx").write_bytes(b"x")
    with pytest.raises(PdfConversionError, match="non supporte"):
        PdfConverter.convert(tmp_path / "a.xlsx", working_dir=tmp_path)


def test_rejects_missing_file(tmp_path: Path):
    with pytest.raises(PdfConversionError, match="introuvable"):
        PdfConverter.convert(Path("nope.docx"), working_dir=tmp_path)


def test_rejects_file_outside_working_dir(tmp_path: Path):
    work = tmp_path / "work"
    work.mkdir()
    _make_docx(tmp_path / "out.docx")
    with pytest.raises(PdfConversionError, match="hors du repertoire"):
        PdfConverter.convert(tmp_path / "out.docx", working_dir=work)
    with pytest.raises(PdfConversionError, match="hors du repertoire"):
        PdfConverter.convert(Path("../out.docx"), working_dir=work)


def test_refuses_to_overwrite_without_force(tmp_path: Path):
    _make_docx(tmp_path / "a.docx")
    (tmp_path / "a.pdf").write_bytes(b"ancien")
    with pytest.raises(PdfConversionError, match="existe deja"):
        PdfConverter.convert(tmp_path / "a.docx", working_dir=tmp_path)
    assert (tmp_path / "a.pdf").read_bytes() == b"ancien"


def test_reports_missing_libreoffice(tmp_path: Path, monkeypatch):
    _make_docx(tmp_path / "a.docx")
    monkeypatch.setattr(PdfConverter, "find_soffice", staticmethod(lambda: None))
    with pytest.raises(PdfConversionError, match="LibreOffice est introuvable"):
        PdfConverter.convert(tmp_path / "a.docx", working_dir=tmp_path)


def test_failed_conversion_leaves_no_pdf(tmp_path: Path, monkeypatch):
    _make_docx(tmp_path / "a.docx")
    monkeypatch.setattr(PdfConverter, "find_soffice", staticmethod(lambda: "soffice"))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "boom"))
    with pytest.raises(PdfConversionError, match="boom"):
        PdfConverter.convert(tmp_path / "a.docx", working_dir=tmp_path)
    assert not (tmp_path / "a.pdf").exists()


@needs_soffice
def test_converts_docx_to_pdf(tmp_path: Path):
    _make_docx(tmp_path / "rapport.docx")
    out = PdfConverter.convert(tmp_path / "rapport.docx", working_dir=tmp_path)
    assert out == (tmp_path / "rapport.pdf").resolve()
    assert out.read_bytes().startswith(b"%PDF")


@needs_soffice
def test_converts_odt_to_pdf(tmp_path: Path):
    _make_docx(tmp_path / "base.docx")
    PdfConverter.TIMEOUT_SECONDS = 180
    subprocess.run([PdfConverter.find_soffice(), "--headless", "--convert-to", "odt", "--outdir", str(tmp_path),
                    str(tmp_path / "base.docx")], check=True, capture_output=True)
    out = PdfConverter.convert(tmp_path / "base.odt", working_dir=tmp_path)
    assert out.read_bytes().startswith(b"%PDF")


@needs_soffice
def test_cli_pdf_with_glob_and_force(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_docx(tmp_path / "a.docx")
    _make_docx(tmp_path / "b.docx")
    r = runner.invoke(app, ["pdf", "*.docx"])
    assert r.exit_code == 0 and (tmp_path / "a.pdf").exists() and (tmp_path / "b.pdf").exists()
    r = runner.invoke(app, ["pdf", "a.docx"])
    assert r.exit_code == 1 and "existe deja" in r.output
    r = runner.invoke(app, ["pdf", "a.docx", "--force"])
    assert r.exit_code == 0 and "ecrase" in r.output
