# Brrrty corpus

`sites.toml` lists public 11ty sites, each pinned to a commit, that Brrrty is tested against.
`.github/workflows/corpus.yml` clones each site inside a GitHub runner, builds it with 11ty and Brrrty (`cargo xtask corpus`), and diffs the outputs.
Run it from the Actions tab (pick a brrrty ref, optionally one site); it also runs daily on main. Each full run on main updates the compatibility chart (`progress/compat.svg`, history in `progress/history.csv`) on the `progress` branch, which brrrty's README shows.
The merged `corpus.json` and `report.md` are in the run's `corpus-results` artifact, kept for one day. No caches, no secrets: site jobs run third-party code. No site code is ever committed here.
