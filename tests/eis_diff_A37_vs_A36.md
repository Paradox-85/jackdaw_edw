# EIS Export Revision Diff Report

**Folder A (new):** `C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\Apr-26\CSV\eis_export_A37_20260411_1107`  
**Folder B (baseline):** `C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\Mar-26\CSV`

**Files compared:** 14

## Summary

| Seq | Register | Rev A | Rev B | Rows A | Rows B | Δ Rows | % | ⚠️ |
|-----|----------|-------|-------|-------:|-------:|-------:|--:|---|
| 004 | Equipment Register (EIS-206) | A37 | A36 | 23,071 | 23,026 | -45 | -0.2% | ⚠️ |
| 005 | Model Part Register (EIS-209) | A37 | A36 | 8,530 | 1,473 | -7,057 | -82.7% | ⚠️ |
| 006 | Tag Physical Connections (EIS-212) | A37 | A36 | 3,790 | 4,502 | +712 | +18.8% | ⚠️ |
| 009 | Tag Class Properties (EIS-307) | A37 | A36 | 5,296 | 1,030 | -4,266 | -80.6% | ⚠️ |
| 010 | Tag Property Values (EIS-303) | A37 | A36 | 166,447 | 116,111 | -50,336 | -30.2% | ⚠️ |
| 011 | Equipment Property Values (EIS-301) | A37 | A36 | 90,100 | 84,670 | -5,430 | -6.0% | ⚠️ |
| 016 | Doc→Tag (EIS-412) | A37 | A36 | 421,770 | 405,564 | -16,206 | -3.8% | ⚠️ |
| 017 | Area Register / Doc→Area (EIS-203/411) | A37 | A36 | 18,839 | 18,856 | +17 | +0.1% | ⚠️ |
| 018 | Process Unit Register / Doc→ProcessUnit (EIS-204/410) | A37 | A36 | 16,516 | 19,262 | +2,746 | +16.6% | ⚠️ |
| 019 | Doc→Equipment (EIS-413) | A37 | A36 | 421,220 | 405,564 | -15,656 | -3.7% | ✅ |
| 020 | Doc→Model Part (EIS-414) | A37 | A36 | 42,450 | 43,656 | +1,206 | +2.8% | ⚠️ |
| 022 | Doc→Purchase Order (EIS-420) | A37 | A36 | 5,808 | 4,334 | -1,474 | -25.4% | ⚠️ |
| 023 | Doc→Plant (EIS-409) | A37 | A36 | 13,477 | 13,477 | +0 | +0.0% | ✅ |
| 024 | Doc→Site (EIS-408) | A37 | A36 | 13,477 | 13,477 | +0 | +0.0% | ✅ |

---

## Detailed Diff per File

### 004 — Equipment Register (EIS-206)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 23,071 | 23,026 | -0.2% |
| New rows (in B only) | — | 1 | |
| Removed rows (in A only) | 3 | — | |
| Changed rows (same PK) | — | — | 23,066 |

> Primary key used: `EQUIPMENT_NUMBER`

#### Column Differences

**Only in A (A37):** `ACTION_DATE`

