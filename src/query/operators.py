import ast
import re
import pandas as pd
import duckdb
import json
from pathlib import Path
from .evidence import collect_evidence

def is_valid_meta_value(v):
    if v is None or pd.isna(v):
        return False
    s = str(v).strip()
    return s != "" and s.lower() not in {"unknown", "nan", "none", "null"}

def load_context(data_dir):
    data_dir = Path(data_dir)
    db_path = data_dir / "index" / "research_corpus.duckdb"
    
    ctx = {
        "data_dir": data_dir,
        "db": None,
        "dfs": {},
        "paper_meta": {}
    }
    
    if db_path.exists():
        ctx["db"] = duckdb.connect(str(db_path))
    
    # Pre-load some critical CSVs for quick lookup
    for name in ["entities", "result_tuples", "paper_entity_summary", "extraction_registry", "paper_section_stats"]:
        p = data_dir / "extracted" / f"{name}.csv"
        if p.exists():
            ctx["dfs"][name] = pd.read_csv(p)
            
    # Metadata priority: 
    # 1. document_registry.csv
    # 2. manifest_100.csv
    # 3. extraction_registry.csv
    # 4. paper_entity_summary.csv
    meta_sources = [
        data_dir / "registry" / "document_registry.csv",
        data_dir / "registry" / "manifest_100.csv",
        data_dir / "extracted" / "extraction_registry.csv",
        data_dir / "extracted" / "paper_entity_summary.csv"
    ]
    
    for ms in meta_sources:
        if ms.exists():
            try:
                df = pd.read_csv(ms)
                
                # Synthesize paper_id for manifest if missing
                if ms.name == "manifest_100.csv" and "paper_id" not in df.columns:
                    df = df.copy()
                    df["paper_id"] = [f"P{i+1:03d}" for i in range(len(df))]
                
                if "paper_id" in df.columns:
                    for _, row in df.iterrows():
                        pid = str(row["paper_id"])
                        if pid not in ctx["paper_meta"]:
                            ctx["paper_meta"][pid] = {"title": "Unknown", "year": "Unknown"}
                        
                        # Merge title: only overwrite if current is invalid
                        for col in ["title", "paper_title"]:
                            if col in df.columns and is_valid_meta_value(row[col]):
                                if not is_valid_meta_value(ctx["paper_meta"][pid].get("title")):
                                    ctx["paper_meta"][pid]["title"] = str(row[col])
                        
                        # Merge year: only overwrite if current is invalid
                        for col in ["year", "publish_year"]:
                            if col in df.columns and is_valid_meta_value(row[col]):
                                if not is_valid_meta_value(ctx["paper_meta"][pid].get("year")):
                                    ctx["paper_meta"][pid]["year"] = row[col]
            except:
                continue

    # Fallback title extraction from sections
    sections_path = data_dir / "sections" / "sections.jsonl"
    if sections_path.exists():
        try:
            with open(sections_path, "r", encoding="utf-8-sig") as f:
                seen_papers = set()
                for line in f:
                    if not line.strip(): continue
                    row = json.loads(line)
                    pid = str(row["paper_id"])
                    if pid in seen_papers: continue
                    
                    if not is_valid_meta_value(ctx["paper_meta"].get(pid, {}).get("title")):
                        text = row.get("text", "").strip()
                        if text:
                            # Take first line or first 160 chars
                            first_line = text.split("\n")[0].strip()
                            fallback_title = first_line[:160]
                            if pid not in ctx["paper_meta"]:
                                ctx["paper_meta"][pid] = {"title": fallback_title, "year": "Unknown"}
                            else:
                                ctx["paper_meta"][pid]["title"] = fallback_title
                    seen_papers.add(pid)
        except:
            pass
                
    # Build internal citation graph from manifest referenced_works
    manifest_paths = [
        data_dir / "registry" / "manifest_100.csv",
        Path("corpus") / "manifest_100.csv",
        Path("artifacts") / "manifests" / "manifest_100.csv",
    ]
    for mp in manifest_paths:
        if mp.exists():
            try:
                mdf = pd.read_csv(mp)
                if "paper_id" not in mdf.columns:
                    mdf["paper_id"] = [f"P{i+1:03d}" for i in range(len(mdf))]
                # Map openalex_id -> paper_id
                oa_to_pid = {}
                if "openalex_id" in mdf.columns:
                    for _, r in mdf.iterrows():
                        oa = str(r["openalex_id"]).strip()
                        if oa and oa.lower() not in {"nan", "none", ""}:
                            oa_to_pid[oa] = str(r["paper_id"])
                # Build cite counts: how many corpus papers cite each corpus paper
                cite_counts = {pid: 0 for pid in oa_to_pid.values()}
                paper_cited_by = {pid: [] for pid in oa_to_pid.values()}
                if "referenced_works" in mdf.columns:
                    for _, r in mdf.iterrows():
                        citing_pid = str(r["paper_id"])
                        rw_raw = r.get("referenced_works", "")
                        if pd.isna(rw_raw) or not str(rw_raw).strip():
                            continue
                        try:
                            refs = ast.literal_eval(str(rw_raw))
                        except Exception:
                            refs = []
                        for ref in refs:
                            ref = str(ref).strip()
                            if ref in oa_to_pid:
                                target_pid = oa_to_pid[ref]
                                cite_counts[target_pid] = cite_counts.get(target_pid, 0) + 1
                                paper_cited_by.setdefault(target_pid, []).append(citing_pid)
                ctx["cite_counts"] = cite_counts
                ctx["paper_cited_by"] = paper_cited_by
                ctx["oa_to_pid"] = oa_to_pid
            except Exception:
                pass
            break

    if "cite_counts" not in ctx:
        ctx["cite_counts"] = {}
        ctx["paper_cited_by"] = {}
        ctx["oa_to_pid"] = {}

    return ctx

