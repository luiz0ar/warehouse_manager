"use client";

import React, { useState } from "react";
import { Info, HelpCircle } from "lucide-react";

export const LegendOverlay: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="absolute bottom-4 left-3 z-20 pointer-events-auto">
      {isOpen ? (
        <div className="bg-[#141824]/95 backdrop-blur-xl border border-slate-700/80 rounded-2xl p-3 shadow-2xl text-slate-200 text-xs space-y-2 animate-in fade-in duration-150 max-w-[240px]">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
            <span className="font-semibold text-slate-100">Legenda 3D</span>
            <button
              onClick={() => setIsOpen(false)}
              className="text-[10px] text-slate-400 hover:text-white"
            >
              Fechar
            </button>
          </div>

          <div className="space-y-1.5 text-[11px]">
            <div className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-md bg-[#22c55e]" />
              <span>Espaço Livre</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-md bg-[#ef4444]" />
              <span>Espaço Ocupado</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-md bg-[#facc15]" />
              <span>Lote Buscado / Alvo</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-md border border-[#38bdf8] bg-[#38bdf8]/20" />
              <span>Doca (Marco Zero)</span>
            </div>
          </div>

          <p className="text-[10px] text-slate-400 pt-1 border-t border-slate-800">
            👆 <strong>Toque:</strong> 1 dedo gira • 2 dedos zoom/pan • Toque
            no cubo para detalhes.
          </p>
        </div>
      ) : (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center space-x-1.5 bg-[#141824]/80 hover:bg-[#141824] backdrop-blur-md border border-slate-800 text-slate-300 px-2.5 py-1.5 rounded-full text-xs shadow-lg transition"
        >
          <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-[11px]">Legenda</span>
        </button>
      )}
    </div>
  );
};
