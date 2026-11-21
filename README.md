# Brrrty corpus

`sites.toml` lists public 11ty sites, each pinned to a commit, that Brrrty is tested against.
`.github/workflows/corpus.yml` clones each site inside a GitHub runner, builds it with 11ty and Brrrty (`cargo xtask corpus`), and diffs the outputs.
Run it from the Actions tab (pick a brrrty ref, optionally one site); it also runs weekly.
The merged `corpus.json` and `report.md` are in the run's `corpus-results` artifact, kept for one day. No caches, no secrets: site jobs run third-party code. No site code is ever committed here.
