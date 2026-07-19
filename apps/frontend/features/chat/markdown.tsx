import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

// Renders AI answer text (and user messages) with GFM Markdown + fenced
// code blocks, styled directly from Design System tokens rather than
// pulling in @tailwindcss/typography (87_Component_Library.md's
// Design-System-First mandate — no ad hoc styling plugin).
export function Markdown({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 text-sm leading-relaxed [&>*:first-child]:mt-0",
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => (
            <p className="whitespace-pre-wrap">{children}</p>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="text-primary underline underline-offset-2"
            >
              {children}
            </a>
          ),
          ul: ({ children }) => (
            <ul className="ml-5 list-disc space-y-1">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="ml-5 list-decimal space-y-1">{children}</ol>
          ),
          h1: ({ children }) => (
            <h1 className="text-h3 font-semibold">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-body font-semibold">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-body font-semibold">{children}</h3>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-border-strong pl-3 text-foreground-muted">
              {children}
            </blockquote>
          ),
          code: ({ className: codeClassName, children, ...props }) => {
            const isBlock = /language-/.test(codeClassName ?? "");
            if (isBlock) {
              return (
                <pre className="overflow-x-auto rounded-md border border-border bg-background-subtle p-3">
                  <code className="font-mono text-xs">{children}</code>
                </pre>
              );
            }
            return (
              <code
                className="rounded-sm bg-background-subtle px-1 py-0.5 font-mono text-xs"
                {...props}
              >
                {children}
              </code>
            );
          },
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-xs">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-border px-2 py-1 text-left font-medium">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-border px-2 py-1">{children}</td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