**Only in B (A36):** `ID`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `EQUIPMENT_NUMBER` | 23,028 | 23,026 | 0 | 0 | 23,026 | **100.0%** ⚠️ | `Equip_01MV-0075` → `Equip_001-01EBD-001-001RE1`; `Equip_72-LI-00X11` → `Equip_01MV-0075`; `Equip_72-PDI-000X3` → `Equip_72-LI-00X11` |
| `WARRANTY_END_DATE` | 1 | 3 | 0 | 22,711 | 23,066 | **100.0%** ⚠️ | `NA` → ``; `NA` → ``; `NA` → `` |
| `MANUFACTURER_SERIAL_NUMBER` | 2,597 | 2,598 | 17,635 | 2,858 | 15,150 | **65.7%** ⚠️ | `` → `NA`; `` → `NA`; `` → `NA` |
| `MODEL_PART_NAME` | 1,264 | 1,382 | 14,215 | 5,812 | 8,635 | **37.4%** ⚠️ | `` → `095495`; `` → `025316`; `` → `NA` |
| `PART_OF` | 94 | 95 | 5,576 | 4,340 | 7,346 | **31.8%** ⚠️ | `ZLEI3H10` → `Z-LEI-3H10`; `ZLEI3E19` → `Z-LEI-3E19`; `ZLEI3E19` → `Z-LEI-3E19` |
| `MANUFACTURER_COMPANY_NAME` | 428 | 452 | 10,017 | 3,105 | 6,957 | **30.2%** ⚠️ | `` → `INTERNAL WIRING`; `` → `INTERNAL WIRING`; `` → `INTERNAL WIRING` |
| `ACTION_STATUS` | 3 | 4 | 0 | 0 | 5,505 | **23.9%** ⚠️ | `No Changes` → `Modified`; `No Changes` → `Modified`; `No Changes` → `Modified` |
| `EQUIPMENT_DESCRIPTION` | 10,716 | 10,563 | 366 | 366 | 3,039 | **13.2%** ⚠️ | `NETWORK AND SERVER CABINET; SHEARWATER` → `NETWORK AND SERVER CABINET, SHEARWATER`; `CRITICAL ACTION PANEL; SHEARWATER` → `CRITICAL ACTION PANEL, SHEARWATER`; `ESD CONTROLLER CABINET; SHEARWATER` → `ESD CONTROLLER CABINET, SHEARWATER` |
| `VENDOR_COMPANY_NAME` | 44 | 47 | 5,610 | 4,340 | 1,308 | 5.7% | `FMC KONGSBERG SUBSEA AS` → `FMC Kongsberg Subsea AS`; `` → `NA`; `` → `NA` |
| `PURCHASE_DATE` | 118 | 119 | 5,576 | 4,340 | 1,220 | 5.3% | `` → `NA`; `` → `NA`; `` → `NA` |
| `INSTALLATION_DATE` | 2 | 4 | 23,007 | 22,664 | 362 | 1.6% | `2023-08-01` → `01-08-2023`; `2023-08-01` → `01-08-2023`; `` → `TBC` |
| `EQUIPMENT_CLASS_NAME` | 223 | 216 | 56 | 54 | 138 | 0.6% | `RELATIVE PRESSURE TRANSMITTER` → `PRESSURE TRANSMITTER`; `RELATIVE PRESSURE TRANSMITTER` → `PRESSURE TRANSMITTER`; `RELATIVE PRESSURE TRANSMITTER` → `PRESSURE TRANSMITTER` |
| `PLANT_CODE` | 3 | 5 | 3 | 0 | 3 | 0.0% | `` → `001`; `` → `JDE`; `` → `tes` |
| `TAG_NAME` | 23,028 | 23,026 | 0 | 0 | 0 | 0.0% |  |
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
  | `MANUFACTURER_SERIAL_NUMBER` | `` | `NA` |
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
  | `MANUFACTURER_SERIAL_NUMBER` | `` | `NA` |
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
  | `MANUFACTURER_SERIAL_NUMBER` | `` | `NA` |
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
  | `MANUFACTURER_SERIAL_NUMBER` | `` | `NA` |
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
  | `MANUFACTURER_SERIAL_NUMBER` | `` | `NA` |
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
| Total rows | 8,530 | 1,473 | **-82.7%** ⚠️ |

