-- migration_024_tag_naming_rules_seed.sql
-- Seed TAG naming rules from JACK_namingRules_master.xlsx into audit_core.naming_rule
-- Apply AFTER migration_023_naming_rules.sql
-- Generated: 2026-04-03
-- Source: JACK_namingRules_master.xlsx, sheets: NamingRules_V3 + NamingRules_V2
-- Total: 35 TAG rules covering ENS sections 5.2 – 5.22 + 7.x interface cables

BEGIN;

-- Remove any previously seeded TAG rows to allow idempotent re-run
DELETE FROM audit_core.naming_rule WHERE domain = 'TAG';

-- ── ENS 5.2 – MECHANICAL & ELECTRICAL MAIN EQUIPMENT ──────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5021', '5.2.1a MECHANICAL MAIN EQUIPMENT',
  $$JDA[ ]?(-|‐)[ ]?((A|B|B|C|D|E|F|G|J|K|L|M|P|R|S|T|U|V|W|X|Z)|(EG|GT|KT|PD|PG|GD|PS|SD|VC|XE|XG|XP))[ ]?(-|‐)[ ]?(01|02|08|29|35|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[A-G]?(\/B)?(\/C)?$$,
  $$^JDA[ ]?(-|‐)[ ]?((A|B|B|C|D|E|F|G|J|K|L|M|P|R|S|T|U|V|W|X|Z)|(EG|GT|KT|PD|PG|GD|PS|SD|VC|XE|XG|XP))[ ]?(-|‐)[ ]?(01|02|08|29|35|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[A-G]?(\/B)?(\/C)?$$$,
  50, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5022', '5.2.1b ELECTRICAL MAIN EQUIPMENT',
  $$JDA[ ]?(-|‐)[ ]?(H|PM|EM|XM|KM|TH|XH|ES|HE|CP|VS)[ ]?(-|‐)[ ]?(01|02|08|29|35|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[A-Z]?(\/B)?(\/C)?$$,
  $$^JDA[ ]?(-|‐)[ ]?(H|PM|EM|XM|KM|TH|XH|ES|HE|CP|VS)[ ]?(-|‐)[ ]?(01|02|08|29|35|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[A-Z]?(\/B)?(\/C)?$$$,
  51, TRUE);

-- ── ENS 5.3 – HVAC ────────────────────────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5031', '5.3.1a HVAC EQUIPMENT',
  $$JDA[ ]?(-|‐)[ ]?(HAH|HCC|HCF|HCU|HCV|HDC|HDF|HDN|HDR|HDS|HDV|HEG|HHU|HLV|HSA|HSG|HTU)[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[0-9A-G]?(\/B)?(\/C)?(-[0-9])?$$,
  $$^JDA[ ]?(-|‐)[ ]?(HAH|HCC|HCF|HCU|HCV|HDC|HDF|HDN|HDR|HDS|HDV|HEG|HHU|HLV|HSA|HSG|HTU)[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[0-9A-G]?(\/B)?(\/C)?(-[0-9])?$$$,
  52, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5032', '5.3.1b HVAC & INTERFACE SIGNALS',
  $$JDA[ ]?(-|‐)[ ]?(CST|DGA|DGB|DGZ|DIT|DST|DSY|DXS|DXT|GA|GB|GEA|GET|GGA|GGB|GHS|GIA|GIT|GKT|GLT|GPT|GST|GTT|GXA|GXZ|HGA|HGB|HIT|HXS|HXZ|IT|KGA|KGB|KIT|KXS|PGA|PGB|PGZ|PIT|PST|PXS|PXZ|TET|TGA|TGB|TIT|TXS|TXT|TXY|XA|XGA|XGB|XI|XIT|XS|XXS)[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[A-Z]?[0-9]?(-[0-9]{1,2}[A-Z]?)?$$,
  $$^JDA[ ]?(-|‐)[ ]?(CST|DGA|DGB|DGZ|DIT|DST|DSY|DXS|DXT|GA|GB|GEA|GET|GGA|GGB|GHS|GIA|GIT|GKT|GLT|GPT|GST|GTT|GXA|GXZ|HGA|HGB|HIT|HXS|HXZ|IT|KGA|KGB|KIT|KXS|PGA|PGB|PGZ|PIT|PST|PXS|PXZ|TET|TGA|TGB|TIT|TXS|TXT|TXY|XA|XGA|XGB|XI|XIT|XS|XXS)[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[A-Z]?[0-9]?(-[0-9]{1,2}[A-Z]?)?$$$,
  53, TRUE);

-- ── ENS 5.4 – SAFETY EQUIPMENT ───────────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5041', '5.4.1 SAFETY EQUIPMENT',
  $$JDA[ ]?(-|‐)[ ]?[0-9]?(YBA|YBS|YDC|YDF|YDT|YDV|YEE|YFA|YFV|YGS|YHC|YHR|YHT|YIM|YLB|YPC|YPM|YSE|YXC|YXP|YXT)[ ]?(-|‐)[ ]?[0-9][0-9]?[0-9]{3}[A-G]?(\/B)?(\/C)?$$,
  $$^JDA[ ]?(-|‐)[ ]?[0-9]?(YBA|YBS|YDC|YDF|YDT|YDV|YEE|YFA|YFV|YGS|YHC|YHR|YHT|YIM|YLB|YPC|YPM|YSE|YXC|YXP|YXT)[ ]?(-|‐)[ ]?[0-9][0-9]?[0-9]{3}[A-G]?(\/B)?(\/C)?$$$,
  54, TRUE);

-- ── ENS 5.5 – ELECTRICAL DISTRIBUTION ───────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5051', '5.5.1 ELECTRICAL DISTRIBUTION AND CONTROL EQUIPMENT',
  $$JDA[ ]?(-|‐)[ ]?(AP|BA|BD|CA|CB|CN|CP|DP|EE|IR|JB|MC|RR|RX|SB|TR|UP|VS|ES)[ ]?(-|‐)[ ]?[A-Z]{1,2}[0-9](A|B|C|D|E|F|V|X|L|R)?$$,
  $$^JDA[ ]?(-|‐)[ ]?(AP|BA|BD|CA|CB|CN|CP|DP|EE|IR|JB|MC|RR|RX|SB|TR|UP|VS|ES)[ ]?(-|‐)[ ]?[A-Z]{1,2}[0-9](A|B|C|D|E|F|V|X|L|R)?$$$,
  55, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5052', '5.5.2 ELECTRICAL HV JUNCTION BOX',
  $$JDA[ ]?(-|‐)[ ]?(JB)[ ]?(-|‐)[ ]?[0-9]{5}[A-G]?(\/B)?(\/C)?$$,
  $$^JDA[ ]?(-|‐)[ ]?(JB)[ ]?(-|‐)[ ]?[0-9]{5}[A-G]?(\/B)?(\/C)?$$$,
  56, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5053', '5.5.3 ELECTRICAL CIRCUIT-BREAKER',
  $$JDA[ ]?(-|‐)[ ]?(AP|BA|BD|CA|CB|CN|CP|DP|EE|IR|JB|MC|RR|RX|SB|TR|UP|VS|ES)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X)?-(F|Q|S)[0-9]{3}$$,
  $$^JDA[ ]?(-|‐)[ ]?(AP|BA|BD|CA|CB|CN|CP|DP|EE|IR|JB|MC|RR|RX|SB|TR|UP|VS|ES)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X)?-(F|Q|S)[0-9]{3}$$$,
  57, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5054', '5.5.4 ELECTRICAL SWITCHBOARD CUBICLE',
  $$JDA[ ]?(-|‐)[ ]?(AP|BA|BD|CA|CB|CN|CP|DP|EE|IR|JB|MC|RR|RX|SB|TR|UP|VS|ES)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X)?[ ]?\+[ ]?(A|B){1,2}[0-9]{1,2}(\.[A-Z]?[0-9]?)?$$,
  $$^JDA[ ]?(-|‐)[ ]?(AP|BA|BD|CA|CB|CN|CP|DP|EE|IR|JB|MC|RR|RX|SB|TR|UP|VS|ES)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X)?[ ]?\+[ ]?(A|B){1,2}[0-9]{1,2}(\.[A-Z]?[0-9]?)?$$$,
  58, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5055', '5.5.5 ELECTRICAL SWITCHBOARD CUBICLE SHORT',
  $$\+(A|B){1,2}[0-9]{1,2}(\.[A-Z]?[0-9]?)?$$,
  $$^\+(A|B){1,2}[0-9]{1,2}(\.[A-Z]?[0-9]?)?$$$,
  59, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5057', '5.5.7 ELECTRICAL CIRCUIT-BREAKER THERMO-MAGNETIC',
  $$JDA[ ]?(-|‐)[ ]?(AP|BA|BD|CA|CB|CN|CP|DP|EE|IR|JB|MC|RR|RX|SB|TR|UP|VS|ES)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X)?-FS[0-9]{2}$$,
  $$^JDA[ ]?(-|‐)[ ]?(AP|BA|BD|CA|CB|CN|CP|DP|EE|IR|JB|MC|RR|RX|SB|TR|UP|VS|ES)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X)?-FS[0-9]{2}$$$,
  60, TRUE);

