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
    "effort acronym list": ("effort.EffortList.save -> the workbook's About sheet", "Format", 3),   # 3.76.0: In the list or Not a term; no approval
    "effort marker": ("effortrelink.write_marker -> Open this effort.skeffort in the effort's folder", "format", 1),   # 3.68.0
    "outline layouts": ("outlinelayouts.save -> outline_layouts.json", "format", 1),   # 3.73.0
    "button use": ("skqt.usage.save -> button_use.json", "format", 1),   # 3.74.0: on this PC only
    "training samples": ("efftrain.add -> training_samples.json in the effort's working folder", "format", 1),   # 3.76.0
    "picture readings": ("picreadings.flush -> picture_readings.json in the effort's working folder", "format", 1),   # 3.80.0
    "verify": ("verifystate.Store.save -> verify.json in the effort's working folder", "format", 1),   # 3.84.0
    "verify menu": ("verifyroles.save_team -> verify_menu.json in the config folder", "format", 1),   # 3.84.0
    "scan readings": ("ocrpdf.save_readings -> <page copy>.readings.json beside the copy", "format", 1),   # 3.84.0
    "section designs": ("sectiondesigns -> section_designs/index.json in the config folder", "format", 1),   # 3.87.0
    "piece types": ("shredtypes.save -> piece_types.json in the config folder", "format", 1),   # 4.1.0
    "Company Standards workbook": ("standardsbook.write -> Company Standards.xlsx in the team library, and an effort's "
                                   "Effort Formatting.xlsx; the About sheet", "Format", 2),   # 4.7.0; 2 in 4.10.0: an effort's
    # workbook has a Volume column (a Format 1 workbook has none: every row is every volume) and the team's has the Theme
    # and Suggestion rules sheets (a Format 1 workbook has neither: nothing to read)
    "team library state": ("teamlib -> team_library_state.json in the config folder", "format", 1),   # 4.7.0
    "suggestion scores": ("teamlib.sync_scores -> suggestion_scores.json in the config folder and Lists, Suggestion "
                          "scores, <PC>.json in the team library", "format", 1),   # 4.10.0
    "redline copy": ("redlinecopy.build -> <copy>.skredline.json beside the Word copy in the Redlines folder", "format", 1),   # 4.8.0
    "effort data": ("effortdata.publish -> Stationkeeper Data\\manifest.json in the effort's folder (Stationkeeper Macros reads it)",
                    "schema_version", "1.0"),   # 4.9.0: contract stationkeeper.effort-data
    "global standards": ("globalstd.take -> global_standards.json in the config folder", "format", 1),   # 4.30.0: the version this PC is on
    "global standards version": ("globalfolder.update -> vNNNN\\manifest.json and current.json in the Global Standards folder", "format", 1),   # 4.31.0
    "effort standards": ("effortset.start -> effort_standards\\set.json in the effort's working folder", "format", 1),   # 4.32.0: the effort's own set
    "global standards notice": ("globalfile.take -> global_notice.json in the config folder", "format", 1),   # 4.33.0: what a version changed on this PC
    "re-shred queue": ("reshred.Queue.save -> changes/reshred.json in the effort's working folder", "format", 1),   # 4.1.0
}


def number(kind):
    return FORMATS[kind][2]
