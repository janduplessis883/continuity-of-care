import re
from math import ceil
import altair as alt
import pandas as pd
import streamlit as st
from analysis import analyse, read_csv, build_audit

st.set_page_config(page_title='Continuity of Care Audit Tool', page_icon='◌', layout='wide')
st.markdown('''<style>
.block-container {max-width:1280px;padding-top:2.5rem;}
h1 {letter-spacing:-1.5px;} [data-testid="stMetric"] {background:white;border:1px solid #e2e8ef;border-radius:14px;padding:18px;}
[data-testid="stMetricLabel"] {color:#54687c;} div.stButton>button {border-radius:9px;}
</style>''', unsafe_allow_html=True)
st.caption('Practice Insights  /  Appointment Analysis')
st.title('Continuity of Care Audit Tool')
st.markdown('Understand how often patients attend - and how many different clinicians they see.')

with st.sidebar:
    st.subheader('Your appointment data')
    upload = st.file_uploader('Upload a SystmOne CSV export', type=['csv'])
    demo = st.checkbox('Explore with demo data', value=False)
    has_header = st.checkbox('CSV has a header row', value=True)
    st.divider()
    st.subheader('Additional audit data')
    st.caption('Optional CSV uploads. These files are available for review; audit fields are not populated from them yet.')
    for label, key in [('MDT', 'mdt_csv'), ('Care Plan', 'care_plan_csv'), ('Medication Reviews', 'medication_reviews_csv')]:
        extra_upload = st.file_uploader(f'Upload {label} CSV', type=['csv'], key=key)
        if extra_upload is not None:
            try:
                extra_data = read_csv(extra_upload)
            except (ValueError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError):
                st.error(f'{label} CSV could not be read. Check that it is a valid CSV with a header row.')
            else:
                st.success(f'{label}: {len(extra_data):,} rows loaded')
                with st.expander(f'{label} columns'):
                    st.write([str(column) for column in extra_data.columns])
    st.divider()
    st.caption('Files are processed in the running app’s memory. This app does not write uploaded data to disk or send it to an external service. If hosted, the server receives the upload.')

if upload is None and not demo:
    st.info('Upload your CSV in the sidebar, or choose “Explore with demo data” to try the dashboard.')
    a, b, c = st.columns(3)
    a.markdown('### 01 · Upload\nBring your appointment export. Column names can be matched in the app.')
    b.markdown('### 02 · Understand\nSee patient appointment counts and the number of distinct clinicians seen.')
    c.markdown('### 03 · Explore\nFilter the cohort, inspect clinician frequencies, and download the results.')
    st.stop()

if upload is not None:
    try:
        data = read_csv(upload, has_header)
    except (ValueError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError):
        st.error('The CSV could not be read. Check its format and whether it has a header row.')
        st.stop()
    st.caption(f'Uploaded CSV · {len(data):,} rows · {len(data.columns)} columns')
else:
    rows = []
    for patient in range(1, 61):
        for visit in range(1 + (patient * 7) % 14):
            rows.append({'age': str(18 + patient % 72), 'nhs_number': f'DEMO-{patient:03}',
                         'app_date': f'{1 + visit:02}/10/2026',
                         'clinician': ['Dr Patel', 'Dr Smith', 'Dr Jones', 'Nurse Williams', 'Dr Evans'][(patient + visit % (1 + patient % 5)) % 5]})
    data = pd.DataFrame(rows)
    st.caption('DEMO DATA · Synthetic patients and appointments')

if data.empty or len(data.columns) < 2:
    st.warning('Upload a CSV with appointment rows and at least patient ID and clinician columns.')
    st.stop()

aliases = {'nhs_number': ['nhsnumber', 'nhsno', 'nhs', 'patientnhsnumber'],
           'clinician': ['clinician', 'appointmentconsultant', 'appointmentclinician', 'consultant', 'doctor'],
           'age': ['age', 'patientage'],
           'app_date': ['appdate', 'appointmentdate', 'dateofappointment', 'appointmentdatetime', 'date']}