-- ── ENS 5.6 – MAIN ELECTRICAL CABLES ─────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5061', '5.6.1 MAIN ELECTRICAL CABLES',
  $$JDA[ ]?(-|‐)[ ]?(01|02|08|29|35|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[ ]?(-|‐)[ ]?CE(C|E|H|L)(B|D|R|Y|N|E)?(-[0-9])?$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|08|29|35|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[ ]?(-|‐)[ ]?CE(C|E|H|L)(B|D|R|Y|N|E)?(-[0-9])?$$$,
  61, TRUE);

-- ── ENS 5.7 – LIGHTING & SMALL POWER ─────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5071', '5.7.1 LIGHTING AND SMALL POWER DEVICES',
  $$JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(EBD|ECJ|ECW|EHF|EIS|EJB|ELF|ENE|ETB|ETC|ETJ|ETM|ETP|ETX|EWO|ESB|ECP)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X){0,2}-F[0-9]{3}(E|H|J|L|P|S|T|X)[0-9]{2}$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(EBD|ECJ|ECW|EHF|EIS|EJB|ELF|ENE|ETB|ETC|ETJ|ETM|ETP|ETX|EWO|ESB|ECP)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X){0,2}-F[0-9]{3}(E|H|J|L|P|S|T|X)[0-9]{2}$$$,
  62, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5072', '5.7.2 LIGHTING CABLES MAIN',
  $$JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(EBD|ECJ|ECW|EHF|EIS|EJB|ELF|ENE|ETB|ETC|ETJ|ETM|ETP|ETX|EWO|ESB|ECP)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X){0,2}-F[0-9]{5}$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(EBD|ECJ|ECW|EHF|EIS|EJB|ELF|ENE|ETB|ETC|ETJ|ETM|ETP|ETX|EWO|ESB|ECP)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X){0,2}-F[0-9]{5}$$$,
  63, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5073', '5.7.3 LIGHTING CABLES SECONDARY',
  $$JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(EBD|ECJ|ECW|EHF|EIS|EJB|ELF|ENE|ETB|ETC|ETJ|ETM|ETP|ETX|EWO|ESB|ECP)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X){0,2}-(A|B)[0-9]{2}(J|N)[0-9]{2}$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|84|85|86)(EBD|ECJ|ECW|EHF|EIS|EJB|ELF|ENE|ETB|ETC|ETJ|ETM|ETP|ETX|EWO|ESB|ECP)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X){0,2}-(A|B)[0-9]{2}(J|N)[0-9]{2}$$$,
  64, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5074', '5.7.4 LIGHTING CABLES HEATING',
  $$JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(EBD|ECJ|ECW|EHF|EIS|EJB|ELF|ENE|ETB|ETC|ETJ|ETM|ETP|ETX|EWO|ESB|ECP)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X){0,2}-F[0-9]{3}H[0-9]{2}$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(EBD|ECJ|ECW|EHF|EIS|EJB|ELF|ENE|ETB|ETC|ETJ|ETM|ETP|ETX|EWO|ESB|ECP)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X){0,2}-F[0-9]{3}H[0-9]{2}$$$,
  65, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5075', '5.7.1c LIGHTING CABLES NAVAID',
  $$JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(CP)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X){0,2}-[0-9]{3}$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(CP)[ ]?(-|‐)[ ]?[A-Z][0-9](A|B|C|D|E|F|V|X){0,2}-[0-9]{3}$$$,
  66, TRUE);

