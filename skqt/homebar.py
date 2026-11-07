"""The Effort Dashboard's one bar (3.75.0, house rule 8): + Add (every new thing the dashboard's cards hold, in one
menu), Edit details...; More (People, Open effort folder, All overviews, Customize, Add to this effort, Steps, Gate goal
defaults); Export (the overview, the tasks and questions, the graphic needs, Export all). The cards keep their content
and their row actions; the buttons that opened another page are gone (the menu opens it)."""
from .commandbar import CommandBar


def build(hp):
    host = hp.host
    bar = CommandBar()
    m = bar.add_menu("+ Add", "Something new on the dashboard: a note, a question, a task, a date, a need")
    for text, fn in (("Note...", lambda: hp.note_dialog()), ("Question...", lambda: hp.note_dialog(question=True)),
                     ("Task...", lambda: hp.task_dialog()), ("Due date...", lambda: _entry(hp, "Due")),
                     ("Event...", lambda: _entry(hp, "Meeting")), ("Meeting notes", lambda: host.go("meetings")),
                     ("Graphic need...", lambda: hp.graphic_dialog()), ("Win theme...", lambda: hp.theme_dialog()),
                     ("Gate goal...", lambda: hp.goal_dialog()), ("Customer information...", lambda: hp.info_dialog()),
                     ("Submission requirement...", lambda: hp.format_dialog())):
        m.addAction(text, fn)
    bar.add("Edit details...", lambda: hp.banner.edit_dialog(),
            "Proposal manager, client, sensitivity, the customer's due date and the effort's own spots")
    bar.more("People...", lambda: hp.banner.people_roles(), "Who works on this effort and in what role")
    bar.more("Open effort folder", lambda: host.open_effort_folder())
    bar.more("All overviews...", lambda: host.record_page.overviews_dialog(), "Every overview exported for this effort")
    bar.more_sep()
    bar.more("Customize...", lambda: hp.customize(), "Your role's layout; show, hide, order and size the cards")
    bar.more("Add to this effort...", lambda: __import__("skqt.mergedialog", fromlist=["x"]).add_to_effort(host, host.effort_name),
             "Merge another copy of this effort (someone else's, an earlier one, or its package) or add files")
    bar.more("Quick note", lambda: __import__("skqt.homecards", fromlist=["x"])._note(hp), "A line caught now, sorted later")
    bar.more("Steps...", lambda: hp.path.steps_dialog() if getattr(hp, "path", None) else None, "Switch a step on or off for this effort")
    bar.more("Check the drafts for the win themes", lambda: hp.check_themes())
    bar.more("Save this stage's gate goals as the default", lambda: hp.save_defaults())
    bar.export("Overview (Word)...", lambda: host.record_page.status_export(), "Where the effort stands, in one Word file")
    bar.export("Tasks and questions (Excel)...", lambda: hp.export_tq(), "For the person shown, or the full team")
    bar.export("Graphic needs (Excel)...", lambda: hp.export_graphics(), "For the graphics team")
    bar.export("Export all...", lambda: host.go("exportall"), "Every output of the effort in one dated folder")
    return bar


def _entry(hp, kind):
    from .calview import entry_dialog
    return entry_dialog(hp, kind)
