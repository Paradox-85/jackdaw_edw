# Claude Code Prompt – Phase 2 CRS Cascade Classification Implementation

**Project**: Jackdaw EDW – Phase 2 v2 (Cascade Classifier with Knowledge Base)  
**Objective**: Implement 4-tier cascade comment classifier that reduces LLM usage by 95%  
**Status**: Architecture approved, specifications complete  
**Estimated Duration**: 3-4 dev days  
**Critical Requirement**: This is the PRODUCTION approach – no modifications to architecture, follow exactly

---

## 🎯 CRITICAL CONTEXT

### Problem Statement

Current Phase 2a design processes all 2 million CRS comments through Qwen3 LLM:
- **Cost**: 20k USD equivalent (compute)
- **Time**: 24-48 hours per batch
- **Scalability**: Impractical for iterative improvements

### Solution: 4-Tier Cascade Classifier

Route comments through escalating complexity tiers:
1. **Tier 0** (5-10%): Deterministic skip (no DB queries)
2. **Tier 1** (50-70%): Knowledge base template matching (DB lookup)
3. **Tier 2** (15-20%): Keyword regex rules (zero cost)
4. **Tier 3** (5-10%): LLM only for unclear cases (~100-200k comments)

**Result**: 95% cost reduction, 85% time reduction, >90% accuracy maintained

### Non-Negotiable Requirements

From architect review + community research (Reddit r/LocalLLaMA):
- ✅ Cascade classifier is proven pattern for cost optimization
- ✅ Knowledge base auto-population (Tier 3 results → Tier 1 templates)
- ✅ Only 5-10% of comments reach LLM in subsequent batches
- ✅ Split JOINs into separate views (prevent Cartesian explosion)
- ✅ Use fuzzy matching for template lookup (>0.92 threshold)
- ✅ Batch inference on Qwen3 (32-item batches, 85% cost reduction)

**You must implement this exact architecture. No simplifications, no "just use LLM for all".**

---

## 📚 REFERENCE DOCUMENTS

All specifications are in `/mnt/user-data/outputs/`:

1. **PHASE2_CASCADE_ARCHITECTURE.md** ← **PRIMARY REFERENCE**
   - Full architecture with 4 tiers explained
   - Database schema changes (2 new tables)
   - Performance analysis (2M comments in 2-4 hours after Tier 1 warm-up)
   - Task breakdown with pseudocode examples
   - Success metrics

2. Previous context (for reference only):
   - PHASE2_IMPLEMENTATION_SPEC.md (old v1 design, superseded)
   - PHASE2_ARCHITECTURE_REVIEW.md (old v1 review)
   - PHASE2_SUMMARY.md (old v1 overview)

---

## 🎯 IMPLEMENTATION TASKS

### Task 1: Create Migrations (migration_016_revised + migration_017_new)

**Files to create**: (Can consolidate into ONE file if preferred)
- `sql/migrations/migration_016_crs_phase2_revised.sql` (~200 lines)
- `sql/migrations/migration_017_crs_comment_templates.sql` (~150 lines)

**What to implement**:

#### Part A: migration_016_crs_phase2_revised.sql

1. **DROP/RECREATE Views (corrected from v1)**
   - ❌ Old: Single mega-view with all JOINs → Cartesian product
   - ✅ New: TWO separate views
     - `project_core.v_tag_with_docs` (tag + document only, no properties)
     - `project_core.v_tag_properties` (tag + properties only, no documents)
   
   Both use LEFT JOINs and WHERE object_status='Active'

2. **Seed 5 validation queries** into `audit_core.crs_validation_query`
   - TAG_EXISTS: tag in EDW with Active status
   - TAG_HAS_DOCUMENT: tag linked to document via mapping.tag_document
   - TAG_HAS_PROPERTY: tag has specific property value
   - TAG_FROM_TO_LINK: FROM/TO relationship
   - TAGS_WITHOUT_PROPERTIES: count of tags with zero properties
   
   Use ON CONFLICT (query_code) DO UPDATE SET ... (not DELETE)

3. **Add CHECK constraint** on category column
   ```sql
   CHECK (category IN (
       'tag_existence', 'document_link', 'property_check', 
       'tag_relationship', 'bulk_check', 'custom'
   ))
   ```

