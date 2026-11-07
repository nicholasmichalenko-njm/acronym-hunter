"""Where a document library's files are (3.78.0, split from docversions): the effort's folder and its Library folder,
and a version's original file, kept relative to the app's working folder (rel) or to the effort's folder (erel), so the
effort opens the same wherever it is moved. Standard library only."""
import os


class PathsMixin:
    @property
    def effort_root(self):
        """3.78.0: the effort's folder (where its Library folder sits): set by effortlib.attach, else beside the app data."""
        er = self.__dict__.get("_effort_root")
        if er is not None:
            return er
        import workspace as W
        dd = self.data_dir
        return os.path.dirname(dd) if dd.endswith(W.DATA_SUFFIX) else ""

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
        """3.78.0: path relative to the effort's folder, when the library knows it and the file is inside it."""
        er = getattr(self, "effort_root", "")
        if not er:
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
            return os.path.join(er, *v["erel"].split("/"))
        if v.get("rel"):                           # the effort's own copy: only that counts, wherever the effort is
            return os.path.join(self.data_dir, *v["rel"].split("/"))
        return v.get("path", "")

    def has_original(self, v):
        p = self.path_of(v)
        return bool(p) and os.path.isfile(p)
