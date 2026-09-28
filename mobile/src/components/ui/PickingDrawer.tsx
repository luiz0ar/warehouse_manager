"use client";

import React from "react";
import { useWarehouseStore } from "@/store/useWarehouseStore";
import { X, Navigation, Award, ArrowUpRight } from "lucide-react";

export const PickingDrawer: React.FC = () => {
  const pickingRecommendations = useWarehouseStore(
    (state) => state.pickingRecommendations
  );
  const activePickingRank = useWarehouseStore((state) => state.activePickingRank);
  const focusPickingRank = useWarehouseStore((state) => state.focusPickingRank);
  const clearPicking = useWarehouseStore((state) => state.clearPicking);

  if (pickingRecommendations.length === 0) return null;

  return (
    <div className="absolute top-36 right-3 left-3 sm:left-auto sm:right-6 sm:w-80 z-20 pointer-events-auto animate-in fade-in slide-in-from-right-4 duration-200">
      <div className="bg-[#141824]/95 backdrop-blur-xl border border-amber-400/40 rounded-3xl p-3.5 shadow-2xl text-slate-100">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 rounded-lg bg-amber-400/20 text-amber-400 flex items-center justify-center">
              <Navigation className="w-3.5 h-3.5" />
            </div>
            <h3 className="text-xs font-bold text-amber-300 uppercase tracking-wider">
              Rota Ótima de Picking
            </h3>
          </div>
          <button
            onClick={clearPicking}
            className="p-1 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        <p className="text-[10px] text-slate-400 mb-2">
          Ordem recomendada pela função de custo $Z = \alpha D + \beta R$:
        </p>

        <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
          {pickingRecommendations.map((item) => {
            const isSelected = activePickingRank === item.rank;
            return (
              <button
                key={item.batch_id}
                onClick={() => focusPickingRank(item.rank)}
                className={`w-full flex items-center justify-between p-2 rounded-2xl border transition text-left ${
                  isSelected
                    ? "bg-amber-400/15 border-amber-400/60 shadow-md"
                    : "bg-slate-900/60 border-slate-800 hover:bg-slate-800/60"
                }`}
              >
                <div className="flex items-center space-x-2.5">
                  <div
                    className={`w-6 h-6 rounded-xl flex items-center justify-center text-[11px] font-bold ${
                      isSelected
                        ? "bg-amber-400 text-slate-950 font-black shadow-sm"
                        : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    #{item.rank}
                  </div>
                  <div>
                    <p className="text-xs font-bold font-mono text-slate-200">
                      {item.batch_id}
                    </p>
                    <p className="text-[10px] text-slate-400">
                      R{item.coordinates.street_x} • C{item.coordinates.column_y} •
                      N{item.coordinates.level_z}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-[10px] text-emerald-400 font-semibold block">
                    {item.distance_to_dock}m doca
                  </span>
                  <span className="text-[9px] text-slate-400">
                    Custo Z: {item.estimated_cost}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
