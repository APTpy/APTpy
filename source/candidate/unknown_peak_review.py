"""Evidence packet helpers for complex unknown APT ion review."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import re

TARGET_ELEMENTS = ("Fe", "C", "Mn", "Si", "Al")

def integrate_window(mass, counts, centre, half_width):
    centre, half_width = float(centre), float(half_width)
    if half_width <= 0: raise ValueError("Peak half-width must be positive.")
    pairs = [(float(x), float(y)) for x, y in zip(mass, counts)
             if centre-half_width <= float(x) <= centre+half_width]
    if not pairs: raise ValueError(f"No spectrum bins fall within {centre:.6f} ± {half_width:.6f} Da/e.")
    return {"position_da": centre, "lower_da": min(x for x,_ in pairs),
            "upper_da": max(x for x,_ in pairs), "integrated_counts": sum(max(0,y) for _,y in pairs),
            "bins": len(pairs)}

def estimate_peak_share(peaks, known_counts=0.0):
    total = sum(max(0., float(p.get("integrated_counts", 0))) for p in peaks) + max(0., float(known_counts))
    for p in peaks:
        p["estimated_one_ion_share_percent"] = 100. * max(0., float(p.get("integrated_counts", 0))) / total if total else 0.
        p["priority"] = "review" if p["estimated_one_ion_share_percent"] >= .1 else "low"
    return peaks

def build_review_packet(peaks, *, alloy_system="Fe-C-Mn-Si-Al", tolerance_da=.05, assigned_ions=None):
    packet = {"format":"aptpy-unknown-peak-review", "version":1,
              "created_utc":datetime.now(timezone.utc).isoformat(), "alloy_system":alloy_system,
              "target_elements":list(TARGET_ELEMENTS), "mass_tolerance_da":float(tolerance_da),
              "assigned_ions":list(assigned_ions or []), "peaks":list(peaks),
              "review_candidates":[p for p in peaks if p.get("priority") == "review"]}
    packet["chatgpt_prompt"] = build_prompt(packet)
    return packet

def build_prompt(packet):
    return ("Interpret these APT unknown peaks using published APT assignments only. Suggest a candidate "
            "only when an exact ion formula and positive charge state has been explicitly assigned in a "
            "published APT source, with a source URL and exact figure, table or passage location. Never "
            "invent or enumerate chemically possible ions from the allowed elements, infer an unreported "
            "charge state, or use a bulk compound/precipitate formula as an APT assignment. Keep multiple "
            "published candidates when ambiguous. Prioritise ions containing Fe, C, Mn, Si or Al; ignore "
            "candidates made only of unrelated elements such as Ti or Ni. Return JSON with peak_id, "
            "candidate_ion, charge, calculated_da, mass_error_da, target_elements_present, confidence, "
            "evidence, source_url, source_location and notes. Mark peaks with no qualifying published "
            "candidate as unresolved. Do not treat one-ion share as a final composition.\n\n" +
            json.dumps({k:v for k,v in packet.items() if k != "chatgpt_prompt"}, ensure_ascii=False, indent=2))

def save_review_packet(path, packet):
    path = Path(path).expanduser(); path.write_text(json.dumps(packet, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"); return path

def parse_chatgpt_suggestions(text):
    match = re.search(r"\{.*\}|\[.*\]", text or "", flags=re.S)
    if not match: raise ValueError("No JSON object or array found in the ChatGPT response.")
    data = json.loads(match.group(0)); rows = data if isinstance(data,list) else data.get("suggestions", data.get("results",[]))
    if not isinstance(rows,list): raise ValueError("ChatGPT response must contain a suggestions/results list.")
    accepted=[]
    for row in rows:
        if isinstance(row,dict) and set(row.get("target_elements_present",[])) & set(TARGET_ELEMENTS):
            row["status"]="needs user confirmation"; accepted.append(row)
    return accepted


