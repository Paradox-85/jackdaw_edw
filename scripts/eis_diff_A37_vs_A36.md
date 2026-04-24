# EIS Export Revision Diff Report

**Folder A (new):** `C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\Apr-26\CSV\eis_export_A37_20260423_0801`  
**Folder B (baseline):** `C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\Mar-26\CSV`

**Files compared:** 17

## Summary

| Seq | Register | Rev A | Rev B | Rows A | Rows B | Δ Rows | % | ⚠️ |
|-----|----------|-------|-------|-------:|-------:|-------:|--:|---|
| 001 | Site Register (EIS-201) | A37 | A36 | 203 | 205 | +2 | +1.0% | ⚠️ |
| 002 | Plant Register (EIS-202) | A37 | A36 | 37 | 37 | +0 | +0.0% | ⚠️ |
| 003 | Tag Register (EIS-205) | A37 | A36 | 23,073 | 23,026 | -47 | -0.2% | ⚠️ |
| 004 | Equipment Register (EIS-206) | A37 | A36 | 23,073 | 23,026 | -47 | -0.2% | ⚠️ |
| 005 | Model Part Register (EIS-209) | A37 | A36 | 1,254 | 1,473 | +219 | +17.5% | ⚠️ |
| 006 | Tag Physical Connections (EIS-212) | A37 | A36 | 3,790 | 4,502 | +712 | +18.8% | ⚠️ |
| 009 | Tag Class Properties (EIS-307) | A37 | A36 | 981 | 1,030 | +49 | +5.0% | ✅ |
| 010 | Tag Property Values (EIS-303) | A37 | A36 | 166,464 | 116,111 | -50,353 | -30.2% | ⚠️ |
| 011 | Equipment Property Values (EIS-301) | A37 | A36 | 90,101 | 84,670 | -5,431 | -6.0% | ⚠️ |
| 016 | Doc→Tag (EIS-412) | A37 | A36 | 494,803 | 405,564 | -89,239 | -18.0% | ⚠️ |
| 017 | Area Register / Doc→Area (EIS-203/411) | A37 | A36 | 20,007 | 18,856 | -1,151 | -5.8% | ⚠️ |
| 018 | Process Unit Register / Doc→ProcessUnit (EIS-204/410) | A37 | A36 | 17,756 | 19,262 | +1,506 | +8.5% | ⚠️ |
| 019 | Doc→Equipment (EIS-413) | A37 | A36 | 494,250 | 405,564 | -88,686 | -17.9% | ⚠️ |
| 020 | Doc→Model Part (EIS-414) | A37 | A36 | 46,569 | 43,656 | -2,913 | -6.3% | ⚠️ |
| 022 | Doc→Purchase Order (EIS-420) | A37 | A36 | 5,596 | 4,334 | -1,262 | -22.6% | ⚠️ |
| 023 | Doc→Plant (EIS-409) | A37 | A36 | 13,265 | 13,477 | +212 | +1.6% | ✅ |
| 024 | Doc→Site (EIS-408) | A37 | A36 | 13,265 | 13,477 | +212 | +1.6% | ✅ |
| 008 | Purchase Order Register (EIS-214) | — | — | — | — | — | — | 🆕 only in A |

---

## Detailed Diff per File

### 001 — Site Register (EIS-201)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 203 | 205 | +1.0% |

> ⚠️ No PK columns available for row-identity analysis.

#### Column Differences

**Only in B (A36):** `ACTION`, `PLANT_REF`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `AREA_NAME` | 152 | 154 | 0 | 0 | 114 | **56.2%** ⚠️ | `CELLAR DECK (GENERAL)` → `CELLAR DECK`; `STAIR CASE (SW)` → `CELLAR DECK (GENERAL)`; `LAY DOWN AREA (SE)` → `STAIR CASE (SW)` |
| `AREA_CODE` | 203 | 203 | 0 | 0 | 113 | **55.7%** ⚠️ | `P101` → `P100`; `P102` → `P101`; `P104` → `P102` |
| `MAIN_AREA_CODE` | 104 | 104 | 0 | 0 | 96 | **47.3%** ⚠️ | `P200` → `P100`; `P300` → `P200`; `U100` → `P300` |
| `PLANT_CODE` | 2 | 2 | 0 | 0 | 2 | 1.0% | `SWA` → `JDA`; `SWA` → `JDA` |

#### Row-Level Diff Examples

> ⚠️ No shared PK — rows matched **positionally** (row N in A vs row N in B). May reflect reordering rather than true changes.

**Example 1**
  - 🔢 Row #118 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `SWA` | `JDA` |
  | `AREA_CODE` | `SWAASW` | `Z200` |
  | `AREA_NAME` | `ACCOMODATION STAIRWELL` | `CRANE` |
  | `MAIN_AREA_CODE` | `SWAASW` | `Z200` |

**Example 2**
  - 🔢 Row #117 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `SWA` | `JDA` |
  | `AREA_CODE` | `SWA` | `Z100` |
  | `AREA_NAME` | `SHEARWATER ALPHA` | `BLAST WALL` |
  | `MAIN_AREA_CODE` | `SWA` | `Z100` |

**Example 3**
  - 🔢 Row #123 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `AREA_CODE` | `SWACMR` | `SWA-CM2` |
  | `AREA_NAME` | `CABINS MODULE ROOF` | `CABINS MODULE LEVEL 2` |
  | `MAIN_AREA_CODE` | `SWACMR` | `SWA-CM2` |

**Example 4**
  - 🔢 Row #124 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `AREA_CODE` | `SWACOL` | `SWA-CM3` |
  | `AREA_NAME` | `WESTERN EXTERNAL COLUMN (ALL LEVELS)` | `CABINS MODULE LEVEL 3` |
  | `MAIN_AREA_CODE` | `SWACOL` | `SWA-CM3` |

**Example 5**
  - 🔢 Row #122 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `AREA_CODE` | `SWACM3` | `SWA-CM1` |
  | `AREA_NAME` | `CABINS MODULE LEVEL 3` | `CABINS MODULE LEVEL 1` |
  | `MAIN_AREA_CODE` | `SWACM3` | `SWA-CM1` |

---

