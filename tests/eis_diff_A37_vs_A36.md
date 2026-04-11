# EIS Export Revision Diff Report

**Folder A (new):** `C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\Apr-26\CSV\eis_export_A37_20260411_1304`  
**Folder B (baseline):** `C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\Mar-26\CSV`

**Files compared:** 8

## Summary

| Seq | Register | Rev A | Rev B | Rows A | Rows B | Δ Rows | % | ⚠️ |
|-----|----------|-------|-------|-------:|-------:|-------:|--:|---|
| 006 | Tag Physical Connections (EIS-212) | A37 | A36 | 3,790 | 4,502 | +712 | +18.8% | ⚠️ |
| 009 | Tag Class Properties (EIS-307) | A37 | A36 | 5,296 | 1,030 | -4,266 | -80.6% | ⚠️ |
| 017 | Area Register / Doc→Area (EIS-203/411) | A37 | A36 | 18,839 | 18,856 | +17 | +0.1% | ⚠️ |
| 018 | Process Unit Register / Doc→ProcessUnit (EIS-204/410) | A37 | A36 | 16,516 | 19,262 | +2,746 | +16.6% | ⚠️ |
| 020 | Doc→Model Part (EIS-414) | A37 | A36 | 42,450 | 43,656 | +1,206 | +2.8% | ⚠️ |
| 022 | Doc→Purchase Order (EIS-420) | A37 | A36 | 5,808 | 4,334 | -1,474 | -25.4% | ⚠️ |
| 023 | Doc→Plant (EIS-409) | A37 | A36 | 13,477 | 13,477 | +0 | +0.0% | ✅ |
| 024 | Doc→Site (EIS-408) | A37 | A36 | 13,477 | 13,477 | +0 | +0.0% | ✅ |

---

## Detailed Diff per File

### 006 — Tag Physical Connections (EIS-212)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 3,790 | 4,502 | **+18.8%** ⚠️ |

> ⚠️ No PK columns available for row-identity analysis.

#### Column Differences

**Only in A (A37):** `FROM_TAG_NAME`, `TO_TAG_NAME`

**Only in B (A36):** `FROM_TAG`, `TO_TAG`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `PLANT_CODE` | 1 | 1 | 0 | 0 | 0 | 0.0% |  |

#### Row-Level Diff Examples

ℹ️ No row-level differences detected in shared rows.

---

### 009 — Tag Class Properties (EIS-307)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 5,296 | 1,030 | **-80.6%** ⚠️ |

> ⚠️ No PK columns available for row-identity analysis.

#### Column Differences

**Only in A (A37):** `CLASS_CODE`, `CLASS_NAME`, `CONCEPT`, `DATA_TYPE`, `INSTANCE_COUNT`, `IS_MANDATORY`, `PROPERTY_CODE`, `PROPERTY_NAME`, `VALID_VALUES`

**Only in B (A36):** `TAG_CLASS_NAME`, `TAG_PROPERTY_NAME`

#### Row-Level Diff Examples

ℹ️ No row-level differences detected in shared rows.

---

### 017 — Area Register / Doc→Area (EIS-203/411)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 18,839 | 18,856 | +0.1% |
| New rows (in B only) | — | 3 | |
| Removed rows (in A only) | 0 | — | |
| Changed rows (same PK) | — | — | 44,421,819 |

> Primary key used: `AREA_CODE`

#### Column Differences

**Only in B (A36):** `DOC_STATUS`, `PLANT_CODE`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `DOCUMENT_NUMBER` | 8,851 | 8,847 | 0 | 0 | 44,421,819 | **100.0%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-0471000-C10-00001`; `JDAW-0471000-A01-00001` → `JDAW-0471000-C10-00002`; `JDAW-0471000-A01-00001` → `JDAW-0471000-C11-00021` |
| `AREA_CODE` | 23 | 26 | 0 | 0 | 13,491 | **71.6%** ⚠️ | `L400` → `U200`; `U200` → `L400`; `L100` → `U200` |

#### Row-Level Diff Examples

> Rows matched by PK: `AREA_CODE`

**Example 1**
  - 🔑 `AREA_CODE` = `L400`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-0471000-A01-00001` | `JDAW-0471000-C10-00001` |

**Example 2**
  - 🔑 `AREA_CODE` = `L400`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-0471000-A01-00001` | `JDAW-0471000-C10-00002` |

**Example 3**
  - 🔑 `AREA_CODE` = `L400`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-0471000-A01-00001` | `JDAW-0471000-C11-00021` |

**Example 4**
  - 🔑 `AREA_CODE` = `L400`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-0471000-A01-00001` | `JDAW-0471000-C11-00037` |

**Example 5**
  - 🔑 `AREA_CODE` = `L400`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-0471000-A01-00001` | `JDAW-0471000-D04-00001` |

---

### 018 — Process Unit Register / Doc→ProcessUnit (EIS-204/410)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 16,516 | 19,262 | **+16.6%** ⚠️ |
| New rows (in B only) | — | 3 | |
| Removed rows (in A only) | 0 | — | |
| Changed rows (same PK) | — | — | 16,392,502 |

