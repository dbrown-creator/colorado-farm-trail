# Local food & farm events

Seasonal events that celebrate Colorado food and farming. The first batch is the seven
events on the Roaring Fork + Farm Map (carbondale.com/roaring-fork-farm-map), researched
2026-10-04. The local food guide reads this file.

**`events.csv`**: one row per event.

| Column | Meaning |
|---|---|
| `Kind` | `farm` (on a farm, or farm-raised food is the point), `food` (culinary festival), `ranch` (rodeo and ranch culture), `community` (a town festival or market with local food in it) |
| `Region` | Same region names as the food guide (`Roaring Fork`, `Western Slope`, …) |
| `Season` | Typical time of year, in words. Always filled in, so an event still shows when its dates aren't out yet |
| `Start`, `End` | ISO dates of the next or most recent run, when published. A weekly series uses its first and last dates |
| `Recurrence` | How it repeats, plus past dates when the next ones aren't published |
| `Status` | `scheduled`, `dates-pending` (recurring, next dates not yet published), `canceled` (this year's run) |
| `Host` | Business name when a listed farm or business runs it (matches `source-data/supply-network/nodes.csv` or the map) |
| `Source URLs` | Where the details come from, `;`-separated |

As with businesses, a cell is filled in only when a source states it. Re-check the dates
every spring: most organizers publish summer dates in March–May.