def answer_single_doc(question, route, ctx):
    pid = route["entities"].get("paper_id")
    df_sum = ctx["dfs"].get("paper_entity_summary")
    meta = ctx["paper_meta"].get(pid, {"title": "Unknown", "year": "Unknown"})
    
    if df_sum is None or pid not in df_sum["paper_id"].values:
        ans = f"Basic metadata for {pid} ({meta['title']}, {meta['year']}):\n"
        ans += "Detailed extraction summary not found. Paper might have failed extraction stages."
        evidence = collect_evidence([{"paper_id": pid}], ctx["data_dir"], paper_meta=ctx["paper_meta"])
        return ans, evidence, ["Paper missing from paper_entity_summary.csv"]
    
    row = df_sum[df_sum["paper_id"] == pid].iloc[0]
    ans = f"Findings for {pid} ({meta['title']}, {meta['year']}):\n"
    ans += f"- Datasets: {row['datasets']}\n"
    ans += f"- Models: {row['models']}\n"
    ans += f"- Metrics: {row['metrics']}\n"
    ans += f"- Generators: {row['generator_families']}\n"
    ans += f"- Method Keywords: {row.get('method_keywords', 'none')}\n"
    ans += f"- Results Extracted: {row['result_tuple_count']}"
    
    df_res = ctx["dfs"].get("result_tuples")
    p_results = df_res[df_res["paper_id"] == pid].to_dict('records') if df_res is not None else []
    
    # Try to get result evidence first
    evidence = collect_evidence(p_results, ctx["data_dir"], paper_meta=ctx["paper_meta"])
    
    # If no result evidence, fallback to section snippets
    if not evidence:
        fallback_rows = [
            {"paper_id": pid, "section_type": "abstract"},
            {"paper_id": pid, "section_type": "introduction"},
            {"paper_id": pid, "section_type": "method"}
        ]
        evidence = collect_evidence(fallback_rows, ctx["data_dir"], paper_meta=ctx["paper_meta"])
        
    # Final fallback if still empty
    if not evidence:
        evidence = collect_evidence([{"paper_id": pid}], ctx["data_dir"], paper_meta=ctx["paper_meta"])
    
    return ans, evidence, []

