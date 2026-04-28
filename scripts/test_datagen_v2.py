"""
Data Gen Comparison: Current vs Improved
Tests formula fix + post-gen sanity checks. Same inputs, compare quality.
Cell 1: %pip install openai numpy | Cell 2: dbutils.library.restartPython() | Cell 3: paste this
"""

# === CONFIG ===
COMPANY_NAME = "First National Bank"
COMPANY_DESCRIPTION = "Regional community bank in southeastern US with 45 branches. Personal/business banking, mortgages, auto loans, wealth management. ~200K customers."
MUST_ANSWER_QUESTIONS = [
    "What is the total loan portfolio value by loan type?",
    "Which branch has the highest deposit growth this year?",
    "What is the average interest rate by loan category?",
    "How many new accounts were opened per month?",
    "Which region has the highest default rate?",
]
DATABRICKS_HOST_ID = "7474655921234161"
LLM_MODEL = "opendoor-claude-opus-46"

import json, re, time, random, datetime, copy
import numpy as np
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
token = ctx.apiToken().get()
client = OpenAI(api_key=token, base_url=f"https://{DATABRICKS_HOST_ID}.ai-gateway.cloud.databricks.com/mlflow/v1")
questions_text = "\n".join(f"- {q}" for q in MUST_ANSWER_QUESTIONS)

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


# ============================================================
# SHARED: Schema Design + Spec Generation (one call, reused by both methods)
# ============================================================
print("=" * 70)
print("SHARED: Schema + Spec Generation")
print("=" * 70)

SCHEMA_PROMPT = (
    "You are a data architect. Design a database schema.\n"
    "Output ONLY valid JSON, no markdown.\n\n"
    "RULES:\n"
    "1. Create 3-4 tables. 5-10 cols each, snake_case.\n"
    "2. First col = PK (sequential int). Use FKs (references: table.column).\n"
    "3. Every table: at least one DATE + one numeric column.\n"
    "4. Column comments are CRITICAL. Tables ordered: referenced BEFORE referencing.\n"
    "5. Must answer ALL must-answer questions via SQL.\n"
    "6. Dimension: 15-25 rows. Fact: 200-400 rows.\n\n"
    "SQL TYPES: STRING, INT, DOUBLE, DATE, BOOLEAN, BIGINT\n\n"
    "OUTPUT: JSON with tables array + sample_questions.\n"
    "Each table: name, comment, row_count, table_type, columns.\n"
    "Each column: name, type, comment, primary_key, references."
)

SPEC_PROMPT = (
    "You are a data engineer designing a data generation specification.\n"
    "Output ONLY valid JSON, no markdown.\n\n"
    "For EACH column, provide {dist: TYPE, ...params}. Valid types:\n"
    "  sequential: {start:1}\n"
    "  fk_sample: {from_table:'X', from_column:'Y'}\n"
    "  weighted_choice: {values:['A','B'], weights:[0.6,0.4]}\n"
    "  uniform_int: {min:1, max:100}\n"
    "  uniform_float: {min:0.0, max:1000.0, decimals:2}\n"
    "  normal: {mean:50000, std:15000, min:20000, max:200000, decimals:2}\n"
    "  date_range: {start:'2023-01-01', end:'2025-04-28'}\n"
    "  boolean: {true_pct:0.7}\n"
    "  formula: {expr:'col_a * 0.85'} — for derived columns\n\n"
    "RULES:\n"
    "- Use formula for correlated columns (outstanding_balance from principal, maturity from origination)\n"
    "- Use normal for continuous numerics, weighted_choice ONLY for categorical\n"
    "- Dimension tables: all rows as fixtures (max 25). Fact: max 10 fixtures.\n"
    "- Every column MUST be in the columns dict.\n\n"
    "OUTPUT: {columns: {...}, fixtures: [...]}"
)

t0 = time.time()
schema = parse_json(call_llm(SCHEMA_PROMPT,
    f"Company: {COMPANY_NAME}\nDescription: {COMPANY_DESCRIPTION}\n\nMUST-ANSWER:\n{questions_text}\n\nDesign."))
t_schema = time.time() - t0
print(f"Schema: {t_schema:.1f}s | {len(schema['tables'])} tables")