-- ── ENS 5.10 – PIPING SYSTEMS ────────────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5101', '5.10 PIPING SYSTEMS',
  $$JDA[ ]?(-|‐)[ ]?[0-9]{1,2}(\s[0-9]{1,2}\/[0-9]{1,2}|\/[0-9])?("|”)[ ]?(-|‐)[ ]?(A|B|C|D|E|F|G|H|L|N|P|Q|R|S|V|W|X|Z|M|T)[0-9]{2}[0-9]?[0-9]{3}[ ]?(-|‐)[ ]?[A-Z0-9]{3,6}([ ]?(-|‐)[ ]?([0-9](FE|C|H|P|F))|[ ]?(-|‐)[ ]?N|[ ]?(-|‐)[ ]?)?$$,
  $$^JDA[ ]?(-|‐)[ ]?[0-9]{1,2}(\s[0-9]{1,2}\/[0-9]{1,2}|\/[0-9])?("|”)[ ]?(-|‐)[ ]?(A|B|C|D|E|F|G|H|L|N|P|Q|R|S|V|W|X|Z|M|T)[0-9]{2}[0-9]?[0-9]{3}[ ]?(-|‐)[ ]?[A-Z0-9]{3,6}([ ]?(-|‐)[ ]?([0-9](FE|C|H|P|F))|[ ]?(-|‐)[ ]?N|[ ]?(-|‐)[ ]?)?$$$,
  67, TRUE);

-- ── ENS 5.12 – UTILITY STATIONS ──────────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5121', '5.12 UTILITY STATIONS',
  $$JDA[ ]?(-|‐)[ ]?US(A|B|C|D)[ ]?(-|‐)[ ]?[0-9]{4}?$$,
  $$^JDA[ ]?(-|‐)[ ]?US(A|B|C|D)[ ]?(-|‐)[ ]?[0-9]{4}?$$$,
  68, TRUE);

