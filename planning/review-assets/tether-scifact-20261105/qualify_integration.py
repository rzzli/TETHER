"""Pin and qualify the full native implementation before actual benchmark use."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qualify_components as qualification

qualification.MODULES = ('baseline', 'check_worker', 'data_views', 'evaluate',
                        'native_contract', 'run', 'runtime', 'score_worker',
                        'split', 'tether_adapter', 'worker')
qualification.TESTS = ('baseline', 'check_worker', 'data_views', 'policy',
                      'qualification', 'run', 'runtime', 'score_worker',
                      'scoring', 'split', 'worker')
qualification.SCOPE = ('fictional native component and controller integration tests; '
                       'full rehearsal separately retained; no real benchmark results')
qualification.EXTRA_SOURCES = (Path(__file__).resolve(), HERE / 'qualify_components.py')

if __name__ == '__main__':
    qualification.main()