### 002 — Plant Register (EIS-202)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 37 | 37 | +0.0% |
| New rows (in B only) | — | 0 | |
| Removed rows (in A only) | 0 | — | |
| Changed rows (same PK) | — | — | 1,334 |

> Primary key used: `PLANT_CODE`

#### Column Differences

**Only in B (A36):** `ACTION`, `COUNT_OF_TAGS`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `PROCESS_UNIT_CODE` | 37 | 37 | 0 | 0 | 1,332 | **97.3%** ⚠️ | `01` → `02`; `01` → `06`; `01` → `08` |
| `PROCESS_UNIT_NAME` | 34 | 34 | 0 | 0 | 1,328 | **97.0%** ⚠️ | `WELLS AND FLOWLINES.` → `MANIFOLD AND EXPORT`; `WELLS AND FLOWLINES.` → `WELLHEADS AND MANIFOLDS`; `WELLS AND FLOWLINES.` → `WELLHEADS AND MANIFOLDS` |
| `PLANT_CODE` | 1 | 1 | 0 | 0 | 0 | 0.0% |  |

#### Row-Level Diff Examples

> Rows matched by PK: `PLANT_CODE`

**Example 1**
  - 🔑 `PLANT_CODE` = `JDA`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PROCESS_UNIT_CODE` | `99` | `88` |
  | `PROCESS_UNIT_NAME` | `DRILLING` | `UTILITIES - HVAC` |

**Example 2**
  - 🔑 `PLANT_CODE` = `JDA`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PROCESS_UNIT_CODE` | `01` | `02` |
  | `PROCESS_UNIT_NAME` | `WELLS AND FLOWLINES.` | `MANIFOLD AND EXPORT` |

**Example 3**
  - 🔑 `PLANT_CODE` = `JDA`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PROCESS_UNIT_CODE` | `01` | `06` |
  | `PROCESS_UNIT_NAME` | `WELLS AND FLOWLINES.` | `WELLHEADS AND MANIFOLDS` |

**Example 4**
  - 🔑 `PLANT_CODE` = `JDA`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PROCESS_UNIT_CODE` | `01` | `08` |
  | `PROCESS_UNIT_NAME` | `WELLS AND FLOWLINES.` | `WELLHEADS AND MANIFOLDS` |

**Example 5**
  - 🔑 `PLANT_CODE` = `JDA`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PROCESS_UNIT_CODE` | `01` | `29` |
  | `PROCESS_UNIT_NAME` | `WELLS AND FLOWLINES.` | `GAS PRODUCTION, PROCESS, HANDLING AND EXPORT` |

---

### 003 — Tag Register (EIS-205)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 23,073 | 23,026 | -0.2% |
| New rows (in B only) | — | 2 | |
| Removed rows (in A only) | 6 | — | |
| Changed rows (same PK) | — | — | 23,065 |

> Primary key used: `TAG_NAME`

#### Column Differences

**Only in A (A37):** `ACTION_DATE`, `SAFETY_CRITICAL_ITEM_GROUP`, `SAFETY_CRITICAL_ITEM_REASON_AWARDED`

**Only in B (A36):** `ID`, `SAFETY_CRITICAL_ITEM _GROUP`, `SAFETY_CRITICAL_ITEM _REASON_AWARDED`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `TAG_NAME` | 23,030 | 23,026 | 0 | 0 | 23,026 | **100.0%** ⚠️ | `01MV-0075` → `001-01EBD-001-001RE1`; `72-LI-00X11` → `01MV-0075`; `72-PDI-000X3` → `72-LI-00X11` |
| `REQUISITION_CODE` | 4,362 | 1 | 13,119 | 0 | 23,065 | **100.0%** ⚠️ | `ART-DUMMY-JDA-79MV-0026` → `NA`; `` → `NA`; `` → `NA` |
| `DESIGNED_BY_COMPANY_NAME` | 2 | 4 | 20,997 | 4 | 20,985 | **91.0%** ⚠️ | `` → `RAM`; `` → `RAM`; `` → `RAM` |
| `COMPANY_NAME` | 4 | 6 | 5,578 | 4,340 | 9,776 | **42.4%** ⚠️ | `AKER SOLUTIONS VERDAL` → `AKER SOLUTIONS  VERDAL`; `AKER SOLUTIONS VERDAL` → `AKER SOLUTIONS  VERDAL`; `AKER SOLUTIONS VERDAL` → `AKER SOLUTIONS  VERDAL` |
| `ACTION_STATUS` | 2 | 4 | 0 | 0 | 5,482 | **23.8%** ⚠️ | `No Changes` → `Modified`; `No Changes` → `Modified`; `No Changes` → `Modified` |
| `PROCESS_UNIT_CODE` | 33 | 38 | 3,480 | 331 | 3,148 | **13.6%** ⚠️ | `` → `NA`; `` → `NA`; `` → `NA` |
| `TAG_DESCRIPTION` | 10,715 | 10,563 | 366 | 366 | 3,057 | **13.3%** ⚠️ | `NETWORK AND SERVER CABINET; SHEARWATER` → `NETWORK AND SERVER CABINET, SHEARWATER`; `CRITICAL ACTION PANEL; SHEARWATER` → `CRITICAL ACTION PANEL, SHEARWATER`; `ESD CONTROLLER CABINET; SHEARWATER` → `ESD CONTROLLER CABINET, SHEARWATER` |
| `PO_CODE` | 144 | 145 | 5,578 | 4,340 | 1,220 | 5.3% | `` → `NA`; `` → `NA`; `` → `NA` |
| `AREA_CODE` | 24 | 26 | 485 | 0 | 506 | 2.2% | `` → `SWA-UL2`; `` → `SWA-UL1`; `` → `SWA-UL2` |
| `PARENT_TAG_NAME` | 3,767 | 3,753 | 5,833 | 5,885 | 140 | 0.6% | `JDA-8"-P01203-LD30-N` → ``; `JDA-8"-P01303-LD30-N` → ``; `JDA-8"-P01603-LD30-N` → `` |
| `TAG_CLASS_NAME` | 223 | 216 | 56 | 54 | 138 | 0.6% | `RELATIVE PRESSURE TRANSMITTER` → `PRESSURE TRANSMITTER`; `RELATIVE PRESSURE TRANSMITTER` → `PRESSURE TRANSMITTER`; `RELATIVE PRESSURE TRANSMITTER` → `PRESSURE TRANSMITTER` |
| `TAG_STATUS` | 6 | 6 | 1 | 1 | 34 | 0.1% | `VOID` → `ACTIVE`; `VOID` → `ACTIVE`; `VOID` → `ACTIVE` |
| `SAFETY_CRITICAL_ITEM` | 3 | 3 | 2,451 | 2,446 | 22 | 0.1% | `NO` → `YES`; `NO` → `YES`; `NO` → `YES` |
| `PLANT_CODE` | 3 | 5 | 3 | 0 | 3 | 0.0% | `` → `001`; `` → `JDE`; `` → `tes` |
| `PRODUCTION_CRITICAL_ITEM` | 3 | 3 | 22,757 | 22,710 | 0 | 0.0% |  |

