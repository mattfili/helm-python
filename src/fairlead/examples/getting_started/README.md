# 01 — Getting Started

The foundation example. Creates a Fairlead instance, registers built-in skills, calls typed operations, and uses `search()` to discover what's available.

## What You'll Learn

- Creating a `Fairlead` instance with `FairleadOptions`
- Registering built-in skills with `.use()`
- Calling operations via attribute access (`agent.fs.read_file(...)`)
- Using `search()` to discover operations by keyword

## Run It

```bash
pip install -e ../..
python main.py
```

## Key Concepts

**Skills** are collections of related operations. fairlead ships with built-in skills for file system (`fs`), git (`git`), grep (`grep`), editing (`edit`), HTTP (`http`), and shell (`shell`).

**Operations** are typed async functions. Instead of parsing CLI output, you get structured Python objects — `GitStatus`, `DirEntry`, `StatResult`, etc.

**Search** finds operations by name, description, or tags. Use it to discover what's available without reading docs.
