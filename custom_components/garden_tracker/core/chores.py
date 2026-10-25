"""Seasonal chores for crops that live for years. Starter set: cutting back brambles in the fall.

Raspberry and blackberry roots live a decade or more, but each cane lives two years: it grows leaves the first year
(a primocane), fruits the second (a floricane) and then dies. So it is the canes that get cut to the ground, not the
plant. Sources: Chelan-Douglas Master Gardeners, "Raspberry pruning tips vary by type you grow", and Penn State
Extension, "Pruning brambles in home fruit plantings" (canes of all brambles except primocane-bearing types are removed
after fruiting; everbearing raspberries are mowed to 1 to 2 inches while dormant)."""
from __future__ import annotations

from datetime import date

FALL = (9, 11)  # September through November

BRAMBLES = {
    "raspberry": ("Raspberries",
                  "Cut the canes that fruited this year to the ground. They are brown and dry and will not fruit again; leave the green new canes, "
                  "which fruit next summer. Fall-bearing (everbearing) types can instead be cut to 1 to 2 inches above the ground once they are "
                  "dormant, for a single fall crop. The plant itself lives for years, so only the canes are cut."),
    "blackberry": ("Blackberries",
                   "Cut the canes that fruited this year to the ground. Like raspberries, each cane fruits in its second year and then dies; "
                   "leave the new canes and tie them to the trellis. Types that fruit on first-year canes can be cut to the ground once "
                   "they are dormant. The plant itself lives for years, so only the canes are cut."),
}


def due(planted: set[str] | list[str], today: date) -> list[dict]:
    """Chores that are due now for the crops planted in a garden."""
    out = []
    if FALL[0] <= today.month <= FALL[1]:
        for key, (name, text) in BRAMBLES.items():
            if key in planted:
                out.append({"crop": key, "name": name, "title": f"Cut back the {name.lower()}", "text": text})
    return out