def answer_aggregation(question, route, ctx):
    df_ent = ctx["dfs"].get("entities")
    if df_ent is None:
        return "Entity data not available for aggregation.", [], ["entities.csv missing"]
    
    q = question.lower()
    etype = "dataset"
    if "metric" in q: etype = "metric"
    elif "model" in q or "backbone" in q: etype = "model_backbone"
    elif "generator" in q: etype = "generator_family"
    
    top = df_ent[df_ent["entity_type"] == etype]["entity"].value_counts().head(10)
    
    if top.empty:
        return f"No common {etype} entities found.", [], []
        
    ans = f"Top 10 {etype} entities across the corpus:\n"
    evidence_rows = []
    for i, (name, count) in enumerate(top.items(), 1):
        ans += f"{i}. {name} (mentioned in {count} locations)\n"
        
        # Collect top 2 example papers for each top entity
        if i <= 5: # Limit to top 5 to avoid evidence bloat
            examples = df_ent[(df_ent["entity_type"] == etype) & (df_ent["entity"] == name)].head(2)
            evidence_rows.extend(examples.to_dict('records'))
        
    evidence = collect_evidence(evidence_rows, ctx["data_dir"], paper_meta=ctx["paper_meta"], max_items=10)
    
    return ans, evidence, ["Entity counts are based on mention frequency, not unique papers."]

def answer_contradiction(question, route, ctx):
    df_res = ctx["dfs"].get("result_tuples")
    if df_res is None or df_res.empty:
        return "Result tuple data not available for contradiction analysis.", [], ["result_tuples.csv missing or empty"]
    
    # Filter for valid numeric values
    df_num = df_res.dropna(subset=["value_numeric"])
    
    # Group by dataset and metric
    groups = df_num.groupby(["dataset_guess", "metric_guess"])
    
    contradictions = []
    for (ds, met), group in groups:
        if ds == "unknown" or len(group["paper_id"].unique()) < 2:
            continue
            
        v_min = group["value_numeric"].min()
        v_max = group["value_numeric"].max()
        spread = v_max - v_min
        
        # Heuristic threshold: >5 for percentages, >0.05 for decimals
        scale = group["value_scale_guess"].iloc[0]
        threshold = 5.0 if scale == "percentage" else 0.05
        
        if spread > threshold:
            contradictions.append({
                "dataset": ds,
                "metric": met,
                "spread": spread,
                "min": v_min,
                "max": v_max,
                "papers": group["paper_id"].unique().tolist(),
                "rows": group.to_dict('records')
            })
            
    if not contradictions:
        return "No significant numeric result contradictions detected among papers reporting comparable metrics.", [], []
        
    # Sort by spread
    contradictions = sorted(contradictions, key=lambda x: x["spread"], reverse=True)[:3]
    
    ans = "Potential result disagreements detected:\n"
    all_evidence_rows = []
    for c in contradictions:
        ans += f"- {c['dataset']} ({c['metric']}): Values range from {c['min']} to {c['max']} (spread: {c['spread']:.2f}) across papers {', '.join(c['papers'])}\n"
        all_evidence_rows.extend(c['rows'][:2])
        
    evidence = collect_evidence(all_evidence_rows, ctx["data_dir"], paper_meta=ctx["paper_meta"])
    return ans, evidence, ["Treating numeric variance as disagreement; results may not be directly comparable due to different settings."]