normalise = lambda value: re.sub(r'[^a-z0-9]', '', str(value).lower())
with st.expander('Match your columns', expanded=upload is not None):
    st.caption('Only NHS number and clinician are required. Age and appointment date are optional. Each row counts as one appointment; patient-count columns are ignored.')
    mapping = {}
    cols = st.columns(4)
    for panel, (field, label) in zip(cols, [('nhs_number', 'NHS number'), ('clinician', 'Clinician'), ('age', 'Age (optional)'), ('app_date', 'Appointment date (optional)')]):
        choices = [None] + list(data.columns)
        guess = next((column for column in data.columns if normalise(column) in aliases[field]), None)
        if guess is None and len(data.columns) == 7:
            guess = data.columns[{'nhs_number': 2, 'clinician': 5, 'age': 0, 'app_date': 4}[field]]
        mapping[field] = panel.selectbox(label, choices, index=choices.index(guess),
                                         format_func=lambda x: 'Not selected' if x is None else str(x))
    st.caption('Appointment date mapping does not filter or change the appointment counts.')
    st.caption('For an unrecognised seven-column export, defaults follow: age, DOB, NHS number, surname, appointment date, clinician, patient count. Please check the matches.')
if mapping['nhs_number'] is None or mapping['clinician'] is None:
    st.info('Select the NHS number and clinician columns to continue.')
    st.stop()
selected = [value for value in mapping.values() if value is not None]
if len(set(selected)) != len(selected):
    st.error('Choose a different source column for each field.')
    st.stop()
patients, frequencies, quality = analyse(data, mapping)
if quality['missing_ids']:
    st.warning(f"{quality['missing_ids']:,} rows excluded because the patient ID is blank.")
if quality['missing_clinicians']:
    st.warning(f"{quality['missing_clinicians']:,} appointments have no clinician. They count as appointments but do not add a distinct clinician.")
if quality['duplicate_rows']:
    st.info(f"{quality['duplicate_rows']:,} exact duplicate rows detected. They remain included; check whether they represent separate appointments.")
if patients.empty:
    st.warning('No patient IDs were found in the selected column.')
    st.stop()

with st.sidebar:
    st.subheader('Cohort filters')
    minimum = st.number_input('Minimum appointments', min_value=1, value=1, step=1)
    clinician_count = st.selectbox('Distinct clinicians seen', ['All'] + sorted(patients['Clinicians'].unique().tolist()))
    st.caption('Filters select patients. All appointments for each selected patient remain included.')
cohort = patients.loc[patients['Appointments'].ge(minimum)].copy()
if clinician_count != 'All':
    cohort = cohort.loc[cohort['Clinicians'].eq(clinician_count)]
if cohort.empty:
    st.info('No patients match these filters. Adjust the cohort filters to continue.')
    st.stop()

st.subheader('Your cohort at a glance')
a, b, c, d = st.columns(4)
a.metric('Patients', f'{len(cohort):,}')
b.metric('Appointments', f"{cohort['Appointments'].sum():,}")
c.metric('Appointments / patient', f"{cohort['Appointments'].mean():.1f}")
d.metric('Clinicians / patient', f"{cohort['Clinicians'].mean():.1f}")
st.caption('Distinct clinicians are counted by their trimmed name. Different spellings remain separate; missing clinicians are excluded from that count.')

st.subheader('Named-team size')
team_percentage = st.slider('Percentage of unique practice clinicians in the team', min_value=10, max_value=50, value=15, step=5, format='%d%%')
practice_clinicians = frequencies['Clinician'].nunique()
team_size = max(1, ceil(practice_clinicians * team_percentage / 100))
audit = build_audit(cohort, frequencies, team_percentage)
st.caption(f'{practice_clinicians} unique clinicians × {team_percentage}% → top {team_size} clinicians per patient (rounded up). Counts use all clinician names in the upload; GP roles are not identified separately.')

