import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { PassThrough, Writable } from "node:stream";
import { resolve } from "node:path";
import { simulateCommand } from "../src/commands/simulate.js";

const TASK = resolve(__dirname, "fixtures/task-basic.md");

describe("simulateCommand", () => {
  let originalStdin: typeof process.stdin;
  let originalStdout: typeof process.stdout;
  let originalStderr: typeof process.stderr;
  let stdoutBuf: string;
  let stderrBuf: string;

  beforeEach(() => {
    originalStdin = process.stdin;
    originalStdout = process.stdout;
    originalStderr = process.stderr;
    stdoutBuf = "";
    stderrBuf = "";
  });

  afterEach(() => {
    Object.defineProperty(process, "stdin", { value: originalStdin, configurable: true });
    Object.defineProperty(process, "stdout", { value: originalStdout, configurable: true });
    Object.defineProperty(process, "stderr", { value: originalStderr, configurable: true });
    delete process.env.OPENAI_API_KEY;
    vi.restoreAllMocks();
  });

  it("errors with exit code 2 when OPENAI_API_KEY is unset", async () => {
    delete process.env.OPENAI_API_KEY;
    await expect(simulateCommand({ task: TASK, model: "gpt-4o" } as any))
      .rejects.toMatchObject({ exitCode: 2 });
  });

  it("runs a turn and exits cleanly on /end without schema", async () => {
    process.env.OPENAI_API_KEY = "test";
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ choices: [{ message: { content: "hello back" } }] }), { status: 200 }),
    );

    // Use a PassThrough so we can push lines asynchronously — Readable.from()
    // ends the stream immediately after delivering all data, which causes
    // readline/promises to close before the second rl.question() call.
    const fakeStdin = new PassThrough();
    Object.defineProperty(process, "stdin", { value: fakeStdin, configurable: true });

    const fakeStdout = new Writable({
      write(chunk, _enc, cb) { stdoutBuf += chunk.toString(); cb(); },
    });
    Object.assign(fakeStdout, { isTTY: false });
    Object.defineProperty(process, "stdout", { value: fakeStdout, configurable: true });

    const fakeStderr = new Writable({
      write(chunk, _enc, cb) { stderrBuf += chunk.toString(); cb(); },
    });
    Object.defineProperty(process, "stderr", { value: fakeStderr, configurable: true });

    // Push user input lines with small delays so readline has time to call
    // .question() again between each line. The fetch mock resolves synchronously
    // so one tick is enough for the loop to advance.
    setTimeout(() => fakeStdin.push("hi\n"), 10);
    setTimeout(() => { fakeStdin.push("/end\n"); fakeStdin.push(null); }, 50);

    await simulateCommand({ task: TASK, model: "gpt-4o" } as any);

    expect(stdoutBuf).toContain("hello back");
    expect(stderrBuf).toContain("Skipping extraction");
  }, 10_000);
});
