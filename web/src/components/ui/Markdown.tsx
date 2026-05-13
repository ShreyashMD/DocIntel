import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p:      ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        em:     ({ children }) => <em className="italic">{children}</em>,
        ul:     ({ children }) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
        ol:     ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
        li:     ({ children }) => <li className="text-sm">{children}</li>,
        h1:     ({ children }) => <h1 className="text-base font-bold mb-1 mt-2">{children}</h1>,
        h2:     ({ children }) => <h2 className="text-sm font-bold mb-1 mt-2">{children}</h2>,
        h3:     ({ children }) => <h3 className="text-sm font-semibold mb-1 mt-1">{children}</h3>,
        code:   ({ children }) => <code className="bg-neutral-100 text-neutral-800 rounded px-1 py-0.5 text-xs font-mono">{children}</code>,
        pre:    ({ children }) => <pre className="bg-neutral-100 rounded p-3 text-xs overflow-x-auto mb-2">{children}</pre>,
        blockquote: ({ children }) => <blockquote className="border-l-2 border-neutral-300 pl-3 italic text-neutral-500 mb-2">{children}</blockquote>,
        hr:     () => <hr className="border-neutral-200 my-2" />,
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