-- ── ENS 5.14 – MANUAL VALVES ─────────────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5141', '5.14 MANUAL VALVES',
  $$(JDA[ ]?(-|‐)[ ]?)?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(MV|NRV)[ ]?(-|‐)[ ]?[0-9]{4}$$,
  $$^(JDA[ ]?(-|‐)[ ]?)?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(MV|NRV)[ ]?(-|‐)[ ]?[0-9]{4}$$$,
  69, TRUE);

-- ── ENS 5.15 – SPECIAL PIPING ITEMS ─────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5151', '5.15 SPECIAL PIPING ITEMS',
  $$(JDA[ ]?(-|‐)[ ]?)?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)SP[ ]?(-|‐)[ ]?[0-9]{4}$$,
  $$^(JDA[ ]?(-|‐)[ ]?)?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)SP[ ]?(-|‐)[ ]?[0-9]{4}$$$,
  70, TRUE);

-- ── ENS 5.16 – TIE-IN POINTS ─────────────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5161', '5.16 TIE-IN POINTS',
  $$(JDA[ ]?(-|‐)[ ]?)?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)TP[ ]?(-|‐)[ ]?[0-9]{3}$$,
  $$^(JDA[ ]?(-|‐)[ ]?)?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)TP[ ]?(-|‐)[ ]?[0-9]{3}$$$,
  71, TRUE);

-- ── ENS 5.17 – SPECIAL PIPE SUPPORTS ────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5171', '5.17 SPECIAL PIPE SUPPORTS',
  $$(JDA[ ]?(-|‐)[ ]?)?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)SPS[ ]?(-|‐)[ ]?[0-9]{3}$$,
  $$^(JDA[ ]?(-|‐)[ ]?)?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)SPS[ ]?(-|‐)[ ]?[0-9]{3}$$$,
  72, TRUE);

-- ── ENS 5.18 – PROCESS INSTRUMENTATION ──────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5182', '5.18.2 PROCESS INSTRUMENTATION (PEFs & F&G)',
  $$(JDA[ ]?(-|‐)[ ]?)?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[A-Z]{2,4}[ ]?(-|‐)[ ]?[0-9]{5}[A-G]?(\/B)?(\/C)?(-[0-9])?$$,
  $$^(JDA[ ]?(-|‐)[ ]?)?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[A-Z]{2,4}[ ]?(-|‐)[ ]?[0-9]{5}[A-G]?(\/B)?(\/C)?(-[0-9])?$$$,
  73, TRUE);

