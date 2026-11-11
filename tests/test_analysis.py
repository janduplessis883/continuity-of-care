import io
import unittest
import pandas as pd
from analysis import read_csv, analyse, build_audit


class AnalysisTests(unittest.TestCase):
    def test_counts_and_missing_clinicians(self):
        data = pd.DataFrame({'id': ['001 234', '001234', '001234', '', '002'],
                             'doctor': ['Dr A', 'Dr B', '', 'Dr C', 'Dr A'],
                             'age': ['40', '41', '41', '20', '70']})
        patients, frequencies, quality = analyse(data, {'nhs_number': 'id', 'clinician': 'doctor', 'age': 'age'})
        first = patients.set_index('NHS number').loc['001234']
        self.assertEqual(first['Appointments'], 3)
        self.assertEqual(first['Clinicians'], 2)
        self.assertEqual(first['Missing clinician'], 1)
        self.assertEqual(first['Age'], 41)
        self.assertEqual(quality['missing_ids'], 1)
        self.assertEqual(frequencies['Appointments'].sum(), 3)

    def test_audit_uses_one_quarter_of_practice_clinicians(self):
        data = pd.DataFrame({
            'id': ['001'] * 12 + ['002'] * 3 + ['003'],
            'doctor': ['A'] * 5 + ['B'] * 3 + ['C'] * 2 + ['D', ''] + ['X', 'Y', 'Y'] + ['']})
        patients, frequencies, _ = analyse(data, {'nhs_number': 'id', 'clinician': 'doctor'})
        audit = build_audit(patients, frequencies).set_index('Patient Identifier')
        self.assertTrue(audit['Is a named practice team in place?'].eq('Yes').all())
        self.assertEqual(audit.loc['001', 'Total clinical contacts in last 12 months'], 12)
        self.assertEqual(audit.loc['001', 'No. of contacts: named team in last 12 months'], 8)
        self.assertEqual(audit.loc['002', 'No. of contacts: named team in last 12 months'], 3)
        self.assertEqual(audit.loc['003', 'No. of contacts: named team in last 12 months'], 0)
        self.assertTrue(audit['Is practice level Care Plan in place?'].eq('').all())

    def test_team_size_uses_full_practice_even_for_filtered_cohort(self):
        for practice_size, expected in [(3, 10), (10, 27)]:
            frequencies = pd.DataFrame({
                'NHS number': ['001'] * practice_size,
                'Clinician': [f'Dr {i}' for i in range(practice_size)],
                'Appointments': list(range(10, 10 - practice_size, -1))})
            patients = pd.DataFrame({'NHS number': ['001'], 'Appointments': [int(frequencies['Appointments'].sum())]})
            audit = build_audit(patients, frequencies)
            self.assertEqual(audit.iloc[0]['No. of contacts: named team in last 12 months'], expected)

    def test_configurable_team_percentage(self):
        frequencies = pd.DataFrame({'NHS number': ['001'] * 10,
                                    'Clinician': [f'GP {i}' for i in range(10)],
                                    'Appointments': list(range(10, 0, -1))})
        patients = pd.DataFrame({'NHS number': ['001'], 'Appointments': [55]})
        for percentage, expected in [(10, 10), (20, 19), (25, 27), (30, 27), (35, 34)]:
            audit = build_audit(patients, frequencies, team_percentage=percentage)
            self.assertEqual(audit.iloc[0]['No. of contacts: named team in last 12 months'], expected)

    def test_csv_preserves_identifiers(self):
        frame = read_csv(io.BytesIO(b'NHS Number,Surname\n0012345678,NA\n'))
        self.assertEqual(frame.iloc[0, 0], '0012345678')
        self.assertEqual(frame.iloc[0, 1], 'NA')

    def test_empty_identifiers_produce_empty_results(self):
        patients, _, quality = analyse(pd.DataFrame({'id': [' '], 'doctor': ['A']}),
                                      {'nhs_number': 'id', 'clinician': 'doctor'})
        self.assertTrue(patients.empty)
        self.assertEqual(quality['missing_ids'], 1)


if __name__ == '__main__':
    unittest.main()
