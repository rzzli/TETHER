# Workflow timeout closeout

**PASS:** final workflow SHA-256 `78d244677183a3778d90d57e626337d92678976df34f54aef707bc1deaaddc8d` parses as YAML with no duplicate keys. All nine run commands match v1 exactly. The P09 timeout remains 15 minutes.

Removing the one new explanatory comment and reverting only the main timeout from 90 to 20 minutes reconstructs exact prior reviewed SHA-256 `08ccc1364abb4413489b9d1cb7bacfc204a1c9064bf1f547b1142ba43458fb1d`. This verifies that no other bytes changed, including actions, permissions, matrix, command flags and build constraints.

The root reports observed local gate elapsed already exceeds 20 minutes. Ninety minutes is a configured budget, not a measured final gate duration. Final local wall times remain pending root terminal evidence; hosted execution is unexecuted. The v1 two-step build-constraint enforcement evidence carries forward. This closeout ran no tests or installs, opened no provider inputs and changed no workflow/environment files.
