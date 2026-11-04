"""Every file Stationkeeper saves, and the format number it writes (3.38.1). One place to look before changing a saved
file: a change that is not purely additive (a key renamed, removed, or its meaning changed) raises the format number
here and in the writer, adds the step that reads the old format, and adds a golden set (tools/make_golden.py) so every
later version is tested to open it. tests/test_formats.py checks each writer still writes the number listed.

Readers take missing keys from defaults, so adding a key needs no new number. A reader that meets a newer number than
it knows keeps what it can and says so; it never drops data."""

# file kind: (where it is written, the key holding the number, the number)
FORMATS = {
    "production standards": ("prodrules.save -> production_standards.json", "version", 3),
    "rules": ("rulebook.save -> rules.json", "format", 1),
    "template library": ("templatelib.Library.save -> template_library/index.json", "format", 1),
    "author list": ("authorlist -> author_list.json", "format", 1),
    "effort package": ("effortpkg.save -> manifest.json in the .skpkg", "format", 1),
    "team pack": ("teampack.make -> pack.json in the .skteam", "format", "sk-team-1"),
    "Stationkeeper Data file": ("teamdata.export -> manifest.json in the .skdata", "format", "sk-data-1"),
    "update pack": ("updatepack -> update.json in the .skupdate", "format", 1),
    "effort record": ("effortrec.Record.save -> record.json", "v", 1),
}


def number(kind):
    return FORMATS[kind][2]