> Primary key used: `PROCESS_UNIT_CODE`

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `DOCUMENT_NUMBER` | 7,987 | 8,847 | 0 | 0 | 16,392,469 | **99.9%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-0471000-B01-00001`; `JDAW-0471000-A01-00001` → `JDAW-0471000-B01-00002`; `JDAW-0471000-A01-00001` → `JDAW-0471000-B01-00003` |
| `PROCESS_UNIT_CODE` | 27 | 30 | 0 | 0 | 15,144 | **91.7%** ⚠️ | `84` → `86`; `86` → `84`; `46` → `83` |
| `PLANT_CODE` | 2 | 2 | 0 | 0 | 21,485 | 0.1% | `JDA` → `SWA`; `JDA` → `SWA`; `JDA` → `SWA` |

#### Row-Level Diff Examples

> Rows matched by PK: `PROCESS_UNIT_CODE`

**Example 1**
  - 🔑 `PROCESS_UNIT_CODE` = `56`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-107805-C11-00002` | `SJDAW-1711000-E02-00010` |
  | `PLANT_CODE` | `JDA` | `SWA` |

**Example 2**
  - 🔑 `PROCESS_UNIT_CODE` = `56`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-107805-C11-00002` | `SJDAW-1711000-E02-00016` |
  | `PLANT_CODE` | `JDA` | `SWA` |

**Example 3**
  - 🔑 `PROCESS_UNIT_CODE` = `56`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-107805-C11-00002` | `SJDAW-1711000-H08-00015` |
  | `PLANT_CODE` | `JDA` | `SWA` |

**Example 4**
  - 🔑 `PROCESS_UNIT_CODE` = `56`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-107805-C11-00002` | `SJDAW-KVE-E-IN-4180-00001` |
  | `PLANT_CODE` | `JDA` | `SWA` |

**Example 5**
  - 🔑 `PROCESS_UNIT_CODE` = `56`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-107805-C11-00002` | `SJDAW-KVE-E-IN-4180-00002` |
  | `PLANT_CODE` | `JDA` | `SWA` |

---

### 020 — Doc→Model Part (EIS-414)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 42,450 | 43,656 | +2.8% |
| New rows (in B only) | — | 46 | |
| Removed rows (in A only) | 84 | — | |
| Changed rows (same PK) | — | — | 0 |

> Primary key used: `DOCUMENT_NUMBER`

#### Column Differences

**Only in A (A37):** `MODEL_PART_CODE`, `PLANT_CODE`

**Only in B (A36):** `MANUFACTURER_COMPANY_NAME`, `MODEL_PART_NAME`, `REVISION_CODE`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `DOCUMENT_NUMBER` | 6,641 | 6,603 | 0 | 0 | 42,432 | **100.0%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-KVE-E-HX-2334-00001`; `JDAW-0471000-B01-00001` → `JDAW-KVE-E-IN-7739-00003`; `JDAW-0471000-B01-00001` → `JDAW-KVE-E-IN-7739-00003` |

#### Row-Level Diff Examples

ℹ️ No row-level differences detected in shared rows.

---

### 022 — Doc→Purchase Order (EIS-420)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 5,808 | 4,334 | **-25.4%** ⚠️ |
| New rows (in B only) | — | 0 | |
| Removed rows (in A only) | 1,474 | — | |
| Changed rows (same PK) | — | — | 0 |

> Primary key used: `DOCUMENT_NUMBER`, `PO_CODE`

#### Column Differences

**Only in A (A37):** `COMPANY_NAME`, `PLANT_CODE`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `DOCUMENT_NUMBER` | 5,715 | 4,280 | 0 | 0 | 302,570 | **98.6%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-0471000-A02-00001`; `JDAW-0471000-A01-00001` → `JDAW-0471000-A04-00001`; `JDAW-0471000-A01-00001` → `JDAW-0471000-B01-00001` |
| `PO_CODE` | 193 | 99 | 0 | 0 | 212 | 4.7% | `JA-BE541-0004` → `JA-BE541-0001`; `JA-BL761-2003` → `JA-BL761-2000`; `JA-BL761-2002` → `JA-BL762-2002` |
| `REVISION_CODE` | 35 | 32 | 3 | 1 | 0 | 0.0% |  |

#### Row-Level Diff Examples

ℹ️ No row-level differences detected in shared rows.

---

### 023 — Doc→Plant (EIS-409)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 13,477 | 13,477 | +0.0% |
| New rows (in B only) | — | 0 | |
| Removed rows (in A only) | 0 | — | |
| Changed rows (same PK) | — | — | 0 |

> Primary key used: `DOCUMENT_NUMBER`

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `DOCUMENT_NUMBER` | 13,477 | 13,477 | 0 | 0 | 0 | 0.0% |  |
| `PLANT_CODE` | 2 | 2 | 0 | 0 | 0 | 0.0% |  |

#### Row-Level Diff Examples

ℹ️ No row-level differences detected in shared rows.

---

### 024 — Doc→Site (EIS-408)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 13,477 | 13,477 | +0.0% |
| New rows (in B only) | — | 0 | |
| Removed rows (in A only) | 0 | — | |
| Changed rows (same PK) | — | — | 13,477 |

> Primary key used: `DOCUMENT_NUMBER`

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `SITE_CODE` | 2 | 1 | 0 | 0 | 13,477 | **100.0%** ⚠️ | `JD` → `SWA`; `JD` → `SWA`; `JD` → `SWA` |
| `DOCUMENT_NUMBER` | 13,477 | 13,477 | 0 | 0 | 0 | 0.0% |  |

#### Row-Level Diff Examples

> Rows matched by PK: `DOCUMENT_NUMBER`

**Example 1**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-0471000-A01-00001`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `SITE_CODE` | `JD` | `SWA` |

**Example 2**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-0471000-A02-00001`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `SITE_CODE` | `JD` | `SWA` |

**Example 3**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-0471000-A04-00001`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `SITE_CODE` | `JD` | `SWA` |

**Example 4**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-0471000-B01-00001`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `SITE_CODE` | `JD` | `SWA` |

**Example 5**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-0471000-B01-00002`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `SITE_CODE` | `JD` | `SWA` |

---
