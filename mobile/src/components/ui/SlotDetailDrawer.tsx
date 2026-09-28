"use client";

import React, { useState } from "react";
import { useWarehouseStore } from "@/store/useWarehouseStore";
import { requestPickingRecommendation } from "@/services/warehouseApi";
import {
  X,
  Package,
  Calendar,
  Weight,
  Compass,
  ArrowRight,
  TrendingUp,
  Loader2,
  Building2,
} from "lucide-react";

export const SlotDetailDrawer: React.FC = () => {
  const selectedSlot = useWarehouseStore((state) => state.selectedSlot);
  const selectSlot = useWarehouseStore((state) => state.selectSlot);
  const warehouse = useWarehouseStore((state) => state.warehouse);
  const setPickingRecommendations = useWarehouseStore(
    (state) => state.setPickingRecommendations
  );

  const [isLoadingPicking, setIsLoadingPicking] = useState(false);

  if (!selectedSlot) return null;

  const { coordinates, status, batch } = selectedSlot;
  const isOccupied = status === "OCCUPIED" && batch !== null;

  // Distância Euclidiana aproximada até a Doca [0,0,0]
  const distToDock = Math.sqrt(
    coordinates.street_x ** 2 +
    coordinates.column_y ** 2 +
    coordinates.level_z ** 2
  ).toFixed(1);

  const handleRequestPicking = async () => {
    if (!warehouse) return;
    setIsLoadingPicking(true);
    try {
      const res = await requestPickingRecommendation({
        warehouse_id: warehouse.warehouse_id,
        coffee_type: batch ? batch.coffee_type : "ARABICA",
        cooperative_id: batch?.cooperative_id,
        max_recommendations: 4,
      });
      setPickingRecommendations(res.recommendations);
    } catch (err) {
      console.error("Falha ao gerar picking:", err);
    } finally {
      setIsLoadingPicking(false);
    }
  };

  return (
    <div className="absolute bottom-0 left-0 right-0 z-30 pointer-events-auto max-w-lg mx-auto p-3 animate-in slide-in-from-bottom-6 duration-200">
      <div className="bg-[#141824]/95 backdrop-blur-xl border border-slate-700/80 rounded-3xl p-4 shadow-2xl text-slate-100">
        {/* Barra superior com Status e Fechar */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <span
              className={`w-3 h-3 rounded-full ${isOccupied
                ? "bg-rose-500 shadow-lg shadow-rose-500/50"
                : "bg-emerald-500 shadow-lg shadow-emerald-500/50"
                }`}
            />
            <span className="text-xs uppercase font-bold tracking-wider">
              {isOccupied ? "Posição Ocupada" : "Posição Livre"}
            </span>
            <span className="text-[11px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full font-mono">
              Rua {coordinates.street_x} • Col {coordinates.column_y} • Nível{" "}
              {coordinates.level_z}
            </span>
          </div>

          <button
            onClick={() => selectSlot(null)}
            className="p-1 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Conteúdo do Lote se Ocupado */}
        {isOccupied ? (
          <div className="py-3 space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">
                  Identificador do Lote
                </p>
                <h3 className="text-lg font-bold text-amber-300 font-mono tracking-tight">
                  {batch.batch_id}
                </h3>
              </div>
              <span className="text-xs bg-amber-400/10 border border-amber-400/30 text-amber-300 font-semibold px-2.5 py-1 rounded-xl">
                {batch.coffee_type}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-slate-900/60 p-2.5 rounded-2xl border border-slate-800/80 flex items-center space-x-2.5">
                <Building2 className="w-4 h-4 text-slate-400 shrink-0" />
                <div className="overflow-hidden">
                  <p className="text-[10px] text-slate-400 leading-tight">
                    Cooperativa
                  </p>
                  <p className="font-semibold text-slate-200 truncate">
                    {batch.cooperative_id}
                  </p>
                </div>
              </div>

              <div className="bg-slate-900/60 p-2.5 rounded-2xl border border-slate-800/80 flex items-center space-x-2.5">
                <Weight className="w-4 h-4 text-emerald-400 shrink-0" />
                <div>
                  <p className="text-[10px] text-slate-400 leading-tight">
                    Peso Total
                  </p>
                  <p className="font-semibold text-emerald-400">
                    {batch.weight_kg} kg
                  </p>
                </div>
              </div>

              <div className="bg-slate-900/60 p-2.5 rounded-2xl border border-slate-800/80 flex items-center space-x-2.5">
                <Calendar className="w-4 h-4 text-slate-400 shrink-0" />
                <div>
                  <p className="text-[10px] text-slate-400 leading-tight">
                    Safra
                  </p>
                  <p className="font-semibold text-slate-200">
                    {batch.harvest_year}
                  </p>
                </div>
              </div>

              <div className="bg-slate-900/60 p-2.5 rounded-2xl border border-slate-800/80 flex items-center space-x-2.5">
                <Compass className="w-4 h-4 text-cyan-400 shrink-0" />
                <div>
                  <p className="text-[10px] text-slate-400 leading-tight">
                    Distância da Doca
                  </p>
                  <p className="font-semibold text-cyan-400">{distToDock} m</p>
                </div>
              </div>
            </div>

            {/* Ação de Picking Heurístico */}
            <button
              onClick={handleRequestPicking}
              disabled={isLoadingPicking}
              className="w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 active:scale-[0.99] text-slate-950 font-bold py-2.5 px-4 rounded-2xl transition shadow-lg shadow-amber-500/20 text-xs disabled:opacity-50"
            >
              {isLoadingPicking ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Calculando Rota...</span>
                </>
              ) : (
                <>
                  <TrendingUp className="w-4 h-4" />
                  <span>Recomendar rota para este item</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="py-4 space-y-3">
            <p className="text-xs text-slate-300">
              Este espaço está <strong>livre</strong> e apto para receber novos items.
            </p>
            <div className="flex items-center justify-between text-xs bg-slate-900/60 p-2.5 rounded-2xl border border-slate-800/80">
              <span className="text-slate-400">Distância até a Doca 01:</span>
              <span className="font-semibold text-cyan-400">{distToDock} m</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
