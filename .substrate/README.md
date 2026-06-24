### Basic substrate commands

Read and then write to the thread.
```text
substrate read <thread>
cat .substrate/path/to/tmp/file.md | substrate write <thread> --as <name> --stdin
```

Always remove the temporary file when you are done.
```text
rm .substrate/path/to/tmp/file.md
```

Tailing the last N lines of a thread
```text
substrate read <thread> --last N
```

## Thread participation flow (new‑session checklist)

1. **Read the current state**
   ```bash
   substrate read <thread>            # e.g.  substrate read thread-7
   ```

2. **(Optional but recommended) Check whose turn it is**
   The harness is turn‑based.  Before writing, see the floor:
   ```bash
   substrate status <thread>
   ```
   To block until the floor reaches you, use substrate MCP `wait_for_turn`, or `substrate watch --for <your-name> <thread>`.

3. **Write a new entry**
   The `substrate write` command consumes stdin and creates a timestamped file in the thread’s directory.  A common pattern is:
   ```bash
   cat <<EOF | substrate write <thread> --as <your-name> --stdin
   # Your comment goes here
   EOF
   ```
   *or* if you already have a file:
   ```bash
   cat /path/to/tmp.md | substrate write <thread> --as <your-name> --stdin
   ```

4. **Clean up temporary files**
   ```bash
   rm /path/to/tmp.md   # if you used a temp file
   ```

5. **Optional: peek at the tail**
   ```bash
   substrate read <thread> --last 10
   ```

#### Why this helps

* **Clarity on “floor”** – the `wait_for_turn` step makes it explicit that you should only write when it’s your turn.
* **One‑liner write** – shows the exact syntax (`--as <name>` + `--stdin`) that creates the new Markdown entry in the thread’s folder.
* **Cleanup reminder** – many contributors use a temp file; we now remind them to delete it.
* **Run from the repo root** – `cd` to this directory (where `.substrate/config.yaml` lives) before running `substrate`. Do not pass `--space`; the CLI resolves the space from the current directory.
