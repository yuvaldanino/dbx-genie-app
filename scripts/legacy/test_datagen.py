"""
Data Generation Test Script v2 — Multi-company test with refined prompts.
Run in a Databricks notebook. Cell 1: %pip install openai numpy, Cell 2: dbutils.library.restartPython(), Cell 3: paste this.
"""

# === TEST COMPANIES ===
TEST_COMPANIES = [
    {
        "name": "First National Bank",
        "description": "Regional community bank in the southeastern US with 45 branches. Personal/business banking, mortgages, auto loans, wealth management. ~200K customers.",
        "questions": [
            "What is the total loan portfolio value by loan type?",
            "Which branch has the highest deposit growth this year?",
            "What is the average interest rate by loan category?",
            "How many new accounts were opened per month?",
            "Which region has the highest default rate?",
        ],
    },
    {
        "name": "CloudPeak SaaS",
        "description": "B2B SaaS company selling project management and CRM tools. 5,000 enterprise customers globally. Subscription-based with monthly and annual plans across 3 tiers.",
        "questions": [
            "What is the monthly recurring revenue by plan tier?",
            "Which industry vertical has the highest churn rate?",
            "What is the average deal size by sales region?",
            "How many new subscriptions were added per quarter?",
            "What is the net revenue retention rate?",
        ],
    },
    {
        "name": "FreshHarvest Grocers",
        "description": "Regional grocery chain with 120 stores across the Midwest. Sells fresh produce, dairy, bakery, meat, packaged goods, and household items. Loyalty program with 500K members.",
        "questions": [
            "What are the top 10 selling product categories by revenue?",
            "Which store location has the highest average basket size?",
            "What is the monthly sales trend for organic products?",
            "How does loyalty member spending compare to non-members?",
            "Which department has the highest profit margin?",
        ],
    },
    {
        "name": "MedFirst Urgent Care",
        "description": "Chain of 30 urgent care clinics across Texas. Treats walk-in patients for non-emergency conditions. Accepts insurance and self-pay. Average 150 visits per clinic per day.",
        "questions": [
            "What is the average wait time by clinic location?",
            "Which diagnosis codes are most common by season?",
            "What is the revenue breakdown by payment type?",
            "How many patient visits per month by clinic?",
            "What is the patient satisfaction score by provider?",
        ],
    },
    {
        "name": "AutoElite Dealerships",
        "description": "Luxury car dealership group with 15 locations in California. Sells new and certified pre-owned vehicles from BMW, Mercedes, Audi, and Porsche. Also provides service and parts.",
        "questions": [
            "What is the total sales revenue by vehicle brand?",
            "Which dealership has the highest service department revenue?",
            "What is the average selling price vs MSRP by model?",
            "How many vehicles were sold per month by type?",
            "What is the gross profit margin by dealership?",
        ],
    },
]

# === CONFIG ===
DATABRICKS_HOST_ID = "7474655921234161"
LLM_MODEL = "opendoor-claude-opus-46"

# How many companies to test (change to len(TEST_COMPANIES) for all)
NUM_TO_TEST = 2  # Start with 2, increase when confident

# === SETUP ===
import json, re, time, random, datetime
import numpy as np
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
token = ctx.apiToken().get()
client = OpenAI(api_key=token, base_url=f"https://{DATABRICKS_HOST_ID}.ai-gateway.cloud.databricks.com/mlflow/v1")

