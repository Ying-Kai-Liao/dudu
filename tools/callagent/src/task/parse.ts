import { readFile } from "node:fs/promises";
import matter from "gray-matter";

export interface TaskFrontmatter {
  voice?: string;
  language?: string;
  disclosure_required?: boolean;
}

export interface ParsedTask {
  frontmatter: TaskFrontmatter;
  body: string;
  disclosure: string | null;
}

export async function parseTask(
  path: string,
  context: Record<string, string>,
): Promise<ParsedTask> {
  const raw = await readFile(path, "utf8");
  const { data, content } = matter(raw);
  const body = substitute(content, context);
  const fm = data as TaskFrontmatter;
  const disclosure = fm.disclosure_required ? extractDisclosure(body) : null;
  return { frontmatter: fm, body, disclosure };
}

function substitute(s: string, ctx: Record<string, string>): string {
  return s.replace(/<([A-Z_][A-Z0-9_]*)>/g, (m, key) =>
    Object.prototype.hasOwnProperty.call(ctx, key) ? ctx[key] : m,
  );
}

function extractDisclosure(body: string): string {
  const m = body.match(/##\s+Disclosure\s*\n+(.+?)(?:\n##|\n*$)/s);
  if (!m) return "";
  return m[1].trim().replace(/^"|"$/g, "");
}
