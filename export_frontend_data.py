#!/usr/bin/env python3
import json
import os

def get_emoji(name_lower):
    # Hardcoded map for popular/base elements
    mapping = {
        "air": "💨",
        "earth": "⛰️",
        "fire": "🔥",
        "water": "💧",
        "time": "⏳",
        "steam": "☁️",
        "lava": "🌋",
        "mud": "💩",
        "rain": "🌧️",
        "stone": "🪨",
        "sand": "⏳",
        "geyser": "⛲",
        "plant": "🌱",
        "tree": "🌳",
        "clay": "🧱",
        "brick": "🧱",
        "metal": "🔩",
        "steel": "🔩",
        "glass": "🥛",
        "electricity": "⚡",
        "energy": "💥",
        "life": "🧬",
        "human": "🧑",
        "animal": "🐾",
        "bird": "🦅",
        "fish": "🐟",
        "sun": "☀️",
        "moon": "🌙",
        "star": "⭐",
        "sky": "🌌",
        "cloud": "☁️",
        "desert": "🏜️",
        "sea": "🌊",
        "ocean": "🌊",
        "wood": "🪵",
        "paper": "📄",
        "coal": "🪨",
        "diamond": "💎",
        "gold": "🪙",
        "clock": "⏰",
        "house": "🏠",
        "city": "🏙️",
        "car": "🚗",
        "train": "🚂",
        "airplane": "✈️",
        "boat": "⛵",
        "gun": "🔫",
        "bomb": "💣",
        "dinosaur": "🦖",
        "monster": "👹",
        "deity": "👼",
        "wizard": "🧙",
        "zombie": "🧟",
        "ice": "🧊",
        "snow": "❄️",
        "cold": "🥶",
        "wind": "💨",
        "sound": "🔊",
        "light": "💡",
        "darkness": "🌑",
        "pressure": "💨",
        "swamp": "🐊",
        "forest": "🌲",
        "mountain": "🏔️",
        "volcano": "🌋"
    }
    
    if name_lower in mapping:
        return mapping[name_lower]
        
    # Keyword rules
    if "fish" in name_lower or "eel" in name_lower or "shark" in name_lower:
        return "🐟"
    if "bird" in name_lower or "duck" in name_lower or "owl" in name_lower or "eagle" in name_lower or "vulture" in name_lower or "pigeon" in name_lower or "seagull" in name_lower:
        return "🦅"
    if "bug" in name_lower or "ant" in name_lower or "spider" in name_lower or "bee" in name_lower or "butterfly" in name_lower or "caterpillar" in name_lower:
        return "🐛"
    if "plant" in name_lower or "grass" in name_lower or "leaf" in name_lower or "flower" in name_lower or "moss" in name_lower or "reed" in name_lower or "ivy" in name_lower:
        return "🌱"
    if "tree" in name_lower or "wood" in name_lower or "forest" in name_lower:
        return "🌲"
    if "cat" in name_lower or "dog" in name_lower or "cow" in name_lower or "pig" in name_lower or "horse" in name_lower or "sheep" in name_lower or "goat" in name_lower or "fox" in name_lower or "wolf" in name_lower:
        return "🐾"
    if "fire" in name_lower or "heat" in name_lower or "lava" in name_lower or "warm" in name_lower:
        return "🔥"
    if "water" in name_lower or "lake" in name_lower or "pond" in name_lower or "river" in name_lower or "stream" in name_lower or "sea" in name_lower or "ocean" in name_lower or "pool" in name_lower:
        return "💧"
    if "ice" in name_lower or "snow" in name_lower or "cold" in name_lower or "glacier" in name_lower:
        return "❄️"
    if "machine" in name_lower or "engine" in name_lower or "car" in name_lower or "truck" in name_lower or "mower" in name_lower or "robot" in name_lower:
        return "⚙️"
    if "metal" in name_lower or "gold" in name_lower or "iron" in name_lower or "steel" in name_lower or "bronze" in name_lower or "copper" in name_lower or "silver" in name_lower:
        return "🪙"
    if "magic" in name_lower or "wizard" in name_lower or "deity" in name_lower or "fairy" in name_lower or "god" in name_lower:
        return "🪄"
    if "star" in name_lower or "sun" in name_lower or "planet" in name_lower or "space" in name_lower or "galaxy" in name_lower or "universe" in name_lower:
        return "✨"
    if "food" in name_lower or "bread" in name_lower or "meat" in name_lower or "fruit" in name_lower or "cheese" in name_lower or "bacon" in name_lower or "egg" in name_lower or "steak" in name_lower or "burger" in name_lower or "pizza" in name_lower:
        return "🍔"
    if "house" in name_lower or "wall" in name_lower or "building" in name_lower or "room" in name_lower or "castle" in name_lower or "pyramid" in name_lower or "temple" in name_lower or "barn" in name_lower:
        return "🏠"
    if "clock" in name_lower or "watch" in name_lower or "timer" in name_lower:
        return "⏰"
    if "glasses" in name_lower or "lens" in name_lower or "goggles" in name_lower or "telescope" in name_lower or "microscope" in name_lower:
        return "👓"
    if "book" in name_lower or "paper" in name_lower or "letter" in name_lower or "newspaper" in name_lower:
        return "📖"
    if "clothing" in name_lower or "fabric" in name_lower or "wool" in name_lower or "leather" in name_lower or "apron" in name_lower or "sweater" in name_lower or "coat" in name_lower or "shirt" in name_lower:
        return "👕"
    
    return "🔮" # Default mystical icon

def main():
    if not os.path.exists("elements.json") or not os.path.exists("recipes.json") or not os.path.exists("paths_cache.json"):
        print("Error: Required JSON files not found in the current directory.")
        return
        
    with open("elements.json", "r", encoding="utf-8") as f:
        elements_data = json.load(f)["elements"]
        
    with open("recipes.json", "r", encoding="utf-8") as f:
        recipes_data = json.load(f)["recipes"]
        
    with open("paths_cache.json", "r", encoding="utf-8") as f:
        paths_data = json.load(f)
        
    # Map emojis to elements
    for elem in elements_data:
        elem["emoji"] = get_emoji(elem["id"])
        
    # Export JavaScript structure
    js_content = f"""// Auto-generated data file for client-side rendering
const GRAPH_DATA = {{
  elements: {json.dumps(elements_data, indent=2)},
  recipes: {json.dumps(recipes_data, indent=2)},
  paths: {json.dumps(paths_data, indent=2)}
}};
"""
    
    with open("frontend_data.js", "w", encoding="utf-8") as f:
        f.write(js_content)
        
    print("Successfully exported data to frontend_data.js.")

if __name__ == "__main__":
    main()
