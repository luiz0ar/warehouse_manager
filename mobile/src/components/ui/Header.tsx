"use client";

import React from "react";
import { useWarehouseStore } from "@/store/useWarehouseStore";
import { Box, Layers, Radio } from "lucide-react";

export const Header: React.FC = () => {
  const warehouse = useWarehouseStore((state) => state.warehouse);
  const isMockMode = useWarehouseStore((state) => state.isMockMode);

  return (
    <header className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between p-3.5 bg-gradient-to-b from-[#0f1117]/95 via-[#0f1117]/80 to-transparent backdrop-blur-sm pointer-events-auto">
      <div className="flex items-center space-x-2.5">
        <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-lg shadow-emerald-500/5">
          <Layers className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-sm font-semibold text-slate-100 tracking-tight leading-none">
            Armazém 3D
          </h1>
          <p className="text-[11px] text-slate-400 mt-0.5 leading-none">
            {warehouse ? warehouse.name : "Carregando topologia..."}
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        {warehouse && (
          <div className="flex items-center space-x-1.5 text-xs bg-slate-900/80 border border-slate-800 rounded-full px-2.5 py-1">
            <span className="flex items-center text-emerald-400 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 mr-1 animate-pulse" />
              {warehouse.free_slots_count}
            </span>
            <span className="text-slate-600">/</span>
            <span className="flex items-center text-rose-400 font-medium">
              <span className="w-2 h-2 rounded-full bg-rose-500 mr-1" />
              {warehouse.occupied_slots_count}
            </span>
          </div>
        )}

        <div
          className={`flex items-center text-[10px] uppercase font-semibold px-2 py-0.5 rounded-md border ${
            isMockMode
              ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
              : "bg-cyan-500/10 text-cyan-400 border-cyan-500/30"
          }`}
        >
          <Radio className="w-2.5 h-2.5 mr-1" />
          {isMockMode ? "Simulado" : "Live API"}
        </div>
      </div>
    </header>
  );
};
