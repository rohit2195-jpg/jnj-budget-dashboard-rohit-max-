# Documentation Index

This folder holds the companion documentation for the project. Keep [`README.md`](../README.md) at the repo root as the public entrypoint, and use these files for focused detail.

## Suggested Reading Order

If you are new to the project, read the docs in this order:

1. [`../README.md`](../README.md) for the product overview and quick start
2. [ARCHITECTURE.md](ARCHITECTURE.md) for runtime flow and system boundaries
3. [DEPLOYMENT.md](DEPLOYMENT.md) for environment and hosting decisions
4. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for known failure modes

If you are contributing code, continue with:

5. [CONTRIBUTING.md](CONTRIBUTING.md)
6. [PROJECT_GUIDE.md](PROJECT_GUIDE.md)

## Guides

- [DEPLOYMENT.md](DEPLOYMENT.md): environment, hosting, and runtime setup
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md): known failure modes and fixes
- [ARCHITECTURE.md](ARCHITECTURE.md): runtime flow, subsystem boundaries, and persistence model
- [PROJECT_HISTORY.md](PROJECT_HISTORY.md): milestone-based history of how the architecture evolved
- [CONTRIBUTING.md](CONTRIBUTING.md): repo workflow and validation expectations
- [PROJECT_GUIDE.md](PROJECT_GUIDE.md): implementation-oriented repo guide for engineers and coding agents

## Visuals

- [assets/system-overview.svg](assets/system-overview.svg): architecture overview diagram
- [assets/user-workflow.svg](assets/user-workflow.svg): user journey from upload to follow-up
- [assets/execution-boundary.svg](assets/execution-boundary.svg): approval boundary and post-approval execution split
- [assets/project-history-timeline.svg](assets/project-history-timeline.svg): six-phase project history timeline
- [assets/workflow-evolution.svg](assets/workflow-evolution.svg): linear flow to LangChain to LangGraph evolution

## Maintainer Notes

- Keep the root `README.md` concise enough to work as the public entrypoint.
- Put implementation-heavy material in this folder instead of expanding the root README indefinitely.
- When runtime behavior changes, update [ARCHITECTURE.md](ARCHITECTURE.md) and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) together so the design and failure guidance stay aligned.
