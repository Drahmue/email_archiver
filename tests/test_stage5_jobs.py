"""
test_stage5_jobs.py — Aufträge aus der INI, atomisches PDF-Schreiben, DryRun (2026-10-27)

Prüft:
  - read_jobs(): nur 'ablage' ohne [belege], 'ablage' + 'belege' mit [belege]
  - save_pdf_atomic(): fertiges PDF unter endgültigem Namen, keine .tmp-Reste,
    bei Fehler weder PDF noch .tmp
  - process_emails(dry_run=True): kein PDF, kein Verschieben
"""

import configparser
import sys
from email.message import EmailMessage
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import main  # noqa: E402


def _config(with_belege: bool) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read_dict({
        "imap": {"source_folder": "01 für Ablage", "processed_folder": "01 für Ablage erledigt"},
        "output": {"folder": r"D:\out\korrespondenz"},
    })
    if with_belege:
        cfg.read_dict({"belege": {"source_folder": "01 für Belege",
                                  "processed_folder": "01 für Ablage erledigt",
                                  "output_folder": r"D:\out\belege"}})
    return cfg


def _mail() -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = "Test Absender <test@example.com>"
    msg["To"] = "ah@example.com"
    msg["Subject"] = "Testbeleg"
    msg["Date"] = "Mon, 27 Oct 2026 10:15:00 +0100"
    msg.set_content("Betrag 4,50 EUR")
    return msg


class _Logger:
    def info(self, *_):
        pass

    def warning(self, *_):
        pass

    def error(self, *_):
        pass


def test_read_jobs_ohne_belege():
    jobs = main.read_jobs(_config(False))
    assert [j.name for j in jobs] == ["ablage"]
    assert jobs[0].source_folder == "01 für Ablage"


def test_read_jobs_mit_belege():
    jobs = main.read_jobs(_config(True))
    assert [j.name for j in jobs] == ["ablage", "belege"]
    assert jobs[1].source_folder == "01 für Belege"
    assert jobs[1].processed_folder == "01 für Ablage erledigt"
    assert jobs[1].output_folder == Path(r"D:\out\belege")


def test_save_pdf_atomic_erfolg(tmp_path):
    ziel = tmp_path / "beleg.pdf"

    def fake_convert(_msg, pfad):
        assert pfad.name == "beleg.pdf.tmp"   # wird unter .tmp geschrieben
        pfad.write_bytes(b"%PDF-1.4 test")

    with mock.patch.object(main.converter, "convert_and_save", fake_convert):
        main.save_pdf_atomic(_mail(), ziel)
    assert ziel.read_bytes() == b"%PDF-1.4 test"
    assert list(tmp_path.iterdir()) == [ziel]


def test_save_pdf_atomic_fehler(tmp_path):
    ziel = tmp_path / "beleg.pdf"

    def fake_convert(_msg, pfad):
        pfad.write_bytes(b"halb")
        raise RuntimeError("Chromium abgestürzt")

    with mock.patch.object(main.converter, "convert_and_save", fake_convert):
        with pytest.raises(RuntimeError):
            main.save_pdf_atomic(_mail(), ziel)
    assert list(tmp_path.iterdir()) == []


def test_sperre_belegen_und_freigeben(tmp_path):
    lock = tmp_path / "email_archiver.lock"
    assert main.acquire_lock(lock, 0, 10, _Logger()) is True
    assert lock.exists()
    main.release_lock(lock)
    assert not lock.exists()


def test_sperre_belegt_wird_uebersprungen(tmp_path):
    lock = tmp_path / "email_archiver.lock"
    lock.write_text("AHMAIN 1234 2026-10-27 12:00:00", encoding="utf-8")
    assert main.acquire_lock(lock, 0, 10, _Logger()) is False
    assert lock.read_text(encoding="utf-8").startswith("AHMAIN")   # fremde Sperre bleibt


def test_verwaiste_sperre_wird_entfernt(tmp_path):
    import os
    import time
    lock = tmp_path / "email_archiver.lock"
    lock.write_text("HAUSERVER 99 alt", encoding="utf-8")
    alt = time.time() - 11 * 60
    os.utime(lock, (alt, alt))
    assert main.acquire_lock(lock, 0, 10, _Logger()) is True
    assert not lock.read_text(encoding="utf-8").startswith("HAUSERVER 99")


def test_dry_run_schreibt_und_verschiebt_nichts(tmp_path):
    job = main.Job("belege", "01 für Belege", "01 für Ablage erledigt", tmp_path)
    with mock.patch.object(main.imap, "fetch_emails", return_value=[(1, _mail())]), \
         mock.patch.object(main.imap, "move_email") as move, \
         mock.patch.object(main.converter, "convert_and_save") as convert:
        ok, err = main.process_emails(object(), job, _Logger(), dry_run=True)
    assert (ok, err) == (1, 0)
    move.assert_not_called()
    convert.assert_not_called()
    assert list(tmp_path.iterdir()) == []