**Acceptance**:
- [ ] Both views created and queryable without Cartesian explosion
- [ ] 5 seed queries inserted successfully
- [ ] ON CONFLICT works (idempotent)
- [ ] Constraint prevents invalid categories

---

#### Part B: migration_017_crs_comment_templates.sql (NEW)

1. **Create `audit_core.crs_comment_template`** table
   - Columns (from ARCHITECTURE spec):
     - id (UUID PK)
     - template_text (TEXT) — normalized comment (no tag names, numbers)
     - template_hash (TEXT UNIQUE) — MD5 hash for exact matching
     - category (TEXT) — MISSING_DOCUMENT_LINK, TAG_NOT_FOUND, etc.
     - check_type (TEXT) — TAG_EXISTS, TAG_HAS_DOCUMENT, etc.
     - response_template (TEXT) — templated response with {placeholders}
     - source (TEXT) — 'llm' | 'manual' | 'rule'
     - confidence (REAL) — 1.0 (exact) or fuzzy score
     - usage_count (INTEGER) — track reuse
     - last_used_at (TIMESTAMP)
     - created_at (TIMESTAMP)
     - object_status (TEXT) — Active | Inactive
   
   - Indexes: (category), (template_hash)

2. **Alter `audit_core.crs_comment` table** (ADD IF NOT EXISTS)
   - classification_tier (SMALLINT) — 0|1|2|3
   - template_id (UUID) — FK to crs_comment_template
   - FK constraint: template_id REFERENCES crs_comment_template(id) ON DELETE SET NULL

3. **Add COMMENTs** documenting purpose and usage

**Acceptance**:
- [ ] Table created with correct columns
- [ ] Indexes on category + template_hash
- [ ] crs_comment updated with new columns
- [ ] FK constraint added
- [ ] All comments documented

---

### Task 2: Implement Tier 0 Pre-filter (`flows/tasks/tier0_prefilter.py`)

**Purpose**: Skip 5-10% of comments that don't need classification (no LLM)

**What to implement**:

```python
@task(name="tier0-prefilter")
def run_tier0(comments: list[dict], engine) -> tuple[list[dict], list[dict]]:
    """
    Deterministic skip conditions.
    Returns (to_process, skipped).
    
    Skip if:
    1. Text matches informational patterns (regex): "for information", "see attached", "FYI", etc.
    2. tag_name NOT NULL but tag_id IS NULL (unknown tag)
    3. tag.object_status = 'Inactive' (deleted tag)
    """
```

**Implementation details**:

1. **Regex pattern** for informational phrases
   ```python
   _INFO_PATTERNS = re.compile(
       r"\b(for\s+information|see\s+attached|fyi\b|...)\b",
       re.IGNORECASE
   )
   ```

2. **Tag status lookup** (single DB query, batch prefetch)
   - If comment has tag_name, fetch tag.object_status from DB
   - Cache in dict for efficiency

3. **Result format** for skipped records
   ```python
   {
       **comment,
       "status": "SKIPPED",
       "llm_category": "N/A",
       "classification_tier": 0,
       "skip_reason": "INFORMATIONAL" | "TAG_NOT_IN_EDW" | "TAG_INACTIVE"
   }
   ```

**Acceptance**:
- [ ] Informational phrase detection works
- [ ] Tag status lookup correct
- [ ] Results have correct status/tier
- [ ] Logging shows count of skipped
- [ ] Unit test: test_tier0_skip_info_phrase()
- [ ] Unit test: test_tier0_skip_unknown_tag()
- [ ] Unit test: test_tier0_skip_inactive_tag()

---

### Task 3: Implement Tier 1 Template Matcher (`flows/tasks/tier1_template_matcher.py`)

**Purpose**: Match normalized comments against knowledge base (template DB)

**What to implement**:

```python
def normalise_comment(text: str) -> str:
    """
    Strip entity-specific values from comment.
    Examples:
      "Tag HIS0163 missing DESIGN_PRESSURE" 
      → "tag XXXXX missing PROPERTY"
      
      "Document JDAW-KVE-E-JA-6944-00001-016 not linked"
      → "document XXXXX not linked"
    """
    # Replace:
    # - Tag names (HIS*, XV-*, etc.) with XXXXX
    # - Document numbers (JDAW-*) with XXXXX
    # - Numbers (any digit sequence) with N
    # Lowercase, strip whitespace

@task(name="tier1-template-matcher")
def run_tier1(comments: list[dict], engine, similarity_threshold: float = 0.92) -> tuple[list[dict], list[dict]]:
    """
    Match normalized comments against crs_comment_template table.
    
    Process:
    1. Load all active templates from DB (cache in memory)
    2. For each comment:
       - Normalize text
       - Try exact hash match
       - If not found, fuzzy match (SequenceMatcher ratio >= threshold)
    3. Return matched (with template_id) and unmatched
    
    Returns (unmatched, classified).
    """
    # Implementation:
    # - SELECT * FROM crs_comment_template WHERE object_status='Active'
    # - For each comment:
    #   - norm = normalise_comment(comment.text)
    #   - hash = MD5(lower(trim(norm)))
    #   - Try exact match in templates by hash
    #   - If not found, do fuzzy matching (SequenceMatcher) against all templates
    #   - If score >= threshold: matched
    #   - Result: status='CLASSIFIED', confidence=score, tier=1, template_id=<id>
```

**Implementation details**:

1. **Normalization function** (case-insensitive, robust)
   ```python
   def normalise_comment(text: str) -> str:
       # 1. Remove tag names (regex: [A-Z]{2,}[0-9]*, XI-*, XV-*)
       # 2. Remove doc numbers (JDAW-*)
       # 3. Replace numbers with 'N'
       # 4. lowercase + strip + compress whitespace
   ```

2. **Fuzzy matching** using difflib.SequenceMatcher
   ```python
   from difflib import SequenceMatcher
   score = SequenceMatcher(None, norm, template_text).ratio()
   ```

3. **Result format**
   ```python
   {
       **comment,
       "llm_category": template["category"],
       "llm_category_confidence": score,  # 0.92-1.0
       "classification_tier": 1,
       "template_id": str(template["id"]),
       "status": "CLASSIFIED"
   }
   ```

**Acceptance**:
- [ ] normalise_comment() handles tag names, doc numbers, digits
- [ ] Exact hash lookup works
- [ ] Fuzzy matching with threshold works
- [ ] Returns correct status/tier/template_id
- [ ] Logging shows # matched vs unmatched
- [ ] Unit test: test_normalize_comment_removes_tag_names()
- [ ] Unit test: test_tier1_exact_hash_match()
- [ ] Unit test: test_tier1_fuzzy_match_above_threshold()

---

### Task 4: Implement Tier 2 Keyword Classifier (`flows/tasks/tier2_keyword_classifier.py`)

**Purpose**: Match against hardcoded regex rules (deterministic, 15-20% coverage)

**What to implement**:

```python
@dataclass
class Rule:
    pattern: re.Pattern
    category: str
    check_type: str
    confidence: float = 0.85

RULES: list[Rule] = [
    Rule(
        pattern=re.compile(r"no\s+document\s+ref|not\s+linked\s+to\s+(any\s+)?doc|missing\s+doc(ument)?", re.I),
        category="MISSING_DOCUMENT_LINK",
        check_type="TAG_HAS_DOCUMENT"
    ),
    Rule(
        pattern=re.compile(r"not\s+(found|present|exist|in\s+edw|in\s+(the\s+)?database)", re.I),
        category="TAG_NOT_FOUND",
        check_type="TAG_EXISTS"
    ),
    Rule(
        pattern=re.compile(r"(property|attribute|field)\s+(not\s+)?(provided|missing|empty|blank|incorrect)", re.I),
        category="MISSING_PROPERTY",
        check_type="TAG_HAS_PROPERTY"
    ),
    # ... more rules (10+ total)
]

@task(name="tier2-keyword-classifier")
def run_tier2(comments: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Match against keyword rules (regex patterns).
    Returns (unmatched, classified).
    """
    # For each comment:
    #   - text = comment.comment or comment.group_comment
    #   - for rule in RULES:
    #       - if rule.pattern.search(text):
    #           - matched! Return category + check_type
    #   - if no match: add to unmatched
    # Result: status='CLASSIFIED', confidence=0.85, tier=2
```

**Implementation details**:

1. **Define 10+ rules** covering common CRS patterns
   - "missing document" → MISSING_DOCUMENT_LINK
   - "tag not found|not present|not exist" → TAG_NOT_FOUND
   - "property missing|empty|blank" → MISSING_PROPERTY
   - "wrong|invalid tag class" → WRONG_TAG_CLASS
   - "tag description missing" → TAG_DESCRIPTION_ISSUE
   - "spelling|typo" → SPELLING_ERROR
   - "FROM|TO tag missing" → MISSING_FROM_TO_LINK
   - "safety critical reason missing" → SAFETY_CRITICAL_MISSING
   - "plant|area|process unit wrong" → WRONG_LOCATION
   - "duplicate|already exists" → DUPLICATE_TAG

2. **Pattern matching** (ordered evaluation, first match wins)
   ```python
   for rule in RULES:
       if rule.pattern.search(text):
           return rule.category, rule.check_type, rule.confidence
   ```

3. **Result format**
   ```python
   {
       **comment,
       "llm_category": category,
       "llm_category_confidence": 0.85,
       "classification_tier": 2,
       "status": "CLASSIFIED"
   }
   ```

**Acceptance**:
- [ ] All 10+ rules defined with correct patterns
- [ ] First-match evaluation works (no overlaps or priority issues)
- [ ] Pattern matching is case-insensitive
- [ ] Results have correct status/confidence/tier
- [ ] Logging shows # matched vs unmatched
- [ ] Unit test: test_rule_missing_document_link()
- [ ] Unit test: test_rule_tag_not_found()
- [ ] Unit test: test_rule_missing_property()

---

### Task 5: Implement Tier 3 LLM Classifier (`flows/tasks/tier3_llm_classifier.py`)

**Purpose**: LLM classification for only 5-10% of comments (unclear/complex cases)

**What to implement**:

```python
@task(name="tier3-llm-classifier", retries=2)
def run_tier3_llm(comments: list[dict], engine) -> list[dict]:
    """
    LLM-based classification for unclear/complex comments.
    
    Process per comment:
    1. Extract parameters (tag_name, property_name, from_tag, to_tag, doc_number)
    2. Query crs_validation_query to pick matching SQL
    3. Execute SQL (with params) to verify issue
    4. Generate response based on result
    5. Return llm_category + check_type + confidence
    
    Only 100-200k comments reach this tier (5-10% of 2M).
    
    Returns list[dict] with status='CLASSIFIED' or 'PENDING_REVIEW',
            classification_tier=3, llm_category, confidence
    """
    # Implementation:
    # - For each comment:
    #   - Extract parameters (use regex from parameter_validator.py)
    #   - Validate parameters (all required params present)
    #   - Query crs_validation_query registry for matching SQL
    #   - Execute SQL with parameters
    #   - Call LLM: "Based on this query result, classify and generate response"
    #   - Return result with llm_category + confidence
```

**Implementation details**:

1. **Parameter extraction** (reuse logic from previous phase)
   ```python
   def extract_parameters(comment_text: str) -> dict:
       params = {}
       # tag_name: "Tag HIS0163" → HIS0163
       # property_name: "DESIGN_PRESSURE" → DESIGN_PRESSURE
       # from_tag, to_tag: "from X to Y"
       # doc_number: "JDAW-KVE-E-JA-6944-00001-016"
       return params
   ```

2. **SQL query selection** (from registry)
   ```python
   # SELECT sql_query, parameter_names FROM crs_validation_query 
   # WHERE category IN (...) AND has_parameters=true
   # Pick best match based on extracted parameters
   ```

3. **LLM inference** (batch 32 comments for 85% cost reduction)
   ```python
   # Use ChatOpenAI with base_url="http://<lxc-ip>:11434/v1"
   # Batch process: 32 comments per LLM call
   # Prompt: "Classify comment type and generate response based on SQL result"
   ```

4. **Result format**
   ```python
   {
       **comment,
       "llm_category": "MISSING_DOCUMENT_LINK",
       "llm_category_confidence": 0.92,
       "classification_tier": 3,
       "check_type": "TAG_HAS_DOCUMENT",
       "status": "CLASSIFIED" or "PENDING_REVIEW",
       "llm_response": "..."
   }
   ```