> ⚠️ No PK columns available for row-identity analysis.

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `MODEL_PART_NAME` | 1,262 | 1,379 | 0 | 0 | 1,473 | **100.0%** ⚠️ | `01122039KPB-DHK` → `PVG-EX`; `01122039KPB-DHK` → `095495`; `01122039KPB-DHK` → `61-1100.0` |
| `MODEL_DESCRIPTION` | 1,262 | 1 | 0 | 0 | 1,473 | **100.0%** ⚠️ | `STEWART-BUCHANAN GAUGES 01122039KPB-DHK - PRESSURE GAUGE. IP66; DIAPHRAGM ELEMENT TECHNOLOGY; CAPSULE ELEMENT TECHNOLOGIES; FOR MEASURING SYSTEMS IN BOURDON TUBE; PRESSURE MEASUREMENT; DIFFERENTIAL PRESSURE MEASUREMENT; STAINLESS STEEL HOUSING. (SOURCE: INTERNAL CATALOG + STEWARTS-GROUP.COM)` → `TBD`; `STEWART-BUCHANAN GAUGES 01122039KPB-DHK - PRESSURE GAUGE. IP66; DIAPHRAGM ELEMENT TECHNOLOGY; CAPSULE ELEMENT TECHNOLOGIES; FOR MEASURING SYSTEMS IN BOURDON TUBE; PRESSURE MEASUREMENT; DIFFERENTIAL PRESSURE MEASUREMENT; STAINLESS STEEL HOUSING. (SOURCE: INTERNAL CATALOG + STEWARTS-GROUP.COM)` → `TBD`; `STEWART-BUCHANAN GAUGES 01122039KPB-DHK - PRESSURE GAUGE. IP66; DIAPHRAGM ELEMENT TECHNOLOGY; CAPSULE ELEMENT TECHNOLOGIES; FOR MEASURING SYSTEMS IN BOURDON TUBE; PRESSURE MEASUREMENT; DIFFERENTIAL PRESSURE MEASUREMENT; STAINLESS STEEL HOUSING. (SOURCE: INTERNAL CATALOG + STEWARTS-GROUP.COM)` → `TBD` |
| `EQUIPMENT_CLASS_NAME` | 195 | 198 | 0 | 0 | 1,446 | **98.2%** ⚠️ | `PRESSURE GAUGE` → `RM NEEDLE VALVE`; `PRESSURE GAUGE` → `ACCESS CONTROL SENSOR`; `PRESSURE GAUGE` → `PUSH BUTTON` |
| `MANUFACTURER_COMPANY_NAME` | 393 | 425 | 1 | 5 | 1,445 | **98.1%** ⚠️ | `STEWART-BUCHANAN GAUGES` → `DANFOSS`; `STEWART-BUCHANAN GAUGES` → `HERNIS`; `STEWART-BUCHANAN GAUGES` → `EAO` |

#### Row-Level Diff Examples

> ⚠️ No shared PK — rows matched **positionally** (row N in A vs row N in B). May reflect reordering rather than true changes.

**Example 1**
  - 🔢 Row #1472 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `MANUFACTURER_COMPANY_NAME` | `DRAKA NORSK KABEL` | `YOKOGAWA` |
  | `MODEL_PART_NAME` | `20110638` | `GP2SY-02XX210W1019E` |
  | `EQUIPMENT_CLASS_NAME` | `SIGNAL CABLE` | `CABINET` |
  | `MODEL_DESCRIPTION` | `DRAKA NORS KABEL 20110638 - FIRE RESISTANCE CABLE. HALOGEN-FREE; 250V; 1X2X1.5M…` | `TBD` |

**Example 2**
  - 🔢 Row #1456 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `MANUFACTURER_COMPANY_NAME` | `DRAKA NORSK KABEL` | `JOBIRD` |
  | `MODEL_PART_NAME` | `20110638` | `JB10FE` |
  | `EQUIPMENT_CLASS_NAME` | `SIGNAL CABLE` | `CABINET` |
  | `MODEL_DESCRIPTION` | `DRAKA NORS KABEL 20110638 - FIRE RESISTANCE CABLE. HALOGEN-FREE; 250V; 1X2X1.5M…` | `TBD` |

