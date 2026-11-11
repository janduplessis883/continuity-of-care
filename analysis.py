"""CSV parsing and patient-level appointment counts; no patient data is persisted."""
from math import ceil
import pandas as pd


def read_csv(source, header=True):
    source.seek(0)
    try:
        return pd.read_csv(source, dtype=str, keep_default_na=False,
                           encoding='utf-8-sig', header=0 if header else None,
                           sep=None, engine='python')
    except UnicodeDecodeError:
        source.seek(0)
        return pd.read_csv(source, dtype=str, keep_default_na=False,
                           encoding='cp1252', header=0 if header else None,
                           sep=None, engine='python')


def analyse(frame, mapping):
    data = pd.DataFrame(index=frame.index)
    for field, column in mapping.items():
        if column is not None:
            data[field] = frame[column].fillna('').astype(str).str.strip()
    data['nhs_number'] = data['nhs_number'].str.replace(r'\s+', '', regex=True)
    missing_ids = int(data['nhs_number'].eq('').sum())
    data = data.loc[data['nhs_number'].ne('')].copy()
    data['age'] = pd.to_numeric(data.get('age', pd.Series(index=data.index, dtype=str)), errors='coerce')
    records = []
    for identifier, group in data.groupby('nhs_number', sort=False):
        clinicians = group.loc[group['clinician'].ne(''), 'clinician']
        counts = clinicians.value_counts()
        records.append({'NHS number': identifier, 'Age': group['age'].max(),
                        'Appointments': len(group), 'Clinicians': len(counts),
                        'Missing clinician': int(group['clinician'].eq('').sum()),
                        'Clinician frequency': '; '.join(f'{name}: {count}' for name, count in counts.items())})
    patients = pd.DataFrame(records, columns=['NHS number', 'Age', 'Appointments', 'Clinicians', 'Missing clinician', 'Clinician frequency'])
    patients = patients.sort_values('Appointments', ascending=False, kind='stable').reset_index(drop=True)
    frequencies = (data.loc[data['clinician'].ne('')].groupby(['nhs_number', 'clinician'])
                   .size().reset_index(name='Appointments')
                   .rename(columns={'nhs_number': 'NHS number', 'clinician': 'Clinician'}))
    quality = {'missing_ids': missing_ids, 'missing_clinicians': int(data['clinician'].eq('').sum()),
               'duplicate_rows': int(frame.duplicated().sum())}
    return patients, frequencies, quality


AUDIT_COLUMNS = [
    'Ref.',
    'Patient Identifier',
    'Is a named practice team in place?',
    'Total clinical contacts in last 12 months',
    'No. of contacts: named team in last 12 months',
    'Is practice level Care Plan in place?',
    'Is Universal Care Plan in place?',
    'Is this patient part of regular MDT review?',
    'No. hospital admissions in last 12 months',
    'Did practice follow up post discharge?',
    'Medication review or optimisation in last 12 months',
    'What actions are being taken for the patient to ensure and maintain continuity?',
]


def build_audit(patients, frequencies, team_percentage=25):
    """Populate the audit using the selected practice-wide team percentage."""
    audit = pd.DataFrame('', index=range(len(patients)), columns=AUDIT_COLUMNS)
    audit['Ref.'] = range(1, len(patients) + 1)
    audit['Patient Identifier'] = patients['NHS number'].to_numpy()
    audit['Is a named practice team in place?'] = 'Yes'
    audit['Total clinical contacts in last 12 months'] = patients['Appointments'].to_numpy()
    team_size = max(1, ceil(frequencies['Clinician'].nunique() * team_percentage / 100))
    top_team = (frequencies.sort_values('Appointments', ascending=False)
                 .groupby('NHS number', sort=False).head(team_size)
                 .groupby('NHS number')['Appointments'].sum())
    audit['No. of contacts: named team in last 12 months'] = (
        patients['NHS number'].map(top_team).fillna(0).astype(int).to_numpy())
    return audit