**Acceptance**:
- [ ] Parameter extraction works for tag, property, doc_number
- [ ] SQL query selection works
- [ ] SQL execution returns correct results
- [ ] LLM returns valid classifications
- [ ] Batch inference (32-item batches) working
- [ ] Results have correct status/tier/category
- [ ] Logging shows # classified per batch
- [ ] Unit test: test_parameter_extraction_tag_name()
- [ ] Unit test: test_sql_query_selection()

---

### Task 6: Implement Template Manager (`flows/tasks/template_manager.py`)

**Purpose**: Auto-populate knowledge base from Tier 3 LLM results

**What to implement**:

```python
@task(name="update-template-db")
def update_template_db(llm_results: list[dict], engine) -> int:
    """
    Called after each Tier 3 batch — turns LLM classifications into reusable patterns.
    
    Process:
    1. For each LLM result with confidence >= 0.85:
       - Normalize the comment text (reuse normalise_comment from tier1)
       - Hash it (MD5)
       - Upsert into audit_core.crs_comment_template
         - If hash exists: increment usage_count, update last_used_at
         - If new: insert with source='llm', confidence, category, check_type
    
    Returns count of new/updated templates.
    
    Key side effect: Tier 1 template DB grows automatically!
    After 3-4 batches, most typical patterns cached → dramatic speedup.
    """
    # Implementation:
    # - For each result in llm_results:
    #   - if confidence < 0.85: skip
    #   - norm = normalise_comment(result.comment_text)
    #   - hash = MD5(lower(trim(norm)))
    #   - INSERT INTO crs_comment_template (...) VALUES (...)
    #     ON CONFLICT (template_hash) DO UPDATE SET
    #        usage_count = usage_count + 1,
    #        last_used_at = now()
```

**Implementation details**:

1. **Reuse normalise_comment()** from tier1_template_matcher.py

2. **SQL upsert**
   ```sql
   INSERT INTO audit_core.crs_comment_template
       (template_text, template_hash, category, check_type, confidence, source, usage_count)
   VALUES
       (:text, :hash, :cat, :chk, :conf, 'llm', 1)
   ON CONFLICT (template_hash) DO UPDATE SET
       usage_count = crs_comment_template.usage_count + 1,
       last_used_at = now()
   ```

3. **Logging**
   ```python
   logger.info(f"Template DB: {added} entries upserted")
   ```

**Acceptance**:
- [ ] Normalization applied to comment text
- [ ] Hash calculated correctly
- [ ] ON CONFLICT upsert works
- [ ] usage_count incremented on re-encounter
- [ ] Returns count of updated entries
- [ ] Logging shows count
- [ ] Unit test: test_template_upsert_new()
- [ ] Unit test: test_template_upsert_increment_usage()

---

### Task 7: Main Orchestration Flow (`flows/classify_crs_comments.py`)

**Purpose**: Chain all 4 tiers with knowledge base accumulation

**What to implement**:

```python
@flow(name="classify-crs-comments-cascade", description="4-tier cascade classifier with KB accumulation")
def classify_crs_comments_cascade(limit: int = 5000, batch_size: int = 500):
    """
    Main orchestration flow.
    
    Process:
    1. Load RECEIVED comments
    2. For each batch:
       - Tier 0: pre-filter (skip informational, unknown tags, inactive tags)
       - Tier 1: template lookup (KB matching)
       - Tier 2: keyword rules (regex)
       - Tier 3: LLM (remaining unclear)
       - Update template DB from Tier 3 results
    3. Save all results to crs_comment table with classification_tier + status
    4. Log summary stats
    
    Returns dict of stats {tier0: count, tier1: count, tier2: count, tier3: count}
    """
    engine = get_engine()
    run_id = str(uuid.uuid4())
    
    comments = load_received_comments(limit=limit, engine=engine)
    
    stats = {"tier0": 0, "tier1": 0, "tier2": 0, "tier3": 0}
    all_results = []
    
    for i in range(0, len(comments), batch_size):
        batch = comments[i : i + batch_size]
        
        # TIER 0
        batch, t0_results = run_tier0(batch, engine)
        stats["tier0"] += len(t0_results)
        all_results.extend(t0_results)
        
        # TIER 1
        batch, t1_results = run_tier1(batch, engine)
        stats["tier1"] += len(t1_results)
        all_results.extend(t1_results)
        
        # TIER 2
        batch, t2_results = run_tier2(batch)
        stats["tier2"] += len(t2_results)
        all_results.extend(t2_results)
        
        # TIER 3
        if batch:
            t3_results = run_tier3_llm(batch, engine)
            stats["tier3"] += len(t3_results)
            all_results.extend(t3_results)
            
            # Auto-populate template DB
            update_template_db(t3_results, engine)
    
    # Save results
    save_classification_results(all_results, engine, run_id)
    
    # Log summary
    logger = get_run_logger()
    logger.info(f"Classification complete: {stats}")
    logger.info(f"Tier 0 (skipped): {stats['tier0']} ({100*stats['tier0']/(sum(stats.values())):.1f}%)")
    logger.info(f"Tier 1 (template): {stats['tier1']} ({100*stats['tier1']/(sum(stats.values())):.1f}%)")
    logger.info(f"Tier 2 (keyword): {stats['tier2']} ({100*stats['tier2']/(sum(stats.values())):.1f}%)")
    logger.info(f"Tier 3 (LLM): {stats['tier3']} ({100*stats['tier3']/(sum(stats.values())):.1f}%)")
    
    return stats
```