#### Row-Level Diff Examples

> Rows matched by PK: `TAG_NAME`

**Example 1**
  - 🔑 `TAG_NAME` = `JDA-4"-D61836-13842-N`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PARENT_TAG_NAME` | `` | `JDA-3"-D61842-13842-N` |
  | `AREA_CODE` | `P300` | `P100` |
  | `TAG_CLASS_NAME` | `PIPELINE` | `PIPE` |
  | `TAG_STATUS` | `VOID` | `ACTIVE` |
  | `REQUISITION_CODE` | `` | `NA` |
  | `DESIGNED_BY_COMPANY_NAME` | `` | `LEIR` |
  | `COMPANY_NAME` | `` | `LEIRVIK AS` |
  | `PO_CODE` | `` | `ZL-108864` |
  | `SAFETY_CRITICAL_ITEM` | `NO` | `YES` |
  | `TAG_DESCRIPTION` | `PIPE` | `OPEN DRAIN LQ` |
  | `ACTION_STATUS` | `Deleted` | `No Changes` |

**Example 2**
  - 🔑 `TAG_NAME` = `JDA-2"-W46965-13842-2F`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PARENT_TAG_NAME` | `` | `JDA-2"-W46016-13842-2F` |
  | `AREA_CODE` | `P300` | `L400` |
  | `TAG_CLASS_NAME` | `PIPELINE` | `PIPE` |
  | `TAG_STATUS` | `VOID` | `ACTIVE` |
  | `REQUISITION_CODE` | `` | `NA` |
  | `DESIGNED_BY_COMPANY_NAME` | `` | `LEIR` |
  | `COMPANY_NAME` | `` | `LEIRVIK AS` |
  | `PO_CODE` | `` | `ZL-108862` |
  | `TAG_DESCRIPTION` | `PIPE` | `FRESHWATER DISTRIBUTION LQ L300` |
  | `ACTION_STATUS` | `Deleted` | `No Changes` |

**Example 3**
  - 🔑 `TAG_NAME` = `JDA-2"-W46030-13842-2F`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PARENT_TAG_NAME` | `` | `JDA-2"-W46016-13842-2F` |
  | `AREA_CODE` | `P300` | `L400` |
  | `TAG_CLASS_NAME` | `PIPELINE` | `PIPE` |
  | `TAG_STATUS` | `VOID` | `ACTIVE` |
  | `REQUISITION_CODE` | `` | `NA` |
  | `DESIGNED_BY_COMPANY_NAME` | `` | `LEIR` |
  | `COMPANY_NAME` | `` | `LEIRVIK AS` |
  | `PO_CODE` | `` | `ZL-108862` |
  | `TAG_DESCRIPTION` | `FRESHWATER FLUID [WATER] FROM [JDA-2"-W46016-13842-2F]` | `FRESHWATER SYSTEM` |
  | `ACTION_STATUS` | `Deleted` | `No Changes` |

**Example 4**
  - 🔑 `TAG_NAME` = `JDA-2"-D61837-13842-N`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PARENT_TAG_NAME` | `` | `JDA-1"-D61093-13842-N` |
  | `TAG_CLASS_NAME` | `PIPELINE` | `PIPE` |
  | `TAG_STATUS` | `VOID` | `ACTIVE` |
  | `REQUISITION_CODE` | `` | `NA` |
  | `DESIGNED_BY_COMPANY_NAME` | `` | `LEIR` |
  | `COMPANY_NAME` | `` | `LEIRVIK AS` |
  | `PO_CODE` | `` | `ZL-108864` |
  | `SAFETY_CRITICAL_ITEM` | `NO` | `YES` |
  | `TAG_DESCRIPTION` | `OPEN DRAIN FLUID [DRAIN] FROM JDA-A-84001A [DIESEL GENERATOR PACKAGE] TO /JDA-4…` | `OPEN DRAIN LQ` |
  | `ACTION_STATUS` | `Deleted` | `No Changes` |

**Example 5**
  - 🔑 `TAG_NAME` = `JDA-2"-D61838-13842-N`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PARENT_TAG_NAME` | `` | `JDA-1"-D61096-13842-N` |
  | `TAG_CLASS_NAME` | `PIPELINE` | `PIPE` |
  | `TAG_STATUS` | `VOID` | `ACTIVE` |
  | `REQUISITION_CODE` | `` | `NA` |
  | `DESIGNED_BY_COMPANY_NAME` | `` | `LEIR` |
  | `COMPANY_NAME` | `` | `LEIRVIK AS` |
  | `PO_CODE` | `` | `ZL-108864` |
  | `SAFETY_CRITICAL_ITEM` | `NO` | `YES` |
  | `TAG_DESCRIPTION` | `OPEN DRAIN FLUID [DRAIN] FROM TO` | `OPEN DRAIN LQ` |
  | `ACTION_STATUS` | `Deleted` | `No Changes` |

---

### 004 — Equipment Register (EIS-206)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 23,073 | 23,026 | -0.2% |
| New rows (in B only) | — | 2 | |
| Removed rows (in A only) | 6 | — | |
| Changed rows (same PK) | — | — | 23,065 |

> Primary key used: `EQUIPMENT_NUMBER`

#### Column Differences

**Only in A (A37):** `ACTION_DATE`