-- ── ENS 5.19 – INSTRUMENTATION PANELS / JBs ─────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5191', '5.19.1 INSTRUMENTATION JUNCTION BOXES',
  $$JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?J(D|E|F|P|T|X)I?[ ]?(-|‐)[ ]?[0-9]{5}[A-Z]?(-[0-9]{2})?$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?J(D|E|F|P|T|X)I?[ ]?(-|‐)[ ]?[0-9]{5}[A-Z]?(-[0-9]{2})?$$$,
  74, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5193', '5.19.3 INSTRUMENTATION LOCAL PANELS',
  $$JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?LP[ ]?(-|‐)[ ]?[0-9]{5}$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?LP[ ]?(-|‐)[ ]?[0-9]{5}$$$,
  75, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5195', '5.19.5 INSTRUMENTATION CABINETS AND CONSOLES',
  $$JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?(ADAM|CAP|CMS|DHG|EMS|ESD|F&G|MET|PCS|PLC|PPS|RIG|SAN|SB|SMS|PMS-RIO)[ ]?(-|‐)[ ]?[0-9]{3}$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?(ADAM|CAP|CMS|DHG|EMS|ESD|F&G|MET|PCS|PLC|PPS|RIG|SAN|SB|SMS|PMS-RIO)[ ]?(-|‐)[ ]?[0-9]{3}$$$,
  76, TRUE);

