"""Where a document library's files are (3.78.0, split from docversions): the effort's folder and its Library folder,
and a version's original file, kept relative to the app's working folder (rel) or to the effort's folder (erel), so the
effort opens the same wherever it is moved. Standard library only."""
import os


def effort_root_of(data_dir):
    """3.81.0: the effort's top folder for its app data folder: the folder plan's root (so Library sits beside Customer
    Documents even when the list is deeper in the tree), else the folder beside the app data."""
    import workspace as W
    dd = os.path.abspath(data_dir or "")
    if not dd.endswith(W.DATA_SUFFIX):
        return ""
    beside = os.path.dirname(dd)
    try:
        import effortfolders as EF
        lst = os.path.join(beside, os.path.basename(dd)[:-len(W.DATA_SUFFIX)] + ".xlsx")
        return EF.root(lst) or beside
    except Exception:  # noqa: BLE001
        return beside


class PathsMixin:
    @property
    def effort_root(self):
        """3.78.0: the effort's folder (where its Library folder sits): set by effortlib.attach, else the effort's top
        folder (3.81.0: the folder plan's root; beside the app data when the list sits at the top)."""
        er = self.__dict__.get("_effort_root")
        if er is not None:
            return er
        return effort_root_of(self.data_dir)

    @effort_root.setter
    def effort_root(self, value):
        self.__dict__["_effort_root"] = value or ""

    @property
    def library_root(self):
        """3.78.0: <effort>\\Library, where the library's own files are kept in real folders ('' when unknown)."""
        lr = self.__dict__.get("_library_root")
        if lr is not None:
            return lr
        er = self.effort_root
        return os.path.join(er, "Library") if er else ""

    @library_root.setter
    def library_root(self, value):
        self.__dict__["_library_root"] = value or ""

    def _rel(self, path):
        """path relative to the effort's data folder, when the file is inside it (a copy kept with the effort)."""
        try:
            base = os.path.normcase(os.path.abspath(self.data_dir))
            p = os.path.normcase(os.path.abspath(path))
            if p.startswith(base + os.sep):
                return os.path.relpath(os.path.abspath(path), os.path.abspath(self.data_dir)).replace(os.sep, "/")
        except (TypeError, ValueError):
            pass
        return ""

    def _erel(self, path):
        """3.78.0: path relative to the effort's folder, for a file in the effort's Library folder. 4.25.1: for a file
        anywhere in the effort's folder (a file dropped in is a document where it sits), so the effort opens the same
        wherever it is moved."""
        er, lr = getattr(self, "effort_root", ""), getattr(self, "library_root", "")
        if not er or not lr:
            return ""
        try:
            base = os.path.normcase(os.path.abspath(er))
            if os.path.normcase(os.path.abspath(path)).startswith(base + os.sep) and not self._rel(path):
                return os.path.relpath(os.path.abspath(path), os.path.abspath(er)).replace(os.sep, "/")
        except (TypeError, ValueError):
            pass
        return ""

    def path_of(self, v):
        """Where a version's original file is now: the copy kept with the effort when there is one, else where it was."""
        er = getattr(self, "effort_root", "")
        if v.get("erel") and er:                    # 3.78.0: in the effort's Library folder, wherever the effort is
            p = os.path.join(er, *v["erel"].split("/"))
            old = v.get("path", "")                 # 3.81.0: a Library a 3.78.0 copy kept beside the list
            beside = os.path.normcase(os.path.dirname(os.path.abspath(self.data_dir))) + os.sep
            if os.path.isfile(p) or not (old and os.path.normcase(os.path.abspath(old)).startswith(beside) and os.path.isfile(old)):
                return p
        if v.get("rel"):                           # the effort's own copy: only that counts, wherever the effort is
            return os.path.join(self.data_dir, *v["rel"].split("/"))
        return v.get("path", "")

    def has_original(self, v):
        p = self.path_of(v)
        return bool(p) and os.path.isfile(p)
