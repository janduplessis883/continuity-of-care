# Continuity of care

A Streamlit dashboard for counting appointments and distinct clinicians per patient from a SystmOne CSV export.

## Run

From this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501. Select **Explore with demo data** to try synthetic appointments, or upload a CSV.

## CSV format

Select the correct NHS number and clinician columns in **Match your columns**. Age and appointment date are optional. Appointment date can be matched to any CSV column; it does not filter or change the appointment counts. Headers are automatically matched where recognised. Headerless files are supported by clearing **CSV has a header row**.

For seven-column files the fallback order is: age, DOB, NHS number, surname, appointment date, clinician, patient count. Always verify the column mapping. DOB, surname, and patient count are not used in the calculation.

Each row counts as an appointment, including duplicates. Blank patient IDs are excluded and reported. Blank clinician names count toward appointments but not distinct clinicians. Whitespace is removed from NHS numbers; names are trimmed but otherwise kept exactly as supplied. Age uses the maximum numeric value for each patient.

The sidebar can restrict the cohort by minimum appointments and exact number of distinct clinicians. Both downloads use that cohort. Patient summary and clinician frequency downloads contain original NHS numbers even when the table hides them.

Uploads are processed in memory without application caching, disk persistence, or external API calls. A hosted deployment receives the uploaded data on its server. Bindings default to localhost; configure an appropriate access-controlled environment before any remote deployment with patient data.

## Verify

```sh
python -m unittest discover -s tests
```

Tests cover counts, missing values, identifier preservation, the demo dashboard, and empty filter results.

## Audit output

The **Audit output** tab exports the named columns in the supplied continuity audit template, in their original order (omitting its empty leading column). References are sequential and patient identifiers are populated from NHS numbers. Total contacts use all uploaded appointments; supply an export covering the last 12 months. Named practice team is set to Yes for all patients. Named-team size uses the slider percentage (10–100% in 5% steps, default 25%) of unique clinicians in the full upload, rounded up (minimum one): 10 clinicians gives a team size of 3; 3 gives 1. Named-team contacts sum that many highest clinician counts for each patient, or all available counts if fewer are present. Cohort filters do not change team size. Blank clinicians are excluded from named-team counts. The mapped appointment date currently does not apply a date filter.

Care plans, Universal Care Plans, MDT review, admissions, discharge follow-up, medication reviews and continuity actions remain blank until supporting data is available. Blank does not mean No. The template's example patient records are not bundled with the app.

## Additional audit uploads

The sidebar provides optional CSV uploads for MDT, Care Plan, and Medication Reviews. These accept headered CSVs and show row counts and column names. They do not yet populate audit fields; matching and interpretation require the export structure and clinical field definitions.
