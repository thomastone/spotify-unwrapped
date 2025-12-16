"use client";

import Hero from "../components/Hero";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center p-8 md:p-24 overflow-x-hidden selection:bg-green-500/30 selection:text-green-200">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm lg:flex mb-12 absolute top-8 left-8 right-8 pointer-events-none">
        <div className="fixed bottom-0 left-0 flex h-48 w-full items-end justify-center bg-gradient-to-t from-slate-950 via-slate-950 lg:static lg:h-auto lg:w-auto lg:bg-none pointer-events-auto">
             <a
              className="flex place-items-center gap-2 p-8 lg:p-0 text-slate-500 hover:text-white transition-colors"
              href="https://github.com/yourusername/spotify-unwrapped" 
              target="_blank"
              rel="noopener noreferrer"
            >
              v0.2.0 // Beta
            </a>
        </div>
      </div>

      <Hero />
      
      <div className="fixed inset-0 -z-10 h-full w-full bg-slate-950">
        <div className="absolute bottom-0 left-0 right-0 top-0 bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:14px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>
      </div>
    </main>
  );
}