**Only in B (A36):** `ID`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `EQUIPMENT_NUMBER` | 23,030 | 23,026 | 0 | 0 | 23,026 | **100.0%** ⚠️ | `Equip_01MV-0075` → `Equip_001-01EBD-001-001RE1`; `Equip_72-LI-00X11` → `Equip_01MV-0075`; `Equip_72-PDI-000X3` → `Equip_72-LI-00X11` |
| `WARRANTY_END_DATE` | 1 | 3 | 0 | 22,711 | 23,065 | **100.0%** ⚠️ | `NA` → ``; `NA` → ``; `NA` → `` |
| `MODEL_PART_NAME` | 1,256 | 1,382 | 14,310 | 5,812 | 8,728 | **37.8%** ⚠️ | `` → `095495`; `` → `025316`; `` → `NA` |
| `PART_OF` | 94 | 95 | 5,578 | 4,340 | 7,345 | **31.8%** ⚠️ | `ZLEI3H10` → `Z-LEI-3H10`; `ZLEI3E19` → `Z-LEI-3E19`; `ZLEI3E19` → `Z-LEI-3E19` |
| `MANUFACTURER_COMPANY_NAME` | 425 | 452 | 10,078 | 3,105 | 7,015 | **30.4%** ⚠️ | `` → `INTERNAL WIRING`; `` → `INTERNAL WIRING`; `` → `INTERNAL WIRING` |
| `ACTION_STATUS` | 2 | 4 | 0 | 0 | 5,482 | **23.8%** ⚠️ | `No Changes` → `Modified`; `No Changes` → `Modified`; `No Changes` → `Modified` |
| `EQUIPMENT_DESCRIPTION` | 10,717 | 10,563 | 366 | 366 | 3,041 | **13.2%** ⚠️ | `NETWORK AND SERVER CABINET; SHEARWATER` → `NETWORK AND SERVER CABINET, SHEARWATER`; `CRITICAL ACTION PANEL; SHEARWATER` → `CRITICAL ACTION PANEL, SHEARWATER`; `ESD CONTROLLER CABINET; SHEARWATER` → `ESD CONTROLLER CABINET, SHEARWATER` |
| `VENDOR_COMPANY_NAME` | 42 | 47 | 6,428 | 4,340 | 2,087 | 9.0% | `FMC KONGSBERG SUBSEA AS` → `FMC Kongsberg Subsea AS`; `` → `NA`; `` → `NA` |
| `PURCHASE_DATE` | 118 | 119 | 5,578 | 4,340 | 1,220 | 5.3% | `` → `NA`; `` → `NA`; `` → `NA` |
| `MANUFACTURER_SERIAL_NUMBER` | 2,598 | 2,598 | 2,852 | 2,858 | 486 | 2.1% | `CPI-NA` → `TBC`; `CPI-NA` → `TBC`; `CPI-NA` → `TBC` |
| `INSTALLATION_DATE` | 2 | 4 | 23,009 | 22,664 | 362 | 1.6% | `2023-08-01` → `01-08-2023`; `2023-08-01` → `01-08-2023`; `` → `TBC` |
| `EQUIPMENT_CLASS_NAME` | 223 | 216 | 56 | 54 | 138 | 0.6% | `RELATIVE PRESSURE TRANSMITTER` → `PRESSURE TRANSMITTER`; `RELATIVE PRESSURE TRANSMITTER` → `PRESSURE TRANSMITTER`; `RELATIVE PRESSURE TRANSMITTER` → `PRESSURE TRANSMITTER` |
| `PLANT_CODE` | 3 | 5 | 3 | 0 | 3 | 0.0% | `` → `001`; `` → `JDE`; `` → `tes` |
| `TAG_NAME` | 23,030 | 23,026 | 0 | 0 | 0 | 0.0% |  |
| `STARTUP_DATE` | 1 | 1 | 0 | 0 | 0 | 0.0% |  |
| `PRICE` | 1 | 1 | 0 | 0 | 0 | 0.0% |  |
| `TECHIDENTNO` | 1 | 1 | 0 | 0 | 0 | 0.0% |  |
| `ALIAS` | 1 | 1 | 0 | 0 | 0 | 0.0% |  |

#### Row-Level Diff Examples

> Rows matched by PK: `EQUIPMENT_NUMBER`

**Example 1**
  - 🔑 `EQUIPMENT_NUMBER` = `Equip_JDA-4"-D61836-13842-N`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `EQUIPMENT_CLASS_NAME` | `PIPELINE` | `PIPE` |
  | `MANUFACTURER_COMPANY_NAME` | `` | `NA` |
  | `MODEL_PART_NAME` | `` | `NA` |
  | `PURCHASE_DATE` | `` | `22.02.2023` |
  | `VENDOR_COMPANY_NAME` | `` | `LEIRVIK AS` |
  | `WARRANTY_END_DATE` | `NA` | `` |
  | `PART_OF` | `` | `Z-LEI-3L20` |
  | `EQUIPMENT_DESCRIPTION` | `PIPE` | `OPEN DRAIN LQ` |
  | `ACTION_STATUS` | `Deleted` | `No Changes` |

**Example 2**
  - 🔑 `EQUIPMENT_NUMBER` = `Equip_JDA-2"-W46965-13842-2F`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `EQUIPMENT_CLASS_NAME` | `PIPELINE` | `PIPE` |
  | `MANUFACTURER_COMPANY_NAME` | `` | `NA` |
  | `MODEL_PART_NAME` | `` | `NA` |
  | `PURCHASE_DATE` | `` | `20.03.2023` |
  | `VENDOR_COMPANY_NAME` | `` | `LEIRVIK AS` |
  | `WARRANTY_END_DATE` | `NA` | `` |
  | `PART_OF` | `` | `Z-LEI-3L16` |
  | `EQUIPMENT_DESCRIPTION` | `PIPE` | `FRESHWATER DISTRIBUTION LQ L300` |
  | `ACTION_STATUS` | `Deleted` | `No Changes` |

**Example 3**
  - 🔑 `EQUIPMENT_NUMBER` = `Equip_JDA-2"-W46030-13842-2F`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `EQUIPMENT_CLASS_NAME` | `PIPELINE` | `PIPE` |
  | `MANUFACTURER_COMPANY_NAME` | `` | `NA` |
  | `MODEL_PART_NAME` | `` | `NA` |
  | `PURCHASE_DATE` | `` | `20.03.2023` |
  | `VENDOR_COMPANY_NAME` | `` | `LEIRVIK AS` |
  | `WARRANTY_END_DATE` | `NA` | `` |
  | `PART_OF` | `` | `Z-LEI-3L16` |
  | `EQUIPMENT_DESCRIPTION` | `FRESHWATER FLUID [WATER] FROM [JDA-2"-W46016-13842-2F]` | `FRESHWATER SYSTEM` |
  | `ACTION_STATUS` | `Deleted` | `No Changes` |