def answer_temporal(question, route, ctx):
    df_sum = ctx["dfs"].get("paper_entity_summary")
    if df_sum is None:
        return "Metadata not available for temporal analysis.", [], ["paper_entity_summary.csv missing"]
    
    # Group by year
    years_data = df_sum[df_sum["year"] != "Unknown"]["year"].dropna()
    years = sorted(years_data.unique())
    ans = "Research trends over time:\n"
    for yr in years:
        count = len(df_sum[df_sum["year"] == yr])
        ans += f"- {yr}: {count} papers\n"
        
    # Add data basis to evidence
    evidence = [{"paper_id": "DATA_BASIS", "title": "paper_entity_summary.csv", "year": "N/A", "anchor": "index", "snippet": f"Summary count over {len(years)} years."}]
    return ans, evidence, ["Temporal analysis is based on extraction summary metadata."]

def answer_citation_graph(question, route, ctx):
    cite_counts = ctx.get("cite_counts", {})
    paper_cited_by = ctx.get("paper_cited_by", {})

    if not cite_counts:
        return (
            "Citation graph is not available: referenced_works data was not loaded.",
            [],
            ["manifest_100.csv not found or missing referenced_works/openalex_id columns."]
        )

    q = question.lower()

    # --- Most-cited within corpus ---
    if any(k in q for k in ["most cited", "highly cited", "most influential", "cited most"]):
        ranked = sorted(cite_counts.items(), key=lambda x: x[1], reverse=True)
        top = [(pid, cnt) for pid, cnt in ranked if cnt > 0][:10]
        if not top:
            return "No internal citations found in the corpus.", [], ["All papers have 0 internal citations."]
        meta = ctx.get("paper_meta", {})
        ans = "Most-cited papers within the corpus (internal citation count):\n"
        for pid, cnt in top:
            m = meta.get(pid, {})
            title = m.get("title", pid)
            ans += f"  {pid} — {title[:80]}: cited by {cnt} corpus paper(s)\n"
        evidence = [{"paper_id": "DATA_BASIS", "title": "manifest_100.csv referenced_works",
                     "year": "N/A", "anchor": "citation_graph",
                     "snippet": f"Internal graph built from {len(cite_counts)} corpus papers."}]
        return ans, evidence, ["Internal citation graph only; does not include external citations."]

    # --- Papers citing a specific paper / building on a specific work ---
    meta = ctx.get("paper_meta", {})
    df_ent = ctx["dfs"].get("entities")
    
    # Identify target papers from question (PID, title fragment, or entity mention)
    targets = []
    # 1. Check for PIDs
    pid_match = re.search(r"\b(p\d{3})\b", q)
    if pid_match:
        targets.append(pid_match.group(1).upper())
    
    # 2. Check for entities mentioned in question that might be 'the work' being built on
    if not targets and df_ent is not None:
        all_entities = df_ent["entity"].dropna().unique()
        # Find entities in question, prioritising longer matches
        matched_entities = sorted([e for e in all_entities if str(e).lower() in q and len(str(e)) > 3], key=len, reverse=True)
        if matched_entities:
            entity = matched_entities[0]
            # Find papers that 'own' this entity (e.g. title contains it or it's a dataset they introduced)
            for pid, m in meta.items():
                if entity.lower() in m.get("title", "").lower():
                    targets.append(pid)
    
    # 3. Check for title fragments
    if not targets:
        for pid, m in meta.items():
            t = m.get("title", "").lower()
            if len(t) > 10 and t in q:
                targets.append(pid)

    if targets:
        targets = list(set(targets)) # unique
        all_citers = []
        for target_pid in targets:
            citers = paper_cited_by.get(target_pid, [])
            if citers:
                all_citers.extend([(target_pid, c) for c in citers])
        
        if all_citers:
            ans = "Citation Graph: Papers in the corpus identified as building on or citing the target work(s):\n"
            for target_pid, citer_pid in all_citers:
                tm = meta.get(target_pid, {})
                cm = meta.get(citer_pid, {})
                ans += f"  - {citer_pid} ({cm.get('title', citer_pid)[:60]}) -> builds on {target_pid} ({tm.get('title', target_pid)[:40]})\n"
            evidence = [{"paper_id": "DATA_BASIS", "title": "manifest_100.csv referenced_works",
                         "year": "N/A", "anchor": "citation_graph", "snippet": f"Found {len(all_citers)} citation edges."}]
            return ans, evidence, ["Internal corpus citations only."]
        else:
            target_str = ", ".join(targets)
            ans = f"No papers in this corpus were found to internally cite or build on the work(s): {target_str}."
            return ans, [], ["Found the target papers but no internal citation edges exist in this 100-paper subset."]

    # --- Fallback: show top 5 most-cited ---
    ranked = sorted(cite_counts.items(), key=lambda x: x[1], reverse=True)
    top = [(pid, cnt) for pid, cnt in ranked if cnt > 0][:5]
    ans = "Citation graph loaded. Top internally-cited papers:\n"
    for pid, cnt in top:
        m = meta.get(pid, {})
        ans += f"  {pid} — {m.get('title', pid)[:70]}: {cnt} internal citation(s)\n"
    evidence = [{"paper_id": "DATA_BASIS", "title": "manifest_100.csv referenced_works",
                 "year": "N/A", "anchor": "citation_graph",
                 "snippet": f"Graph built from {len(cite_counts)} corpus papers."}]
    return ans, evidence, ["Question did not match a specific paper; showing top-cited as fallback."]


