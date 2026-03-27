# Phase 2 CRS Classification – Cascade Architecture v2

**Version**: 2.0 (Cascade Classifier with Knowledge Base)  
**Status**: ✅ APPROVED FOR IMPLEMENTATION  
**Date**: 2026-03-27  
**Cost Reduction**: 95% (from 2M → ~100-200k LLM calls)  

---

## Executive Summary

**Problem (v1)**: Process 2 million comments with LLM → impractical, expensive, slow  
**Solution (v2)**: 4-tier cascade classifier that handles 90-95% without LLM  
**Result**: Only 100-200k comments need Qwen3, rest handled by rules + knowledge base matching

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│ audit_core.crs_comment (status='RECEIVED')                       │
│ From Phase 1 ingestion (~2M records)                             │
└──────────────────┬───────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│ TIER 0: Pre-filter (Deterministic skip)                          │
│ ~5-10% of comments                                               │
│                                                                  │
│ Skip conditions (no DB queries):                                 │
│  1. Informational phrases: "For information", "See attached"     │
│  2. tag_name NOT NULL BUT tag_id IS NULL → unknown tag          │
│  3. tag.object_status = 'Inactive' → deleted tag                │
│                                                                  │
│ Result: status='SKIPPED', llm_category='N/A',                   │
│         classification_tier=0                                    │
│ Speed: O(1) regex checks, ~500k/sec                             │
└──────────────────┬───────────────────────────────────────────────┘
                   │
        ~90-95% remaining
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│ TIER 1: Template Lookup (Knowledge base matching)                │
│ ~60-70% of remaining comments                                    │
│                                                                  │
│ Process:                                                         │
│  1. Normalize comment: strip tag names, numbers, specific refs   │
│  2. Hash normalization → lookup in audit_core.crs_comment_template
│  3. If exact match found → return category + response template   │
│  4. If not found → Fuzzy similarity (SequenceMatcher > 0.92)    │
│                                                                  │
│ Database: audit_core.crs_comment_template (populated from Tier 3)
│ Result: status='CLASSIFIED', confidence=0.92-1.0,               │
│         classification_tier=1, template_id=<match>              │
│ Speed: ~50k/sec (single DB query + fuzzy match)                │
│                                                                  │
│ Key advantage: Auto-populated from previous LLM results.        │
│ After 3-4 batches, most typical patterns cached.                │
└──────────────────┬───────────────────────────────────────────────┘
                   │
        ~20-30% remaining
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│ TIER 2: Keyword Rules (Deterministic regex patterns)             │
│ ~15-20% of remaining comments                                    │
│                                                                  │
│ Predefined regex rules matching common CRS patterns:             │
│  • "missing document" → MISSING_DOCUMENT_LINK                    │
│  • "tag not found" → TAG_NOT_FOUND                              │
│  • "property missing" → MISSING_PROPERTY                         │
│  • "wrong tag class" → WRONG_TAG_CLASS                          │
│  • "spelling error" → SPELLING_ERROR                             │
│  • "FROM/TO missing" → MISSING_FROM_TO_LINK                     │
│  ... (10+ patterns)                                             │
│                                                                  │
│ Result: status='CLASSIFIED', confidence=0.85,                   │
│         classification_tier=2                                    │
│ Speed: ~200k/sec (pure regex, O(n) text match)                  │
│                                                                  │
│ Database: Rules stored as Python code (no DB lookup needed)      │
└──────────────────┬───────────────────────────────────────────────┘
                   │
        ~5-10% remaining
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│ TIER 3: Qwen3 LLM (Only for unclear/complex)                     │
│ ~5-10% of original comments = 100-200k records                  │
│                                                                  │
│ Process:                                                         │
│  1. Extract parameters from text (tag_name, property, etc.)      │
│  2. Query crs_validation_query registry → get SQL query          │
│  3. Execute SQL against EDW → get verification result            │
│  4. Generate response based on result                            │
│                                                                  │
│ Result: status='CLASSIFIED' or 'PENDING_REVIEW',                │
│         classification_tier=3, llm_category + response           │
│ Speed: ~15-30 tokens/sec per comment (local Qwen3)              │
│                                                                  │
│ Side effect: Results fed back into TIER 1 template DB            │
│ (Auto-populate knowledge base for future batches)               │
└──────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Changes

### New Table: `audit_core.crs_comment_template`

Purpose: Accumulating knowledge base of comment patterns → avoids repeated LLM classification

