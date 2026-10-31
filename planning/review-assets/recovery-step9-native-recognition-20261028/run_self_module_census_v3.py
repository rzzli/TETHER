"""Separate self-module-census parent, acyclic metadata binding/preparation revision3.

Preparation grants no constructor/child execution permission; the general SDK gate remains false.
Census completeness is observational and never establishes ABI eligibility.
The execute function is for a separately audited driver after an exact once-only
root decision; this file's CLI only prepares a protocol and does not dispatch it.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from importlib import metadata, util
import json
import os
from pathlib import Path
import subprocess  # list2cmdline only; no Popen.
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASIS=HERE/"qualify_detached_native_worker_v1.py"
BASIS_SHA="6be0634f9bc9ea89eff1e54cbb963c355853eacc9ad9bbe63496b2f1aa50fea9"
def sha(path):
    with Path(path).open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
if sha(BASIS)!=BASIS_SHA:raise RuntimeError("Detached qualifier source basis changed")
spec=util.spec_from_file_location("qualified_detached_basis_for_census",BASIS)
q=util.module_from_spec(spec);spec.loader.exec_module(q)
sdk=q.load_sdk()  # Declarations only; no Kernel32 instance or SDK mutation.
safe,pin,canonical,write_new,require=q.safe,q.pin,q.canonical,q.write_new,q.require
SDK_SHA="3bfac51893b60221728ac915516c5e816c0cfc5a82899f5871f7931469d7fdfd"
QUALIFICATION=HERE/"DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json"
QUALIFICATION_SHA="7f184e9b4d04019c6fba3bc661dabe241b7ef6a2a0ee8c713711eeeae12eb961"
DESIGN_CONTRACT=HERE/"SELF-MODULE-CENSUS-CONTRACT-v1.json"
DESIGN_CONTRACT_SHA="5bcde6482793961eb20ec10c7bb9002747f42a5670ff227bee6745d65b8caf41"
IMPLEMENTATION_DECISION=HERE/"SELF-MODULE-CENSUS-IMPLEMENTATION-ROOT-DECISION-v1.json"
IMPLEMENTATION_DECISION_SHA="8b9ebb0cdf7543a080af04aa70c602c5373a1e665e28b1b180a70758b39386ab"
RUNTIME=ROOT/"data/cache/approved-native-mirror-20261028T004531Z/runtime"
EXE=ROOT/"data/cache/r09-module-census-build-v1-20261029T011510Z/typed_public_c_recognizer_abi.exe"
EXE_SHA="559e4e9a654c9487679c551eebf73d6a279416d0990f491d0918d99cdb6f6183"
VERIFIED_BUILD=HERE/"SELF-MODULE-CENSUS-BUILD-RESULT-VERIFICATION-v1.json"
VERIFIED_BUILD_SHA="51c255ec00aaf050a833682f4a41abd27f6b82fe6ffadef18a8e1a92d6756306"
EXECUTION_AUTHORITY=HERE/"SELF-MODULE-CENSUS-STATIC-AUTHORITY-v2.json"
EXECUTION_AUTHORITY_SHA="70efee36da8aa73845fee25ba2eea495895a84b4cd9676c98ae9777ce084b42c"
PROTOCOL=HERE/"SELF-MODULE-CENSUS-EXECUTION-PROTOCOL-v2.json"
CHECKER=HERE/"check_self_module_census_binding_v3.py"
PURE=HERE/"SELF-MODULE-CENSUS-BINDING-PURE-PROOF-v3.json"
PREPARATION=ROOT/"data/cache/r09-self-module-census-preparation-v3-20261029.json"
STATIC_PATHS=(
    'C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um\\fileapi.h',
    'C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um\\jobapi2.h',
    'C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um\\namedpipeapi.h',
    'C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um\\processthreadsapi.h',
    'C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um\\winbase.h',
    'C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um\\winnt.h',
    'C:\\Users\\zzric\\AppData\\Roaming\\uv\\python\\cpython-3.11.15-windows-x86_64-none\\python.exe',
    'C:\\Windows\\System32\\advapi32.dll',
    'C:\\Windows\\System32\\bcrypt.dll',
    'C:\\Windows\\System32\\bcryptprimitives.dll',
    'C:\\Windows\\System32\\cryptbase.dll',
    'C:\\Windows\\System32\\cryptsp.dll',
    'C:\\Windows\\System32\\kernel32.dll',
    'C:\\Windows\\System32\\kernelbase.dll',
    'C:\\Windows\\System32\\msvcp140.dll',
    'C:\\Windows\\System32\\msvcrt.dll',
    'C:\\Windows\\System32\\ntdll.dll',
    'C:\\Windows\\System32\\psapi.dll',
    'C:\\Windows\\System32\\rpcrt4.dll',
    'C:\\Windows\\System32\\sechost.dll',
    'C:\\Windows\\System32\\ucrtbase.dll',
    'C:\\Windows\\System32\\vcruntime140.dll',
    'C:\\Windows\\System32\\vcruntime140_1.dll',
    'D:\\Projects\\drug_target_agents\\data\\cache\\approved-native-mirror-20261028T004531Z\\runtime\\ggml-base.dll',
    'D:\\Projects\\drug_target_agents\\data\\cache\\approved-native-mirror-20261028T004531Z\\runtime\\ggml.dll',
    'D:\\Projects\\drug_target_agents\\data\\cache\\approved-native-mirror-20261028T004531Z\\runtime\\libomp.dll',
    'D:\\Projects\\drug_target_agents\\data\\cache\\approved-native-mirror-20261028T004531Z\\runtime\\llama.dll',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-build-v1-20261029T011510Z\\build-report.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-build-v1-20261029T011510Z\\post-lease-cleanup.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-build-v1-20261029T011510Z\\receipt.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-build-v1-20261029T011510Z\\terminal-seal.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-build-v1-20261029T011510Z\\typed_public_c_recognizer_abi.exe',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-preparation-v1-20261029T011510Z\\headers\\ggml-alloc.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-preparation-v1-20261029T011510Z\\headers\\ggml-backend.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-preparation-v1-20261029T011510Z\\headers\\ggml-cpu.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-preparation-v1-20261029T011510Z\\headers\\ggml-opt.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-preparation-v1-20261029T011510Z\\headers\\ggml.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-preparation-v1-20261029T011510Z\\headers\\gguf.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-preparation-v1-20261029T011510Z\\headers\\llama.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-preparation-v1-20261029T011510Z\\recognizer_runtime_pins.hpp',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-module-census-preparation-v1-20261029T011510Z\\typed_public_c_recognizer.cpp',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-grammar-source-20261028T020623Z\\sources\\include\\llama.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-followup-source-20261028T164431Z\\sources\\ggml\\include\\ggml-alloc.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-source-20261028T161554Z\\sources\\ggml\\include\\ggml-backend.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-source-20261028T161554Z\\sources\\ggml\\include\\ggml-cpu.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-source-20261028T161554Z\\sources\\ggml\\include\\ggml-opt.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-source-20261028T161554Z\\sources\\ggml\\include\\ggml.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-source-20261028T161554Z\\sources\\ggml\\include\\gguf.h',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\dist\\asof_target_agents-0.3.11-py3-none-any.whl',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\__init__.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\__main__.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\agents.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\__init__.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\__main__.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\core.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\interpretation.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\paths.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\restore.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\semantic_dependencies.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\artifacts.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\atomic.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\chrono.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\cli.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\contracts.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\case.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\evidence.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\future.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\replay.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\scorer.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\snapshot.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\case.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\evidence.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\future.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\raw-inputs.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\replay.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\scorer.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\snapshot.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\evaluation.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\features.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\ingest.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\journal.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\ledger.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\local_model.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\maintenance.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\provenance.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\retrieval.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\scorer.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\semantics.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\serde.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\__init__.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\__main__.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\authority_four_arm.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\baseline_smoke.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\baselines.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\collected_source.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\diagnostic.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\diagnostic_codec.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\diagnostic_resources.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\fixed_evidence.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\fixed_evidence_smoke.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\interpretation_generation.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\interpretation_grammar.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\interpretation_interface.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\native.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\native_accounting.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\native_diagnostic.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\native_interpretation.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\native_mode.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\preparation_payloads.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\process.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\proofs.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\recorded.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\authority-four-arm-stimuli-v1.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\diagnostic-templates-v1.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\fixed-evidence-plan-v1.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\native-server-v2.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\retrieval-corpus-v1.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\retrieval-policy-v1.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\retrieval-recorded-stimuli-v1.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\simplified-response-schema-v1.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\simplified-response-schema-v2.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\synthetic-context-v1.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\synthetic-orientation-v1.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\tokenizer-assets-v1.json',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\retrieval_preparation.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\retrieval_smoke.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\session.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\source_preparation.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\source_rows.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\stable_read.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\token_capacity.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\tokenization.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\wire.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\workflow.py',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof_target_agents-0.3.11.dist-info\\entry_points.txt',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof_target_agents-0.3.11.dist-info\\METADATA',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof_target_agents-0.3.11.dist-info\\WHEEL',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\pyvenv.cfg',
    'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Scripts\\python.exe',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-generation-contract-20261028\\acceptance.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-generation-contract-20261028\\WHEEL-ENVIRONMENTS.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\abi_parent_launch_draft_v3.py',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\census_fixture_v1.py',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\check_module_census_sealer_v1.py',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\check_module_census_validation_v1.py',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\DETACHED-ABI-TERMINAL-COMPONENT-PROOF-v3.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\DETACHED-ABI-V3-RESULT-VERIFICATION.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\DETACHED-NATIVE-QUALIFICATION-PROTOCOL-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\DETACHED-POLICY-CONTRACT-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\DETACHED-POLICY-DESIGN-v1.md',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\detached_abi_terminal_observation_v3.py',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\detached_parent_launch_draft_v1.py',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\HEADER-CLOSURE-FOLLOWUP.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\module_census_status_seal_v1.py',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\module_census_validation_v1.py',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\prepare_census_static_authority_v2.py',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\qualify_detached_native_worker_v1.py',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\run_self_module_census_v1.py',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-ARTIFACT-PURE-PROOF-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-BINDING-FINDINGS-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-BUILD-PROTOCOL-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-BUILD-RESULT-VERIFICATION-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-BUILD-ROOT-DECISION-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-CHILD-PURE-PROOF-v3.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-CHILD-SOURCE-PEER-REVIEW-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-CONTRACT-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-DESIGN-PEER-REVIEW-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-DESIGN-v1.md',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-IMPLEMENTATION-ROOT-DECISION-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-PARENT-MECHANICS-PEER-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-PARENT-PURE-PROOF-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-PARSER-INDEPENDENT-PROOF-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-REGRESSIONS-AFTER-v4.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-SEALER-PURE-PROOF-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-VALIDATION-PURE-PROOF-v1.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\SELF-MODULE-CENSUS-WIRE-v2.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TYPED-ABI-BUILD-PROTOCOL-v5.json',
    'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\typed_public_c_recognizer_v8.cpp',
)
WIRE=HERE/"SELF-MODULE-CENSUS-WIRE-v2.json"
WIRE_SHA="228e8af00e3da2cba05cdc4d2523a99812ce84fb43968cd65d6bc08021843934"
VALIDATOR_SOURCE=HERE/"module_census_validation_v1.py"
VALIDATOR_SHA="f5b8b4496018bfa66473bb694c99c3588a49bbb1060b814196f1ba80b32b95db"
SEALER_SOURCE=HERE/"module_census_status_seal_v1.py"
SEALER_SHA="7794819e3b8013847f0f5e8912d8b8424edfea8c2a95a09354b0918409daf682"
STATUS="module_census_observations_retained_not_ABI_qualification"
TERMINAL_SOURCE=HERE/"detached_abi_terminal_observation_v3.py"
TERMINAL_SHA="4ea2c429a8e4d512d42ae449fc3764550421ae8cf6491e3866c8322880d5c96c"
TERMINAL_POLICY=dict(capture_drain_seconds=0.25,maximum_capture_polls=64,
    physical_pipe_EOF_is_not_child_exit=True,unknown_creation_is_not_final=True,
    skip_new_observations_and_input_rechecks_after_interruption=True,late_returned_bytes_retained=True)
LIMITS=dict(parent_seconds=60,child_seconds=30,child_cleanup_reserved_seconds=2,finalization_reserved_seconds=5,
    process_and_job_commit_bytes=268435456,active_processes=1,maximum_children=1,stream_bytes=65536,
    maximum_job_snapshots=40,job_pid_capacity=16,attempt_bytes=4096,result_bytes=2097152,row_bytes=65536,
    child_structured_artifact_bytes=2097152,attempt_terminal_failure_reserve_bytes=65536,max_modules=64)
RUNTIME_EXPECTED={
    "libomp.dll":dict(bytes=768000,sha256="a12116ba72d1d6820407cf30be23da04ce79d6bb8a71a5ee71759c5a1faa6f1c"),
    "ggml-base.dll":dict(bytes=803840,sha256="84e3057e6fe2c581a9d194d27e5510b1a71723074e01dfb9b34926e4d5af52f3"),
    "ggml.dll":dict(bytes=78848,sha256="2a49a0f2d3c58b182bfa5267950cef2e4f3378a12e9ebbc6b36554bf5ca016ba"),
    "llama.dll":dict(bytes=3581952,sha256="166e8de1bd07573dc0f51ab1f429ab5df0d08492e7302bbe41a39014248f5e6d")}
CLASSIFICATION_METADATA=HERE/"TYPED-ABI-BUILD-PROTOCOL-v5.json"
CLASSIFICATION_METADATA_SHA="371b1791ba413173ecfab132ea6f9a22994a0d601981367553a3a94cf8d85222"
require(sha(CLASSIFICATION_METADATA)==CLASSIFICATION_METADATA_SHA,"Pinned system-description basis changed")
require(sha(DESIGN_CONTRACT)==DESIGN_CONTRACT_SHA,"Census design contract changed")
_system_names={name.casefold() for name in json.loads(DESIGN_CONTRACT.read_bytes())["existing_classification_policy"]["System32_candidate_names"]}
SYSTEM_PINS={item["path"]:item for item in json.loads(CLASSIFICATION_METADATA.read_bytes())["inputs"]
             if Path(item["path"]).parent==Path(r"C:\Windows\System32")
             and Path(item["path"]).name.casefold() in _system_names}
require(len(_system_names)==len(SYSTEM_PINS)==16,"Exactly sixteen unchanged system-description names required")


def validate_static_records(records):
    require(type(records) is list and len(records)==len(STATIC_PATHS),"Exact static input count required")
    expected=set(STATIC_PATHS);seen=set()
    for record in records:
        require(type(record) is dict and set(record)=={"path","bytes","sha256"},"Strict three-field static pin required")
        path=record["path"]
        require(type(path) is str and path in expected and path not in seen,"Static input outside exact finite path universe")
        require(type(record["bytes"]) is int and 0<=record["bytes"]<=128*1024**2
                and type(record["sha256"]) is str and len(record["sha256"])==64
                and all(c in "0123456789abcdef" for c in record["sha256"]),"Malformed static byte/hash pin")
        seen.add(path)
    require(seen==expected,"Missing exact static input")
    return records


def authority():
    require(EXECUTION_AUTHORITY_SHA!="PENDING_STATIC_AUTHORITY" and bool(STATIC_PATHS),"Census static authority is not frozen")
    require(sha(EXECUTION_AUTHORITY)==EXECUTION_AUTHORITY_SHA,"Exact acyclic authority bytes changed")
    value=json_value(EXECUTION_AUTHORITY.read_bytes())
    require(type(value) is dict and set(value)=={"schema_version","status","mode","executable","verified_build",
        "ABI_eligibility_established","execution_authorized","static_inputs","closure_scope","forbidden_dynamic_dependencies"},
        "Exact static authority schema required")
    require(value["schema_version"]==1 and type(value["schema_version"]) is int
            and value["status"]=="verified_build_static_basis_not_execution_permission"
            and value["mode"]=="--module-census" and value["ABI_eligibility_established"] is False
            and value["execution_authorized"] is False,"Authority cannot grant ABI or execution eligibility")
    validate_static_records(value["static_inputs"])
    require(value["executable"]==next(r for r in value["static_inputs"] if r["path"]==str(EXE))
            and value["verified_build"]==next(r for r in value["static_inputs"] if r["path"]==str(VERIFIED_BUILD))
            and value["executable"]["sha256"]==EXE_SHA and value["verified_build"]["sha256"]==VERIFIED_BUILD_SHA,
            "Exact independently verified census build differs")
    require(sha(VERIFIED_BUILD)==VERIFIED_BUILD_SHA and sha(DESIGN_CONTRACT)==DESIGN_CONTRACT_SHA
            and sha(IMPLEMENTATION_DECISION)==IMPLEMENTATION_DECISION_SHA and sha(q.SDK_SOURCE)==SDK_SHA
            and sdk.NATIVE_EXECUTION_ENABLED is False,"Critical source/build/SDK boundary changed")
    return value


def dynamic_paths():
    return (Path(__file__).resolve(),EXECUTION_AUTHORITY,CHECKER,PURE)


def validate_inputs(records,static):
    validate_static_records(static)
    require(type(records) is list and len(records)==len(static)+len(dynamic_paths()),"Exact combined input count required")
    expected={record["path"]:record for record in static};dynamic={str(path) for path in dynamic_paths()}
    require(not(set(expected)&dynamic),"Static/dynamic authority dependency cycle")
    seen=set()
    for record in records:
        require(type(record) is dict and set(record)=={"path","bytes","sha256"},"Strict three-field combined pin required")
        path=record["path"]
        require(type(path) is str and path in (set(expected)|dynamic) and path not in seen,"Combined input addition/alias/duplicate")
        require(type(record["bytes"]) is int and 0<=record["bytes"]<=128*1024**2
                and type(record["sha256"]) is str and len(record["sha256"])==64
                and all(c in "0123456789abcdef" for c in record["sha256"]),"Malformed combined pin")
        require(path not in expected or record==expected[path],"Static pin differs from reviewed authority")
        seen.add(path)
    require(seen==set(expected)|dynamic,"Missing combined input")
    by_path={r["path"]:r for r in records}
    require(all(by_path[str(path)]==pin(path) for path in dynamic_paths()),"Dynamic self/authority/current evidence changed")
    return records


def collect_inputs():
    static=authority()["static_inputs"]
    # Scope and schema are checked before reading any listed leaf; no reported module path is followed.
    validate_static_records(static)
    for record in static:
        require(pin(record["path"])==record,"Current static input differs: "+record["path"])
    result=static+[pin(path) for path in dynamic_paths()]
    validate_inputs(result,static)
    return result


def wire_schema():
    require(WIRE_SHA is not None and sha(WIRE)==WIRE_SHA,"Census wire schema is not frozen")
    return json_value(WIRE.read_bytes())


def census_validator():
    require(VALIDATOR_SHA is not None and sha(VALIDATOR_SOURCE)==VALIDATOR_SHA,"Census validator is not frozen")
    spec=util.spec_from_file_location("pure_census_validation",VALIDATOR_SOURCE)
    module=util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.validate_census_rows


def census_sealer():
    require(sha(SEALER_SOURCE)==SEALER_SHA,"Census status-only sealer changed")
    spec=util.spec_from_file_location("census_status_only_sealer",SEALER_SOURCE)
    module=util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.make_sealer(sdk)  # Call directly; never replace any SDK function.




def terminal_observer():
    require(sha(TERMINAL_SOURCE)==TERMINAL_SHA,"Terminal observation component changed")
    spec=util.spec_from_file_location("fixed_ABI_terminal_observation_v3",TERMINAL_SOURCE)
    module=util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.CAPTURE_DRAIN_SECONDS==TERMINAL_POLICY["capture_drain_seconds"]
            and module.MAX_CAPTURE_POLLS==TERMINAL_POLICY["maximum_capture_polls"],
            "Terminal observation policy differs")
    return module.observe_terminal

def api_class():
    class FixedCensusKernel32(sdk.Kernel32):
        def __init__(self,config,expected):
            validate_role(config)
            require(not config.get("pure_fixture"),"Synthetic census configuration cannot bind real SDK")
            require(sdk.NATIVE_EXECUTION_ENABLED is False,"Original SDK execution gate changed")
            self.config,self.expected,self.attempted=config,expected,False
            sdk.layouts();C=sdk.C;ptr=C.POINTER
            self.k=C.WinDLL(r"C:\Windows\System32\kernel32.dll",use_last_error=True)
            specs={
                "CreateJobObjectW":([sdk.PVOID,sdk.LPWSTR],sdk.HANDLE),
                "SetInformationJobObject":([sdk.HANDLE,sdk.DWORD,sdk.PVOID,sdk.DWORD],sdk.BOOL),
                "QueryInformationJobObject":([sdk.HANDLE,sdk.DWORD,sdk.PVOID,sdk.DWORD,ptr(sdk.DWORD)],sdk.BOOL),
                "IsProcessInJob":([sdk.HANDLE,sdk.HANDLE,ptr(sdk.BOOL)],sdk.BOOL),
                "CreatePipe":([ptr(sdk.HANDLE),ptr(sdk.HANDLE),ptr(sdk.SECURITY_ATTRIBUTES),sdk.DWORD],sdk.BOOL),
                "SetHandleInformation":([sdk.HANDLE,sdk.DWORD,sdk.DWORD],sdk.BOOL),
                "InitializeProcThreadAttributeList":([sdk.PVOID,sdk.DWORD,sdk.DWORD,ptr(sdk.SIZE_T)],sdk.BOOL),
                "UpdateProcThreadAttribute":([sdk.PVOID,sdk.DWORD,sdk.SIZE_T,sdk.PVOID,sdk.SIZE_T,sdk.PVOID,ptr(sdk.SIZE_T)],sdk.BOOL),
                "DeleteProcThreadAttributeList":([sdk.PVOID],None),
                "CreateProcessW":([sdk.LPWSTR,ptr(sdk.WCHAR),sdk.PVOID,sdk.PVOID,sdk.BOOL,sdk.DWORD,sdk.PVOID,sdk.LPWSTR,ptr(sdk.STARTUPINFOW),ptr(sdk.PROCESS_INFORMATION)],sdk.BOOL),
                "ResumeThread":([sdk.HANDLE],sdk.DWORD),"WaitForSingleObject":([sdk.HANDLE,sdk.DWORD],sdk.DWORD),
                "GetExitCodeProcess":([sdk.HANDLE,ptr(sdk.DWORD)],sdk.BOOL),
                "TerminateProcess":([sdk.HANDLE,sdk.DWORD],sdk.BOOL),"TerminateJobObject":([sdk.HANDLE,sdk.DWORD],sdk.BOOL),
                "CloseHandle":([sdk.HANDLE],sdk.BOOL),"GetProcessId":([sdk.HANDLE],sdk.DWORD),
                "GetThreadId":([sdk.HANDLE],sdk.DWORD),"GetProcessIdOfThread":([sdk.HANDLE],sdk.DWORD),
                "QueryFullProcessImageNameW":([sdk.HANDLE,sdk.DWORD,ptr(sdk.WCHAR),ptr(sdk.DWORD)],sdk.BOOL),
                "GetProcessTimes":([sdk.HANDLE,ptr(sdk.FILETIME),ptr(sdk.FILETIME),ptr(sdk.FILETIME),ptr(sdk.FILETIME)],sdk.BOOL),
                "PeekNamedPipe":([sdk.HANDLE,sdk.PVOID,sdk.DWORD,ptr(sdk.DWORD),ptr(sdk.DWORD),ptr(sdk.DWORD)],sdk.BOOL),
                "ReadFile":([sdk.HANDLE,sdk.PVOID,sdk.DWORD,ptr(sdk.DWORD),sdk.PVOID],sdk.BOOL),
                "CreateFileW":([sdk.LPWSTR,sdk.DWORD,sdk.DWORD,ptr(sdk.SECURITY_ATTRIBUTES),sdk.DWORD,sdk.DWORD,sdk.HANDLE],sdk.HANDLE),
                "GetFileSizeEx":([sdk.HANDLE,ptr(sdk.LARGE_INTEGER)],sdk.BOOL),
                "GetFileInformationByHandleEx":([sdk.HANDLE,sdk.DWORD,sdk.PVOID,sdk.DWORD],sdk.BOOL),
                "GetFinalPathNameByHandleW":([sdk.HANDLE,ptr(sdk.WCHAR),sdk.DWORD,sdk.DWORD],sdk.DWORD)}
            for name,(args,result) in specs.items():
                method=getattr(self.k,name);method.argtypes,method.restype=args,result
        def create_suspended(self,argv,command,environment,cwd,handles,pi,job,creation,event):
            validate_role(self.config)
            require((argv,command)==census_argv(EXE,RUNTIME,Path(self.config["output"])/"execution/child")
                    and environment==sdk.effective_environment(Path(self.config["output"]))
                    and Path(cwd)==Path(self.config["output"]),"Exact detached census-only launch required")
            require(not self.attempted,"census attempt already reserved; no repeat");self.attempted=True
            return super().create_suspended(argv,command,environment,cwd,handles,pi,job,creation,event)
    return FixedCensusKernel32

def exact(actual,expected):
    """Compare JSON structures without bool/int or field-set coercion."""
    if type(actual) is not type(expected):return False
    if isinstance(expected,dict):
        return set(actual)==set(expected) and all(exact(actual[key],value) for key,value in expected.items())
    if isinstance(expected,list):return len(actual)==len(expected) and all(exact(a,b) for a,b in zip(actual,expected))
    return actual==expected

def json_value(raw):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,"Duplicate census JSON key");result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda value:(_ for _ in ()).throw(RuntimeError("Nonfinite census JSON")))

def runtime_pins():
    return {str(RUNTIME/name):dict(path=str(RUNTIME/name),**value) for name,value in RUNTIME_EXPECTED.items()}

def census_argv(exe,runtime,child):
    """Same Windows formatting bounds, independently bound to this new own EXE."""
    require(EXE is not None,"Census executable is not yet independently bound")
    argv=[str(safe(exe)),"--module-census",str(safe(runtime)),str(safe(child,output=True))]
    require(Path(argv[0])==EXE and Path(argv[2])==RUNTIME and len(argv)==4,
            "Exact new census-only executable/runtime/argv required")
    require(all("\0" not in value for value in argv),"NUL argv")
    command=subprocess.list2cmdline(argv)
    require(len(command.encode("utf-16-le"))//2+1<=32767,"Command line cap")
    return argv,command


def inspect_child_artifact_bounds(child):
    """Inspect only own output entries; never follow any reported module path."""
    child=safe(child,output=True)
    allowed={"attempt.json","result.jsonl","result.partial.jsonl","failure.json"}
    entries=list(child.iterdir())
    require(len(entries)<=4 and {item.name for item in entries}<=allowed,"Unexpected census child entry")
    sizes={}
    for item in entries:
        item=safe(item,output=True)
        require(item.is_file(),"Census artifacts must be regular non-reparse files")
        sizes[item.name]=item.stat().st_size
    require(sum(sizes.values())<=LIMITS["child_structured_artifact_bytes"],"All-child structured census byte cap")
    require(sizes.get("attempt.json",0)<=LIMITS["attempt_bytes"]
            and sizes.get("failure.json",0)<=LIMITS["row_bytes"],"Census attempt/failure bound")
    require(sizes.get("attempt.json",0)+sizes.get("failure.json",0)<=LIMITS["attempt_terminal_failure_reserve_bytes"],
            "Census attempt/failure reserve bound")
    return dict(status="observed_sizes_within_bounds",files=sizes,total_bytes=sum(sizes.values()),
                scope="Own structured output sizes; no completeness or ABI eligibility follows")


def validate_child_artifacts(child,config=None,*,expected_pid):
    """Distinct census format; the five-row ABI success parser is never called."""
    child=safe(child,output=True)
    bounded=inspect_child_artifact_bounds(child)
    require(set(bounded["files"])=={"attempt.json","result.jsonl"},"Unexpected/incomplete census success files")
    attempt,result=safe(child/"attempt.json",output=True),safe(child/"result.jsonl",output=True)
    wire=wire_schema()
    require(0<attempt.stat().st_size<=LIMITS["attempt_bytes"] and 0<result.stat().st_size<=LIMITS["result_bytes"],
            "Census positive artifact byte bounds")
    require(exact(json_value(attempt.read_bytes()),wire["artifacts"]["attempt_claim"]),"Census attempt claim")
    raw=result.read_bytes();require(raw.endswith(b"\n"),"Unterminated census result")
    lines=[line+b"\n" for line in raw[:-1].split(b"\n")]
    require(0<len(lines)<=333 and all(0<len(line)-1<=LIMITS["row_bytes"] for line in lines),"Census row count/cap")
    require(EXE is not None,"Census result executable is not independently bound")
    observations=census_validator()([json_value(line) for line in lines],expected_pid=expected_pid,
        expected_executable=str(EXE),expected_runtime=str(RUNTIME),raw_lines=lines,attempt_bytes=attempt.stat().st_size)
    require(observations["status"]==STATUS and observations["ABI_eligibility_established"] is False,
            "Census metadata cannot authorize ABI eligibility")
    return observations


def validate_success_stdout(path):
    path=safe(path,output=True)
    require(path.is_file() and 0<path.stat().st_size<=LIMITS["stream_bytes"],"Census success stdout bounds")
    raw=path.read_bytes()
    require(raw.endswith(b"\n") and exact(json_value(raw),wire_schema()["stdout_success"]),
            "Census stdout must remain metadata-only and match its declared outcome")

def configuration(output,inputs):
    binding=authority();output=safe(output,output=True)
    validate_inputs(inputs,binding["static_inputs"])
    argv,command=census_argv(EXE,RUNTIME,output/"execution/child")
    return dict(schema_version=1,kind="detached_self_module_census_v2",helper=pin(__file__),
        authority=pin(EXECUTION_AUTHORITY),executable=binding["executable"],verified_build=binding["verified_build"],
        runtime_pins=list(runtime_pins().values()),system_candidates=list(SYSTEM_PINS.values()),mode="--module-census",
        output=str(output),argv=argv,command_line=command,environment=sdk.effective_environment(output),
        inputs=inputs,limits=LIMITS,creation_flags=0x0008040C,maximum_attempts=1,automatic_retry=False,
        explicit_target_C_calls=0,target_export_resolution=0,ABI_eligibility_established=False,
        execution_authorized_by_preparation=False,qualified_sdk_sha256=SDK_SHA,
        terminal_component=pin(TERMINAL_SOURCE),terminal_policy=TERMINAL_POLICY,
        status_sealer=pin(SEALER_SOURCE),wire_schema=pin(WIRE),validator=pin(VALIDATOR_SOURCE))


def validate_role(config):
    binding=authority()
    validate_inputs(config["inputs"],binding["static_inputs"])
    require(exact(config,configuration(config["output"],config["inputs"])),"Exact census-only role/configuration required")
    require(config["mode"]=="--module-census" and config["explicit_target_C_calls"]==0
            and config["target_export_resolution"]==0 and config["ABI_eligibility_established"] is False,
            "Census cannot authorize target calls or ABI eligibility")
    return safe(config["output"],output=True)


def execute(config,expected):
    output=validate_role(config);require(not output.exists(),"census output consumed; never restart")
    require(os.name=="nt" and sys.flags.isolated and sys.dont_write_bytecode
            and Path(sys.executable)==q.DEFAULT and metadata.version("asof-target-agents")=="0.3.11",
            "Accepted installed -I -B census parent required")
    started=time.monotonic();parent_end=started+60;child=output/"execution/child"
    journal=None;reservation=dict(owned=False,journal_reserved=False);api=None;owner=None;leases=[]
    sinks=ExitStack();failure=None;failure_object=None;child_start=None;child_end=None;interrupted=False
    captures={name:dict(observed_bytes_at_least=0,retained_bytes=0,truncated=False,eof=False) for name in ("stdout","stderr")}
    report=dict(schema_version=1,status="failed",automatic_retry=False,captures=captures,finalization_errors=[],
        parent_GGUF_reads=0,model_paths_supplied_to_child=False,explicit_bridge_call_policy=dict(
            llama_version=0,llama_model_default_params=0,model_API=0,vocabulary_API=0,backend_init_API=0,
            GGML_registry_API=0,tokenizer_API=0,grammar_API=0),counters_instrumented=False,
        ABI_eligibility_established=False,explicit_target_C_calls=0,target_export_resolution=0,
        dependency_initializers_may_have_effects=True,attempt_reserved=False,call_return_observed=False)
    def event(name,**details):journal.append(name,**details)
    def note_interruption(error,phase):
        nonlocal interrupted
        if isinstance(error,(KeyboardInterrupt,SystemExit)):
            interrupted=True
            report.setdefault("interruptions",[]).append(dict(phase=phase,error_class=type(error).__name__,identity_checked=True))
    try:
        journal=sdk.reserve_parent_journal(output,reservation)
        event("detached_module_census_attempt_reserved",protocol_sha256=expected,limits=LIMITS)
        report["attempt_reserved"]=True
        child.mkdir();write_new(output/"effective-protocol.json",config)
        require(sha(output/"effective-protocol.json")==expected,"census protocol archive differs")
        api=api_class()(config,expected)
        for item in config["inputs"]+[pin(PROTOCOL),pin(output/"effective-protocol.json")]:
            sdk.finite_deadline(parent_end-5);api.read_lease(item,parent_end-5,leases)
        owner=sdk.OwnedLaunch(api,event)
        streams={name:sinks.enter_context((output/(name+".bin")).open("xb")) for name in captures}
        child_start=time.monotonic();child_end=min(child_start+30,parent_end-5)
        check=lambda:sdk.finite_deadline(child_end-2)
        owner.start(config["argv"],config["command_line"],config["environment"],output,check)
        owner.observe_job("running_first","running_or_finished");last=time.monotonic()
        while True:
            check();sdk.capture_poll(owner,captures,streams)
            if api.wait(owner.pi.hProcess,0):break
            if time.monotonic()-last>=.9:owner.observe_job("running_periodic","running_or_finished");last=time.monotonic()
            time.sleep(.01)
        report["returncode"]=api.exit_code(owner.pi.hProcess);report["call_return_observed"]=True
        require(report["returncode"]==0,"census child failed")
    except BaseException as error:
        failure_object=error;failure=dict(error_class=type(error).__name__,error=str(error)[:2048])
        note_interruption(error,"execution")
    finally:
        if not reservation["owned"]:raise failure_object or RuntimeError("No exclusive census output ownership")
        if owner:
            # Preserve the original execution failure, then observe still-open
            # owned handles independently before unchanged Owner cleanup.
            try:
                if interrupted:
                    terminal=dict(status="not_attempted_due_to_preexisting_interruption",complete=False,
                        interrupted=True,exit_observed=False,scope="skipped_due_to_interruption",
                        physical_pipe_EOF_does_not_establish_child_exit=True,observations=dict(
                            job_snapshot=dict(status="not_attempted",reason="Preexisting interruption"),
                            memory_limits_and_peaks=dict(status="not_attempted",reason="Preexisting interruption")),errors=[])
                    report["terminal_observation"]=terminal;report["terminal_observation_errors"]=terminal["errors"]
                else:
                    terminal=terminal_observer()(owner,report,captures,locals().get("streams",{}),
                        sdk=sdk,event=event,work_deadline=min((child_end or parent_end)-2,parent_end-5),
                        drain_seconds=TERMINAL_POLICY["capture_drain_seconds"])
                if terminal.get("interrupted") is True:
                    interrupted=True;report["interrupted_cleanup_only"]=True
                observed=terminal["observations"]
                snapshot=observed["job_snapshot"]
                if terminal["exit_observed"] and snapshot.get("return_observed"):
                    report["final_job_snapshot"]=snapshot["raw"]
                peaks=observed["memory_limits_and_peaks"]
                if peaks.get("return_observed"):report["memory_limits_and_peaks"]=peaks["value"]
                if not terminal["complete"] and failure is None:
                    failure=dict(error_class="TerminalObservationIncomplete",error="See independent terminal outcomes/errors")
            except BaseException as error:
                detail=dict(phase="terminal_observation_unexpected_error",error_class=type(error).__name__,error=str(error)[:512])
                report["finalization_errors"].append(detail);failure=failure or detail
                note_interruption(error,"terminal_observation_binding_or_call")
            if not interrupted and report.get("call_return_observed"):
                try:
                    sdk.finite_deadline(parent_end)
                    report["child_artifact_bounds"]=inspect_child_artifact_bounds(child)
                    sdk.finite_deadline(parent_end)
                except BaseException as error:
                    detail=dict(phase="census_artifact_bounds",error_class=type(error).__name__,error=str(error)[:512])
                    report["finalization_errors"].append(detail);failure=failure or detail
                    note_interruption(error,"census_artifact_bounds")
            if failure is None:
                try:
                    require(report["call_return_observed"] and report["returncode"]==0,"No successful observed census exit")
                    sdk.finite_deadline(parent_end-5)
                    for stream in locals().get("streams",{}).values():
                        stream.flush();os.fsync(stream.fileno())
                    validate_success_stdout(output/"stdout.bin")
                    report["observations"]=validate_child_artifacts(child,config,expected_pid=int(owner.pi.dwProcessId))
                    sdk.finite_deadline(parent_end-5)
                    report["status"]=STATUS
                except BaseException as error:
                    failure=dict(error_class=type(error).__name__,error=str(error)[:2048])
                    note_interruption(error,"child_artifact_validation")
            try:owner.cleanup(min(child_end or parent_end,parent_end))
            except BaseException as error:
                report["owned_cleanup_exception"]=dict(error_class=type(error).__name__,error=str(error)[:512])
                failure=failure or report["owned_cleanup_exception"]
                note_interruption(error,"owned_cleanup")
            if any(row.get("error_class") in ("KeyboardInterrupt","SystemExit") for row in owner.cleanup_errors):
                interrupted=True;report["interruption_recorded_by_unchanged_cleanup_metadata"]=True
            report.update(reaped=owner.reaped,resumption=owner.resumption_record(),cleanup_errors=owner.cleanup_errors)
            if (not owner.reaped or owner.cleanup_errors) and failure is None:
                failure=dict(error_class="OwnedCleanupFailure",error="See retained owned cleanup")
        try:
            try:
                for stream in locals().get("streams",{}).values():stream.flush();os.fsync(stream.fileno())
            finally:sinks.close()
            report["child_full_process_elapsed_seconds"]=None if child_start is None else time.monotonic()-child_start
            require(child_start is None or report["child_full_process_elapsed_seconds"]<=30,"census child including cleanup exceeded30s")
            if api and interrupted:
                report["final_input_recheck"]=dict(status="skipped_due_to_interruption",new_read_leases=0,
                    new_eligibility_claim=False,original_lease_cleanup_still_required=True)
            elif api:
                report["final_input_recheck"]=dict(status="in_progress",new_read_leases=0,closed_recheck_leases=0,outcomes=[])
                for item in config["inputs"]+[pin(PROTOCOL),pin(output/"effective-protocol.json")]:
                    report["final_input_recheck"]["new_read_leases"]+=1
                    outcome=dict(path=item["path"],read_lease_reserved=True,return_observed=False,close_return_observed=False)
                    report["final_input_recheck"]["outcomes"].append(outcome)
                    record=api.read_lease(item,parent_end,leases);outcome.update(return_observed=True,handle=record["handle"])
                    record["final_recheck_close_attempted"]=True
                    try:
                        api.close(record["handle"]);record["closed"]=True;record["final_recheck_close_return_observed"]=True
                        outcome["close_return_observed"]=True;report["final_input_recheck"]["closed_recheck_leases"]+=1
                    except BaseException as error:
                        detail=dict(phase="final_input_recheck_close",error_class=type(error).__name__,error=str(error)[:512])
                        record["cleanup_errors"].append(detail);record["final_recheck_close_return_observed"]=False
                        outcome["close_error"]=detail
                        report["finalization_errors"].append(dict(path=record["path"],handle=record["handle"],**detail));raise
                report["final_input_recheck"]["status"]="completed"
            else:
                report["final_input_recheck"]=dict(status="not_attempted",reason="No SDK API instance",new_read_leases=0)
            sdk.finite_deadline(parent_end)
        except BaseException as error:
            detail=dict(phase="final_input_recheck_or_cleanup",error_class=type(error).__name__,error=str(error)[:2048])
            report["finalization_errors"].append(detail);failure=failure or detail
            note_interruption(error,"final_input_recheck_or_cleanup")
            recheck=report.setdefault("final_input_recheck",dict(status="not_attempted",new_read_leases=0))
            if recheck["status"]=="in_progress":
                recheck.update(status="interrupted" if isinstance(error,(KeyboardInterrupt,SystemExit)) else "failed",error=detail)
            elif recheck["status"]=="not_attempted":recheck["reason"]="Earlier finalization failure prevented input recheck"
        try:
            if failure:
                report.update(status="failed",failure=failure)
                if not (output/"failure.json").exists():write_new(output/"failure.json",dict(authoritative=True,automatic_retry=False,**failure))
            try:
                if journal:event("detached_module_census_terminal",status=report["status"],failure=failure)
            finally:
                if journal:journal.close()
            report["lease_ownership"]=leases;report["elapsed_before_early_receipt_seconds"]=time.monotonic()-started
            write_new(output/"parent-report.json",report);sdk.finite_deadline(parent_end)
            outputs={}
            for path in sorted(output.rglob("*")):
                sdk.finite_deadline(parent_end)
                if path.is_file():outputs[path.relative_to(output).as_posix()]={key:pin(path)[key] for key in ("bytes","sha256")}
            write_new(output/"receipt.json",dict(schema_version=1,status=report["status"],outputs=outputs,
                protocol_sha256=expected,failure_veto="Every authoritative failure marker or missing/failed terminal seal vetoes"))
            sdk.finite_deadline(parent_end)
        except BaseException as error:
            detail=dict(phase="terminal_publication",error_class=type(error).__name__,error=str(error)[:512])
            report["finalization_errors"].append(detail);failure=failure or detail
            try:write_new(output/"terminal-publication-error.json",dict(authoritative=True,automatic_retry=False,
                publication_error=detail,primary_failure=failure,finalization_errors=report["finalization_errors"]))
            except BaseException:pass
            if not (output/"failure.json").exists():
                try:write_new(output/"failure.json",dict(authoritative=True,automatic_retry=False,**failure))
                except BaseException:pass
        finally:
            terminal=SEAL_POST_LEASE_CLEANUP(output,api,leases,failure,report["status"],started,parent_end)
            report["status"]=terminal["status"];report["terminal_seal"]=pin(output/"terminal-seal.json")
    require(sdk.NATIVE_EXECUTION_ENABLED is False,"Qualified detached SDK gate changed")
    return report

def prepare():
    require(os.name=="nt" and sys.flags.isolated and sys.dont_write_bytecode
            and Path(sys.executable)==q.DEFAULT and metadata.version("asof-target-agents")=="0.3.11",
            "Pinned accepted -I -B preparation parent required")
    require(not PROTOCOL.exists() and not PREPARATION.exists(),"Census preparation already consumed")
    proof=json_value(PURE.read_bytes())
    require(proof["status"]=="passed" and proof["helper_sha256"]==sha(__file__)
            and proof["checker_sha256"]==sha(CHECKER) and proof["actual_children"]==0
            and proof["actual_SDK_constructors"]==0,"Exact current acyclic-binding pure proof required")
    inputs=collect_inputs()
    output=safe(ROOT/"data/cache"/("r09-self-module-census-v1-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")),output=True)
    require(not output.exists(),"Exclusive future census output exists")
    config=configuration(output,inputs);validate_role(config)
    with PROTOCOL.open("xb") as stream:stream.write(canonical(config)+b"\n");stream.flush();os.fsync(stream.fileno())
    write_new(PREPARATION,dict(schema_version=1,status="prepared_census_only_not_execution_authority",
        helper=pin(__file__),authority=pin(EXECUTION_AUTHORITY),protocol=pin(PROTOCOL),static_inputs=len(STATIC_PATHS),
        dynamic_inputs=len(dynamic_paths()),inputs=len(inputs),output=str(output),output_absent=not output.exists(),
        actual_SDK_constructors=0,actual_children=0,SDK_general_gate=False,execution_authorized=False))
    print(json.dumps(dict(status="prepared_census_only_not_execution_authority",helper_sha256=sha(__file__),
        protocol_sha256=sha(PROTOCOL),static_inputs=len(STATIC_PATHS),inputs=len(inputs),output=str(output))))


# Trusted declaration-time binding, before any attempted execution/interruption.
# Only own Python source is loaded; make_sealer reads SDK functions without mutating them.
SEAL_POST_LEASE_CLEANUP=census_sealer()


if __name__=="__main__":
    if sys.argv[1:]==["--prepare"]:prepare()
    else:raise SystemExit("Preparation-only CLI; actual constructor/dispatch needs a separate exact root decision and audited driver")