# Generate specs
def get_deps(td):
    return {c.get("references","").split(".")[0] for c in td.get("columns",[]) if c.get("references")}

def gen_spec(td, parents):
    cols = "\n".join(
        f"- {c['name']} ({c.get('type','STRING')}){': '+c['comment'] if c.get('comment') else ''}"
        f"{' [PK]' if c.get('primary_key') else ''}{' [FK->'+c['references']+']' if c.get('references') else ''}"
        for c in td["columns"])
    fks = "\n".join(
        f"Available {c['name']}: {list(set(str(r.get(c['references'].split('.')[1] if '.' in c['references'] else c['references']+'_id')) for r in parents.get(c['references'].split('.')[0] if '.' in c['references'] else c['references'],[]) if r.get(c['references'].split('.')[1] if '.' in c['references'] else c['references']+'_id') is not None))[:30]}"
        for c in td["columns"] if c.get("references"))
    for attempt in range(3):
        try:
            return parse_json(call_llm(SPEC_PROMPT,
                f"Company: {COMPANY_NAME}\nTable: \"{td['name']}\" — {td.get('comment','')}\n"
                f"Rows: {td.get('row_count',100)} | Type: {td.get('table_type','fact')}\n\nCols:\n{cols}\n{fks}\n\nQuestions:\n{questions_text}"))
        except: pass
    return {"columns": {}, "fixtures": []}

tbn = {t["name"]: t for t in schema["tables"]}
levels, resolved, rem = [], set(), set(tbn.keys())
while rem:
    cur = [n for n in rem if get_deps(tbn[n]).issubset(resolved)]
    if not cur: cur = list(rem)
    levels.append(cur); resolved.update(cur); rem -= set(cur)

t0 = time.time()
specs, parent_data_for_specs = {}, {}
for li, lns in enumerate(levels):
    if len(lns) > 1:
        def _g(n): return n, gen_spec(tbn[n], parent_data_for_specs)
        with ThreadPoolExecutor(max_workers=4) as ex:
            for f in as_completed({ex.submit(_g, n): n for n in lns}):
                n, sp = f.result(); specs[n] = sp
    else:
        for n in lns: specs[n] = gen_spec(tbn[n], parent_data_for_specs)
    # Need to generate data for this level so next level has FK values
    for n in lns:
        # Quick generation just for FK references (Method A generator)
        sp = specs[n]
        fixtures = sp.get("fixtures", [])
        parent_data_for_specs[n] = fixtures  # Use fixtures as parent data for now

t_specs = time.time() - t0
print(f"Specs: {t_specs:.1f}s")
for n, sp in specs.items():
    print(f"  {n}: {len(sp.get('columns',{}))} col specs, {len(sp.get('fixtures',[]))} fixtures")


# ============================================================
# METHOD A: Current (basic row generator)
# ============================================================
print("\n" + "=" * 70)
print("METHOD A: Current Row Generator")
print("=" * 70)

