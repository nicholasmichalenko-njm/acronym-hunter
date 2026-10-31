"""The production format engine (3.6.0): reads and changes Word files at the XML level under a unit guard and a
content fingerprint, so every change is declared, checked and refused when it would touch anything else.

engine/  package reader and writer, unit guard, fingerprint, element order, guarded write, Word operations
pe/      the production rules: standards model, tables by row role, captions, TOC, bookmarks and cross-references,
         pages and sections, headers and footers, lists, fonts, terms

Proven first in the feasibility lab on the build PC with Word (production-format-engine repository) and in the cloud
lab on generated volumes. Stationkeeper runs it only on copies it made itself (prodcopy.py)."""
