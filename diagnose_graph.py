#!/usr/bin/env python3
import json
import os

# ----------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------
ELEMENTS_JSON = "elements.json"
RECIPES_JSON = "recipes.json"
PARSE_ERRORS_LOG = "parse_errors.log"
UNREACHABLE_LOG = "unreachable_elements.log"

def main():
    print("=" * 60)
    print("ALCHEMY SEED GRAPH DIAGNOSTIC REPORT")
    print("=" * 60)

    # 1. Total elements and recipes count
    if not os.path.exists(ELEMENTS_JSON) or not os.path.exists(RECIPES_JSON):
        print("Error: JSON files not found. Run build_seed_graph.py first.")
        return

    with open(ELEMENTS_JSON, "r", encoding="utf-8") as f:
        elements_data = json.load(f)["elements"]
    with open(RECIPES_JSON, "r", encoding="utf-8") as f:
        recipes_data = json.load(f)["recipes"]

    print(f"Total Elements: {len(elements_data)}")
    print(f"Total Recipes:  {len(recipes_data)}")
    print("-" * 60)

    # 2. Element count per level
    level_counts = {}
    for el in elements_data:
        lvl = el["level"]
        level_counts[lvl] = level_counts.get(lvl, 0) + 1

    print("Element Count per Level:")
    # Sort levels. None (unreachable) will be listed at the end.
    sorted_levels = sorted([k for k in level_counts.keys() if k is not None])
    for lvl in sorted_levels:
        print(f"  Level {lvl:2d}: {level_counts[lvl]:3d} elements")
    if None in level_counts:
        print(f"  Unreachable (Level None): {level_counts[None]:3d} elements")
    print("-" * 60)

    # 3. Count + sample of skipped/malformed lines
    parse_errors = []
    if os.path.exists(PARSE_ERRORS_LOG):
        with open(PARSE_ERRORS_LOG, "r", encoding="utf-8") as f:
            parse_errors = [line.strip() for line in f if line.strip()]

    print(f"Malformed/Skipped Lines Count: {len(parse_errors)}")
    if parse_errors:
        print("Sample of Skipped Lines:")
        for err in parse_errors[:5]:
            print(f"  * {err}")
        if len(parse_errors) > 5:
            print(f"  ... and {len(parse_errors) - 5} more errors logged in {PARSE_ERRORS_LOG}")
    print("-" * 60)

    # 4. Count + list of unreachable elements
    unreachable_elements = []
    if os.path.exists(UNREACHABLE_LOG):
        with open(UNREACHABLE_LOG, "r", encoding="utf-8") as f:
            unreachable_elements = [line.strip() for line in f if line.strip()]

    print(f"Unreachable Elements Count: {len(unreachable_elements)}")
    if unreachable_elements:
        print("Sample of Unreachable Elements:")
        for el in unreachable_elements[:10]:
            print(f"  * {el}")
        if len(unreachable_elements) > 10:
            print(f"  ... and {len(unreachable_elements) - 10} more logged in {UNREACHABLE_LOG}")
    print("-" * 60)

    # 5. Orphan elements (no incoming recipes and not a level 0 primitive)
    primitives = {"air", "earth", "fire", "water", "time"}
    recipe_outputs = {r["output"].lower().strip() for r in recipes_data}
    
    orphans = []
    for el in elements_data:
        el_id = el["id"]
        if el_id not in primitives and el_id not in recipe_outputs:
            orphans.append(f"{el['id']} ({el['name']})")

    print(f"Orphan Elements Count (no incoming recipes & not a primitive): {len(orphans)}")
    if orphans:
        print("List of Orphan Elements:")
        for el in orphans[:10]:
            print(f"  * {el}")
        if len(orphans) > 10:
            print(f"  ... and {len(orphans) - 10} more orphans identified.")
    print("=" * 60)

if __name__ == "__main__":
    main()