def gen_rows_current(spec, row_count, parents):
    columns = spec.get("columns", {})
    fixtures = spec.get("fixtures", [])
    rows = list(fixtures)
    start_id = len(rows) + 1
    for i in range(max(0, row_count - len(rows))):
        row = {}
        for cn, cs in columns.items():
            if not isinstance(cs, dict): row[cn] = cs; continue
            dist = cs.get("dist", cs.get("type", ""))
            try:
                if dist == "sequential": row[cn] = cs.get("start",1) + len(fixtures) + i
                elif dist == "fk_sample":
                    p = parents.get(cs.get("from_table",""), [])
                    ids = [r.get(cs.get("from_column","")) for r in p if r.get(cs.get("from_column","")) is not None]
                    row[cn] = random.choice(ids) if ids else random.randint(1,10)
                elif dist == "weighted_choice":
                    v,w = cs.get("values",["A"]), cs.get("weights",[])
                    if not w or len(w)!=len(v): w = [1/len(v)]*len(v)
                    t = sum(w); row[cn] = random.choices(v, weights=[x/t for x in w], k=1)[0]
                elif dist == "uniform_int": row[cn] = random.randint(int(cs.get("min",0)), int(cs.get("max",100)))
                elif dist in ("uniform_float","uniform_double"):
                    row[cn] = round(random.uniform(float(cs.get("min",0)), float(cs.get("max",1000))), int(cs.get("decimals",2)))
                elif dist in ("normal","gaussian"):
                    v = np.random.normal(float(cs.get("mean",50)), float(cs.get("std",10)))
                    v = max(float(cs.get("min",0)), min(float(cs.get("max",1e9)), v))
                    row[cn] = round(float(v), int(cs.get("decimals",2)))
                elif dist == "date_range":
                    s = datetime.date.fromisoformat(str(cs.get("start","2023-01-01")))
                    e = datetime.date.fromisoformat(str(cs.get("end","2025-04-28")))
                    row[cn] = (s + datetime.timedelta(days=random.randint(0, max((e-s).days,1)))).isoformat()
                elif dist == "boolean": row[cn] = random.random() < float(cs.get("true_pct",0.5))
                elif dist == "formula":
                    try: row[cn] = round(eval(str(cs.get("expr","0")), {"__builtins__":{}}, row), 2)
                    except: row[cn] = 0
                else:
                    if "values" in cs: row[cn] = random.choice(cs["values"])
                    elif "min" in cs and "max" in cs: row[cn] = round(random.uniform(float(cs["min"]),float(cs["max"])),2)
                    else: row[cn] = None
            except: row[cn] = None
        rows.append(row)
    return rows[:row_count]

t0 = time.time()
data_a = {}
for td in schema["tables"]:
    n = td["name"]
    data_a[n] = gen_rows_current(specs[n], td.get("row_count",100), data_a)
t_a = time.time() - t0
print(f"Generated in {t_a:.3f}s")
for n, rows in data_a.items():
    nf = len(specs[n].get("fixtures",[]))
    print(f"  {n}: {len(rows)} rows ({nf} fix + {len(rows)-nf} gen)")


# ============================================================
# METHOD B: Improved (two-pass formula + sanity checks)
# ============================================================
print("\n" + "=" * 70)
print("METHOD B: Improved Row Generator (formula fix + sanity)")
print("=" * 70)

