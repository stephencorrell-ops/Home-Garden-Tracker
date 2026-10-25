"""Crop rotation rules: which crops share diseases and how many years to keep them off the same ground.

Sources: Washington State University Extension, "Crop Rotation in Home Gardens" (families, wait three to four
years) and Cornell Vegetable MD Online, "Do rotations matter within disease management programs" (years per
disease, and which crops share them). `rest` is the number of years before the same family goes back in the same
spot, so a family with rest 3 is flagged when it was there one or two years ago and clear when it was three or
more years ago. The values lean to the shorter end of the ranges the sources give."""
from __future__ import annotations

FAMILIES: dict[str, dict] = {
    "nightshade": {
        "name": "Nightshade", "rest": 3,
        "note": "Tomato, pepper and potato share early blight, Verticillium wilt and bacterial spot, so they should not follow each other.",
    },
    "cucurbit": {
        "name": "Cucurbit", "rest": 3,
        "note": "Cucumber, melons, squash and pumpkin share gummy stem blight, leaf spots and Fusarium wilt.",
    },
    "brassica": {
        "name": "Cabbage family", "rest": 4,
        "note": "Cabbage, cauliflower, horseradish and the rest of the family share clubroot, black rot and blackleg. Clubroot can last 7 years in the soil.",
    },
    "allium": {
        "name": "Onion family", "rest": 3,
        "note": "Onion and garlic share leaf blights and white rot, which can stay in the soil for many years once it arrives.",
    },
    "legume": {
        "name": "Bean and pea", "rest": 3,
        "note": "Beans and peas share root rots, white mold and anthracnose.",
    },
    "apiaceae": {
        "name": "Carrot family", "rest": 3,
        "note": "Carrot, parsley, celery and dill share leaf blights.",
    },
    "aster": {
        "name": "Lettuce family", "rest": 3,
        "note": "Lettuce and its relatives share bottom rot and Sclerotinia drop.",
    },
    "chenopod": {
        "name": "Beet and spinach", "rest": 3,
        "note": "Beets, chard and spinach share leaf spots and root pests.",
    },
}

CROP_FAMILY = {
    "tomato": "nightshade", "pepper": "nightshade", "jalapeno": "nightshade", "habanero": "nightshade", "potato": "nightshade",
    "cucumber": "cucurbit", "watermelon": "cucurbit", "cantaloupe": "cucurbit", "pumpkin": "cucurbit",
    "cabbage": "brassica", "cauliflower": "brassica", "horseradish": "brassica",
    "garlic": "allium", "onion": "allium", "onion_red": "allium", "onion_white": "allium", "onion_sweet": "allium",
    "bean": "legume", "pea": "legume", "carrot": "apiaceae", "lettuce": "aster",
    "beet": "chenopod", "chard": "chenopod", "spinach": "chenopod",
}
SAME_CROP_REST = 2  # a crop with no known family still should not go back to the same spot the next year
SOURCES = [
    "https://wpcdn.web.wsu.edu/extension/uploads/sites/68/2015/08/Crop-Rotation-in-Home-Gardens.pdf",
    "https://www.vegetables.cornell.edu/pest-management/disease-factsheets/do-rotations-matter-within-disease-management-programs",
]


def family(crop: str) -> str | None:
    return CROP_FAMILY.get(crop)


def check(crop: str, earlier: str, years_ago: int) -> dict | None:
    """Is planting `crop` where `earlier` grew `years_ago` years back a problem? None when it is fine."""
    fam, other_fam = family(crop), family(earlier)
    if fam and fam == other_fam:
        rest = FAMILIES[fam]["rest"]
        if years_ago < rest:
            return {"level": "same" if crop == earlier else "family", "rest": rest, "family": FAMILIES[fam]["name"],
                    "note": FAMILIES[fam]["note"]}
        return None
    if crop == earlier and years_ago < SAME_CROP_REST:
        return {"level": "same", "rest": SAME_CROP_REST, "family": None, "note": ""}
    return None