def call_llm(system, user, max_tokens=8192):
    r = client.chat.completions.create(model=LLM_MODEL, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return r.choices[0].message.content.strip()

def parse_json(raw):
    if raw.startswith("```"): raw = raw.split("\n", 1)[1]
    if raw.endswith("```"): raw = raw[:raw.rfind("```")]
    for sc, ec in [("{", "}"), ("[", "]")]:
        s, e = raw.find(sc), raw.rfind(ec) + 1
        if s >= 0 and e > s:
            c = re.sub(r",\s*([}\]])", r"\1", raw[s:e])
            try: return json.loads(c)
            except: continue
    return json.loads(raw)


# === PROMPTS ===

SCHEMA_PROMPT = (
    "You are a data architect. Design a database schema for the given company.\n"
    "Output ONLY valid JSON, no markdown fences.\n\n"
    "RULES:\n"
    "1. Create 3-4 tables representing core business entities.\n"
    "2. Each table: 5-10 columns, snake_case names.\n"
    "3. First column = primary key (sequential integer).\n"
    "4. Use FKs to link tables. Set references to 'table.column'.\n"
    "5. Every table needs at least one DATE and one numeric column.\n"
    "6. Column comments are CRITICAL — they go to the AI query engine.\n"
    "7. Tables ordered: referenced BEFORE referencing.\n"
    "8. Design tables that can answer ALL must-answer questions via SQL.\n"
    "9. Dimension tables: 15-25 rows. Fact tables: 200-400 rows.\n\n"
    "SQL TYPES: STRING, INT, DOUBLE, DATE, BOOLEAN, BIGINT\n\n"
    "OUTPUT: JSON with 'tables' array and 'sample_questions' array.\n"
    "Each table: name, comment, row_count, table_type (dimension/fact), columns array.\n"
    "Each column: name, type, comment, primary_key (bool), references ('' or table.column)."
)

SPEC_PROMPT = (
    "You are a data engineer designing a data generation specification.\n"
    "Output ONLY valid JSON, no markdown fences.\n\n"
    "For EACH column, provide a distribution spec with a 'dist' field set to one of:\n"
    "  sequential: {dist:'sequential', start:1} — for primary keys\n"
    "  fk_sample: {dist:'fk_sample', from_table:'X', from_column:'Y'} — picks from parent\n"
    "  weighted_choice: {dist:'weighted_choice', values:['A','B'], weights:[0.6,0.4]} — categorical\n"
    "  uniform_int: {dist:'uniform_int', min:1, max:100}\n"
    "  uniform_float: {dist:'uniform_float', min:0.0, max:1000.0, decimals:2}\n"
    "  normal: {dist:'normal', mean:50000, std:15000, min:20000, max:200000, decimals:2}\n"
    "  date_range: {dist:'date_range', start:'2023-01-01', end:'2025-04-28'}\n"
    "  boolean: {dist:'boolean', true_pct:0.7}\n"
    "  formula: {dist:'formula', expr:'principal_amount * 0.85'} — derived from other cols\n\n"
    "CRITICAL RULES:\n"
    "- Use 'formula' for columns that should correlate with others (e.g., outstanding_balance = principal * random factor, maturity_date = origination_date + term)\n"
    "- Use 'normal' (not 'weighted_choice') for continuous numeric columns like prices, amounts, salaries\n"
    "- Use 'weighted_choice' ONLY for categorical/discrete values with domain-specific options\n"
    "- weighted_choice values must be REAL domain data (real city names, real product names)\n"
    "- Every column MUST appear in the columns dict with a valid dist\n"
    "- Dimension tables: ALL rows as fixtures (max 25). Fact tables: max 10 fixtures + distributions\n"
    "- Fixtures must cover key data points needed to answer the must-answer questions\n\n"
    "OUTPUT: {columns: {col: {dist:..., ...}}, fixtures: [{...}]}"
)


# === ROW GENERATOR ===

def generate_rows(spec, row_count, parent_tables):
    columns = spec.get("columns", {})
    fixtures = spec.get("fixtures", [])
    rows = list(fixtures)
    remaining = max(0, row_count - len(rows))
    start_id = len(rows) + 1

    for i in range(remaining):
        row = {}
        for col_name, cs in columns.items():
            if not isinstance(cs, dict):
                row[col_name] = cs
                continue
            dist = cs.get("dist", cs.get("type", ""))
            try:
                if dist == "sequential":
                    row[col_name] = cs.get("start", 1) + len(fixtures) + i
                elif dist == "fk_sample":
                    parent = parent_tables.get(cs.get("from_table", ""), [])
                    ids = [r.get(cs.get("from_column", "")) for r in parent if r.get(cs.get("from_column", "")) is not None]
                    row[col_name] = random.choice(ids) if ids else random.randint(1, 10)
                elif dist == "weighted_choice":
                    vals = cs.get("values", cs.get("choices", ["A"]))
                    wts = cs.get("weights", [1.0/len(vals)] * len(vals))
                    if len(wts) != len(vals): wts = [1.0/len(vals)] * len(vals)
                    total = sum(wts)
                    row[col_name] = random.choices(vals, weights=[w/total for w in wts], k=1)[0]
                elif dist == "uniform_int":
                    row[col_name] = random.randint(int(cs.get("min", 0)), int(cs.get("max", 100)))
                elif dist in ("uniform_float", "uniform_double"):
                    row[col_name] = round(random.uniform(float(cs.get("min", 0)), float(cs.get("max", 1000))), int(cs.get("decimals", 2)))
                elif dist in ("normal", "gaussian"):
                    v = np.random.normal(float(cs.get("mean", 50)), float(cs.get("std", cs.get("stddev", 10))))
                    v = max(float(cs.get("min", 0)), min(float(cs.get("max", 1e9)), v))
                    row[col_name] = round(float(v), int(cs.get("decimals", 2)))
                elif dist == "date_range":
                    s = datetime.date.fromisoformat(str(cs.get("start", "2023-01-01")))
                    e = datetime.date.fromisoformat(str(cs.get("end", "2025-04-28")))
                    d = (e - s).days
                    row[col_name] = (s + datetime.timedelta(days=random.randint(0, max(d, 1)))).isoformat()
                elif dist == "boolean":
                    row[col_name] = random.random() < float(cs.get("true_pct", 0.5))
                elif dist == "formula":
                    try:
                        v = eval(str(cs.get("expr", "0")), {"__builtins__": {}, "round": round, "max": max, "min": min, "random": random.random()}, row)
                        row[col_name] = round(v, 2) if isinstance(v, float) else v
                    except: row[col_name] = 0
                elif dist in ("fixed", "constant"):
                    row[col_name] = cs.get("value", "")
                else:
                    if "values" in cs and "weights" in cs:
                        vals, wts = cs["values"], cs["weights"]
                        if len(wts) == len(vals):
                            total = sum(wts)
                            row[col_name] = random.choices(vals, weights=[w/total for w in wts], k=1)[0]
                        else:
                            row[col_name] = random.choice(vals)
                    elif "min" in cs and "max" in cs:
                        if isinstance(cs.get("min"), float) or isinstance(cs.get("max"), float):
                            row[col_name] = round(random.uniform(float(cs["min"]), float(cs["max"])), 2)
                        else:
                            row[col_name] = random.randint(int(cs["min"]), int(cs["max"]))
                    else:
                        row[col_name] = None
            except Exception as ex:
                row[col_name] = None
        rows.append(row)
    return rows[:row_count]


def get_deps(tdef):
    return {c.get("references", "").split(".")[0] for c in tdef.get("columns", []) if c.get("references")}

def gen_spec(tdef, parent_tables, company_name, company_desc, questions_text):
    name = tdef["name"]
    col_lines = []
    for c in tdef["columns"]:
        d = f"- {c['name']} ({c.get('type','STRING')})"
        if c.get("comment"): d += f": {c['comment']}"
        if c.get("primary_key"): d += " [PK]"
        if c.get("references"): d += f" [FK -> {c['references']}]"
        col_lines.append(d)
    fk_info = []
    for c in tdef["columns"]:
        ref = c.get("references", "")
        if not ref: continue
        rt = ref.split(".")[0] if "." in ref else ref
        rc = ref.split(".")[1] if "." in ref else f"{ref}_id"
        parent = parent_tables.get(rt, [])
        if parent:
            ids = list(set(str(r.get(rc)) for r in parent if r.get(rc) is not None))[:40]
            fk_info.append(f"Available {c['name']} values: {ids}")
    prompt = (
        f"Company: {company_name}\nDescription: {company_desc}\n"
        f"Table: \"{name}\" — {tdef.get('comment','')}\n"
        f"Row count: {tdef.get('row_count', 100)} | Type: {tdef.get('table_type', 'fact')}\n\n"
        f"Columns:\n" + "\n".join(col_lines) + "\n"
        + ("\n".join(fk_info) + "\n" if fk_info else "")
        + f"\nMust-answer questions:\n{questions_text}\n\nDesign the spec."
    )
    for attempt in range(3):
        try:
            return parse_json(call_llm(SPEC_PROMPT, prompt))
        except Exception as e:
            if attempt == 2:
                print(f"    [{name}] SPEC FAILED: {str(e)[:80]}")
                return {"columns": {}, "fixtures": []}
            print(f"    [{name}] Parse retry {attempt+1}")
    return {"columns": {}, "fixtures": []}


# ============================================================
# RUN TESTS
# ============================================================
all_results = []

for idx, company in enumerate(TEST_COMPANIES[:NUM_TO_TEST]):
    COMPANY_NAME = company["name"]
    COMPANY_DESC = company["description"]
    questions = company["questions"]
    questions_text = "\n".join(f"- {q}" for q in questions)

    print("\n" + "#" * 70)
    print(f"  COMPANY {idx+1}/{NUM_TO_TEST}: {COMPANY_NAME}")
    print("#" * 70)

    # Schema
    t0 = time.time()
    schema = parse_json(call_llm(SCHEMA_PROMPT,
        f"Company: {COMPANY_NAME}\nDescription: {COMPANY_DESC}\n\nMUST-ANSWER QUESTIONS:\n{questions_text}\n\nDesign the schema."))
    t_schema = time.time() - t0
    print(f"\n  Schema: {t_schema:.1f}s | {len(schema['tables'])} tables")
    for t in schema["tables"]:
        print(f"    {t['name']} ({t.get('table_type','?')}, {t.get('row_count','?')} rows)")

    # Dependency levels
    tbn = {t["name"]: t for t in schema["tables"]}
    levels, resolved, rem = [], set(), set(tbn.keys())
    while rem:
        cur = [n for n in rem if get_deps(tbn[n]).issubset(resolved)]
        if not cur: cur = list(rem)
        levels.append(cur)
        resolved.update(cur)
        rem -= set(cur)

    # Generate
    t0 = time.time()
    specs, gen_data = {}, {}
    for li, lnames in enumerate(levels):
        par = len(lnames) > 1
        print(f"\n  Level {li}: {lnames} {'(parallel)' if par else ''}")
        if not par:
            n = lnames[0]
            st = time.time()
            spec = gen_spec(tbn[n], gen_data, COMPANY_NAME, COMPANY_DESC, questions_text)
            specs[n] = spec
            nf = len(spec.get("fixtures", []))
            print(f"    [{n}] Spec {time.time()-st:.1f}s | {len(spec.get('columns',{}))} cols, {nf} fixtures")
            rows = generate_rows(spec, tbn[n].get("row_count", 100), gen_data)
            gen_data[n] = rows
            print(f"    [{n}] {len(rows)} rows")
        else:
            def _g(n):
                st = time.time()
                sp = gen_spec(tbn[n], gen_data, COMPANY_NAME, COMPANY_DESC, questions_text)
                return n, sp, time.time()-st
            with ThreadPoolExecutor(max_workers=4) as ex:
                for f in as_completed({ex.submit(_g, n): n for n in lnames}):
                    n, sp, dur = f.result()
                    specs[n] = sp
                    nf = len(sp.get("fixtures", []))
                    print(f"    [{n}] Spec {dur:.1f}s | {len(sp.get('columns',{}))} cols, {nf} fixtures")
            for n in lnames:
                rows = generate_rows(specs[n], tbn[n].get("row_count", 100), gen_data)
                gen_data[n] = rows
                print(f"    [{n}] {len(rows)} rows")

    t_data = time.time() - t0

    # Quality check
    quality_issues = []
    for name, rows in gen_data.items():
        nf = len(specs[name].get("fixtures", []))
        gen_rows = rows[nf:]
        if not gen_rows:
            continue
        for col in gen_rows[0].keys():
            nulls = sum(1 for r in gen_rows if r.get(col) in (None, ""))
            if nulls > len(gen_rows) * 0.3:
                quality_issues.append(f"{name}.{col}: {nulls}/{len(gen_rows)} null")

    result = {
        "company": COMPANY_NAME,
        "schema_time": t_schema,
        "data_time": t_data,
        "total_time": t_schema + t_data,
        "tables": {n: len(r) for n, r in gen_data.items()},
        "quality_issues": quality_issues,
    }
    all_results.append(result)

    # Sample output
    print(f"\n  --- Results for {COMPANY_NAME} ---")
    print(f"  Time: schema={t_schema:.0f}s + data={t_data:.0f}s = {t_schema+t_data:.0f}s")
    print(f"  Tables: {', '.join(f'{n}({len(r)})' for n,r in gen_data.items())}")
    if quality_issues:
        print(f"  Quality issues: {quality_issues}")
    else:
        print(f"  Quality: ALL OK")

    for name, rows in gen_data.items():
        nf = len(specs[name].get("fixtures", []))
        print(f"\n  {name} — {len(rows)} rows ({nf} fix + {len(rows)-nf} gen)")
        if rows:
            print(f"    Sample fixture: {rows[0]}")
        if len(rows) > nf:
            print(f"    Sample generated: {rows[nf]}")


# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n\n" + "=" * 70)
print("FINAL SUMMARY ACROSS ALL COMPANIES")
print("=" * 70)
for r in all_results:
    status = "OK" if not r["quality_issues"] else f"ISSUES: {len(r['quality_issues'])}"
    print(f"  {r['company']:30s} | {r['total_time']:5.0f}s | {sum(r['tables'].values()):4d} rows | {status}")

avg_time = sum(r["total_time"] for r in all_results) / len(all_results)
total_issues = sum(len(r["quality_issues"]) for r in all_results)
print(f"\n  Average time: {avg_time:.0f}s")
print(f"  Total quality issues: {total_issues}")
print("=" * 70)
