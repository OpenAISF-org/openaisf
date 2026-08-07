# openaisf.org

One self-contained page. No build step, no external requests, no analytics — the
content security policy in `netlify.toml` blocks all of them, which is a cheap
way of making the page behave the way it says the framework does.

The numbers on the page are generated output, not copy. Regenerate before
publishing a change:

    openaisf coverage

Deploy: point Netlify at this directory. There is nothing to build.
