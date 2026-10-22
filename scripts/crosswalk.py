import sqlite3
import json
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = "data/grc.db"
TOP_N_CANDIDATES = 5

def load_controls(conn, framework):
    cur = conn.execute(
        "SELECT control_id, title, text FROM controls WHERE framework = ?", (framework,)
    )
    return [{"control_id": r[0], "title": r[1], "text": r[2]} for r in cur.fetchall()]

def find_candidates(cmmc_controls, pcidss_controls, top_n=TOP_N_CANDIDATES):
    pcidss_texts = [c["text"] for c in pcidss_controls]
    cmmc_texts = [c["text"] for c in cmmc_controls]

    vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
    all_texts = pcidss_texts + cmmc_texts
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    pcidss_vectors = tfidf_matrix[:len(pcidss_texts)]
    cmmc_vectors = tfidf_matrix[len(pcidss_texts):]

    similarity = cosine_similarity(cmmc_vectors, pcidss_vectors)

    candidates = {}
    for i, cmmc_control in enumerate(cmmc_controls):
        scores = similarity[i]
        top_indices = scores.argsort()[::-1][:top_n]
        candidates[cmmc_control["control_id"]] = [
            pcidss_controls[j] for j in top_indices
        ]
    return candidates

def ask_llm_for_mapping(cmmc_control, pcidss_candidates):
    candidates_text = "\n\n".join(
        f"PCI-DSS {c['control_id']}: {c['text'][:400]}" for c in pcidss_candidates
    )

    system_prompt = (
        "You are a GRC compliance analyst assistant. You will be given one CMMC Level 2 "
        "practice and several candidate PCI-DSS v4.0.1 requirements. Determine which, if any, "
        "of the PCI-DSS requirements address the same underlying security control intent. "
        "Only use the control text provided — never invent control language. "
        "Respond ONLY in valid JSON, with this exact structure:\n"
        '{"mappings": [{"pcidss_id": "<id>", "confidence": "high|medium|low", "rationale": "<1-2 sentence explanation citing specific overlapping language>"}]}\n'
        "If no candidates are a reasonable match, return an empty mappings list. "
        "For pcidss_id, return ONLY the bare numeric ID (e.g. '8.2.8'), never prefixed with 'PCI-DSS'."
    )

    user_prompt = (
        f"CMMC Control {cmmc_control['control_id']}: {cmmc_control['text'][:600]}\n\n"
        f"Candidate PCI-DSS requirements:\n{candidates_text}"
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return {"mappings": [], "error": "Failed to parse LLM response"}

def log_action(conn, action, source_control_id, details):
    conn.execute(
        "INSERT INTO audit_log (action, source_control_id, details) VALUES (?, ?, ?)",
        (action, source_control_id, json.dumps(details))
    )
    conn.commit()

def normalize_pcidss_id(raw_id):
    """Strip any 'PCI-DSS' prefix the LLM may have echoed back, so IDs match the controls table exactly."""
    return raw_id.replace("PCI-DSS", "").strip()

def save_crosswalk(conn, cmmc_id, mapping):
    clean_id = normalize_pcidss_id(mapping["pcidss_id"])
    conn.execute(
        """INSERT INTO crosswalk (cmmc_control_id, pcidss_control_id, mapping_rationale, confidence, requires_human_review)
           VALUES (?, ?, ?, ?, 1)""",
        (cmmc_id, clean_id, mapping["rationale"], mapping["confidence"])
    )
    conn.commit()

def run_crosswalk(limit=None):
    conn = sqlite3.connect(DB_PATH)
    cmmc_controls = load_controls(conn, "CMMC")
    pcidss_controls = load_controls(conn, "PCI-DSS")

    if limit:
        cmmc_controls = cmmc_controls[:limit]

    print(f"Finding TF-IDF candidates for {len(cmmc_controls)} CMMC controls...")
    candidates = find_candidates(cmmc_controls, pcidss_controls)

    for cmmc_control in cmmc_controls:
        cid = cmmc_control["control_id"]
        print(f"\nProcessing {cid}...")
        result = ask_llm_for_mapping(cmmc_control, candidates[cid])

        log_action(conn, "crosswalk_attempt", cid, {
            "candidates_considered": [c["control_id"] for c in candidates[cid]],
            "result": result
        })

        for mapping in result.get("mappings", []):
            save_crosswalk(conn, cid, mapping)
            print(f"  -> {mapping['pcidss_id']} ({mapping['confidence']}): {mapping['rationale'][:100]}")

    conn.close()

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_crosswalk(limit=limit)
