#!/usr/bin/env python3
import json
import os
import sqlite3

# ----------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------
RAW_TSV_PATH = "/Users/asha/Downloads/little/la2_recipes_raw.tsv"
PARSE_ERRORS_LOG = "parse_errors.log"
UNREACHABLE_LOG = "unreachable_elements.log"
ELEMENTS_JSON = "elements.json"
RECIPES_JSON = "recipes.json"
SQLITE_DB = "alchemy_graph.db"

def main():
    print("Starting Phase 1 - Seed Graph Builder...")

    # Primitive hardcoded elements
    primitives = {"air", "earth", "fire", "water"}
    
    # In-memory stores
    # elements dict: key (lowercase ID) -> {id, name, level, source, unlock_type (optional)}
    elements = {}
    
    # Initialize hardcoded primitives
    for p in primitives:
        elements[p] = {
            "id": p,
            "name": p.capitalize(),
            "level": 0,
            "source": "dataset"
        }
    
    # Initialize Time
    elements["time"] = {
        "id": "time",
        "name": "Time",
        "level": 0,
        "source": "dataset",
        "unlock_type": "progression"
    }

    # Raw parsing results
    raw_recipes = [] # list of tuples: (input_a, input_b, output_id)
    skipped_count = 0
    total_tsv_rows = 0

    # Ensure log files are cleared
    with open(PARSE_ERRORS_LOG, "w") as f:
        pass
    with open(UNREACHABLE_LOG, "w") as f:
        pass

    if not os.path.exists(RAW_TSV_PATH):
        print(f"Error: Raw dataset not found at {RAW_TSV_PATH}")
        return

    # 1. Parse the TSV file
    with open(RAW_TSV_PATH, "r", encoding="utf-8") as f:
        # Skip header
        header = f.readline()
        
        for line_num, line in enumerate(f, start=2):
            total_tsv_rows += 1
            stripped = line.strip("\n")
            if not stripped.strip():
                continue
            
            parts = stripped.split("\t")
            if len(parts) != 2:
                # Malformed row
                with open(PARSE_ERRORS_LOG, "a", encoding="utf-8") as err_f:
                    err_f.write(f"Line {line_num}: Raw split count != 2. Raw line: {stripped}\n")
                skipped_count += 1
                continue
            
            res_name = parts[0].strip()
            combos_str = parts[1].strip()
            res_key = res_name.lower().strip()

            # Ignore / override fire, water, air, earth, time
            if res_key in primitives or res_key == "time":
                # These are our Level 0 hardcoded primitives, we ignore any recipes that would define them
                continue
            
            # Special strings checking
            if combos_str == "Available from start" or combos_str == "Unlocked through progression":
                # Only Air, Earth, Time should have these, but we already handled them.
                # If any other element has it, check it.
                continue

            # Parse combos string
            # Split by '/' first, then check each segment for commas
            segments = [s.strip() for s in combos_str.split("/") if s.strip()]
            
            # Final list of valid parsed combinations for this row
            row_combos = []
            row_malformed = False

            for seg in segments:
                # Comma splitting (alternate separator)
                sub_segs = [ss.strip() for ss in seg.split(",") if ss.strip()]
                for sub in sub_segs:
                    # Validate combination format: "ingredient_a + ingredient_b"
                    plus_parts = [p.strip() for p in sub.split("+")]
                    # Check if it splits into exactly 2 non-empty ingredients
                    if len(plus_parts) != 2 or not plus_parts[0] or not plus_parts[1]:
                        row_malformed = True
                        with open(PARSE_ERRORS_LOG, "a", encoding="utf-8") as err_f:
                            err_f.write(f"Line {line_num}: Malformed combo segment '{sub}' in line: {stripped}\n")
                        break
                    
                    row_combos.append((plus_parts[0], plus_parts[1]))
                
                if row_malformed:
                    break

            if row_malformed:
                skipped_count += 1
                continue

            # Add output element if not already present
            if res_key not in elements:
                elements[res_key] = {
                    "id": res_key,
                    "name": res_name,
                    "level": None,
                    "source": "dataset"
                }

            # Add recipe definitions
            for in_a, in_b in row_combos:
                in_a_key = in_a.lower().strip()
                in_b_key = in_b.lower().strip()
                
                # Ensure input elements exist in elements dict
                if in_a_key not in elements:
                    elements[in_a_key] = {
                        "id": in_a_key,
                        "name": in_a,
                        "level": None,
                        "source": "dataset"
                    }
                if in_b_key not in elements:
                    elements[in_b_key] = {
                        "id": in_b_key,
                        "name": in_b,
                        "level": None,
                        "source": "dataset"
                    }
                
                # Sort inputs alphabetically by key
                sorted_inputs = sorted([in_a_key, in_b_key])
                raw_recipes.append((sorted_inputs[0], sorted_inputs[1], res_key))

    print(f"Parsing complete. TSV Rows evaluated: {total_tsv_rows}. Malformed lines skipped: {skipped_count}.")

    # 2. Level Computation (Iterative Relaxation)
    print("Computing element levels...")
    level_updated = True
    passes = 0
    
    while level_updated:
        level_updated = False
        passes += 1
        
        for in_a, in_b, out in raw_recipes:
            lvl_a = elements[in_a]["level"]
            lvl_b = elements[in_b]["level"]
            
            if lvl_a is not None and lvl_b is not None:
                candidate_lvl = 1 + max(lvl_a, lvl_b)
                current_lvl = elements[out]["level"]
                
                if current_lvl is None or current_lvl > candidate_lvl:
                    elements[out]["level"] = candidate_lvl
                    level_updated = True

    print(f"Level computation converged after {passes} passes.")

    # 3. Handle unreachable elements
    unreachable_count = 0
    for e_key, e_val in list(elements.items()):
        if e_val["level"] is None:
            unreachable_count += 1
            with open(UNREACHABLE_LOG, "a", encoding="utf-8") as un_f:
                un_f.write(f"{e_val['id']} : {e_val['name']}\n")

    print(f"Unreachable elements logged: {unreachable_count}.")

    # Generate unique recipe list (avoid duplicates)
    # Deduplicate raw_recipes list
    unique_recipes = []
    seen_recipes = set()
    recipe_counter = 1
    
    for in_a, in_b, out in raw_recipes:
        recipe_tuple = (in_a, in_b, out)
        if recipe_tuple not in seen_recipes:
            seen_recipes.add(recipe_tuple)
            unique_recipes.append({
                "id": f"r{recipe_counter:04d}",
                "input_a": in_a,
                "input_b": in_b,
                "output": out,
                "source": "dataset"
            })
            recipe_counter += 1

    # 4. Output JSON files
    # Filter elements: convert dict to list, matching output schema
    element_list = list(elements.values())
    
    with open(ELEMENTS_JSON, "w", encoding="utf-8") as f:
        json.dump({"elements": element_list}, f, indent=2)
        
    with open(RECIPES_JSON, "w", encoding="utf-8") as f:
        json.dump({"recipes": unique_recipes}, f, indent=2)
        
    print(f"Saved {len(element_list)} elements to {ELEMENTS_JSON}.")
    print(f"Saved {len(unique_recipes)} recipes to {RECIPES_JSON}.")

    # 5. SQLite Storage (Component 1 - Graph Store)
    print(f"Saving to SQLite database: {SQLITE_DB}...")
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
    DROP TABLE IF EXISTS elements
    """)
    cursor.execute("""
    CREATE TABLE elements (
        id TEXT PRIMARY KEY,
        name TEXT,
        level INTEGER,
        source TEXT,
        unlock_type TEXT DEFAULT NULL
    )
    """)
    
    cursor.execute("""
    DROP TABLE IF EXISTS recipes
    """)
    cursor.execute("""
    CREATE TABLE recipes (
        id TEXT PRIMARY KEY,
        input_a TEXT,
        input_b TEXT,
        output TEXT,
        source TEXT
    )
    """)
    
    # Insert elements
    for e in element_list:
        cursor.execute(
            "INSERT INTO elements (id, name, level, source, unlock_type) VALUES (?, ?, ?, ?, ?)",
            (e["id"], e["name"], e["level"], e["source"], e.get("unlock_type"))
        )
        
    # Insert recipes
    for r in unique_recipes:
        cursor.execute(
            "INSERT INTO recipes (id, input_a, input_b, output, source) VALUES (?, ?, ?, ?, ?)",
            (r["id"], r["input_a"], r["input_b"], r["output"], r["source"])
        )
        
    conn.commit()
    conn.close()
    print("Database sync complete.")
    print("Phase 1 Seed Graph Builder completed successfully!")

if __name__ == "__main__":
    main()
