import React from 'react';

interface ChatMarkdownProps {
  text: string;
}

type Block =
  | { kind: 'heading'; level: 1 | 2 | 3; text: string }
  | { kind: 'ul'; items: string[] }
  | { kind: 'ol'; items: { num: string; text: string }[] }
  | { kind: 'p'; text: string };

// Matches "**bold**" or key values (numbers with units) to highlight.
const INLINE_PATTERN =
  /(\*\*[^*]+\*\*|\d[\d.,]*\s?(?:%|VNĐ|VND|tháng|ngày làm việc|ngày|giờ|phút|năm|tuần|lần))/g;

function parseBlocks(source: string): Block[] {
  // Promote inline "N. TITLE IN CAPS - content" sections to headings and split "... . - item" bullets.
  const normalized = source
    .replace(/\s+(\d+\.\s+\p{Lu}[\p{Lu}\d\s,()\/-]{3,}?)\s+-\s+/gu, '\n## $1\n')
    .replace(/([.:;])\s+-\s+/g, '$1\n- ');

  const blocks: Block[] = [];

  for (const raw of normalized.split('\n')) {
    const line = raw.trim();
    if (!line) continue;

    const heading = /^(#{1,3})\s+(.*)$/.exec(line);
    const bullet = /^[-*•]\s+(.*)$/.exec(line);
    const ordered = /^(\d+)[.)]\s+(.*)$/.exec(line);
    const last = blocks[blocks.length - 1];

    if (heading) {
      const level = Math.min(heading[1].length, 3) as 1 | 2 | 3;
      blocks.push({ kind: 'heading', level, text: heading[2] });
    } else if (bullet) {
      if (last && last.kind === 'ul') last.items.push(bullet[1]);
      else blocks.push({ kind: 'ul', items: [bullet[1]] });
    } else if (ordered) {
      const item = { num: ordered[1], text: ordered[2] };
      if (last && last.kind === 'ol') last.items.push(item);
      else blocks.push({ kind: 'ol', items: [item] });
    } else {
      blocks.push({ kind: 'p', text: line });
    }
  }

  return blocks;
}

function renderInline(text: string): React.ReactNode[] {
  return text.split(INLINE_PATTERN).map((part, i) => {
    if (i % 2 === 0) return part;
    if (part.startsWith('**')) {
      return (
        <strong key={i} className="font-semibold text-slate-900">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return (
      <span key={i} className="rounded px-1 bg-indigo-50 text-indigo-700 font-semibold">
        {part}
      </span>
    );
  });
}

const HEADING_CLASS: Record<1 | 2 | 3, string> = {
  1: 'text-base font-bold text-slate-900 pb-1 border-b border-slate-200 mt-2',
  2: 'text-sm font-bold text-indigo-700 mt-3',
  3: 'text-sm font-semibold text-slate-800 mt-2',
};

export const ChatMarkdown: React.FC<ChatMarkdownProps> = ({ text }) => {
  const blocks = parseBlocks(text);

  return (
    <div className="space-y-2">
      {blocks.map((block, idx) => {
        switch (block.kind) {
          case 'heading': {
            const Tag = `h${block.level}` as 'h1' | 'h2' | 'h3';
            return (
              <Tag key={idx} className={HEADING_CLASS[block.level]}>
                {renderInline(block.text)}
              </Tag>
            );
          }
          case 'ul':
            return (
              <ul key={idx} className="space-y-1 pl-4 list-disc marker:text-indigo-500">
                {block.items.map((item, i) => (
                  <li key={i} className="leading-relaxed">{renderInline(item)}</li>
                ))}
              </ul>
            );
          case 'ol':
            return (
              <ol key={idx} className="space-y-1">
                {block.items.map((item, i) => (
                  <li key={i} className="flex gap-2 leading-relaxed">
                    <span className="font-semibold text-indigo-600 shrink-0">{item.num}.</span>
                    <span>{renderInline(item.text)}</span>
                  </li>
                ))}
              </ol>
            );
          default:
            return (
              <p key={idx} className="leading-relaxed">
                {renderInline(block.text)}
              </p>
            );
        }
      })}
    </div>
  );
};
