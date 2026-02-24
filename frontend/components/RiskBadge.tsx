import type { RiskLevel } from "@/lib/api";

interface Props {
  level: RiskLevel;
  score?: number;
}

const config: Record<RiskLevel, { label: string; className: string; dot: string }> = {
  LOW: {
    label: "Low",
    className: "risk-low badge",
    dot: "bg-[#22c55e]",
  },
  MEDIUM: {
    label: "Medium",
    className: "risk-medium badge",
    dot: "bg-[#f59e0b]",
  },
  HIGH: {
    label: "High",
    className: "risk-high badge",
    dot: "bg-[#ef4444]",
  },
};

export default function RiskBadge({ level, score }: Props) {
  const { label, className, dot } = config[level];
  return (
    <span className={className}>
      <span className={`inline-block w-1.5 h-1.5 rounded-full ${dot}`} />
      {label}
      {score !== undefined && (
        <span className="opacity-70 ml-0.5">({score}%)</span>
      )}
    </span>
  );
}
