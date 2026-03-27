# VDAB API Audit: "Butcher" Job Request Analysis
Date: 2026-03-27

## Overview
Analysis of the VDAB API responses for the job "butcher" identified two primary issues: a **search mismatch** and a **content filtration issue** that causes the app to display empty results.

---

## 1. Search Mismatch (VDAB API Oddity)
When the app searches for "butcher" (English) using the Dutch language parameter (`language="nl"`), the VDAB API fails to return the correct profile for "Slager" (Butcher). Instead, it returns:

**Unexpected Profile Result:**
- **Job Title**: "Huishoudhulp-poetshulp" (Domestic helper/cleaner)
- **Profile ID**: `c975483a-b03f-47a3-9c0a-c773babb1510`
- **ISCO Codes**: 5152 (Domestic housekeepers), 9111 (Domestic cleaners)

**Correct Profile (Retrieved via "slager"):**
- **Job Title**: "Slager" (Butcher)
- **Profile ID**: `07f701ec-57c9-40dd-97d9-e9238062db1e`
- **ISCO Code**: 7511 (Butchers, fishmongers and related food preparers)

---

## 2. The Content Filtration Bug (App Logic)
The most critical issue is how the app fetches details for identified profiles in `vdab_api_service.py` within the `get_skills` method.

### Root Cause: Hard API Filtration
The `get_skills` method passes `params={"lang": lang}` (default: `"en"`) to the detail endpoint. The VDAB API responds by filtering the response and setting **ALL** language fields to `null` if no English translation exists.

### Test Results on Butcher Profile (ID: `07f701ec...`)
| API Parameter (`lang`) | Title Field in JSON Response | Effect on App |
| :--- | :--- | :--- |
| **`lang="en"`** | `{'nl': null, 'fr': null, 'en': null}` | **FAILURE**: `_extract_mls` finds nothing, section is empty. |
| **`lang=None`** | `{'nl': 'Slager', 'fr': 'Boucher', 'en': null}` | **SUCCESS**: App falls back to Dutch/French correctly. |
| **`lang="nl"`** | `{'nl': 'Slager', 'fr': null, 'en': null}` | **PARTIAL**: Only Dutch content is available. |

---

## 3. Impact Summary
Because the app explicitly requests English from the API, and many profiles (including "Butcher") lack English translations in the VDAB database, the VDAB API hides the available Dutch and French descriptions. The app's `_extract_mls` function then receives `None` for all candidates, resulting in an empty UI experience for the user.

## Recommendations
1. **Remove API-side Filtration**: In `vdab_api_service.py:get_skills`, stop passing the `lang` parameter to the `releases/.../occupationalprofiles/{profile_id}` request. This ensures all available translations are received.
2. **Handle English Searches**: If possible, translate English job titles (e.g. via a small dictionary or LLM) to Dutch before querying the `/search` endpoint to improve match accuracy.