```sql
CREATE TABLE audit_core.crs_comment_template (
    id                  UUID        NOT NULL PRIMARY KEY,
    template_text       TEXT        NOT NULL,   -- Normalized phrase (no tag names, numbers)
    template_hash       TEXT        NOT NULL UNIQUE,  -- MD5(lower(trim(template_text)))
    category            TEXT        NOT NULL,   -- MISSING_DOCUMENT, TAG_NOT_FOUND, etc.
    check_type          TEXT        NULL,       -- TAG_EXISTS, TAG_HAS_DOCUMENT, etc.
    response_template   TEXT        NULL,       -- Templated response with placeholders
    source              TEXT        NOT NULL,   -- 'llm' (auto-populated) | 'manual' | 'rule'
    confidence          REAL        NOT NULL,   -- 1.0 (exact) or fuzzy score
    usage_count         INTEGER     NOT NULL,   -- Track reuse (for metrics)
    last_used_at        TIMESTAMP   NOT NULL,   -- When last matched
    created_at          TIMESTAMP   NOT NULL,
    object_status       TEXT        NOT NULL,   -- Active | Inactive
    
    -- Indexes
    INDEX (category),
    INDEX (template_hash)
);
```

### Updated Table: `audit_core.crs_comment`

New columns added:

```sql
ALTER TABLE audit_core.crs_comment
ADD COLUMN IF NOT EXISTS classification_tier  SMALLINT NULL,  -- 0|1|2|3
ADD COLUMN IF NOT EXISTS template_id          UUID NULL;      -- FK to template (Tier 1 only)

COMMENT ON COLUMN crs_comment.classification_tier IS
    '0=Skipped (Tier 0), 1=Template matched (Tier 1), '
    '2=Keyword rule (Tier 2), 3=LLM classified (Tier 3)';
```

---

## Implementation Structure

### Core Flow: `flows/classify_crs_comments.py`

Main orchestration flow that chains all 4 tiers:

```python
@flow(name="classify-crs-comments-cascade")
def classify_crs_comments_cascade(limit: int = 5000, batch_size: int = 500):
    """
    4-tier cascade classifier with knowledge base accumulation.
    
    Processing order (each tier skips what previous tiers matched):
    1. Tier 0: Pre-filter (skip informational, missing tags, inactive tags)
    2. Tier 1: Template lookup (exact hash + fuzzy match against KB)
    3. Tier 2: Keyword rules (regex patterns)
    4. Tier 3: LLM (only for unclear/complex, results → update template DB)
    """
    engine = get_engine()
    run_id = str(uuid.uuid4())
    
    comments = load_received_comments(limit=limit, engine=engine)
    
    stats = {"tier0": 0, "tier1": 0, "tier2": 0, "tier3": 0}
    all_results = []
    
    for i in range(0, len(comments), batch_size):
        batch = comments[i : i + batch_size]
        
        # TIER 0: Pre-filter
        batch, skipped = run_tier0(batch, engine)
        stats["tier0"] += len(skipped)
        all_results.extend(skipped)
        
        # TIER 1: Template lookup (knowledge base)
        batch, classified = run_tier1(batch, engine)
        stats["tier1"] += len(classified)
        all_results.extend(classified)
        
        # TIER 2: Keyword rules
        batch, classified = run_tier2(batch)
        stats["tier2"] += len(classified)
        all_results.extend(classified)
        
        # TIER 3: LLM (only remaining)
        if batch:
            classified = run_tier3_llm(batch, engine)
            stats["tier3"] += len(classified)
            all_results.extend(classified)
            
            # Auto-populate template DB from LLM results
            update_template_db(classified, engine)
    
    save_results(all_results, engine, run_id)
    return stats
```

### Task 1: `flows/tasks/tier0_prefilter.py`

Deterministic skip conditions (no LLM, minimal DB access):

```python
@task(name="tier0-prefilter")
def run_tier0(comments: list[dict], engine) -> tuple[list[dict], list[dict]]:
    """
    Skip comments that don't need classification.
    Returns (to_process, skipped).
    """
    # Conditions:
    # 1. Text matches: "For information", "See attached", "FYI", etc.
    # 2. tag_name NOT NULL but tag_id IS NULL (unknown tag)
    # 3. tag_id lookup shows object_status='Inactive' (deleted tag)
    
    # Result: status='SKIPPED', llm_category='N/A', classification_tier=0
```

### Task 2: `flows/tasks/tier1_template_matcher.py`

Knowledge base matching (exact hash + fuzzy):

