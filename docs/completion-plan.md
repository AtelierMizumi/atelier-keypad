# Atelier6K — tooling survey and completion plan

How to take the project from "rev 0, unverified" to a product someone else
can build and use safely, and which tools make each step checkable. Written
in November 2026.

The tools below were found by web search and are **not installed or tried
yet**, except where marked "in use". Version support and maintenance status
come from each project's own README or directory listings; confirm before
depending on one. Third-party code should be read before it is run.

Related: [rev 0 design review](design-review.md),
[rev 1 research](rev1-research.md), [case notes](case.md).

## 1. Tools

### Design review and AI assistance

| Tool | What it adds | Use here |
|------|--------------|----------|
| [kicad-happy](https://github.com/aklofas/kicad-happy) | Claude Code plugin with 11 skills: schematic analysis, PCB layout review, EMC pre-compliance, SPICE simulation, datasheet download, component sourcing, fabrication prep | Second, structured pass over the rev 1 schematic and layout; BOM sourcing; pre-fab checklist. Closest match to this project's needs |
| [KiCad MCP Pro](https://glama.ai/mcp/servers/oaslananka/kicad-mcp-pro) | MCP server with schematic inspection, ERC, connectivity and power review workflows. Its authors describe it as an assistant, not a manufacturing sign-off | Alternative to kicad-happy if live access to an open KiCad project is wanted |
| [KiCAD-MCP-Server](https://claudemarketplaces.com/mcp/mixelpixx/kicad-mcp-server) | Large MCP server (KiCad 10 plugin, bundled skills, design-review audits) | Only if the agent should drive KiCad directly; needs the KiCad GUI installed |
| `kicad-cli` ERC/DRC | Rule checks from the command line | **In use** via `scripts/export.sh` |

### Board generation and routing

| Tool | What it adds | Use here |
|------|--------------|----------|
| KiCad `pcbnew` Python API | Scripted placement, net assignment, zone fill | Place parts at exact coordinates so the case generator and PCB agree. Available in the KiCad Docker image already used |
| [KiCadRoutingTools](https://github.com/atomic14/KiCadRoutingTools) | Rust-accelerated A* autorouter working on `.kicad_pcb` files; states support for KiCad 9 and 10 | First choice for routing rev 1 without the GUI |
| Freerouting | Established autorouter via Specctra DSN/SES; used for rev 0 | Fallback router |
| [atopile](https://github.com/atopile/atopile) | Circuit described in code (`.ato`), compiled to a KiCad board; component picking; MIT | Option for defining rev 1 as code. Layout still happens in KiCad |
| [tscircuit](https://github.com/tscircuit/tscircuit) | Circuit and layout in TypeScript, MIT | Alternative to atopile; a larger change of toolchain |

A small board like this (about 45 parts, 2 layers) does not need a
code-defined flow. The pragmatic route is: KiCad schematic as the source of
truth, scripted placement, an autorouter, then DRC and a manual look.

### Manufacturing outputs and CI

| Tool | What it adds | Use here |
|------|--------------|----------|
| [KiBot](https://kibot.readthedocs.io/) | One YAML file produces Gerbers, drill, position files, BOM, 3D renders, diffs; Docker images for CI; 1.9.1 (July 2026) added a KiCad 10 `kicad-cli` interface, with stated limitations | Replace the hand-written parts of `export.sh` once rev 1 needs fabrication files; run in GitHub Actions on every push |
| [KiKit](https://pypi.org/project/kikit/) | Panelisation and fab-house export presets | Only if boards are panelised or the FR4 plate is ordered on the same panel |
| KiBot's diff output | Visual schematic and PCB diffs between commits | Review rev 0 → rev 1 changes in pull requests |
| Interactive HTML BOM | Clickable assembly guide | Already wired into `export.sh` behind `WITH_IBOM=1` |
| KiCanvas | In-browser schematic and PCB viewer | **In use** on the demo site |

### Firmware

| Tool | What it adds | Use here |
|------|--------------|----------|
| QMK userspace + GitHub Actions build | Firmware lives in this repo and CI attaches a `.uf2` to each release | Reproducible builds; no "works on my machine" firmware |
| QMK `keyboard.json` schema and `qmk lint` | Static checks on the keyboard definition | Run in CI |
| VIA v3 definition + Design tab | Custom menu (debounce slider, lighting) | Required for runtime debounce |
| QMK Console / `DEBUG_MATRIX_SCAN_RATE` | Reports the matrix scan rate | Confirms the scan is faster than the 1 ms USB poll |

### Measurement

Scan rate, USB poll interval and end-to-end latency are three different
quantities and each needs its own method.

| Tool | Measures | Notes |
|------|----------|-------|
| [XLAT](https://relatedrepos.com/gh/teamfinalmouse/xlat) (Finalmouse) | USB-HID latency from an electrical trigger to the report | Open source; runs on a dev board |
| [pico-usb-input-tester](https://github.com/InfraredAces/pico-usb-input-tester) | Input latency, built on an RP2040 | Work in progress; same MCU family as rev 1 |
| [keyboard-latency-tester](https://github.com/joelspadin/keyboard-latency-tester) | Latency with the tester deliberately out of step with the keyboard's scan | Avoids results skewed by synchronisation |
| [Stapelberg's method](https://michael.stapelberg.ch/posts/2021-05-08-keyboard-input-latency-qmk-kinesis/) | End-to-end latency with a high-speed USB eval board; also lists QMK causes of latency | Good reference for what to fix |
| USB multimeter / inline meter | Board current at each brightness level | Verifies the 500 mA budget; cheap |

Browser-based "latency tests" include OS and browser delays and do not
isolate the keypad.

### Already available in this environment

Skills and agents installed here that fit the work: `research` and
`deep-research` (background research with citations), `tdd` and `test-first`
(used for the case generator), `code-review`, `diagnosing-bugs`, `prototype`,
`wizard` (guided human-only steps such as ordering and Pages setup),
`setup-pre-commit`, and browser automation for checking the demo site.

## Third-party code vetting

Checked on 2026-11-14 by reading a shallow clone of each repository without
running anything. The scan looked for install or auto-run hooks, real
`eval`/`exec`/`shell=True` use, obfuscated payloads, credential and home
directory access, outbound uploads, committed binaries and instructions aimed
at an AI agent. This is a source read, not a guarantee; re-check when
updating to a newer commit.

| Tool | Commit checked | Trust signals | Findings | Verdict |
|------|----------------|---------------|----------|---------|
| kicad-happy | `7d9d4d9` (2026-11-06) | 1.7k stars, MIT, active since March 2026 | No hooks, no MCP server, no `eval`/`exec`/`shell=True`, no binaries. Network calls only from the sourcing and datasheet skills, to DigiKey, Mouser, element14, LCSC and jlcsearch. API keys are read from environment variables and sent only to the matching distributor. Writes a config file and a cache under the home directory | Acceptable. Use the `kicad`, `emc` and `bom` skills offline; do not set distributor API keys unless sourcing is wanted |
| InteractiveHtmlBom | `363d5df` (2026-11-13) | 4.6k stars, MIT, since 2018 | No network code. Subprocess use is limited to `git` for its version string and opening the result in a browser | Acceptable. Still run with `--network none` and read-only mounts, as `export.sh` does |
| KiCadRoutingTools (`atomic14` fork) | `6ab59a6` (2026-07-11) | The repository found by search is a 3-star fork created and last pushed on one day; upstream is `drandyhaas/KiCadRoutingTools` (779 stars) | `build_router.py` downloads a prebuilt native router binary from GitHub releases, or builds it with Cargo (pulling crates); it suggests `curl … \| sh` for rustup. One `exec()` of import statements in the plugin's dependency check | **Do not use the fork.** If the router is needed, take upstream at a pinned commit, build from source rather than downloading the binary, and run it in a container with no network. Freerouting is the alternative and is equally unreviewable as a binary, so it gets the same sandbox |
| Freerouting 2.5.0 | release jar, SHA-256 `f6f51bb0…5de3c7` | Official repository, 2.2k stars, GPL-3.0, since 2014 | A 64 MB jar cannot be reviewed by reading. Downloaded and checksum-verified, **never run**: the session's permission system refused to execute it | Not used. Rev 1 was routed by `hardware/rev1/route.py`, written for this board, and judged by KiCad's DRC |
| QMK firmware and `qmk_cli` image | — | Official QMK organisation | Not read line by line; standard upstream toolchain | Acceptable from the official sources only, pinned to a tag |

Rules applied to all of them: pin to a commit or tag, run in a container
without network access and with the project mounted read-only where possible,
never give them credentials, and treat their output as a checklist to verify.

## 2. Completion plan

Each phase has a gate that can be checked by a command or a measurement.
"Done" for the project means every gate has passed on a physical board.

| Phase | Work | Tools | Gate |
|-------|------|-------|------|
| A. Publish rev 0 as-is | Merge `revamp`; enable Pages | git, GitHub Pages | Demo site live; `check-assets.sh` passes in CI |
| B. Decide rev 1 | Answer the open questions (MCU, wiring, LEDs, plate, layout) | — | Decisions recorded in `rev1-research.md` |
| C. Rev 1 schematic | New schematic: RP2040, direct pins, one LED chain, fuse, decoupling, level shifter | KiCad, kicad-happy schematic review | ERC with 0 errors; every rev 0 review finding closed or explicitly waived |
| D. Rev 1 layout | Scripted placement on the existing outline, hole and switch positions; autoroute; ground pour | pcbnew API, KiCadRoutingTools or Freerouting | DRC with 0 errors against fab rules; 0 unconnected; schematic parity clean; power tracks ≥ 0.5 mm |
| E. Second-opinion review | Independent pass on schematic, layout, EMC and BOM | kicad-happy, datasheets for every IC and LED | Written review with no blocker; LED pinout checked against the actual part's datasheet |
| F. Firmware | Current QMK, VIA v3 definition, eager per-key debounce with runtime setting, brightness cap, osu! layers | QMK, GitHub Actions | CI builds a `.uf2`; `qmk lint` clean; VIA definition loads |
| G. Fabrication package | Gerbers, drill, BOM with supplier part numbers, position file, assembly guide | KiBot, Interactive HTML BOM | Fab-house DFM check passes; BOM has a purchasable part for every line |
| H. Case update | Regenerate for the rev 1 board (module height, plate choice) | `case/generate.py` | 21 case tests pass against the rev 1 board file |
| I. Build one | Order 5 PCBs and one case; assemble a single board | — | Powers up; enumerates over USB; all 9 keys and 10 LEDs work |
| J. Electrical safety checks | Measure before trusting | USB meter, multimeter, thermometer | Current ≤ 450 mA at maximum allowed brightness; a deliberate short on the 5 V rail trips the fuse and recovers; no part above 50 °C after 1 hour; ESD diodes present on D+/D− |
| K. Performance checks | Measure latency and stability | QMK Console, a latency tester from the list above | Scan rate ≥ 5 kHz; 1000 Hz polling confirmed; end-to-end latency ≤ 2 ms at the 95th percentile; no missed or doubled presses in a 1-hour soak at the chosen debounce |
| L. Release | Tag, release notes, build guide, known issues | GitHub Releases, `wizard` for the manual steps | A second person can build one from the repository alone |

Phases C–H are desk work and can all be verified by commands. Phases I–K
need hardware and cannot be replaced by any tool: the review found four
blockers on paper, and a first build usually finds more.

### Status on 2026-11-14

| Phase | State |
|-------|-------|
| A | Not done: nothing is committed or published yet |
| B | Done |
| C | Done by command: ERC 0, netlist equals `circuit.py`. The kicad-happy review was not run |
| D | Done by command: DRC 0 errors, 0 unconnected, parity clean. See [rev1-board.md](rev1-board.md) for what the checks do not cover |
| E | Not done |
| F | Firmware builds with the rev 1 pin map; not run on hardware; no CI yet |
| G | Not done: no Gerbers, no BOM with supplier part numbers, no plate Gerbers |
| H | Done by command: 15 rev 1 case tests pass (36 with the rev 0 ones). Hole positions for BOOT and RESET are from a drawing |
| I-L | Need hardware |

### What "safer" means here, concretely

1. Over-current: polyfuse on 5 V, verified by a short test (J).
2. Current budget: brightness cap in firmware, verified with a meter (J).
3. ESD: protection on the USB lines, good ground pour, no exposed 5 V on the
   case edge.
4. Thermal: nothing hot to the touch after an hour (J).
5. Firmware: cannot be bricked (ROM bootloader), settings survive power
   loss, a corrupted settings block falls back to defaults.
6. Mechanical: no sharp acrylic edges, screws do not protrude from the base,
   feet stop it sliding.
7. Documentation: the README states plainly what has and has not been
   verified, as it does now.

### Risks to the plan

- Autorouted boards pass DRC but can route power and USB poorly. Constrain
  net classes (USB pair, 5 V, ground) before routing and inspect the result.
- The AI review tools are assistants. Their output is a checklist to verify
  against datasheets, not a sign-off.
- KiBot's KiCad 10 support is recent and has stated limitations; keep
  `export.sh` as the fallback.
- Hardware phases depend on parts availability and shipping time.
