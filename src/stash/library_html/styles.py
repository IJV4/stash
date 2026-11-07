STYLESHEET = """
:root { color-scheme: light dark; --bg: #fafaf7; --fg: #1f2328; --muted: #656d76;
  --card: #ffffff; --line: #d8dee4; --link: #0b5cad; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #14171a; --fg: #e6e8ea; --muted: #9aa4ad; --card: #1c2024;
    --line: #2d333b; --link: #6cb2ff; }
}
* { box-sizing: border-box; }
body { margin: 0; padding: 1rem; background: var(--bg); color: var(--fg);
  font: 16px/1.5 system-ui, sans-serif; overflow-wrap: anywhere; }
main, header { max-width: 46rem; margin: 0 auto; }
h1 { margin: 0 0 .25rem; font-size: 1.6rem; }
h2 { margin: 2rem 0 .5rem; font-size: 1.25rem; border-bottom: 1px solid var(--line); }
h3 { margin: 1.25rem 0 .25rem; font-size: 1rem; color: var(--muted); }
ul { list-style: none; margin: 0; padding: 0; }
li.entry { background: var(--card); border: 1px solid var(--line); border-radius: .5rem;
  margin: .5rem 0; padding: .6rem .8rem; }
a { color: var(--link); }
.meta, .empty, .more { color: var(--muted); font-size: .9rem; }
.stars { color: #d4a017; letter-spacing: .1rem; }
.note { margin: .25rem 0 0; white-space: pre-wrap; }
.takeaways { margin: .25rem 0 0; padding-left: 1rem; list-style: disc; }
details > summary { cursor: pointer; font-weight: 600; }
"""
