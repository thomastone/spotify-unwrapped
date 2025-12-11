"use client";

import { useState } from "react";
import FileUploader from "../components/FileUploader";
import { ResponsiveCalendar } from "@nivo/calendar";

export default function Home() {
  const [data, setData] = useState<any>(null);

  return (
    <main className="flex min-h-screen flex-col items-center p-8 md:p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex mb-12">
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-green-400 to-blue-500 text-transparent bg-clip-text">
          SPOTIFY <span className="text-white">UNWRAPPED</span>
        </h1>
        <div className="fixed bottom-0 left-0 flex h-48 w-full items-end justify-center bg-gradient-to-t from-black via-black lg:static lg:h-auto lg:w-auto lg:bg-none">
          <p className="text-slate-400">v0.1.0 // Prototype</p>
        </div>
      </div>

      {!data ? (
        // STATE 1: No Data -> Show Uploader
        <div className="w-full max-w-xl animate-in fade-in zoom-in duration-500">
          <FileUploader onDataReceived={(res) => setData(res)} />
        </div>
      ) : (
        // STATE 2: Data Exists -> Show Visualization
        <div className="w-full animate-in slide-in-from-bottom duration-700">
          <div className="bg-slate-900/50 p-6 rounded-2xl border border-slate-800 backdrop-blur-sm">
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
              📅 Listening Consistency
            </h2>
            
            <div className="h-[400px] w-full text-black">
              {/* Nivo Calendar expects "day" and "value" keys, which our Python backend provides */}
              <ResponsiveCalendar
                data={data.heatmap}
                from="2023-01-01" 
                to="2023-12-31" 
                emptyColor="#1e293b" // slate-800
                colors={['#0e4429', '#006d32', '#26a641', '#39d353']} // GitHub Green scale
                margin={{ top: 40, right: 40, bottom: 40, left: 40 }}
                yearSpacing={40}
                monthBorderColor="#0f172a"
                dayBorderWidth={2}
                dayBorderColor="#0f172a"
                legends={[
                  {
                    anchor: 'bottom-right',
                    direction: 'row',
                    translateY: 36,
                    itemCount: 4,
                    itemWidth: 42,
                    itemHeight: 36,
                    itemsSpacing: 14,
                    itemDirection: 'right-to-left'
                  }
                ]}
              />
            </div>

            <div className="mt-8 grid grid-cols-2 gap-4">
              <div className="p-4 bg-slate-800 rounded-lg">
                <p className="text-slate-400 text-sm">Total Tracks Processed</p>
                <p className="text-3xl font-bold text-white">{data.total_tracks.toLocaleString()}</p>
              </div>
              <div className="p-4 bg-slate-800 rounded-lg">
                 <p className="text-slate-400 text-sm">Active Listening Days</p>
                 <p className="text-3xl font-bold text-green-400">{data.heatmap.length}</p>
              </div>
            </div>
            
            <button 
              onClick={() => setData(null)}
              className="mt-8 text-sm text-slate-500 hover:text-white underline"
            >
              Upload different files
            </button>
          </div>
        </div>
      )}
    </main>
  );
}