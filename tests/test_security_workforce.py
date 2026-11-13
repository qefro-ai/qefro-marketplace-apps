"""App contracts; runtime/security claims require the separate Rust/live suites."""
import unittest
from pathlib import Path
import yaml

APP = Path(__file__).resolve().parents[1] / 'apps/security-workforce-manager'
def read(path): return yaml.safe_load((APP / path).read_text())

class SecurityWorkforceTests(unittest.TestCase):
    def test_all_inventory_files_and_relationships_resolve(self):
        manifest = read('manifest.yaml')
        ids = set(manifest['entities'])
        self.assertEqual(ids, {p.stem for p in (APP/'entities').glob('*.yaml')})
        for id in ids:
            entity = read(f'entities/{id}.yaml')
            self.assertEqual(entity['id'], id)
            if 'allocate_code' in entity:
                allocated = next(f for f in entity['fields'] if f['name'] == entity['allocate_code']['field'])
                self.assertTrue(allocated['unique'])
                self.assertFalse(allocated.get('required', False), 'Native host rejects hidden allocated input when required')
            for field in entity['fields']:
                if field['type'] == 'relation': self.assertIn(field['ref_entity'], ids)
                self.assertNotIn(field['name'], ['tenant_id','workspace_id','installation_id'])
        self.assertEqual(set(manifest['flows']), {p.stem for p in (APP/'workflows').glob('*.yaml')})

    def test_staff_only_flows_bind_real_dynamic_choice_outputs(self):
        self.assertEqual(read('manifest.yaml')['channels'], [])
        for path in (APP/'workflows').glob('*.yaml'):
            flow = yaml.safe_load(path.read_text())
            self.assertEqual(flow['surfaces'], ['staff'])
            outputs = set()
            for step in flow['steps']:
                if 'choices_from' in step:
                    self.assertIn(step['choices_from'], outputs)
                    self.assertEqual(step['value_field'], 'id')
                    self.assertTrue(step['empty_message'])
                if 'output' in step: outputs.add(step['output'])
                if step['type']=='tool':
                    self.assertEqual(step['execution'], 'runtime')
                    self.assertTrue(step['tool'].startswith('entity.'))
                    for key,value in step.get('input_map',{}).items():
                        self.assertNotIn(key,['tenant_id','workspace_id','installation_id','version'])
            self.assertEqual(flow['steps'][-1]['type'],'complete')

    def test_private_entities_are_not_general_dashboard_sources(self):
        sources = read('ui/sources.yaml')
        self.assertTrue({'employee_private','emirates_id'}.isdisjoint(s['target'] for s in sources))
        fields = read('entities/emirates_id.yaml')['fields']
        suffix = next(f for f in fields if f['name']=='number_last_four')
        self.assertEqual(suffix['validation']['pattern'], '^[0-9]{4}$')
        self.assertNotIn('emirates_id_number', [f['name'] for f in fields])

    def test_dashboard_uses_server_metrics_and_resolvable_navigation(self):
        pages = {p['id'] for p in read('ui/pages.yaml')}
        sources = {s['id'] for s in read('ui/sources.yaml')}
        widgets = {w['id']:w for w in read('ui/widgets.yaml')}
        for page in read('ui/pages.yaml'):
            for placement in page.get('widgets',[]): self.assertIn(placement['widget'],widgets)
        for widget in widgets.values():
            if 'source' in widget: self.assertIn(widget['source'],sources)
            options=widget.get('options',{})
            if 'navigate_to' in options: self.assertIn(options['navigate_to'],pages)
            if widget['type']=='metric':
                self.assertIn(options['aggregate'],['count','today'])
                self.assertNotIn('value',options)
        self.assertIn('present records',widgets['today_present']['title'])

    def test_contract_defaults_and_history_are_explicit(self):
        self.assertEqual(read('settings/business.yaml')['settings']['contract_duration_years']['default'],2)
        contract=read('entities/employment_contract.yaml')
        fields={f['name']:f for f in contract['fields']}
        self.assertEqual(fields['duration_years']['default_from_setting'],'contract_duration_years')
        self.assertEqual(fields['previous_contract']['ref_entity'],'employment_contract')
        self.assertEqual(fields['cancellation_reason']['required_when']['value'],'terminated')
        self.assertEqual(contract['concurrency'],'optimistic')
        self.assertNotIn('computed',contract, 'No invented calendar expression')
        self.assertEqual(contract['state_machine']['initial'], 'draft')
        self.assertEqual(contract['state_machine']['initial_state'], 'draft')
        for state in contract['state_machine']['states']:
            self.assertEqual(state['name'], state['id'])
            self.assertEqual(state['terminal'], state['final'])

    def test_date_watches_declare_events_and_status_guards(self):
        events=set(read('manifest.yaml')['events'])
        for id in ['employment_contract','emirates_id']:
            entity=read(f'entities/{id}.yaml')
            fields={f['name']:f for f in entity['fields']}
            for watch in entity['date_events']:
                self.assertIn(watch['event'],events)
                self.assertEqual(fields[watch['field']]['type'],'date')
                self.assertTrue(watch['when_status'])
                self.assertNotIn('offset_days',watch)

    def test_synthetic_seed_uses_symbols_not_tenant_ids(self):
        data=yaml.safe_load((Path(__file__).parent/'fixtures/security-workforce/seed.yaml').read_text())
        symbols=set()
        for row in data['records']:
            self.assertNotIn(row['key'],symbols)
            for value in row['document'].values():
                if isinstance(value,str) and value.startswith('@'): self.assertIn(value[1:],symbols)
            symbols.add(row['key'])
            self.assertTrue({'tenant_id','workspace_id','installation_id'}.isdisjoint(row['document']))

if __name__=='__main__':unittest.main()