**Example 4**
  - 🔑 `EQUIPMENT_NUMBER` = `Equip_JDA-2"-W46004-13842-2F`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `EQUIPMENT_CLASS_NAME` | `PIPELINE` | `PIPE` |
  | `MANUFACTURER_COMPANY_NAME` | `` | `NA` |
  | `MODEL_PART_NAME` | `` | `NA` |
  | `PURCHASE_DATE` | `` | `20.03.2023` |
  | `VENDOR_COMPANY_NAME` | `` | `LEIRVIK AS` |
  | `WARRANTY_END_DATE` | `NA` | `` |
  | `PART_OF` | `` | `Z-LEI-3L16` |
  | `EQUIPMENT_DESCRIPTION` | `PIPE` | `FRESHWATER SYSTEM` |
  | `ACTION_STATUS` | `Deleted` | `No Changes` |

**Example 5**
  - 🔑 `EQUIPMENT_NUMBER` = `Equip_JDA-2"-D61837-13842-N`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `EQUIPMENT_CLASS_NAME` | `PIPELINE` | `PIPE` |
  | `MANUFACTURER_COMPANY_NAME` | `` | `NA` |
  | `MODEL_PART_NAME` | `` | `NA` |
  | `PURCHASE_DATE` | `` | `22.02.2023` |
  | `VENDOR_COMPANY_NAME` | `` | `LEIRVIK AS` |
  | `WARRANTY_END_DATE` | `NA` | `` |
  | `PART_OF` | `` | `Z-LEI-3L20` |
  | `EQUIPMENT_DESCRIPTION` | `OPEN DRAIN FLUID [DRAIN] FROM JDA-A-84001A [DIESEL GENERATOR PACKAGE] TO /JDA-4…` | `OPEN DRAIN LQ` |
  | `ACTION_STATUS` | `Deleted` | `No Changes` |

---

### 005 — Model Part Register (EIS-209)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 1,254 | 1,473 | **+17.5%** ⚠️ |

> ⚠️ No PK columns available for row-identity analysis.

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `MODEL_PART_NAME` | 1,254 | 1,379 | 0 | 0 | 1,254 | **100.0%** ⚠️ | `212102` → `PVG-EX`; `20110516` → `095495`; `T-5-EX-L4` → `61-1100.0` |
| `MODEL_DESCRIPTION` | 1,254 | 1 | 0 | 0 | 1,254 | **100.0%** ⚠️ | `MENTO AS 212102 - HOSE LOADING STATION. EXPLOSION PROTECTION (EX): EX NA; IP UNKNOWN; OFFSHORE ENVIRONMENTS HANDLING; 2 X 4' LOADING HOSES. (SOURCE: INTERNAL CATALOG + LINKEDIN.COM/COMPANY/MENTO-AS + MOUSER.COM/PRODUCTDETAIL/AMPHENOL-RF/212102)` → `TBD`; `**DRAKA NORSK KABEL 20110516 - POWER CABLE** HALOGEN-FREE; FIRE-RESISTANT; FLAME RETARDANT AND MUD-RESISTANT INSTRUMENTATION CABLE; 2X2;5+E SQMM BLACK; P5/P12/P105; BFOU M 0;6/1KV 3G 2;5MM2; SUITABLE FOR SHIPS; OFFSHORE UNITS; AND FIXED INSTALLATIONS FOR POWER; CONTROL; AND LIGHTING; EMERGENCY; AND CRITICAL SYSTEMS. (SOURCE: INTERNAL CATALOG + COMPONENTS.SEMCOMARITIME.COM)` → `TBD`; `SHANGHAI CHENZHU T-5-EX-L4 - CONTROL DEVICE. EX IA; IP 20. (SOURCE: INTERNAL CATALOG + .)` → `TBD` |
| `MANUFACTURER_COMPANY_NAME` | 390 | 425 | 1 | 5 | 1,241 | **99.0%** ⚠️ | `MENTO AS` → `DANFOSS`; `DRAKA NORSK KABEL` → `HERNIS`; `SHANGHAI CHENZHU` → `EAO` |
| `EQUIPMENT_CLASS_NAME` | 187 | 198 | 0 | 0 | 1,232 | **98.2%** ⚠️ | `HOSE` → `RM NEEDLE VALVE`; `POWER CABLE` → `ACCESS CONTROL SENSOR`; `LIGHTNING ARRESTOR` → `PUSH BUTTON` |

#### Row-Level Diff Examples

> ⚠️ No shared PK — rows matched **positionally** (row N in A vs row N in B). May reflect reordering rather than true changes.

**Example 1**
  - 🔢 Row #1253 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `MANUFACTURER_COMPANY_NAME` | `GAM-PIANA` | `FUTURE` |
  | `MODEL_PART_NAME` | `GAM_32750_32` | `FUTURE` |
  | `MODEL_DESCRIPTION` | `HERNIS GAM-PIANA GAM_32750_32 - BEND 60 DEG 5D 8'. ASTM A815 UNS S32750; 34.1MM…` | `TBD` |
  | `EQUIPMENT_CLASS_NAME` | `PIPE BEND` | `UMBILICAL` |

**Example 2**
  - 🔢 Row #0 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `MANUFACTURER_COMPANY_NAME` | `MENTO AS` | `DANFOSS` |
  | `MODEL_PART_NAME` | `212102` | `PVG-EX` |
  | `MODEL_DESCRIPTION` | `MENTO AS 212102 - HOSE LOADING STATION. EXPLOSION PROTECTION (EX): EX NA; IP UN…` | `TBD` |
  | `EQUIPMENT_CLASS_NAME` | `HOSE` | `RM NEEDLE VALVE` |