```python
@task(name="tier1-template-matcher")
def run_tier1(comments: list[dict], engine) -> tuple[list[dict], list[dict]]:
    """
    Match normalized comments against audit_core.crs_comment_template.
    
    Process:
    1. Load all active templates from DB (cached in memory)
    2. For each comment:
       - Normalize: lowercase, remove tag names, numbers, specific refs
       - Hash and try exact match
       - If not found, fuzzy match (SequenceMatcher ratio > 0.92)
    3. Return matched comments with template_id + category
    
    Returns (unmatched, classified).
    """
    # Normalization examples:
    # "Tag HIS0163 missing DESIGN_PRESSURE" 
    #   → "tag XXXXX missing PROPERTY"
    # "Document JDAW-KVE-E-JA-6944-00001-016 not linked"
    #   → "document XXXXX not linked"
    
    # Result: status='CLASSIFIED', confidence=score, classification_tier=1, template_id=<id>
```

### Task 3: `flows/tasks/tier2_keyword_classifier.py`

Predefined regex rules (no LLM, no DB):

```python
@task(name="tier2-keyword-classifier")
def run_tier2(comments: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Match against hardcoded keyword patterns.
    
    Rules (examples):
    - "no document ref|not linked to doc" → MISSING_DOCUMENT_LINK
    - "not found|not present|not in edw|not in database" → TAG_NOT_FOUND
    - "property|attribute missing|empty|blank" → MISSING_PROPERTY
    - "wrong|incorrect tag class|equipment class" → WRONG_TAG_CLASS
    - "tag description missing|blank" → TAG_DESCRIPTION_ISSUE
    - "spelling|typo|misspell" → SPELLING_ERROR
    - "FROM|TO tag missing" → MISSING_FROM_TO_LINK
    ... (10+ rules total)
    
    Result: status='CLASSIFIED', confidence=0.85, classification_tier=2
    """
    # Pure regex matching, O(n*m) where m = number of rules
```

### Task 4: `flows/tasks/tier3_llm_classifier.py`

Full LLM classification (with SQL verification):

```python
@task(name="tier3-llm-classifier")
def run_tier3_llm(comments: list[dict], engine) -> list[dict]:
    """
    LLM-based classification for unclear/complex comments.
    
    Process per comment:
    1. Extract parameters (tag_name, property_name, doc_number)
    2. Query crs_validation_query registry to pick SQL
    3. Execute SQL to verify the issue
    4. Generate response based on result
    5. Return with llm_category, check_type, confidence
    
    Only 100-200k comments reach this tier (5-10% of total).
    
    Result: status='CLASSIFIED'|'PENDING_REVIEW', classification_tier=3
    
    Side effect: Results added to crs_comment_template for Tier 1 reuse.
    """
    # Called only for ~5-10% of comments
    # Batched inference on Qwen3 (batch size 32)
    # Results fed back into template DB
```

### Task 5: `flows/tasks/template_manager.py`

Auto-populate knowledge base:

```python
@task(name="update-template-db")
def update_template_db(llm_results: list[dict], engine) -> int:
    """
    Called after each Tier 3 batch — turns new LLM classifications into patterns.
    
    Process:
    1. For each LLM result with confidence >= 0.85:
       - Normalize the comment text
       - Hash it
       - Upsert into audit_core.crs_comment_template (ON CONFLICT increment usage_count)
    
    After 3-4 batches, most typical patterns will be in templates.
    Subsequent batches will have higher Tier 1 coverage.
    
    Returns count of new/updated templates.
    """
    # Key SQL:
    # INSERT INTO crs_comment_template (template_text, template_hash, category, check_type, ...)
    # ON CONFLICT (template_hash) DO UPDATE SET
    #    usage_count = usage_count + 1, last_used_at = now()
```

---

## Expected Performance (2M comments)

### Phase 1: Initial batch (no templates yet)

| Tier | Method | Count | % | Speed | Time |
|------|--------|-------|---|-------|------|
| 0 | Pre-filter | 100-200k | 5-10% | ~500k/sec | ~0.2-0.4 sec |
| 1 | Template (empty KB) | 0 | 0% | N/A | N/A |
| 2 | Keyword rules | 300-400k | 15-20% | ~200k/sec | ~1.5-2 sec |
| 3 | LLM Qwen3 | 1.4-1.6M | 70-80% | ~15-30 tok/s | ~24-48 hours |
| **TOTAL** | | 2M | 100% | | ~24-48 hours |

### Phase 2-4: Knowledge base accumulated

| Tier | Method | Count | % | Speed | Time |
|------|--------|-------|---|-------|------|
| 0 | Pre-filter | 100-200k | 5-10% | ~500k/sec | ~0.2-0.4 sec |
| 1 | Template (warm KB) | 1.0-1.2M | 50-60% | ~50k/sec | ~20-25 sec |
| 2 | Keyword rules | 400-600k | 20-30% | ~200k/sec | ~2-3 sec |
| 3 | LLM Qwen3 | 100-200k | 5-10% | ~15-30 tok/s | ~2-4 hours |
| **TOTAL** | | 2M | 100% | | ~2-4 hours per batch |

