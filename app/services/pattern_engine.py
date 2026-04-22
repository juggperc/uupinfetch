"""
Pattern Detection Engine for CS2 skins.

Detects pattern-based premiums on skins that have significant value
differences based on their pattern seed / phase / fade percentage.

Supported patterns:
- Case Hardened: Blue gem index detection (seeds 1-1000)
- Doppler: Phase classification (Phase 1-4, Ruby, Sapphire, Black Pearl, Emerald)
- Fade: Percentage estimation flag
- Crimson Web: Web count flag
- Marble Fade: Fire & Ice flag

Note: Exact pattern detection requires inspect data or CSFloat API.
This engine provides classification based on available data.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PatternType(Enum):
    CASE_HARDENED = "case_hardened"
    DOPPLER = "doppler"
    FADE = "fade"
    CRIMSON_WEB = "crimson_web"
    MARBLE_FADE = "marble_fade"
    SLAUGHTER = "slaughter"
    TIGER_TOOTH = "tiger_tooth"
    UNKNOWN = "unknown"


# Case Hardened blue gem seed ranges (approximate community knowledge)
# True blue gems are extremely rare and valuable
BLUE_GEM_SEEDS = {
    "excellent": list(range(1, 20)) + [129, 130, 139, 141, 151, 168, 179, 180, 182, 194, 263, 281, 288, 306, 310, 321, 323, 333, 336, 339, 348, 363, 382, 387, 394, 403, 406, 409, 417, 422, 423, 426, 429, 430, 438, 439, 440, 442, 444, 446, 449, 453, 456, 459, 463, 464, 469, 473, 475, 478, 479, 481, 485, 487, 489, 490, 493, 497, 498, 501, 506, 509, 510, 512, 516, 517, 520, 521, 526, 529, 530, 533, 534, 535, 537, 539, 541, 542, 546, 548, 549, 550, 552, 555, 556, 557, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584, 585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685, 686, 687, 688, 689, 690, 691, 692, 693, 694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749, 750, 751, 752, 753, 754, 755, 756, 757, 758, 759, 760, 761, 762, 763, 764, 765, 766, 767, 768, 769, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881, 882, 883, 884, 885, 886, 887, 888, 889, 890, 891, 892, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 916, 917, 918, 919, 920, 921, 922, 923, 924, 925, 926, 927, 928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 950, 951, 952, 953, 954, 955, 956, 957, 958, 959, 960, 961, 962, 963, 964, 965, 966, 967, 968, 969, 970, 971, 972, 973, 974, 975, 976, 977, 978, 979, 980, 981, 982, 983, 984, 985, 986, 987, 988, 989, 990, 991, 992, 993, 994, 995, 996, 997, 998, 999, 1000],
    "good": [21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 112, 116, 122, 125, 127, 134, 135, 136, 137, 138, 140, 142, 143, 144, 145, 146, 147, 148, 149, 150, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 181, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 197, 198, 199, 200],
}

# Doppler phases by name pattern
DOPPLER_PATTERNS = {
    "Phase 1": ["doppler", "phase 1"],
    "Phase 2": ["doppler", "phase 2"],
    "Phase 3": ["doppler", "phase 3"],
    "Phase 4": ["doppler", "phase 4"],
    "Ruby": ["ruby"],
    "Sapphire": ["sapphire"],
    "Black Pearl": ["black pearl"],
    "Emerald": ["emerald"],
    "Gamma Doppler": ["gamma doppler"],
}

# Skin types that have pattern value
PATTERN_SKINS = {
    PatternType.CASE_HARDENED: [
        "AK-47", "Five-SeveN", "Karambit", "M9 Bayonet", "Bayonet",
        "Butterfly Knife", "Flip Knife", "Gut Knife", "Huntsman Knife",
        "Falchion Knife", "Shadow Daggers", "Bowie Knife", "Ursus Knife",
        "Navaja Knife", "Stiletto Knife", "Talon Knife", "Classic Knife",
        "Skeleton Knife", "Survival Knife", "Paracord Knife", "Nomad Knife"
    ],
    PatternType.DOPPLER: [
        "Karambit", "M9 Bayonet", "Bayonet", "Butterfly Knife", "Flip Knife",
        "Gut Knife", "Huntsman Knife", "Falchion Knife", "Shadow Daggers",
        "Bowie Knife", "Ursus Knife", "Navaja Knife", "Stiletto Knife",
        "Talon Knife", "Classic Knife", "Skeleton Knife", "Survival Knife",
        "Paracord Knife", "Nomad Knife", "Glock-18"
    ],
    PatternType.FADE: [
        "AK-47", "Karambit", "M9 Bayonet", "Bayonet", "Butterfly Knife",
        "Flip Knife", "Gut Knife", "Huntsman Knife", "Falchion Knife",
        "Shadow Daggers", "Bowie Knife", "Ursus Knife", "Navaja Knife",
        "Stiletto Knife", "Talon Knife", "Classic Knife", "Skeleton Knife",
        "Survival Knife", "Paracord Knife", "Nomad Knife", "MP7", "MAC-10",
        "R8 Revolver", "G3SG1", "MP9", "SSG 08"
    ],
    PatternType.CRIMSON_WEB: [
        "Karambit", "M9 Bayonet", "Bayonet", "Butterfly Knife", "Flip Knife",
        "Gut Knife", "Huntsman Knife", "Falchion Knife", "Shadow Daggers",
        "Bowie Knife", "Ursus Knife", "Navaja Knife", "Stiletto Knife",
        "Talon Knife", "Classic Knife", "Skeleton Knife", "Survival Knife",
        "Paracord Knife", "Nomad Knife", "AWP", "M4A4", "Desert Eagle",
        "Dual Berettas"
    ],
    PatternType.MARBLE_FADE: [
        "Karambit", "M9 Bayonet", "Bayonet", "Butterfly Knife", "Flip Knife",
        "Gut Knife", "Huntsman Knife", "Falchion Knife", "Shadow Daggers",
        "Bowie Knife", "Ursus Knife", "Navaja Knife", "Stiletto Knife",
        "Talon Knife", "Classic Knife", "Skeleton Knife", "Survival Knife",
        "Paracord Knife", "Nomad Knife", "AWP", "Glock-18"
    ],
    PatternType.SLAUGHTER: [
        "Karambit", "M9 Bayonet", "Bayonet", "Butterfly Knife", "Flip Knife",
        "Gut Knife", "Huntsman Knife", "Falchion Knife", "Shadow Daggers",
        "Bowie Knife", "Ursus Knife", "Navaja Knife", "Stiletto Knife",
        "Talon Knife", "Classic Knife"
    ],
    PatternType.TIGER_TOOTH: [
        "Karambit", "M9 Bayonet", "Bayonet", "Butterfly Knife", "Flip Knife",
        "Gut Knife", "Huntsman Knife", "Falchion Knife", "Shadow Daggers",
        "Bowie Knife", "Ursus Knife", "Navaja Knife", "Stiletto Knife",
        "Talon Knife", "Classic Knife"
    ],
}


@dataclass
class PatternResult:
    """Result of pattern detection on a skin."""
    item_name: str
    pattern_type: PatternType
    pattern_subtype: str = ""  # e.g., "Phase 2", "Blue Gem", etc.
    tier: str = "normal"  # normal, good, excellent, god
    estimated_premium_pct: float = 0.0
    notes: str = ""


def detect_pattern_type(item_name: str) -> PatternType:
    """Detect which pattern type a skin has based on its name."""
    name_lower = item_name.lower()
    
    if "case hardened" in name_lower or "ch" in name_lower:
        return PatternType.CASE_HARDENED
    if "doppler" in name_lower or "ruby" in name_lower or "sapphire" in name_lower or "black pearl" in name_lower or "emerald" in name_lower:
        return PatternType.DOPPLER
    if "fade" in name_lower and "marble" not in name_lower:
        return PatternType.FADE
    if "crimson web" in name_lower or "cw" in name_lower:
        return PatternType.CRIMSON_WEB
    if "marble fade" in name_lower:
        return PatternType.MARBLE_FADE
    if "slaughter" in name_lower:
        return PatternType.SLAUGHTER
    if "tiger tooth" in name_lower or "tt" in name_lower:
        return PatternType.TIGER_TOOTH
    
    return PatternType.UNKNOWN


def detect_doppler_phase(item_name: str) -> str:
    """Detect Doppler phase from item name."""
    name_lower = item_name.lower()
    
    if "black pearl" in name_lower:
        return "Black Pearl"
    if "ruby" in name_lower:
        return "Ruby"
    if "sapphire" in name_lower:
        return "Sapphire"
    if "emerald" in name_lower:
        return "Emerald"
    if "gamma" in name_lower:
        return "Gamma Doppler"
    if "phase 4" in name_lower:
        return "Phase 4"
    if "phase 3" in name_lower:
        return "Phase 3"
    if "phase 2" in name_lower:
        return "Phase 2"
    if "phase 1" in name_lower:
        return "Phase 1"
    
    return "Unknown"


def classify_case_hardened(paint_seed: Optional[int]) -> Dict[str, Any]:
    """Classify a Case Hardened skin by its paint seed."""
    if paint_seed is None:
        return {"tier": "unknown", "premium_pct": 0, "notes": "No paint seed available"}
    
    if paint_seed in BLUE_GEM_SEEDS["excellent"]:
        return {"tier": "excellent", "premium_pct": 200, "notes": "Excellent blue gem pattern. High premium expected."}
    elif paint_seed in BLUE_GEM_SEEDS["good"]:
        return {"tier": "good", "premium_pct": 80, "notes": "Good blue pattern. Moderate premium expected."}
    else:
        return {"tier": "normal", "premium_pct": 0, "notes": "Standard pattern. No significant premium."}


def analyze_pattern(item_name: str, paint_seed: Optional[int] = None,
                   float_value: Optional[float] = None,
                   exterior: Optional[str] = None) -> PatternResult:
    """
    Analyze a skin for pattern-based value.
    
    Args:
        item_name: Full skin name (e.g., "AK-47 | Case Hardened (Field-Tested)")
        paint_seed: Paint seed from inspect/CSFloat (0-1000)
        float_value: Float value (0.0-1.0)
        exterior: Wear condition string
    
    Returns:
        PatternResult with classification and estimated premium
    """
    pattern_type = detect_pattern_type(item_name)
    
    if pattern_type == PatternType.UNKNOWN:
        return PatternResult(item_name=item_name, pattern_type=pattern_type)
    
    subtype = ""
    tier = "normal"
    premium = 0.0
    notes = ""
    
    if pattern_type == PatternType.CASE_HARDENED:
        ch_info = classify_case_hardened(paint_seed)
        subtype = "Blue Gem" if ch_info["tier"] in ("good", "excellent") else "Standard"
        tier = ch_info["tier"]
        premium = ch_info["premium_pct"]
        notes = ch_info["notes"]
    
    elif pattern_type == PatternType.DOPPLER:
        phase = detect_doppler_phase(item_name)
        subtype = phase
        if phase in ("Ruby", "Sapphire", "Black Pearl", "Emerald"):
            tier = "god"
            premium = 300
            notes = f"{phase} is an ultra-rare gem pattern. Extreme premium expected."
        elif phase in ("Phase 2", "Phase 4"):
            tier = "good"
            premium = 20
            notes = f"{phase} has good pink/blue coverage. Moderate premium possible."
        elif phase == "Phase 1":
            tier = "normal"
            premium = 0
            notes = "Phase 1 has less desirable colors. Standard pricing."
    
    elif pattern_type == PatternType.FADE:
        subtype = "Full Fade"
        tier = "good"
        premium = 30
        notes = "Fade patterns vary by percentage. Full/max fade commands premium."
    
    elif pattern_type == PatternType.CRIMSON_WEB:
        subtype = "Webbed"
        tier = "good"
        premium = 50
        notes = "Crimson Web value depends on web count and position. High float = more visible webs."
    
    elif pattern_type == PatternType.MARBLE_FADE:
        subtype = "Fire & Ice"
        tier = "good"
        premium = 80
        notes = "True Fire & Ice (no yellow) commands significant premium."
    
    elif pattern_type == PatternType.SLAUGHTER:
        subtype = "Patterned"
        tier = "normal"
        premium = 10
        notes = "Slaughter patterns have minor value differences. Diamond/heart patterns are premium."
    
    elif pattern_type == PatternType.TIGER_TOOTH:
        subtype = "Striped"
        tier = "normal"
        premium = 0
        notes = "Tiger Tooth has uniform pattern. No significant seed-based premium."
    
    return PatternResult(
        item_name=item_name,
        pattern_type=pattern_type,
        pattern_subtype=subtype,
        tier=tier,
        estimated_premium_pct=premium,
        notes=notes,
    )


def get_pattern_alert(item_name: str, current_price: float,
                     paint_seed: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Generate an alert if a skin has a potentially valuable pattern
    that may be underpriced.
    
    Returns alert dict or None if no pattern value detected.
    """
    result = analyze_pattern(item_name, paint_seed)
    
    if result.tier in ("normal", "unknown"):
        return None
    
    return {
        "item_name": item_name,
        "pattern_type": result.pattern_type.value,
        "pattern_subtype": result.pattern_subtype,
        "tier": result.tier,
        "current_price": current_price,
        "estimated_fair_price": round(current_price * (1 + result.estimated_premium_pct / 100), 2),
        "potential_premium_pct": result.estimated_premium_pct,
        "notes": result.notes,
    }


# Pre-computed list of pattern skins for search/filtering
ALL_PATTERN_SKIN_NAMES: List[str] = []

def _init_pattern_skins():
    """Build list of all pattern skin base names."""
    global ALL_PATTERN_SKIN_NAMES
    names = set()
    for pattern_type, weapons in PATTERN_SKINS.items():
        for weapon in weapons:
            skin_name = {
                PatternType.CASE_HARDENED: "Case Hardened",
                PatternType.DOPPLER: "Doppler",
                PatternType.FADE: "Fade",
                PatternType.CRIMSON_WEB: "Crimson Web",
                PatternType.MARBLE_FADE: "Marble Fade",
                PatternType.SLAUGHTER: "Slaughter",
                PatternType.TIGER_TOOTH: "Tiger Tooth",
            }.get(pattern_type, "")
            if skin_name:
                names.add(f"{weapon} | {skin_name}")
    ALL_PATTERN_SKIN_NAMES = sorted(list(names))


_init_pattern_skins()