**Example 3**
  - 🔢 Row #1455 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `MANUFACTURER_COMPANY_NAME` | `DRAKA NORSK KABEL` | `JOBIRD` |
  | `MODEL_PART_NAME` | `20110638` | `JB38` |
  | `EQUIPMENT_CLASS_NAME` | `SIGNAL CABLE` | `CABINET` |
  | `MODEL_DESCRIPTION` | `DRAKA NORS KABEL 20110638 - FIRE RESISTANCE CABLE. HALOGEN-FREE; 250V; 1X2X1.5M…` | `TBD` |

**Example 4**
  - 🔢 Row #1454 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `MANUFACTURER_COMPANY_NAME` | `DRAKA NORSK KABEL` | `JOBIRD` |
  | `MODEL_PART_NAME` | `20110638` | `RS250FE` |
  | `EQUIPMENT_CLASS_NAME` | `SIGNAL CABLE` | `CABINET` |
  | `MODEL_DESCRIPTION` | `DRAKA NORS KABEL 20110638 - FIRE RESISTANCE CABLE. HALOGEN-FREE; 250V; 1X2X1.5M…` | `TBD` |

**Example 5**
  - 🔢 Row #1453 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `MANUFACTURER_COMPANY_NAME` | `DRAKA NORSK KABEL` | `JO BIRD` |
  | `MODEL_PART_NAME` | `20110638` | `JB10` |
  | `EQUIPMENT_CLASS_NAME` | `SIGNAL CABLE` | `HEALTH, SAFETY AND ENVIRONMENT EQUIPMENT CLASS` |
  | `MODEL_DESCRIPTION` | `DRAKA NORS KABEL 20110638 - FIRE RESISTANCE CABLE. HALOGEN-FREE; 250V; 1X2X1.5M…` | `TBD` |

---

### 006 — Tag Physical Connections (EIS-212)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 3,790 | 4,502 | **+18.8%** ⚠️ |

> ⚠️ No PK columns available for row-identity analysis.

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `FROM_TAG` | 2,514 | 2,468 | 1 | 0 | 3,779 | **99.7%** ⚠️ | `HELIDECK GUTTER` → `JDA-79-PLC-001`; `JDA-83ESB-V3C-F110L10` → `JDA-57-JE-00010`; `JDA-86-JE-00853` → `JDA-01-SAN-001` |
| `TO_TAG` | 2,397 | 2,367 | 10 | 0 | 3,778 | **99.7%** ⚠️ | `JDA-8"-D61806-13842-N` → `JDA-57-JE-00010`; `JDA-83ESB-V3C-F110L18` → `JDA-01-SAN-002`; `JDA-55-PCS-002` → `JDA-55-PCS-005` |
| `PLANT_CODE` | 1 | 1 | 0 | 0 | 0 | 0.0% |  |

#### Row-Level Diff Examples

> ⚠️ No shared PK — rows matched **positionally** (row N in A vs row N in B). May reflect reordering rather than true changes.

**Example 1**
  - 🔢 Row #3789 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `FROM_TAG` | `JDA-57XZ-06203` | `JDA-83ESB-V3C-F013L03` |
  | `TO_TAG` | `JDA-57XZ-06307` | `JDA-83ESB-V3C-F013L04` |

**Example 2**
  - 🔢 Row #0 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `FROM_TAG` | `HELIDECK GUTTER` | `JDA-79-PLC-001` |
  | `TO_TAG` | `JDA-8"-D61806-13842-N` | `JDA-57-JE-00010` |

**Example 3**
  - 🔢 Row #1 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `FROM_TAG` | `JDA-83ESB-V3C-F110L10` | `JDA-57-JE-00010` |
  | `TO_TAG` | `JDA-83ESB-V3C-F110L18` | `JDA-01-SAN-002` |

**Example 4**
  - 🔢 Row #2 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `FROM_TAG` | `JDA-86-JE-00853` | `JDA-01-SAN-001` |
  | `TO_TAG` | `JDA-55-PCS-002` | `JDA-55-PCS-005` |

