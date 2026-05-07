# EIS Property Values — Three-Layer Audit Report

**RDL Reference:** `C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\JDE-Power-BI\_master\data\TagProperties-rdl.xlsx`  
**File 010 (Tag Property Values):** `C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\May-26\CSV\eis_export_A38_20260505_0928\JDAW-KVE-E-JA-6944-00001-010-A38.CSV`  
**File 011 (Equipment Property Values):** `C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\May-26\CSV\eis_export_A38_20260505_0928\JDAW-KVE-E-JA-6944-00001-011-A38.CSV`  

---

## Executive Summary

| Metric | LAYER 0 (RDL vs CSV) | LAYER 1 (RDL vs SQL) | LAYER 2 (SQL vs CSV 010) | LAYER 2 (SQL vs CSV 011) |
|--------|---------------------|---------------------|--------------------------|--------------------------|
| Reference rows | — | 0 | 0 | 0 |
| 🚫 RDL_CSV_MISSING | **43,379 gaps (70 groups)** | — | — | — |
| ⚠️ RDL_CSV_VALUE_MISMATCH | 16,003 gaps (71 groups) | — | — | — |
| ℹ️ RDL_CSV_NA_HAS_VALUE | 0 | — | — | — |
| ⚠️ RDL_CSV_VALUE_MISSING | 918 gaps (82 groups) | — | — | — |
| 🔕 RDL_CSV_NA_BLANK | 0 | — | — | — |
| ⛔ SQL_MISSING (critical) | — | N/A (no-db) | — | — |
| ⚠️ SQL_VALUE_MISMATCH | — | N/A (no-db) | — | — |
| ⚠️ SQL_VALUE_MISSING | — | N/A (no-db) | — | — |
| 🔕 SQL_NA_BLANK | — | N/A (no-db) | — | — |
| ➕ SQL_EXTRA | — | N/A (no-db) | — | — |
| ❌ CSV_MISSING | — | — | **0** | **0** |
| ⚠️ CSV_VALUE_MISMATCH | — | — | 0 | 0 |
| ⚠️ CSV_VALUE_MISSING | — | — | N/A (no-db) | 0 |
| ℹ️ CSV_EXTRA_VALUE | — | — | N/A (no-db) | 0 |
| 🔕 CSV_NA_BLANK | — | — | 0 | 0 |
| 🔀 WRONG_FILE | — | — | 0 | 0 |
| ➕ EXTRA (unknown) | — | — | 0 | 0 |


- ✅ File 010 rows with empty PROPERTY_NAME: **0**
- ✅ File 011 rows with empty PROPERTY_NAME: **0**

---

## DB State (live — project_core.property_value)

> ⚠️ DB query unavailable: `--no-db flag set`
> Layer 1 and Layer 2 gaps are empty. Re-run without `--no-db` for full analysis.

---

## LAYER 0 — RDL vs CSV (Direct, no SQL)

> This layer checks RDL reference values directly against CSV export files.
> **SQL is not required** — useful when DB is unavailable.

### Metrics

| Metric | vs CSV-010 | vs CSV-011 |
|--------|-----------:|-----------:|
| 🚫 RDL_CSV_MISSING | **19,312** | **24,067** |
| ⚠️ RDL_CSV_VALUE_MISMATCH | 14,531 | 1,472 |
| 🔕 RDL_CSV_NA_BLANK | 0 | 0 |

### File-010 (Tag Property Values) Details

### 🚫 RDL_CSV_MISSING — Critical: in RDL, absent from CSV-010 (19,312 total gaps — 42 property groups)

#### Property: `from tag name` | Concept: Functional | 4,606 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-79-PLC-001-03/57-JE-00010` | JDA-79-PLC-001 |  | <missing> | <missing> |
| 2 | `JDA-57-JE-00010/01-SAN-002` | JDA-57-JE-00010 |  | <missing> | <missing> |
| 3 | `JDA-01-SAN-001-02/55-PCS-005` | JDA-01-SAN-001 |  | <missing> | <missing> |
| 4 | `JDA-C-02MOV-00005/01-SAN-001` | JDA-02MOV-00005 |  | <missing> | <missing> |
| 5 | `JDA-C-01MOV-05004B/01-SAN-001` | JDA-01MOV-05004B |  | <missing> | <missing> |
| 6 | `JDA-C-02MOV-00006/46MOV-00018` | JDA-02MOV-00006 |  | <missing> | <missing> |
| 7 | `ESB1_BUSCABLE2_0104` | JDA-55-PCS-001 |  | <missing> | <missing> |
| 8 | `ESB2_BUSCABLE2_0104` | JDA-55-PCS-001 |  | <missing> | <missing> |
| 9 | `ESB1_BUSCABLE2_0103` | JDA-55-PCS-001 |  | <missing> | <missing> |
| 10 | `ESB2_BUSCABLE2_0103` | JDA-55-PCS-001 |  | <missing> | <missing> |
| … | *(4,596 more tags with this pattern)* |  |  |  |  |

#### Property: `to tag name` | Concept: Functional | 4,606 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-79-PLC-001-03/57-JE-00010` | JDA-79-PLC-001 |  | <missing> | <missing> |
| 2 | `JDA-57-JE-00010/01-SAN-002` | JDA-57-JE-00010 |  | <missing> | <missing> |
| 3 | `JDA-01-SAN-001-02/55-PCS-005` | JDA-01-SAN-001 |  | <missing> | <missing> |
| 4 | `JDA-C-02MOV-00005/01-SAN-001` | JDA-02MOV-00005 |  | <missing> | <missing> |
| 5 | `JDA-C-01MOV-05004B/01-SAN-001` | JDA-01MOV-05004B |  | <missing> | <missing> |
| 6 | `JDA-C-02MOV-00006/46MOV-00018` | JDA-02MOV-00006 |  | <missing> | <missing> |
| 7 | `ESB1_BUSCABLE2_0104` | JDA-55-PCS-001 |  | <missing> | <missing> |
| 8 | `ESB2_BUSCABLE2_0104` | JDA-55-PCS-001 |  | <missing> | <missing> |
| 9 | `ESB1_BUSCABLE2_0103` | JDA-55-PCS-001 |  | <missing> | <missing> |
| 10 | `ESB2_BUSCABLE2_0103` | JDA-55-PCS-001 |  | <missing> | <missing> |
| … | *(4,596 more tags with this pattern)* |  |  |  |  |

#### Property: `component cooling type` | Concept: Functional Physical | 1,572 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-74001-CEL` | NA |  | <missing> | <missing> |
| 2 | `JDA-74002-CEL` | NA |  | <missing> | <missing> |
| 3 | `JDA-74005-CEL` | NA |  | <missing> | <missing> |
| 4 | `JDA-74006-CEL` | NA |  | <missing> | <missing> |
| 5 | `JDA-73001-CEL` | NA |  | <missing> | <missing> |
| 6 | `JDA-73004-CEL` | NA |  | <missing> | <missing> |
| 7 | `JDA-73007-CEL` | NA |  | <missing> | <missing> |
| 8 | `JDA-62001-CELR-1` | NA |  | <missing> | <missing> |
| 9 | `JDA-62001-CELY-1` | NA |  | <missing> | <missing> |
| 10 | `JDA-62001-CELB-1` | NA |  | <missing> | <missing> |
| … | *(1,562 more tags with this pattern)* |  |  |  |  |

#### Property: `pressure equipment category` | Concept: Functional Physical | 1,339 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-CP-62001` | NA |  | <missing> | <missing> |
| 2 | `JDA-CP-68001` | NA |  | <missing> | <missing> |
| 3 | `JDA-TH-74002A` | NA |  | <missing> | <missing> |
| 4 | `JDA-TH-74002B` | NA |  | <missing> | <missing> |
| 5 | `JDA-TH-73002A` | NA |  | <missing> | <missing> |
| 6 | `JDA-TH-73002B` | NA |  | <missing> | <missing> |
| 7 | `JDA-TH-73001` | NA |  | <missing> | <missing> |
| 8 | `JDA-TH-62002` | NA |  | <missing> | <missing> |
| 9 | `JDA-TH-62001` | NA |  | <missing> | <missing> |
| 10 | `JDA-TH-61001` | NA |  | <missing> | <missing> |
| … | *(1,329 more tags with this pattern)* |  |  |  |  |

#### Property: `explosion protection zone` | Concept: Functional Physical | 1,275 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-SB-E1A+A03.D1` | NA |  | <missing> | <missing> |
| 2 | `JDA-SB-E1A+A05.L` | NA |  | <missing> | <missing> |
| 3 | `JDA-SB-E1B+B06.P` | NA |  | <missing> | <missing> |
| 4 | `JDA-SB-E1A+A05.J1` | NA |  | <missing> | <missing> |
| 5 | `JDA-SB-E1B+B06.H1` | NA |  | <missing> | <missing> |
| 6 | `JDA-SB-E1B+B06.H2` | NA |  | <missing> | <missing> |
| 7 | `JDA-SB-E1A+A05.R` | NA |  | <missing> | <missing> |
| 8 | `JDA-SB-E1B+B06.N` | NA |  | <missing> | <missing> |
| 9 | `JDA-SB-E1A+A05.J2` | NA |  | <missing> | <missing> |
| 10 | `JDA-SB-E1B+B06.L1` | NA |  | <missing> | <missing> |
| … | *(1,265 more tags with this pattern)* |  |  |  |  |

#### Property: `rated voltage` | Concept: Functional Physical | 1,088 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-83CP-V2-125` | 1000 | V(MAX) | <missing> | <missing> |
| 2 | `JDA-83CP-V2-126` | 24 | Vdc | <missing> | <missing> |
| 3 | `JDA-84ESB-E2A-F451S01` | 110-130 | V | <missing> | <missing> |
| 4 | `JDA-84ESB-E1A-A04JS02` | 400 | V | <missing> | <missing> |
| 5 | `JDA-84ESB-E2A-F452S01` | 110-130 | V | <missing> | <missing> |
| 6 | `JDA-84ESB-E1A-A04JS03` | 400 | V | <missing> | <missing> |
| 7 | `JDA-84ESB-E2A-F453S01` | 110-130 | V | <missing> | <missing> |
| 8 | `JDA-84ESB-E1A-A04JS04` | 400 | V | <missing> | <missing> |
| 9 | `JDA-84ESB-E2A-F454S01` | 110-130 | V | <missing> | <missing> |
| 10 | `JDA-84ESB-E2B-F351S01` | 110-130 | V | <missing> | <missing> |
| … | *(1,078 more tags with this pattern)* |  |  |  |  |

