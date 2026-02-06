I want to create a plugin that knows how to create claude-code related features. The idea is based on the idea that agents need to track their own context, and do their own learning. That learning should be updated autonomously so that claude simply gets better over time without humans needing to fine-tune prompts and skills and hooks all the time. Claude should instead identify when it hit an issue that could have been solved with a proper /.claude setup, and update the setup to resolve the issue.

I want you to do some research before you build this feature for me. openclaw automatically updates it's memory, so I want you to poke inside of that to see if there's anything useful in it's hooks/skills/etc... that enables it to proactively update it's memory best.
https://github.com/openclaw/openclaw/

Then I want you to take a quick look at a plugin that helps create the scaffolding for building these things, but does not automate the creation of them. Perhaps the best way to build this skill is to use the claude-code-builder as a dependency, perhaps it would be better to take inspiration and build from the ground up. I'll let you decide what you think is best.
https://github.com/alexanderop/claude-code-builder

Finally, a couple resources I found that might help:
https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en
https://claude.com/blog/how-to-configure-hooks
https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them