**Example 3**
  - 🔢 Row #1 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `MANUFACTURER_COMPANY_NAME` | `DRAKA NORSK KABEL` | `HERNIS` |
  | `MODEL_PART_NAME` | `20110516` | `095495` |
  | `MODEL_DESCRIPTION` | `**DRAKA NORSK KABEL 20110516 - POWER CABLE** HALOGEN-FREE; FIRE-RESISTANT; FLAM…` | `TBD` |
  | `EQUIPMENT_CLASS_NAME` | `POWER CABLE` | `ACCESS CONTROL SENSOR` |

**Example 4**
  - 🔢 Row #2 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `MANUFACTURER_COMPANY_NAME` | `SHANGHAI CHENZHU` | `EAO` |
  | `MODEL_PART_NAME` | `T-5-EX-L4` | `61-1100.0` |
  | `MODEL_DESCRIPTION` | `SHANGHAI CHENZHU T-5-EX-L4 - CONTROL DEVICE. EX IA; IP 20. (SOURCE: INTERNAL CA…` | `TBD` |
  | `EQUIPMENT_CLASS_NAME` | `LIGHTNING ARRESTOR` | `PUSH BUTTON` |

**Example 5**
  - 🔢 Row #3 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `MANUFACTURER_COMPANY_NAME` | `SAVAL` | `HP` |
  | `MODEL_PART_NAME` | `COMPACT F3 FLOURIDE FREE EXTINGUISHER (ABF)` | `PRODESK 400 DM` |
  | `MODEL_DESCRIPTION` | `SAVAL COMPACT F3 FLOURIDE FREE EXTINGUISHER (ABF) - FOAM EXTINGUISHER. IP RATIN…` | `TBD` |
  | `EQUIPMENT_CLASS_NAME` | `FIRE EXTINGUISHER` | `COMPUTER` |

---

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
| Total rows | 981 | 1,030 | +5.0% |
| New rows (in B only) | — | 143 | |
| Removed rows (in A only) | 141 | — | |
| Changed rows (same PK) | — | — | 0 |

> Primary key used: `TAG_CLASS_NAME`

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `TAG_CLASS_NAME` | 141 | 143 | 0 | 0 | 981 | **100.0%** ⚠️ | `ACCESS CONTROL SENSOR` → `control panel`; `ACCESS CONTROL SENSOR` → `control panel`; `ACCESS CONTROL SENSOR` → `control panel` |
| `TAG_PROPERTY_NAME` | 184 | 181 | 0 | 0 | 0 | 0.0% |  |

#### Row-Level Diff Examples

ℹ️ No row-level differences detected in shared rows.

---

### 010 — Tag Property Values (EIS-303)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 166,464 | 116,111 | **-30.2%** ⚠️ |
| New rows (in B only) | — | 116,041 | |
| Removed rows (in A only) | 97,837 | — | |
| Changed rows (same PK) | — | — | 0 |

> Primary key used: `TAG_NAME`, `PROPERTY_NAME`

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `PROPERTY_NAME` | 178 | 181 | 0 | 0 | 3,548,969 | **100.0%** ⚠️ | `ACTUAL LENGTH` → `from tag name`; `ACTUAL LENGTH` → `to tag name`; `ACTUAL LENGTH` → `cable specification` |
| `PLANT_CODE` | 2 | 2 | 0 | 0 | 0 | 0.0% |  |
| `TAG_NAME` | 14,279 | 15,475 | 0 | 0 | 0 | 0.0% |  |
| `PROPERTY_VALUE` | 2,460 | 5,599 | 280 | 0 | 0 | 0.0% |  |
| `PROPERTY_VALUE_UOM` | 66 | 53 | 79,806 | 80,834 | 0 | 0.0% |  |

#### Row-Level Diff Examples

ℹ️ No row-level differences detected in shared rows.

---

### 011 — Equipment Property Values (EIS-301)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 90,101 | 84,670 | **-6.0%** ⚠️ |
| New rows (in B only) | — | 84,670 | |
| Removed rows (in A only) | 61,552 | — | |
| Changed rows (same PK) | — | — | 0 |

> Primary key used: `EQUIPMENT_NUMBER`, `PROPERTY_NAME`

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `PROPERTY_NAME` | 213 | 212 | 0 | 0 | 1,071,926 | **100.0%** ⚠️ | `WEIGHT NET` → `weight net`; `WEIGHT NET` → `actual length`; `WEIGHT NET` → `weight net` |
| `PLANT_CODE` | 2 | 2 | 0 | 0 | 0 | 0.0% |  |
| `EQUIPMENT_NUMBER` | 11,968 | 12,990 | 0 | 0 | 0 | 0.0% |  |
| `PROPERTY_VALUE` | 3,046 | 4,218 | 639 | 0 | 0 | 0.0% |  |
| `PROPERTY_VALUE_UOM` | 79 | 31 | 47,135 | 55,347 | 0 | 0.0% |  |

#### Row-Level Diff Examples

ℹ️ No row-level differences detected in shared rows.

---

### 016 — Doc→Tag (EIS-412)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 494,803 | 405,564 | **-18.0%** ⚠️ |
| New rows (in B only) | — | 3,723 | |
| Removed rows (in A only) | 89,288 | — | |
| Changed rows (same PK) | — | — | 250 |

> Primary key used: `DOCUMENT_NUMBER`, `TAG_NAME`

#### Column Differences

**Only in B (A36):** `DOCUMENT_TITLE`, `Match`, `TAG_DOC_ID`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `TAG_NAME` | 17,828 | 17,293 | 0 | 0 | 279,128,620 | **99.9%** ⚠️ | `JDA-01001-CEL` → `JDA-84XB-00147`; `JDA-01001-CEL` → `JDA-84XB-00147-LOOP`; `JDA-01001-CEL` → `JDA-86KSV-02801` |
| `DOCUMENT_NUMBER` | 9,137 | 8,847 | 0 | 0 | 25,648,776 | **98.4%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-KVE-E-EA-1380-00001`; `JDAW-0471000-A01-00001` → `JDAW-KVE-E-EA-4005-00002`; `JDAW-0471000-A01-00001` → `JDAW-KVE-E-EA-4012-00002` |
| `PLANT_CODE` | 2 | 2 | 0 | 0 | 250 | 0.1% | `SWA` → `JDA`; `SWA` → `JDA`; `SWA` → `JDA` |

#### Row-Level Diff Examples

> Rows matched by PK: `DOCUMENT_NUMBER`, `TAG_NAME`

**Example 1**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-KVE-E-PX-2310-00003`; `TAG_NAME` = `SWA.SW-HS-01400`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `SWA` | `JDA` |