def answer_multihop(question, route, ctx):
    df_ent = ctx["dfs"].get("entities")
    if df_ent is None:
        return "Missing entity data.", [], ["entities.csv missing"]

    q = question.lower()

    # Extract up to two entity terms from the question using known entity dictionaries
    # We search for any entity name that appears in the question text
    all_entities = df_ent["entity"].dropna().unique()
    matched = [e for e in all_entities if str(e).lower() in q and len(str(e)) > 2]

    # Year filter
    year_match = re.search(r'\b(20\d{2})\b', question)
    year_filter = int(year_match.group(1)) if year_match else None

    if not matched and year_filter is None:
        ans = "Could not identify specific entities in question for multihop intersection.\n"
        ans += "Try phrasing as: 'Papers using [EntityA] and [EntityB]'"
        evidence = [{"paper_id": "DATA_BASIS", "title": "entities.csv", "year": "N/A",
                     "anchor": "index", "snippet": "No entity terms matched from question."}]
        return ans, evidence, ["Entity names must appear verbatim in the question."]

    # Build intersection of paper_id sets
    paper_sets = []
    for entity in matched[:3]:  # cap at 3 conditions
        pids = set(df_ent[df_ent["entity"].str.lower() == entity.lower()]["paper_id"].dropna())
        paper_sets.append((entity, pids))

    if paper_sets:
        intersection = paper_sets[0][1]
        for _, s in paper_sets[1:]:
            intersection &= s
    else:
        intersection = set(df_ent["paper_id"].dropna())

    # Year filter
    if year_filter:
        meta = ctx.get("paper_meta", {})
        intersection = {p for p in intersection
                        if str(meta.get(p, {}).get("year", "")) == str(year_filter)}

    intersection = sorted(intersection)
    meta = ctx.get("paper_meta", {})
    conditions = [e for e, _ in paper_sets]
    if year_filter:
        conditions.append(f"year={year_filter}")

    if not intersection:
        ans = f"No papers found matching all conditions: {', '.join(conditions)}"
    else:
        ans = f"Papers matching all conditions ({', '.join(conditions)}):\n"
        for pid in intersection[:20]:
            m = meta.get(pid, {})
            ans += f"  {pid} — {m.get('title', pid)[:70]}\n"
        if len(intersection) > 20:
            ans += f"  ... and {len(intersection) - 20} more."

    evidence_rows = [{"paper_id": p} for p in intersection[:5]]
    evidence = collect_evidence(evidence_rows, ctx["data_dir"], paper_meta=meta)
    if not evidence:
        evidence = [{"paper_id": "DATA_BASIS", "title": "entities.csv", "year": "N/A",
                     "anchor": "index", "snippet": f"Intersection of {len(paper_sets)} entity condition(s)."}]
    return ans, evidence, ["Entity matching is string-based; acronym variants may be missed."]


