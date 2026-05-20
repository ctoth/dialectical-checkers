# dialectical-checkers

An experimental, UCI-free dialectical **English-draughts** (8x8 American
checkers) engine that selects its moves through a Dung argumentation framework
rather than a scalar evaluation. It is the second concrete game in the
dialectical-games line and mirrors the `dialectical-chess` project conventions
(uv-managed, `pyright` basic mode, `pytest` markers `unit` / `property` /
`differential`). This repository is experimental and a work in progress — see
`notes/checkers-design.md` and `notes/checkers-port-plan.md` for the design and
the phased build plan.
