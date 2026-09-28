"use client";

import React, { useState, useMemo } from "react";
import { useWarehouseStore } from "@/store/useWarehouseStore";
import {
  X,
  Search,
  Coffee,
  Building2,
  Sparkles,
  Check,
  PackageSearch,
  Filter,
} from "lucide-react";

export const SearchModal: React.FC = () => {
  const isSearchModalOpen = useWarehouseStore((state) => state.isSearchModalOpen);
  const setIsSearchModalOpen = useWarehouseStore(
    (state) => state.setIsSearchModalOpen
  );
  const warehouse = useWarehouseStore((state) => state.warehouse);
  const executeFilterSearch = useWarehouseStore(
    (state) => state.executeFilterSearch
  );

  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [selectedCoop, setSelectedCoop] = useState<string>("ALL");
  const [batchIdInput, setBatchIdInput] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Extrai tipos de café e cooperativas presentes no armazém
  const { coffeeTypes, cooperatives } = useMemo(() => {
    if (!warehouse) return { coffeeTypes: [], cooperatives: [] };

    const types = new Set<string>();
    const coops = new Set<string>();

    warehouse.slots.forEach((s) => {
      if (s.batch) {
        if (s.batch.coffee_type) types.add(s.batch.coffee_type);
        if (s.batch.cooperative_id) coops.add(s.batch.cooperative_id);
      }
    });

    return {
      coffeeTypes: Array.from(types).sort(),
      cooperatives: Array.from(coops).sort(),
    };
  }, [warehouse]);

  // Contagem dinâmica de lotes compatíveis
  const matchingCount = useMemo(() => {
    if (!warehouse) return 0;

    return warehouse.slots.filter((s) => {
      if (s.status !== "OCCUPIED" || !s.batch) return false;
      if (selectedType !== "ALL" && s.batch.coffee_type !== selectedType)
        return false;
      if (selectedCoop !== "ALL" && s.batch.cooperative_id !== selectedCoop)
        return false;
      if (
        batchIdInput.trim() &&
        !s.batch.batch_id
          .toUpperCase()
          .includes(batchIdInput.trim().toUpperCase())
      ) {
        return false;
      }
      return true;
    }).length;
  }, [warehouse, selectedType, selectedCoop, batchIdInput]);

  if (!isSearchModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await executeFilterSearch({
        coffeeType: selectedType,
        cooperative: selectedCoop,
        batchId: batchIdInput,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg bg-[#141824] border border-slate-700/80 rounded-3xl shadow-2xl p-5 text-slate-100 max-h-[92vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Cabeçalho */}
        <div className="flex items-center justify-between pb-3.5 border-b border-slate-800 shrink-0">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-2xl bg-amber-400/10 border border-amber-400/30 flex items-center justify-center text-amber-400">
              <PackageSearch className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100 leading-tight">
                Buscar Lote no Armazém
              </h2>
              <p className="text-xs text-slate-400">
                Selecione os filtros para focar no lote ideal (Top 1)
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsSearchModalOpen(false)}
            className="p-1.5 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Formulário com Scroll suave */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
          {/* Filtro: Tipo de Café */}
          <div>
            <label className="flex items-center space-x-2 text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              <Coffee className="w-3.5 h-3.5 text-amber-400" />
              <span>Tipo do Café</span>
            </label>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => setSelectedType("ALL")}
                className={`text-xs py-1.5 px-3 rounded-xl border transition ${selectedType === "ALL"
                    ? "bg-amber-400 text-slate-950 font-bold border-amber-400 shadow-md shadow-amber-400/10"
                    : "bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700"
                  }`}
              >
                Todos os Cafés
              </button>
              {coffeeTypes.map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setSelectedType(type)}
                  className={`text-xs py-1.5 px-3 rounded-xl border transition flex items-center space-x-1.5 ${selectedType === type
                      ? "bg-amber-400 text-slate-950 font-bold border-amber-400 shadow-md shadow-amber-400/10"
                      : "bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700"
                    }`}
                >
                  {selectedType === type && <Check className="w-3.5 h-3.5" />}
                  <span>{type.replace(/_/g, " ")}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Filtro: Cooperado / Cooperativa */}
          <div>
            <label className="flex items-center space-x-2 text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              <Building2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>Cooperado / Cooperativa</span>
            </label>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => setSelectedCoop("ALL")}
                className={`text-xs py-1.5 px-3 rounded-xl border transition ${selectedCoop === "ALL"
                    ? "bg-cyan-400 text-slate-950 font-bold border-cyan-400 shadow-md shadow-cyan-400/10"
                    : "bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700"
                  }`}
              >
                Todas as Cooperativas
              </button>
              {cooperatives.map((coop) => (
                <button
                  key={coop}
                  type="button"
                  onClick={() => setSelectedCoop(coop)}
                  className={`text-xs py-1.5 px-3 rounded-xl border transition flex items-center space-x-1.5 ${selectedCoop === coop
                      ? "bg-cyan-400 text-slate-950 font-bold border-cyan-400 shadow-md shadow-cyan-400/10"
                      : "bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700"
                    }`}
                >
                  {selectedCoop === coop && <Check className="w-3.5 h-3.5" />}
                  <span>{coop}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Código do Lote (Opcional) */}
          <div>
            <label className="flex items-center space-x-2 text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              <Search className="w-3.5 h-3.5 text-emerald-400" />
              <span>Código do Lote (Opcional)</span>
            </label>
            <input
              type="text"
              value={batchIdInput}
              onChange={(e) => setBatchIdInput(e.target.value)}
              placeholder="Digite o código exato (ex: LOT-1043)..."
              className="w-full bg-slate-900/80 border border-slate-700/80 rounded-2xl px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 transition"
            />
          </div>

          {/* Resumo de Matches */}
          <div className="flex items-center justify-between bg-slate-900/50 border border-slate-800 rounded-2xl p-3 text-xs">
            <span className="text-slate-400">Lotes compatíveis no armazém:</span>
            <span
              className={`font-bold px-2 py-0.5 rounded-lg ${matchingCount > 0
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                }`}
            >
              {matchingCount} {matchingCount === 1 ? "lote" : "lotes"}
            </span>
          </div>

          {/* Botão de Ação */}
          <button
            type="submit"
            disabled={matchingCount === 0 || isSubmitting}
            className="w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 active:scale-[0.99] text-slate-950 font-bold py-3.5 px-4 rounded-2xl transition shadow-xl shadow-amber-500/20 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Sparkles className="w-4 h-4" />
            <span>
              {isSubmitting
                ? "Localizando Lote..."
                : matchingCount > 0
                  ? "Buscar melhor rota"
                  : "Nenhum lote com estes filtros"}
            </span>
          </button>
        </form>
      </div>
    </div>
  );
};
