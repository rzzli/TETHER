"""Trusted-platform ABI parent v2; exact acyclic runtime metadata preparation only.

Existing typed child only: --abi RUNTIME CHILD_OUTPUT. Original SDK gates remain
False; no prepare_config, compiler, backend/registry/model/vocabulary/grammar path.
Preparation grants no execution permission. Only a separately reviewed root driver and exact once-only decision may call execute. The original SDK gate remains false.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from importlib import metadata, util
import json
import os
from pathlib import Path
import sys
import subprocess  # Windows list2cmdline only; never Popen.
import time
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASIS=HERE/"qualify_detached_native_worker_v1.py"
BASIS_SHA="6be0634f9bc9ea89eff1e54cbb963c355853eacc9ad9bbe63496b2f1aa50fea9"
def sha(path):
    with Path(path).open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
if sha(BASIS)!=BASIS_SHA:raise RuntimeError("Detached qualifier source basis changed")
spec=util.spec_from_file_location("qualified_detached_basis_for_fixed_abi",BASIS)
q=util.module_from_spec(spec);spec.loader.exec_module(q)
sdk=q.load_sdk()  # Declaration import only; original Kernel32 constructor stays disabled.
safe,pin,canonical,write_new,require=q.safe,q.pin,q.canonical,q.write_new,q.require
SDK_SHA="3bfac51893b60221728ac915516c5e816c0cfc5a82899f5871f7931469d7fdfd"
QUALIFICATION=HERE/"DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json"
QUALIFICATION_SHA="7f184e9b4d04019c6fba3bc661dabe241b7ef6a2a0ee8c713711eeeae12eb961"
EXE=Path('D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-build-v2-20261029T024601Z\\typed_public_c_recognizer_abi.exe')
EXE_SHA='2feffe29d916f9345067d9458714525eb73a2554824f3567383856562c2b2464'
RUNTIME=ROOT/"data/cache/approved-native-mirror-20261028T004531Z/runtime"
PROTOCOL=HERE/'TRUSTED-PLATFORM-ABI-EXECUTION-PROTOCOL-v1.json'
EXECUTION_AUTHORIZED=False
CONTRACT=HERE/'TRUSTED-SYSTEM32-ABI-CONTRACT-v2.json'
CONTRACT_SHA='f32dcfa3dff922937691b85129d8db7cfabf26e123fdc829027eff6e080bebc8'
TERMINAL_SOURCE=HERE/"detached_abi_terminal_observation_v3.py"
TERMINAL_SHA="4ea2c429a8e4d512d42ae449fc3764550421ae8cf6491e3866c8322880d5c96c"
POLICY_SOURCE=HERE/"trusted_system32_module_policy_v1.py"
POLICY_SOURCE_SHA="77e39b3bb82fb83049aba9956da0251b4a8d914f167dc6d6512d554ad7bfb3a8"
POLICY_ID="trusted-System32-platform-v1"
POLICY_SHA="807995f6061d7a2c85144c58668fc2e4ecb79a4fb51d462e43d0a8dfc586d589"
TERMINAL_POLICY=dict(capture_drain_seconds=0.25,maximum_capture_polls=64,
    physical_pipe_EOF_is_not_child_exit=True,unknown_creation_is_not_final=True,
    skip_new_observations_and_input_rechecks_after_interruption=True,late_returned_bytes_retained=True)
LIMITS=dict(parent_seconds=60,child_seconds=30,child_cleanup_reserved_seconds=2,finalization_reserved_seconds=5,
    process_and_job_commit_bytes=268435456,active_processes=1,maximum_children=1,stream_bytes=65536,
    maximum_job_snapshots=40,job_pid_capacity=16,attempt_bytes=4096,result_bytes=4194304,row_bytes=65536)
RUNTIME_EXPECTED={
    "libomp.dll":dict(bytes=768000,sha256="a12116ba72d1d6820407cf30be23da04ce79d6bb8a71a5ee71759c5a1faa6f1c"),
    "ggml-base.dll":dict(bytes=803840,sha256="84e3057e6fe2c581a9d194d27e5510b1a71723074e01dfb9b34926e4d5af52f3"),
    "ggml.dll":dict(bytes=78848,sha256="2a49a0f2d3c58b182bfa5267950cef2e4f3378a12e9ebbc6b36554bf5ca016ba"),
    "llama.dll":dict(bytes=3581952,sha256="166e8de1bd07573dc0f51ab1f429ab5df0d08492e7302bbe41a39014248f5e6d")}



EXECUTION_AUTHORITY=HERE/'TRUSTED-PLATFORM-ABI-STATIC-AUTHORITY-v1.json'
EXECUTION_AUTHORITY_SHA='130ab496826afcef74236bfddae5386b267a7c788fe4496682c3f57338c0f8d2'
VERIFIED_BUILD=HERE/'TRUSTED-PLATFORM-BUILD-RESULT-VERIFICATION-v2.json'
VERIFIED_BUILD_SHA='057c0fb212a9b7488f71a442182808c0f728c0b54f7a0fc83eaa13b400e51580'
CHECKER=HERE/'check_platform_abi_binding_v2.py'
PURE=HERE/'TRUSTED-PLATFORM-ABI-BINDING-PURE-PROOF-v2.json'
PREPARATION=ROOT/'data/cache/r09-trusted-platform-ABI-preparation-v2-20261029.json'
STATIC_PATHS=('C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um\\fileapi.h', 'C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um\\jobapi2.h', 'C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um\\namedpipeapi.h', 'C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um\\processthreadsapi.h', 'C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um\\winbase.h', 'C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um\\winnt.h', 'C:\\Users\\zzric\\AppData\\Roaming\\uv\\python\\cpython-3.11.15-windows-x86_64-none\\python.exe', 'C:\\Windows\\System32\\advapi32.dll', 'C:\\Windows\\System32\\bcrypt.dll', 'C:\\Windows\\System32\\bcryptprimitives.dll', 'C:\\Windows\\System32\\cryptbase.dll', 'C:\\Windows\\System32\\cryptsp.dll', 'C:\\Windows\\System32\\kernel32.dll', 'C:\\Windows\\System32\\kernelbase.dll', 'C:\\Windows\\System32\\msvcp140.dll', 'C:\\Windows\\System32\\msvcrt.dll', 'C:\\Windows\\System32\\ntdll.dll', 'C:\\Windows\\System32\\psapi.dll', 'C:\\Windows\\System32\\rpcrt4.dll', 'C:\\Windows\\System32\\sechost.dll', 'C:\\Windows\\System32\\ucrtbase.dll', 'C:\\Windows\\System32\\vcruntime140.dll', 'C:\\Windows\\System32\\vcruntime140_1.dll', 'D:\\Projects\\drug_target_agents\\data\\cache\\approved-native-mirror-20261028T004531Z\\runtime\\ggml-base.dll', 'D:\\Projects\\drug_target_agents\\data\\cache\\approved-native-mirror-20261028T004531Z\\runtime\\ggml.dll', 'D:\\Projects\\drug_target_agents\\data\\cache\\approved-native-mirror-20261028T004531Z\\runtime\\libomp.dll', 'D:\\Projects\\drug_target_agents\\data\\cache\\approved-native-mirror-20261028T004531Z\\runtime\\llama.dll', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-grammar-source-20261028T020623Z\\sources\\include\\llama.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-followup-source-20261028T164431Z\\sources\\ggml\\include\\ggml-alloc.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-source-20261028T161554Z\\sources\\ggml\\include\\ggml-backend.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-source-20261028T161554Z\\sources\\ggml\\include\\ggml-cpu.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-source-20261028T161554Z\\sources\\ggml\\include\\ggml-opt.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-source-20261028T161554Z\\sources\\ggml\\include\\ggml.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-source-20261028T161554Z\\sources\\ggml\\include\\gguf.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-build-v2-20261029T024601Z\\build-report.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-build-v2-20261029T024601Z\\post-lease-cleanup.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-build-v2-20261029T024601Z\\receipt.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-build-v2-20261029T024601Z\\terminal-seal.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-build-v2-20261029T024601Z\\typed_public_c_recognizer_abi.exe', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-preparation-v2-20261029T024601Z\\headers\\ggml-alloc.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-preparation-v2-20261029T024601Z\\headers\\ggml-backend.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-preparation-v2-20261029T024601Z\\headers\\ggml-cpu.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-preparation-v2-20261029T024601Z\\headers\\ggml-opt.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-preparation-v2-20261029T024601Z\\headers\\ggml.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-preparation-v2-20261029T024601Z\\headers\\gguf.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-preparation-v2-20261029T024601Z\\headers\\llama.h', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-preparation-v2-20261029T024601Z\\recognizer_runtime_pins.hpp', 'D:\\Projects\\drug_target_agents\\data\\cache\\r09-trusted-platform-bridge-preparation-v2-20261029T024601Z\\typed_public_c_recognizer.cpp', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\dist\\asof_target_agents-0.3.11-py3-none-any.whl', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\__init__.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\__main__.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\agents.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\__init__.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\__main__.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\core.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\interpretation.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\paths.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\restore.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\archive\\semantic_dependencies.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\artifacts.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\atomic.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\chrono.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\cli.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\contracts.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\case.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\evidence.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\future.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\replay.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\scorer.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\snapshot.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\case.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\evidence.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\future.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\raw-inputs.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\replay.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\scorer.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\demo\\v2\\snapshot.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\evaluation.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\features.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\ingest.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\journal.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\ledger.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\local_model.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\maintenance.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\provenance.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\retrieval.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\scorer.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\semantics.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\serde.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\__init__.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\__main__.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\authority_four_arm.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\baseline_smoke.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\baselines.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\collected_source.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\diagnostic.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\diagnostic_codec.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\diagnostic_resources.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\fixed_evidence.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\fixed_evidence_smoke.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\interpretation_generation.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\interpretation_grammar.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\interpretation_interface.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\native.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\native_accounting.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\native_diagnostic.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\native_interpretation.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\native_mode.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\preparation_payloads.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\process.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\proofs.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\recorded.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\authority-four-arm-stimuli-v1.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\diagnostic-templates-v1.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\fixed-evidence-plan-v1.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\native-server-v2.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\retrieval-corpus-v1.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\retrieval-policy-v1.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\retrieval-recorded-stimuli-v1.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\simplified-response-schema-v1.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\simplified-response-schema-v2.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\synthetic-context-v1.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\synthetic-orientation-v1.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\resources\\tokenizer-assets-v1.json', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\retrieval_preparation.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\retrieval_smoke.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\session.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\source_preparation.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\source_rows.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\stable_read.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\token_capacity.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\study\\tokenization.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\wire.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof\\workflow.py', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof_target_agents-0.3.11.dist-info\\entry_points.txt', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof_target_agents-0.3.11.dist-info\\METADATA', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Lib\\site-packages\\asof_target_agents-0.3.11.dist-info\\WHEEL', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\pyvenv.cfg', 'D:\\Projects\\drug_target_agents\\data\\cache\\recovery-step9-generation-wheel-20261028\\environment\\Scripts\\python.exe', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-generation-contract-20261028\\acceptance.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-generation-contract-20261028\\WHEEL-ENVIRONMENTS.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\abi_parent_launch_draft_v3.py', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\BRIDGE-SYMBOL-OWNERS-PURE-PROOF-v5.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\check_platform_abi_parent_v3.py', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\check_trusted_system32_module_policy_v1.py', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\DETACHED-ABI-TERMINAL-COMPONENT-PROOF-v3.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\DETACHED-NATIVE-QUALIFICATION-PROTOCOL-v1.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\DETACHED-POLICY-CONTRACT-v1.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\DETACHED-POLICY-DESIGN-v1.md', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\detached_abi_terminal_observation_v3.py', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\detached_parent_launch_draft_v1.py', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\HEADER-CLOSURE-FOLLOWUP.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\POST-CENSUS-PLATFORM-POLICY-ROOT-DECISION-v1.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\prepare_platform_abi_binding_v3.py', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\qualify_detached_native_worker_v1.py', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\run_detached_abi_observation_v6.py', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\run_platform_abi_observation_v1.py', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-PLATFORM-BUILD-PEER-REVIEW-v2.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-PLATFORM-BUILD-PROTOCOL-v2.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-PLATFORM-BUILD-RESULT-VERIFICATION-v2.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-PLATFORM-BUILD-ROOT-DECISION-v2.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-SYSTEM32-ABI-CONTRACT-v1.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-SYSTEM32-ABI-CONTRACT-v2.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-SYSTEM32-ABI-PARENT-PURE-PROOF-v3.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-SYSTEM32-CHILD-SOURCE-PEER-REVIEW-v1.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-SYSTEM32-CHILD-SOURCE-PURE-PROOF-v1.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-SYSTEM32-MODULE-POLICY-v1.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-SYSTEM32-MODULE-VECTORS-v1.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-SYSTEM32-PARENT-MATCHER-PEER-REVIEW-v1.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\TRUSTED-SYSTEM32-PARENT-MATCHER-PURE-PROOF-v1.json', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\trusted_system32_module_policy_v1.py', 'D:\\Projects\\drug_target_agents\\planning\\review-assets\\recovery-step9-native-recognition-20261028\\typed_public_c_recognizer_platform_v1.cpp')


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


def authority():
    require(bool(STATIC_PATHS) and sha(EXECUTION_AUTHORITY)==EXECUTION_AUTHORITY_SHA,"Exact acyclic static authority changed")
    value=json_value(EXECUTION_AUTHORITY.read_bytes())
    require(type(value) is dict and set(value)=={"schema_version","status","mode","executable","verified_build","ABI_contract",
        "module_policy_id","module_policy_sha256","ABI_eligibility_established","execution_authorized","static_inputs","closure_scope","forbidden_dynamic_dependencies"},
        "Exact trusted-platform static authority schema required")
    require(type(value["schema_version"]) is int and value["schema_version"]==1
        and value["status"]=="verified_build_static_basis_not_execution_permission" and value["mode"]=="--abi"
        and value["execution_authorized"] is False and value["ABI_eligibility_established"] is False,
        "Static basis cannot grant execution or ABI eligibility")
    validate_static_records(value["static_inputs"])
    by_path={r["path"]:r for r in value["static_inputs"]}
    require(value["executable"]==by_path[str(EXE)] and value["executable"]["sha256"]==EXE_SHA
        and value["verified_build"]==by_path[str(VERIFIED_BUILD)] and value["verified_build"]["sha256"]==VERIFIED_BUILD_SHA
        and value["ABI_contract"]==by_path[str(CONTRACT)] and value["ABI_contract"]["sha256"]==CONTRACT_SHA,
        "Verified executable/build/contract static bindings differ")
    require(value["module_policy_id"]==POLICY_ID and value["module_policy_sha256"]==POLICY_SHA,
        "Static module policy fingerprint differs")
    require(sha(VERIFIED_BUILD)==VERIFIED_BUILD_SHA and sha(CONTRACT)==CONTRACT_SHA
        and sha(q.SDK_SOURCE)==SDK_SHA and sdk.NATIVE_EXECUTION_ENABLED is False,"Critical build/contract/SDK boundary changed")
    contract=json_value(CONTRACT.read_bytes());build=json_value(VERIFIED_BUILD.read_bytes())
    require(contract["verified_bridge_executable"]==value["executable"]==build["executable"]
        and contract["verified_build_proof"]==value["verified_build"]
        and build["status"]=="VERIFIED_trusted_platform_bridge_compiled_recognition_disabled_NOT_EXECUTED"
        and contract["module_policy_id"]==POLICY_ID and contract["module_policy_sha256"]==POLICY_SHA
        and contract["execution_authorized"] is False,"Current bound ABI contract differs")
    return dict(contract,static_inputs=value["static_inputs"])



def policy_matcher():
    require(sha(POLICY_SOURCE)==POLICY_SOURCE_SHA,"Frozen mathematical module policy changed")
    spec=util.spec_from_file_location("trusted_platform_ABI_pure_policy_v1",POLICY_SOURCE)
    module=util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.POLICY_ID==POLICY_ID and module.POLICY_SHA256==POLICY_SHA,"Policy semantic fingerprint differs")
    return module


def terminal_observer():
    require(sha(TERMINAL_SOURCE)==TERMINAL_SHA,"Terminal observation component changed")
    spec=util.spec_from_file_location("fixed_ABI_terminal_observation_v3",TERMINAL_SOURCE)
    module=util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.CAPTURE_DRAIN_SECONDS==TERMINAL_POLICY["capture_drain_seconds"]
            and module.MAX_CAPTURE_POLLS==TERMINAL_POLICY["maximum_capture_polls"],
            "Terminal observation policy differs")
    return module.observe_terminal


def api_class():
    class FixedABIKernel32(sdk.Kernel32):
        def __init__(self,config,expected):
            validate_role(config)
            require(not config.get("pure_fixture"),"Synthetic ABI configuration cannot bind real SDK")
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
            require((argv,command)==abi_argv(EXE,RUNTIME,Path(self.config["output"])/"execution/child")
                    and environment==sdk.effective_environment(Path(self.config["output"]))
                    and Path(cwd)==Path(self.config["output"]),"Exact detached ABI-only launch required")
            require(not self.attempted,"ABI attempt already reserved; no repeat");self.attempted=True
            return super().create_suspended(argv,command,environment,cwd,handles,pi,job,creation,event)
    return FixedABIKernel32


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
            require(key not in result,"Duplicate ABI JSON key");result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda value:(_ for _ in ()).throw(RuntimeError("Nonfinite ABI JSON")))


def runtime_pins():
    return {str(RUNTIME/name):dict(path=str(RUNTIME/name),**value) for name,value in RUNTIME_EXPECTED.items()}


def validate_modules(rows):
    require(EXE is not None,"Unbound ABI context is not an approved self executable")
    return policy_matcher().match_modules(rows,expected_self=str(EXE),expected_runtime=str(RUNTIME))


def validate_child_rows(rows,*,contract,expected_self,expected_runtime):
    """Pure complete-wire validation using externally prevalidated fixed native context.

    Context identity must come from live original-path native leases in a future
    qualified parent, never from child-supplied verified flags or platform paths.
    """
    require(type(rows) is list and len(rows)==5,"ABI row count differs")
    require([row.get("event") if type(row) is dict else None for row in rows]==contract["child_artifacts"]["result_events"],
            "ABI event sequence differs")
    require(exact(rows[0],dict(event="before_explicit_required_OpenMP_dependency_load",dependency_native_initialization_possible=True)),
            "OpenMP initialization row differs")
    require(set(rows[1])=={"event","modules","layouts","module_policy_id","module_policy_sha256"} and exact(rows[1]["layouts"],contract["expected_layouts"]),
            "Compiled x64 layout fields/types/offsets differ")
    require(type(rows[1]["module_policy_id"]) is str and rows[1]["module_policy_id"]==POLICY_ID
            and type(rows[1]["module_policy_sha256"]) is str and rows[1]["module_policy_sha256"]==POLICY_SHA,
            "Compiled module policy identifier/fingerprint differs")
    classified=policy_matcher().match_modules(rows[1]["modules"],expected_self=expected_self,expected_runtime=expected_runtime)
    observed=rows[2];require(set(observed)=={"event","version","defaults","no_backend_or_model_call_so_far"},"Typed observation fields differ")
    version=observed["version"]
    require(type(version) is str and 1<=len(version)<=255 and all(32<=ord(char)<=126 for char in version),"Invalid first ABI version observation")
    require(exact(observed["defaults"],contract["expected_defaults"])
            and observed["no_backend_or_model_call_so_far"] is True,"Typed defaults/scope differ")
    require(exact(rows[3],dict(event="abi_observations_returned",version_expected_previously_known=False,
        backend_init_called=False,registry_called=False,model_called=False,
        scope="typed version/defaults observation; independent ABI acceptance pending")),"ABI explicit-call scope differs")
    require(set(rows[4])=={"event","mode","elapsed_ms","parent_qualification_required"}
            and rows[4]["mode"]=="--abi" and type(rows[4]["elapsed_ms"]) is int
            and 0<=rows[4]["elapsed_ms"]<=30000 and rows[4]["parent_qualification_required"] is True,
            "ABI completion/time scope differs")
    return dict(version=version,version_expected_previously_known=False,defaults=observed["defaults"],
        layouts=rows[1]["layouts"],raw_modules=rows[1]["modules"],module_classification=classified,result_rows=5,
        module_policy_id=POLICY_ID,module_policy_sha256=POLICY_SHA,
        independent_ABI_acceptance="pending",scientific_validation="not_established",
        module_inventory_scope="Reported before explicit version/default calls; trusted platform context, not image authentication or lifetime attestation")


def validate_child_artifacts(child,config=None):
    """Strict data-only validator; no DLL, process, model or archived code call."""
    contract=authority();child=safe(child,output=True)
    require({path.name for path in child.iterdir()}=={"attempt.json","result.jsonl"},"Unexpected/incomplete ABI child files")
    attempt,result=safe(child/"attempt.json",output=True),safe(child/"result.jsonl",output=True)
    require(attempt.is_file() and result.is_file(),"ABI artifacts must be regular non-reparse files")
    require(0<attempt.stat().st_size<=4096 and 0<result.stat().st_size<=4194304,"ABI child file cap")
    require(exact(json_value(attempt.read_bytes()),contract["child_artifacts"]["exact_attempt_claim"]),"ABI child attempt claim")
    raw=result.read_bytes();require(raw.endswith(b"\n"),"Unterminated ABI result")
    lines=raw.split(b"\n")[:-1];require(len(lines)==5 and all(0<len(line)<=65536 for line in lines),"ABI row count/cap")
    rows=[json_value(line) for line in lines]

    require(EXE is not None,"Unbound ABI executable context")
    return validate_child_rows(rows,contract=contract,expected_self=str(EXE),expected_runtime=str(RUNTIME))


def abi_argv(exe,runtime,child):
    """Same Windows formatting bounds, independently bound to this new own EXE."""
    argv=[str(safe(exe)),"--abi",str(safe(runtime)),str(safe(child,output=True))]
    require(Path(argv[0])==EXE and Path(argv[2])==RUNTIME and len(argv)==4,
            "Exact new ABI-only executable/runtime/argv required")
    require(all("\0" not in value for value in argv),"NUL argv")
    command=subprocess.list2cmdline(argv)
    require(len(command.encode("utf-16-le"))//2+1<=32767,"Command line cap")
    return argv,command


def configuration(output,inputs):
    binding=authority();output=safe(output,output=True);validate_inputs(inputs,binding["static_inputs"])
    argv,command=abi_argv(EXE,RUNTIME,output/"execution/child")
    return dict(schema_version=1,kind="detached_trusted_platform_ABI_observation_v1",helper=pin(__file__),
        authority=pin(EXECUTION_AUTHORITY),executable=binding["verified_bridge_executable"],verified_build=binding["verified_build_proof"],
        contract_sha256=CONTRACT_SHA,runtime_pins=list(runtime_pins().values()),mode="--abi",module_policy_id=POLICY_ID,
        module_policy_sha256=POLICY_SHA,platform_image_authentication="not_established",reported_platform_path_filesystem_operations=0,
        output=str(output),argv=argv,command_line=command,environment=sdk.effective_environment(output),inputs=inputs,
        limits=LIMITS,creation_flags=0x0008040C,maximum_attempts=1,automatic_retry=False,
        explicit_target_calls=["llama_version","llama_model_default_params"],recognition_enabled=False,
        no_model_or_CPU_paths_supplied=True,initializer_effects_instrumented=False,expected_version="",
        version_expected_previously_known=False,execution_authorized_by_preparation=False,
        qualified_sdk_sha256=SDK_SHA,qualified_harmless_sha256=QUALIFICATION_SHA,terminal_component=pin(TERMINAL_SOURCE),terminal_policy=TERMINAL_POLICY)



def validate_role(config):
    binding=authority();validate_inputs(config["inputs"],binding["static_inputs"])
    require(exact(config,configuration(config["output"],config["inputs"])),"Exact trusted-platform ABI-only role/configuration required")
    return safe(config["output"],output=True)



def execute(config,expected):
    output=validate_role(config);require(not output.exists(),"ABI output consumed; never restart")
    require(os.name=="nt" and sys.flags.isolated and sys.dont_write_bytecode
            and Path(sys.executable)==q.DEFAULT and metadata.version("asof-target-agents")=="0.3.11",
            "Accepted installed -I -B ABI parent required")
    started=time.monotonic();parent_end=started+60;child=output/"execution/child"
    journal=None;reservation=dict(owned=False,journal_reserved=False);api=None;owner=None;leases=[]
    sinks=ExitStack();failure=None;failure_object=None;child_start=None;child_end=None;interrupted=False
    captures={name:dict(observed_bytes_at_least=0,retained_bytes=0,truncated=False,eof=False) for name in ("stdout","stderr")}
    report=dict(schema_version=1,status="failed",automatic_retry=False,captures=captures,finalization_errors=[],
        parent_GGUF_reads=0,model_paths_supplied_to_child=False,explicit_bridge_call_policy=dict(
            llama_version=1,llama_model_default_params=1,model_API=0,vocabulary_API=0,backend_init_API=0,
            GGML_registry_API=0,tokenizer_API=0,grammar_API=0),counters_instrumented=False,
        dependency_initializers_may_have_effects=True,attempt_reserved=False,call_return_observed=False)
    def event(name,**details):journal.append(name,**details)
    def note_interruption(error,phase):
        nonlocal interrupted
        if isinstance(error,(KeyboardInterrupt,SystemExit)):
            interrupted=True
            report.setdefault("interruptions",[]).append(dict(phase=phase,error_class=type(error).__name__,identity_checked=True))
    try:
        journal=sdk.reserve_parent_journal(output,reservation)
        event("detached_ABI_attempt_reserved",protocol_sha256=expected,limits=LIMITS)
        report["attempt_reserved"]=True
        child.mkdir();write_new(output/"effective-protocol.json",config)
        require(sha(output/"effective-protocol.json")==expected,"ABI protocol archive differs")
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
        require(report["returncode"]==0,"ABI child failed")
    except BaseException as error:
        failure_object=error;failure=dict(error_class=type(error).__name__,error=str(error)[:2048])
        note_interruption(error,"execution")
    finally:
        if not reservation["owned"]:raise failure_object or RuntimeError("No exclusive ABI output ownership")
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
            if failure is None:
                try:
                    require(report["call_return_observed"] and report["returncode"]==0,"No successful observed ABI exit")
                    report["observations"]=validate_child_artifacts(child,config)
                    report["status"]="ABI_observations_retained_independent_qualification_pending"
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
            require(child_start is None or report["child_full_process_elapsed_seconds"]<=30,"ABI child including cleanup exceeded30s")
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
                if journal:event("detached_ABI_terminal",status=report["status"],failure=failure)
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
            terminal=sdk.seal_post_lease_cleanup(output,api,leases,failure,report["status"],started,parent_end)
            report["status"]=terminal["status"];report["terminal_seal"]=pin(output/"terminal-seal.json")
    require(sdk.NATIVE_EXECUTION_ENABLED is False,"Qualified detached SDK gate changed")
    return report


def prepare():
    require(os.name=="nt" and sys.flags.isolated and sys.dont_write_bytecode
            and Path(sys.executable)==q.DEFAULT and metadata.version("asof-target-agents")=="0.3.11",
            "Pinned accepted -I -B preparation parent required")
    require(not PROTOCOL.exists() and not PREPARATION.exists(),"Trusted-platform ABI preparation already consumed")
    proof=json_value(PURE.read_bytes())
    require(proof["status"]=="passed" and proof["helper_sha256"]==sha(__file__)
            and proof["checker_sha256"]==sha(CHECKER) and proof["actual_children"]==0
            and proof["actual_SDK_constructors"]==0,"Exact current acyclic-binding pure proof required")
    inputs=collect_inputs()
    output=safe(ROOT/"data/cache"/("r09-trusted-platform-ABI-observation-v1-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")),output=True)
    require(not output.exists(),"Exclusive future trusted-platform ABI output exists")
    config=configuration(output,inputs);validate_role(config)
    with PROTOCOL.open("xb") as stream:stream.write(canonical(config)+b"\n");stream.flush();os.fsync(stream.fileno())
    write_new(PREPARATION,dict(schema_version=1,status="prepared_ABI_only_not_execution_authority",
        helper=pin(__file__),authority=pin(EXECUTION_AUTHORITY),protocol=pin(PROTOCOL),static_inputs=len(STATIC_PATHS),
        dynamic_inputs=len(dynamic_paths()),inputs=len(inputs),output=str(output),output_absent=not output.exists(),
        actual_SDK_constructors=0,actual_children=0,SDK_general_gate=False,execution_authorized=False))
    print(json.dumps(dict(status="prepared_ABI_only_not_execution_authority",helper_sha256=sha(__file__),
        protocol_sha256=sha(PROTOCOL),static_inputs=len(STATIC_PATHS),inputs=len(inputs),output=str(output))))


if __name__=="__main__":
    if sys.argv[1:]==["--prepare"]:prepare()
    else:raise SystemExit("Preparation-only CLI; constructor/dispatch requires separate exact root decision and audited driver")
