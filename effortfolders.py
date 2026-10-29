"""An effort's own folders (2.90.0): one folder per effort, laid out so a person can find everything without the app.

    <effort>\\
      Customer Documents\\     the RFP and its attachments, as the customer sent them
      Volumes\\                the Word volumes the team writes
      Response Setup\\         the documents writers start from
      Exports\\                acronym lists, status reports, the calendar, reviews, Export all
      <name>_Compliance_Matrix.xlsx
      <name>_Effort_List.xlsx
      <name>_Effort_List - app data\\   the app's working files for the effort (a note inside says not to edit them)

A new effort gets the four folders. An older effort keeps its files where they are; a folder appears the first time
something is saved into it. Every save still asks where to put the file: these are only where the dialog starts.
Standard library only.
"""
import os

SUBS = {"customer": "Customer Documents", "volumes": "Volumes", "setup": "Response Setup", "exports": "Exports"}
NOTE = "About this folder.txt"
NOTE_TEXT = ("Stationkeeper keeps this effort's working files here: the record, the document library and its versions,\r\n"
             "what was taken from documents, change decisions, backups of the matrix and the calendar.\r\n\r\n"
             "Do not edit, move or rename anything in this folder. Keep it beside the effort list: effort packages and\r\n"
             "backups carry it, and the effort opens from it. Your own files go in the folders beside it.\r\n")


def root(effort_path):
    return os.path.dirname(os.path.abspath(effort_path)) if effort_path else ""


def folder(effort_path, kind, make=True):
    """The effort's folder of that kind (created unless make is False); '' with no effort."""
    r = root(effort_path)
    if not r:
        return ""
    p = os.path.join(r, SUBS[kind])
    if make:
        try:
            os.makedirs(p, exist_ok=True)
        except OSError:
            return r
    return p


def out(effort_path, name="", kind="exports"):
    """Where a save dialog starts: the effort's Exports (or other) folder, with the suggested file name."""
    f = folder(effort_path, kind)
    return os.path.join(f, name) if f and name else (f or name)


def create_all(effort_path):
    return [folder(effort_path, k) for k in SUBS]


def note_app_data(data_dir):
    """The note inside the effort's app data folder (written once)."""
    p = os.path.join(data_dir, NOTE)
    if data_dir and os.path.isdir(data_dir) and not os.path.exists(p):
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(NOTE_TEXT)
        except OSError:
            pass
    return p