**Example 2**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-KVE-E-PX-2310-00003`; `TAG_NAME` = `SWA.SW-HS-11547`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `SWA` | `JDA` |

**Example 3**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-KVE-E-PX-2310-00003`; `TAG_NAME` = `SWA.SW-HS-11548`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `SWA` | `JDA` |

**Example 4**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-KVE-E-PX-2310-00003`; `TAG_NAME` = `SWA.SW-HS-11549`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `SWA` | `JDA` |

**Example 5**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-KVE-E-PX-2310-00003`; `TAG_NAME` = `SWA.SW-HS-11550`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `SWA` | `JDA` |

---

### 017 — Area Register / Doc→Area (EIS-203/411)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 20,007 | 18,856 | **-5.8%** ⚠️ |
| New rows (in B only) | — | 3 | |
| Removed rows (in A only) | 0 | — | |
| Changed rows (same PK) | — | — | 46,969,309 |

> Primary key used: `AREA_CODE`

#### Column Differences

**Only in B (A36):** `DOC_STATUS`, `PLANT_CODE`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `DOCUMENT_NUMBER` | 9,131 | 8,847 | 0 | 0 | 46,969,309 | **100.0%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-0471000-B01-00001`; `JDAW-0471000-A01-00001` → `JDAW-0471000-B01-00002`; `JDAW-0471000-A01-00001` → `JDAW-0471000-B01-00003` |
| `AREA_CODE` | 23 | 26 | 0 | 0 | 16,082 | **85.3%** ⚠️ | `L100` → `U200`; `L200` → `L100`; `L400` → `L100` |

#### Row-Level Diff Examples

> Rows matched by PK: `AREA_CODE`

**Example 1**
  - 🔑 `AREA_CODE` = `L100`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-0471000-A01-00001` | `JDAW-0471000-B01-00001` |

**Example 2**
  - 🔑 `AREA_CODE` = `L100`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-0471000-A01-00001` | `JDAW-0471000-B01-00002` |

**Example 3**
  - 🔑 `AREA_CODE` = `L100`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-0471000-A01-00001` | `JDAW-0471000-B01-00003` |

**Example 4**
  - 🔑 `AREA_CODE` = `L100`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-0471000-A01-00001` | `JDAW-0471000-C03-00001` |

**Example 5**
  - 🔑 `AREA_CODE` = `L100`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-0471000-A01-00001` | `JDAW-0471000-C03-00002` |

---

### 018 — Process Unit Register / Doc→ProcessUnit (EIS-204/410)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 17,756 | 19,262 | **+8.5%** ⚠️ |
| New rows (in B only) | — | 3 | |
| Removed rows (in A only) | 1 | — | |
| Changed rows (same PK) | — | — | 17,644,478 |

> Primary key used: `PROCESS_UNIT_CODE`

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `DOCUMENT_NUMBER` | 8,278 | 8,847 | 0 | 0 | 17,644,445 | **99.9%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-0471000-C10-00001`; `JDAW-0471000-A01-00001` → `JDAW-0471000-C11-00021`; `JDAW-0471000-A01-00001` → `JDAW-0471000-C12-00001` |
| `PROCESS_UNIT_CODE` | 28 | 30 | 0 | 0 | 16,509 | **93.0%** ⚠️ | `83` → `86`; `86` → `84`; `46` → `84` |
| `PLANT_CODE` | 2 | 2 | 0 | 0 | 21,589 | 0.1% | `JDA` → `SWA`; `JDA` → `SWA`; `JDA` → `SWA` |

#### Row-Level Diff Examples

> Rows matched by PK: `PROCESS_UNIT_CODE`

**Example 1**
  - 🔑 `PROCESS_UNIT_CODE` = `56`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-3041000-B01-00001` | `SJDAW-1711000-H08-00015` |
  | `PLANT_CODE` | `JDA` | `SWA` |

**Example 2**
  - 🔑 `PROCESS_UNIT_CODE` = `56`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-3041000-B01-00001` | `SJDAW-KVE-E-IN-4180-00001` |
  | `PLANT_CODE` | `JDA` | `SWA` |

**Example 3**
  - 🔑 `PROCESS_UNIT_CODE` = `56`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-3041000-B01-00001` | `SJDAW-KVE-E-IN-4180-00002` |
  | `PLANT_CODE` | `JDA` | `SWA` |

**Example 4**
  - 🔑 `PROCESS_UNIT_CODE` = `56`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-3041000-B01-00001` | `SJDAW-KVE-E-IN-7770-00001` |
  | `PLANT_CODE` | `JDA` | `SWA` |

**Example 5**
  - 🔑 `PROCESS_UNIT_CODE` = `56`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `DOCUMENT_NUMBER` | `JDAW-3041000-B01-00001` | `SJDAW-KVE-E-IN-8804-00004` |
  | `PLANT_CODE` | `JDA` | `SWA` |

---

### 019 — Doc→Equipment (EIS-413)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 494,250 | 405,564 | **-17.9%** ⚠️ |
| New rows (in B only) | — | 4,273 | |
| Removed rows (in A only) | 89,285 | — | |
| Changed rows (same PK) | — | — | 250 |

> Primary key used: `DOCUMENT_NUMBER`, `EQUIPMENT_NUMBER`

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `EQUIPMENT_NUMBER` | 17,799 | 17,293 | 0 | 0 | 279,022,913 | **99.9%** ⚠️ | `Equip_JDA-01001-CEL` → `Equip_JDA-84XB-00147`; `Equip_JDA-01001-CEL` → `Equip_JDA-84XB-00147-LOOP`; `Equip_JDA-01001-CEL` → `Equip_JDA-86KSV-02801` |
| `DOCUMENT_NUMBER` | 9,127 | 8,847 | 0 | 0 | 25,638,232 | **98.4%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-KVE-E-EA-1380-00001`; `JDAW-0471000-A01-00001` → `JDAW-KVE-E-EA-4005-00002`; `JDAW-0471000-A01-00001` → `JDAW-KVE-E-EA-4012-00002` |
| `PLANT_CODE` | 2 | 2 | 0 | 0 | 250 | 0.1% | `SWA` → `JDA`; `SWA` → `JDA`; `SWA` → `JDA` |