overview, details, audit_tab, methods = st.tabs(['Overview', 'Patient details', 'Audit output', 'How it works'])
with overview:
    left, right = st.columns(2)
    for panel, field, title in [(left, 'Clinicians', 'How many clinicians does each patient see?'),
                                 (right, 'Appointments', 'How often do patients attend?')]:
        panel.markdown(f'#### {title}')
        distribution = cohort.groupby(field).size().reset_index(name='Patients')
        chart = alt.Chart(distribution).mark_bar(color='#087f8c', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X(f'{field}:Q', title=f'{field} per patient', axis=alt.Axis(tickMinStep=1)),
            y=alt.Y('Patients:Q', axis=alt.Axis(tickMinStep=1)), tooltip=[field, 'Patients']).properties(height=300)
        mean_value = float(cohort[field].mean())
        mean_data = pd.DataFrame({'Mean': [mean_value], 'Label': [f'Mean: {mean_value:.1f}']})
        mean_line = alt.Chart(mean_data).mark_rule(color='#d97706', strokeDash=[6, 4], strokeWidth=2).encode(
            x=alt.X('Mean:Q'), tooltip=[alt.Tooltip('Mean:Q', format='.2f')])
        mean_label = alt.Chart(mean_data).mark_text(
            color='#a35405', align='left', dx=6, fontWeight='bold').encode(
                x=alt.X('Mean:Q'), y=alt.value(12), text='Label:N')
        panel.altair_chart(chart + mean_line + mean_label, width='stretch')
    st.markdown('#### Appointment count and clinician variety')
    bubbles = cohort.groupby(['Appointments', 'Clinicians']).size().reset_index(name='Patients')
    scatter = alt.Chart(bubbles).mark_circle(color='#087f8c', opacity=.65).encode(
        x=alt.X('Appointments:Q', title='Appointments per patient', axis=alt.Axis(tickMinStep=1)),
        y=alt.Y('Clinicians:Q', title='Distinct clinicians per patient', axis=alt.Axis(tickMinStep=1)),
        size='Patients:Q', tooltip=['Appointments', 'Clinicians', 'Patients']).properties(height=300)
    st.altair_chart(scatter, width='stretch')
with details:
    st.markdown('#### Patient appointment summary')
    show_ids = st.checkbox('Show NHS numbers in the table', value=False)
    display = cohort.copy()
    if not show_ids:
        display['NHS number'] = [f'Patient {i + 1:03}' for i in range(len(display))]
    st.dataframe(display, hide_index=True, width='stretch')
    st.caption('Table labels hide NHS numbers by default. Downloads contain the original NHS numbers and must be handled as patient data.')
    st.download_button('Download patient summary', cohort.to_csv(index=False).encode('utf-8'), 'patient_summary.csv', 'text/csv')
    selected_frequencies = frequencies.loc[frequencies['NHS number'].isin(cohort['NHS number'])]
    st.download_button('Download clinician frequencies', selected_frequencies.to_csv(index=False).encode('utf-8'), 'clinician_frequencies.csv', 'text/csv')
with audit_tab:
    st.markdown('#### Continuity audit output')
    st.caption('Matches the supplied audit template, with one row per patient in the filtered cohort, ordered by appointment count.')
    st.caption(f'This upload contains {practice_clinicians} unique clinicians. Named-team contacts sum each patient’s top {team_size} clinician counts: {team_percentage}% of the practice total, rounded up. The practice total uses the full upload, before cohort filters. If a patient saw fewer clinicians, all their available clinician counts are used. Blank clinician names are excluded. Named practice team is set to Yes for all patients; fields awaiting supporting data remain blank.')
    show_audit_ids = st.checkbox('Show patient identifiers in the audit preview', value=False)
    audit_preview = audit.copy()
    if not show_audit_ids:
        audit_preview['Patient Identifier'] = [f'Patient {i + 1:03}' for i in range(len(audit_preview))]
    st.dataframe(audit_preview, hide_index=True, width='stretch')
    st.caption('The download contains original patient identifiers. Blank fields mean data has not been provided, rather than “No”.')
    st.download_button('Download **Audit** template CSV', audit.to_csv(index=False).encode('utf-8-sig'), 'continuity_of_care_audit.csv', 'text/csv', type='primary')
with methods:
    st.markdown('''#### Counting rules
- Each uploaded row represents one appointment, including rows without an appointment date.
- Patients are grouped by NHS number after removing whitespace. Leading zeros are preserved.
- Appointment counts include rows with missing clinicians; distinct clinician counts exclude blank names.
- Clinician names are trimmed, but spelling and capitalisation are otherwise preserved.
- Audit team size uses the selected percentage (10–50%, default 15%) of all unique nonblank clinicians in the upload, rounded up (minimum one). Named-team contacts sum that many highest clinician counts separately for each patient. Cohort filters do not change the practice team size. Named-team status is set to Yes for everyone, as specified.
- Audit 12-month columns use all uploaded appointments; the export should cover the last 12 months.
- Age is the maximum numeric age recorded for that patient, matching your original script.
- Exact duplicate rows remain included. Filter the export beforehand if cancellations or other appointment statuses should be excluded.

The charts describe the uploaded appointments. They do not assess clinical quality or establish a clinical continuity score.''')
