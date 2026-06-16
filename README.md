# SRPG Sims

A text-first RPG-style AI-sims prototype where every interactable thing in the world behaves like an agent. The game loop is inspired by Multi-Agent Debate (MAD): nearby agents propose perspectives, odd events, risks, and plans, then a director chooses a coherent-but-surprising outcome.

## Quick start

```bash
python -m srpg_sims
```

Type natural language commands to explore. Useful commands:

- `status` — show SRPG-like stats, inventory, tools, flags, and current plan.
- `plan` — show only the current ProAgent action plan.
- `look` — ask the place and senses to describe the scene.
- `quit` — exit.

## Concept coverage

- Text-based RPG world entry.
- Objects, places, people, animals, senses, and actions are represented as agents.
- Player prompts trigger multi-agent proposals and director synthesis.
- ProAgent-style action plans are maintained alongside chaotic events.
- Memory avoids repeating similar experiences.
- Status is hidden unless requested.
- GUI can be added later because the engine and CLI are separated.