**Example 5**
  - 🔢 Row #3 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `FROM_TAG` | `JDA-SB-E2B` | `JDA-02MOV-00005` |
  | `TO_TAG` | `JDA-75-11-TCB-801` | `JDA-01-SAN-001` |

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

### 010 — Tag Property Values (EIS-303)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 166,447 | 116,111 | **-30.2%** ⚠️ |
| New rows (in B only) | — | 1,237 | |
| Removed rows (in A only) | 38 | — | |
| Changed rows (same PK) | — | — | 3,549,005 |

> Primary key used: `TAG_NAME`

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `TAG_NAME` | 14,276 | 15,475 | 0 | 0 | 116,111 | **100.0%** ⚠️ | `ESB1_BUSCABLE1_0101` → `JDA-CP-62001`; `ESB1_BUSCABLE1_0101` → `JDA-CP-62001`; `ESB1_BUSCABLE1_0101` → `JDA-CP-62001` |
| `PROPERTY_NAME` | 178 | 181 | 0 | 0 | 3,549,005 | **100.0%** ⚠️ | `ACTUAL LENGTH` → `from tag name`; `ACTUAL LENGTH` → `to tag name`; `ACTUAL LENGTH` → `cable specification` |
| `PROPERTY_VALUE` | 2,460 | 5,599 | 274 | 0 | 2,796,262 | **78.8%** ⚠️ | `1000` → `JDA-55-PCS-001`; `1000` → `JDA-55-PCS-001`; `1000` → `YCB301-C100` |
| `PROPERTY_VALUE_UOM` | 66 | 53 | 79,797 | 80,834 | 2,314,628 | **65.2%** ⚠️ | `mm` → ``; `mm` → ``; `mm` → `` |
| `PLANT_CODE` | 2 | 2 | 0 | 0 | 506 | 0.0% | `JDA` → `SWA`; `JDA` → `SWA`; `JDA` → `SWA` |

#### Row-Level Diff Examples

> Rows matched by PK: `TAG_NAME`

**Example 1**
  - 🔑 `TAG_NAME` = `KVMSW-YSS012-KVM`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PROPERTY_NAME` | `CABLE SPECIFICATION` | `actual length` |
  | `PROPERTY_VALUE` | `Cat6a U/FTP AWG27/7 Patch Cable` | `2000` |
  | `PROPERTY_VALUE_UOM` | `` | `mm` |

**Example 2**
  - 🔑 `TAG_NAME` = `KVMSW-YSS012-KVM`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PROPERTY_NAME` | `ACTUAL LENGTH` | `cable specification` |
  | `PROPERTY_VALUE` | `2000` | `Cat6a U/FTP AWG27/7 Patch Cable` |
  | `PROPERTY_VALUE_UOM` | `mm` | `` |

**Example 3**
  - 🔑 `TAG_NAME` = `KVMSW-YSS012-KVM`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PROPERTY_NAME` | `ACTUAL LENGTH` | `to tag name` |
  | `PROPERTY_VALUE` | `2000` | `JDA-01-SAN-002` |
  | `PROPERTY_VALUE_UOM` | `mm` | `` |

**Example 4**
  - 🔑 `TAG_NAME` = `KVMSW-YSS012-KVM`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PROPERTY_NAME` | `ACTUAL LENGTH` | `from tag name` |
  | `PROPERTY_VALUE` | `2000` | `JDA-01-SAN-002` |
  | `PROPERTY_VALUE_UOM` | `mm` | `` |