-- ── ENS 5.20 – INSTRUMENT CABLES ────────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5201', '5.20.1a INSTRUMENT SINGLE CABLE (FIELD-PANEL)',
  $$JDA(-|‐)(PD|PA|C)(-|‐)(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[A-Z]{2,3}(-|‐)[0-9]{5}[A-Z]?\/(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(-|‐)(ADAM|CAP|CMS|DHG|EMS|ESD|F&G|MET|PCS|PLC|PPS|RIG|SAN|SB|SMS|PMS-RIO)(-|‐)[0-9]{3}$$,
  $$^JDA(-|‐)(PD|PA|C)(-|‐)(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[A-Z]{2,3}(-|‐)[0-9]{5}[A-Z]?\/(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(-|‐)(ADAM|CAP|CMS|DHG|EMS|ESD|F&G|MET|PCS|PLC|PPS|RIG|SAN|SB|SMS|PMS-RIO)(-|‐)[0-9]{3}$$$,
  77, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5220', '5.20.2 INSTRUMENT MULTICORE CABLE',
  $$JDA(-|‐)(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(-|‐)[A-Z]{2,3}(-|‐)[0-9]{3,5}(-[0-9]{2})?/(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(-|‐)(ADAM|CAP|CMS|DHG|EMS|ESD|F&G|MET|PCS|PLC|PPS|RIG|SAN|SB|SMS|PMS-RIO)(-|‐)[0-9]{3}$$,
  $$^JDA(-|‐)(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(-|‐)[A-Z]{2,3}(-|‐)[0-9]{3,5}(-[0-9]{2})?/(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)(-|‐)(ADAM|CAP|CMS|DHG|EMS|ESD|F&G|MET|PCS|PLC|PPS|RIG|SAN|SB|SMS|PMS-RIO)(-|‐)[0-9]{3}$$$,
  84, TRUE);

-- ── ENS 5.21 – TELECOMMUNICATIONS ──────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5211', '5.21a TELECOMMUNICATIONS DEVICE',
  $$JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?[0-9]{2}[ ]?(-|‐)[ ]?(TAD|TAH|TAM|TAN|TAP|TAR|TAS|TAT|TBA|TBC|TBG|TCE|TCL|TCK|TCM|TCO|TCP|TCR|TCT|TCV|TDC|TDF|TDH|TDL|TDO|TDR|TDT|TDU|TDX|TEL|TEP|TEX|TFE|TFL|TFO|TFS|TFT|TFX|TGP|THA|THC|THG|THP|THR|THS|THT|THU|THV|TIN|TIR|TIS|TIU|TJS|TKA|TKB|TLA|TLR|TLW|TMB|TMD|TMG|TMN|TMO|TMP|TMR|TMU|TMX|TNA|TNC|TNF|TNR|TNS|TOU|TPA|TPB|TPD|TPR|TPT|TPU|TRA|TRB|TRE|TRH|TRI|TRL|TRU|TRV|TSA|TSB|TSD|TSE|TSO|TSP|TSR|TST|TTE|TTM|TTR|TTS|TTV|TUP|TVA|TVP|TVR|TWG|TWS|TWT|TWV)[ ]?(-|‐)[ ]?[0-9]{3}$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?[0-9]{2}[ ]?(-|‐)[ ]?(TAD|TAH|TAM|TAN|TAP|TAR|TAS|TAT|TBA|TBC|TBG|TCE|TCL|TCK|TCM|TCO|TCP|TCR|TCT|TCV|TDC|TDF|TDH|TDL|TDO|TDR|TDT|TDU|TDX|TEL|TEP|TEX|TFE|TFL|TFO|TFS|TFT|TFX|TGP|THA|THC|THG|THP|THR|THS|THT|THU|THV|TIN|TIR|TIS|TIU|TJS|TKA|TKB|TLA|TLR|TLW|TMB|TMD|TMG|TMN|TMO|TMP|TMR|TMU|TMX|TNA|TNC|TNF|TNR|TNS|TOU|TPA|TPB|TPD|TPR|TPT|TPU|TRA|TRB|TRE|TRH|TRI|TRL|TRU|TRV|TSA|TSB|TSD|TSE|TSO|TSP|TSR|TST|TTE|TTM|TTR|TTS|TTV|TUP|TVA|TVP|TVR|TWG|TWS|TWT|TWV)[ ]?(-|‐)[ ]?[0-9]{3}$$$,
  80, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5212', '5.21b TELECOMMUNICATIONS CABLE',
  $$JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?[0-9]{2}[ ]?(-|‐)[ ]?(TCA)[ ]?(-|‐)[ ]?[0-9]{3}$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?[0-9]{2}[ ]?(-|‐)[ ]?(TCA)[ ]?(-|‐)[ ]?[0-9]{3}$$$,
  81, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5213', '5.21c TELECOMMUNICATIONS JUNCTION BOX',
  $$JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?[0-9]{2}[ ]?(-|‐)[ ]?(TJB)[ ]?(-|‐)[ ]?[0-9]{3}$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?[0-9]{2}[ ]?(-|‐)[ ]?(TJB)[ ]?(-|‐)[ ]?[0-9]{3}$$$,
  82, TRUE);

INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5214', '5.21d TELECOMMUNICATIONS CABINET & PANELS',
  $$JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?[0-9]{2}[ ]?(-|‐)[ ]?(TCB|TPP|TRT)[ ]?(-|‐)[ ]?[0-9]{3}$$,
  $$^JDA[ ]?(-|‐)[ ]?(01|02|29|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[ ]?(-|‐)[ ]?[0-9]{2}[ ]?(-|‐)[ ]?(TCB|TPP|TRT)[ ]?(-|‐)[ ]?[0-9]{3}$$$,
  83, TRUE);

-- ── ENS 5.22 – SUB-SEA EQUIPMENT ────────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-5221', '5.22 SUB-SEA EQUIPMENT',
  $$JDA[ ]?(-|‐)[ ]?(EDM|FWC|HYD|ICS|IST|JAR|JAS|JAT|MBD|MFD|MTR|PBA|QAY|ROV|SCP|SLD|UTA|WCS|WTH|XTS)[ ]?(-|‐)[ ]?[0-9]{2}[0-9]?[0-9]{3}$$,
  $$^JDA[ ]?(-|‐)[ ]?(EDM|FWC|HYD|ICS|IST|JAR|JAS|JAT|MBD|MFD|MTR|PBA|QAY|ROV|SCP|SLD|UTA|WCS|WTH|XTS)[ ]?(-|‐)[ ]?[0-9]{2}[0-9]?[0-9]{3}$$$,
  85, TRUE);

-- ── ENS 7.x – INTERFACE CABLES ───────────────────────────────────────────
INSERT INTO audit_core.naming_rule (domain, source_code, description, regex_search, regex_full, sort_order, is_active)
VALUES ('TAG', 'NR-7001', '7.0.1 INTERFACE CABLE (MAIN ELEC-MAIN ELEC)',
  $$JDA(-|‐)(H|PM|EM|XM|KM|TH|XH|ES|HE|CP|VS)(-|‐)(01|02|08|29|35|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[A-Z]?(-[0-9]{1,2})?\/( H|PM|EM|XM|KM|TH|XH|ES|HE|CP|VS)(-|‐)(01|02|08|29|35|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[A-Z]?(-[0-9]{1,2})?$$,
  $$^JDA(-|‐)(H|PM|EM|XM|KM|TH|XH|ES|HE|CP|VS)(-|‐)(01|02|08|29|35|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[A-Z]?(-[0-9]{1,2})?\/(H|PM|EM|XM|KM|TH|XH|ES|HE|CP|VS)(-|‐)(01|02|08|29|35|46|47|51|54|55|56|57|59|61|62|63|65|67|68|69|72|73|74|75|79|83|84|85|86)[0-9]{3}[A-Z]?(-[0-9]{1,2})?$$$,
  90, TRUE);

COMMIT;

-- Verify:
-- SELECT source_code, description, sort_order
-- FROM audit_core.naming_rule
-- WHERE domain = 'TAG'
-- ORDER BY sort_order;
-- Expected: 27 rows
