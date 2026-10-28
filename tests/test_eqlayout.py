"""2.55.0 equation pictures by position rules: subscripts, superscripts and fractions from where the characters sit;
ordinary text and a table row over a rule are left alone."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import eqlayout as EL

W = lambda x0, y0, x1, y1, t: (x0, y0, x1, y1, t, 90.0)
# v0 = 2 m s^-1 : "0" small and low after v, "-1" small and high after s
line = [W(0, 10, 20, 40, "v"), W(21, 30, 30, 45, "0"), W(40, 10, 55, 40, "="), W(60, 10, 75, 40, "2"),
        W(80, 10, 100, 40, "m"), W(105, 10, 120, 40, "s"), W(121, 2, 135, 18, "-1")]
assert EL.join_words(line) == "v₀ = 2 m s⁻¹", EL.join_words(line)
# a subscript word that has no Unicode form: v_{ref}
line2 = [W(0, 10, 20, 40, "v"), W(21, 30, 50, 45, "ref"), W(60, 10, 75, 40, "="), W(80, 10, 95, 40, "Δ")]
assert EL.join_words(line2) == "v_{ref} = Δ", EL.join_words(line2)
# ordinary text keeps its words, even with a small word
plain = [W(0, 10, 60, 40, "Thermal"), W(65, 30, 80, 45, "a"), W(85, 10, 150, 40, "design")]
assert EL.join_words(plain) == "Thermal a design"
# a fraction: ΔV over g0 with a bar between, and "t =" to its left
g = np.full((120, 300), 255, np.uint8)
g[49:52, 100:180] = 0                                   # the fraction bar
lines = [W(100, 20, 170, 46, "ΔV", ), W(40, 40, 90, 66, "t ="), W(105, 55, 175, 80, "g0 Isp")]
got = EL.fractions(lines, g)
assert [l[4] for l in got] == ["t = ΔV/(g0 Isp)"], [l[4] for l in got]
# a table row over a rule: not a fraction
g2 = np.full((120, 300), 255, np.uint8); g2[49:52, 0:300] = 0
rows = [W(100, 20, 170, 46, "Mass"), W(105, 55, 175, 80, "12 kg")]
assert [l[4] for l in EL.fractions(rows, g2)] == ["Mass", "12 kg"]
# no bar: not a fraction
assert [l[4] for l in EL.fractions(lines, np.full((120, 300), 255, np.uint8))] == ["ΔV", "t =", "g0 Isp"]
print("eqlayout ok")