**Example 5**
  - 🔑 `TAG_NAME` = `KVMSW-YSS012-KVM`

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PROPERTY_NAME` | `ACTUAL LENGTH` | `cable specification` |
  | `PROPERTY_VALUE` | `2000` | `Cat6a U/FTP AWG27/7 Patch Cable` |
  | `PROPERTY_VALUE_UOM` | `mm` | `` |

---

### 011 — Equipment Property Values (EIS-301)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 90,100 | 84,670 | **-6.0%** ⚠️ |

> ⚠️ No PK columns available for row-identity analysis.

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `PROPERTY_NAME` | 213 | 212 | 0 | 0 | 84,670 | **100.0%** ⚠️ | `WEIGHT NET` → `weight content`; `WEIGHT NET` → `Starter Type`; `WEIGHT NET` → `Contactor Type` |
| `EQUIPMENT_NUMBER` | 11,967 | 12,990 | 0 | 0 | 84,661 | **100.0%** ⚠️ | `Equip_ESB1_BUSCABLE1_0101` → `Equip_JDA-CP-62001`; `Equip_ESB1_BUSCABLE1_0101` → `Equip_JDA-CP-62001`; `Equip_ESB1_BUSCABLE1_0101` → `Equip_JDA-CP-62001` |
| `PROPERTY_VALUE` | 3,046 | 4,218 | 639 | 0 | 79,855 | **94.3%** ⚠️ | `1` → `0`; `1` → `NA`; `1` → `yes, Thyristor` |
| `PROPERTY_VALUE_UOM` | 79 | 31 | 47,135 | 55,347 | 50,154 | **59.2%** ⚠️ | `kg` → ``; `kg` → ``; `kg` → `` |
| `PLANT_CODE` | 2 | 2 | 0 | 0 | 1,193 | 1.4% | `JDA` → `SWA`; `JDA` → `SWA`; `JDA` → `SWA` |

#### Row-Level Diff Examples

> ⚠️ No shared PK — rows matched **positionally** (row N in A vs row N in B). May reflect reordering rather than true changes.

**Example 1**
  - 🔢 Row #80327 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `JDA` | `SWA` |
  | `EQUIPMENT_NUMBER` | `Equip_JDA-SB-E2A-F006` | `Equip_GB.SWA.SW-L-7885` |
  | `PROPERTY_NAME` | `WEIGHT NET` | `pcs_EX_CERTIFICATE` |
  | `PROPERTY_VALUE` | `0.28` | `NA` |
  | `PROPERTY_VALUE_UOM` | `kg` | `` |

**Example 2**
  - 🔢 Row #80328 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `JDA` | `SWA` |
  | `EQUIPMENT_NUMBER` | `Equip_JDA-SB-E2A-F006` | `Equip_GB.SWA.SW-L-7885` |
  | `PROPERTY_NAME` | `WEIGHT NET` | `pcs_EX_CLASS` |
  | `PROPERTY_VALUE` | `0.28` | `NA` |
  | `PROPERTY_VALUE_UOM` | `kg` | `` |

**Example 3**
  - 🔢 Row #80329 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `JDA` | `SWA` |
  | `EQUIPMENT_NUMBER` | `Equip_JDA-SB-E2A-F006` | `Equip_GB.SWA.SW-L-7885` |
  | `PROPERTY_NAME` | `WEIGHT NET` | `pcs_IP_GRADE` |
  | `PROPERTY_VALUE` | `0.28` | `IP 54` |
  | `PROPERTY_VALUE_UOM` | `kg` | `` |

**Example 4**
  - 🔢 Row #80333 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `JDA` | `SWA` |
  | `EQUIPMENT_NUMBER` | `Equip_JDA-SB-E2A-F007` | `Equip_GB.SWA.SW-L-7885` |
  | `PROPERTY_NAME` | `RATED IMPULSE VOLTAGE` | `atex group` |
  | `PROPERTY_VALUE` | `4000` | `NA` |
  | `PROPERTY_VALUE_UOM` | `v` | `` |

**Example 5**
  - 🔢 Row #80330 (0-based positional index)

  | Column | Rev A (A37) | Rev B (A36) |
  |--------|:------|:------|
  | `PLANT_CODE` | `JDA` | `SWA` |
  | `EQUIPMENT_NUMBER` | `Equip_JDA-SB-E2A-F006` | `Equip_GB.SWA.SW-L-7885` |
  | `PROPERTY_NAME` | `WEIGHT NET` | `explosion protection notified body` |
  | `PROPERTY_VALUE` | `0.28` | `NA` |
  | `PROPERTY_VALUE_UOM` | `kg` | `` |

---

### 016 — Doc→Tag (EIS-412)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 421,770 | 405,564 | -3.8% |
| New rows (in B only) | — | 71 | |
| Removed rows (in A only) | 16,277 | — | |
| Changed rows (same PK) | — | — | 250 |

> Primary key used: `DOCUMENT_NUMBER`, `TAG_NAME`

#### Column Differences

**Only in B (A36):** `DOCUMENT_TITLE`, `Match`, `TAG_DOC_ID`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `TAG_NAME` | 17,291 | 17,293 | 0 | 0 | 261,027,699 | **99.8%** ⚠️ | `JDA-84XB-00147` → `JDA-84XB-00147-LOOP`; `JDA-84XB-00147` → `JDA-86KSV-02801`; `JDA-84XB-00147` → `JDA-86KSV-02801-LOOP` |
| `DOCUMENT_NUMBER` | 8,857 | 8,847 | 0 | 0 | 23,310,296 | **98.3%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-KVE-E-IN-4327-00004`; `JDAW-0471000-A01-00001` → `JDAW-KVE-E-IN-8880-00005-014`; `JDAW-0471000-A01-00001` → `JDAW-KVE-E-IN-0901-00003-013` |
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