def gen_rows_improved(spec, row_count, parents, table_def):
    columns = spec.get("columns", {})
    fixtures = spec.get("fixtures", [])
    rows = list(fixtures)
    start_id = len(rows) + 1

    # Split columns into regular + formula (formula computed in second pass)
    regular_cols = {cn: cs for cn, cs in columns.items() if isinstance(cs, dict) and cs.get("dist") != "formula"}
    formula_cols = {cn: cs for cn, cs in columns.items() if isinstance(cs, dict) and cs.get("dist") == "formula"}

    for i in range(max(0, row_count - len(rows))):
        row = {}

        # PASS 1: Generate all non-formula columns
        for cn, cs in regular_cols.items():
            dist = cs.get("dist", cs.get("type", ""))
            try:
                if dist == "sequential": row[cn] = cs.get("start",1) + len(fixtures) + i
                elif dist == "fk_sample":
                    p = parents.get(cs.get("from_table",""), [])
                    ids = [r.get(cs.get("from_column","")) for r in p if r.get(cs.get("from_column","")) is not None]
                    row[cn] = random.choice(ids) if ids else random.randint(1,10)
                elif dist == "weighted_choice":
                    v,w = cs.get("values",["A"]), cs.get("weights",[])
                    if not w or len(w)!=len(v): w = [1/len(v)]*len(v)
                    t = sum(w); row[cn] = random.choices(v, weights=[x/t for x in w], k=1)[0]
                elif dist == "uniform_int": row[cn] = random.randint(int(cs.get("min",0)), int(cs.get("max",100)))
                elif dist in ("uniform_float","uniform_double"):
                    row[cn] = round(random.uniform(float(cs.get("min",0)), float(cs.get("max",1000))), int(cs.get("decimals",2)))
                elif dist in ("normal","gaussian"):
                    v = np.random.normal(float(cs.get("mean",50)), float(cs.get("std",10)))
                    v = max(float(cs.get("min",0)), min(float(cs.get("max",1e9)), v))
                    row[cn] = round(float(v), int(cs.get("decimals",2)))
                elif dist == "date_range":
                    s = datetime.date.fromisoformat(str(cs.get("start","2023-01-01")))
                    e = datetime.date.fromisoformat(str(cs.get("end","2025-04-28")))
                    row[cn] = (s + datetime.timedelta(days=random.randint(0, max((e-s).days,1)))).isoformat()
                elif dist == "boolean": row[cn] = random.random() < float(cs.get("true_pct",0.5))
                else:
                    if "values" in cs: row[cn] = random.choice(cs["values"])
                    elif "min" in cs and "max" in cs: row[cn] = round(random.uniform(float(cs["min"]),float(cs["max"])),2)
                    else: row[cn] = None
            except: row[cn] = None

        # PASS 2: Compute formula columns (now all dependencies are available)
        for cn, cs in formula_cols.items():
            expr = str(cs.get("expr", "0"))
            try:
                # Build a safe eval context with the row's values + math helpers
                ctx = {"__builtins__": {}, "round": round, "max": max, "min": min, "abs": abs, "int": int, "float": float}
                ctx.update(row)
                val = eval(expr, ctx)
                row[cn] = round(val, 2) if isinstance(val, float) else val
            except Exception as e:
                # Fallback: if formula references another column, try percentage of it
                for other_cn, other_val in row.items():
                    if other_cn in expr and isinstance(other_val, (int, float)) and other_val > 0:
                        row[cn] = round(other_val * random.uniform(0.5, 0.95), 2)
                        break
                else:
                    row[cn] = 0

        rows.append(row)

    # PASS 3: Post-generation sanity checks
    col_names = [c["name"] for c in table_def.get("columns", [])]
    fixes = 0
    for row in rows[len(fixtures):]:  # Only check generated rows, not fixtures
        # outstanding_balance should be <= principal/original amount
        for bal_col in ["outstanding_balance", "remaining_balance"]:
            for prin_col in ["principal_amount", "original_amount", "loan_amount"]:
                if bal_col in row and prin_col in row:
                    if isinstance(row[bal_col], (int,float)) and isinstance(row[prin_col], (int,float)):
                        if row[bal_col] > row[prin_col]:
                            row[bal_col] = round(row[prin_col] * random.uniform(0.3, 0.95), 2)
                            fixes += 1

        # selling_price should be > dealer_cost
        if "selling_price" in row and "dealer_cost_at_sale" in row:
            sp, dc = row["selling_price"], row["dealer_cost_at_sale"]
            if isinstance(sp,(int,float)) and isinstance(dc,(int,float)) and sp < dc:
                row["selling_price"] = round(dc * random.uniform(1.02, 1.25), 2)
                fixes += 1

        # gross_profit should match selling_price - cost
        if "gross_profit" in row and "selling_price" in row and "dealer_cost_at_sale" in row:
            sp, dc = row["selling_price"], row["dealer_cost_at_sale"]
            if isinstance(sp,(int,float)) and isinstance(dc,(int,float)):
                row["gross_profit"] = round(sp - dc, 2)

        # collected_amount should be <= charge_amount
        if "collected_amount" in row and "charge_amount" in row:
            ca, ch = row["collected_amount"], row["charge_amount"]
            if isinstance(ca,(int,float)) and isinstance(ch,(int,float)) and ca > ch:
                row["collected_amount"] = round(ch * random.uniform(0.5, 0.95), 2)
                fixes += 1

        # maturity_date should be after origination_date
        if "maturity_date" in row and "origination_date" in row:
            mat, orig = row.get("maturity_date"), row.get("origination_date")
            if isinstance(mat, str) and isinstance(orig, str) and mat <= orig:
                try:
                    orig_d = datetime.date.fromisoformat(orig[:10])
                    term = row.get("term_months", 60)
                    if not isinstance(term, (int,float)): term = 60
                    row["maturity_date"] = (orig_d + datetime.timedelta(days=int(term)*30)).isoformat()
                    fixes += 1
                except: pass

            # Fix maturity_date = 0 (formula failure)
            if row.get("maturity_date") in (0, "0", None):
                try:
                    orig_d = datetime.date.fromisoformat(str(row.get("origination_date","2024-01-01"))[:10])
                    term = row.get("term_months", 60)
                    if not isinstance(term, (int,float)): term = 60
                    row["maturity_date"] = (orig_d + datetime.timedelta(days=int(term)*30)).isoformat()
                    fixes += 1
                except: pass

    if fixes > 0:
        print(f"    Sanity fixes applied: {fixes}")

    return rows[:row_count]

