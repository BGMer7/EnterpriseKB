/**
 * 预设问题建议芯片组件
 */
interface SuggestionChipsProps {
  questions: string[];
  onSelect: (question: string) => void;
}

export function SuggestionChips({ questions, onSelect }: SuggestionChipsProps) {
  return (
    <div>
      <h3 className="text-sm font-medium mb-3 text-muted-foreground">
        热门查询
      </h3>
      <div className="flex flex-wrap gap-2">
        {questions.map((question, index) => (
          <button
            key={index}
            onClick={() => onSelect(question)}
            className="px-3 py-2 bg-secondary hover:bg-secondary/80 text-sm rounded-lg transition-colors"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