def answer_negation(question, route, ctx):
    df_reg = ctx["dfs"].get("extraction_registry")
    df_sect = ctx["dfs"].get("paper_section_stats")
    df_ent = ctx["dfs"].get("entities")

    q = question.lower()
    all_pids = set(df_reg["paper_id"].dropna()) if df_reg is not None else set()
    evidence = []

    # --- Entity-specific absence ---
    if df_ent is not None:
        all_entities = df_ent["entity"].dropna().unique()
        matched = [e for e in all_entities if str(e).lower() in q and len(str(e)) > 2]
        if matched:
            entity = matched[0]
            papers_with_entity = set(df_ent[df_ent["entity"].str.lower() == entity.lower()]["paper_id"].dropna())
            papers_without = sorted(all_pids - papers_with_entity)
            ans = f"Papers with no mention of '{entity}':\n"
            ans += f"  Count: {len(papers_without)}\n"
            ans += f"  Sample: {', '.join(papers_without[:15])}"
            evidence = [{"paper_id": "DATA_BASIS", "title": "entities.csv", "year": "N/A",
                         "anchor": "negation", "snippet": f"Set difference: all_papers minus papers mentioning '{entity}'."}]
            return ans, evidence, ["Entity matching is string-based; partial name variants may affect results."]

    # --- Section-based absence ---
    if df_reg is None or df_sect is None:
        return "Missing registry or section stats data.", [], ["extraction_registry.csv or paper_section_stats.csv missing"]

    if "abstract" in q:
        no_abs = df_sect[df_sect["has_abstract"] == False]["paper_id"].tolist() if "has_abstract" in df_sect.columns else []
        ans = f"Papers missing an abstract section: {len(no_abs)}\n  {', '.join(no_abs[:15])}"
    elif "method" in q:
        no_method = df_sect[df_sect["has_method"] == False]["paper_id"].tolist() if "has_method" in df_sect.columns else []
        ans = f"Papers missing a method section: {len(no_method)}\n  {', '.join(no_method[:15])}"
    elif "result" in q or "tuple" in q:
        missing_results = df_reg[df_reg["result_tuple_count"] == 0]["paper_id"].tolist()
        ans = f"Papers with no extracted result tuples: {len(missing_results)}\n  {', '.join(missing_results[:15])}"
    elif "entit" in q:
        no_ent = df_reg[df_reg["entity_count"] == 0]["paper_id"].tolist() if "entity_count" in df_reg.columns else []
        ans = f"Papers with no extracted entities: {len(no_ent)}\n  {', '.join(no_ent[:15])}"
    else:
        missing_results = df_reg[df_reg["result_tuple_count"] == 0]["paper_id"].tolist()
        ans = f"Papers with no extracted result tuples: {len(missing_results)}\n  Sample: {', '.join(missing_results[:10])}"

    evidence = [{"paper_id": "DATA_BASIS", "title": "paper_section_stats.csv",
                 "year": "N/A", "anchor": "negation", "snippet": "Gap analysis via section presence flags."}]
    return ans, evidence, ["Section detection is heuristic; a missing flag may reflect parser failure, not true absence."]


