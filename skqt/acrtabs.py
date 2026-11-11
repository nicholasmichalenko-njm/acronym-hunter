"""Acronyms in two tabs (3.93.0; claude/stationkeeper-acronyms-two-tabs-3.93.md): On the page (the customer's pages, one
at a time, every find boxed; acrpageview) and The list (the effort's terms, definitions, sources and where each goes;
acrlayout). One set of decisions underneath: a term decided in either tab is decided in both. Each tab has its own
bar with one main button (Page done; In our drafts). A page opens on On the page while finds are left to decide, else
on The list. Acronym Finder (the tool window) keeps the list with the page beside it. Rules only (No AI)."""
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QTabBar, QWidget

import acrpages as AG
import diag
from . import design as D
from .commandbar import CommandBar

TABS = ("On the page", "The list")


def install(page, v):
    from .acrpageview import OnPage
    page.list_only = True                                  # the list without the page beside it (the tool: False)
    page.onpage = OnPage(page)
    page.tabs = QTabBar(); page.tabs.setDrawBase(False); page.tabs.setExpanding(False)
    for name in TABS:
        page.tabs.addTab(name)
    ob = CommandBar(page)
    page.on_bar = ob
    page.b_nextpage = ob.add("Next page with finds", lambda: page.onpage.next_page(),
                             "The next page with finds to decide (pages marked done are skipped)")
    page.b_pagedone = ob.primary("Page done", lambda: page.onpage.page_done(),
                                 "This page is done: marked with the effort, and the next page with finds shows")
    page.show_not_act = ob.more("Show Not a term", lambda: _show_not(page), checkable=True)
    ob.more("Every page to do again", lambda: again(page), "Clears the Page done marks")
    page.bars = QStackedWidget()
    page.bars.addWidget(ob); page.bars.addWidget(page.bar)
    page.head_w = QWidget()
    head = QHBoxLayout(page.head_w); head.setContentsMargins(0, 0, 0, 0); head.setSpacing(D.SPACE["m"])
    head.addWidget(page.tabs); head.addWidget(page.progress, 1); head.addWidget(page.b_cancel); head.addWidget(page.bars)
    page.tab_stack = QStackedWidget()
    page.tab_stack.addWidget(page.onpage); page.tab_stack.addWidget(page.list_w)
    v.insertWidget(0, page.head_w)
    v.insertWidget(1, page.tab_stack, 1)
    page.tabs.currentChanged.connect(lambda i: switch(page, i))
    page.tab_set = False
    page.show_in_list = lambda t: show_in_list(page, t)
    page.show_on_page = lambda t: show_on_page(page, t)


def switch(page, i):
    page.tab_stack.setCurrentIndex(i)
    page.bars.setCurrentIndex(i)
    if i == 0:
        page.onpage.fill()
    diag.activity("acronym_tab", n=i)
    return i


def after_fill(page):
    """After the list is filled: the tabs show once there is anything; the first time, the tab to start on."""
    s = page.session
    has = bool(s and s.results) or page.worker is not None
    page.head_w.setVisible(has)
    page.tab_stack.setVisible(has)
    if getattr(page, "tool", False):
        return None
    if s is not None and s.results and not page.tab_set:
        page.tab_set = True
        left = AG.totals(AG.pages(s.results, AG.done_set(s.ws)))["to_decide"]
        if page.tabs.currentIndex() != (0 if left else 1):
            page.tabs.setCurrentIndex(0 if left else 1)      # switch() fills the page
            return page.tabs.currentIndex()
    if page.tabs.currentIndex() == 0 and has:
        page.onpage.fill()
    return page.tabs.currentIndex()


def tool(page):
    """Acronym Finder: no tabs; the list with the page beside it, as before."""
    page.list_only = False
    page.tabs.setVisible(False)
    page.tabs.setCurrentIndex(1)
    page.tab_stack.setCurrentIndex(1); page.bars.setCurrentIndex(1)
    page.mid.setVisible(True)
    from .acrlayout import KEEP_COLS
    for c in range(page.table.columnCount()):
        page.table.setColumnHidden(c, c not in KEEP_COLS)
    if getattr(page, "split", None) is not None:
        page.split.setSizes([300, 1200])


def show_in_list(page, t):
    page.tabs.setCurrentIndex(1)
    page.f_search.clear()
    page.f_status.setCurrentIndex(0)
    page.f_pics.setChecked(False)
    page.fill()
    return page.select(t)


def show_on_page(page, t):
    page.tabs.setCurrentIndex(0)
    return page.onpage.show_term(t)


def show_place(page, loc):
    page.tabs.setCurrentIndex(0)
    return page.onpage.go(AG.place_of(loc))


def _show_not(page):
    return page.onpage.set_show_not(page.show_not_act.isChecked())


def again(page):
    s = page.session
    if s is None or s.ws is None:
        return 0
    n = len(AG.done_set(s.ws))
    s.ws.set(AG.DONE_KEY, [])
    page.onpage.fill()
    page.host.toast(f"{n} page(s) to do again")
    return n
