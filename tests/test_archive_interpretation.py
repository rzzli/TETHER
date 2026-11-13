"""Portable archive tests: recorded fixtures only; no inference or protected labels."""
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from tether_engine.contracts import Case
from tether_engine.serde import ContractError, encode, decode, read_json, write_json, fingerprint
from tether_engine.archive.paths import ArchiveResolver
from tether_engine.archive.interpretation import (verify_interpretation_archive,
    inspect_failed_interpretation_archive, validate_response, _Context)
from tools.science import question_interpretation_runtime as runtime
from tools.science.interpretation_questions import prepare_question

ROOT=Path(__file__).resolve().parents[1]

class ArchiveInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.original=self.root/'original'
        self.inputs=self.original/'inputs';shutil.copytree(ROOT/'src/tether_engine/demo/v2',self.inputs)
        case=replace(decode(Case,read_json(self.inputs/'case.json')),task='T6',endpoint=None)
        write_json(self.inputs/'case.json',encode(case))
        self.prepared=prepare_question(self.inputs/'case.json',self.inputs/'snapshot.json','mechanism-report.v1')
        request=self.prepared.request
        self.response=dict(schema_version=2,kind='question_interpretation',request_sha256=fingerprint(request),
            hypothesis_key=request['hypothesis_key'],question_key=request['question_key'],answer_status='abstained',
            claims=[],abstention_reason='Synthetic recorded abstention, not scientific evidence.',features={},clinical_probability=None)
        self.output=self.original/'run'

    def generate(self, malformed=False, legacy=False):
        replay=self.original/'replay.json';response={'bad':'fixture'} if malformed else self.response
        write_json(replay,dict(schema_version=2,request_sha256=fingerprint(self.prepared.request),
            response=response,usage=dict(input_tokens=0,output_tokens=0,cost_usd=0)))
        call=lambda:runtime.run_question_interpretation(self.inputs/'case.json',self.inputs/'snapshot.json',
            'mechanism-report.v1',self.output,runtime.RecordedQuestionInterpreter(replay))
        if legacy:
            from tools.science.bounded_interpretation import prepare_input, RecordedInterpreter, run_interpretation
            prepared=prepare_input(self.inputs/'case.json',self.inputs/'snapshot.json')
            response=dict(schema_version=1,kind='generated_interpretation',request_sha256=fingerprint(prepared.request),
                hypothesis_key=prepared.request['hypothesis_key'],claims=[],abstention_reason='Synthetic legacy abstention.',
                features={},clinical_probability=None)
            write_json(replay,dict(schema_version=1,request_sha256=fingerprint(prepared.request),response=response,
                                  usage=dict(input_tokens=0,output_tokens=0,cost_usd=0)))
            run_interpretation(self.inputs/'case.json',self.inputs/'snapshot.json',self.output,RecordedInterpreter(replay))
        elif malformed:
            with self.assertRaises(ContractError):call()
        else:call()
        self.anchor=hashlib.sha256((self.output/'receipt.json').read_bytes()).hexdigest() if not malformed else None
        config=read_json(self.output/'configuration.json')
        physical=self.root/'restored';project=physical/'project';fixture=physical/'fixture';fixture.mkdir(parents=True)
        shutil.copytree(self.original,fixture,dirs_exist_ok=True)
        paths=[]
        for proof in ([config['code'],*config['dependency_code']] if legacy else config['code']):
            old=Path(proof['path']);new=project/old.relative_to(ROOT);new.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(old,new);paths.append((old,new,'project',new.relative_to(project)))
        for old in self.original.rglob('*'):
            if old.is_file():paths.append((old,fixture/old.relative_to(self.original),'fixture',old.relative_to(self.original)))
        self.files=[dict(logical_path=str(old),root_id=rid,relative_path=rel.as_posix(),
            sha256=hashlib.sha256(new.read_bytes()).hexdigest(),bytes=new.stat().st_size) for old,new,rid,rel in paths]
        self.bindings=[dict(root_id='project',logical_root=str(ROOT),physical_root=str(project)),
                       dict(root_id='fixture',logical_root=str(self.original),physical_root=str(fixture))]
        if self.original.is_relative_to(ROOT):
            # Workspace-contained temporary roots share a single logical project binding.
            relocated=project/self.original.relative_to(ROOT);relocated.parent.mkdir(parents=True,exist_ok=True)
            shutil.copytree(fixture,relocated)
            for item in self.files:
                if item['root_id']=='fixture':
                    item['root_id']='project'
                    item['relative_path']=(self.original.relative_to(ROOT)/item['relative_path']).as_posix()
            self.bindings=self.bindings[:1]
        self.resolver=ArchiveResolver(self.bindings,self.files)
        # Original fixture root is unavailable during every archive verification.
        self.original.rename(self.root/'original-unavailable')

    def test_recorded_question_requires_original_semantic_checkpoint(self):
        self.generate()
        with self.assertRaisesRegex(ContractError, 'Unsupported executing semantic dependencies'):
            verify_interpretation_archive(str(self.output),self.resolver,self.anchor)

    def test_bounded_recorded_requires_original_semantic_checkpoint(self):
        self.generate(legacy=True)
        with self.assertRaisesRegex(ContractError, 'Unsupported executing semantic dependencies'):
            verify_interpretation_archive(str(self.output),self.resolver,self.anchor)

    def test_wrong_external_receipt_anchor_fails(self):
        self.generate()
        with self.assertRaisesRegex(ContractError,'anchor'):verify_interpretation_archive(str(self.output),self.resolver,'0'*64)

    def test_altered_archived_code_and_missing_dependency_fail(self):
        self.generate();entry=next(x for x in self.files if x['logical_path'].endswith('interpretation_questions.py'))
        physical=self.resolver.resolve(entry['logical_path']);payload=physical.read_bytes();physical.write_bytes(payload+b'\n# changed')
        with self.assertRaises(ContractError):verify_interpretation_archive(str(self.output),self.resolver,self.anchor)
        physical.write_bytes(payload)
        resolver=ArchiveResolver(self.bindings,[x for x in self.files if x is not entry])
        with self.assertRaises(ContractError):verify_interpretation_archive(str(self.output),resolver,self.anchor)

    def test_failed_run_is_inspected_not_promoted_or_repeated(self):
        self.generate(malformed=True)
        # This inspector reconstructs admission, so it must not reinterpret an
        # old failure with the current derivation policy or redispatch a call.
        with self.assertRaisesRegex(ContractError, 'Unsupported executing semantic dependencies'):
            inspect_failed_interpretation_archive(str(self.output),self.resolver)
        with self.assertRaises(ContractError):verify_interpretation_archive(str(self.output),self.resolver)

    def test_response_identity_and_state_mismatch_fail(self):
        response=copy.deepcopy(self.response);response['question_key']='0'*64
        with self.assertRaises(ContractError):validate_response(self.prepared.request,response)
        response=copy.deepcopy(self.response);response['answer_status']='answered'
        with self.assertRaises(ContractError):validate_response(self.prepared.request,response)

    def test_original_root_fallback_is_absent(self):
        self.generate();resolver=ArchiveResolver(self.bindings,[])
        with self.assertRaises(ContractError):verify_interpretation_archive(str(self.output),resolver,self.anchor)

if __name__=='__main__':unittest.main()