def answer_quantitative(question, route, ctx):
    df_sum = ctx["dfs"].get("paper_entity_summary")
    df_res = ctx["dfs"].get("result_tuples")
    df_ent = ctx["dfs"].get("entities")
    df_sect = ctx["dfs"].get("paper_section_stats")
    df_reg = ctx["dfs"].get("extraction_registry")

    if df_sum is None:
        return "Missing summary data.", [], ["paper_entity_summary.csv missing"]

    q = question.lower()
    paper_count = len(df_sum)
    result_count = len(df_res) if df_res is not None else 0

    # --- Entity-specific count ---
    if df_ent is not None:
        all_entities = df_ent["entity"].dropna().unique()
        matched = [e for e in all_entities if str(e).lower() in q and len(str(e)) > 2]
        if matched:
            entity = matched[0]
            papers_with = df_ent[df_ent["entity"].str.lower() == entity.lower()]["paper_id"].nunique()
            ans = f"Papers mentioning '{entity}': {papers_with} out of {paper_count} corpus papers."
            evidence = [{"paper_id": "DATA_BASIS", "title": "entities.csv", "year": "N/A",
                         "anchor": "count", "snippet": f"Distinct paper_id count for entity='{entity}'."}]
            return ans, evidence, []

    # --- Percentage questions ---
    if "percent" in q or "%" in q:
        if "method" in q and df_sect is not None and "has_method" in df_sect.columns:
            pct = 100 * df_sect["has_method"].mean()
            ans = f"Percentage of papers with a method section: {pct:.1f}%"
        elif "result" in q and df_reg is not None and "result_tuple_count" in df_reg.columns:
            has_results = (df_reg["result_tuple_count"] > 0).sum()
            pct = 100 * has_results / len(df_reg)
            ans = f"Percentage of papers with at least one result tuple: {pct:.1f}%"
        else:
            ans = f"Corpus coverage: {paper_count} papers extracted out of 100 in manifest."
        evidence = [{"paper_id": "DATA_BASIS", "title": "paper_section_stats.csv",
                     "year": "N/A", "anchor": "percent", "snippet": "Percentage computed from section/registry flags."}]
        return ans, evidence, []

    # --- Median/average sections ---
    if ("median" in q or "average" in q or "mean" in q) and "section" in q:
        if df_sect is not None and "total_sections" in df_sect.columns:
            med = df_sect["total_sections"].median()
            avg = df_sect["total_sections"].mean()
            ans = f"Sections per paper — Median: {med:.1f}, Average: {avg:.1f}"
        else:
            ans = "Section stats not available."
        evidence = [{"paper_id": "DATA_BASIS", "title": "paper_section_stats.csv",
                     "year": "N/A", "anchor": "median", "snippet": "Computed from total_sections column."}]
        return ans, evidence, []

    # --- Average results per paper ---
    if "average" in q or "mean" in q:
        avg = result_count / paper_count if paper_count else 0
        ans = f"Average result tuples per paper: {avg:.1f} (across {paper_count} papers, {result_count} total tuples)"
        evidence = [{"paper_id": "DATA_BASIS", "title": "result_tuples.csv",
                     "year": "N/A", "anchor": "average", "snippet": "Mean computed from extraction_registry."}]
        return ans, evidence, []

    # --- Total entity count ---
    if "total" in q and "entit" in q and df_reg is not None and "entity_count" in df_reg.columns:
        total_ent = int(df_reg["entity_count"].sum())
        ans = f"Total entities extracted across corpus: {total_ent:,}"
        evidence = [{"paper_id": "DATA_BASIS", "title": "extraction_registry.csv",
                     "year": "N/A", "anchor": "total", "snippet": f"Sum of entity_count: {total_ent}."}]
        return ans, evidence, []

    # --- Generic fallback ---
    ans = f"Quantitative Corpus Summary:\n"
    ans += f"- Total papers with extraction: {paper_count}\n"
    ans += f"- Total result tuples: {result_count}\n"
    ans += f"- Avg results per paper: {result_count/paper_count:.1f}\n"
    if df_ent is not None:
        ans += f"- Total entity mentions: {len(df_ent):,}"
    evidence = [{"paper_id": "DATA_BASIS", "title": "paper_entity_summary.csv",
                 "year": "N/A", "anchor": "summary",
                 "snippet": f"Numeric aggregation over {paper_count} papers."}]
    return ans, evidence, []
