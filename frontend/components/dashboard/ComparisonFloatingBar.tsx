"use client";

import { Button } from "@/components/ui/button";
import { ArrowUpRight } from "lucide-react";

interface ComparisonFloatingBarProps {
  selectedCount: number;
  maxCompare: number;
  onClear: () => void;
  onCompare: () => void;
}

export function ComparisonFloatingBar({
  selectedCount,
  maxCompare,
  onClear,
  onCompare,
}: ComparisonFloatingBarProps) {
  if (selectedCount === 0) return null;

  return (
    <aside
      className="comparison-selection-bar"
      aria-label="Acciones de comparación de sesiones"
    >
      <div className="comparison-selection-info">
        <span className="comparison-selection-badge font-mono">
          {selectedCount}
        </span>
        <span className="text-xs sm:text-sm">
          {selectedCount === 1
            ? "1 sesión seleccionada. Marca al menos otra para comparar."
            : `${selectedCount} sesiones seleccionadas (máximo ${maxCompare}).`}
        </span>
      </div>

      <div className="comparison-selection-actions">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onClear}
          className="text-xs bg-transparent border-white/30 text-white hover:bg-white/10"
        >
          Deseleccionar
        </Button>
        <Button
          type="button"
          size="sm"
          onClick={onCompare}
          disabled={selectedCount < 2}
          className="btn text-xs font-bold"
        >
          Comparar ({selectedCount}) <ArrowUpRight className="w-3.5 h-3.5 ml-1" />
        </Button>
      </div>
    </aside>
  );
}

