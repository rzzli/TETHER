"""Preserve the first failed harness; create a corrected fresh probe helper."""
from pathlib import Path

here=Path(__file__).resolve().parent
text=(here/'probe_installed_toolchain.py').read_text(encoding='utf-8')
assert (here/'TOOLCHAIN-LOCAL-PROBE.json').is_file()
assert "run('linker-version-help', [linker, '/?'], build_env)" in text
text=text.replace("'TOOLCHAIN-LOCAL-PROBE.json'","'TOOLCHAIN-LOCAL-PROBE-v2.json'")
text=text.replace("for name in ('c1.dll', 'c1xx.dll', 'c2.dll', 'mspdbcore.dll', 'lib.exe'):",
                  "for name in ('c1.dll', 'c1xx.dll', 'c2.dll', 'mspdbcore.dll', 'mspdb140.dll', '1033/clui.dll', 'lib.exe'):")
text=text.replace("    run('linker-version-help', [linker, '/?'], build_env)",
                  "    help_result = run('linker-version-help', [linker, '/?'], build_env, expected=(0, 1100))\n"
                  "    assert b'Incremental Linker Version' in help_result.stdout and b'usage: LINK' in help_result.stdout and not help_result.stderr")
with (here/'probe_installed_toolchain_v2.py').open('x',encoding='utf-8') as stream:
    stream.write(text)
