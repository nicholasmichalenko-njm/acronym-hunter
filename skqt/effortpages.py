"""The effort's own pages beside the Overview (4.27.1): Tasks and Calendar, menu entries under the Dashboard, and
Activity, a tab of it. Made here so the window's module stays inside its size limit."""


def install(w):
    """Called once while the window is built, before its pages go on the stack."""
    from .activitypage import ActivityPage
    from .calendarpage import CalendarPage
    from .taskspage import TasksPage
    w.tasks_page, w.calendar_page, w.activity_page = TasksPage(w), CalendarPage(w), ActivityPage(w)
    w.pages.update({"tasks": w.tasks_page, "calendar": w.calendar_page, "activity": w.activity_page})
    return w.pages
