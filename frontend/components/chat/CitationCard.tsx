/**
 * 引用卡片组件
 */
import { FileText, ExternalLink } from "lucide-react";

interface CitationCardProps {
  source: {
    documentId: string;
    documentTitle: string;
    section?: string;
    content: string;
  };
}

export function CitationCard({ source }: CitationCardProps) {
  return (
    <div className="bg-card border rounded-md p-3 text-sm">
      <div className="flex items-start gap-2">
        <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="font-medium truncate">{source.documentTitle}</div>
          {source.section && (
            <div className="text-xs text-muted-foreground">
              {source.section}
            </div>
          )}
        </div>
        <button className="text-muted-foreground hover:text-primary">
          <ExternalLink className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
