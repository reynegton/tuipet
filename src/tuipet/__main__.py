"""`python3 -m tuipet` — the launch that always works.

The `tuipet` console script needs pip's bin dir on PATH, which is not a given
on every host (a-Shell on iOS installs scripts where PATH does not look).
Module execution has no such dependency, so this is the launch we document for
iOS (iOS support 2026-07-13).
"""
from tuipet.app import main

if __name__ == "__main__":
    main()