#### Row-Level Diff Examples

> Rows matched by PK: `DOCUMENT_NUMBER`, `EQUIPMENT_NUMBER`

**Example 1**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-KVE-E-PX-2310-00003`; `EQUIPMENT_NUMBER` = `Equip_SWA.SW-HS-01400`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `SWA` | `JDA` |

**Example 2**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-KVE-E-PX-2310-00003`; `EQUIPMENT_NUMBER` = `Equip_SWA.SW-HS-11547`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `SWA` | `JDA` |

**Example 3**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-KVE-E-PX-2310-00003`; `EQUIPMENT_NUMBER` = `Equip_SWA.SW-HS-11548`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `SWA` | `JDA` |

**Example 4**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-KVE-E-PX-2310-00003`; `EQUIPMENT_NUMBER` = `Equip_SWA.SW-HS-11549`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `SWA` | `JDA` |

**Example 5**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-KVE-E-PX-2310-00003`; `EQUIPMENT_NUMBER` = `Equip_SWA.SW-HS-11550`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `SWA` | `JDA` |

---

### 020 — Doc→Model Part (EIS-414)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 46,569 | 43,656 | **-6.3%** ⚠️ |
| New rows (in B only) | — | 176 | |
| Removed rows (in A only) | 497 | — | |
| Changed rows (same PK) | — | — | 0 |

> Primary key used: `DOCUMENT_NUMBER`

#### Column Differences

**Only in A (A37):** `MODEL_PART_CODE`, `PLANT_CODE`

**Only in B (A36):** `MANUFACTURER_COMPANY_NAME`, `MODEL_PART_NAME`, `REVISION_CODE`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `DOCUMENT_NUMBER` | 6,924 | 6,603 | 0 | 0 | 43,633 | **99.9%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-KVE-E-HX-2334-00001`; `JDAW-0471000-A01-00001` → `JDAW-KVE-E-IN-7739-00003`; `JDAW-0471000-A01-00001` → `JDAW-KVE-E-IN-7739-00003` |

#### Row-Level Diff Examples

ℹ️ No row-level differences detected in shared rows.

---

### 022 — Doc→Purchase Order (EIS-420)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 5,596 | 4,334 | **-22.6%** ⚠️ |
| New rows (in B only) | — | 155 | |
| Removed rows (in A only) | 1,417 | — | |
| Changed rows (same PK) | — | — | 40 |

> Primary key used: `DOCUMENT_NUMBER`, `PO_CODE`

#### Column Differences

**Only in A (A37):** `COMPANY_NAME`, `PLANT_CODE`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `DOCUMENT_NUMBER` | 5,508 | 4,280 | 0 | 0 | 295,991 | **98.6%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-0471000-A02-00001`; `JDAW-0471000-A01-00001` → `JDAW-0471000-A04-00001`; `JDAW-0471000-A01-00001` → `JDAW-0471000-B01-00001` |
| `PO_CODE` | 188 | 99 | 0 | 0 | 212 | 4.8% | `JA-BE541-0004` → `JA-BE541-0001`; `JA-BL761-2003` → `JA-BL761-2000`; `JA-BL761-2002` → `JA-BL762-2002` |
| `REVISION_CODE` | 34 | 32 | 1 | 1 | 40 | 1.0% | `C01` → `R01`; `Z02` → `Z01`; `R03` → `R02` |

#### Row-Level Diff Examples

> Rows matched by PK: `DOCUMENT_NUMBER`, `PO_CODE`

**Example 1**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-0471000-K01-00001`; `PO_CODE` = `JA-EE047-1000`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `REVISION_CODE` | `C01` | `R01` |

**Example 2**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-0601000-A01-00001`; `PO_CODE` = `JA-EE060-1000`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `REVISION_CODE` | `Z02` | `Z01` |

**Example 3**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-0601000-K01-00001`; `PO_CODE` = `JA-EE060-1000`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `REVISION_CODE` | `R03` | `R02` |

**Example 4**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-0601000-K10-00001`; `PO_CODE` = `JA-EE060-1000`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `REVISION_CODE` | `Z02` | `Z01` |

**Example 5**
  - 🔑 `DOCUMENT_NUMBER` = `JDAW-1011000-J01-00001`; `PO_CODE` = `JA-ES101-1000`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `REVISION_CODE` | `Z04` | `Z03` |

---

### 023 — Doc→Plant (EIS-409)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 13,265 | 13,477 | +1.6% |
| New rows (in B only) | — | 232 | |
| Removed rows (in A only) | 20 | — | |
| Changed rows (same PK) | — | — | 0 |

> Primary key used: `DOCUMENT_NUMBER`

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `DOCUMENT_NUMBER` | 13,265 | 13,477 | 0 | 0 | 13,146 | **99.1%** ⚠️ | `JDAW-0601000-L45-00002` → `JDAW-0601000-M01-00001`; `JDAW-0601000-M01-00001` → `JDAW-0601000-X01-00001`; `JDAW-0601000-X01-00001` → `JDAW-0702000-A01-02001` |
| `PLANT_CODE` | 2 | 2 | 0 | 0 | 0 | 0.0% |  |

#### Row-Level Diff Examples

ℹ️ No row-level differences detected in shared rows.

---

### 024 — Doc→Site (EIS-408)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 13,265 | 13,477 | +1.6% |
| New rows (in B only) | — | 232 | |
| Removed rows (in A only) | 20 | — | |
| Changed rows (same PK) | — | — | 13,245 |

> Primary key used: `DOCUMENT_NUMBER`

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `SITE_CODE` | 2 | 1 | 0 | 0 | 13,245 | **100.0%** ⚠️ | `JD` → `SWA`; `JD` → `SWA`; `JD` → `SWA` |
| `DOCUMENT_NUMBER` | 13,265 | 13,477 | 0 | 0 | 13,146 | **99.1%** ⚠️ | `JDAW-0601000-L45-00002` → `JDAW-0601000-M01-00001`; `JDAW-0601000-M01-00001` → `JDAW-0601000-X01-00001`; `JDAW-0601000-X01-00001` → `JDAW-0702000-A01-02001` |

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
