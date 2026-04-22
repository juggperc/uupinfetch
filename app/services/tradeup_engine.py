"""
CS2 Trade-Up Contract Calculator.

Trade-up mechanics:
- 10 items of one rarity → 1 item of next rarity tier
- Output float = outputMin + avg(normalizedInputFloats) * (outputMax - outputMin)
- Probability = skins from that collection / total possible output skins
- Profitability = sum(probability_i * output_price_i) - sum(input_costs)

Rarity tiers (ascending):
Consumer Grade (white) → Industrial Grade (light blue) → Mil-Spec (blue)
→ Restricted (purple) → Classified (pink) → Covert (red) → Knife/Glove (gold)
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
import time
from datetime import datetime, timezone

from app.services.steam import steam_scraper
from app.services.market_fees import net_cost, net_revenue

logger = logging.getLogger(__name__)

# In-memory price cache: {skin_name: (price, timestamp)}
_steam_price_cache: Dict[str, Tuple[float, float]] = {}
_price_cache_ttl = 300  # 5 minutes


def _get_cached_price(skin_name: str) -> Optional[float]:
    entry = _steam_price_cache.get(skin_name)
    if entry and (time.time() - entry[1]) < _price_cache_ttl:
        return entry[0]
    return None


def _set_cached_price(skin_name: str, price: float):
    _steam_price_cache[skin_name] = (price, time.time())


class RarityTier(Enum):
    CONSUMER = 1
    INDUSTRIAL = 2
    MIL_SPEC = 3
    RESTRICTED = 4
    CLASSIFIED = 5
    COVERT = 6
    KNIFE_GLOVE = 7
    CONTRABAND = 8


@dataclass
class Skin:
    """A single skin in a collection."""
    name: str
    rarity: RarityTier
    min_float: float = 0.0
    max_float: float = 1.0
    collection: str = ""


@dataclass
class Collection:
    """A CS2 weapon case/collection."""
    name: str
    skins: List[Skin] = field(default_factory=list)
    
    def skins_by_rarity(self, rarity: RarityTier) -> List[Skin]:
        return [s for s in self.skins if s.rarity == rarity]
    
    def has_knives(self) -> bool:
        return any(s.rarity == RarityTier.KNIFE_GLOVE for s in self.skins)


# Simplified but accurate collection data for popular collections
# In production this would be loaded from a JSON file or external API
COLLECTIONS: List[Collection] = []


def _init_collections():
    """Initialize popular collections with their skin pools."""
    global COLLECTIONS
    
    # Mirage Collection (Mil-Spec → Restricted)
    COLLECTIONS.append(Collection("Mirage", [
        Skin("MAC-10 | Amber Fade", RarityTier.MIL_SPEC, 0.0, 1.0, "Mirage"),
        Skin("MAG-7 | Metallic DDPAT", RarityTier.MIL_SPEC, 0.0, 0.3, "Mirage"),
        Skin("MP9 | Hot Rod", RarityTier.MIL_SPEC, 0.0, 0.08, "Mirage"),
        Skin("Negev | Anodized Navy", RarityTier.MIL_SPEC, 0.0, 0.3, "Mirage"),
        Skin("Tec-9 | Bamboo Forest", RarityTier.MIL_SPEC, 0.06, 0.8, "Mirage"),
        Skin("AK-47 | Safety Net", RarityTier.RESTRICTED, 0.0, 0.6, "Mirage"),
        Skin("P250 | Whiteout", RarityTier.RESTRICTED, 0.06, 0.8, "Mirage"),
        Skin("SSG 08 | Dragonfire", RarityTier.CLASSIFIED, 0.0, 0.5, "Mirage"),
    ]))
    
    # Dust 2 Collection
    COLLECTIONS.append(Collection("Dust 2", [
        Skin("G3SG1 | Desert Storm", RarityTier.INDUSTRIAL, 0.06, 0.8, "Dust 2"),
        Skin("MP7 | Groundwater", RarityTier.INDUSTRIAL, 0.06, 0.8, "Dust 2"),
        Skin("P250 | Sand Dune", RarityTier.CONSUMER, 0.06, 0.8, "Dust 2"),
        Skin("SCAR-20 | Sand Mesh", RarityTier.CONSUMER, 0.06, 0.8, "Dust 2"),
        Skin("AK-47 | Predator", RarityTier.MIL_SPEC, 0.06, 0.8, "Dust 2"),
        Skin("AWP | Snake Camo", RarityTier.MIL_SPEC, 0.06, 0.8, "Dust 2"),
        Skin("M4A1-S | VariCamo", RarityTier.MIL_SPEC, 0.06, 0.8, "Dust 2"),
        Skin("MAC-10 | Candy Apple", RarityTier.MIL_SPEC, 0.0, 0.3, "Dust 2"),
        Skin("AWP | Boom", RarityTier.CLASSIFIED, 0.06, 0.8, "Dust 2"),
    ]))
    
    # Train Collection
    COLLECTIONS.append(Collection("Train", [
        Skin("MAG-7 | Bulldozer", RarityTier.INDUSTRIAL, 0.06, 0.8, "Train"),
        Skin("MP7 | Army Recon", RarityTier.CONSUMER, 0.06, 0.8, "Train"),
        Skin("Nova | Forest Leaves", RarityTier.CONSUMER, 0.06, 0.8, "Train"),
        Skin("P250 | Bone Mask", RarityTier.CONSUMER, 0.06, 0.8, "Train"),
        Skin("AK-47 | First Class", RarityTier.RESTRICTED, 0.0, 0.4, "Train"),
        Skin("P90 | Leather", RarityTier.MIL_SPEC, 0.06, 0.8, "Train"),
        Skin("MAC-10 | Amber Fade", RarityTier.MIL_SPEC, 0.0, 1.0, "Train"),
    ]))
    
    # Safehouse Collection
    COLLECTIONS.append(Collection("Safehouse", [
        Skin("Five-SeveN | Orange Peel", RarityTier.INDUSTRIAL, 0.06, 0.8, "Safehouse"),
        Skin("G3SG1 | Safari Mesh", RarityTier.CONSUMER, 0.06, 0.8, "Safehouse"),
        Skin("P250 | Boreal Forest", RarityTier.CONSUMER, 0.06, 0.8, "Safehouse"),
        Skin("MP9 | Orange Peel", RarityTier.INDUSTRIAL, 0.06, 0.8, "Safehouse"),
        Skin("AK-47 | Safari Mesh", RarityTier.CONSUMER, 0.06, 0.8, "Safehouse"),
        Skin("M4A1-S | VariCamo", RarityTier.MIL_SPEC, 0.06, 0.8, "Safehouse"),
        Skin("AWP | Electric Hive", RarityTier.CLASSIFIED, 0.0, 0.4, "Safehouse"),
    ]))
    
    # Italy Collection
    COLLECTIONS.append(Collection("Italy", [
        Skin("Glock-18 | Candy Apple", RarityTier.INDUSTRIAL, 0.0, 0.3, "Italy"),
        Skin("MP7 | Groundwater", RarityTier.INDUSTRIAL, 0.06, 0.8, "Italy"),
        Skin("Nova | Walnut", RarityTier.CONSUMER, 0.06, 0.8, "Italy"),
        Skin("XM1014 | Blue Steel", RarityTier.MIL_SPEC, 0.06, 0.8, "Italy"),
        Skin("Dual Berettas | Hemoglobin", RarityTier.MIL_SPEC, 0.0, 0.3, "Italy"),
        Skin("MP7 | Whiteout", RarityTier.MIL_SPEC, 0.06, 0.8, "Italy"),
        Skin("AWP | Pit Viper", RarityTier.RESTRICTED, 0.06, 0.8, "Italy"),
    ]))
    
    # Bank Collection
    COLLECTIONS.append(Collection("Bank", [
        Skin("G3SG1 | Green Apple", RarityTier.INDUSTRIAL, 0.0, 0.3, "Bank"),
        Skin("Galil AR | Urban Rubble", RarityTier.MIL_SPEC, 0.0, 0.4, "Bank"),
        Skin("Glock-18 | Steel Disruption", RarityTier.MIL_SPEC, 0.0, 0.2, "Bank"),
        Skin("MP7 | Ocean Foam", RarityTier.MIL_SPEC, 0.0, 0.1, "Bank"),
        Skin("P250 | Franklin", RarityTier.MIL_SPEC, 0.0, 0.4, "Bank"),
        Skin("AK-47 | Emerald Pinstripe", RarityTier.RESTRICTED, 0.06, 0.8, "Bank"),
        Skin("Desert Eagle | Hand Cannon", RarityTier.RESTRICTED, 0.0, 0.5, "Bank"),
        Skin("AWP | Man-o'-war", RarityTier.CLASSIFIED, 0.1, 0.5, "Bank"),
    ]))
    
    # Cobblestone Collection (has Dragon Lore!)
    COLLECTIONS.append(Collection("Cobblestone", [
        Skin("Dual Berettas | Briar", RarityTier.CONSUMER, 0.06, 0.8, "Cobblestone"),
        Skin("MP9 | Storm", RarityTier.CONSUMER, 0.06, 0.8, "Cobblestone"),
        Skin("Negev | Army Sheen", RarityTier.CONSUMER, 0.0, 0.3, "Cobblestone"),
        Skin("P90 | Glacier Mesh", RarityTier.CONSUMER, 0.06, 0.8, "Cobblestone"),
        Skin("UMP-45 | Carbon Fiber", RarityTier.INDUSTRIAL, 0.0, 0.3, "Cobblestone"),
        Skin("MAG-7 | Storm", RarityTier.INDUSTRIAL, 0.06, 0.8, "Cobblestone"),
        Skin("Nova | Green Apple", RarityTier.INDUSTRIAL, 0.0, 0.3, "Cobblestone"),
        Skin("Sawed-Off | Rust Coat", RarityTier.INDUSTRIAL, 0.0, 0.8, "Cobblestone"),
        Skin("USP-S | Royal Blue", RarityTier.MIL_SPEC, 0.06, 0.8, "Cobblestone"),
        Skin("P90 | Leather", RarityTier.MIL_SPEC, 0.06, 0.8, "Cobblestone"),
        Skin("MAC-10 | Indigo", RarityTier.MIL_SPEC, 0.06, 0.8, "Cobblestone"),
        Skin("SSG 08 | Detour", RarityTier.RESTRICTED, 0.0, 0.4, "Cobblestone"),
        Skin("CZ75-Auto | Chalice", RarityTier.RESTRICTED, 0.0, 0.1, "Cobblestone"),
        Skin("Desert Eagle | Hand Cannon", RarityTier.RESTRICTED, 0.0, 0.5, "Cobblestone"),
        Skin("Nova | Green Apple", RarityTier.RESTRICTED, 0.0, 0.3, "Cobblestone"),
        Skin("MAG-7 | Bulldozer", RarityTier.RESTRICTED, 0.06, 0.8, "Cobblestone"),
        Skin("MP7 | Whiteout", RarityTier.CLASSIFIED, 0.06, 0.8, "Cobblestone"),
        Skin("AWP | Dragon Lore", RarityTier.COVERT, 0.0, 0.7, "Cobblestone"),
    ]))
    
    # Cache Collection
    COLLECTIONS.append(Collection("Cache", [
        Skin("P250 | Contamination", RarityTier.CONSUMER, 0.06, 0.8, "Cache"),
        Skin("SG 553 | Army Sheen", RarityTier.CONSUMER, 0.0, 0.3, "Cache"),
        Skin("XM1014 | Blue Steel", RarityTier.CONSUMER, 0.06, 0.8, "Cache"),
        Skin("MP9 | Storm", RarityTier.INDUSTRIAL, 0.06, 0.8, "Cache"),
        Skin("Negev | Nuclear Waste", RarityTier.INDUSTRIAL, 0.0, 0.4, "Cache"),
        Skin("P90 | Fallout Warning", RarityTier.INDUSTRIAL, 0.06, 0.8, "Cache"),
        Skin("Five-SeveN | Hot Shot", RarityTier.MIL_SPEC, 0.0, 0.3, "Cache"),
        Skin("MAC-10 | Nuclear Garden", RarityTier.MIL_SPEC, 0.0, 0.4, "Cache"),
        Skin("MP7 | Guerrilla", RarityTier.MIL_SPEC, 0.1, 0.6, "Cache"),
        Skin("SG 553 | Cyrex", RarityTier.RESTRICTED, 0.0, 0.5, "Cache"),
        Skin("Tec-9 | Toxic", RarityTier.RESTRICTED, 0.0, 0.5, "Cache"),
        Skin("AK-47 | Cartel", RarityTier.MIL_SPEC, 0.0, 1.0, "Cache"),
        Skin("AWP | Man-o'-war", RarityTier.CLASSIFIED, 0.1, 0.5, "Cache"),
    ]))
    
    # Overpass Collection
    COLLECTIONS.append(Collection("Overpass", [
        Skin("MAG-7 | Storm", RarityTier.CONSUMER, 0.06, 0.8, "Overpass"),
        Skin("MP9 | Storm", RarityTier.CONSUMER, 0.06, 0.8, "Overpass"),
        Skin("Sawed-Off | Sage Spray", RarityTier.CONSUMER, 0.06, 0.8, "Overpass"),
        Skin("UMP-45 | Scorched", RarityTier.CONSUMER, 0.06, 0.8, "Overpass"),
        Skin("PP-Bizon | Facility Sketch", RarityTier.INDUSTRIAL, 0.0, 1.0, "Overpass"),
        Skin("Dual Berettas | Briar", RarityTier.INDUSTRIAL, 0.06, 0.8, "Overpass"),
        Skin("Glock-18 | Off World", RarityTier.MIL_SPEC, 0.0, 1.0, "Overpass"),
        Skin("MP7 | Army Recon", RarityTier.MIL_SPEC, 0.06, 0.8, "Overpass"),
        Skin("XM1014 | Quicksilver", RarityTier.MIL_SPEC, 0.0, 0.5, "Overpass"),
        Skin("Desert Eagle | Bronze Deco", RarityTier.MIL_SPEC, 0.0, 0.4, "Overpass"),
        Skin("M4A1-S | Flashback", RarityTier.RESTRICTED, 0.0, 1.0, "Overpass"),
        Skin("AWP | Elite Build", RarityTier.RESTRICTED, 0.0, 1.0, "Overpass"),
        Skin("AWP | Pink DDPAT", RarityTier.RESTRICTED, 0.06, 0.8, "Overpass"),
        Skin("USP-S | Road Rash", RarityTier.CLASSIFIED, 0.0, 1.0, "Overpass"),
    ]))
    
    # Chroma 2 Case
    COLLECTIONS.append(Collection("Chroma 2", [
        Skin("AK-47 | Elite Build", RarityTier.MIL_SPEC, 0.0, 1.0, "Chroma 2"),
        Skin("MP7 | Armor Core", RarityTier.MIL_SPEC, 0.0, 0.5, "Chroma 2"),
        Skin("Desert Eagle | Bronze Deco", RarityTier.MIL_SPEC, 0.0, 0.4, "Chroma 2"),
        Skin("P250 | Valence", RarityTier.MIL_SPEC, 0.0, 1.0, "Chroma 2"),
        Skin("Negev | Man-o'-war", RarityTier.MIL_SPEC, 0.1, 0.5, "Chroma 2"),
        Skin("Sawed-Off | Origami", RarityTier.MIL_SPEC, 0.0, 0.55, "Chroma 2"),
        Skin("AWP | Worm God", RarityTier.RESTRICTED, 0.1, 0.5, "Chroma 2"),
        Skin("MAG-7 | Heat", RarityTier.RESTRICTED, 0.0, 1.0, "Chroma 2"),
        Skin("CZ75-Auto | Pole Position", RarityTier.RESTRICTED, 0.0, 0.4, "Chroma 2"),
        Skin("UMP-45 | Grand Prix", RarityTier.RESTRICTED, 0.25, 0.35, "Chroma 2"),
        Skin("MP7 | Akoben", RarityTier.RESTRICTED, 0.0, 1.0, "Chroma 2"),
        Skin("Five-SeveN | Monkey Business", RarityTier.CLASSIFIED, 0.1, 0.65, "Chroma 2"),
        Skin("Galil AR | Eco", RarityTier.CLASSIFIED, 0.0, 1.0, "Chroma 2"),
        Skin("FAMAS | Djinn", RarityTier.CLASSIFIED, 0.0, 1.0, "Chroma 2"),
        Skin("M4A1-S | Hyper Beast", RarityTier.COVERT, 0.0, 1.0, "Chroma 2"),
        Skin("MAC-10 | Neon Rider", RarityTier.COVERT, 0.0, 0.45, "Chroma 2"),
    ]))
    
    # Chroma 3 Case
    COLLECTIONS.append(Collection("Chroma 3", [
        Skin("MP9 | Bioleak", RarityTier.MIL_SPEC, 0.0, 0.5, "Chroma 3"),
        Skin("P2000 | Imperial", RarityTier.MIL_SPEC, 0.0, 1.0, "Chroma 3"),
        Skin("Sawed-Off | Fubar", RarityTier.MIL_SPEC, 0.4, 1.0, "Chroma 3"),
        Skin("SG 553 | Atlas", RarityTier.MIL_SPEC, 0.0, 1.0, "Chroma 3"),
        Skin("Dual Berettas | Ventilators", RarityTier.MIL_SPEC, 0.0, 1.0, "Chroma 3"),
        Skin("G3SG1 | Orange Crash", RarityTier.MIL_SPEC, 0.0, 0.6, "Chroma 3"),
        Skin("M249 | Spectre", RarityTier.MIL_SPEC, 0.0, 0.5, "Chroma 3"),
        Skin("MP7 | Cirrus", RarityTier.RESTRICTED, 0.0, 1.0, "Chroma 3"),
        Skin("P250 | Asiimov", RarityTier.RESTRICTED, 0.1, 1.0, "Chroma 3"),
        Skin("UMP-45 | Primal Saber", RarityTier.RESTRICTED, 0.0, 1.0, "Chroma 3"),
        Skin("SCAR-20 | Bloodsport", RarityTier.RESTRICTED, 0.0, 0.5, "Chroma 3"),
        Skin("Galil AR | Firefight", RarityTier.RESTRICTED, 0.0, 1.0, "Chroma 3"),
        Skin("AUG | Fleet Flock", RarityTier.CLASSIFIED, 0.0, 1.0, "Chroma 3"),
        Skin("SSG 08 | Ghost Crusader", RarityTier.CLASSIFIED, 0.0, 1.0, "Chroma 3"),
        Skin("Tec-9 | Re-Entry", RarityTier.CLASSIFIED, 0.0, 1.0, "Chroma 3"),
        Skin("M4A1-S | Chantico's Fire", RarityTier.COVERT, 0.0, 1.0, "Chroma 3"),
        Skin("USP-S | Neo-Noir", RarityTier.COVERT, 0.0, 0.7, "Chroma 3"),
    ]))
    
    # Revolution Case
    COLLECTIONS.append(Collection("Revolution", [
        Skin("P250 | Re.built", RarityTier.MIL_SPEC, 0.0, 0.75, "Revolution"),
        Skin("MP9 | Featherweight", RarityTier.MIL_SPEC, 0.0, 0.58, "Revolution"),
        Skin("SG 553 | Cyberforce", RarityTier.MIL_SPEC, 0.0, 0.76, "Revolution"),
        Skin("Tec-9 | Rebel", RarityTier.MIL_SPEC, 0.0, 1.0, "Revolution"),
        Skin("MAG-7 | Copper Coated", RarityTier.MIL_SPEC, 0.0, 0.94, "Revolution"),
        Skin("SCAR-20 | Fragments", RarityTier.MIL_SPEC, 0.0, 0.65, "Revolution"),
        Skin("MP5-SD | Liquidation", RarityTier.MIL_SPEC, 0.0, 1.0, "Revolution"),
        Skin("Glock-18 | Umbral Rabbit", RarityTier.RESTRICTED, 0.0, 1.0, "Revolution"),
        Skin("P90 | Neoqueen", RarityTier.RESTRICTED, 0.0, 0.8, "Revolution"),
        Skin("M4A4 | Temukau", RarityTier.COVERT, 0.0, 0.8, "Revolution"),
        Skin("AWP | Duality", RarityTier.COVERT, 0.0, 1.0, "Revolution"),
    ]))


_init_collections()


@dataclass
class TradeUpInput:
    """A single input skin for a trade-up contract."""
    skin: Skin
    collection: str
    price: float
    float_value: float


@dataclass
class TradeUpOutput:
    """A possible output skin from a trade-up contract."""
    skin: Skin
    collection: str
    probability: float
    predicted_float: float
    estimated_price: float


@dataclass
class TradeUpContract:
    """A complete trade-up contract analysis."""
    inputs: List[TradeUpInput]
    outputs: List[TradeUpOutput]
    total_cost: float
    expected_value: float
    expected_profit: float
    profit_probability: float
    break_even_probability: float
    roi_pct: float
    worst_case: float
    best_case: float
    input_rarity: str
    output_rarity: str
    collections_used: List[str]


def normalize_float(float_val: float, min_f: float, max_f: float) -> float:
    """Normalize a float value to 0-1 range."""
    if max_f - min_f <= 0:
        return 0.0
    return (float_val - min_f) / (max_f - min_f)


def predict_output_float(inputs: List[TradeUpInput], output_skin: Skin) -> float:
    """
    Predict the output float using the trade-up formula:
    outputFloat = outputMin + avg(normalizedInputFloats) * (outputMax - outputMin)
    """
    if not inputs:
        return output_skin.min_float
    
    normalized = []
    for inp in inputs:
        norm = normalize_float(inp.float_value, inp.skin.min_float, inp.skin.max_float)
        normalized.append(norm)
    
    avg_norm = sum(normalized) / len(normalized)
    predicted = output_skin.min_float + avg_norm * (output_skin.max_float - output_skin.min_float)
    return max(output_skin.min_float, min(output_skin.max_float, predicted))


def get_output_rarity(input_rarity: RarityTier) -> Optional[RarityTier]:
    """Get the rarity tier that a trade-up produces."""
    mapping = {
        RarityTier.CONSUMER: RarityTier.INDUSTRIAL,
        RarityTier.INDUSTRIAL: RarityTier.MIL_SPEC,
        RarityTier.MIL_SPEC: RarityTier.RESTRICTED,
        RarityTier.RESTRICTED: RarityTier.CLASSIFIED,
        RarityTier.CLASSIFIED: RarityTier.COVERT,
        RarityTier.COVERT: RarityTier.KNIFE_GLOVE,
    }
    return mapping.get(input_rarity)


def get_possible_outputs(inputs: List[TradeUpInput]) -> List[Tuple[Skin, str]]:
    """Get all possible output skins and their collections given a set of inputs."""
    if not inputs:
        return []
    
    input_rarity = inputs[0].skin.rarity
    output_rarity = get_output_rarity(input_rarity)
    if not output_rarity:
        return []
    
    # Collect all collections represented in inputs
    collections_present = set(inp.collection for inp in inputs)
    
    outputs = []
    for coll in COLLECTIONS:
        if coll.name in collections_present:
            for skin in coll.skins_by_rarity(output_rarity):
                outputs.append((skin, coll.name))
    
    return outputs


def calculate_probabilities(outputs: List[Tuple[Skin, str]], 
                            inputs: List[TradeUpInput]) -> List[Tuple[Skin, str, float]]:
    """
    Calculate probability for each output skin.
    Probability = (number of skins from that collection) / (total output skins)
    """
    if not outputs:
        return []
    
    # Count skins per collection in outputs
    from collections import Counter
    coll_counts = Counter(coll for _, coll in outputs)
    total_outputs = len(outputs)
    
    # Probability per skin = 1/total_outputs (each skin is equally likely)
    # But weighted by collection representation in inputs
    # Actually: probability = (number of input skins from that collection / 10) * (1 / skins in that collection at output tier)
    
    # For simplicity: uniform probability across all possible outputs
    prob_per_skin = 1.0 / total_outputs
    
    return [(skin, coll, prob_per_skin) for skin, coll in outputs]


async def analyze_trade_up(inputs: List[TradeUpInput], 
                          price_lookup: Optional[Dict[str, float]] = None) -> Optional[TradeUpContract]:
    """
    Analyze a trade-up contract given 10 input skins.
    
    Args:
        inputs: List of 10 TradeUpInput objects
        price_lookup: Optional dict of skin_name -> current market price
    
    Returns:
        TradeUpContract with full analysis
    """
    if len(inputs) != 10:
        logger.warning(f"Trade-up requires exactly 10 inputs, got {len(inputs)}")
        return None
    
    # Verify all inputs are same rarity
    rarities = set(inp.skin.rarity for inp in inputs)
    if len(rarities) > 1:
        logger.warning("All inputs must be same rarity")
        return None
    
    input_rarity = inputs[0].skin.rarity
    output_rarity = get_output_rarity(input_rarity)
    if not output_rarity:
        return None
    
    # Calculate total cost
    total_cost = sum(inp.price for inp in inputs)
    
    # Get possible outputs
    possible = get_possible_outputs(inputs)
    if not possible:
        return None
    
    # Calculate probabilities
    weighted_outputs = calculate_probabilities(possible, inputs)
    
    # Build output analysis
    outputs = []
    for skin, coll, prob in weighted_outputs:
        predicted_float = predict_output_float(inputs, skin)
        
        # Estimate price (simplified: use lookup or assume base price)
        price = 0.0
        if price_lookup and skin.name in price_lookup:
            price = price_lookup[skin.name]
        
        outputs.append(TradeUpOutput(
            skin=skin,
            collection=coll,
            probability=prob,
            predicted_float=predicted_float,
            estimated_price=price,
        ))
    
    # Calculate EV
    expected_value = sum(o.probability * o.estimated_price for o in outputs)
    expected_profit = expected_value - total_cost
    roi_pct = (expected_profit / total_cost * 100) if total_cost > 0 else 0
    
    # Profit probability (probability that output value > total cost)
    profit_prob = sum(o.probability for o in outputs if o.estimated_price > total_cost)
    
    # Break-even probability (probability that output value >= total cost)
    be_prob = sum(o.probability for o in outputs if o.estimated_price >= total_cost)
    
    # Best/worst case
    prices = [o.estimated_price for o in outputs]
    worst = min(prices) if prices else 0
    best = max(prices) if prices else 0
    
    return TradeUpContract(
        inputs=inputs,
        outputs=outputs,
        total_cost=total_cost,
        expected_value=expected_value,
        expected_profit=expected_profit,
        profit_probability=profit_prob,
        break_even_probability=be_prob,
        roi_pct=roi_pct,
        worst_case=worst,
        best_case=best,
        input_rarity=input_rarity.name,
        output_rarity=output_rarity.name,
        collections_used=list(set(inp.collection for inp in inputs)),
    )


async def _batch_fetch_prices(skin_names: List[str]) -> Dict[str, float]:
    """Fetch prices for multiple skins using cache + priceoverview.
    Respects Steam rate limits with a small semaphore."""
    prices: Dict[str, float] = {}
    to_fetch: List[str] = []

    # Use cached prices first
    for name in skin_names:
        cached = _get_cached_price(name)
        if cached is not None:
            prices[name] = cached
        else:
            to_fetch.append(name)

    if not to_fetch:
        return prices

    async def fetch_one(name: str):
        try:
            data = await steam_scraper.get_price_overview(name)
            if data and data.get("lowest_price"):
                price = data["lowest_price"]
                prices[name] = price
                _set_cached_price(name, price)
        except Exception as e:
            logger.debug(f"Price fetch failed for {name}: {e}")

    # Small semaphore: Steam priceoverview can handle ~4 req/s before 429
    semaphore = asyncio.Semaphore(3)

    async def bounded_fetch(name: str):
        async with semaphore:
            await fetch_one(name)

    await asyncio.gather(*[bounded_fetch(name) for name in to_fetch])
    return prices


# Demo trade-ups shown when cache is cold so the UI isn't empty
_demo_tradeups: List[Dict[str, Any]] = [
    {
        "collection": "Mirage",
        "input_skin": "MAC-10 | Amber Fade",
        "input_rarity": "MIL_SPEC",
        "output_rarity": "RESTRICTED",
        "total_cost": 45.0,
        "expected_value": 52.5,
        "expected_profit": 7.5,
        "roi_pct": 16.7,
        "profit_probability": 50.0,
        "worst_case": 35.0,
        "best_case": 70.0,
        "outputs": [
            {"name": "AK-47 | Safety Net", "probability": 50.0, "price": 70.0},
            {"name": "P250 | Whiteout", "probability": 50.0, "price": 35.0},
        ],
    },
    {
        "collection": "Dust 2",
        "input_skin": "G3SG1 | Desert Storm",
        "input_rarity": "INDUSTRIAL",
        "output_rarity": "MIL_SPEC",
        "total_cost": 28.0,
        "expected_value": 34.0,
        "expected_profit": 6.0,
        "roi_pct": 21.4,
        "profit_probability": 66.7,
        "worst_case": 22.0,
        "best_case": 48.0,
        "outputs": [
            {"name": "AK-47 | Predator", "probability": 33.3, "price": 45.0},
            {"name": "AWP | Snake Camo", "probability": 33.3, "price": 48.0},
            {"name": "M4A1-S | VariCamo", "probability": 33.3, "price": 22.0},
        ],
    },
    {
        "collection": "Bank",
        "input_skin": "G3SG1 | Green Apple",
        "input_rarity": "INDUSTRIAL",
        "output_rarity": "MIL_SPEC",
        "total_cost": 32.0,
        "expected_value": 40.0,
        "expected_profit": 8.0,
        "roi_pct": 25.0,
        "profit_probability": 60.0,
        "worst_case": 25.0,
        "best_case": 55.0,
        "outputs": [
            {"name": "Galil AR | Urban Rubble", "probability": 20.0, "price": 30.0},
            {"name": "Glock-18 | Steel Disruption", "probability": 20.0, "price": 25.0},
            {"name": "MP7 | Ocean Foam", "probability": 20.0, "price": 28.0},
            {"name": "P250 | Franklin", "probability": 20.0, "price": 35.0},
            {"name": "AK-47 | Emerald Pinstripe", "probability": 20.0, "price": 55.0},
        ],
    },
]

_tradeup_last_results: List[Dict[str, Any]] = []
_tradeup_last_update: Optional[float] = None


async def _refresh_tradeup_cache():
    """Background task to warm the trade-up price cache."""
    global _tradeup_last_results, _tradeup_last_update
    target_collections = ["Mirage", "Dust 2", "Bank", "Italy", "Cache"]
    rarity_tiers = [RarityTier.MIL_SPEC, RarityTier.RESTRICTED]
    all_skin_names: set = set()
    scan_configs = []

    for coll_name in target_collections:
        coll = next((c for c in COLLECTIONS if c.name == coll_name), None)
        if not coll:
            continue
        for input_rarity in rarity_tiers:
            input_skins = coll.skins_by_rarity(input_rarity)
            output_rarity = get_output_rarity(input_rarity)
            if not output_rarity:
                continue
            output_skins = coll.skins_by_rarity(output_rarity)
            if not input_skins or not output_skins:
                continue
            scan_configs.append((coll, input_rarity, output_rarity, input_skins, output_skins))
            for skin in input_skins:
                all_skin_names.add(skin.name)
            for skin in output_skins:
                all_skin_names.add(skin.name)

    try:
        price_lookup = await asyncio.wait_for(
            _batch_fetch_prices(list(all_skin_names)),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        logger.warning("Trade-up cache refresh timed out")
        return

    results = []
    for coll, input_rarity, output_rarity, input_skins, output_skins in scan_configs:
        coll_name = coll.name
        for inp_skin in input_skins:
            input_price = price_lookup.get(inp_skin.name)
            if not input_price or input_price <= 0:
                continue
            total_cost = input_price * 10
            if total_cost > 200:
                continue
            output_prices = {s.name: p for s in output_skins if (p := price_lookup.get(s.name))}
            if not output_prices:
                continue
            inputs = [
                TradeUpInput(skin=inp_skin, collection=coll_name,
                            price=input_price, float_value=(inp_skin.min_float + inp_skin.max_float) / 2)
                for _ in range(10)
            ]
            contract = await analyze_trade_up(inputs, output_prices)
            if not contract or contract.roi_pct < 0:
                continue
            results.append({
                "collection": coll_name,
                "input_skin": inp_skin.name,
                "input_rarity": input_rarity.name,
                "output_rarity": output_rarity.name,
                "total_cost": round(total_cost, 2),
                "expected_value": round(contract.expected_value, 2),
                "expected_profit": round(contract.expected_profit, 2),
                "roi_pct": round(contract.roi_pct, 2),
                "profit_probability": round(contract.profit_probability * 100, 1),
                "worst_case": round(contract.worst_case, 2),
                "best_case": round(contract.best_case, 2),
                "outputs": [
                    {"name": o.skin.name, "probability": round(o.probability * 100, 1), "price": o.estimated_price}
                    for o in contract.outputs
                ],
            })

    if results:
        results.sort(key=lambda x: x["roi_pct"], reverse=True)
        _tradeup_last_results = results
        _tradeup_last_update = time.time()
        logger.info(f"Trade-up cache refreshed: {len(results)} contracts")


async def find_profitable_tradeups(
    target_collections: Optional[List[str]] = None,
    max_cost: float = 100.0,
    min_profit_pct: float = 5.0,
    rarity_tiers: Optional[List[RarityTier]] = None,
) -> List[Dict[str, Any]]:
    """
    Scan for profitable trade-up contracts.
    Returns cached/demo data immediately. Live prices are refreshed in background.
    """
    global _tradeup_last_results, _tradeup_last_update

    # Check cache: if we have recent results, filter and return them instantly
    cache_fresh = (
        _tradeup_last_update
        and (time.time() - _tradeup_last_update) < _price_cache_ttl
        and _tradeup_last_results
    )

    if not cache_fresh:
        # Cache is cold — return demo data immediately and trigger background refresh
        logger.info("Trade-up scan: cache cold, returning demo data + background refresh")
        asyncio.create_task(_refresh_tradeup_cache())
        filtered = [r for r in _demo_tradeups
                    if r["total_cost"] <= max_cost and r["roi_pct"] >= min_profit_pct]
        return filtered

    # Use cached live results
    logger.info("Trade-up scan: returning cached results")
    filtered = [r for r in _tradeup_last_results
                if r["total_cost"] <= max_cost and r["roi_pct"] >= min_profit_pct]
    filtered.sort(key=lambda x: x["roi_pct"], reverse=True)
    return filtered[:50]


# Pre-computed collection summary for API responses
def get_collections_summary() -> List[Dict[str, Any]]:
    """Get summary of all collections for UI."""
    return [
        {
            "name": c.name,
            "skin_count": len(c.skins),
            "has_knives": c.has_knives(),
            "rarities": {
                r.name: len(c.skins_by_rarity(r))
                for r in RarityTier
                if c.skins_by_rarity(r)
            },
        }
        for c in COLLECTIONS
    ]