**Key insight**: After initial batch, subsequent batches process 2M comments in 2-4 hours (vs 24-48 hours first time).

---

## Cost Reduction Analysis

### Old approach (v1)
- 2M comments × LLM per comment
- Cost per comment: ~0.01 USD (local Qwen3, compute cost equivalent)
- **Total: 20k USD equivalent + time = 24-48 hours**

### New approach (v2)
- Tier 0: 100-200k comments, $0 (regex)
- Tier 1: 1M+ comments, $0 (database lookup)
- Tier 2: 300-600k comments, $0 (regex)
- Tier 3: 100-200k comments, $100 equivalent + time = 2-4 hours
- **Total: 100 USD equivalent + time = 2-4 hours**

**Savings: 95% cost reduction, 85% time reduction**

---

## Migration Files

### `migration_016_crs_phase2.sql`
- Create VIEW `project_core.v_tag_with_docs` (corrected, split into 2 views)
- Create VIEW `project_core.v_tag_properties`
- Seed 5 validation queries into `crs_validation_query`
- Use ON CONFLICT instead of DELETE

### `migration_017_crs_comment_templates.sql` (NEW)
- Create `audit_core.crs_comment_template` table
- Add columns to `audit_core.crs_comment` (classification_tier, template_id)
- Add FK constraint

---

## Timeline

### Week 1 (Phase 2a – Foundation)
- [ ] Day 1: Apply migrations 016 + 017
- [ ] Day 2: Implement Tier 0 + Tier 1 tasks
- [ ] Day 3: Implement Tier 2 + Tier 3 tasks + template_manager

### Week 2 (Phase 2b – Integration)
- [ ] Integrate main flow
- [ ] Run initial batch on 5000 comments (test)
- [ ] Verify stats + accuracy

### Week 3 (Phase 2c – Scale)
- [ ] Deploy to production
- [ ] Run on full 2M comments in batches
- [ ] Monitor template DB growth
- [ ] Tune Tier 2 rules based on results

---

## Key Design Decisions

1. **4-tier cascade vs monolithic LLM**
   - Why: 90-95% of patterns are deterministic (rules + templates)
   - LLM only for genuinely unclear cases

2. **Knowledge base auto-population**
   - Why: Tier 1 improves automatically as Tier 3 processes more data
   - After 3-4 batches, most patterns cached → dramatic speedup

3. **Tier 0 pre-filter**
   - Why: Skip 5-10% of comments that have no data to classify
   - Examples: informational notes, references to deleted tags

4. **Hash-based template matching**
   - Why: Exact match is O(1), fuzzy match for edge cases
   - Prevents repeatedly classifying same-pattern comments

5. **SQL verification in Tier 3**
   - Why: Tie LLM decisions to database truth
   - Generate responses based on actual data state

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Tier 0 accuracy | 100% (deterministic skip) |
| Tier 1 accuracy | 95%+ (template match) |
| Tier 2 accuracy | 85%+ (keyword rules) |
| Tier 3 accuracy | 90%+ (LLM + verification) |
| **Overall accuracy** | **>90%** |
| Tier 3 % of total | **<10%** (ideally 5%) |
| Template DB growth | +10-20k templates per batch |
| Processing time (batch 1) | 24-48 hours |
| Processing time (batch 2+) | 2-4 hours |

---

## Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| LLM hallucination | MEDIUM | SQL verification + human review queue |
| Template pollution | LOW | Min confidence 0.85 + manual review |
| Tier 1 false positives | MEDIUM | Fuzzy threshold 0.92, fallback to Tier 3 |
| Tier 2 rule collisions | LOW | Ordered evaluation, most specific rules first |
| Knowledge base imbalance | MEDIUM | Monitor template distribution, add missing patterns |

---

## Files to Create

1. `migration_016_crs_phase2_revised.sql` — Views + seed queries (corrected)
2. `migration_017_crs_comment_templates.sql` — Template table (NEW)
3. `flows/classify_crs_comments.py` — Main orchestration flow
4. `flows/tasks/tier0_prefilter.py`
5. `flows/tasks/tier1_template_matcher.py`
6. `flows/tasks/tier2_keyword_classifier.py`
7. `flows/tasks/tier3_llm_classifier.py`
8. `flows/tasks/template_manager.py`

(Can be consolidated into 2 files as required)

---

**Status**: ✅ **ARCHITECTURE READY FOR IMPLEMENTATION**

Cascade classifier with knowledge base accumulation reduces LLM usage by 95% while maintaining >90% accuracy.

