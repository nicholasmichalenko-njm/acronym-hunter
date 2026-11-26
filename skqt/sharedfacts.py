"""4.78.0: Customer, Solicitation number and Proposal due are one value each (E1 of
claude/stationkeeper-effort-settings-direction-2026-11-25.md). Customer information, Effort Settings and Shred's
More > Customer info all go through here, so a change in one place is the value everywhere. custinfo holds the rules;
this finds the open effort's list and tells the effort registry. Nothing leaves the PC."""
import custinfo as CI
import diag
import effortrec as R


def effort_list(host):
    """The open effort's list (where Customer and Solicitation number live), or None."""
    if getattr(host, "ws", None) is None or not getattr(host, "effort_path", ""):
        return None
    try:
        import effort as E
        return E.EffortList(host.effort_path, host.effort_name).load()
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None


def _put(host):
    def put(L):
        host.efforts.put(host.effort_name, client=L.client, solicitation=L.solicitation, internal_no=L.internal_no)
    return put


def who():
    try:
        import effort as E
        return E.user_name()
    except Exception:  # noqa: BLE001
        return ""


def fact(host, label, L=None):
    rec = R.Record(host.ws.root)
    return CI.fact(rec, label, L if L is not None else effort_list(host))


def set_fact(host, label, value, how="typed", source=None, replace=None, L=None):
    """CI.set_fact for the open effort, with its list and the registry. Says what went wrong on the status line."""
    rec = R.Record(host.ws.root)
    L = L if L is not None else effort_list(host)
    out = CI.set_fact(rec, label, value, how, who(), source, replace, effort=L, put=_put(host))
    if out == "not understood":
        host.status(f"{label}: no date was found in that. Write it like Dec 15, 2026 2:00 PM ET.")
    elif out == "locked":
        host.status("The effort list is open in Excel: close it, then change it again.")
    return out


MESSAGES = {"not understood", "locked"}