#### Property: `rated power consumption` | Concept: Functional Physical | 774 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-83CP-V2-125` | NA | kW | <missing> | <missing> |
| 2 | `JDA-83CP-V2-126` | NA | kW | <missing> | <missing> |
| 3 | `JDA-83CP-V2-033` | 0.008 | kW | <missing> | <missing> |
| 4 | `JDA-83CP-V2-034` | 0.008 | kW | <missing> | <missing> |
| 5 | `JDA-83CP-V2-035` | 0.008 | kW | <missing> | <missing> |
| 6 | `JDA-83CP-V2-036` | 0.008 | kW | <missing> | <missing> |
| 7 | `JDA-84ESB-E2A-F105L01` | 0.103 | kW | <missing> | <missing> |
| 8 | `JDA-84ESB-E2A-F113L01` | 0.103 | kW | <missing> | <missing> |
| 9 | `JDA-84ESB-E2B-F113L01` | 0.103 | kW | <missing> | <missing> |
| 10 | `JDA-84ESB-E6-F262L04` | 0.053 | kW | <missing> | <missing> |
| … | *(764 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_VALVE_SIZE` | Concept: Functional Physical | 742 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-74MV-0074` | 80 | mm | <missing> | <missing> |
| 2 | `JDA-74MV-0045` | 50 | mm | <missing> | <missing> |
| 3 | `JDA-74MV-0052` | 80 | mm | <missing> | <missing> |
| 4 | `JDA-51MV-0030` | 80 | mm | <missing> | <missing> |
| 5 | `JDA-51MV-0009` | 80 | mm | <missing> | <missing> |
| 6 | `JDA-74MV-0058` | 50 | mm | <missing> | <missing> |
| 7 | `JDA-74MV-0065` | 80 | mm | <missing> | <missing> |
| 8 | `JDA-63MV-0024` | 100 | mm | <missing> | <missing> |
| 9 | `JDA-63MV-0025` | 25 | mm | <missing> | <missing> |
| 10 | `JDA-63MV-0022` | 25 | mm | <missing> | <missing> |
| … | *(732 more tags with this pattern)* |  |  |  |  |

#### Property: `SIL_Level` | Concept: Functional | 489 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E6-F208J01` | NA |  | <missing> | <missing> |
| 2 | `JDA-84ESB-E6-F207J01` | NA |  | <missing> | <missing> |
| 3 | `JDA-84ESB-E6-F300J01` | NA |  | <missing> | <missing> |
| 4 | `JDA-84ESB-E6-F301J01` | NA |  | <missing> | <missing> |
| 5 | `JDA-83ESB-V3C-F110J01` | NA |  | <missing> | <missing> |
| 6 | `JDA-83ESB-V3C-F101J01` | NA |  | <missing> | <missing> |
| 7 | `JDA-84ESB-E6-F200J01` | NA |  | <missing> | <missing> |
| 8 | `JDA-84ESB-E6-F200J21` | NA |  | <missing> | <missing> |
| 9 | `JDA-83ESB-V3C-F100J01` | NA |  | <missing> | <missing> |
| 10 | `JDA-84ESB-E6-F201J41` | NA |  | <missing> | <missing> |
| … | *(479 more tags with this pattern)* |  |  |  |  |

#### Property: `operating voltage` | Concept: Functional Physical | 394 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-62PDI-00018` | 24 | VDC | <missing> | <missing> |
| 2 | `JDA-74PDI-00033` | 10.5 - 30 | V DC | <missing> | <missing> |
| 3 | `JDA-74PDI-00032` | 10.5 - 30 | V DC | <missing> | <missing> |
| 4 | `JDA-62PDI-00022` | 10.5 - 45 | VDC | <missing> | <missing> |
| 5 | `JDA-73PDI-00054` | 24 | VDC | <missing> | <missing> |
| 6 | `JDA-73PDI-00256` | 24 | VDC | <missing> | <missing> |
| 7 | `JDA-73PDI-00257` | 24 | VDC | <missing> | <missing> |
| 8 | `JDA-84PDT-00130` | 24 | volt | <missing> | <missing> |
| 9 | `JDA-84PDT-00230` | 24 | volt | <missing> | <missing> |
| 10 | `JDA-84PDT-00330` | 24 | volt | <missing> | <missing> |
| … | *(384 more tags with this pattern)* |  |  |  |  |

#### Property: `rated current` | Concept: Functional Physical | 368 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2A-F451S01` | 16 | ampere | <missing> | <missing> |
| 2 | `JDA-84ESB-E1A-A04JS02` | 63 | ampere | <missing> | <missing> |
| 3 | `JDA-84ESB-E2A-F452S01` | 16 | ampere | <missing> | <missing> |
| 4 | `JDA-84ESB-E1A-A04JS03` | 63 | ampere | <missing> | <missing> |
| 5 | `JDA-84ESB-E2A-F453S01` | 16 | ampere | <missing> | <missing> |
| 6 | `JDA-84ESB-E1A-A04JS04` | 63 | ampere | <missing> | <missing> |
| 7 | `JDA-84ESB-E2A-F454S01` | 16 | ampere | <missing> | <missing> |
| 8 | `JDA-84ESB-E2B-F351S01` | 16 | ampere | <missing> | <missing> |
| 9 | `JDA-84ESB-E1B-B04NS02` | 63 | ampere | <missing> | <missing> |
| 10 | `JDA-84ESB-E2B-F352S01` | 16 | ampere | <missing> | <missing> |
| … | *(358 more tags with this pattern)* |  |  |  |  |

#### Property: `explosion protection gas group` | Concept: Functional Physical | 290 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-83CP-V2-037` | IIC |  | <missing> | <missing> |
| 2 | `JDA-83CP-V2-041` | IIC |  | <missing> | <missing> |
| 3 | `JDA-83CP-V2-043` | IIC |  | <missing> | <missing> |
| 4 | `JDA-ES-84802` | NA |  | <missing> | <missing> |
| 5 | `JDA-ES-84803` | NA |  | <missing> | <missing> |
| 6 | `JDA-ES-84801` | NA |  | <missing> | <missing> |
| 7 | `JDA-83ESB-V3C-F102X01` | NA |  | <missing> | <missing> |
| 8 | `JDA-TH-86804` | IIC |  | <missing> | <missing> |
| 9 | `JDA-TH-86831` | NA |  | <missing> | <missing> |
| 10 | `JDA-84ESB-E2A-F106X01` | IIC |  | <missing> | <missing> |
| … | *(280 more tags with this pattern)* |  |  |  |  |

#### Property: `explosion protection temperature class` | Concept: Functional Physical | 290 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-83CP-V2-037` | T5 |  | <missing> | <missing> |
| 2 | `JDA-83CP-V2-041` | T5 |  | <missing> | <missing> |
| 3 | `JDA-83CP-V2-043` | T5 |  | <missing> | <missing> |
| 4 | `JDA-ES-84802` | NA |  | <missing> | <missing> |
| 5 | `JDA-ES-84803` | NA |  | <missing> | <missing> |
| 6 | `JDA-ES-84801` | NA |  | <missing> | <missing> |
| 7 | `JDA-83ESB-V3C-F102X01` | NA |  | <missing> | <missing> |
| 8 | `JDA-TH-86804` | T6 |  | <missing> | <missing> |
| 9 | `JDA-TH-86831` | NA |  | <missing> | <missing> |
| 10 | `JDA-84ESB-E2A-F106X01` | T6 |  | <missing> | <missing> |
| … | *(280 more tags with this pattern)* |  |  |  |  |

#### Property: `explosion rated item` | Concept: Functional | 196 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-54TE-00020` | true |  | <missing> | <missing> |
| 2 | `JDA-54TE-00021` | true |  | <missing> | <missing> |
| 3 | `JDA-61TE-00020` | true |  | <missing> | <missing> |
| 4 | `JDA-62TE-00038` | true |  | <missing> | <missing> |
| 5 | `JDA-63TE-00023` | true |  | <missing> | <missing> |
| 6 | `JDA-63TE-00022` | true |  | <missing> | <missing> |
| 7 | `JDA-83CP-V2-052` | true |  | <missing> | <missing> |
| 8 | `JDA-01XI-02013` | true |  | <missing> | <missing> |
| 9 | `JDA-01XI-05013` | true |  | <missing> | <missing> |
| 10 | `JDA-01XI-03013` | true |  | <missing> | <missing> |
| … | *(186 more tags with this pattern)* |  |  |  |  |

#### Property: `failure action` | Concept: Functional Physical | 103 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-74UZV-00002` | Fail close |  | <missing> | <missing> |
| 2 | `JDA-73UZV-00203` | Fail Close |  | <missing> | <missing> |
| 3 | `JDA-54UZV-00001` | Fail Close |  | <missing> | <missing> |
| 4 | `JDA-73UZV-00201` | Fail close |  | <missing> | <missing> |
| 5 | `JDA-73UZV-00102` | Fail Close |  | <missing> | <missing> |
| 6 | `JDA-01UZV-02003` | Fail close |  | <missing> | <missing> |
| 7 | `JDA-74UZV-02001` | Fail close |  | <missing> | <missing> |
| 8 | `JDA-73UZV-00204` | Fail close |  | <missing> | <missing> |
| 9 | `JDA-63UZV-00002` | Fail Close |  | <missing> | <missing> |
| 10 | `JDA-01UZV-05003` | Fail close |  | <missing> | <missing> |
| … | *(93 more tags with this pattern)* |  |  |  |  |

#### Property: `rated short circuit current` | Concept: Functional Physical | 98 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-H-62001` | 25000 | ampere | <missing> | <missing> |
| 2 | `JDA-H-63001` | 25000 | ampere | <missing> | <missing> |
| 3 | `JDA-H-46001B` | NA | ampere | <missing> | <missing> |
| 4 | `JDA-H-61001` | NA | ampere | <missing> | <missing> |
| 5 | `JDA-H-46001A` | NA | ampere | <missing> | <missing> |
| 6 | `JDA-H-84101` | NA | ampere | <missing> | <missing> |
| 7 | `JDA-H-84102` | NA | ampere | <missing> | <missing> |
| 8 | `JDA-H-84103` | NA | ampere | <missing> | <missing> |
| 9 | `JDA-H-84104` | NA | ampere | <missing> | <missing> |
| 10 | `JDA-H-84201` | NA | ampere | <missing> | <missing> |
| … | *(88 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ALARM_LIMIT_HH` | Concept: Functional | 93 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-57XZ-01101` | NA |  | <missing> | <missing> |
| 2 | `JDA-57XZ-01102` | NA |  | <missing> | <missing> |
| 3 | `JDA-57XZ-01103` | NA |  | <missing> | <missing> |
| 4 | `JDA-57XZ-01104` | NA |  | <missing> | <missing> |
| 5 | `JDA-57XZ-01105` | NA |  | <missing> | <missing> |
| 6 | `JDA-57XZ-01106` | NA |  | <missing> | <missing> |
| 7 | `JDA-57XZ-01107` | NA |  | <missing> | <missing> |
| 8 | `JDA-57XZ-01108` | NA |  | <missing> | <missing> |
| 9 | `JDA-57XZ-01109` | NA |  | <missing> | <missing> |
| 10 | `JDA-57XZ-01201` | NA |  | <missing> | <missing> |
| … | *(83 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ALARM_LIMIT_LL` | Concept: Functional | 93 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-57XZ-01101` | NA |  | <missing> | <missing> |
| 2 | `JDA-57XZ-01102` | NA |  | <missing> | <missing> |
| 3 | `JDA-57XZ-01103` | NA |  | <missing> | <missing> |
| 4 | `JDA-57XZ-01104` | NA |  | <missing> | <missing> |
| 5 | `JDA-57XZ-01105` | NA |  | <missing> | <missing> |
| 6 | `JDA-57XZ-01106` | NA |  | <missing> | <missing> |
| 7 | `JDA-57XZ-01107` | NA |  | <missing> | <missing> |
| 8 | `JDA-57XZ-01108` | NA |  | <missing> | <missing> |
| 9 | `JDA-57XZ-01109` | NA |  | <missing> | <missing> |
| 10 | `JDA-57XZ-01201` | NA |  | <missing> | <missing> |
| … | *(83 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ALARM_LIMIT_WH` | Concept: Functional | 93 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-57XZ-01101` | NA |  | <missing> | <missing> |
| 2 | `JDA-57XZ-01102` | NA |  | <missing> | <missing> |
| 3 | `JDA-57XZ-01103` | NA |  | <missing> | <missing> |
| 4 | `JDA-57XZ-01104` | NA |  | <missing> | <missing> |
| 5 | `JDA-57XZ-01105` | NA |  | <missing> | <missing> |
| 6 | `JDA-57XZ-01106` | NA |  | <missing> | <missing> |
| 7 | `JDA-57XZ-01107` | NA |  | <missing> | <missing> |
| 8 | `JDA-57XZ-01108` | NA |  | <missing> | <missing> |
| 9 | `JDA-57XZ-01109` | NA |  | <missing> | <missing> |
| 10 | `JDA-57XZ-01201` | NA |  | <missing> | <missing> |
| … | *(83 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ALARM_LIMIT_WL` | Concept: Functional | 93 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-57XZ-01101` | NA |  | <missing> | <missing> |
| 2 | `JDA-57XZ-01102` | NA |  | <missing> | <missing> |
| 3 | `JDA-57XZ-01103` | NA |  | <missing> | <missing> |
| 4 | `JDA-57XZ-01104` | NA |  | <missing> | <missing> |
| 5 | `JDA-57XZ-01105` | NA |  | <missing> | <missing> |
| 6 | `JDA-57XZ-01106` | NA |  | <missing> | <missing> |
| 7 | `JDA-57XZ-01107` | NA |  | <missing> | <missing> |
| 8 | `JDA-57XZ-01108` | NA |  | <missing> | <missing> |
| 9 | `JDA-57XZ-01109` | NA |  | <missing> | <missing> |
| 10 | `JDA-57XZ-01201` | NA |  | <missing> | <missing> |
| … | *(83 more tags with this pattern)* |  |  |  |  |

#### Property: `rated speed` | Concept: Functional Physical | 81 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-G-84001A` | 1500 | rpm | <missing> | <missing> |
| 2 | `JDA-G-84001B` | 1500 | rpm | <missing> | <missing> |
| 3 | `JDA-G-84001C` | 1500 | rpm | <missing> | <missing> |
| 4 | `JDA-PM-74002A` | 245.833333333333 | rpm | <missing> | <missing> |
| 5 | `JDA-PM-54001` | 2907 | rpm | <missing> | <missing> |
| 6 | `JDA-PM-62001` | 2907 | rpm | <missing> | <missing> |
| 7 | `JDA-PM-62002` | 245.833333333333 | rpm | <missing> | <missing> |
| 8 | `JDA-PM-73001` | 160.833333333333 | rpm | <missing> | <missing> |
| 9 | `JDA-PM-73002A` | 241.666666666667 | rpm | <missing> | <missing> |
| 10 | `JDA-PM-73002B` | 241.666666666667 | rpm | <missing> | <missing> |
| … | *(71 more tags with this pattern)* |  |  |  |  |

#### Property: `actual length` | Concept: Functional Physical | 57 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-H-62001` | 3928 | mm | <missing> | <missing> |
| 2 | `JDA-H-63001` | 1580 | mm | <missing> | <missing> |
| 3 | `JDA-H-46001B` | 1250 | mm | <missing> | <missing> |
| 4 | `JDA-H-61001` | 2179 | mm | <missing> | <missing> |
| 5 | `JDA-H-46001A` | 1250 | mm | <missing> | <missing> |
| 6 | `JDA-H-84101` | NA | mm | <missing> | <missing> |
| 7 | `JDA-H-84102` | NA | mm | <missing> | <missing> |
| 8 | `JDA-H-84103` | 230 | mm | <missing> | <missing> |
| 9 | `JDA-H-84104` | 834 | mm | <missing> | <missing> |
| 10 | `JDA-H-84201` | NA | mm | <missing> | <missing> |
| … | *(47 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ACTUAL_LOAD` | Concept: Functional Physical | 57 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-H-62001` | NA |  | <missing> | <missing> |
| 2 | `JDA-H-63001` | NA |  | <missing> | <missing> |
| 3 | `JDA-H-46001B` | NA | kW | <missing> | <missing> |
| 4 | `JDA-H-61001` | NA |  | <missing> | <missing> |
| 5 | `JDA-H-46001A` | NA | kW | <missing> | <missing> |
| 6 | `JDA-H-84101` | NA | kW | <missing> | <missing> |
| 7 | `JDA-H-84102` | NA | kW | <missing> | <missing> |
| 8 | `JDA-H-84103` | NA | kW | <missing> | <missing> |
| 9 | `JDA-H-84104` | NA | kW | <missing> | <missing> |
| 10 | `JDA-H-84201` | NA | kW | <missing> | <missing> |
| … | *(47 more tags with this pattern)* |  |  |  |  |

#### Property: `rated frequency` | Concept: Functional Physical | 56 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-G-84001A` | 50 | Hz | <missing> | <missing> |
| 2 | `JDA-G-84001B` | 50 | Hz | <missing> | <missing> |
| 3 | `JDA-G-84001C` | 50 | Hz | <missing> | <missing> |
| 4 | `JDA-TR-VV1B` | 50 | Hz | <missing> | <missing> |
| 5 | `JDA-TR-VV1A` | 50 | Hz | <missing> | <missing> |
| 6 | `JDA-TR-VV2B` | 50 | Hz | <missing> | <missing> |
| 7 | `JDA-TR-VV2A` | 50 | Hz | <missing> | <missing> |
| 8 | `JDA-PM-74002A` | 50 | Hz | <missing> | <missing> |
| 9 | `JDA-PM-54001` | 50 | hertz | <missing> | <missing> |
| 10 | `JDA-PM-62001` | 50 | hertz | <missing> | <missing> |
| … | *(46 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_RANGE_MAX` | Concept: Functional | 47 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-54TE-00020` | 450 |  | <missing> | <missing> |
| 2 | `JDA-54TE-00021` | 450 |  | <missing> | <missing> |
| 3 | `JDA-61TE-00020` | 450 |  | <missing> | <missing> |
| 4 | `JDA-62TE-00038` | 450 |  | <missing> | <missing> |
| 5 | `JDA-63TE-00023` | 450 |  | <missing> | <missing> |
| 6 | `JDA-63TE-00022` | 450 |  | <missing> | <missing> |
| 7 | `JDA-63LI-00008` | 2500 |  | <missing> | <missing> |
| 8 | `JDA-74LI-00012` | 2400 |  | <missing> | <missing> |
| 9 | `JDA-73LI-00104` | 3600 |  | <missing> | <missing> |
| 10 | `JDA-73LI-00206` | 3600 |  | <missing> | <missing> |
| … | *(37 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_RANGE_SI` | Concept: Functional | 45 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-54TE-00020` | NA |  | <missing> | <missing> |
| 2 | `JDA-54TE-00021` | NA |  | <missing> | <missing> |
| 3 | `JDA-61TE-00020` | NA |  | <missing> | <missing> |
| 4 | `JDA-62TE-00038` | NA |  | <missing> | <missing> |
| 5 | `JDA-63TE-00023` | NA |  | <missing> | <missing> |
| 6 | `JDA-63TE-00022` | NA |  | <missing> | <missing> |
| 7 | `JDA-63LI-00008` | 400 - 2400 mm |  | <missing> | <missing> |
| 8 | `JDA-74LI-00012` | 400 - 2800 mm |  | <missing> | <missing> |
| 9 | `JDA-73LI-00104` | 0 - 3600 mm |  | <missing> | <missing> |
| 10 | `JDA-73LI-00206` | 0 - 3600 mm |  | <missing> | <missing> |
| … | *(35 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_RANGE_MIN` | Concept: Functional | 45 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-54TE-00020` | -50 |  | <missing> | <missing> |
| 2 | `JDA-54TE-00021` | -50 |  | <missing> | <missing> |
| 3 | `JDA-61TE-00020` | -50 |  | <missing> | <missing> |
| 4 | `JDA-62TE-00038` | -50 |  | <missing> | <missing> |
| 5 | `JDA-63TE-00023` | -50 |  | <missing> | <missing> |
| 6 | `JDA-63TE-00022` | -50 |  | <missing> | <missing> |
| 7 | `JDA-63LI-00008` | 0 |  | <missing> | <missing> |
| 8 | `JDA-74LI-00012` | 0 |  | <missing> | <missing> |
| 9 | `JDA-73LI-00104` | 0 |  | <missing> | <missing> |
| 10 | `JDA-73LI-00206` | 0 |  | <missing> | <missing> |
| … | *(35 more tags with this pattern)* |  |  |  |  |

#### Property: `cable cross sectional area` | Concept: Functional | 41 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2A-F003H01` | 2.52 | mm | <missing> | <missing> |
| 2 | `JDA-84ESB-E2A-F004H01` | 2.52 | mm | <missing> | <missing> |
| 3 | `JDA-84ESB-E2B-F003H01` | 2.52 | mm | <missing> | <missing> |
| 4 | `JDA-H-47800H01` | 1.32 | mm | <missing> | <missing> |
| 5 | `JDA-84ESB-E2B-F006H04` | NA |  | <missing> | <missing> |
| 6 | `JDA-84ESB-E2B-F006H05` | NA |  | <missing> | <missing> |
| 7 | `JDA-84ESB-E2B-F006H06` | NA |  | <missing> | <missing> |
| 8 | `JDA-84ESB-E2B-F002H08` | NA |  | <missing> | <missing> |
| 9 | `JDA-84ESB-E2B-F001H03` | NA |  | <missing> | <missing> |
| 10 | `JDA-84ESB-E7-F401H02` | 2.52 | mm | <missing> | <missing> |
| … | *(31 more tags with this pattern)* |  |  |  |  |

#### Property: `number of cores` | Concept: Functional | 41 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2A-F003H01` | 2 |  | <missing> | <missing> |
| 2 | `JDA-84ESB-E2A-F004H01` | 2 |  | <missing> | <missing> |
| 3 | `JDA-84ESB-E2B-F003H01` | 2 |  | <missing> | <missing> |
| 4 | `JDA-H-47800H01` | 2 |  | <missing> | <missing> |
| 5 | `JDA-84ESB-E2B-F006H04` | 2 |  | <missing> | <missing> |
| 6 | `JDA-84ESB-E2B-F006H05` | 2 |  | <missing> | <missing> |
| 7 | `JDA-84ESB-E2B-F006H06` | 2 |  | <missing> | <missing> |
| 8 | `JDA-84ESB-E2B-F002H08` | 0 |  | <missing> | <missing> |
| 9 | `JDA-84ESB-E2B-F001H03` | 2 |  | <missing> | <missing> |
| 10 | `JDA-84ESB-E7-F401H02` | 2 |  | <missing> | <missing> |
| … | *(31 more tags with this pattern)* |  |  |  |  |

#### Property: `set point` | Concept: Functional | 39 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-63LI-00008` | NA |  | <missing> | <missing> |
| 2 | `JDA-74LI-00012` | NA |  | <missing> | <missing> |
| 3 | `JDA-73LI-00104` | NA |  | <missing> | <missing> |
| 4 | `JDA-73LI-00206` | NA |  | <missing> | <missing> |
| 5 | `JDA-54LI-00006` | NA |  | <missing> | <missing> |
| 6 | `JDA-84LC-00111` | NA |  | <missing> | <missing> |
| 7 | `JDA-84LC-00211` | NA |  | <missing> | <missing> |
| 8 | `JDA-84LC-00311` | NA |  | <missing> | <missing> |
| 9 | `JDA-62LZ-00005` | NA |  | <missing> | <missing> |
| 10 | `JDA-62LZ-00010` | NA |  | <missing> | <missing> |
| … | *(29 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_CALIBRATED_RANGE_LOWER_LIMIT` | Concept: Functional | 39 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-63LI-00008` | NA |  | <missing> | <missing> |
| 2 | `JDA-74LI-00012` | NA |  | <missing> | <missing> |
| 3 | `JDA-73LI-00104` | -75.7 |  | <missing> | <missing> |
| 4 | `JDA-73LI-00206` | -80.3 |  | <missing> | <missing> |
| 5 | `JDA-54LI-00006` | NA |  | <missing> | <missing> |
| 6 | `JDA-84LC-00111` | NA |  | <missing> | <missing> |
| 7 | `JDA-84LC-00211` | NA |  | <missing> | <missing> |
| 8 | `JDA-84LC-00311` | NA |  | <missing> | <missing> |
| 9 | `JDA-62LZ-00005` | NA |  | <missing> | <missing> |
| 10 | `JDA-62LZ-00010` | NA |  | <missing> | <missing> |
| … | *(29 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_CALIBRATED_RANGE_UPPER_LIMIT` | Concept: Functional | 39 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-63LI-00008` | NA |  | <missing> | <missing> |
| 2 | `JDA-74LI-00012` | NA |  | <missing> | <missing> |
| 3 | `JDA-73LI-00104` | 360.5 |  | <missing> | <missing> |
| 4 | `JDA-73LI-00206` | 261.2 |  | <missing> | <missing> |
| 5 | `JDA-54LI-00006` | NA |  | <missing> | <missing> |
| 6 | `JDA-84LC-00111` | NA |  | <missing> | <missing> |
| 7 | `JDA-84LC-00211` | NA |  | <missing> | <missing> |
| 8 | `JDA-84LC-00311` | NA |  | <missing> | <missing> |
| 9 | `JDA-62LZ-00005` | NA |  | <missing> | <missing> |
| 10 | `JDA-62LZ-00010` | NA |  | <missing> | <missing> |
| … | *(29 more tags with this pattern)* |  |  |  |  |

#### Property: `driver type` | Concept: Functional Physical | 36 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-G-84001A` | diesel engine |  | <missing> | <missing> |
| 2 | `JDA-G-84001B` | diesel engine |  | <missing> | <missing> |
| 3 | `JDA-G-84001C` | diesel engine |  | <missing> | <missing> |
| 4 | `JDA-K-86805B` | electric motor |  | <missing> | <missing> |
| 5 | `JDA-K-86806A` | electric motor |  | <missing> | <missing> |
| 6 | `JDA-K-86806B` | electric motor |  | <missing> | <missing> |
| 7 | `JDA-K-86805A` | electric motor |  | <missing> | <missing> |
| 8 | `JDA-X-79001` | diesel engine |  | <missing> | <missing> |
| 9 | `JDA-YLB-68001` | unset |  | <missing> | <missing> |
| 10 | `JDA-P-62001` | electric motor |  | <missing> | <missing> |
| … | *(26 more tags with this pattern)* |  |  |  |  |

#### Property: `upper limit operating discharge pressure` | Concept: Functional Physical | 30 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-K-86805B` | NA | pascal | <missing> | <missing> |
| 2 | `JDA-K-86806A` | NA | pascal | <missing> | <missing> |
| 3 | `JDA-K-86806B` | NA | pascal | <missing> | <missing> |
| 4 | `JDA-K-86805A` | NA | pascal | <missing> | <missing> |
| 5 | `JDA-P-62001` | 500000 | pascal | <missing> | <missing> |
| 6 | `JDA-P-54001` | 200000 | pascal | <missing> | <missing> |
| 7 | `JDA-P-61001` | 500000 | pascal | <missing> | <missing> |
| 8 | `JDA-P-46001A` | NA | pascal | <missing> | <missing> |
| 9 | `JDA-P-46001B` | NA | pascal | <missing> | <missing> |
| 10 | `JDA-P-47800` | NA | pascal | <missing> | <missing> |
| … | *(20 more tags with this pattern)* |  |  |  |  |

#### Property: `rated output power` | Concept: Functional Physical | 27 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-P-62001` | 4.46 | kW | <missing> | <missing> |
| 2 | `JDA-P-54001` | 1.78 | kW | <missing> | <missing> |
| 3 | `JDA-P-61001` | 1.35 | kW | <missing> | <missing> |
| 4 | `JDA-P-46001A` | NA | kW | <missing> | <missing> |
| 5 | `JDA-P-46001B` | NA | kW | <missing> | <missing> |
| 6 | `JDA-P-47800` | 0.0011 | kW | <missing> | <missing> |
| 7 | `JDA-P-47801` | 0.0011 | kW | <missing> | <missing> |
| 8 | `JDA-P-86851A` | NA | kW | <missing> | <missing> |
| 9 | `JDA-P-86850B` | NA | kW | <missing> | <missing> |
| 10 | `JDA-P-86851B` | NA | kW | <missing> | <missing> |
| … | *(17 more tags with this pattern)* |  |  |  |  |

#### Property: `fluid name` | Concept: Functional | 10 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-46LI-00006A` | Silicone 200 |  | <missing> | <missing> |
| 2 | `JDA-46LI-00007A` | Silicone 200 |  | <missing> | <missing> |
| 3 | `JDA-54LI-00006A` | Silicone 200 |  | <missing> | <missing> |
| 4 | `JDA-74LI-00012A` | Silicone 200 |  | <missing> | <missing> |
| 5 | `JDA-73LI-00104A` | Silicone 200 |  | <missing> | <missing> |
| 6 | `JDA-61LI-00002A` | Silicone 200 |  | <missing> | <missing> |
| 7 | `JDA-62LI-00004A` | Silicone 200 |  | <missing> | <missing> |
| 8 | `JDA-63LI-00008A` | Silicone 200 |  | <missing> | <missing> |
| 9 | `JDA-63LI-00008B` | Silicone 200 |  | <missing> | <missing> |
| 10 | `JDA-73LI-00206A` | Silicone 200 |  | <missing> | <missing> |

#### Property: `design specification` | Concept: Functional Physical | 6 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-S-84102` |  |  | <missing> | <missing> |
| 2 | `JDA-S-84202` |  |  | <missing> | <missing> |
| 3 | `JDA-S-84302` |  |  | <missing> | <missing> |
| 4 | `JDA-S-84103` |  |  | <missing> | <missing> |
| 5 | `JDA-S-84203` |  |  | <missing> | <missing> |
| 6 | `JDA-S-84303` |  |  | <missing> | <missing> |

#### Property: `rated output apparent power` | Concept: Functional Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-TR-VV1B` | 60 | kW | <missing> | <missing> |
| 2 | `JDA-TR-VV1A` | 60 | kW | <missing> | <missing> |
| 3 | `JDA-TR-VV2B` | 60 | kW | <missing> | <missing> |
| 4 | `JDA-TR-VV2A` | 60 | kW | <missing> | <missing> |

#### Property: `lower limit operating suction pressure` | Concept: Functional Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-K-86805B` | 2500000 | pascal | <missing> | <missing> |
| 2 | `JDA-K-86806A` | 2500000 | pascal | <missing> | <missing> |
| 3 | `JDA-K-86806B` | 2500000 | pascal | <missing> | <missing> |
| 4 | `JDA-K-86805A` | 2500000 | pascal | <missing> | <missing> |

#### Property: `valve tight shut off flag` | Concept: Functional | 3 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-86FCV-70802` | no |  | <missing> | <missing> |
| 2 | `JDA-86FCV-70800` | no |  | <missing> | <missing> |
| 3 | `JDA-86FCV-70801` | no |  | <missing> | <missing> |

#### Property: `height` | Concept: Functional Physical | 2 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-X-79001` | 85500 | mm | <missing> | <missing> |
| 2 | `JDA-XG-79007` | NA | mm | <missing> | <missing> |

#### Property: `pcs_REACTIVE_POWER` | Concept: Functional Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-S-68001` | NA |  | <missing> | <missing> |


### ⚠️ RDL_CSV_VALUE_MISMATCH (14,531 total gaps — 43 property groups)

#### Property: `rated current` | Concept: Functional Physical | 2,272 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-SB-E1A+A03.D1` | 52 | ampere | 52 | a |
| 2 | `JDA-SB-E1A+A05.L` | 160 | ampere | 160 | a |
| 3 | `JDA-SB-E1B+B06.P` | 160 | ampere | 160 | a |
| 4 | `JDA-SB-E1A+A05.J1` | 20 | ampere | 20 | a |
| 5 | `JDA-SB-E1B+B06.H1` | 20 | ampere | 20 | a |
| 6 | `JDA-SB-E1B+B06.H2` | 20 | ampere | 20 | a |
| 7 | `JDA-SB-E1A+A05.R` | 630 | ampere | 630 | a |
| 8 | `JDA-SB-E1B+B06.N` | 160 | ampere | 160 | a |
| 9 | `JDA-SB-E1A+A05.J2` | 52 | ampere | 52 | a |
| 10 | `JDA-SB-E1B+B06.L1` | 25 | ampere | 25 | a |
| … | *(2,262 more tags with this pattern)* |  |  |  |  |

#### Property: `rated voltage` | Concept: Functional Physical | 1,579 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-83ESB-V3C-F030S06` | 250 | V | 1000 | v |
| 2 | `JDA-74001-CEL` | 1000 | volt | 1000 | v |
| 3 | `JDA-74002-CEL` | 1000 | volt | 1000 | v |
| 4 | `JDA-74005-CEL` | 1000 | volt | 1000 | v |
| 5 | `JDA-74006-CEL` | 1000 | volt | 1000 | v |
| 6 | `JDA-73001-CEL` | 1000 | volt | 1000 | v |
| 7 | `JDA-73004-CEL` | 1000 | volt | 1000 | v |
| 8 | `JDA-73007-CEL` | 1000 | volt | 1000 | v |
| 9 | `JDA-62001-CELR-1` | 1000 | volt | 1000 | v |
| 10 | `JDA-62001-CELY-1` | 1000 | volt | 1000 | v |
| … | *(1,569 more tags with this pattern)* |  |  |  |  |

#### Property: `rated short circuit current` | Concept: Functional Physical | 1,544 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-74001-CEL` | 9800 | ampere | 9800 | a |
| 2 | `JDA-74002-CEL` | 9800 | ampere | 9800 | a |
| 3 | `JDA-74005-CEL` | 9800 | ampere | 9800 | a |
| 4 | `JDA-74006-CEL` | 9800 | ampere | 9800 | a |
| 5 | `JDA-73001-CEL` | 840 | ampere | 840 | a |
| 6 | `JDA-73004-CEL` | 840 | ampere | 840 | a |
| 7 | `JDA-73007-CEL` | 840 | ampere | 840 | a |
| 8 | `JDA-62001-CELR-1` | 42000 | ampere | 42000 | a |
| 9 | `JDA-62001-CELY-1` | 42000 | ampere | 42000 | a |
| 10 | `JDA-62001-CELB-1` | 42000 | ampere | 42000 | a |
| … | *(1,534 more tags with this pattern)* |  |  |  |  |

#### Property: `cable specification` | Concept: Functional | 999 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-H-47800H01` | 10BTV2-CT |  | 10 | btv2-ct |
| 2 | `JDA-46009-CEL` | BFOU M 0,6/1kV P5/P12/P105 |  | BFOU M 0;6/1kV P5/P12/P105 |  |
| 3 | `JDA-84011-CEL` | BFOU M 0,6/1kV P5/P12/P105 |  | BFOU M 0;6/1kV P5/P12/P105 |  |
| 4 | `JDA-84012-CEL` | BFOU M 0,6/1kV P5/P12/P105 |  | BFOU M 0;6/1kV P5/P12/P105 |  |
| 5 | `JDA-84013-CEL` | BFOU M 0,6/1kV P5/P12/P105 |  | BFOU M 0;6/1kV P5/P12/P105 |  |
| 6 | `JDA-84015-CEL` | BFOU M 0,6/1kV P5/P12/P105 |  | BFOU M 0;6/1kV P5/P12/P105 |  |
| 7 | `JDA-84016-CEL` | BFOU M 0,6/1kV P5/P12/P105 |  | BFOU M 0;6/1kV P5/P12/P105 |  |
| 8 | `JDA-84017-CEL` | BFOU M 0,6/1kV P5/P12/P105 |  | BFOU M 0;6/1kV P5/P12/P105 |  |
| 9 | `JDA-84027-CEL` | BFOU M 0,6/1kV P5/P12/P105 |  | BFOU M 0;6/1kV P5/P12/P105 |  |
| 10 | `JDA-84028-CEL` | BFOU M 0,6/1kV P5/P12/P105 |  | BFOU M 0;6/1kV P5/P12/P105 |  |
| … | *(989 more tags with this pattern)* |  |  |  |  |

#### Property: `breaking capacity` | Concept: Functional | 675 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-SB-E1A+A03.D1` | 36000 | ampere | 36000 | a |
| 2 | `JDA-SB-E1A+A05.L` | 36000 | ampere | 36000 | a |
| 3 | `JDA-SB-E1B+B06.P` | 36000 | ampere | 36000 | a |
| 4 | `JDA-SB-E1A+A05.J1` | 36000 | ampere | 36000 | a |
| 5 | `JDA-SB-E1B+B06.H1` | 36000 | ampere | 36000 | a |
| 6 | `JDA-SB-E1B+B06.H2` | 36000 | ampere | 36000 | a |
| 7 | `JDA-SB-E1A+A05.R` | 36000 | ampere | 36000 | a |
| 8 | `JDA-SB-E1B+B06.N` | 36000 | ampere | 36000 | a |
| 9 | `JDA-SB-E1A+A05.J2` | 36000 | ampere | 36000 | a |
| 10 | `JDA-SB-E1B+B06.L1` | 36000 | ampere | 36000 | a |
| … | *(665 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_MCB_RATING` | Concept: Functional | 671 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-SB-E1A+A03.D1` | 52 | ampere | 52 | a |
| 2 | `JDA-SB-E1A+A05.L` | 160 | ampere | 160 | a |
| 3 | `JDA-SB-E1B+B06.P` | 160 | ampere | 160 | a |
| 4 | `JDA-SB-E1A+A05.J1` | 20 | ampere | 20 | a |
| 5 | `JDA-SB-E1B+B06.H1` | 20 | ampere | 20 | a |
| 6 | `JDA-SB-E1B+B06.H2` | 20 | ampere | 20 | a |
| 7 | `JDA-SB-E1A+A05.R` | 630 | ampere | 630 | a |
| 8 | `JDA-SB-E1B+B06.N` | 160 | ampere | 160 | a |
| 9 | `JDA-SB-E1A+A05.J2` | 52 | ampere | 52 | a |
| 10 | `JDA-SB-E1B+B06.L1` | 25 | ampere | 25 | a |
| … | *(661 more tags with this pattern)* |  |  |  |  |

#### Property: `normal operating pressure` | Concept: Functional | 598 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | 0 | pascal | 0 | pa |
| 2 | `JDA-3"-H74012-LD30-N` | 75900000 | pascal | 75900000 | pa |
| 3 | `JDA-4"-P63005-13842-3FE` | 400000 | pascal | 400000 | pa |
| 4 | `JDA-3"-B51012-13842-N` | 0 | pascal | 0 | pa |
| 5 | `JDA-6"-P63004-13842-3FE` | 0 | pascal | 0 | pa |
| 6 | `JDA-3"-P02007-LD30-N` | 16500000 | pascal | 16500000 | pa |
| 7 | `JDA-16"-P02003-LD30-N` | 16500000 | pascal | 16500000 | pa |
| 8 | `JDA-3"-H74014-LD30-N` | 75900000 | pascal | 75900000 | pa |
| 9 | `JDA-6"-P01201-LD30-N` | 75900000 | pascal | 75900000 | pa |
| 10 | `JDA-8"-P01203-LD30-N` | 16500000 | pascal | 16500000 | pa |
| … | *(588 more tags with this pattern)* |  |  |  |  |

#### Property: `upper limit design pressure` | Concept: Functional | 598 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | 15.8 | pascal | 15.8 | pa |
| 2 | `JDA-3"-H74012-LD30-N` | 103400000 | pascal | 103400000 | pa |
| 3 | `JDA-4"-P63005-13842-3FE` | 1580000 | pascal | 1580000 | pa |
| 4 | `JDA-3"-B51012-13842-N` | 1580000 | pascal | 1580000 | pa |
| 5 | `JDA-6"-P63004-13842-3FE` | 1580000 | pascal | 1580000 | pa |
| 6 | `JDA-3"-P02007-LD30-N` | 103400000 | pascal | 103400000 | pa |
| 7 | `JDA-16"-P02003-LD30-N` | 103400000 | pascal | 103400000 | pa |
| 8 | `JDA-3"-H74014-LD30-N` | 103400000 | pascal | 103400000 | pa |
| 9 | `JDA-6"-P01201-LD30-N` | 103400000 | pascal | 103400000 | pa |
| 10 | `JDA-8"-P01203-LD30-N` | 103400000 | pascal | 103400000 | pa |
| … | *(588 more tags with this pattern)* |  |  |  |  |

#### Property: `cross section area` | Concept: Functional | 598 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | 1256mm2 |  | 1256 | mm2 |
| 2 | `JDA-3"-H74012-LD30-N` | 5024mm2 |  | 5024 | mm2 |
| 3 | `JDA-4"-P63005-13842-3FE` | 7850mm2 |  | 7850 | mm2 |
| 4 | `JDA-3"-B51012-13842-N` | 5024mm2 |  | 5024 | mm2 |
| 5 | `JDA-6"-P63004-13842-3FE` | 17663mm2 |  | 17663 | mm2 |
| 6 | `JDA-3"-P02007-LD30-N` | 5024mm2 |  | 5024 | mm2 |
| 7 | `JDA-16"-P02003-LD30-N` | 125600mm2 |  | 125600 | mm2 |
| 8 | `JDA-3"-H74014-LD30-N` | 5024mm2 |  | 5024 | mm2 |
| 9 | `JDA-6"-P01201-LD30-N` | 17663mm2 |  | 17663 | mm2 |
| 10 | `JDA-8"-P01203-LD30-N` | 31400mm2 |  | 31400 | mm2 |
| … | *(588 more tags with this pattern)* |  |  |  |  |

#### Property: `nominal pipe size` | Concept: Functional | 598 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | 1 1/2" |  | 1 1/2 | inch |
| 2 | `JDA-3"-H74012-LD30-N` | 3" |  | 3 | inch |
| 3 | `JDA-4"-P63005-13842-3FE` | 4" |  | 4 | inch |
| 4 | `JDA-3"-B51012-13842-N` | 3" |  | 3 | inch |
| 5 | `JDA-6"-P63004-13842-3FE` | 6" |  | 6 | inch |
| 6 | `JDA-3"-P02007-LD30-N` | 3" |  | 3 | inch |
| 7 | `JDA-16"-P02003-LD30-N` | 16" |  | 16 | inch |
| 8 | `JDA-3"-H74014-LD30-N` | 3" |  | 3 | inch |
| 9 | `JDA-6"-P01201-LD30-N` | 6" |  | 6 | inch |
| 10 | `JDA-8"-P01203-LD30-N` | 8" |  | 8 | inch |
| … | *(588 more tags with this pattern)* |  |  |  |  |

#### Property: `test pressure` | Concept: Functional | 597 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | 1 | pascal | 1 | pa |
| 2 | `JDA-3"-H74012-LD30-N` | 164700000 | pascal | 164700000 | pa |
| 3 | `JDA-4"-P63005-13842-3FE` | 3000000 | pascal | 3000000 | pa |
| 4 | `JDA-3"-B51012-13842-N` | 3000000 | pascal | 3000000 | pa |
| 5 | `JDA-6"-P63004-13842-3FE` | 3000000 | pascal | 3000000 | pa |
| 6 | `JDA-3"-P02007-LD30-N` | 164700000 | pascal | 164700000 | pa |
| 7 | `JDA-16"-P02003-LD30-N` | 164700000 | pascal | 164700000 | pa |
| 8 | `JDA-3"-H74014-LD30-N` | 164700000 | pascal | 164700000 | pa |
| 9 | `JDA-6"-P01201-LD30-N` | 164700000 | pascal | 164700000 | pa |
| 10 | `JDA-8"-P01203-LD30-N` | 164700000 | pascal | 164700000 | pa |
| … | *(587 more tags with this pattern)* |  |  |  |  |

#### Property: `upper limit operating pressure` | Concept: Functional | 590 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | 1 | pascal | 1 | pa |
| 2 | `JDA-3"-H74012-LD30-N` | 98100000 | pascal | 98100000 | pa |
| 3 | `JDA-4"-P63005-13842-3FE` | 1000000 | pascal | 1000000 | pa |
| 4 | `JDA-3"-B51012-13842-N` | 1000000 | pascal | 1000000 | pa |
| 5 | `JDA-6"-P63004-13842-3FE` | 1000000 | pascal | 1000000 | pa |
| 6 | `JDA-3"-P02007-LD30-N` | 18500000 | pascal | 18500000 | pa |
| 7 | `JDA-16"-P02003-LD30-N` | 18500000 | pascal | 18500000 | pa |
| 8 | `JDA-3"-H74014-LD30-N` | 98100000 | pascal | 98100000 | pa |
| 9 | `JDA-6"-P01201-LD30-N` | 98100000 | pascal | 98100000 | pa |
| 10 | `JDA-8"-P01203-LD30-N` | 18500000 | pascal | 18500000 | pa |
| … | *(580 more tags with this pattern)* |  |  |  |  |

#### Property: `making capacity` | Concept: Functional | 544 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-SB-E1A+A03.D1` | 75600 | ampere | 75600 | a |
| 2 | `JDA-SB-E1A+A05.L` | 75600 | ampere | 75600 | a |
| 3 | `JDA-SB-E1B+B06.P` | 75600 | ampere | 75600 | a |
| 4 | `JDA-SB-E1A+A05.J1` | 75600 | ampere | 75600 | a |
| 5 | `JDA-SB-E1B+B06.H1` | 75600 | ampere | 75600 | a |
| 6 | `JDA-SB-E1B+B06.H2` | 75600 | ampere | 75600 | a |
| 7 | `JDA-SB-E1A+A05.R` | 75600 | ampere | 75600 | a |
| 8 | `JDA-SB-E1B+B06.N` | 75600 | ampere | 75600 | a |
| 9 | `JDA-SB-E1A+A05.J2` | 75600 | ampere | 75600 | a |
| 10 | `JDA-SB-E1B+B06.L1` | 75600 | ampere | 75600 | a |
| … | *(534 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_RANGE_SI` | Concept: Functional | 520 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-GTT-84001A-1` | -50 - 10000 Deg C |  | -50 - 10000 | degc |
| 2 | `JDA-GTT-84001A-2` | 1 - -50 Deg C |  | 1 - -50 | degc |
| 3 | `JDA-GTT-84001A-8` | -50 - 200 Deg C |  | -50 - 200 | degc |
| 4 | `JDA-GTT-84001A-9` | 0 - 100 Deg C |  | 0 - 100 | degc |
| 5 | `JDA-GTT-84001A-10` | 0 - 200 Deg C |  | 0 - 200 | degc |
| 6 | `JDA-GTT-84001A-11` | 0 - 200 Deg C |  | 0 - 200 | degc |
| 7 | `JDA-GTT-84001A-12` | 0 - 200 Deg C |  | 0 - 200 | degc |
| 8 | `JDA-GTT-84001B-1` | -50 - 10000 Deg C |  | -50 - 10000 | degc |
| 9 | `JDA-GTT-84001B-2` | 1 - -50 Deg C |  | 1 - -50 | degc |
| 10 | `JDA-GTT-84001B-8` | -50 - 200 Deg C |  | -50 - 200 | degc |
| … | *(510 more tags with this pattern)* |  |  |  |  |

#### Property: `non destructive testing methods` | Concept: Functional | 490 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | 4D |  | 4 | d |
| 2 | `JDA-3"-H74012-LD30-N` | 1A |  | 1 | a |
| 3 | `JDA-4"-P63005-13842-3FE` | 3C |  | 3 | c |
| 4 | `JDA-3"-B51012-13842-N` | 3C |  | 3 | c |
| 5 | `JDA-6"-P63004-13842-3FE` | 3C |  | 3 | c |
| 6 | `JDA-3"-P02007-LD30-N` | 1A |  | 1 | a |
| 7 | `JDA-16"-P02003-LD30-N` | 1A |  | 1 | a |
| 8 | `JDA-3"-H74014-LD30-N` | 1A |  | 1 | a |
| 9 | `JDA-6"-P01201-LD30-N` | 1A |  | 1 | a |
| 10 | `JDA-8"-P01203-LD30-N` | 1A |  | 1 | a |
| … | *(480 more tags with this pattern)* |  |  |  |  |

#### Property: `estimated equivalent length` | Concept: Functional | 420 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-4"-P63005-13842-3FE` | 46147mm |  | 46147 | mm |
| 2 | `JDA-3"-B51012-13842-N` | 1211mm |  | 1211 | mm |
| 3 | `JDA-6"-P63004-13842-3FE` | 10338mm |  | 10338 | mm |
| 4 | `JDA-3"-P02007-LD30-N` | 20552mm |  | 20552 | mm |
| 5 | `JDA-16"-P02003-LD30-N` | 6050mm |  | 6050 | mm |
| 6 | `JDA-3"-H74014-LD30-N` | 33763mm |  | 33763 | mm |
| 7 | `JDA-6"-P01201-LD30-N` | 68116mm |  | 68116 | mm |
| 8 | `JDA-8"-P01203-LD30-N` | 9463mm |  | 9463 | mm |
| 9 | `JDA-6"-B51008-13451-N` | 53190mm |  | 53190 | mm |
| 10 | `JDA-6"-B51004-13451-N` | 2961mm |  | 2961 | mm |
| … | *(410 more tags with this pattern)* |  |  |  |  |

#### Property: `paint code` | Concept: Functional | 244 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | 2A |  | 2 | a |
| 2 | `JDA-3"-H74012-LD30-N` | 2A |  | 2 | a |
| 3 | `JDA-4"-P63005-13842-3FE` | 2A |  | 2 | a |
| 4 | `JDA-6"-P63004-13842-3FE` | 2A |  | 2 | a |
| 5 | `JDA-3"-P02007-LD30-N` | 2A |  | 2 | a |
| 6 | `JDA-16"-P02003-LD30-N` | 2A |  | 2 | a |
| 7 | `JDA-3"-H74014-LD30-N` | 2A |  | 2 | a |
| 8 | `JDA-6"-P01201-LD30-N` | 2A |  | 2 | a |
| 9 | `JDA-8"-P01203-LD30-N` | 2A |  | 2 | a |
| 10 | `JDA-3"-B51016-LD30-N` | 2A |  | 2 | a |
| … | *(234 more tags with this pattern)* |  |  |  |  |

#### Property: `emergency upper limit design temperature` | Concept: Functional | 156 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | 150degC |  | 150 | degc |
| 2 | `JDA-3/8"-W46948-TS03-2H` | 70degC |  | 70 | degc |
| 3 | `JDA-1"-W46939-TS03-2C` | 20degC |  | 20 | degc |
| 4 | `JDA-3/8"-W46944-TS03-2C` | 20degC |  | 20 | degc |
| 5 | `JDA-3/8"-W46940-TS03-2C` | 20degC |  | 20 | degc |
| 6 | `JDA-1"-W46960-TS03-2H` | 70degC |  | 70 | degc |
| 7 | `JDA-1"-W46946-TS03-2H` | 70degC |  | 70 | degc |
| 8 | `JDA-1/2"-W46942-TS03-2C` | 20degC |  | 20 | degc |
| 9 | `JDA-3/8"-W46952-TS03-2H` | 70degC |  | 70 | degc |
| 10 | `JDA-1/2"-W46941-TS03-2C` | 20degC |  | 20 | degc |
| … | *(146 more tags with this pattern)* |  |  |  |  |

#### Property: `rated frequency` | Concept: Functional Physical | 143 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-SB-E1A+AB00.1` | 50 | hertz | 50 | hz |
| 2 | `JDA-SB-E7-F503` | 50 | hertz | 50 | hz |
| 3 | `JDA-SB-E7-F102` | 50 | hertz | 50 | hz |
| 4 | `JDA-SB-E7-F205` | 50 | hertz | 50 | hz |
| 5 | `JDA-SB-E7-F502` | 50 | hertz | 50 | hz |
| 6 | `JDA-SB-E7-F401` | 50 | hertz | 50 | hz |
| 7 | `JDA-SB-E7-F204` | 50 | hertz | 50 | hz |
| 8 | `JDA-SB-E7-F520` | 50 | hertz | 50 | hz |
| 9 | `JDA-SB-E7-F300` | 50 | hertz | 50 | hz |
| 10 | `JDA-SB-E7-F529` | 50 | hertz | 50 | hz |
| … | *(133 more tags with this pattern)* |  |  |  |  |

#### Property: `insulation code` | Concept: Functional | 109 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | 2F |  | 2 | f |
| 2 | `JDA-4"-P63005-13842-3FE` | 3FE |  | 3 | fe |
| 3 | `JDA-6"-P63004-13842-3FE` | 3FE |  | 3 | fe |
| 4 | `JDA-3"-D62003-13842-3FE` | 3FE |  | 3 | fe |
| 5 | `JDA-2"-D62021-153842-3FE` | 3FE |  | 3 | fe |
| 6 | `JDA-3"-D62016-153842-3FE` | 3FE |  | 3 | fe |
| 7 | `JDA-3"-D62015-13842-3FE` | 3FE |  | 3 | fe |
| 8 | `JDA-4"-D61058-13842-2FE` | 2FE |  | 2 | fe |
| 9 | `JDA-2"-W46018-13842-2F` | 2F |  | 2 | f |
| 10 | `JDA-2"-W46021-13842-2F` | 2F |  | 2 | f |
| … | *(99 more tags with this pattern)* |  |  |  |  |

#### Property: `insulation thickness` | Concept: Functional | 109 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | 20mm |  | 20 | mm |
| 2 | `JDA-4"-P63005-13842-3FE` | 20mm |  | 20 | mm |
| 3 | `JDA-6"-P63004-13842-3FE` | 20mm |  | 20 | mm |
| 4 | `JDA-3"-D62003-13842-3FE` | 20mm |  | 20 | mm |
| 5 | `JDA-2"-D62021-153842-3FE` | 20mm |  | 20 | mm |
| 6 | `JDA-3"-D62016-153842-3FE` | 20mm |  | 20 | mm |
| 7 | `JDA-3"-D62015-13842-3FE` | 20mm |  | 20 | mm |
| 8 | `JDA-4"-D61058-13842-2FE` | 20mm |  | 20 | mm |
| 9 | `JDA-2"-W46018-13842-2F` | 20mm |  | 20 | mm |
| 10 | `JDA-2"-W46021-13842-2F` | 20mm |  | 20 | mm |
| … | *(99 more tags with this pattern)* |  |  |  |  |

#### Property: `nominal current` | Concept: Functional Physical | 104 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-BA-V1A` | 86.6 | ampere | 86.6 | a |
| 2 | `JDA-BA-V1B` | 86.6 | ampere | 86.6 | a |
| 3 | `JDA-BA-V2` | 78.3 | ampere | 78.3 | a |
| 4 | `JDA-BA-X1L` | 1400 | ampere | 1400 | a |
| 5 | `JDA-BA-X1R` | 1400 | ampere | 1400 | a |
| 6 | `JDA-BA-X2L` | 1400 | ampere | 1400 | a |
| 7 | `JDA-BA-X2R` | 1400 | ampere | 1400 | a |
| 8 | `JDA-BA-X3L` | 1400 | ampere | 1400 | a |
| 9 | `JDA-BA-X3R` | 1400 | ampere | 1400 | a |
| 10 | `JDA-H-62001` | 318 | ampere | 318 | a |
| … | *(94 more tags with this pattern)* |  |  |  |  |

#### Property: `remarks` | Concept: Functional | 87 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-2"-D61057-13842-N` | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere, ref.: PE(S)R Schedul… |  | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere; ref.: PE(S)R Schedul… |  |
| 2 | `JDA-6"-D61001-13842-N` | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere, ref.: PE(S)R Schedul… |  | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere; ref.: PE(S)R Schedul… |  |
| 3 | `JDA-3"-D61007-13842-N` | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere, ref.: PE(S)R Schedul… |  | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere; ref.: PE(S)R Schedul… |  |
| 4 | `JDA-4"-D61058-13842-2FE` | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere, ref.: PE(S)R Schedul… |  | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere; ref.: PE(S)R Schedul… |  |
| 5 | `JDA-3"-D61006-13842-N` | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere, ref.: PE(S)R Schedul… |  | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere; ref.: PE(S)R Schedul… |  |
| 6 | `JDA-3"-D61005-13842-N` | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere, ref.: PE(S)R Schedul… |  | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere; ref.: PE(S)R Schedul… |  |
| 7 | `JDA-2"-D61059-13842-N` | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere, ref.: PE(S)R Schedul… |  | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere; ref.: PE(S)R Schedul… |  |
| 8 | `JDA-3"-D61009-13842-N` | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere, ref.: PE(S)R Schedul… |  | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere; ref.: PE(S)R Schedul… |  |
| 9 | `JDA-2"-D61025-13842-N` | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere, ref.: PE(S)R Schedul… |  | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere; ref.: PE(S)R Schedul… |  |
| 10 | `JDA-6"-D61037-13842-2FE` | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere, ref.: PE(S)R Schedul… |  | Water Fill Leak Test only. Hydrostatic pressure test not practical as system is open to atmosphere; ref.: PE(S)R Schedul… |  |
| … | *(77 more tags with this pattern)* |  |  |  |  |

#### Property: `fluid name` | Concept: Functional | 45 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | Water, sewage black/grey [D] |  | Water; sewage black/grey [D] |  |
| 2 | `JDA-1 1/2"-G65891-BS20-N` | Water, fire fighting dry and wet systems [G] |  | Water; fire fighting dry and wet systems [G] |  |
| 3 | `JDA-3"-G65893-BS20-N` | Water, fire fighting dry and wet systems [G] |  | Water; fire fighting dry and wet systems [G] |  |
| 4 | `JDA-3"-G65890-BS20-N` | Water, fire fighting dry and wet systems [G] |  | Water; fire fighting dry and wet systems [G] |  |
| 5 | `JDA-1 1/2"-G65892-BS20-N` | Water, fire fighting dry and wet systems [G] |  | Water; fire fighting dry and wet systems [G] |  |
| 6 | `JDA-1 1/2"-W65873-13842-N` | Water, fire fighting dry and wet systems [W] |  | Water; fire fighting dry and wet systems [W] |  |
| 7 | `JDA-1 1/2"-W65853-13842-N` | Water, fire fighting dry and wet systems [W] |  | Water; fire fighting dry and wet systems [W] |  |
| 8 | `JDA-1 1/2"-W65864-13842-N` | Water, fire fighting dry and wet systems [W] |  | Water; fire fighting dry and wet systems [W] |  |
| 9 | `JDA-1 1/2"-W65879-13842-N` | Water, fire fighting dry and wet systems [W] |  | Water; fire fighting dry and wet systems [W] |  |
| 10 | `JDA-1 1/2"-W65876-13842-N` | Water, fire fighting dry and wet systems [W] |  | Water; fire fighting dry and wet systems [W] |  |
| … | *(35 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ALARM_LIMIT_HH` | Concept: Functional | 28 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-57QZ-04201` | 50% LEL |  | 50 | % lel |
| 2 | `JDA-57QZ-04202` | 50% LEL |  | 50 | % lel |
| 3 | `JDA-57QZ-04401` | 50% LEL |  | 50 | % lel |
| 4 | `JDA-57QZ-04402` | 50% LEL |  | 50 | % lel |
| 5 | `JDA-57QZ-04101` | 50% LEL |  | 50 | % lel |
| 6 | `JDA-57QZ-04102` | 50% LEL |  | 50 | % lel |
| 7 | `JDA-57QZ-04303` | 50% LEL |  | 50 | % lel |
| 8 | `JDA-57QZ-04304` | 50% LEL |  | 50 | % lel |
| 9 | `JDA-57QZ-04701` | 50% LEL |  | 50 | % lel |
| 10 | `JDA-57QZ-04702` | 50% LEL |  | 50 | % lel |
| … | *(18 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_RANGE_MAX` | Concept: Functional | 28 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-74UZV-00002` | 345 | BARG | 345 | bar(g) |
| 2 | `JDA-73UZV-00203` | 345 | BARG | 345 | bar(g) |
| 3 | `JDA-54UZV-00001` | 345 | BARG | 345 | bar(g) |
| 4 | `JDA-73UZV-00201` | 345 | BARG | 345 | bar(g) |
| 5 | `JDA-73UZV-00102` | 345 | BARG | 345 | bar(g) |
| 6 | `JDA-01UZV-02003` | 345 | BARG | 345 | bar(g) |
| 7 | `JDA-74UZV-02001` | 345 | BARG | 345 | bar(g) |
| 8 | `JDA-73UZV-00204` | 345 | BARG | 345 | bar(g) |
| 9 | `JDA-63UZV-00002` | 345 | BARG | 345 | bar(g) |
| 10 | `JDA-74UZV-00001` | 345 | BARG | 345 | bar(g) |
| … | *(18 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_RANGE_MIN` | Concept: Functional | 28 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-74UZV-00002` | 250 | BARG | 250 | bar(g) |
| 2 | `JDA-73UZV-00203` | 250 | BARG | 250 | bar(g) |
| 3 | `JDA-54UZV-00001` | 250 | BARG | 250 | bar(g) |
| 4 | `JDA-73UZV-00201` | 250 | BARG | 250 | bar(g) |
| 5 | `JDA-73UZV-00102` | 250 | BARG | 250 | bar(g) |
| 6 | `JDA-01UZV-02003` | 240 | BARG | 240 | bar(g) |
| 7 | `JDA-74UZV-02001` | 250 | BARG | 250 | bar(g) |
| 8 | `JDA-73UZV-00204` | 250 | BARG | 250 | bar(g) |
| 9 | `JDA-63UZV-00002` | 250 | BARG | 250 | bar(g) |
| 10 | `JDA-74UZV-00001` | 250 | BARG | 250 | bar(g) |
| … | *(18 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ALARM_LIMIT_WH` | Concept: Functional | 27 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-57QZ-04201` | 20% LEL |  | 20 | % lel |
| 2 | `JDA-57QZ-04202` | 20% LEL |  | 20 | % lel |
| 3 | `JDA-57QZ-04401` | 20% LEL |  | 20 | % lel |
| 4 | `JDA-57QZ-04402` | 20% LEL |  | 20 | % lel |
| 5 | `JDA-57QZ-04101` | 20% LEL |  | 20 | % lel |
| 6 | `JDA-57QZ-04102` | 20% LEL |  | 20 | % lel |
| 7 | `JDA-57QZ-04303` | 20% LEL |  | 20 | % lel |
| 8 | `JDA-57QZ-04304` | 20% LEL |  | 20 | % lel |
| 9 | `JDA-57QZ-04701` | 20% LEL |  | 20 | % lel |
| 10 | `JDA-57QZ-04702` | 20% LEL |  | 20 | % lel |
| … | *(17 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ALARM_LIMIT_WL` | Concept: Functional | 27 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-57QZ-04201` | 10% LEL |  | 10 | % lel |
| 2 | `JDA-57QZ-04202` | 10% LEL |  | 10 | % lel |
| 3 | `JDA-57QZ-04401` | 10% LEL |  | 10 | % lel |
| 4 | `JDA-57QZ-04402` | 10% LEL |  | 10 | % lel |
| 5 | `JDA-57QZ-04101` | 10% LEL |  | 10 | % lel |
| 6 | `JDA-57QZ-04102` | 10% LEL |  | 10 | % lel |
| 7 | `JDA-57QZ-04303` | 10% LEL |  | 10 | % lel |
| 8 | `JDA-57QZ-04304` | 10% LEL |  | 10 | % lel |
| 9 | `JDA-57QZ-04701` | 10% LEL |  | 10 | % lel |
| 10 | `JDA-57QZ-04702` | 10% LEL |  | 10 | % lel |
| … | *(17 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_REACTIVE_POWER` | Concept: Functional Physical | 26 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-MM-47811` | 0.67kVAr |  | 0.67 | kvar |
| 2 | `JDA-PM-47801` | 0.67kVAr |  | 0.67 | kvar |
| 3 | `JDA-PM-47800` | 0.67kVAr |  | 0.67 | kvar |
| 4 | `JDA-KM-86804` | 0.4kVAr |  | 0.4 | kvar |
| 5 | `JDA-KM-86802A` | 1.2kVAr |  | 1.2 | kvar |
| 6 | `JDA-KM-86803A` | 0.4kVAr |  | 0.4 | kvar |
| 7 | `JDA-KM-86803B` | 0.4kVAr |  | 0.4 | kvar |
| 8 | `JDA-KM-86802B` | 1.2kVAr |  | 1.2 | kvar |
| 9 | `JDA-KM-86801B` | 5.43kVAr |  | 5.43 | kvar |
| 10 | `JDA-KM-86801A` | 5.43kVAr |  | 5.43 | kvar |
| … | *(16 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_FUSE_SIZE` | Concept: Functional | 12 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-CP-84103R` | 63 | ampere | 63 | a |
| 2 | `JDA-CP-84103L` | 63 | ampere | 63 | a |
| 3 | `JDA-CP-84203L` | 63 | ampere | 63 | a |
| 4 | `JDA-CP-84203R` | 63 | ampere | 63 | a |
| 5 | `JDA-CP-84303L` | 63 | ampere | 63 | a |
| 6 | `JDA-CP-84303R` | 63 | ampere | 63 | a |
| 7 | `JDA-H-84102` | 4 | ampere | 4 | a |
| 8 | `JDA-H-84202` | 4 | ampere | 4 | a |
| 9 | `JDA-H-84302` | 4 | ampere | 4 | a |
| 10 | `JDA-H-84802` | 1000 | ampere | 1000 | a |
| … | *(2 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_CALIBRATED_RANGE_LOWER_LIMIT` | Concept: Functional | 10 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-01PG-02053` | -1% |  | -1 | % |
| 2 | `JDA-01PG-03053` | -1% |  | -1 | % |
| 3 | `JDA-01PG-05053` | -1% |  | -1 | % |
| 4 | `JDA-01PG-06053` | -1% |  | -1 | % |
| 5 | `JDA-01PG-04053` | -1% |  | -1 | % |
| 6 | `JDA-01PG-07053` | -1% |  | -1 | % |
| 7 | `JDA-01PG-08053` | -1% |  | -1 | % |
| 8 | `JDA-01PG-09053` | -1% |  | -1 | % |
| 9 | `JDA-54PG-00023` | - 20 | deg C | - 20 | degc |
| 10 | `JDA-63PG-00025` | - 20 | deg C | - 20 | degc |

#### Property: `pcs_CALIBRATED_RANGE_UPPER_LIMIT` | Concept: Functional | 10 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-01PG-02053` | +1% |  | +1 | % |
| 2 | `JDA-01PG-03053` | +1% |  | +1 | % |
| 3 | `JDA-01PG-05053` | +1% |  | +1 | % |
| 4 | `JDA-01PG-06053` | +1% |  | +1 | % |
| 5 | `JDA-01PG-04053` | +1% |  | +1 | % |
| 6 | `JDA-01PG-07053` | +1% |  | +1 | % |
| 7 | `JDA-01PG-08053` | +1% |  | +1 | % |
| 8 | `JDA-01PG-09053` | +1% |  | +1 | % |
| 9 | `JDA-54PG-00023` | 100 | deg C | 100 | degc |
| 10 | `JDA-63PG-00025` | 100 | deg C | 100 | degc |

#### Property: `normal operating inlet pressure` | Concept: Functional | 8 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-M-47811` | 1 | pascal | 1 | pa |
| 2 | `JDA-P-62001` | 0 | pascal | 0 | pa |
| 3 | `JDA-P-54001` | 0 | pascal | 0 | pa |
| 4 | `JDA-P-61001` | 0 | pascal | 0 | pa |
| 5 | `JDA-P-86851A` | 400000 | pascal | 400000 | pa |
| 6 | `JDA-P-86850B` | 400000 | pascal | 400000 | pa |
| 7 | `JDA-P-86851B` | 400000 | pascal | 400000 | pa |
| 8 | `JDA-P-86850A` | 400000 | pascal | 400000 | pa |

#### Property: `pcs_ALARM_LIMIT_LL` | Concept: Functional | 7 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-57QZ-03301` | 5-60% LFL |  | 5-60 | % lfl |
| 2 | `JDA-57QZ-03302` | 5-60% LFL |  | 5-60 | % lfl |
| 3 | `JDA-57QZ-03303` | 5-60% LFL |  | 5-60 | % lfl |
| 4 | `JDA-65PZ-00801` | 5 Barg |  | 5 | bar(g) |
| 5 | `JDA-84TT-00129` | 4degree |  | 4 | degree |
| 6 | `JDA-84TT-00229` | 4degree |  | 4 | degree |
| 7 | `JDA-84TT-00329` | 4degrees |  | 4 | degrees |

#### Property: `normal operating outlet pressure` | Concept: Functional | 7 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-P-62001` | 500000 | pascal | 500000 | pa |
| 2 | `JDA-P-54001` | 200000 | pascal | 200000 | pa |
| 3 | `JDA-P-61001` | 208000 | pascal | 208000 | pa |
| 4 | `JDA-P-86851A` | 400000 | pascal | 400000 | pa |
| 5 | `JDA-P-86850B` | 400000 | pascal | 400000 | pa |
| 6 | `JDA-P-86851B` | 400000 | pascal | 400000 | pa |
| 7 | `JDA-P-86850A` | 400000 | pascal | 400000 | pa |

#### Property: `upper limit operating inlet pressure` | Concept: Functional | 7 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-P-62001` | 0 | pascal | 0 | pa |
| 2 | `JDA-P-54001` | 0 | pascal | 0 | pa |
| 3 | `JDA-P-61001` | 0 | pascal | 0 | pa |
| 4 | `JDA-P-86851A` | 1600000 | pascal | 1600000 | pa |
| 5 | `JDA-P-86850B` | 1600000 | pascal | 1600000 | pa |
| 6 | `JDA-P-86851B` | 1600000 | pascal | 1600000 | pa |
| 7 | `JDA-P-86850A` | 1600000 | pascal | 1600000 | pa |

#### Property: `pcs_primary_voltage` | Concept: Functional | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-TR-VV1B` | 400 | volt | 400 | v |
| 2 | `JDA-TR-VV1A` | 400 | volt | 400 | v |
| 3 | `JDA-TR-VV2B` | 400 | volt | 400 | v |
| 4 | `JDA-TR-VV2A` | 400 | volt | 400 | v |

#### Property: `secondary voltage` | Concept: Functional Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-TR-VV1B` | 230 | volt | 230 | v |
| 2 | `JDA-TR-VV1A` | 230 | volt | 230 | v |
| 3 | `JDA-TR-VV2B` | 230 | volt | 230 | v |
| 4 | `JDA-TR-VV2A` | 230 | volt | 230 | v |

#### Property: `normal operating differential pressure` | Concept: Functional | 3 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-P-62001` | 500000 | pascal | 500000 | pa |
| 2 | `JDA-P-54001` | 200000 | pascal | 200000 | pa |
| 3 | `JDA-P-61001` | 208000 | pascal | 208000 | pa |

#### Property: `normal operating vapour pressure` | Concept: Functional | 3 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-P-62001` | 101000 | pascal | 101000 | pa |
| 2 | `JDA-P-54001` | 150 | pascal | 150 | pa |
| 3 | `JDA-P-63001` | 0 | pascal | 0 | pa |

#### Property: `pcs_DUTY_STANDBY` | Concept: Functional | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-H-01001` | 0W |  | 0 | w |

#### Property: `product stored` | Concept: Functional | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-YSE-65002` | Water, fire fighting fresh |  | Water; fire fighting fresh |  |


### ⚠️ RDL_CSV_VALUE_MISSING — RDL has value, CSV is blank (279 total gaps — 50 property groups)

#### Property: `actual length` | Concept: Functional Physical | 24 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-EE-E1A` |  |  | <blank> |  |
| 2 | `JDA-EE-E1B` |  |  | <blank> |  |
| 3 | `JDA-EE-E1C` |  |  | <blank> |  |
| 4 | `JDA-EE-V1A` |  |  | <blank> |  |
| 5 | `JDA-EE-V1B` |  |  | <blank> |  |
| 6 | `JDA-C-63TE-00022/63TI-00022` | unset |  | <blank> |  |
| 7 | `JDA-57-JE-00001-01/57-RIG-001` | unset |  | <blank> |  |
| 8 | `JDA-57-JE-00001-02/57-RIG-001` | unset |  | <blank> |  |
| 9 | `JDA-83ESB-V3C-F05502` | unset |  | <blank> |  |
| 10 | `JDA-83ESB-V3C-F05503` | unset |  | <blank> |  |
| … | *(14 more tags with this pattern)* |  |  |  |  |

#### Property: `cable specification` | Concept: Functional | 19 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-EE-E1A` | unset |  | <blank> |  |
| 2 | `JDA-EE-E1B` | unset |  | <blank> |  |
| 3 | `JDA-EE-E1C` | unset |  | <blank> |  |
| 4 | `JDA-EE-V1A` | unset |  | <blank> |  |
| 5 | `JDA-EE-V1B` | unset |  | <blank> |  |
| 6 | `JDA-75-11-TCA-840` | unset |  | <blank> |  |
| 7 | `JDA-75-11-TCA-841` | unset |  | <blank> |  |
| 8 | `JDA-75-11-TCA-842` | unset |  | <blank> |  |
| 9 | `JDA-75-11-TCA-843` | unset |  | <blank> |  |
| 10 | `JDA-75-11-TCA-844` | unset |  | <blank> |  |
| … | *(9 more tags with this pattern)* |  |  |  |  |

#### Property: `pressure equipment category` | Concept: Functional Physical | 14 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-01SP-0131` | unset |  | <blank> |  |
| 2 | `JDA-01SP-0133` | unset |  | <blank> |  |
| 3 | `JDA-01SP-0090` | unset |  | <blank> |  |
| 4 | `JDA-01SP-0091` | unset |  | <blank> |  |
| 5 | `JDA-01SP-0137` | unset |  | <blank> |  |
| 6 | `JDA-01SP-0139` | unset |  | <blank> |  |
| 7 | `JDA-02SP-0141` | unset |  | <blank> |  |
| 8 | `JDA-02SP-0142` | unset |  | <blank> |  |
| 9 | `JDA-01SP-0258` | unset |  | <blank> |  |
| 10 | `JDA-01SP-0146` | unset |  | <blank> |  |
| … | *(4 more tags with this pattern)* |  |  |  |  |

#### Property: `paint code` | Concept: Functional | 14 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-3/8"-G59113-TLX3-N` |  |  | <blank> |  |
| 2 | `JDA-1"-G59024-13844-N` |  |  | <blank> |  |
| 3 | `JDA-1"-G59025-13844-N` |  |  | <blank> |  |
| 4 | `JDA-1"-G59026-13844-N` |  |  | <blank> |  |
| 5 | `JDA-2"-H74031-13842-N` |  |  | <blank> |  |
| 6 | `JDA-2"-H74032-13842-N` |  |  | <blank> |  |
| 7 | `JDA-2"-D61083-13842-N` |  |  | <blank> |  |
| 8 | `JDA-1"-E73050-LD30-N` |  |  | <blank> |  |
| 9 | `JDA-1"-E73051-LD30-N` |  |  | <blank> |  |
| 10 | `JDA-1"-E73052-LD30-N` |  |  | <blank> |  |
| … | *(4 more tags with this pattern)* |  |  |  |  |

#### Property: `estimated length` | Concept: Functional | 13 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-3"-H74012-LD30-N` | unset |  | <blank> |  |
| 2 | `JDA-2"-D62021-153842-3FE` | unset |  | <blank> |  |
| 3 | `JDA-3"-D62016-153842-3FE` | unset |  | <blank> |  |
| 4 | `JDA-3"-H74018-LD30-N` | unset |  | <blank> |  |
| 5 | `JDA-3"-H74013-LD30-N` | unset |  | <blank> |  |
| 6 | `JDA-2"-D62022-153842-3FE` | unset |  | <blank> |  |
| 7 | `JDA-2"-X73010-13842-N` | unset |  | <blank> |  |
| 8 | `JDA-9/16"-D72053-13842-N` | unset |  | <blank> |  |
| 9 | `JDA-9/16"-D72054-13842-N` | unset |  | <blank> |  |
| 10 | `JDA-3"-H74019-LD30-N` | unset |  | <blank> |  |
| … | *(3 more tags with this pattern)* |  |  |  |  |

#### Property: `estimated equivalent length` | Concept: Functional | 13 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-3"-H74012-LD30-N` | unset |  | <blank> |  |
| 2 | `JDA-2"-D62021-153842-3FE` | unset |  | <blank> |  |
| 3 | `JDA-3"-D62016-153842-3FE` | unset |  | <blank> |  |
| 4 | `JDA-3"-H74018-LD30-N` | unset |  | <blank> |  |
| 5 | `JDA-3"-H74013-LD30-N` | unset |  | <blank> |  |
| 6 | `JDA-2"-D62022-153842-3FE` | unset |  | <blank> |  |
| 7 | `JDA-2"-X73010-13842-N` | unset |  | <blank> |  |
| 8 | `JDA-9/16"-D72053-13842-N` | unset |  | <blank> |  |
| 9 | `JDA-9/16"-D72054-13842-N` | unset |  | <blank> |  |
| 10 | `JDA-3"-H74019-LD30-N` | unset |  | <blank> |  |
| … | *(3 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ALARM_LIMIT_WH` | Concept: Functional | 12 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-01PZO-02045` |  |  | <blank> |  |
| 2 | `JDA-01PZC-02045` |  |  | <blank> |  |
| 3 | `JDA-01PZO-03045` |  |  | <blank> |  |
| 4 | `JDA-01PZC-03045` |  |  | <blank> |  |
| 5 | `JDA-01PZO-05045` |  |  | <blank> |  |
| 6 | `JDA-01PZC-05045` |  |  | <blank> |  |
| 7 | `JDA-01PZO-06045` |  |  | <blank> |  |
| 8 | `JDA-01PZC-06045` |  |  | <blank> |  |
| 9 | `JDA-57XA-00006` |  |  | <blank> |  |
| 10 | `JDA-57XA-00007` |  |  | <blank> |  |
| … | *(2 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ALARM_LIMIT_WL` | Concept: Functional | 12 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-01PZO-02045` |  |  | <blank> |  |
| 2 | `JDA-01PZC-02045` |  |  | <blank> |  |
| 3 | `JDA-01PZO-03045` |  |  | <blank> |  |
| 4 | `JDA-01PZC-03045` |  |  | <blank> |  |
| 5 | `JDA-01PZO-05045` |  |  | <blank> |  |
| 6 | `JDA-01PZC-05045` |  |  | <blank> |  |
| 7 | `JDA-01PZO-06045` |  |  | <blank> |  |
| 8 | `JDA-01PZC-06045` |  |  | <blank> |  |
| 9 | `JDA-57XA-00006` |  |  | <blank> |  |
| 10 | `JDA-57XA-00007` |  |  | <blank> |  |
| … | *(2 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ALARM_LIMIT_HH` | Concept: Functional | 11 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-01PZO-02045` |  |  | <blank> |  |
| 2 | `JDA-01PZC-02045` |  |  | <blank> |  |
| 3 | `JDA-01PZO-03045` |  |  | <blank> |  |
| 4 | `JDA-01PZC-03045` |  |  | <blank> |  |
| 5 | `JDA-01PZO-05045` |  |  | <blank> |  |
| 6 | `JDA-01PZC-05045` |  |  | <blank> |  |
| 7 | `JDA-01PZO-06045` |  |  | <blank> |  |
| 8 | `JDA-01PZC-06045` |  |  | <blank> |  |
| 9 | `JDA-57XA-00006` |  |  | <blank> |  |
| 10 | `JDA-57XA-00007` |  |  | <blank> |  |
| … | *(1 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ALARM_LIMIT_LL` | Concept: Functional | 11 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-01PZO-02045` |  |  | <blank> |  |
| 2 | `JDA-01PZC-02045` |  |  | <blank> |  |
| 3 | `JDA-01PZO-03045` |  |  | <blank> |  |
| 4 | `JDA-01PZC-03045` |  |  | <blank> |  |
| 5 | `JDA-01PZO-05045` |  |  | <blank> |  |
| 6 | `JDA-01PZC-05045` |  |  | <blank> |  |
| 7 | `JDA-01PZO-06045` |  |  | <blank> |  |
| 8 | `JDA-01PZC-06045` |  |  | <blank> |  |
| 9 | `JDA-57XA-00006` |  |  | <blank> |  |
| 10 | `JDA-57XA-00007` |  |  | <blank> |  |
| … | *(1 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_WN_FREQUENCY_RATIO` | Concept: Functional | 7 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-61SP-0396` | unset |  | <blank> |  |
| 2 | `JDA-61SP-0397` | unset |  | <blank> |  |
| 3 | `JDA-62SP-0398` | unset |  | <blank> |  |
| 4 | `JDA-62SP-0399` | unset |  | <blank> |  |
| 5 | `JDA-62SP-0400` | unset |  | <blank> |  |
| 6 | `JDA-63SP-0401` | unset |  | <blank> |  |
| 7 | `JDA-63SP-0402` | unset |  | <blank> |  |

#### Property: `normal operating inlet pressure` | Concept: Functional | 6 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-K-84101` | unset |  | <blank> |  |
| 2 | `JDA-K-84102` | unset |  | <blank> |  |
| 3 | `JDA-K-84201` | unset |  | <blank> |  |
| 4 | `JDA-K-84301` | unset |  | <blank> |  |
| 5 | `JDA-K-84202` | unset |  | <blank> |  |
| 6 | `JDA-K-84302` | unset |  | <blank> |  |

#### Property: `normal operating inlet temperature` | Concept: Functional | 6 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-K-84101` | unset |  | <blank> |  |
| 2 | `JDA-K-84102` | unset |  | <blank> |  |
| 3 | `JDA-K-84201` | unset |  | <blank> |  |
| 4 | `JDA-K-84301` | unset |  | <blank> |  |
| 5 | `JDA-K-84202` | unset |  | <blank> |  |
| 6 | `JDA-K-84302` | unset |  | <blank> |  |

#### Property: `normal operating mass flow rate` | Concept: Functional | 6 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-K-84101` | unset |  | <blank> |  |
| 2 | `JDA-K-84102` | unset |  | <blank> |  |
| 3 | `JDA-K-84201` | unset |  | <blank> |  |
| 4 | `JDA-K-84301` | unset |  | <blank> |  |
| 5 | `JDA-K-84202` | unset |  | <blank> |  |
| 6 | `JDA-K-84302` | unset |  | <blank> |  |

#### Property: `fluid name` | Concept: Functional | 6 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-S-84102` |  |  | <blank> |  |
| 2 | `JDA-S-84202` |  |  | <blank> |  |
| 3 | `JDA-S-84302` |  |  | <blank> |  |
| 4 | `JDA-S-84103` |  |  | <blank> |  |
| 5 | `JDA-S-84203` |  |  | <blank> |  |
| 6 | `JDA-S-84303` |  |  | <blank> |  |

#### Property: `pcs_RANGE_SI` | Concept: Functional | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-01HS-02031` |  |  | <blank> |  |
| 2 | `JDA-01HS-03031` |  |  | <blank> |  |
| 3 | `JDA-01HS-05031` |  |  | <blank> |  |
| 4 | `JDA-01HS-06031` |  |  | <blank> |  |
| 5 | `JDA-56XZ-00008` |  |  | <blank> |  |

#### Property: `safety integrity level` | Concept: Functional | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-83CP-V2-052` |  |  | <blank> |  |
| 2 | `JDA-01XI-02013` |  |  | <blank> |  |
| 3 | `JDA-01XI-05013` |  |  | <blank> |  |
| 4 | `JDA-01XI-03013` |  |  | <blank> |  |
| 5 | `JDA-01XI-06013` |  |  | <blank> |  |

#### Property: `lower limit wall thickness` | Concept: Functional | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `net tank capacity` | Concept: Functional Physical | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `nominal tank capacity` | Concept: Functional | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `product stored` | Concept: Functional | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `sacrificial anodes` | Concept: Functional Physical | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `tank roof type` | Concept: Functional Physical | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `tank usage type` | Concept: Functional | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `total tank capacity` | Concept: Functional | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `upper limit design product fill height` | Concept: Functional | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `upper limit design product inflow rate` | Concept: Functional | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `upper limit design product outflow rate` | Concept: Functional | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `tank shape` | Concept: Functional | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `diameter` | Concept: Functional | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `SIL_Level` | Concept: Functional | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-02WE-00101` | unset |  | <blank> |  |
| 2 | `JDA-02WE-00102` | unset |  | <blank> |  |
| 3 | `JDA-02WE-00204` | unset |  | <blank> |  |
| 4 | `JDA-62WE-00004` | unset |  | <blank> |  |

#### Property: `pcs_VALVE_SIZE` | Concept: Functional Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-73NRV-0601` | unset |  | <blank> |  |
| 2 | `JDA-73NRV-0501` | unset |  | <blank> |  |
| 3 | `JDA-73NRV-0301` | unset |  | <blank> |  |
| 4 | `JDA-73NRV-0201` | unset |  | <blank> |  |

#### Property: `lower limit operating heat tracing temperature` | Concept: Functional | 3 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-4"-D61035-13842-N` | unset |  | <blank> |  |
| 2 | `JDA-2"-D61029-13842-N` | unset |  | <blank> |  |
| 3 | `JDA-2"-E73033-13411-N` | unset |  | <blank> |  |

#### Property: `lower limit operating temperature` | Concept: Functional | 2 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-P-62001` | unset |  | <blank> |  |
| 2 | `JDA-P-54001` | unset |  | <blank> |  |

#### Property: `rated short circuit current` | Concept: Functional Physical | 2 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-83CP-V2-122` | unset |  | <blank> |  |
| 2 | `JDA-83CP-V2-127` | unset |  | <blank> |  |

#### Property: `pcs_ACTUAL_LOAD` | Concept: Functional Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2B-F002H08` |  |  | <blank> |  |

#### Property: `controlled property` | Concept: Functional | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-56XZ-00008-LOOP` | unset |  | <blank> |  |

#### Property: `pcs_CALIBRATED_RANGE_LOWER_LIMIT` | Concept: Functional | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-56XZ-00008` |  |  | <blank> |  |

#### Property: `pcs_CALIBRATED_RANGE_UPPER_LIMIT` | Concept: Functional | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-56XZ-00008` |  |  | <blank> |  |

#### Property: `pipeline colour code` | Concept: Functional | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-3/8"-G59113-TLX3-N` | unset |  | <blank> |  |

#### Property: `test pressure` | Concept: Functional | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-3/8"-G59113-TLX3-N` | unset |  | <blank> |  |

#### Property: `chemical cleaning required` | Concept: Functional | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-3/8"-G59113-TLX3-N` | unset |  | <blank> |  |

#### Property: `stress analysis required` | Concept: Functional | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-3/8"-G59113-TLX3-N` | unset |  | <blank> |  |

#### Property: `non destructive testing methods` | Concept: Functional | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-3/8"-G59113-TLX3-N` |  |  | <blank> |  |

#### Property: `critical line` | Concept: Functional | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-3/8"-G59113-TLX3-N` |  |  | <blank> |  |

#### Property: `H2S Concentration` | Concept: Functional | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-P-63001` | unset |  | <blank> |  |

#### Property: `explosion protection gas group` | Concept: Functional Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `explosion protection temperature class` | Concept: Functional Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `explosion protection zone` | Concept: Functional Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `rated voltage` | Concept: Functional Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-75-38-TJB-801` | unset |  | <blank> |  |


### File-011 (Equipment Property Values) Details

### 🚫 RDL_CSV_MISSING — Critical: in RDL, absent from CSV-011 (24,067 total gaps — 45 property groups)

#### Property: `actual length` | Concept: Functional Physical | 3,972 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-79-PLC-001-03/57-JE-00010` | 45000 | mm | <missing> | <missing> |
| 2 | `JDA-57-JE-00010/01-SAN-002` | 62360 | mm | <missing> | <missing> |
| 3 | `JDA-01-SAN-001-02/55-PCS-005` | 20000 | mm | <missing> | <missing> |
| 4 | `JDA-C-02MOV-00005/01-SAN-001` | 79390 | mm | <missing> | <missing> |
| 5 | `JDA-C-01MOV-05004B/01-SAN-001` | 70480 | mm | <missing> | <missing> |
| 6 | `JDA-C-02MOV-00006/46MOV-00018` | 27080 | mm | <missing> | <missing> |
| 7 | `ESB1_BUSCABLE2_0104` | 200 | mm | <missing> | <missing> |
| 8 | `ESB2_BUSCABLE2_0104` | 200 | mm | <missing> | <missing> |
| 9 | `ESB1_BUSCABLE2_0103` | 1000 | mm | <missing> | <missing> |
| 10 | `ESB2_BUSCABLE2_0103` | 1000 | mm | <missing> | <missing> |
| … | *(3,962 more tags with this pattern)* |  |  |  |  |

#### Property: `rated current` | Concept: Functional Physical | 2,269 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-SB-E1A+A03.D1` | 52 | ampere | <missing> | <missing> |
| 2 | `JDA-SB-E1A+A05.L` | 160 | ampere | <missing> | <missing> |
| 3 | `JDA-SB-E1B+B06.P` | 160 | ampere | <missing> | <missing> |
| 4 | `JDA-SB-E1A+A05.J1` | 20 | ampere | <missing> | <missing> |
| 5 | `JDA-SB-E1B+B06.H1` | 20 | ampere | <missing> | <missing> |
| 6 | `JDA-SB-E1B+B06.H2` | 20 | ampere | <missing> | <missing> |
| 7 | `JDA-SB-E1A+A05.R` | 630 | ampere | <missing> | <missing> |
| 8 | `JDA-SB-E1B+B06.N` | 160 | ampere | <missing> | <missing> |
| 9 | `JDA-SB-E1A+A05.J2` | 52 | ampere | <missing> | <missing> |
| 10 | `JDA-SB-E1B+B06.L1` | 25 | ampere | <missing> | <missing> |
| … | *(2,259 more tags with this pattern)* |  |  |  |  |

#### Property: `rated voltage` | Concept: Functional Physical | 2,244 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-SB-E1A+A03.D1` | 400 | V | <missing> | <missing> |
| 2 | `JDA-SB-E1A+A05.L` | 400 | V | <missing> | <missing> |
| 3 | `JDA-SB-E1B+B06.P` | 400 | V | <missing> | <missing> |
| 4 | `JDA-SB-E1A+A05.J1` | 400 | V | <missing> | <missing> |
| 5 | `JDA-SB-E1B+B06.H1` | 400 | V | <missing> | <missing> |
| 6 | `JDA-SB-E1B+B06.H2` | 400 | V | <missing> | <missing> |
| 7 | `JDA-SB-E1A+A05.R` | 400 | V | <missing> | <missing> |
| 8 | `JDA-SB-E1B+B06.N` | 400 | V | <missing> | <missing> |
| 9 | `JDA-SB-E1A+A05.J2` | 400 | V | <missing> | <missing> |
| 10 | `JDA-SB-E1B+B06.L1` | 400 | V | <missing> | <missing> |
| … | *(2,234 more tags with this pattern)* |  |  |  |  |

#### Property: `rated short circuit current` | Concept: Functional Physical | 1,595 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2A-F003H01` | NA | ampere | <missing> | <missing> |
| 2 | `JDA-84ESB-E2A-F004H01` | NA | ampere | <missing> | <missing> |
| 3 | `JDA-84ESB-E2B-F003H01` | NA | ampere | <missing> | <missing> |
| 4 | `JDA-H-47800H01` | NA | ampere | <missing> | <missing> |
| 5 | `JDA-84ESB-E2B-F006H04` | NA | ampere | <missing> | <missing> |
| 6 | `JDA-84ESB-E2B-F006H05` | NA | ampere | <missing> | <missing> |
| 7 | `JDA-84ESB-E2B-F006H06` | NA | ampere | <missing> | <missing> |
| 8 | `JDA-84ESB-E2B-F002H08` | unset |  | <missing> | <missing> |
| 9 | `JDA-84ESB-E2B-F001H03` | NA | ampere | <missing> | <missing> |
| 10 | `JDA-84ESB-E7-F401H02` | NA | ampere | <missing> | <missing> |
| … | *(1,585 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_IP_GRADE` | Concept: Physical | 1,370 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-SB-E1A+A03.D1` | IP42 |  | <missing> | <missing> |
| 2 | `JDA-SB-E1A+A05.L` | IP42 |  | <missing> | <missing> |
| 3 | `JDA-SB-E1B+B06.P` | IP42 |  | <missing> | <missing> |
| 4 | `JDA-SB-E1A+A05.J1` | IP42 |  | <missing> | <missing> |
| 5 | `JDA-SB-E1B+B06.H1` | IP42 |  | <missing> | <missing> |
| 6 | `JDA-SB-E1B+B06.H2` | IP42 |  | <missing> | <missing> |
| 7 | `JDA-SB-E1A+A05.R` | IP42 |  | <missing> | <missing> |
| 8 | `JDA-SB-E1B+B06.N` | IP42 |  | <missing> | <missing> |
| 9 | `JDA-SB-E1A+A05.J2` | IP42 |  | <missing> | <missing> |
| 10 | `JDA-SB-E1B+B06.L1` | IP42 |  | <missing> | <missing> |
| … | *(1,360 more tags with this pattern)* |  |  |  |  |

#### Property: `weight net` | Concept: Physical | 1,282 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-X-79950` | unset |  | <missing> | <missing> |
| 2 | `JDA-83CP-V2-037` | 1.7 | kg | <missing> | <missing> |
| 3 | `JDA-83CP-V2-041` | 2.5 | kg | <missing> | <missing> |
| 4 | `JDA-83CP-V2-043` | 2.5 | kg | <missing> | <missing> |
| 5 | `JDA-ES-84802` | 0.3 | kg | <missing> | <missing> |
| 6 | `JDA-ES-84803` | 0.3 | kg | <missing> | <missing> |
| 7 | `JDA-ES-84801` | 0.3 | kg | <missing> | <missing> |
| 8 | `JDA-83ESB-V3C-F102X01` | 0.24 | kg | <missing> | <missing> |
| 9 | `JDA-TH-86804` | 0.3 | kg | <missing> | <missing> |
| 10 | `JDA-TH-86831` | 0.3 | kg | <missing> | <missing> |
| … | *(1,272 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_VALVE_SIZE` | Concept: Functional Physical | 1,267 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-73MV-0045` | 20 | mm | <missing> | <missing> |
| 2 | `JDA-73MV-0040` | 20 | mm | <missing> | <missing> |
| 3 | `JDA-73MV-0021` | 50 | mm | <missing> | <missing> |
| 4 | `JDA-51MV-0021` | 50 | mm | <missing> | <missing> |
| 5 | `JDA-73MV-0049` | 20 | mm | <missing> | <missing> |
| 6 | `JDA-51MV-0023` | 50 | mm | <missing> | <missing> |
| 7 | `JDA-73MV-0053` | 20 | mm | <missing> | <missing> |
| 8 | `JDA-51MV-0025` | 50 | mm | <missing> | <missing> |
| 9 | `JDA-73MV-0057` | 20 | mm | <missing> | <missing> |
| 10 | `JDA-51MV-0027` | 50 | mm | <missing> | <missing> |
| … | *(1,257 more tags with this pattern)* |  |  |  |  |

#### Property: `explosion protection zone` | Concept: Functional Physical | 1,250 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-83CP-V2-125` | Non Hazardous |  | <missing> | <missing> |
| 2 | `JDA-83CP-V2-126` | Zone 2 |  | <missing> | <missing> |
| 3 | `JDA-84ESB-E2A-F451S01` | Zone 2 |  | <missing> | <missing> |
| 4 | `JDA-84ESB-E1A-A04JS02` | Zone 2 |  | <missing> | <missing> |
| 5 | `JDA-84ESB-E2A-F452S01` | Zone 2 |  | <missing> | <missing> |
| 6 | `JDA-84ESB-E1A-A04JS03` | Zone 2 |  | <missing> | <missing> |
| 7 | `JDA-84ESB-E2A-F453S01` | Zone 2 |  | <missing> | <missing> |
| 8 | `JDA-84ESB-E1A-A04JS04` | Zone 2 |  | <missing> | <missing> |
| 9 | `JDA-84ESB-E2A-F454S01` | Zone 2 |  | <missing> | <missing> |
| 10 | `JDA-84ESB-E2B-F351S01` | Zone 2 |  | <missing> | <missing> |
| … | *(1,240 more tags with this pattern)* |  |  |  |  |

#### Property: `Valve Rating` | Concept: Physical | 1,221 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-73MV-0045` | Tubing HP |  | <missing> | <missing> |
| 2 | `JDA-73MV-0040` | Tubing HP |  | <missing> | <missing> |
| 3 | `JDA-73MV-0021` | 150 psi |  | <missing> | <missing> |
| 4 | `JDA-51MV-0021` | 150 psi |  | <missing> | <missing> |
| 5 | `JDA-73MV-0049` | Tubing HP |  | <missing> | <missing> |
| 6 | `JDA-51MV-0023` | 150 psi |  | <missing> | <missing> |
| 7 | `JDA-73MV-0053` | Tubing HP |  | <missing> | <missing> |
| 8 | `JDA-51MV-0025` | 150 psi |  | <missing> | <missing> |
| 9 | `JDA-73MV-0057` | Tubing HP |  | <missing> | <missing> |
| 10 | `JDA-51MV-0027` | 150 psi |  | <missing> | <missing> |
| … | *(1,211 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_EX_CERTIFICATE` | Concept: Physical | 885 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-BA-V1A` | NA |  | <missing> | <missing> |
| 2 | `JDA-BA-V1B` | NA |  | <missing> | <missing> |
| 3 | `JDA-BA-V2` | DEKRA 17 ATEX 0074X |  | <missing> | <missing> |
| 4 | `JDA-BA-X1L` | NA |  | <missing> | <missing> |
| 5 | `JDA-BA-X1R` | NA |  | <missing> | <missing> |
| 6 | `JDA-BA-X2L` | NA |  | <missing> | <missing> |
| 7 | `JDA-BA-X2R` | NA |  | <missing> | <missing> |
| 8 | `JDA-BA-X3L` | NA |  | <missing> | <missing> |
| 9 | `JDA-BA-X3R` | NA |  | <missing> | <missing> |
| 10 | `JDA-G-84001A` | NA |  | <missing> | <missing> |
| … | *(875 more tags with this pattern)* |  |  |  |  |

#### Property: `pressure equipment category` | Concept: Functional Physical | 756 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-57QZ-01101` | NA |  | <missing> | <missing> |
| 2 | `JDA-57QZ-01102` | NA |  | <missing> | <missing> |
| 3 | `JDA-57QZ-01103` | NA |  | <missing> | <missing> |
| 4 | `JDA-57QZ-01104` | NA |  | <missing> | <missing> |
| 5 | `JDA-57QZ-01105` | NA |  | <missing> | <missing> |
| 6 | `JDA-57QZ-01106` | NA |  | <missing> | <missing> |
| 7 | `JDA-57QZ-01107` | NA |  | <missing> | <missing> |
| 8 | `JDA-57QZ-01108` | NA |  | <missing> | <missing> |
| 9 | `JDA-57QZ-01109` | NA |  | <missing> | <missing> |
| 10 | `JDA-57QZ-01201` | NA |  | <missing> | <missing> |
| … | *(746 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_TRIP` | Concept: Physical | 677 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-SB-E1A+A03.D1` | NA |  | <missing> | <missing> |
| 2 | `JDA-SB-E1A+A05.L` | NA |  | <missing> | <missing> |
| 3 | `JDA-SB-E1B+B06.P` | NA |  | <missing> | <missing> |
| 4 | `JDA-SB-E1A+A05.J1` | NA |  | <missing> | <missing> |
| 5 | `JDA-SB-E1B+B06.H1` | NA |  | <missing> | <missing> |
| 6 | `JDA-SB-E1B+B06.H2` | NA |  | <missing> | <missing> |
| 7 | `JDA-SB-E1A+A05.R` | NA |  | <missing> | <missing> |
| 8 | `JDA-SB-E1B+B06.N` | NA |  | <missing> | <missing> |
| 9 | `JDA-SB-E1A+A05.J2` | NA |  | <missing> | <missing> |
| 10 | `JDA-SB-E1B+B06.L1` | NA |  | <missing> | <missing> |
| … | *(667 more tags with this pattern)* |  |  |  |  |

#### Property: `rated frequency` | Concept: Functional Physical | 677 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-SB-E1A+A03.D1` | 50 | Hz | <missing> | <missing> |
| 2 | `JDA-SB-E1A+A05.L` | 50 | Hz | <missing> | <missing> |
| 3 | `JDA-SB-E1B+B06.P` | 50 | Hz | <missing> | <missing> |
| 4 | `JDA-SB-E1A+A05.J1` | 50 | Hz | <missing> | <missing> |
| 5 | `JDA-SB-E1B+B06.H1` | 50 | Hz | <missing> | <missing> |
| 6 | `JDA-SB-E1B+B06.H2` | 50 | Hz | <missing> | <missing> |
| 7 | `JDA-SB-E1A+A05.R` | 50 | Hz | <missing> | <missing> |
| 8 | `JDA-SB-E1B+B06.N` | 50 | Hz | <missing> | <missing> |
| 9 | `JDA-SB-E1A+A05.J2` | 50 | Hz | <missing> | <missing> |
| 10 | `JDA-SB-E1B+B06.L1` | 50 | Hz | <missing> | <missing> |
| … | *(667 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_EX_CLASS` | Concept: Physical | 653 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-BA-V1A` | NA |  | <missing> | <missing> |
| 2 | `JDA-BA-V1B` | NA |  | <missing> | <missing> |
| 3 | `JDA-BA-V2` | Ex eb |  | <missing> | <missing> |
| 4 | `JDA-BA-X1L` | NA |  | <missing> | <missing> |
| 5 | `JDA-BA-X1R` | NA |  | <missing> | <missing> |
| 6 | `JDA-BA-X2L` | NA |  | <missing> | <missing> |
| 7 | `JDA-BA-X2R` | NA |  | <missing> | <missing> |
| 8 | `JDA-BA-X3L` | NA |  | <missing> | <missing> |
| 9 | `JDA-BA-X3R` | NA |  | <missing> | <missing> |
| 10 | `JDA-83CP-V2-037` | Ex db eb |  | <missing> | <missing> |
| … | *(643 more tags with this pattern)* |  |  |  |  |

#### Property: `nominal pipe diameter` | Concept: Functional Physical | 598 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-1 1/2"-D47935-13842-2F` | 40 | mm | <missing> | <missing> |
| 2 | `JDA-3"-H74012-LD30-N` | 80 | mm | <missing> | <missing> |
| 3 | `JDA-4"-P63005-13842-3FE` | 100 | mm | <missing> | <missing> |
| 4 | `JDA-3"-B51012-13842-N` | 80 | mm | <missing> | <missing> |
| 5 | `JDA-6"-P63004-13842-3FE` | 150 | mm | <missing> | <missing> |
| 6 | `JDA-3"-P02007-LD30-N` | 80 | mm | <missing> | <missing> |
| 7 | `JDA-16"-P02003-LD30-N` | 400 | mm | <missing> | <missing> |
| 8 | `JDA-3"-H74014-LD30-N` | 80 | mm | <missing> | <missing> |
| 9 | `JDA-6"-P01201-LD30-N` | 150 | mm | <missing> | <missing> |
| 10 | `JDA-8"-P01203-LD30-N` | 200 | mm | <missing> | <missing> |
| … | *(588 more tags with this pattern)* |  |  |  |  |

#### Property: `body material` | Concept: Physical | 527 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-86MV-0022` | carbon steel |  | <missing> | <missing> |
| 2 | `JDA-86MV-0027` | carbon steel |  | <missing> | <missing> |
| 3 | `JDA-86MV-0023` | carbon steel |  | <missing> | <missing> |
| 4 | `JDA-86MV-0015` | carbon steel |  | <missing> | <missing> |
| 5 | `JDA-86MV-0020` | carbon steel |  | <missing> | <missing> |
| 6 | `JDA-86MV-0018` | carbon steel |  | <missing> | <missing> |
| 7 | `JDA-86MV-0024` | carbon steel |  | <missing> | <missing> |
| 8 | `JDA-86MV-0025` | carbon steel |  | <missing> | <missing> |
| 9 | `JDA-86MV-0026` | carbon steel |  | <missing> | <missing> |
| 10 | `JDA-86MV-0016` | carbon steel |  | <missing> | <missing> |
| … | *(517 more tags with this pattern)* |  |  |  |  |

#### Property: `calibration range` | Concept: Physical | 245 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-86FI-13801` | 0 To 200 Pa |  | <missing> | <missing> |
| 2 | `JDA-86FI-12801` | 0 To 200 Pa |  | <missing> | <missing> |
| 3 | `JDA-86FI-11801` | 0 To 200 Pa |  | <missing> | <missing> |
| 4 | `JDA-61FI-00007` | 0 - 50m3/hr |  | <missing> | <missing> |
| 5 | `JDA-63LI-00008` | NA |  | <missing> | <missing> |
| 6 | `JDA-74LI-00012` | NA |  | <missing> | <missing> |
| 7 | `JDA-73LI-00104` | Same as column AG & AH |  | <missing> | <missing> |
| 8 | `JDA-73LI-00206` | Same as column AG & AH |  | <missing> | <missing> |
| 9 | `JDA-54LI-00006` | NA |  | <missing> | <missing> |
| 10 | `JDA-84LC-00111` | NA |  | <missing> | <missing> |
| … | *(235 more tags with this pattern)* |  |  |  |  |

#### Property: `Accuracy` | Concept: Physical | 244 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-86FI-13801` | ± 0,10% |  | <missing> | <missing> |
| 2 | `JDA-86FI-12801` | ± 0,10% |  | <missing> | <missing> |
| 3 | `JDA-86FI-11801` | ± 0,10% |  | <missing> | <missing> |
| 4 | `JDA-63LI-00008` | Ref ±0.08 in |  | <missing> | <missing> |
| 5 | `JDA-74LI-00012` | 0.8mm |  | <missing> | <missing> |
| 6 | `JDA-73LI-00104` | ± 0.075% of span |  | <missing> | <missing> |
| 7 | `JDA-73LI-00206` | ± 0.075% of span |  | <missing> | <missing> |
| 8 | `JDA-54LI-00006` | Ref ±0.08 in |  | <missing> | <missing> |
| 9 | `JDA-84LC-00111` | NA |  | <missing> | <missing> |
| 10 | `JDA-84LC-00211` | NA |  | <missing> | <missing> |
| … | *(234 more tags with this pattern)* |  |  |  |  |

#### Property: `Equipment Type` | Concept: Physical | 244 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-86FI-13801` | Differential Pressure Transmitter |  | <missing> | <missing> |
| 2 | `JDA-86FI-12801` | Differential Pressure Transmitter |  | <missing> | <missing> |
| 3 | `JDA-86FI-11801` | Differential Pressure Transmitter |  | <missing> | <missing> |
| 4 | `JDA-63LI-00008` | Electric |  | <missing> | <missing> |
| 5 | `JDA-74LI-00012` | Electric |  | <missing> | <missing> |
| 6 | `JDA-73LI-00104` | Electric |  | <missing> | <missing> |
| 7 | `JDA-73LI-00206` | Electric |  | <missing> | <missing> |
| 8 | `JDA-54LI-00006` | Electric |  | <missing> | <missing> |
| 9 | `JDA-84LC-00111` | Level Transmitter |  | <missing> | <missing> |
| 10 | `JDA-84LC-00211` | Level Transmitter |  | <missing> | <missing> |
| … | *(234 more tags with this pattern)* |  |  |  |  |

#### Property: `K - Factor` | Concept: Physical | 244 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-86FI-13801` | NA |  | <missing> | <missing> |
| 2 | `JDA-86FI-12801` | NA |  | <missing> | <missing> |
| 3 | `JDA-86FI-11801` | NA |  | <missing> | <missing> |
| 4 | `JDA-63LI-00008` | NA |  | <missing> | <missing> |
| 5 | `JDA-74LI-00012` | NA |  | <missing> | <missing> |
| 6 | `JDA-73LI-00104` | NA |  | <missing> | <missing> |
| 7 | `JDA-73LI-00206` | NA |  | <missing> | <missing> |
| 8 | `JDA-54LI-00006` | NA |  | <missing> | <missing> |
| 9 | `JDA-84LC-00111` | NA |  | <missing> | <missing> |
| 10 | `JDA-84LC-00211` | NA |  | <missing> | <missing> |
| … | *(234 more tags with this pattern)* |  |  |  |  |

#### Property: `Obsolescence Date` | Concept: Physical | 244 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-86FI-13801` | 02/09/2024 01:00:00 |  | <missing> | <missing> |
| 2 | `JDA-86FI-12801` | 02/09/2024 01:00:00 |  | <missing> | <missing> |
| 3 | `JDA-86FI-11801` | 02/09/2024 01:00:00 |  | <missing> | <missing> |
| 4 | `JDA-63LI-00008` | NA |  | <missing> | <missing> |
| 5 | `JDA-74LI-00012` | NA |  | <missing> | <missing> |
| 6 | `JDA-73LI-00104` | NA |  | <missing> | <missing> |
| 7 | `JDA-73LI-00206` | NA |  | <missing> | <missing> |
| 8 | `JDA-54LI-00006` | NA |  | <missing> | <missing> |
| 9 | `JDA-84LC-00111` | NA |  | <missing> | <missing> |
| 10 | `JDA-84LC-00211` | NA |  | <missing> | <missing> |
| … | *(234 more tags with this pattern)* |  |  |  |  |

#### Property: `operating voltage` | Concept: Functional Physical | 229 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-86FI-13801` | 24 | VDC | <missing> | <missing> |
| 2 | `JDA-86FI-12801` | 24 | VDC | <missing> | <missing> |
| 3 | `JDA-86FI-11801` | 24 | VDC | <missing> | <missing> |
| 4 | `JDA-63LI-00008` | 24 | Vdc | <missing> | <missing> |
| 5 | `JDA-74LI-00012` | 12-28 | Vdc | <missing> | <missing> |
| 6 | `JDA-73LI-00104` | 24 | Vdc | <missing> | <missing> |
| 7 | `JDA-73LI-00206` | 24 | Vdc | <missing> | <missing> |
| 8 | `JDA-54LI-00006` | 24 | Vdc | <missing> | <missing> |
| 9 | `JDA-84LC-00111` | 24 | VDC | <missing> | <missing> |
| 10 | `JDA-84LC-00211` | 42.4 | V | <missing> | <missing> |
| … | *(219 more tags with this pattern)* |  |  |  |  |

#### Property: `explosion protection temperature class` | Concept: Functional Physical | 189 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-54TE-00020` | T5 |  | <missing> | <missing> |
| 2 | `JDA-54TE-00021` | T5 |  | <missing> | <missing> |
| 3 | `JDA-61TE-00020` | T5 |  | <missing> | <missing> |
| 4 | `JDA-62TE-00038` | T5 |  | <missing> | <missing> |
| 5 | `JDA-63TE-00023` | T5 |  | <missing> | <missing> |
| 6 | `JDA-63TE-00022` | T4 |  | <missing> | <missing> |
| 7 | `JDA-62FE-00015A-02` | T5 |  | <missing> | <missing> |
| 8 | `JDA-62FE-00015A-01` | T5 |  | <missing> | <missing> |
| 9 | `JDA-01FE-02035B` | T6 |  | <missing> | <missing> |
| 10 | `JDA-01FE-02035A` | T6 |  | <missing> | <missing> |
| … | *(179 more tags with this pattern)* |  |  |  |  |

#### Property: `explosion protection gas group` | Concept: Functional Physical | 187 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-54TE-00020` | IIC |  | <missing> | <missing> |
| 2 | `JDA-54TE-00021` | IIC |  | <missing> | <missing> |
| 3 | `JDA-61TE-00020` | IIC |  | <missing> | <missing> |
| 4 | `JDA-62TE-00038` | IIC |  | <missing> | <missing> |
| 5 | `JDA-63TE-00023` | IIC |  | <missing> | <missing> |
| 6 | `JDA-63TE-00022` | IIC |  | <missing> | <missing> |
| 7 | `JDA-62FE-00015A-02` | IIC |  | <missing> | <missing> |
| 8 | `JDA-62FE-00015A-01` | IIC |  | <missing> | <missing> |
| 9 | `JDA-01FE-02035B` | IIC |  | <missing> | <missing> |
| 10 | `JDA-01FE-02035A` | IIC |  | <missing> | <missing> |
| … | *(177 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_RATED_POWER` | Concept: Functional Physical | 125 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-BA-V1A` | 60 | kW | <missing> | <missing> |
| 2 | `JDA-BA-V1B` | 60 | kW | <missing> | <missing> |
| 3 | `JDA-BA-V2` | NA | kW | <missing> | <missing> |
| 4 | `JDA-BA-X1L` | 2.4 | kW | <missing> | <missing> |
| 5 | `JDA-BA-X1R` | 2.4 | kW | <missing> | <missing> |
| 6 | `JDA-BA-X2L` | 2.4 | kW | <missing> | <missing> |
| 7 | `JDA-BA-X2R` | 2.4 | kW | <missing> | <missing> |
| 8 | `JDA-BA-X3L` | 2.4 | kW | <missing> | <missing> |
| 9 | `JDA-BA-X3R` | 2.4 | kW | <missing> | <missing> |
| 10 | `JDA-G-84001A` | 250 | kW | <missing> | <missing> |
| … | *(115 more tags with this pattern)* |  |  |  |  |

#### Property: `nominal current` | Concept: Functional Physical | 121 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-BA-V1A` | 86.6 | ampere | <missing> | <missing> |
| 2 | `JDA-BA-V1B` | 86.6 | ampere | <missing> | <missing> |
| 3 | `JDA-BA-V2` | 78.3 | ampere | <missing> | <missing> |
| 4 | `JDA-BA-X1L` | 1400 | ampere | <missing> | <missing> |
| 5 | `JDA-BA-X1R` | 1400 | ampere | <missing> | <missing> |
| 6 | `JDA-BA-X2L` | 1400 | ampere | <missing> | <missing> |
| 7 | `JDA-BA-X2R` | 1400 | ampere | <missing> | <missing> |
| 8 | `JDA-BA-X3L` | 1400 | ampere | <missing> | <missing> |
| 9 | `JDA-BA-X3R` | 1400 | ampere | <missing> | <missing> |
| 10 | `JDA-G-84001A` | NA | ampere | <missing> | <missing> |
| … | *(111 more tags with this pattern)* |  |  |  |  |

#### Property: `explosion protection notified body` | Concept: Physical | 117 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-54TE-00020` | BAS / 0598 |  | <missing> | <missing> |
| 2 | `JDA-54TE-00021` | BAS / 0598 |  | <missing> | <missing> |
| 3 | `JDA-61TE-00020` | BAS / 0598 |  | <missing> | <missing> |
| 4 | `JDA-62TE-00038` | BAS / 0598 |  | <missing> | <missing> |
| 5 | `JDA-63TE-00023` | BAS / 0598 |  | <missing> | <missing> |
| 6 | `JDA-63TE-00022` | Derka |  | <missing> | <missing> |
| 7 | `JDA-63LI-00008` | DNV / 2460 |  | <missing> | <missing> |
| 8 | `JDA-74LI-00012` | BAS / 1180 |  | <missing> | <missing> |
| 9 | `JDA-73LI-00104` | BAS / 0598 |  | <missing> | <missing> |
| 10 | `JDA-73LI-00206` | BAS / 0598 |  | <missing> | <missing> |
| … | *(107 more tags with this pattern)* |  |  |  |  |

#### Property: `seat material` | Concept: Physical | 101 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-74UZV-00002` | ASTM A182 F53 |  | <missing> | <missing> |
| 2 | `JDA-73UZV-00203` | ASTM A182 F53 |  | <missing> | <missing> |
| 3 | `JDA-54UZV-00001` | ASTM A182 F53 |  | <missing> | <missing> |
| 4 | `JDA-73UZV-00201` | ASTM 182 F53 |  | <missing> | <missing> |
| 5 | `JDA-73UZV-00102` | ASTM A182 F53 |  | <missing> | <missing> |
| 6 | `JDA-01UZV-02003` | ASTM A182 F53 |  | <missing> | <missing> |
| 7 | `JDA-74UZV-02001` | ASTM 182 F53 |  | <missing> | <missing> |
| 8 | `JDA-73UZV-00204` | ASTM 182 F53 |  | <missing> | <missing> |
| 9 | `JDA-63UZV-00002` | ASTM A182 F53 |  | <missing> | <missing> |
| 10 | `JDA-01UZV-05003` | ASTM A182 F53 |  | <missing> | <missing> |
| … | *(91 more tags with this pattern)* |  |  |  |  |

#### Property: `weight content` | Concept: Physical | 59 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-02UZV-00101` | 8710 | kg | <missing> | <missing> |
| 2 | `JDA-02UZV-00102` | 8710 | kg | <missing> | <missing> |
| 3 | `JDA-02UZV-00204` | 25886 | kg | <missing> | <missing> |
| 4 | `JDA-01UZV-02022` | 0 | kg | <missing> | <missing> |
| 5 | `JDA-01UZV-02021` | 0 | kg | <missing> | <missing> |
| 6 | `JDA-79MOV-00006B` | 0 | kg | <missing> | <missing> |
| 7 | `JDA-01UZV-05022` | 0 | kg | <missing> | <missing> |
| 8 | `JDA-01KSV-05031` | 0 | kg | <missing> | <missing> |
| 9 | `JDA-01UZV-05021` | 0 | kg | <missing> | <missing> |
| 10 | `JDA-01MOV-05002` | 5352 | kg | <missing> | <missing> |
| … | *(49 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_REACTIVE_POWER` | Concept: Functional Physical | 58 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-G-84001A` | NA |  | <missing> | <missing> |
| 2 | `JDA-G-84001B` | NA |  | <missing> | <missing> |
| 3 | `JDA-G-84001C` | NA |  | <missing> | <missing> |
| 4 | `JDA-TR-VV1B` | 60 kVA |  | <missing> | <missing> |
| 5 | `JDA-TR-VV1A` | 60 kVA |  | <missing> | <missing> |
| 6 | `JDA-TR-VV2B` | 60 kVA |  | <missing> | <missing> |
| 7 | `JDA-TR-VV2A` | 60 kVA |  | <missing> | <missing> |
| 8 | `JDA-UP-V1A` | NA |  | <missing> | <missing> |
| 9 | `JDA-UP-V1B` | NA |  | <missing> | <missing> |
| 10 | `JDA-PM-74002A` | 48.4 |  | <missing> | <missing> |
| … | *(48 more tags with this pattern)* |  |  |  |  |

#### Property: `gas analysed` | Concept: Physical | 53 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-57XZ-01101` | flammable hydrocarbon gas |  | <missing> | <missing> |
| 2 | `JDA-57XZ-01102` | flammable hydrocarbon gas |  | <missing> | <missing> |
| 3 | `JDA-57XZ-01103` | flammable hydrocarbon gas |  | <missing> | <missing> |
| 4 | `JDA-57XZ-01104` | flammable hydrocarbon gas |  | <missing> | <missing> |
| 5 | `JDA-57XZ-01105` | flammable hydrocarbon gas |  | <missing> | <missing> |
| 6 | `JDA-57XZ-01106` | flammable hydrocarbon gas |  | <missing> | <missing> |
| 7 | `JDA-57XZ-01107` | flammable hydrocarbon gas |  | <missing> | <missing> |
| 8 | `JDA-57XZ-01108` | flammable hydrocarbon gas |  | <missing> | <missing> |
| 9 | `JDA-57XZ-01109` | flammable hydrocarbon gas |  | <missing> | <missing> |
| 10 | `JDA-57XZ-01201` | flammable hydrocarbon gas |  | <missing> | <missing> |
| … | *(43 more tags with this pattern)* |  |  |  |  |

#### Property: `atex category` | Concept: Physical | 45 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-54TE-00020` | 1 |  | <missing> | <missing> |
| 2 | `JDA-54TE-00021` | 1 |  | <missing> | <missing> |
| 3 | `JDA-61TE-00020` | 1 |  | <missing> | <missing> |
| 4 | `JDA-62TE-00038` | 1 |  | <missing> | <missing> |
| 5 | `JDA-63TE-00023` | 1 |  | <missing> | <missing> |
| 6 | `JDA-63TE-00022` | 1 |  | <missing> | <missing> |
| 7 | `JDA-63LI-00008` | 1 |  | <missing> | <missing> |
| 8 | `JDA-74LI-00012` | NA |  | <missing> | <missing> |
| 9 | `JDA-73LI-00104` | 1 |  | <missing> | <missing> |
| 10 | `JDA-73LI-00206` | 1 |  | <missing> | <missing> |
| … | *(35 more tags with this pattern)* |  |  |  |  |

#### Property: `atex explosive atmosphere` | Concept: Physical | 45 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-54TE-00020` | G |  | <missing> | <missing> |
| 2 | `JDA-54TE-00021` | G |  | <missing> | <missing> |
| 3 | `JDA-61TE-00020` | G |  | <missing> | <missing> |
| 4 | `JDA-62TE-00038` | G |  | <missing> | <missing> |
| 5 | `JDA-63TE-00023` | G |  | <missing> | <missing> |
| 6 | `JDA-63TE-00022` | G |  | <missing> | <missing> |
| 7 | `JDA-63LI-00008` | G |  | <missing> | <missing> |
| 8 | `JDA-74LI-00012` | NA |  | <missing> | <missing> |
| 9 | `JDA-73LI-00104` | G |  | <missing> | <missing> |
| 10 | `JDA-73LI-00206` | G |  | <missing> | <missing> |
| … | *(35 more tags with this pattern)* |  |  |  |  |

#### Property: `atex group` | Concept: Physical | 45 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-54TE-00020` | II |  | <missing> | <missing> |
| 2 | `JDA-54TE-00021` | II |  | <missing> | <missing> |
| 3 | `JDA-61TE-00020` | II |  | <missing> | <missing> |
| 4 | `JDA-62TE-00038` | II |  | <missing> | <missing> |
| 5 | `JDA-63TE-00023` | II |  | <missing> | <missing> |
| 6 | `JDA-63TE-00022` | II |  | <missing> | <missing> |
| 7 | `JDA-63LI-00008` | II |  | <missing> | <missing> |
| 8 | `JDA-74LI-00012` | II |  | <missing> | <missing> |
| 9 | `JDA-73LI-00104` | II |  | <missing> | <missing> |
| 10 | `JDA-73LI-00206` | II |  | <missing> | <missing> |
| … | *(35 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_STANDARD` | Concept: Functional Physical | 45 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-74UZV-00002` | 13842 |  | <missing> | <missing> |
| 2 | `JDA-73UZV-00203` | 13842 |  | <missing> | <missing> |
| 3 | `JDA-54UZV-00001` | 13842 |  | <missing> | <missing> |
| 4 | `JDA-73UZV-00201` | LD30 |  | <missing> | <missing> |
| 5 | `JDA-73UZV-00102` | 13842 |  | <missing> | <missing> |
| 6 | `JDA-01UZV-02003` | 253842 |  | <missing> | <missing> |
| 7 | `JDA-74UZV-02001` | LD30 |  | <missing> | <missing> |
| 8 | `JDA-73UZV-00204` | LD30 |  | <missing> | <missing> |
| 9 | `JDA-63UZV-00002` | 13842 |  | <missing> | <missing> |
| 10 | `JDA-01UZV-05003` | 253842 |  | <missing> | <missing> |
| … | *(35 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_VDS_NUMBER` | Concept: Functional Physical | 45 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-74UZV-00002` | JDAW-6972000-C08-02001 |  | <missing> | <missing> |
| 2 | `JDA-73UZV-00203` | JDAW-6972000-C08-02001 |  | <missing> | <missing> |
| 3 | `JDA-54UZV-00001` | JDAW-6972000-C08-02001 |  | <missing> | <missing> |
| 4 | `JDA-73UZV-00201` | IDS |  | <missing> | <missing> |
| 5 | `JDA-73UZV-00102` | JDAW-6972000-C08-02001 |  | <missing> | <missing> |
| 6 | `JDA-01UZV-02003` | JDAW-6972000-C08-02001 |  | <missing> | <missing> |
| 7 | `JDA-74UZV-02001` | IDS |  | <missing> | <missing> |
| 8 | `JDA-73UZV-00204` | IDS |  | <missing> | <missing> |
| 9 | `JDA-63UZV-00002` | JDAW-6972000-C08-02001 |  | <missing> | <missing> |
| 10 | `JDA-01UZV-05003` | JDAW-6972000-C08-02001 |  | <missing> | <missing> |
| … | *(35 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_ACTUAL_LOAD` | Concept: Functional Physical | 41 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2A-F003H01` | 14 | W | <missing> | <missing> |
| 2 | `JDA-84ESB-E2A-F004H01` | 14 | W | <missing> | <missing> |
| 3 | `JDA-84ESB-E2B-F003H01` | 14 | W | <missing> | <missing> |
| 4 | `JDA-H-47800H01` | 640 | watt | <missing> | <missing> |
| 5 | `JDA-84ESB-E2B-F006H04` | NA |  | <missing> | <missing> |
| 6 | `JDA-84ESB-E2B-F006H05` | NA |  | <missing> | <missing> |
| 7 | `JDA-84ESB-E2B-F006H06` | NA |  | <missing> | <missing> |
| 8 | `JDA-84ESB-E2B-F002H08` |  |  | <missing> | <missing> |
| 9 | `JDA-84ESB-E2B-F001H03` | NA |  | <missing> | <missing> |
| 10 | `JDA-84ESB-E7-F401H02` | 0.41 | kW | <missing> | <missing> |
| … | *(31 more tags with this pattern)* |  |  |  |  |

#### Property: `height` | Concept: Functional Physical | 34 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-V-63001` | 3885 | mm | <missing> | <missing> |
| 2 | `JDA-V-74001` | 3735 | mm | <missing> | <missing> |
| 3 | `JDA-T-61001` | 1500 | mm | <missing> | <missing> |
| 4 | `JDA-T-54001` | 4250 | mm | <missing> | <missing> |
| 5 | `JDA-T-73001` | 3800 | mm | <missing> | <missing> |
| 6 | `JDA-T-46001` | 3400 | mm | <missing> | <missing> |
| 7 | `JDA-T-73002` | 3800 | mm | <missing> | <missing> |
| 8 | `JDA-T-69101` | 1638 | mm | <missing> | <missing> |
| 9 | `JDA-T-69102` | 1638 | mm | <missing> | <missing> |
| 10 | `JDA-T-69103` | 1638 | mm | <missing> | <missing> |
| … | *(24 more tags with this pattern)* |  |  |  |  |

#### Property: `insulation class` | Concept: Functional Physical | 24 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-85AD013` | H (180 DegC) |  | <missing> | <missing> |
| 2 | `JDA-85AD017` | H (180 DegC) |  | <missing> | <missing> |
| 3 | `JDA-85AD021` | H (180 DegC) |  | <missing> | <missing> |
| 4 | `JDA-85AD002` | H (180 DegC) |  | <missing> | <missing> |
| 5 | `JDA-85AD006` | H (180 DegC) |  | <missing> | <missing> |
| 6 | `JDA-85AD010` | H (180 DegC) |  | <missing> | <missing> |
| 7 | `JDA-85AD014` | H (180 DegC) |  | <missing> | <missing> |
| 8 | `JDA-85AD018` | H (180 DegC) |  | <missing> | <missing> |
| 9 | `JDA-85AD022` | H (180 DegC) |  | <missing> | <missing> |
| 10 | `JDA-85AD003` | H (180 DegC) |  | <missing> | <missing> |
| … | *(14 more tags with this pattern)* |  |  |  |  |

#### Property: `insulation required` | Concept: Physical | 20 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-79SP-0130` | no |  | <missing> | <missing> |
| 2 | `JDA-79SP-0131` | no |  | <missing> | <missing> |
| 3 | `JDA-65SP-0340` | no |  | <missing> | <missing> |
| 4 | `JDA-65SP-0344` | no |  | <missing> | <missing> |
| 5 | `JDA-65SP-0345` | no |  | <missing> | <missing> |
| 6 | `JDA-65SP-0346` | no |  | <missing> | <missing> |
| 7 | `JDA-01SP-0131` | unset |  | <missing> | <missing> |
| 8 | `JDA-01SP-0133` | unset |  | <missing> | <missing> |
| 9 | `JDA-01SP-0090` | unset |  | <missing> | <missing> |
| 10 | `JDA-01SP-0091` | unset |  | <missing> | <missing> |
| … | *(10 more tags with this pattern)* |  |  |  |  |

#### Property: `seal type` | Concept: Physical | 13 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-P-62001` | Sealless |  | <missing> | <missing> |
| 2 | `JDA-P-54001` | Double Mechanical seal with Seal flush plan 53B |  | <missing> | <missing> |
| 3 | `JDA-P-61001` | Single dry running seal |  | <missing> | <missing> |
| 4 | `JDA-P-46001A` | NA |  | <missing> | <missing> |
| 5 | `JDA-P-46001B` | NA |  | <missing> | <missing> |
| 6 | `JDA-P-47800` | NA |  | <missing> | <missing> |
| 7 | `JDA-P-47801` | NA |  | <missing> | <missing> |
| 8 | `JDA-P-86851A` | NA |  | <missing> | <missing> |
| 9 | `JDA-P-86850B` | NA |  | <missing> | <missing> |
| 10 | `JDA-P-86851B` | NA |  | <missing> | <missing> |
| … | *(3 more tags with this pattern)* |  |  |  |  |

#### Property: `rated output power` | Concept: Functional Physical | 3 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-GD-84101` | 267 | kW | <missing> | <missing> |
| 2 | `JDA-GD-84201` | 267 | kW | <missing> | <missing> |
| 3 | `JDA-GD-84301` | 267 | kW | <missing> | <missing> |

#### Property: `rated output apparent power` | Concept: Functional Physical | 2 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-UP-V1A` | NA | kW | <missing> | <missing> |
| 2 | `JDA-UP-V1B` | NA | kW | <missing> | <missing> |

#### Property: `Auto-Overload-Protection-Sys` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-X-79001` | unset |  | <missing> | <missing> |

#### Property: `lower limit operating suction pressure` | Concept: Functional Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-P-63001` | NA | pascal | <missing> | <missing> |


### ⚠️ RDL_CSV_VALUE_MISMATCH (1,472 total gaps — 33 property groups)

#### Property: `rated impulse voltage` | Concept: Physical | 677 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-SB-E1A+A03.D1` | 8000 | volt | 8000 | v |
| 2 | `JDA-SB-E1A+A05.L` | 8000 | volt | 8000 | v |
| 3 | `JDA-SB-E1B+B06.P` | 8000 | volt | 8000 | v |
| 4 | `JDA-SB-E1A+A05.J1` | 8000 | volt | 8000 | v |
| 5 | `JDA-SB-E1B+B06.H1` | 8000 | volt | 8000 | v |
| 6 | `JDA-SB-E1B+B06.H2` | 8000 | volt | 8000 | v |
| 7 | `JDA-SB-E1A+A05.R` | 8000 | volt | 8000 | v |
| 8 | `JDA-SB-E1B+B06.N` | 8000 | volt | 8000 | v |
| 9 | `JDA-SB-E1A+A05.J2` | 8000 | volt | 8000 | v |
| 10 | `JDA-SB-E1B+B06.L1` | 8000 | volt | 8000 | v |
| … | *(667 more tags with this pattern)* |  |  |  |  |

#### Property: `rated current` | Concept: Functional Physical | 248 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-H-62001` | 318 | ampere | 318 | a |
| 2 | `JDA-H-63001` | 14.5 | ampere | 14.5 | a |
| 3 | `JDA-H-46001B` | 14.4 | ampere | 14.4 | a |
| 4 | `JDA-H-61001` | 15 | ampere | 15 | a |
| 5 | `JDA-H-46001A` | 14.4 | ampere | 14.4 | a |
| 6 | `JDA-H-84102` | 4 | ampere | 4 | a |
| 7 | `JDA-H-84103` | 10.7 | ampere | 10.7 | a |
| 8 | `JDA-H-84202` | 4 | ampere | 4 | a |
| 9 | `JDA-H-84302` | 4 | ampere | 4 | a |
| 10 | `JDA-H-84203` | 10.7 | ampere | 10.7 | a |
| … | *(238 more tags with this pattern)* |  |  |  |  |

#### Property: `Power - Normal` | Concept: Physical | 103 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-G-84001A` | 235/293,75 kW/kVA |  | 235/293;75 kW/kVA |  |
| 2 | `JDA-G-84001B` | 235/293,75 kW/kVA |  | 235/293;75 kW/kVA |  |
| 3 | `JDA-G-84001C` | 235/293,75 kW/kVA |  | 235/293;75 kW/kVA |  |
| 4 | `JDA-H-84102` | 50W |  | 50 | w |
| 5 | `JDA-H-84103` | 2.5kW |  | 2.5 | kw |
| 6 | `JDA-H-84104` | 300W |  | 300 | w |
| 7 | `JDA-H-84201` | 250W |  | 250 | w |
| 8 | `JDA-H-84301` | 250W |  | 250 | w |
| 9 | `JDA-H-84202` | 50W |  | 50 | w |
| 10 | `JDA-H-84302` | 50W |  | 50 | w |
| … | *(93 more tags with this pattern)* |  |  |  |  |

#### Property: `Accuracy` | Concept: Physical | 79 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84PDT-00130` | 0.08% |  | 0.08 | % |
| 2 | `JDA-84PDT-00230` | 0.08% |  | 0.08 | % |
| 3 | `JDA-84PDT-00330` | 0.08% |  | 0.08 | % |
| 4 | `JDA-86PDI-12802` | ± 0,10% |  | ± 0;10% |  |
| 5 | `JDA-86PDI-60802` | ± 0,10% |  | ± 0;10% |  |
| 6 | `JDA-86PDI-11803` | ± 0,10% |  | ± 0;10% |  |
| 7 | `JDA-86PDI-11802` | ± 0,10% |  | ± 0;10% |  |
| 8 | `JDA-86PDI-00801` | ± 0,10% |  | ± 0;10% |  |
| 9 | `JDA-86PDI-60801` | ± 0,10% |  | ± 0;10% |  |
| 10 | `JDA-86PDI-01801` | ± 0,10% |  | ± 0;10% |  |
| … | *(69 more tags with this pattern)* |  |  |  |  |

#### Property: `Inlet Size` | Concept: Physical | 46 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-72MOV-00015` | 1" |  | 1 | inch |
| 2 | `JDA-72MOV-00014` | 1inch |  | 1 | in |
| 3 | `JDA-72MOV-00007` | 1inch |  | 1 | in |
| 4 | `JDA-72MOV-00006` | 1inch |  | 1 | in |
| 5 | `JDA-02UZV-00204` | 11" |  | 11 | inch |
| 6 | `JDA-01UZV-02022` | 3/8 " |  | 3/8 | inch |
| 7 | `JDA-01UZV-02021` | 3/8 " |  | 3/8 | inch |
| 8 | `JDA-79MOV-00006B` | 1/2" |  | 1/2 | inch |
| 9 | `JDA-01UZV-05022` | 3/8 " |  | 3/8 | inch |
| 10 | `JDA-01KSV-05031` | 3/8 " |  | 3/8 | inch |
| … | *(36 more tags with this pattern)* |  |  |  |  |

#### Property: `rated voltage` | Concept: Functional Physical | 36 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E6-F208J01` | 690 | volt | 690 | v |
| 2 | `JDA-84ESB-E6-F207J01` | 690 | volt | 690 | v |
| 3 | `JDA-84ESB-E6-F300J01` | 690 | volt | 690 | v |
| 4 | `JDA-84ESB-E6-F301J01` | 690 | volt | 690 | v |
| 5 | `JDA-84ESB-E6-F200J01` | 250 | volt | 250 | v |
| 6 | `JDA-84ESB-E6-F200J21` | 250 | volt | 250 | v |
| 7 | `JDA-84ESB-E6-F201J41` | 250 | volt | 250 | v |
| 8 | `JDA-84ESB-E5-F301J01` | 690 | volt | 690 | v |
| 9 | `JDA-84ESB-E6-F202J41` | 250 | volt | 250 | v |
| 10 | `JDA-84ESB-E6-F204J01` | 250 | volt | 250 | v |
| … | *(26 more tags with this pattern)* |  |  |  |  |

#### Property: `starting current` | Concept: Physical | 35 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-G-84001A` | 0.9 | ampere | 0.9 | a |
| 2 | `JDA-G-84001B` | 0.9 | ampere | 0.9 | a |
| 3 | `JDA-G-84001C` | 0.9 | ampere | 0.9 | a |
| 4 | `JDA-PM-74002A` | 7.3 | ampere | 7.3 | a |
| 5 | `JDA-PM-54001` | 48 | ampere | 48 | a |
| 6 | `JDA-PM-62001` | 107 | ampere | 107 | a |
| 7 | `JDA-PM-62002` | 7.3 | ampere | 7.3 | a |
| 8 | `JDA-PM-73001` | 7.4 | ampere | 7.4 | a |
| 9 | `JDA-PM-73002A` | 7.4 | ampere | 7.4 | a |
| 10 | `JDA-PM-73002B` | 7.4 | ampere | 7.4 | a |
| … | *(25 more tags with this pattern)* |  |  |  |  |

#### Property: `cable type` | Concept: Physical | 32 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2B-F006H04` | 3BTV2-CT |  | 3 | btv2-ct |
| 2 | `JDA-84ESB-E2B-F006H05` | 3BTV2-CT |  | 3 | btv2-ct |
| 3 | `JDA-84ESB-E2B-F006H06` | 3BTV2-CT |  | 3 | btv2-ct |
| 4 | `JDA-84ESB-E2B-F001H03` | 5HTV2-CT |  | 5 | htv2-ct |
| 5 | `JDA-84ESB-E2A-F001H01` | 3HTV2-CT |  | 3 | htv2-ct |
| 6 | `JDA-84ESB-E2A-F001H02` | 3HTV2-CT |  | 3 | htv2-ct |
| 7 | `JDA-84ESB-E2A-F001H03` | 3HTV2-CT |  | 3 | htv2-ct |
| 8 | `JDA-84ESB-E2A-F002H01` | 3HTV2-CT |  | 3 | htv2-ct |
| 9 | `JDA-84ESB-E2A-F002H02` | 3HTV2-CT |  | 3 | htv2-ct |
| 10 | `JDA-84ESB-E2A-F002H03` | 3HTV2-CT |  | 3 | htv2-ct |
| … | *(22 more tags with this pattern)* |  |  |  |  |

#### Property: `Length Of Heat Trace` | Concept: Physical | 32 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2B-F006H04` | 6000mm |  | 6000 | mm |
| 2 | `JDA-84ESB-E2B-F006H05` | 5000mm |  | 5000 | mm |
| 3 | `JDA-84ESB-E2B-F006H06` | 7000mm |  | 7000 | mm |
| 4 | `JDA-84ESB-E2B-F001H03` | 30000mm |  | 30000 | mm |
| 5 | `JDA-84ESB-E2A-F001H01` | 27m |  | 27 | m |
| 6 | `JDA-84ESB-E2A-F001H02` | 13m |  | 13 | m |
| 7 | `JDA-84ESB-E2A-F001H03` | 15m |  | 15 | m |
| 8 | `JDA-84ESB-E2A-F002H01` | 14m |  | 14 | m |
| 9 | `JDA-84ESB-E2A-F002H02` | 57m |  | 57 | m |
| 10 | `JDA-84ESB-E2A-F002H03` | 57m |  | 57 | m |
| … | *(22 more tags with this pattern)* |  |  |  |  |

#### Property: `junction box construction material` | Concept: Physical | 27 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-JB-01001` | 316SS |  | 316 | ss |
| 2 | `JDA-84ESB-E2A-F001J01` | Engineering polymers, black |  | Engineering polymers; black |  |
| 3 | `JDA-84ESB-E2A-F002J01` | Engineering polymers, black |  | Engineering polymers; black |  |
| 4 | `JDA-84ESB-E2B-F001J01` | Engineering polymers, black |  | Engineering polymers; black |  |
| 5 | `JDA-84ESB-E2B-F002J01` | Engineering polymers, black |  | Engineering polymers; black |  |
| 6 | `JDA-84ESB-E2A-F007J01` | Engineering polymers, black |  | Engineering polymers; black |  |
| 7 | `JDA-84ESB-E2B-F006J01` | Engineering polymers, black |  | Engineering polymers; black |  |
| 8 | `JDA-84ESB-E2A-F001J02` | Engineering polymers, black |  | Engineering polymers; black |  |
| 9 | `JDA-84ESB-E2A-F001J03` | Engineering polymers, black |  | Engineering polymers; black |  |
| 10 | `JDA-83ESB-V3C-F057J01` | Engineering polymers, black |  | Engineering polymers; black |  |
| … | *(17 more tags with this pattern)* |  |  |  |  |

#### Property: `mounting arrangement` | Concept: Physical | 27 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-PM-54001` | IM3011, V1(flange) |  | IM3011; V1(flange) |  |
| 2 | `JDA-PM-62001` | IM3011, V1(flange) |  | IM3011; V1(flange) |  |
| 3 | `JDA-PM-61001` | IM3011, V1(flange) |  | IM3011; V1(flange) |  |
| 4 | `JDA-PM-63001` | IM2001, B35(foot-flange) |  | IM2001; B35(foot-flange) |  |
| 5 | `JDA-KM-84101` | IM1001, B3 (foot) |  | IM1001; B3 (foot) |  |
| 6 | `JDA-KM-84102` | IM1001, B3 (foot) |  | IM1001; B3 (foot) |  |
| 7 | `JDA-KM-84201` | IM1001, B3 (foot) |  | IM1001; B3 (foot) |  |
| 8 | `JDA-KM-84301` | IM1001, B3 (foot) |  | IM1001; B3 (foot) |  |
| 9 | `JDA-KM-84202` | IM1001, B3 (foot) |  | IM1001; B3 (foot) |  |
| 10 | `JDA-KM-84302` | IM1001, B3 (foot) |  | IM1001; B3 (foot) |  |
| … | *(17 more tags with this pattern)* |  |  |  |  |

#### Property: `upper limit operating discharge pressure` | Concept: Functional Physical | 14 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-P-62001` | 500000 | pascal | 500000 | pa |
| 2 | `JDA-P-54001` | 200000 | pascal | 200000 | pa |
| 3 | `JDA-P-61001` | 500000 | pascal | 500000 | pa |
| 4 | `JDA-P-62002` | 98100000 | pascal | 98100000 | pa |
| 5 | `JDA-P-73002A` | 17000000 | pascal | 17000000 | pa |
| 6 | `JDA-P-73002B` | 17000000 | pascal | 17000000 | pa |
| 7 | `JDA-P-73001` | 98800000 | pascal | 98800000 | pa |
| 8 | `JDA-P-74002B` | 98100000 | pascal | 98100000 | pa |
| 9 | `JDA-P-74002A` | 98100000 | pascal | 98100000 | pa |
| 10 | `JDA-P-72002B` | 38000000 | pascal | 38000000 | pa |
| … | *(4 more tags with this pattern)* |  |  |  |  |

#### Property: `operating voltage` | Concept: Functional Physical | 13 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84PDT-00130` | 24 | volt | 24 | v |
| 2 | `JDA-84PDT-00230` | 24 | volt | 24 | v |
| 3 | `JDA-84PDT-00330` | 24 | volt | 24 | v |
| 4 | `JDA-72PDI-00013` | 9.0–32.0 | Vdc | 9.0-32.0 | vdc |
| 5 | `JDA-72PDI-00012` | 9.0–32.0 | Vdc | 9.0-32.0 | vdc |
| 6 | `JDA-72PDI-00011` | 9.0–32.0 | Vdc | 9.0-32.0 | vdc |
| 7 | `JDA-72PDI-00010` | 9.0–32.0 | Vdc | 9.0-32.0 | vdc |
| 8 | `JDA-72PDI-00009` | 9.0–32.0 | Vdc | 9.0-32.0 | vdc |
| 9 | `JDA-02TI-00025` | 24 | volt | 24 | v |
| 10 | `JDA-02TI-00024` | 24 | volt | 24 | v |
| … | *(3 more tags with this pattern)* |  |  |  |  |

#### Property: `rated frequency` | Concept: Functional Physical | 13 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-PM-54001` | 50 | hertz | 50 | hz |
| 2 | `JDA-PM-62001` | 50 | hertz | 50 | hz |
| 3 | `JDA-PM-61001` | 50 | hertz | 50 | hz |
| 4 | `JDA-PM-63001` | 50 | hertz | 50 | hz |
| 5 | `JDA-KM-86804` | 50 | hertz | 50 | hz |
| 6 | `JDA-KM-86802A` | 50 | hertz | 50 | hz |
| 7 | `JDA-KM-86803A` | 50 | hertz | 50 | hz |
| 8 | `JDA-KM-86803B` | 50 | hertz | 50 | hz |
| 9 | `JDA-KM-86802B` | 50 | hertz | 50 | hz |
| 10 | `JDA-KM-86801B` | 50 | hertz | 50 | hz |
| … | *(3 more tags with this pattern)* |  |  |  |  |

#### Property: `calibration range` | Concept: Physical | 11 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-74PDI-00033` | 2.5 barg |  | 2.5 | bar(g) |
| 2 | `JDA-74PDI-00032` | 2.5 barg |  | 2.5 | bar(g) |
| 3 | `JDA-84PDT-00130` | 0-12mBar |  | 0-12 | mbar |
| 4 | `JDA-84PDT-00230` | 0-12mBar |  | 0-12 | mbar |
| 5 | `JDA-84PDT-00330` | 0-12mBar |  | 0-12 | mbar |
| 6 | `JDA-86PI-70803` | 0-10 barg |  | 0-10 | bar(g) |
| 7 | `JDA-86PI-70802` | 0-10 barg |  | 0-10 | bar(g) |
| 8 | `JDA-86PI-70800` | 0-10 barg |  | 0-10 | bar(g) |
| 9 | `JDA-86PI-70801` | 0-10 barg |  | 0-10 | bar(g) |
| 10 | `JDA-86PI-70804` | 0-10 barg |  | 0-10 | bar(g) |
| … | *(1 more tags with this pattern)* |  |  |  |  |

#### Property: `Temperature Rise - Rotor` | Concept: Physical | 7 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-G-84001A` | 90,0 0C |  | 90;0 0C |  |
| 2 | `JDA-G-84001B` | 90,0 0C |  | 90;0 0C |  |
| 3 | `JDA-G-84001C` | 90,0 0C |  | 90;0 0C |  |
| 4 | `JDA-PM-54001` | 29K |  | 29 | k |
| 5 | `JDA-PM-62001` | 48K |  | 48 | k |
| 6 | `JDA-PM-61001` | 29K |  | 29 | k |
| 7 | `JDA-PM-63001` | 60K |  | 60 | k |

#### Property: `rated short circuit current` | Concept: Functional Physical | 7 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-H-62001` | 25000 | ampere | 25000 | a |
| 2 | `JDA-H-63001` | 25000 | ampere | 25000 | a |
| 3 | `JDA-H-01001` | 25000 | ampere | 25000 | a |
| 4 | `JDA-XH-79001` | 10000 | ampere | 10000 | a |
| 5 | `JDA-XH-79002` | 10000 | ampere | 10000 | a |
| 6 | `JDA-H-62002` | 25000 | ampere | 25000 | a |
| 7 | `JDA-H-63002` | 25000 | ampere | 25000 | a |

#### Property: `frame size` | Concept: Physical | 7 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-PM-46001B` | 100L |  | 100 | l |
| 2 | `JDA-PM-46001A` | 100L |  | 100 | l |
| 3 | `JDA-PM-72003A` | 112M |  | 112 | m |
| 4 | `JDA-PM-72003B` | 112M |  | 112 | m |
| 5 | `JDA-PM-72002A` | 160M |  | 160 | m |
| 6 | `JDA-PM-72002B` | 160M |  | 160 | m |
| 7 | `JDA-PM-72001` | 90L |  | 90 | l |

#### Property: `Serial Number Of Actuator` | Concept: Physical | 7 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-51MOV-00001` | 6X00015923 |  | 6 | x00015923 |
| 2 | `JDA-01MOV-02001` | 6X00015681 |  | 6 | x00015681 |
| 3 | `JDA-01MOV-05001` | 6X00015683 |  | 6 | x00015683 |
| 4 | `JDA-01MOV-03001` | 6X00015682 |  | 6 | x00015682 |
| 5 | `JDA-01MOV-06001` | 6X00015684 |  | 6 | x00015684 |
| 6 | `JDA-62PCV-00026` | 6X00044866 |  | 6 | x00044866 |
| 7 | `JDA-63PCV-00064` | 6X00037897 |  | 6 | x00037897 |

#### Property: `Length Tangent/Tangent` | Concept: Physical | 6 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-H-84103` | 230mm |  | 230 | mm |
| 2 | `JDA-H-84104` | 834mm |  | 834 | mm |
| 3 | `JDA-H-84203` | 230mm |  | 230 | mm |
| 4 | `JDA-H-84303` | 230mm |  | 230 | mm |
| 5 | `JDA-H-84204` | 834mm |  | 834 | mm |
| 6 | `JDA-H-84304` | 834mm |  | 834 | mm |

#### Property: `Valve Rating` | Concept: Physical | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-01PCV-00008` | 1034 barg |  | 1034 | bar(g) |
| 2 | `JDA-01MOV-05002` | 15kpsi |  | 15 | kpsi |
| 3 | `JDA-01MOV-06002` | 15kpsi |  | 15 | kpsi |
| 4 | `JDA-01MOV-03002` | 15kpsi |  | 15 | kpsi |
| 5 | `JDA-01MOV-02002` | 15kpsi |  | 15 | kpsi |

#### Property: `impedance voltage` | Concept: Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-TR-VV1B` | 0.04 | volt | 0.04 | v |
| 2 | `JDA-TR-VV1A` | 0.04 | volt | 0.04 | v |
| 3 | `JDA-TR-VV2B` | 0.04 | volt | 0.04 | v |
| 4 | `JDA-TR-VV2A` | 0.04 | volt | 0.04 | v |

#### Property: `rated primary voltage` | Concept: Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-TR-VV1B` | 400 | volt | 400 | v |
| 2 | `JDA-TR-VV1A` | 400 | volt | 400 | v |
| 3 | `JDA-TR-VV2B` | 400 | volt | 400 | v |
| 4 | `JDA-TR-VV2A` | 400 | volt | 400 | v |

#### Property: `rated primary winding voltage` | Concept: Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-TR-VV1B` | 400 | volt | 400 | v |
| 2 | `JDA-TR-VV1A` | 400 | volt | 400 | v |
| 3 | `JDA-TR-VV2B` | 400 | volt | 400 | v |
| 4 | `JDA-TR-VV2A` | 400 | volt | 400 | v |

#### Property: `rated secondary winding voltage` | Concept: Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-TR-VV1B` | 400 | volt | 400 | v |
| 2 | `JDA-TR-VV1A` | 400 | volt | 400 | v |
| 3 | `JDA-TR-VV2B` | 400 | volt | 400 | v |
| 4 | `JDA-TR-VV2A` | 400 | volt | 400 | v |

#### Property: `secondary voltage` | Concept: Functional Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-TR-VV1B` | 230 | volt | 230 | v |
| 2 | `JDA-TR-VV1A` | 230 | volt | 230 | v |
| 3 | `JDA-TR-VV2B` | 230 | volt | 230 | v |
| 4 | `JDA-TR-VV2A` | 230 | volt | 230 | v |

#### Property: `lower limit operating suction pressure` | Concept: Functional Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-K-86805B` | 2500000 | pascal | 2500000 | pa |
| 2 | `JDA-K-86806A` | 2500000 | pascal | 2500000 | pa |
| 3 | `JDA-K-86806B` | 2500000 | pascal | 2500000 | pa |
| 4 | `JDA-K-86805A` | 2500000 | pascal | 2500000 | pa |

#### Property: `Suction Pressure - Normal` | Concept: Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-P-62001` | 0 barg |  | 0 | bar(g) |
| 2 | `JDA-P-54001` | 0 barg |  | 0 | bar(g) |
| 3 | `JDA-P-61001` | 0 barg |  | 0 | bar(g) |
| 4 | `JDA-P-63001` | 0 barg |  | 0 | bar(g) |

#### Property: `Actuator Size` | Concept: Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-72MOV-00015` | 7kg |  | 7 | kg |
| 2 | `JDA-72MOV-00014` | 7kg |  | 7 | kg |
| 3 | `JDA-72MOV-00007` | 7kg |  | 7 | kg |
| 4 | `JDA-72MOV-00006` | 7kg |  | 7 | kg |

#### Property: `pcs_SOUND_LEVEL_CALCULATION` | Concept: Physical | 3 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-67UZV-00803` | 0dB |  | 0 | db |
| 2 | `JDA-67UZV-00801` | 0dB |  | 0 | db |
| 3 | `JDA-67UZV-00802` | 0dB |  | 0 | db |

#### Property: `Flow Maximum` | Concept: Physical | 2 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-K-86806A` | 9,50 l/s |  | 9;50 l/s |  |
| 2 | `JDA-K-86806B` | 9,50 l/s |  | 9;50 l/s |  |

#### Property: `Connection Size` | Concept: Physical | 2 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-54SP-0021` | 80mm |  | 80 | mm |
| 2 | `JDA-61SP-0532` | 80mm |  | 80 | mm |

#### Property: `Contactor Type` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-CP-62001` | yes, Thyristor |  | yes; Thyristor |  |


### ⚠️ RDL_CSV_VALUE_MISSING — RDL has value, CSV is blank (639 total gaps — 40 property groups)

#### Property: `explosion protection material group` | Concept: Physical | 256 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-83CP-V2-037` |  |  | <blank> |  |
| 2 | `JDA-83CP-V2-041` |  |  | <blank> |  |
| 3 | `JDA-83CP-V2-043` |  |  | <blank> |  |
| 4 | `JDA-ES-84802` |  |  | <blank> |  |
| 5 | `JDA-ES-84803` |  |  | <blank> |  |
| 6 | `JDA-ES-84801` |  |  | <blank> |  |
| 7 | `JDA-83ESB-V3C-F102X01` |  |  | <blank> |  |
| 8 | `JDA-TH-86804` |  |  | <blank> |  |
| 9 | `JDA-TH-86831` |  |  | <blank> |  |
| 10 | `JDA-84ESB-E2A-F106X01` |  |  | <blank> |  |
| … | *(246 more tags with this pattern)* |  |  |  |  |

#### Property: `rated current` | Concept: Functional Physical | 130 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-83CP-V2-037` | unset |  | <blank> |  |
| 2 | `JDA-83CP-V2-041` | unset |  | <blank> |  |
| 3 | `JDA-83CP-V2-043` | unset |  | <blank> |  |
| 4 | `JDA-ES-84802` | unset |  | <blank> |  |
| 5 | `JDA-ES-84803` | unset |  | <blank> |  |
| 6 | `JDA-ES-84801` | unset |  | <blank> |  |
| 7 | `JDA-83ESB-V3C-F102X01` | unset |  | <blank> |  |
| 8 | `JDA-TH-86804` | unset |  | <blank> |  |
| 9 | `JDA-TH-86831` | unset |  | <blank> |  |
| 10 | `JDA-84ESB-E2A-F106X01` | unset |  | <blank> |  |
| … | *(120 more tags with this pattern)* |  |  |  |  |

#### Property: `rated voltage` | Concept: Functional Physical | 90 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-ES-84802` | unset |  | <blank> |  |
| 2 | `JDA-ES-84803` | unset |  | <blank> |  |
| 3 | `JDA-ES-84801` | unset |  | <blank> |  |
| 4 | `JDA-83ESB-V3C-F102X01` | unset |  | <blank> |  |
| 5 | `JDA-TH-86831` | unset |  | <blank> |  |
| 6 | `JDA-84ESB-E6-F200X04` | unset |  | <blank> |  |
| 7 | `JDA-84ESB-E6-F200X01` | unset |  | <blank> |  |
| 8 | `JDA-84ESB-E6-F200X03` | unset |  | <blank> |  |
| 9 | `JDA-84ESB-E6-F200X23` | unset |  | <blank> |  |
| 10 | `JDA-84ESB-E6-F200X44` | unset |  | <blank> |  |
| … | *(80 more tags with this pattern)* |  |  |  |  |

#### Property: `weight net` | Concept: Physical | 47 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-EE-E1A` | unset |  | <blank> |  |
| 2 | `JDA-EE-E1B` | unset |  | <blank> |  |
| 3 | `JDA-EE-E1C` | unset |  | <blank> |  |
| 4 | `JDA-EE-V1A` | unset |  | <blank> |  |
| 5 | `JDA-EE-V1B` | unset |  | <blank> |  |
| 6 | `JDA-X-79951` | unset |  | <blank> |  |
| 7 | `JDA-X-68801` | unset |  | <blank> |  |
| 8 | `JDA-X-68004` | unset |  | <blank> |  |
| 9 | `JDA-3"-H74012-LD30-N` | unset |  | <blank> |  |
| 10 | `JDA-2"-D62021-153842-3FE` | unset |  | <blank> |  |
| … | *(37 more tags with this pattern)* |  |  |  |  |

#### Property: `operating voltage` | Concept: Functional Physical | 11 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-86PI-70803` |  |  | <blank> |  |
| 2 | `JDA-86PI-70802` |  |  | <blank> |  |
| 3 | `JDA-86PI-70800` |  |  | <blank> |  |
| 4 | `JDA-86PI-70801` |  |  | <blank> |  |
| 5 | `JDA-86PI-70804` |  |  | <blank> |  |
| 6 | `JDA-86PI-70805` |  |  | <blank> |  |
| 7 | `JDA-73FE-00108` |  |  | <blank> |  |
| 8 | `JDA-73FE-00109` |  |  | <blank> |  |
| 9 | `JDA-73FE-00110` |  |  | <blank> |  |
| 10 | `JDA-73FE-00111` |  |  | <blank> |  |
| … | *(1 more tags with this pattern)* |  |  |  |  |

#### Property: `pcs_EX_CLASS` | Concept: Physical | 9 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-01PG-02053` |  |  | <blank> |  |
| 2 | `JDA-01PG-03053` |  |  | <blank> |  |
| 3 | `JDA-01PG-05053` |  |  | <blank> |  |
| 4 | `JDA-01PG-06053` |  |  | <blank> |  |
| 5 | `JDA-01PG-04053` |  |  | <blank> |  |
| 6 | `JDA-01PG-07053` |  |  | <blank> |  |
| 7 | `JDA-01PG-08053` |  |  | <blank> |  |
| 8 | `JDA-01PG-09053` |  |  | <blank> |  |
| 9 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `signal type` | Concept: Physical | 6 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-86PI-70803` | unset |  | <blank> |  |
| 2 | `JDA-86PI-70802` | unset |  | <blank> |  |
| 3 | `JDA-86PI-70800` | unset |  | <blank> |  |
| 4 | `JDA-86PI-70801` | unset |  | <blank> |  |
| 5 | `JDA-86PI-70804` | unset |  | <blank> |  |
| 6 | `JDA-86PI-70805` | unset |  | <blank> |  |

#### Property: `Type [Pneumatic/Electronic]` | Concept: Physical | 6 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-86PI-70803` | unset |  | <blank> |  |
| 2 | `JDA-86PI-70802` | unset |  | <blank> |  |
| 3 | `JDA-86PI-70800` | unset |  | <blank> |  |
| 4 | `JDA-86PI-70801` | unset |  | <blank> |  |
| 5 | `JDA-86PI-70804` | unset |  | <blank> |  |
| 6 | `JDA-86PI-70805` | unset |  | <blank> |  |

#### Property: `outlet flange size` | Concept: Physical | 6 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-S-84102` | unset |  | <blank> |  |
| 2 | `JDA-S-84202` | unset |  | <blank> |  |
| 3 | `JDA-S-84302` | unset |  | <blank> |  |
| 4 | `JDA-S-84103` | unset |  | <blank> |  |
| 5 | `JDA-S-84203` | unset |  | <blank> |  |
| 6 | `JDA-S-84303` | unset |  | <blank> |  |

#### Property: `design specification` | Concept: Functional Physical | 6 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-S-84102` |  |  | <blank> |  |
| 2 | `JDA-S-84202` |  |  | <blank> |  |
| 3 | `JDA-S-84302` |  |  | <blank> |  |
| 4 | `JDA-S-84103` |  |  | <blank> |  |
| 5 | `JDA-S-84203` |  |  | <blank> |  |
| 6 | `JDA-S-84303` |  |  | <blank> |  |

#### Property: `inlet flange rating` | Concept: Physical | 6 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-S-84102` |  |  | <blank> |  |
| 2 | `JDA-S-84202` |  |  | <blank> |  |
| 3 | `JDA-S-84302` |  |  | <blank> |  |
| 4 | `JDA-S-84103` |  |  | <blank> |  |
| 5 | `JDA-S-84203` |  |  | <blank> |  |
| 6 | `JDA-S-84303` |  |  | <blank> |  |

#### Property: `outlet flange rating` | Concept: Physical | 6 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-S-84102` |  |  | <blank> |  |
| 2 | `JDA-S-84202` |  |  | <blank> |  |
| 3 | `JDA-S-84302` |  |  | <blank> |  |
| 4 | `JDA-S-84103` |  |  | <blank> |  |
| 5 | `JDA-S-84203` |  |  | <blank> |  |
| 6 | `JDA-S-84303` |  |  | <blank> |  |

#### Property: `net tank capacity` | Concept: Functional Physical | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `sacrificial anodes` | Concept: Functional Physical | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `tank roof type` | Concept: Functional Physical | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `Sacraficial Anodes [Yes/No]` | Concept: Physical | 5 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-T-69101` | unset |  | <blank> |  |
| 2 | `JDA-T-69102` | unset |  | <blank> |  |
| 3 | `JDA-T-69103` | unset |  | <blank> |  |
| 4 | `JDA-T-69104` | unset |  | <blank> |  |
| 5 | `JDA-T-69105` | unset |  | <blank> |  |

#### Property: `pressure equipment category` | Concept: Functional Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-02WE-00101` | unset |  | <blank> |  |
| 2 | `JDA-02WE-00102` | unset |  | <blank> |  |
| 3 | `JDA-02WE-00204` | unset |  | <blank> |  |
| 4 | `JDA-62WE-00004` | unset |  | <blank> |  |

#### Property: `connection symbol` | Concept: Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-TR-VV1B` | unset |  | <blank> |  |
| 2 | `JDA-TR-VV1A` | unset |  | <blank> |  |
| 3 | `JDA-TR-VV2B` | unset |  | <blank> |  |
| 4 | `JDA-TR-VV2A` | unset |  | <blank> |  |

#### Property: `impedance/reactance` | Concept: Physical | 4 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-TR-VV1B` |  |  | <blank> |  |
| 2 | `JDA-TR-VV1A` |  |  | <blank> |  |
| 3 | `JDA-TR-VV2B` |  |  | <blank> |  |
| 4 | `JDA-TR-VV2A` |  |  | <blank> |  |

#### Property: `atex category` | Concept: Physical | 3 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2A-F106X01` |  |  | <blank> |  |
| 2 | `JDA-29GZT-00001` |  |  | <blank> |  |
| 3 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `atex explosive atmosphere` | Concept: Physical | 3 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2A-F106X01` |  |  | <blank> |  |
| 2 | `JDA-29GZT-00001` |  |  | <blank> |  |
| 3 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `atex group` | Concept: Physical | 3 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2A-F106X01` |  |  | <blank> |  |
| 2 | `JDA-29GZT-00001` |  |  | <blank> |  |
| 3 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `Valve Rating` | Concept: Physical | 2 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-02UZV-00101` | unset |  | <blank> |  |
| 2 | `JDA-02UZV-00102` | unset |  | <blank> |  |

#### Property: `Power - Normal` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2B-F002H08` | unset |  | <blank> |  |

#### Property: `rated power consumption` | Concept: Functional Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2B-F002H08` | unset |  | <blank> |  |

#### Property: `cable type` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2B-F002H08` | unset |  | <blank> |  |

#### Property: `Length Of Heat Trace` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-84ESB-E2B-F002H08` | unset |  | <blank> |  |

#### Property: `rated output voltage` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-S-68001` | unset |  | <blank> |  |

#### Property: `driver type` | Concept: Functional Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-YLB-68001` | unset |  | <blank> |  |

#### Property: `type of boat/capsule` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-YLB-68001` | unset |  | <blank> |  |

#### Property: `body material` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-62MV-0078` |  |  | <blank> |  |

#### Property: `Trim Size` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-79PCV-00001` | unset |  | <blank> |  |

#### Property: `explosion protection gas group` | Concept: Functional Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `explosion protection temperature class` | Concept: Functional Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `explosion protection zone` | Concept: Functional Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `pcs_EX_CERTIFICATE` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `pcs_IP_GRADE` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `explosion protection notified body` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-75-38-TJB-801` |  |  | <blank> |  |

#### Property: `junction box construction material` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-75-38-TJB-801` | unset |  | <blank> |  |

#### Property: `pcs_HEATTRACE_FUNCTION` | Concept: Physical | 1 tags affected

| # | Tag | RDL Value | RDL UoM | CSV Value | CSV UoM |
|---|-----|--- | --- | --- | ---|
| 1 | `JDA-75-38-TJB-801` |  |  | <blank> |  |


---

## LAYER 1 — RDL vs SQL Gaps

> RDL after filters: **313,302** rows pre-filter; **0** tag props, **0** equip props, **0** Functional Physical (both files).

> ⚠️ DB unavailable — Layer 1 analysis skipped.

---

## LAYER 2 — SQL vs CSV 010 (Tag Property Values)

> ⚠️ DB unavailable — Layer 2 file-010 analysis skipped.

---

## LAYER 2 — SQL vs CSV 011 (Equipment Property Values)

> ⚠️ DB unavailable — Layer 2 file-011 analysis skipped.

---

---

## Legend

| Icon | Code | Layer | Meaning |
|------|------|-------|---------|
| ⛔ | SQL_MISSING | L1 | In RDL but absent from SQL database — never imported |
| ⚠️ | SQL_VALUE_MISMATCH | L1 | Value in SQL differs from RDL reference |
| ⚠️ | SQL_VALUE_MISSING | L1 | RDL has value, SQL is blank (not NA) — import error |
| 🔕 | SQL_NA_BLANK | L1 | RDL has 'NA' but SQL has empty/null |
| ➕ | SQL_EXTRA | L1 | In SQL (non-Common) but not present in RDL |
| ❌ | CSV_MISSING | L2 | In SQL but absent from export CSV |
| ⚠️ | CSV_VALUE_MISMATCH | L2 | Value in CSV differs from SQL |
| ⚠️ | CSV_VALUE_MISSING | L2 | SQL has value, CSV is blank (not NA) — export error |
| ℹ️ | CSV_EXTRA_VALUE | L2 | SQL is blank, CSV has value — unexpected content |
| 🔕 | CSV_NA_BLANK | L2 | SQL has 'NA' but CSV has empty string |
| 🔁 | CSV_DUPLICATE | L2 | Same TAG_NAME/EQUIP_NUMBER + PROPERTY_NAME appears >1 time in CSV |
| 🔀 | CSV_WRONG_FILE | L2 | Property in wrong file (Physical in 010 or Functional in 011) |
| ➕ | EXTRA_UNKNOWN_TAG | L2 | Tag in CSV has no matching tag in SQL at all |
| ➕ | EXTRA_UNKNOWN_PROP | L2 | Tag known in SQL but this property pair is not in SQL |
| ℹ️ | RDL_CSV_NA_HAS_VALUE | L0 | RDL has 'NA' but CSV has value — possible RDL error |
| ⚠️ | RDL_CSV_VALUE_MISSING | L0 | RDL has value, CSV is blank — omitted during export |

> **Compact mode** (`--compact`): gaps grouped by (property, concept). Up to 10 example tags shown per group. Use VALUE_MISMATCH count / group count to estimate whether an issue is systemic (high ratio) or sporadic (low ratio).