**Implementation details**:

1. **load_received_comments()** — fetch from DB
2. **run_tier0/1/2/3()** — call each task in sequence
3. **update_template_db()** — populate KB from Tier 3
4. **save_classification_results()** — batch UPDATE of crs_comment table
5. **Logging** — stats per tier

**Acceptance**:
- [ ] All 4 tiers execute in order
- [ ] Results accumulated correctly
- [ ] Template DB updated after Tier 3
- [ ] Stats logged per tier
- [ ] Final results saved to DB
- [ ] Prefect logs show execution trace
- [ ] Unit test: test_flow_chains_tiers()

---

### Task 8: Helper Functions & Tests

**What to implement**:

1. **`flows/tasks/helpers.py`** (shared utilities)
   ```python
   def load_received_comments(limit: int, engine) -> list[dict]:
       """SELECT * FROM crs_comment WHERE status='RECEIVED' LIMIT limit"""
   
   def get_engine():
       """Return SQLAlchemy engine (from config)"""
   
   def save_classification_results(results: list[dict], engine, run_id: str):
       """Batch UPDATE crs_comment table with classifications"""
   
   def prefetch_tag_statuses(tag_names: list[str], engine) -> dict[str, str]:
       """Returns {tag_name: object_status} for Tier 0 lookup"""
   ```

2. **`tests/test_cascade_classifier.py`** (unit + integration tests)
   ```python
   # Tier 0
   test_tier0_skip_info_phrase()
   test_tier0_skip_unknown_tag()
   test_tier0_skip_inactive_tag()
   
   # Tier 1
   test_normalize_comment_removes_tag_names()
   test_tier1_exact_hash_match()
   test_tier1_fuzzy_match_above_threshold()
   
   # Tier 2
   test_rule_missing_document_link()
   test_rule_tag_not_found()
   
   # Tier 3
   test_parameter_extraction_tag_name()
   test_sql_query_selection()
   
   # Template manager
   test_template_upsert_new()
   test_template_upsert_increment_usage()
   
   # Flow
   test_flow_chains_tiers()
   test_flow_stats_reported()
   ```

**Acceptance**:
- [ ] All helper functions work
- [ ] All tests pass (>80% coverage)
- [ ] No import errors
- [ ] Logging works throughout

---

## 🔧 TECHNICAL REQUIREMENTS

### Database

Before implementation:
- [ ] PostgreSQL connection working (config/db_config.yaml)
- [ ] Migrations 016 + 017 applied
- [ ] `crs_comment_template` table exists
- [ ] `crs_comment.classification_tier` + `template_id` columns exist

### Prefect

- [ ] Prefect 3.x installed
- [ ] flows/ directory structure ready
- [ ] flows/tasks/ subdirectory exists

### Dependencies

```bash
langchain_openai>=0.1.0
psycopg2-binary>=2.9.0
prefect>=3.0.0
pytest>=7.0.0
```

### LXC Setup

- [ ] Qwen3-Coder-48B running in LXC on port 11434 (Ollama) or 8080 (llama.cpp)
- [ ] Test endpoint: `curl http://<lxc-ip>:11434/api/tags`
- [ ] Update OLLAMA_BASE_URL in tier3_llm_classifier.py with actual IP

