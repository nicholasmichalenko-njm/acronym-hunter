"""Archive and restore an effort (3.70.0; claude/stationkeeper-archive-merge-decisions-2026-11-06.md). Archiving is a
flag in the effort registry, with who and when: the effort leaves All Efforts, the effort picker, My Work and the other
lists (they already leave archived efforts out), and every file stays where it is. Restore clears the flag. There is no
delete: nothing here removes an effort or a file.

archive(registry, name, who=None) -> True       restore(registry, name) -> True
archived(registry) -> [names]                    active(registry) -> [names]"""
import datetime, getpass


def archive(registry, name, who=None):
    if not registry.get(name):
        return False
    registry.put(name, archived=True, archived_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                 archived_by=who or getpass.getuser())
    if registry.current == name:
        try:
            registry.current = ""
        except OSError:
            pass
    return True


def restore(registry, name):
    if not registry.get(name):
        return False
    registry.put(name, archived=False)
    return True


def archived(registry):
    return [n for n in registry.names() if (registry.get(n) or {}).get("archived")]


def active(registry):
    return [n for n in registry.names() if not (registry.get(n) or {}).get("archived")]
