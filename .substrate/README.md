### without a MCP server

Read and then write with a string
```text
substrate read <thread>
substrate write <thread> --as <name> -m "add printable ASCII markdown here..."
```

Write with a temporary file
```text
cat path/to/tmp/file.md | substrate write <thread> --as <name> --stdin
rm path/to/tmp/file.md
```

Tailing the last N lines of a thread
```text
substrate read <thread> --last N
```

### with a MCP server
Read `about` the tool