---

## 🚀 IMPLEMENTATION SEQUENCE

### Week 1: Foundation (Days 1-3)

```bash
# Day 1: Migrations
1a. Create migration_016_crs_phase2_revised.sql
1b. Create migration_017_crs_comment_templates.sql
1c. psql -f migration_016_crs_phase2_revised.sql
1d. psql -f migration_017_crs_comment_templates.sql
1e. Verify: SELECT COUNT(*) FROM audit_core.crs_comment_template;

# Day 2: Tiers 0 + 1
2a. Create flows/tasks/tier0_prefilter.py
2b. Create flows/tasks/tier1_template_matcher.py (with normalise_comment)
2c. Test: python -m pytest tests/test_tier0.py tests/test_tier1.py -v

# Day 3: Tiers 2 + 3 + Manager
3a. Create flows/tasks/tier2_keyword_classifier.py
3b. Create flows/tasks/tier3_llm_classifier.py (with ChatOpenAI setup)
3c. Create flows/tasks/template_manager.py
3d. Create flows/tasks/helpers.py
3e. Test: python -m pytest tests/test_tier2.py tests/test_tier3.py -v
```

### Week 2: Integration (Days 4-5)

```bash
# Day 4: Main flow
4a. Create flows/classify_crs_comments.py
4b. Create tests/test_cascade_classifier.py (integration tests)
4c. Test on 100 comments: prefect run flows/classify_crs_comments.py --limit 100

# Day 5: Production validation
5a. Run on 5000 comments: prefect run flows/classify_crs_comments.py --limit 5000
5b. Verify tier distribution: check stats output
5c. Check template DB growth: SELECT COUNT(*) FROM crs_comment_template
5d. Verify accuracy: spot-check 20-30 random classifications
```

---

## 🎯 SUCCESS CRITERIA

All of these must be met before Phase 2 is complete:

### Tier 0
- [x] Skips 5-10% of comments (informational, unknown tags, inactive tags)
- [x] Speed: <1 sec for 5000 comments
- [x] Accuracy: 100% (deterministic)

### Tier 1
- [x] Matches 0% on first batch (no templates yet)
- [x] Matches 50-70% on subsequent batches (KB warm)
- [x] Speed: <30 sec for 5000 comments
- [x] Fuzzy matching threshold working (>0.92)
- [x] Template hash exact matching working

### Tier 2
- [x] Matches 15-20% of remaining comments
- [x] Speed: <5 sec for 5000 comments
- [x] All 10+ rules firing correctly
- [x] No false positives (spot-check)

### Tier 3
- [x] Only 5-10% of comments (100-200k per batch)
- [x] LLM inference working (ChatOpenAI → Qwen3)
- [x] Parameter extraction working
- [x] SQL query selection working
- [x] Batch inference (32-item batches) working

### Template Manager
- [x] Auto-populates crs_comment_template from Tier 3
- [x] usage_count incremented on re-encounter
- [x] Tier 1 coverage improves batch-over-batch