t0 = time.time()
data_b = {}
for td in schema["tables"]:
    n = td["name"]
    data_b[n] = gen_rows_improved(specs[n], td.get("row_count",100), data_b, td)
t_b = time.time() - t0
print(f"Generated in {t_b:.3f}s")
for n, rows in data_b.items():
    nf = len(specs[n].get("fixtures",[]))
    print(f"  {n}: {len(rows)} rows ({nf} fix + {len(rows)-nf} gen)")


# ============================================================
# COMPARISON
# ============================================================
print("\n" + "=" * 70)
print("COMPARISON: Method A (current) vs Method B (improved)")
print("=" * 70)

for table_name in data_a:
    a_rows = data_a[table_name]
    b_rows = data_b[table_name]
    nf = len(specs[table_name].get("fixtures",[]))

    a_gen = a_rows[nf:]
    b_gen = b_rows[nf:]

    if not a_gen and not b_gen:
        print(f"\n  {table_name}: ALL FIXTURES (same in both)")
        continue

    print(f"\n  --- {table_name} ({len(a_gen)} gen rows) ---")

    cols = list(a_gen[0].keys()) if a_gen else list(b_gen[0].keys()) if b_gen else []

    for col in cols:
        a_vals = [r.get(col) for r in a_gen if r.get(col) is not None]
        b_vals = [r.get(col) for r in b_gen if r.get(col) is not None]

        a_nulls = len(a_gen) - len(a_vals)
        b_nulls = len(b_gen) - len(b_vals)

        # Check for zeros and formula failures
        a_zeros = sum(1 for v in a_vals if v in (0, 0.0, "0"))
        b_zeros = sum(1 for v in b_vals if v in (0, 0.0, "0"))

        # Numeric comparison
        try:
            a_nums = [float(v) for v in a_vals if v not in (None, "")]
            b_nums = [float(v) for v in b_vals if v not in (None, "")]
            if a_nums and b_nums:
                a_bad = a_nulls + a_zeros
                b_bad = b_nulls + b_zeros
                flag = ""
                if a_bad > 0 or b_bad > 0:
                    flag = f" {'<< A has issues' if a_bad > b_bad else '<< B has issues' if b_bad > a_bad else ''}"
                if a_bad > 0 or b_bad > 0 or abs(np.mean(a_nums) - np.mean(b_nums)) > np.mean(a_nums) * 0.5:
                    print(f"    {col}:")
                    print(f"      A: avg={np.mean(a_nums):.1f}, nulls={a_nulls}, zeros={a_zeros}")
                    print(f"      B: avg={np.mean(b_nums):.1f}, nulls={b_nulls}, zeros={b_zeros}{flag}")
                continue
        except: pass

    # Show one sample side by side
    if a_gen and b_gen:
        print(f"    Sample A: {a_gen[0]}")
        print(f"    Sample B: {b_gen[0]}")


# ============================================================
# VERDICT
# ============================================================
print("\n" + "=" * 70)
print("VERDICT")
print("=" * 70)

total_a_issues = 0
total_b_issues = 0
for table_name in data_a:
    nf = len(specs[table_name].get("fixtures",[]))
    for label, data in [("A", data_a), ("B", data_b)]:
        gen = data[table_name][nf:]
        for row in gen:
            for col, val in row.items():
                if val in (0, 0.0, "0", None):
                    if label == "A": total_a_issues += 1
                    else: total_b_issues += 1

print(f"  Method A (current):  {total_a_issues} zero/null values in generated rows")
print(f"  Method B (improved): {total_b_issues} zero/null values in generated rows")
print(f"  Generation time: A={t_a:.3f}s vs B={t_b:.3f}s (both instant)")

if total_b_issues < total_a_issues:
    print(f"\n  >> Method B wins: {total_a_issues - total_b_issues} fewer issues")
elif total_b_issues == total_a_issues:
    print(f"\n  >> TIE: Same quality. Method B has sanity checks as safety net.")
else:
    print(f"\n  >> Method A wins (unexpected). Check sanity check logic.")
print("=" * 70)
