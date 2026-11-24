"""The effort's own pages beside the Overview (4.27.1): Tasks and Calendar, menu entries under the Dashboard, and
Activity, a tab of it. 4.28.2: the templates you name, and Team defaults on the Team page. Made here so the window's
module stays inside its size limit."""


def install(w):
    """Called once while the window is built, before its pages go on the stack."""
    from .activitypage import ActivityPage
    from .calendarpage import CalendarPage
    from .taskspage import TasksPage
    w.tasks_page, w.calendar_page, w.activity_page = TasksPage(w), CalendarPage(w), ActivityPage(w)
    w.pages.update({"tasks": w.tasks_page, "calendar": w.calendar_page, "activity": w.activity_page})
    from .backuppage import BackupPage                     # 4.61.0: Effort Backup, at the foot of the menu
    w.backup_page = BackupPage(w); w.pages["backup"] = w.backup_page
    from .assignview import AssignView                     # 4.66.0: Matrix > Assign
    w.assignto_page = AssignView(w); w.pages["assignto"] = w.assignto_page
    from .namedtplpage import NamedTemplatesPage           # 4.28.2: the templates you name are the Template entry's first tab;
    w.named_page = NamedTemplatesPage(w)                   # the ones the Effort Profiles make are the next ("From profiles")
    w.pages.update({"tplprofiles": w.templates_page, "templates": w.named_page})
    from .teamview import TeamCard                         # 4.28.2 (answer 12): Team defaults is on the Team page, not in Settings
    w.team_page.team_card = TeamCard(w); w.team_page.layout().insertWidget(w.team_page.layout().count() - 1, w.team_page.team_card)
    return w.pages
