"""Crop rotation rules: which crops share which soil and residue diseases, and how long to keep them off the same ground.

Sources: Washington State University Extension, "Crop Rotation in Home Gardens" (families; wait three to four years)
and Cornell Vegetable MD Online, "Do rotations matter within disease management programs" (years per disease and
which crops share it). Each disease lists the crops it affects and `rest`, the number of years before one of those
crops should go back where another host grew: a rest of 3 flags it one or two years later and clears it from the
third year on. The values lean to the shorter end of the ranges the sources give.

A variety can be resistant to some of the diseases (the letters on a seed packet, like the V and F in "Roma VF").
A disease the variety resists is left out, so the wait is set by the diseases that are left."""
from __future__ import annotations

NIGHTSHADE = ("tomato", "pepper", "jalapeno", "habanero", "potato")
CUCURBIT = ("cucumber", "watermelon", "cantaloupe", "pumpkin")
BRASSICA = ("cabbage", "cauliflower", "horseradish")
ALLIUM = ("garlic", "onion", "onion_red", "onion_white", "onion_sweet")
LEGUME = ("bean", "pea")

DISEASES: list[dict] = [
    # nightshade
    {"key": "verticillium", "name": "Verticillium wilt", "code": "V", "rest": 3, "hosts": NIGHTSHADE + ("eggplant", "strawberry", "raspberry", "blackberry")},  # strawberries should not follow nightshades
    {"key": "fusarium", "name": "Fusarium wilt", "code": "F", "rest": 3, "hosts": ("tomato",)},
    {"key": "nematode", "name": "Root-knot nematodes", "code": "N", "rest": 2, "hosts": ("tomato", "pepper", "jalapeno", "habanero")},
    {"key": "early_blight", "name": "Early blight", "code": "A", "rest": 2, "hosts": ("tomato", "potato")},
    {"key": "bacterial_spot", "name": "Bacterial spot", "code": "", "rest": 2, "hosts": ("tomato", "pepper", "jalapeno", "habanero")},
    {"key": "potato_scab", "name": "Scab and Rhizoctonia", "code": "", "rest": 3, "hosts": ("potato",)},
    # cucurbit
    {"key": "melon_fusarium", "name": "Fusarium wilt of melons", "code": "F", "rest": 4, "hosts": ("watermelon", "cantaloupe")},
    {"key": "squash_fusarium", "name": "Fusarium crown and fruit rot", "code": "F", "rest": 3, "hosts": ("pumpkin",)},
    {"key": "gummy_stem", "name": "Gummy stem blight and leaf spots", "code": "", "rest": 2, "hosts": CUCURBIT},
    # cabbage family
    {"key": "clubroot", "name": "Clubroot", "code": "", "rest": 4, "hosts": BRASSICA},
    {"key": "black_rot", "name": "Black rot and blackleg", "code": "", "rest": 3, "hosts": ("cabbage", "cauliflower")},
    # onion family
    {"key": "allium_blight", "name": "Onion leaf blights", "code": "", "rest": 2, "hosts": ALLIUM},
    {"key": "white_rot", "name": "White rot", "code": "", "rest": 3, "hosts": ALLIUM},
    # beans and peas
    {"key": "root_rot", "name": "Root rots", "code": "", "rest": 3, "hosts": LEGUME},
    {"key": "anthracnose", "name": "Anthracnose and bacterial blight", "code": "", "rest": 2, "hosts": ("bean",)},
    # others
    {"key": "carrot_blight", "name": "Carrot leaf blights", "code": "", "rest": 3, "hosts": ("carrot",)},
    {"key": "lettuce_rot", "name": "Bottom rot and drop", "code": "", "rest": 3, "hosts": ("lettuce",)},
    # shared across families (Cornell: Sclerotinia affects lettuce, beans, potato, tomato, cabbage, carrot)
    {"key": "white_mold", "name": "White mold (Sclerotinia)", "code": "", "rest": 2, "same_only": True,
     "hosts": ("lettuce", "bean", "potato", "tomato", "cabbage", "cauliflower", "carrot")},
]
BY_KEY = {d["key"]: d for d in DISEASES}
SAME_CROP_REST = 2  # a crop with no listed diseases still should not go back to the same spot the next year
SOURCES = [
    "https://wpcdn.web.wsu.edu/extension/uploads/sites/68/2015/08/Crop-Rotation-in-Home-Gardens.pdf",
    "https://www.vegetables.cornell.edu/pest-management/disease-factsheets/do-rotations-matter-within-disease-management-programs",
]


def diseases_for(crop: str) -> list[dict]:
    """The diseases a variety of this crop can be resistant to, for the seed-packet checklist."""
    return [{"key": d["key"], "name": d["name"], "code": d["code"]} for d in DISEASES if crop in d["hosts"] and not d.get("same_only")]


def check(crop: str, earlier: str, years_ago: int, resist: set[str] | frozenset[str] = frozenset()) -> dict | None:
    """Is planting `crop` where `earlier` grew `years_ago` years back a problem? None when it is fine.

    Returns the diseases that are still a risk (`risks`), the ones a resistant variety takes off the list (`resisted`),
    and `rest`, the years to wait counting only the risks left. `level` is "same" for the same crop, "family" for a
    different crop with a shared disease, and "resistant" when only resisted diseases applied."""
    hit = [d for d in DISEASES if crop in d["hosts"] and earlier in d["hosts"] and years_ago < d["rest"]
           and (crop == earlier or not d.get("same_only"))]
    if not hit and crop == earlier and not any(crop in d["hosts"] for d in DISEASES) and years_ago < SAME_CROP_REST:
        return {"level": "same", "rest": SAME_CROP_REST, "risks": ["Soil diseases and pests that build up"], "resisted": []}
    if not hit:
        return None
    risks = [d for d in hit if d["key"] not in resist]
    resisted = [d["name"] for d in hit if d["key"] in resist]
    if not risks:
        return {"level": "resistant", "rest": 0, "risks": [], "resisted": resisted}
    return {"level": "same" if crop == earlier else "family", "rest": max(d["rest"] for d in risks),
            "risks": [d["name"] for d in risks], "resisted": resisted}
