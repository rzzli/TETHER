"""Small independent counter controls, not a benchmark invocation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[4]
PATH=Path(__file__).resolve().parent.parent/'stage/implementation_inventory.py'
spec=importlib.util.spec_from_file_location('inventory_under_review',PATH)
inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)


class InventoryCounterTests(unittest.TestCase):
    def setUp(self):
        base=ROOT/'data/cache/inspect-inventory-counter-tests';base.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base);self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_physical_nested_async_and_lexical_comment_definition(self):
        path=self.root/'sample.py'
        path.write_bytes(b"# heading\n\n'''Docstring\n# inside docstring\n'''\ndef outer():\n    async def inner():\n        return 1\n    return inner\nclass Thing:\n    pass\n")
        result=inventory.describe(path,self.root)
        self.assertEqual(result['physical_lines'],11)
        self.assertEqual(result['nonblank_lines_not_starting_hash'],8)
        self.assertEqual(result['functions'],2);self.assertEqual(result['classes'],1)
        self.assertEqual(result['path'],'sample.py')

    def test_duplicate_path_is_not_double_counted(self):
        first=self.root/'a.py';second=self.root/'b.py'
        first.write_text('x = 1\n');second.write_text('y = 2\n')
        result=inventory.group([second,first,first],self.root,'fictional')
        self.assertEqual(result['file_count'],2);self.assertEqual(result['physical_lines'],2)
        self.assertEqual([row['path'] for row in result['files']],['a.py','b.py'])

    def test_bom_counts_original_bytes_but_valid_python_text(self):
        path=self.root/'bom.py';path.write_bytes(b'\xef\xbb\xbfvalue = 1\n')
        result=inventory.describe(path,self.root)
        self.assertEqual(result['bytes'],13);self.assertEqual(result['physical_lines'],1)


if __name__=='__main__':unittest.main()
