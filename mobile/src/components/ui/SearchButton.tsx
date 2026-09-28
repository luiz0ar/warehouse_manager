"use client";

import React from "react";
import { useWarehouseStore } from "@/store/useWarehouseStore";
import { Search, Sparkles, X, Filter } from "lucide-react";

export const SearchButton: React.FC = () => {
  const setIsSearchModalOpen = useWarehouseStore(
    (state) => state.setIsSearchModalOpen
  );
  const highlightedBatchId = useWarehouseStore((state) => state.highlightedBatchId);
  const highlightedSlotCoords = useWarehouseStore(
    (state) => state.highlightedSlotCoords
  );
  const clearSearch = useWarehouseStore((state) => state.clearSearch);

  return (
    <div className="absolute top-16 left-3 right-3 sm:left-6 sm:right-auto z-20 pointer-events-auto flex items-center space-x-2">
      {/* Botão Principal Buscar Lote */}
      <button
        onClick={() => setIsSearchModalOpen(true)}
        className="flex items-center space-x-2.5 bg-[#141824]/95 hover:bg-[#1e2336] active:scale-[0.98] backdrop-blur-xl border border-slate-700/80 hover:border-amber-400/80 rounded-2xl px-4 py-2.5 shadow-2xl transition group"
      >
        <div className="w-6 h-6 rounded-xl bg-amber-400/15 border border-amber-400/30 flex items-center justify-center text-amber-400 group-hover:scale-110 transition">
          <Search className="w-3.5 h-3.5" />
        </div>
        <span className="text-xs font-bold text-slate-100 group-hover:text-amber-300 transition">
          Buscar Lote
        </span>
        <span className="text-[10px] bg-slate-800 text-slate-400 group-hover:text-slate-200 px-2 py-0.5 rounded-lg border border-slate-700">
          Filtros
        </span>
      </button>

      {/* Pill Indicando Lote em Destaque com Botão Limpar */}
      {highlightedBatchId && highlightedSlotCoords && (
        <div className="flex items-center space-x-2 bg-amber-400/10 border border-amber-400/50 backdrop-blur-md px-3 py-2 rounded-2xl text-amber-300 text-xs shadow-lg animate-in fade-in duration-200">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
          <span className="font-semibold">{highlightedBatchId}</span>
          <span className="text-[10px] bg-amber-400/20 px-1.5 py-0.5 rounded font-mono">
            R{highlightedSlotCoords.street_x} C{highlightedSlotCoords.column_y} N
            {highlightedSlotCoords.level_z}
          </span>
          <button
            onClick={clearSearch}
            className="p-1 rounded-full hover:bg-amber-400/20 text-amber-300 transition"
            title="Limpar destaque"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};
