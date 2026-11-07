import unittest

from tether_engine.serde import ContractError
from tools.framework.audit_virtual_biotech import agent_configuration, literal_assignment


class VirtualBiotechAuditTests(unittest.TestCase):
    def test_literal_dataset_and_model_extraction_never_imports_source(self):
        text = "raise RuntimeError('must not execute')\nOPEN_TARGETS_DATASETS = ('a', 'b')\nDEFAULT_MODEL_ID='example'\n"
        self.assertEqual(literal_assignment(text, 'OPEN_TARGETS_DATASETS'), ('a', 'b'))
        self.assertEqual(literal_assignment(text, 'DEFAULT_MODEL_ID'), 'example')
        with self.assertRaises(ContractError): literal_assignment(text, 'missing')

    def test_agent_models_and_tools_are_reported_from_ast(self):
        source = '''
def build():
    agents['specialist'] = AgentDefinition(prompt=unknown(), model=specialist_model, tools=['Read', 'Bash'])
    agents['reviewer'] = AgentDefinition(model='haiku', tools=['Read'])
'''
        result = agent_configuration(source)
        self.assertEqual(result['specialist']['model'], 'specialist_model')
        self.assertEqual(result['specialist']['tools'], ['Read', 'Bash'])
        self.assertEqual(result['reviewer']['model'], 'haiku')
        with self.assertRaises(ContractError): agent_configuration('print("not executed")')


if __name__ == '__main__': unittest.main()
