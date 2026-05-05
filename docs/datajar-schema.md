# Data Jar Schema - Complete Data Dictionary

Generated: 2026-04-26
Source: `/tmp/datajar-backup/store.json` (29 MB)
Total top-level datasets: 40

---

## Table of Contents

1. [LifeTrackerLog](#1-lifetrackerlog)
2. [clipboard to text](#2-clipboard-to-text)
3. [BookmarkRecords](#3-bookmarkrecords)
4. [dailyjournal](#4-dailyjournal)
5. [driving_records](#5-driving_records)
6. [Historical Milage](#6-historical-milage)
7. [IoniqCarLogger](#7-ioniqcarlogger)
8. [FitnessRecords](#8-fitnessrecords)
9. [health](#9-health)
10. [Locations Parked](#10-locations-parked)
11. [habit tracker](#11-habit-tracker)
12. [morning life](#12-morning-life)
13. [api keys](#13-api-keys)
14. [foresterOdo](#14-foresterodo)
15. [Cross-Dataset Analysis](#cross-dataset-analysis)
16. [All Datasets Summary](#all-datasets-summary)

---

## Data Jar Value Format

Every value in Data Jar follows a nested wrapper pattern:

```json
{
  "value": {
    "type": "dictionary",
    "value": {
      "field_name": {
        "value": { "type": "string", "value": "actual_value" },
        "modifiedAt": 123456.789,
        "createdAt": 123456.789,
        "order": 0,
        "identifier": "UUID"
      }
    }
  },
  "modifiedAt": ...,
  "createdAt": ...,
  "order": ...,
  "identifier": "..."
}
```

Supported types: `string`, `number`, `boolean`, `dictionary`, `array`, `data` (binary).

---

## 1. LifeTrackerLog

| Property | Value |
|----------|-------|
| Type | array |
| Record count | 8,309 |
| Date range | Jun 24, 2025 -- Apr 26, 2026 (~10 months) |
| Date format | `M/D/YY` (Date field) + `HH:MM` or `H:MM AM/PM` (Time field) |

### Entry Type Breakdown

| Entry | Count | % |
|-------|-------|---|
| Charger Plugged In | 3,053 | 36.7% |
| Charger Unplugged | 3,015 | 36.3% |
| Initiate Driving | 1,124 | 13.5% |
| End Driving | 1,001 | 12.0% |
| IONIQ 6 Key Entry | 13 | 0.2% |
| Bedtime | 9 | 0.1% |
| Free-text journal entries | ~94 | 1.1% |

### Fields

| Field | Type | Present | Quality Issues | Example |
|-------|------|---------|----------------|---------|
| `Date` | string | 8,309/8,309 | Date format inconsistent: some `M/D/YY`, some with AM/PM suffix | `4/26/26` |
| `Time` | string | 8,309/8,309 | Mixed formats: `20:30` (24h) vs `1:40 AM` (12h) | `20:30`, `6:21 PM` |
| `Entry` | string | 8,309/8,309 | Some entries are free-text journal blobs, not event labels | `End Driving` |
| `Location` | string | 8,309/8,309 | 7 empties; multi-line address format | `3005 Oakwood St\nAnn Arbor MI 48104\nUnited States` |
| `Device_Battery` | string | 8,309/8,309 | Numeric stored as string | `92` |
| `Device_Type` | string | 8,309/8,309 | -- | `iPhone` |
| `Temperature` | string | 8,309/8,309 | Includes unit suffix | `57F` |
| `Weather_Condition` | string | 8,309/8,309 | Duplicates Temperature + adds condition | `57F and Clear` |
| `Focus_Mode` | string | 8,309/8,309 | 3,109 empties (37.4%) | `Traveling`, `Do Not Disturb`, `Sleep`, `Work` |
| `HRV` | string | 2,763/8,309 | 5,546 missing, 2,228 empties; numeric as string; float precision | `11.19442337085995` |
| `Steps` | string | 2,763/8,309 | 5,546 missing, 37 empties; numeric as string | `3451` |
| `Elevation` | string | 26/8,309 | 8,283 missing; includes unit | `248.669 m` |
| `Car_Mileage` | int | 1/8,309 | 8,308 missing; only 1 record has this | `38259` |

### Schema Variations

- **Core fields** (Date, Time, Entry, Location, Device_Battery, Device_Type, Temperature, Weather_Condition, Focus_Mode): present in all 8,309 records.
- **Health fields** (HRV, Steps): present in 2,763 records (33.3%) -- added later in the shortcut's evolution.
- **Elevation**: very sparse, only 26 records.
- **Car_Mileage**: effectively unused (1 record).
- **Free-text entries**: ~94 records where `Entry` contains journal text instead of an event label. These are long-form notes mixed in with structured events.

### Data Quality Issues

- Time format inconsistency: 24-hour (`20:30`) vs 12-hour with AM/PM (`1:40 AM`).
- Numeric values stored as strings (Device_Battery, HRV, Steps).
- Weather_Condition is redundant with Temperature (always includes the temperature value).
- Focus_Mode has a 37.4% empty rate -- charging events often lack focus mode.

---

## 2. clipboard to text

| Property | Value |
|----------|-------|
| Type | array |
| Record count | 3,791 |
| Date range | May 7, 2025 -- Apr 24, 2026 (~12 months) |
| Date format | `MMM D, YYYY at HH:MM` or `MMM D, YYYY at H:MM AM/PM` |

### Two Schema Versions

**Schema v2 (older, 2,886 records)** -- flat fields:

| Field | Type | Present | Quality Issues | Example |
|-------|------|---------|----------------|---------|
| `datetime` | string | 2,886/2,886 | -- | `Apr 24, 2026 at 17:20` |
| `char count` | int | 2,886/2,886 | -- | `1042` |
| `word count` | int | 2,886/2,886 | -- | `134` |
| `speech length` | string | 2,886/2,886 | Numeric as string; appears to be a negative float (duration?) | `-41.968211` |
| `current focus` | string | 2,886/2,886 | 1,835 empties | `Traveling`, `Sleep` |
| `location` | string | 2,886/2,886 | Multi-line address | `3107-3125 Fort St\nLincoln Park MI 48146\nUnited States` |
| `weather` | string | 2,886/2,886 | -- | `69F and Rain` |
| `steps` | string | 2,886/2,886 | 109 empties; numeric as string | `466` |
| `heart_rate` | string | 2,886/2,886 | 2,454 empties (85%!) | -- |
| `hrv` | string | 2,886/2,886 | 2,196 empties (76%) | -- |
| `env_decibles` | string | 2,886/2,886 | 2,466 empties (85%) | -- |
| `` (empty key) | string | 2,886/2,886 | All empty; artifact/bug | `""` |

**Schema v1 (newer, 905 records)** -- nested health dict:

| Field | Type | Present | Quality Issues | Example |
|-------|------|---------|----------------|---------|
| `datetime` | string | 905/905 | -- | `Apr 24, 2026 at 17:20` |
| `char count` | int | 905/905 | -- | `488` |
| `word count` | int | 905/905 | -- | `59` |
| `speech length` | string | 905/905 | -- | `-11.61273` |
| `current focus` | string | 905/905 | Empties present | `Traveling` |
| `current app` | string | 905/905 | 26 empties | `Claude`, `Safari` |
| `health` | dict | 905/905 | Nested health data | See below |

**Schema v1 `health` sub-fields:**

| Field | Type | Example |
|-------|------|---------|
| `getHR` | string | `73` |
| `getStep` | int | `1064` |
| `getHRV` | string | `20.38` |
| `getDecibel` | float | `43.89` |

### Schema Variations

- v2 has flat health fields (heart_rate, hrv, steps, env_decibles) with massive empty rates.
- v1 consolidated health into a nested dict and added `current app`; dropped `location` and `weather`.
- v1 dropped the empty-key bug field.

### Data Quality Issues

- Empty string key `""` in v2 schema (all values empty).
- `speech length` appears to be a negative float -- unclear semantics (possibly an API artifact from speech-to-text duration).
- Heart rate, HRV, and decibel data are >75% empty in v2.
- v1 loses location and weather data -- those fields were dropped in the schema migration.

---

## 3. BookmarkRecords

| Property | Value |
|----------|-------|
| Type | array |
| Record count | 410 |
| Date range | Apr 13, 2023 -- Sep 5, 2025 (~2.5 years) |
| Date format | `MMM D, YYYY` (date) + `HH:MM` (time) |

### Fields

| Field | Type | Present | Quality Issues | Example |
|-------|------|---------|----------------|---------|
| `date` | string | 410/410 | -- | `Apr 2, 2026` |
| `time` | string | 410/410 | -- | `20:41` |
| `author` | string | 410/410 | -- | `David Foster Wallace` |
| `book_title` | string | 399/410 | 11 missing | `Infinite Jest` |
| `highlights` | string | 385/410 | 25 missing, 10 empties | Long quoted text |
| `location` | string | 381/410 | 29 missing; often just `Home` | `Home` |
| `progress` | int | 159/410 | 251 missing | `1` |
| `notes` | string/null | 24/410 | 386 missing, 1 null | Personal annotations |
| `highlight` | string | 8/410 | 402 missing; legacy/duplicate of `highlights` | Same content as highlights |
| `tags` | string/null | 5/410 | 405 missing, 1 null, 1 empty | `Science`, `ADHD` |

### Schema Variations

- `highlight` (singular) appears in only 8 records -- likely an early version of the field before it was renamed to `highlights` (plural).
- `progress`, `notes`, `tags` are sparsely populated -- optional fields that were rarely used.
- `book_title` missing in 11 records.

### Data Quality Issues

- Two highlight fields (`highlight` and `highlights`) with slight overlap.
- `progress` is always `1` where present -- unclear if this means "100%" or "bookmark count".
- `tags` almost never used (5/410).

---

## 4. dailyjournal

| Property | Value |
|----------|-------|
| Type | array |
| Record count | 729 |
| Date range | May 1, 2025 -- Apr 2, 2026 (~11 months) |
| Date format | `MMM D, YYYY at HH:MM` |

### Fields

| Field | Type | Present | Quality Issues | Example |
|-------|------|---------|----------------|---------|
| `datetime` | string | 729/729 | -- | `Apr 2, 2026 at 20:41` |
| `entry` | string | 729/729 | Contains embedded structured data (see below) | Mixed formats |

### Entry Content Types

| Type | Count | Description |
|------|-------|-------------|
| Bookmark entries | 669 (91.8%) | Start with `{Entry: {"date":...,"book_title":...` -- serialized BookmarkRecords |
| Structured journal | ~47 | Start with `{Entry: ...` with location/weather/steps metadata |
| Free-text journal | ~12 | Plain text voice transcriptions and personal notes |
| Voice journal | 1 | Explicitly tagged as voice |

### Schema Variations

- Bookmark entries embed a JSON object inside the `entry` string field (not parsed, just serialized).
- Non-bookmark entries use a pseudo-structured format: `{Entry: ..., Time: ..., Location: ..., Weather: ..., Steps: ..., HRV: ...}`.
- Some entries are raw voice memo transcriptions.

### Data Quality Issues

- The `entry` field mixes structured data (bookmark JSON, metadata blocks) with free-text -- parsing requires format detection.
- Bookmark entries in dailyjournal overlap heavily with BookmarkRecords (669 vs 410 -- dailyjournal has MORE bookmark entries).
- `dailyjournal_cleaned` exists but has 0 records.

---

## 5. driving_records

| Property | Value |
|----------|-------|
| Type | array |
| Record count | 148 |
| Date range | Oct 6, 2023 -- Jul 20, 2024 (~9 months) |
| Date format | `MMM D, YYYY at H:MM AM/PM` |

### Fields

| Field | Type | Present | Quality Issues | Example |
|-------|------|---------|----------------|---------|
| `create_ts` | string | 148/148 | Contains narrow no-break space before AM/PM | `Jul 20, 2024 at 3:12 PM` |
| `record_name` | string | 148/148 | Prefixed with `CarChat_shell-` | `CarChat_shell-Jul 20, 2024 at 3:12 PM` |
| `location` | string | 148/148 | Multi-line address | `3901 Jackson Rd\nAnn Arbor MI 48103\nUnited States` |
| `phone_battery` | string | 148/148 | Numeric as string | `73` |
| `weather` | string | 148/148 | -- | `79F and Cloudy` |
| `historical_milea` | string | 148/148 | Embedded timestamp + mileage; typo in field name | `7/20/24, 3:11 PM, 63999` |

### Data Quality Issues

- `historical_milea` is a compound field (timestamp + odometer in one string) -- needs parsing.
- Field name typo: `historical_milea` should be `historical_mileage`.
- `record_name` encodes the timestamp redundantly with `create_ts`.
- Unicode narrow no-break space (U+202F) in timestamps.
- This dataset stopped in Jul 2024 -- superseded by LifeTrackerLog driving entries.

---

## 6. Historical Milage

| Property | Value |
|----------|-------|
| Type | array |
| Record count | 410 |
| Date range | Feb 18, 2023 -- Apr 26, 2026 (~3 years) |
| Format | Flat strings, not dictionaries |

### Format

Records are **plain strings**, not dictionaries:

```
M/D/YY, HH:MM, MILEAGE
```

Examples:
- `4/26/26, 20:23, 69625`
- `3/1/25, 12:41 AM, 69378`
- `2/18/23, 13:26, 39619`

### Data Quality Issues

- Not structured data -- each record is a comma-separated string that needs parsing.
- Unicode narrow no-break space in some timestamps.
- Mileage values span from ~39,619 to ~69,625 (Subaru Forester, later Hyundai Ioniq 6).

---

## 7. IoniqCarLogger

| Property | Value |
|----------|-------|
| Type | array |
| Record count | 3 |
| Date range | Jul 27, 2024 (single day) |

### Fields

| Field | Type | Present | Example |
|-------|------|---------|---------|
| `action` | string | 3/3 | `engine_start` |
| `datetime` | string | 3/3 | `Jul 27, 2024 at 4:04 AM` |

### Notes

- Only 3 records, all from the same day -- this was likely a test/prototype.
- Related: **IoniqActivationLog** has 4 records from the same day (`7/27/24`), with only a `date` field.
- Both datasets appear to be abandoned prototypes for car event logging, superseded by LifeTrackerLog.

---

## 8. FitnessRecords

| Property | Value |
|----------|-------|
| Type | array |
| Record count | 3 |
| Date range | Feb 15, 2023 (single day) |
| Format | Flat strings, not dictionaries |

### Format

Records are **plain strings** with embedded structured data:

```
* Date: 2/15/23, 19:49, Weather Condition: 43F and Partly Cloudy
* Active Calories:
* Distance Traveled: 0.02 Miles
```

### Notes

- Only 3 records, all from the same day -- abandoned prototype.
- Active Calories field is empty in all records.
- Health/fitness tracking moved to LifeTrackerLog (HRV, Steps fields).

---

## 9. health

| Property | Value |
|----------|-------|
| Type | dictionary |
| Sub-datasets | 2 |

### Sub-dataset: orgasm_tracker

| Property | Value |
|----------|-------|
| Record count | 3 |
| Date range | Nov 19, 2025 (single entry with date visible) |

**Fields:**

| Field | Type | Example |
|-------|------|---------|
| `health_sample` | string | `orgasm_tracker` |
| `datetime` | string | `11/19/25, 10:55 PM` |

### Sub-dataset: sex_tracker

| Property | Value |
|----------|-------|
| Record count | 1 |
| Date | Oct 30, 2023 |

**Fields:**

| Field | Type | Example |
|-------|------|---------|
| `health_sample` | string | `sexual_activity` |
| `datetime` | string | `Oct 30, 2023 at 10:32 PM` |
| `solo` | boolean | `true` |

### Related: organism_tracker (top-level)

| Property | Value |
|----------|-------|
| Record count | 20 |
| Date range | Jan 24, 2026 -- Jan 26, 2026 (3 days) |

**Fields:**

| Field | Type | Example |
|-------|------|---------|
| `time` | string | `Jan 26, 2026 at 02:24` |
| `didYou?` | boolean | `true` |

### Notes

- Three separate datasets track overlapping sexual health data: `health.orgasm_tracker`, `health.sex_tracker`, and `organism_tracker`.
- All have very low record counts (1-20).
- `organism_tracker` appears to be the most recent/active version.

---

## 10. Locations Parked

| Property | Value |
|----------|-------|
| Type | array |
| Record count | 1 |
| Format | Flat string |

### Format

Single record: `10/26/23, 2:25 AM, 2551 Country Village Ct\nAnn Arbor MI 48103\nUnited States`

### Notes

- Effectively unused -- only 1 record.
- Parking location tracking moved to LifeTrackerLog (Location field on driving events).

---

## 11. habit tracker

| Property | Value |
|----------|-------|
| Type | array |
| Record count | 1 |
| Date | Aug 20, 2023 |

### Fields

| Field | Type | Example |
|-------|------|---------|
| `date` | string | `Aug 20, 2023 at 2:39 AM` |
| `habit_name` | string | `guitar` |
| `num_of_mins` | int | `30` |
| `comment` | string | `Did a little work on learning the A Chore and the E chore...` |

### Notes

- Only 1 record -- abandoned after initial test.

---

## 12. morning life

| Property | Value |
|----------|-------|
| Type | array |
| Record count | 1 |

### Fields

| Field | Type | Value |
|-------|------|-------|
| `morning message` | null | `null` |
| `time added` | null | `null` |

### Notes

- Single record with all null values -- never used.

---

## 13. api keys

| Property | Value |
|----------|-------|
| Type | dictionary |
| Key count | 5 |

### Stored Keys

| Key Name | Type |
|----------|------|
| `PLEX` | string |
| `GPT` | string |
| `babel` | string |
| `finviz` | string |
| `claude` | string |

Values redacted.

---

## 14. foresterOdo

| Property | Value |
|----------|-------|
| Type | dictionary |
| Keys | 2 |

### Structure

```json
{
  "data": {
    "vehicleMileageDate": "2026-04-27T00:23:35.136+00:00",
    "vehicleMileage": 69625,
    "isServiceDue": false,
    "nextServiceMileage": "72,000 Miles / 72 Month Service"
  },
  "success": true
}
```

### Notes

- Despite the name "foresterOdo" (Subaru Forester), the current data reflects the Hyundai Ioniq 6 (69,625 miles matches Historical Milage latest entry).
- `vehicleMileageDate` is ISO 8601 -- the only dataset using this format.
- This appears to be a live API response cache from the Hyundai/Subaru connected vehicle API.

---

## Cross-Dataset Analysis

### Datasets with Location Data (Globe Visualization Candidates)

| Dataset | Location Field | Format | Records with Location |
|---------|---------------|--------|----------------------|
| **LifeTrackerLog** | `Location` | Multi-line US address | 8,302 (7 empty) |
| **clipboard to text** (v2) | `location` | Multi-line US address | 2,886 |
| **BookmarkRecords** | `location` | Usually `Home` or place name | 381 |
| **driving_records** | `location` | Multi-line US address | 148 |
| **Locations Parked** | (flat string) | Embedded address | 1 |
| **Historical Milage** | none | -- | 0 |

**Note:** All location data is street-address format (not lat/lon). Geocoding required for globe visualization.

### Datasets with Timeline-Compatible Timestamps

| Dataset | Date Field(s) | Format | Count |
|---------|--------------|--------|-------|
| **LifeTrackerLog** | `Date` + `Time` | `M/D/YY` + `HH:MM` / `H:MM AM/PM` | 8,309 |
| **clipboard to text** | `datetime` | `MMM D, YYYY at HH:MM` | 3,791 |
| **dailyjournal** | `datetime` | `MMM D, YYYY at HH:MM` | 729 |
| **BookmarkRecords** | `date` + `time` | `MMM D, YYYY` + `HH:MM` | 410 |
| **Historical Milage** | (embedded) | `M/D/YY, HH:MM` | 410 |
| **driving_records** | `create_ts` | `MMM D, YYYY at H:MM AM/PM` | 148 |
| **organism_tracker** | `time` | `MMM D, YYYY at HH:MM` | 20 |
| **IoniqCarLogger** | `datetime` | `MMM D, YYYY at H:MM AM/PM` | 3 |
| **health** | `datetime` | Mixed formats | 4 |
| **habit tracker** | `date` | `MMM D, YYYY at H:MM AM/PM` | 1 |

**Date format inconsistency across datasets** -- at least 4 distinct datetime formats in use.

### Datasets with Health/Biometric Data

| Dataset | Health Fields | Records |
|---------|-------------|---------|
| **LifeTrackerLog** | HRV, Steps | 2,763 |
| **clipboard to text** (v2) | heart_rate, hrv, steps, env_decibles | 2,886 (mostly empty) |
| **clipboard to text** (v1) | health.getHR, health.getStep, health.getHRV, health.getDecibel | 905 |
| **health** | orgasm_tracker, sex_tracker | 4 |
| **organism_tracker** | didYou? | 20 |
| **FitnessRecords** | Active Calories, Distance | 3 (abandoned) |
| **habit tracker** | num_of_mins | 1 (abandoned) |

### Overlapping / Duplicate Datasets

| Overlap | Details |
|---------|---------|
| **dailyjournal vs BookmarkRecords** | dailyjournal contains 669 serialized bookmark entries; BookmarkRecords has 410. dailyjournal is a superset that also includes non-bookmark journal entries. |
| **driving_records vs LifeTrackerLog** | driving_records covers Oct 2023 -- Jul 2024 (148 records). LifeTrackerLog covers Jun 2025+ with Initiate Driving / End Driving entries (2,125 records). No date overlap -- driving_records is the predecessor. |
| **Historical Milage vs driving_records** | driving_records.historical_milea embeds the same data as Historical Milage entries. |
| **Historical Milage vs foresterOdo** | foresterOdo.data.vehicleMileage matches the latest Historical Milage entry (69,625). foresterOdo is a live API snapshot; Historical Milage is the historical log. |
| **IoniqCarLogger vs IoniqActivationLog** | Both from Jul 27, 2024 with 3-4 records. IoniqCarLogger has action+datetime; IoniqActivationLog has only date. Both abandoned. |
| **health vs organism_tracker** | Three overlapping trackers for sexual health data across two datasets. |
| **clipboard to text v1 vs v2** | Same dataset, two schema versions. v1 (905 records) has nested health dict + current app. v2 (2,886 records) has flat fields + location/weather. |

### Dataset Evolution Timeline

```
2023-02  FitnessRecords (abandoned)
2023-02  Historical Milage (ongoing -> 2026)
2023-04  BookmarkRecords (ongoing -> 2025-09)
2023-08  habit tracker (abandoned)
2023-10  driving_records (Oct 2023 -> Jul 2024, then replaced)
2023-10  health.sex_tracker (1 record)
2023-10  Locations Parked (abandoned)
2024-07  IoniqCarLogger / IoniqActivationLog (abandoned prototypes)
2025-05  dailyjournal (ongoing -> 2026-04, absorbed BookmarkRecords)
2025-05  clipboard to text (ongoing -> 2026-04)
2025-06  LifeTrackerLog (ongoing -> 2026-04, absorbed driving + charging + health)
2025-11  health.orgasm_tracker (3 records)
2026-01  organism_tracker (20 records)
```

---

## All Datasets Summary

| Dataset | Type | Count | Status |
|---------|------|-------|--------|
| LifeTrackerLog | array | 8,309 | **Active** -- primary life event log |
| clipboard to text | array | 3,791 | **Active** -- clipboard capture with metadata |
| dailyjournal | array | 729 | **Active** -- combined bookmark + journal log |
| BookmarkRecords | array | 410 | Likely superseded by dailyjournal |
| Historical Milage | array | 410 | **Active** -- odometer snapshots |
| driving_records | array | 148 | Superseded by LifeTrackerLog |
| temp | array | 100 | Scratch/temporary |
| list of dumb jokes aboot powrr | array | 43 | Novelty |
| serendipity | array | 30 | Unknown purpose |
| organism_tracker | array | 20 | **Active** -- sexual health tracking |
| TodaysEntries | array | 16 | Scratch/daily buffer |
| reddit_counter | array | 13 | Social media usage tracking |
| Shopping List | array | 8 | Shopping list |
| allCaptiansLogEntries | array | 6 | Captain's log entries |
| api keys | dictionary | 5 | API key store (PLEX, GPT, babel, finviz, claude) |
| IoniqActivationLog | array | 4 | Abandoned car logger prototype |
| ask Assistant Later | array | 4 | Deferred questions |
| health | dictionary | 2 sub | Sexual health (orgasm_tracker: 3, sex_tracker: 1) |
| IoniqCarLogger | array | 3 | Abandoned car logger prototype |
| FitnessRecords | array | 3 | Abandoned fitness prototype |
| babel semantic temp | dictionary | 3 | Babel Palace temp data |
| babel temp | dictionary | 3 | Babel Palace temp data |
| foresterOdo | dictionary | 2 | Live vehicle API cache |
| shortcut logging | array | 2 | Shortcut debug logs |
| photography | dictionary | 1 | Unknown |
| habit tracker | array | 1 | Abandoned |
| morning life | array | 1 | Abandoned (null values) |
| Locations Parked | array | 1 | Abandoned |
| logger | array | 1 | Test |
| ai memory | array | 1 | AI context store |
| book-temp | array | 1 | Temp |
| temp_books | array | 1 | Temp |
| threads_saver | array | 1 | Threads social media |
| YearOfReading | array | 1 | Reading tracker |
| current physical book | string | 1 | Current reading state |
| current physical author | string | 1 | Current reading state |
| voice memo highlight bool | string | 1 | Flag |
| tempbook | dictionary | 1 | Temp |
| dailyjournal_cleaned | array | 0 | Empty |
| lsibbsoaosh_occurance | array | 0 | Empty |

---

## Dashboard Integration Recommendations

### High-Value Datasets for Dashboard

1. **LifeTrackerLog** (8,309 records) -- driving patterns, charging cycles, sleep/wake via charger plug/unplug, weather, location movement.
2. **clipboard to text** (3,791 records) -- digital activity patterns, app usage (v1), reading/writing metrics.
3. **Historical Milage** (410 records) -- vehicle mileage over 3+ years, calculate driving distance per period.
4. **dailyjournal** (729 records) -- reading highlights timeline, personal journal entries.
5. **BookmarkRecords** (410 records) -- reading history with books, authors, highlights.

### Parsing Requirements

1. **Address geocoding** -- all location data is street addresses; need geocoding API for lat/lon coordinates for globe visualization.
2. **Date normalization** -- at least 4 datetime formats across datasets; need a unified parser.
3. **String-to-number casting** -- Device_Battery, Steps, HRV, heart_rate, phone_battery all stored as strings.
4. **Compound field splitting** -- Historical Milage strings and driving_records.historical_milea need comma-split parsing.
5. **Embedded JSON extraction** -- dailyjournal.entry contains serialized JSON that needs secondary parsing.
6. **Schema version detection** -- clipboard to text has two schemas that need version-aware parsing.
