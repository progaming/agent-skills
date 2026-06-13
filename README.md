# ProGaming Agent Skills

A collection of AI agent skills for the ProGaming team, designed to work with [Vercel Skills](https://github.com/vercel-labs/skills).

## Quick Start

Install a skill using the Vercel Skills CLI:

```bash
npx skills add progaming/agent-skills
```

For more details on how Vercel Skills works, see the [official documentation](https://github.com/vercel-labs/skills).

## Setup for Hermes Agent

To make these skills available to Hermes, run:

```bash
hermes config edit
```

Then add `~/.agents/skills` to `skills -> external_dirs` so Hermes detects skills added to the global scope skills folder.

## Contributing

To add a new skill, create a directory under `skills/<skill-name>/` and add a `SKILL.md` with the skill definition, triggers, and usage instructions.
