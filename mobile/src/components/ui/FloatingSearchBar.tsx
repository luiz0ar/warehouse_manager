"use client";

import React, { useState } from "react";
import { useWarehouseStore } from "@/store/useWarehouseStore";
import { Search, X, CheckCircle2, Sparkles, Filter } from "lucide-react";

export const FloatingSearchBar: React.FC = () => {
  const searchQuery = useWarehouseStore((state) => state.searchQuery);
  const setSearchQuery = useWarehouseStore((state) => state.setSearchQuery);
  const clearSearch = useWarehouseStore((state) => state.clearSearch);
  const highlightedBatchId = useWarehouseStore((state) => state.highlightedBatchId);
  const highlightedSlotCoords = useWarehouseStore((state) => state.highlightedSlotCoords);
  const searchFilterType = useWarehouseStore((state) => state.searchFilterType);
  const setSearchFilterType = useWarehouseStore((state) => state.setSearchFilterType);
  const warehouse = useWarehouseStore((state) => state.warehouse);
  const selectSlot = useWarehouseStore((state) => state.selectSlot);

  const [isFilterOpen, setIsFilterOpen] = useState(false);

  // Filtra sugestões rápidas se houver texto
  const quickMatches =
    searchQuery.trim().length > 1 && warehouse
      ? warehouse.slots
          .filter(
            (s) =>
              s.batch &&
              s.batch.batch_id.toUpperCase().includes(searchQuery.trim().toUpperCase())
          )
          .slice(0, 3)
      : [];

  const handleFilterClick = (type: string) => {
    setSearchFilterType(type);
    if (type !== "ALL" && warehouse) {
      // Procura primeiro lote que atenda ao filtro
      const match = warehouse.slots.find(
        (s) => s.batch && s.batch.coffee_type.toUpperCase() === type.toUpperCase()
      );
      if (match) {
        selectSlot(match);
      }
    }
  };

  return (
    <div className="absolute top-16 left-3 right-3 sm:left-6 sm:right-auto sm:w-96 z-20 pointer-events-auto flex flex-col space-y-2">
      {/* Campo de Busca Principal */}
      <div className="relative flex items-center bg-[#141824]/95 backdrop-blur-md border border-slate-700/80 rounded-2xl shadow-2xl p-1.5 transition-all focus-within:border-amber-400/70 focus-within:ring-2 focus-within:ring-amber-400/20">
        <div className="pl-2.5 text-slate-400">
          <Search className="w-4 h-4" />
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Buscar lote (ex: LOTE-2026-001)..."
          className="w-full bg-transparent px-2.5 py-1.5 text-sm text-slate-100 placeholder-slate-400 outline-none"
        />
        {searchQuery && (
          <button
            onClick={clearSearch}
            className="p-1 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        )}
        <button
          onClick={() => setIsFilterOpen(!isFilterOpen)}
          className={`p-1.5 rounded-xl border ml-1 transition ${
            isFilterOpen || searchFilterType !== "ALL"
              ? "bg-amber-400/10 text-amber-400 border-amber-400/40"
              : "text-slate-400 border-slate-700/60 hover:text-white"
          }`}
          title="Filtrar por café"
        >
          <Filter className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Pills de Filtro Rápido */}
      {isFilterOpen && (
        <div className="flex items-center space-x-1.5 bg-[#141824]/90 backdrop-blur-md p-1.5 rounded-xl border border-slate-800 animate-in fade-in slide-in-from-top-1 duration-150">
          {["ALL", "ARABICA", "CONILON"].map((type) => (
            <button
              key={type}
              onClick={() => handleFilterClick(type)}
              className={`flex-1 text-[11px] font-medium py-1 px-2 rounded-lg transition ${
                searchFilterType === type
                  ? "bg-amber-400 text-slate-950 font-semibold shadow-sm"
                  : "text-slate-300 hover:bg-slate-800"
              }`}
            >
              {type === "ALL" ? "Todos os Cafés" : type}
            </button>
          ))}
        </div>
      )}

      {/* Sugestões de Auto-complete rápidas */}
      {quickMatches.length > 0 && !highlightedBatchId && (
        <div className="bg-[#141824]/95 backdrop-blur-md border border-slate-800 rounded-xl overflow-hidden shadow-xl p-1">
          {quickMatches.map((slot) => (
            <button
              key={slot.batch!.batch_id}
              onClick={() => selectSlot(slot)}
              className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-slate-800/80 transition text-left"
            >
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                <span className="text-xs font-semibold text-slate-200">
                  {slot.batch!.batch_id}
                </span>
                <span className="text-[10px] text-slate-400">
                  ({slot.batch!.coffee_type})
                </span>
              </div>
              <span className="text-[10px] text-slate-400">
                R{slot.coordinates.street_x} • C{slot.coordinates.column_y} • N
                {slot.coordinates.level_z}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Notificação de Lote Localizado (Amarelo) */}
      {highlightedBatchId && highlightedSlotCoords && (
        <div className="flex items-center justify-between bg-amber-400/10 border border-amber-400/40 backdrop-blur-md px-3 py-2 rounded-xl text-amber-300 text-xs shadow-lg animate-in fade-in">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping" />
            <span>
              Lote <strong>{highlightedBatchId}</strong> localizado em amarelo!
            </span>
          </div>
          <span className="text-[10px] bg-amber-400/20 px-2 py-0.5 rounded font-mono">
            R{highlightedSlotCoords.street_x} C{highlightedSlotCoords.column_y} N
            {highlightedSlotCoords.level_z}
          </span>
        </div>
      )}
    </div>
  );
};