### Overall Flow
- [x] All 4 tiers execute in correct order
- [x] Stats reported (# per tier, percentages)
- [x] Results saved to crs_comment table
- [x] classification_tier column populated (0-3)
- [x] First batch: 24-48 hours (mostly Tier 3)
- [x] Subsequent batches: 2-4 hours (mostly Tier 1)

### Code Quality
- [x] All functions have Prefect @task decorators
- [x] All tasks logged via get_run_logger()
- [x] Error handling with try-except
- [x] No hardcoded credentials
- [x] Type hints on function signatures
- [x] All unit tests pass (>80% coverage)
- [x] Code follows project conventions

---

## ⚠️ CRITICAL POINTS

1. **Cascade is non-negotiable**
   - Do NOT simplify to "just use LLM for everything"
   - Do NOT skip Tier 0/1/2
   - Do NOT skip knowledge base accumulation

2. **Split views required**
   - v_tag_with_docs (tag + document only)
   - v_tag_properties (tag + property only)
   - NOT a single mega-view (prevents Cartesian explosion)

3. **Fuzzy matching threshold**
   - Minimum 0.92 (SequenceMatcher ratio)
   - Higher = fewer false positives, more pass to next tier (which is OK)

4. **Knowledge base auto-population**
   - Tier 3 results feed directly into Tier 1 templates
   - This is what makes subsequent batches fast
   - Without this, you don't get the 2-4 hour per-batch performance

5. **Batch inference on Qwen3**
   - 32-item batches reduce cost 85%
   - Process Tier 3 comments in groups
   - Single LLM call for 32 comments at once

6. **Parameter extraction must be robust**
   - Handle tag names, doc numbers, special references
   - Reuse regex from previous phase work

---

## 🧪 QUICK SMOKE TEST

Once complete, run this to verify everything:

```python
# Test 1: Migrations applied
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM audit_core.crs_comment_template"))
    print(f"Template table exists: {result.scalar()} rows")

# Test 2: Tier 0 skip
from flows.tasks.tier0_prefilter import should_skip
skip, reason = should_skip(
    {"comment": "For information only", "tag_name": "HIS0163", "tag_id": "..."},
    {"HIS0163": "Active"}
)
assert skip == True and reason == "INFORMATIONAL"
print("✓ Tier 0 skip works")

# Test 3: Tier 1 normalize
from flows.tasks.tier1_template_matcher import normalise_comment
norm = normalise_comment("Tag HIS0163 missing DESIGN_PRESSURE")
assert "XXXXX" in norm and "PROPERTY" in norm
print("✓ Tier 1 normalize works")

# Test 4: Tier 2 rules
from flows.tasks.tier2_keyword_classifier import classify_by_keywords
cat, chk, conf = classify_by_keywords("tag not found in database")
assert cat == "TAG_NOT_FOUND"
print("✓ Tier 2 rule matching works")

# Test 5: Flow execution
from flows.classify_crs_comments import classify_crs_comments_cascade
stats = classify_crs_comments_cascade(limit=100)
assert stats["tier0"] + stats["tier1"] + stats["tier2"] + stats["tier3"] == 100
print(f"✓ Flow works: {stats}")
```

---

## 📞 ESCALATION

If you encounter:

- **Template table not found**: Run migration_017
- **LXC not responding**: Verify IP, test `curl http://<lxc-ip>:11434/api/tags`
- **Schema mismatch**: Check that migrations applied completely
- **Tier accuracy <90%**: Add more keyword rules, adjust fuzzy threshold
- **First batch taking too long**: Expected (no templates yet), Tier 3 only reaches ~70% of comments
- **Template DB not growing**: Verify update_template_db() is called after Tier 3

---

## ✅ CRITICAL CHECKLIST BEFORE STARTING

- [ ] Read PHASE2_CASCADE_ARCHITECTURE.md (full arch understanding required)
- [ ] Read this entire prompt carefully
- [ ] Have /mnt/user-data/outputs/ directory accessible for reference
- [ ] PostgreSQL connection verified
- [ ] Qwen3 LXC running and accessible
- [ ] Understand 4-tier cascade (not just LLM)
- [ ] Understand knowledge base auto-population
- [ ] Understand fuzzy matching at 0.92 threshold
- [ ] Understand batch inference (32-item groups)

---

## 🎯 DELIVERABLE

When complete, you should have:

1. ✅ `sql/migrations/migration_016_crs_phase2_revised.sql` (applied)
2. ✅ `sql/migrations/migration_017_crs_comment_templates.sql` (applied)
3. ✅ `flows/classify_crs_comments.py` (main orchestration flow)
4. ✅ `flows/tasks/tier0_prefilter.py`
5. ✅ `flows/tasks/tier1_template_matcher.py`
6. ✅ `flows/tasks/tier2_keyword_classifier.py`
7. ✅ `flows/tasks/tier3_llm_classifier.py`
8. ✅ `flows/tasks/template_manager.py`
9. ✅ `flows/tasks/helpers.py`
10. ✅ `tests/test_cascade_classifier.py` (integration tests)

All code reviewed against PHASE2_CASCADE_ARCHITECTURE.md and passing all acceptance criteria.

**Phase 2 will be production-ready after integration validation on 5000-comment test batch.**

---

**Status**: ✅ **READY FOR IMPLEMENTATION**

This is the architect-approved approach. Follow exactly. No modifications to cascade design.