### 019 — Doc→Equipment (EIS-413)
**Revisions:** `A37` (A, new) vs `A36` (B, baseline)

#### Row Counts

| Metric | Rev A (A37) | Rev B (A36) | Delta |
|--------|--------:|--------:|------:|
| Total rows | 421,220 | 405,564 | -3.7% |
| New rows (in B only) | — | 621 | |
| Removed rows (in A only) | 16,277 | — | |
| Changed rows (same PK) | — | — | 250 |

> Primary key used: `DOCUMENT_NUMBER`, `EQUIPMENT_NUMBER`

#### Column Differences

✅ Column sets are identical.

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `EQUIPMENT_NUMBER` | 17,262 | 17,293 | 0 | 0 | 260,923,282 | **99.8%** ⚠️ | `Equip_JDA-84XB-00147` → `Equip_JDA-84XB-00147-LOOP`; `Equip_JDA-84XB-00147` → `Equip_JDA-86KSV-02801`; `Equip_JDA-84XB-00147` → `Equip_JDA-86KSV-02801-LOOP` |
| `DOCUMENT_NUMBER` | 8,847 | 8,847 | 0 | 0 | 23,299,810 | **98.3%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-KVE-E-IN-4327-00004`; `JDAW-0471000-A01-00001` → `JDAW-KVE-E-IN-8880-00005-014`; `JDAW-0471000-A01-00001` → `JDAW-KVE-E-IN-0901-00003-013` |
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

**Only in A (A37):** `PLANT_CODE`

**Only in B (A36):** `REVISION_CODE`

#### Per-Column Value Statistics

| Column | Unique A | Unique B | Empty A | Empty B | Changed Rows | % Changed | Samples |
|--------|--------:|--------:|--------:|--------:|------------:|----------:|---------|
| `DOCUMENT_NUMBER` | 5,715 | 4,280 | 0 | 0 | 302,570 | **98.6%** ⚠️ | `JDAW-0471000-A01-00001` → `JDAW-0471000-A02-00001`; `JDAW-0471000-A01-00001` → `JDAW-0471000-A04-00001`; `JDAW-0471000-A01-00001` → `JDAW-0471000-B01-00001` |
| `PO_CODE` | 193 | 99 | 0 | 0 | 212 | 4.7% | `JA-BE541-0004` → `JA-BE541-0001`; `JA-BL761-2003` → `JA-BL761-2000`; `JA-BL761-2002` → `JA-BL762-2002` |

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
